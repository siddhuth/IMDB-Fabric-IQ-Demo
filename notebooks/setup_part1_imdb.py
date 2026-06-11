# ============================================================
# IMDB Casting Graph — Setup Part 1: Download, Filter, Enrich
# ============================================================
# Paste into Cell 1 of a Fabric notebook attached to your
# Lakehouse. Downloads real IMDB datasets, filters to ~25K
# movies (1970+, 1K+ votes), normalizes into graph-ready tables.
#
# Expected runtime: ~3-5 min (mostly download time on F2).
# ============================================================

from pyspark.sql import functions as F
from pyspark.sql.window import Window
import urllib.request, os, time

# ── Configuration ──
IMDB_BASE = "https://datasets.imdbws.com"
FILES = [
    "title.basics.tsv.gz",
    "title.ratings.tsv.gz",
    "title.principals.tsv.gz",
    "name.basics.tsv.gz",
]
MIN_YEAR = 1970
MIN_VOTES = 1000
LAKEHOUSE_FILES = "/lakehouse/default/Files/imdb"

# Tier thresholds — referenced by config/agent_prompt.md and
# config/ontology/entity_descriptions.md. Change in ALL places or run
# the demo/QUALITY_GATES.md review to catch drift.
TOP_TIER_RATING = 7.5      # title_tier "Top" / sentiment_tier "Acclaimed"
BOTTOM_TIER_RATING = 4.5   # title_tier "Bottom"
SOLID_RATING = 5.5         # sentiment_tier "Solid"
MIXED_RATING = 4.0         # sentiment_tier "Mixed"
VIRAL_VOTES = 100_000      # votes_tier "Viral"
POPULAR_VOTES = 10_000     # votes_tier "Popular"
LEAD_BILLING_ORDER = 3     # is_lead


def votes_tier_col():
    return (
        F.when(F.col("num_votes") >= VIRAL_VOTES, "Viral")
         .when(F.col("num_votes") >= POPULAR_VOTES, "Popular")
         .otherwise("Niche")
    )

# ── Step 1: Download IMDB datasets ──
os.makedirs(LAKEHOUSE_FILES, exist_ok=True)
for f in FILES:
    dest = f"{LAKEHOUSE_FILES}/{f}"
    if os.path.exists(dest):
        print(f"  ⏭️  {f} already exists, skipping")
    else:
        print(f"  ⬇️  Downloading {f}...")
        urllib.request.urlretrieve(f"{IMDB_BASE}/{f}", dest)
        size_mb = os.path.getsize(dest) / (1024 * 1024)
        print(f"  ✅ {f} ({size_mb:.1f} MB)")

print("\nAll IMDB files downloaded. Reading into Spark...\n")

# ── Step 2: Read raw TSVs ──
def read_imdb(filename):
    return spark.read.csv(
        f"Files/imdb/{filename}",
        sep="\t",
        header=True,
        nullValue="\\N",
    )

basics_raw = read_imdb("title.basics.tsv.gz")
ratings_raw = read_imdb("title.ratings.tsv.gz")
principals_raw = read_imdb("title.principals.tsv.gz")
names_raw = read_imdb("name.basics.tsv.gz")

print("  All 4 datasets loaded into Spark. Filtering...")

# ── Step 3: Filter to movies, 1970+, 1K+ votes ──
titles_filtered = (
    basics_raw
    .filter(F.col("titleType") == "movie")
    .filter(F.col("startYear").cast("int") >= MIN_YEAR)
    .filter(F.col("isAdult") == "0")
    .join(ratings_raw, "tconst", "inner")
    .filter(F.col("numVotes").cast("int") >= MIN_VOTES)
)

title_ids = titles_filtered.select("tconst")

principals_filtered = principals_raw.join(title_ids, "tconst", "inner")

person_ids = principals_filtered.select("nconst").distinct()
names_filtered = names_raw.join(person_ids, "nconst", "inner")

print(f"\nAfter filtering (movies, {MIN_YEAR}+, {MIN_VOTES}+ votes):")
print(f"  Titles:     {titles_filtered.count():>10,}")
print(f"  Principals: {principals_filtered.count():>10,}")
print(f"  People:     {names_filtered.count():>10,}")

# ── Step 4: Build the Titles table ──
titles_df = (
    titles_filtered
    .select(
        F.col("tconst").alias("title_id"),
        F.col("primaryTitle").alias("primary_title"),
        F.col("startYear").cast("int").alias("start_year"),
        F.col("runtimeMinutes").cast("int").alias("runtime_minutes"),
        F.col("genres").alias("genres_str"),
        F.col("averageRating").cast("double").alias("avg_rating"),
        F.col("numVotes").cast("int").alias("num_votes"),
    )
    .withColumn("decade", (F.floor(F.col("start_year") / 10) * 10).cast("int"))
    .withColumn(
        "title_tier",
        F.when(F.col("avg_rating") >= TOP_TIER_RATING, "Top")
         .when(F.col("avg_rating") < BOTTOM_TIER_RATING, "Bottom")
         .otherwise("Middle"),
    )
    .withColumn("votes_tier", votes_tier_col())
    .withColumn(
        "primary_genre",
        F.split(F.col("genres_str"), ",").getItem(0),
    )
)
step_start = time.time()
titles_df.write.format("delta").mode("overwrite").saveAsTable("titles")
print(f"\n  ✅ titles written [{time.time()-step_start:.1f}s]")

# ── Step 5: Build the People table ──
people_base = (
    names_filtered
    .select(
        F.col("nconst").alias("person_id"),
        F.col("primaryName").alias("name"),
        F.col("birthYear").cast("int").alias("birth_year"),
        F.col("deathYear").cast("int").alias("death_year"),
        F.col("primaryProfession").alias("primary_profession_str"),
        F.col("knownForTitles").alias("known_for_titles_str"),
    )
    .withColumn(
        "primary_profession",
        F.split(F.col("primary_profession_str"), ",").getItem(0),
    )
)

# Compute career stats from principals
career_stats = (
    principals_filtered
    .groupBy("nconst")
    .agg(
        F.countDistinct("tconst").alias("career_title_count"),
    )
)

# Compute average rating across their filmography
person_avg_rating = (
    principals_filtered
    .join(titles_filtered.select("tconst", "averageRating", "startYear"), "tconst", "inner")
    .groupBy("nconst")
    .agg(
        F.round(F.avg(F.col("averageRating").cast("double")), 2).alias("avg_title_rating"),
        F.min(F.col("startYear").cast("int")).alias("first_title_year"),
        F.max(F.col("startYear").cast("int")).alias("last_title_year"),
    )
)

# Compute dominant genre per person
person_genres = (
    principals_filtered
    .join(
        titles_filtered.select("tconst", F.split("genres", ",").getItem(0).alias("pg")),
        "tconst", "inner",
    )
    .groupBy("nconst", "pg")
    .count()
)
genre_window = Window.partitionBy("nconst").orderBy(F.desc("count"))
dominant_genre = (
    person_genres
    .withColumn("rn", F.row_number().over(genre_window))
    .filter(F.col("rn") == 1)
    .select(F.col("nconst"), F.col("pg").alias("dominant_genre"))
)

people_df = (
    people_base
    .join(career_stats, people_base["person_id"] == career_stats["nconst"], "left")
    .join(person_avg_rating, people_base["person_id"] == person_avg_rating["nconst"], "left")
    .join(dominant_genre, people_base["person_id"] == dominant_genre["nconst"], "left")
    .withColumn(
        "career_span_years",
        F.col("last_title_year") - F.col("first_title_year"),
    )
    .withColumn(
        "is_active",
        F.col("last_title_year") >= 2020,
    )
    .select(
        "person_id", "name", "birth_year", "death_year",
        "primary_profession", "career_title_count", "avg_title_rating",
        "first_title_year", "last_title_year", "career_span_years",
        "dominant_genre", "is_active",
    )
)
step_start = time.time()
people_df.write.format("delta").mode("overwrite").saveAsTable("people")
print(f"  ✅ people written [{time.time()-step_start:.1f}s]")

# ── Step 6: Build the Casting Decisions table ──
# This is the graph edge — connects People to Titles with role metadata
casting_base = (
    principals_filtered
    .select(
        F.col("tconst").alias("title_id"),
        F.col("nconst").alias("person_id"),
        F.col("ordering").cast("int").alias("billing_order"),
        F.col("category"),
        F.col("job"),
        F.col("characters").alias("character_name"),
    )
    # (tconst, ordering) is the primary key of IMDB title.principals, so this
    # is unique. Part 3 Step 0 validates it before it becomes the entity key.
    .withColumn(
        "cast_id",
        F.concat(F.col("title_id"), F.lit("_"), F.col("billing_order").cast("string")),
    )
    .withColumn("is_lead", F.col("billing_order") <= LEAD_BILLING_ORDER)
)

# Add career_stage at time of this title (how experienced was the person then?)
title_years = titles_df.select("title_id", "start_year")
person_first_year = people_df.select(
    F.col("person_id"), F.col("first_title_year")
)

casting_with_stage = (
    casting_base
    .join(title_years, "title_id", "left")
    .join(person_first_year, "person_id", "left")
    .withColumn(
        "years_in_career",
        F.greatest(F.lit(0), F.col("start_year") - F.col("first_title_year")),
    )
    .withColumn(
        "career_stage",
        F.when(F.col("years_in_career").isNull(), "Newcomer")
         .when(F.col("years_in_career") <= 2, "Newcomer")
         .when(F.col("years_in_career") <= 8, "Rising")
         .when(F.col("years_in_career") <= 25, "Established")
         .otherwise("Veteran"),
    )
)

# Add was_against_type flag (person's dominant genre != title's primary genre)
person_dom_genre = people_df.select(
    F.col("person_id"), F.col("dominant_genre").alias("person_genre")
)
title_genre = titles_df.select(
    F.col("title_id"), F.col("primary_genre").alias("title_genre")
)

casting_df = (
    casting_with_stage
    .join(person_dom_genre, "person_id", "left")
    .join(title_genre, "title_id", "left")
    .withColumn(
        "was_against_type",
        (F.col("person_genre").isNotNull())
        & (F.col("title_genre").isNotNull())
        & (F.col("person_genre") != F.col("title_genre")),
    )
    .select(
        "cast_id", "title_id", "person_id", "category", "billing_order",
        "character_name", "is_lead", "career_stage", "was_against_type",
    )
)
step_start = time.time()
casting_df.write.format("delta").mode("overwrite").saveAsTable("casting_decisions")
print(f"  ✅ casting_decisions written [{time.time()-step_start:.1f}s]")

# ── Step 7: Build the Ratings table (1:1 with titles) ──
ratings_df = (
    titles_filtered
    .select(
        F.col("tconst").alias("title_id"),
        F.col("averageRating").cast("double").alias("avg_rating"),
        F.col("numVotes").cast("int").alias("num_votes"),
    )
    .withColumn(
        "sentiment_tier",
        F.when(F.col("avg_rating") >= TOP_TIER_RATING, "Acclaimed")
         .when(F.col("avg_rating") >= SOLID_RATING, "Solid")
         .when(F.col("avg_rating") >= MIXED_RATING, "Mixed")
         .otherwise("Panned"),
    )
    .withColumn("votes_tier", votes_tier_col())
)
step_start = time.time()
ratings_df.write.format("delta").mode("overwrite").saveAsTable("ratings")
print(f"  ✅ ratings written [{time.time()-step_start:.1f}s]")

# ── Step 8: Build the Genres dimension ──
# Explode the comma-separated genres into individual rows, then aggregate
genres_exploded = (
    titles_filtered
    .select(
        F.col("tconst"),
        F.explode(F.split("genres", ",")).alias("genre_name"),
        F.col("averageRating").cast("double").alias("rating"),
    )
    .filter(F.col("genre_name").isNotNull())
)
genres_df = (
    genres_exploded
    .groupBy("genre_name")
    .agg(
        F.count("*").alias("title_count"),
        F.round(F.avg("rating"), 2).alias("avg_rating"),
    )
    .withColumn("genre_id", F.col("genre_name"))
)
step_start = time.time()
genres_df.write.format("delta").mode("overwrite").saveAsTable("genres")
print(f"  ✅ genres written [{time.time()-step_start:.1f}s]")

print("\n✅ Part 1 complete. Run Part 2 for synthetic BoxOffice + Kevin Bacon + validation.")

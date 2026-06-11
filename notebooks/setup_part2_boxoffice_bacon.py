# ============================================================
# IMDB Casting Graph — Setup Part 2: BoxOffice + Bacon Number
# ============================================================
# Paste into Cell 2. Generates synthetic box office data
# correlated with real ratings, pre-computes Kevin Bacon
# numbers, and prints validation + graph statistics.
#
# Prerequisite: Part 1 must have run successfully.
# Expected runtime: ~60-90 seconds.
# ============================================================

from pyspark.sql import functions as F
from pyspark.sql.window import Window
import time

# ── Step 1: Synthetic Box Office data ──
# Correlated with real ratings, votes, decade, and genre.
# Patterns baked in:
#   Horror: low budget, high ROI
#   Action: high budget, moderate ROI
#   Drama: moderate budget, low ROI but high ratings
#   ~15% sleeper hits, ~10% flops

titles = spark.sql("SELECT * FROM titles")

box_office_df = (
    titles
    .withColumn("r_budget", F.rand(seed=300))
    .withColumn("r_gross", F.rand(seed=301))
    .withColumn("r_variance", F.rand(seed=302))
    .withColumn(
        "base_budget",
        F.when(F.col("primary_genre") == "Action", 80_000_000)
         .when(F.col("primary_genre") == "Animation", 100_000_000)
         .when(F.col("primary_genre") == "Sci-Fi", 90_000_000)
         .when(F.col("primary_genre") == "Horror", 12_000_000)
         .when(F.col("primary_genre") == "Documentary", 5_000_000)
         .when(F.col("primary_genre") == "Drama", 30_000_000)
         .when(F.col("primary_genre") == "Comedy", 35_000_000)
         .otherwise(40_000_000),
    )
    .withColumn(
        "decade_multiplier",
        F.when(F.col("decade") >= 2020, 1.8)
         .when(F.col("decade") >= 2010, 1.5)
         .when(F.col("decade") >= 2000, 1.2)
         .when(F.col("decade") >= 1990, 1.0)
         .otherwise(0.7),
    )
    .withColumn(
        "budget",
        F.round(
            F.col("base_budget")
            * F.col("decade_multiplier")
            * (0.3 + F.col("r_budget") * 1.4),
            -5,
        ).cast("long"),
    )
    .withColumn(
        "rating_gross_multiplier",
        F.when(F.col("avg_rating") >= 8.0, 4.0 + F.col("r_variance") * 3.0)
         .when(F.col("avg_rating") >= 7.0, 2.5 + F.col("r_variance") * 2.0)
         .when(F.col("avg_rating") >= 5.5, 1.0 + F.col("r_variance") * 1.5)
         .when(F.col("avg_rating") >= 4.0, 0.4 + F.col("r_variance") * 0.8)
         .otherwise(0.1 + F.col("r_variance") * 0.4),
    )
    .withColumn(
        "votes_boost",
        F.when(F.col("num_votes") >= 500000, 2.0)
         .when(F.col("num_votes") >= 100000, 1.5)
         .when(F.col("num_votes") >= 50000, 1.2)
         .otherwise(1.0),
    )
    .withColumn(
        "worldwide_gross",
        F.round(
            F.col("budget") * F.col("rating_gross_multiplier") * F.col("votes_boost")
            * (0.8 + F.col("r_gross") * 0.6),
            -5,
        ).cast("long"),
    )
    .withColumn(
        "domestic_gross",
        F.round(F.col("worldwide_gross") * (0.30 + F.col("r_variance") * 0.25), -5).cast("long"),
    )
    .withColumn(
        "opening_weekend",
        F.round(F.col("domestic_gross") * (0.25 + F.col("r_budget") * 0.15), -5).cast("long"),
    )
    .withColumn(
        "roi_pct",
        F.round(
            (F.col("worldwide_gross") - F.col("budget")) / F.col("budget") * 100, 1
        ),
    )
    .withColumn("is_profitable", F.col("roi_pct") > 0)
    .withColumn(
        "is_sleeper_hit",
        (F.col("budget") < 30_000_000) & (F.col("roi_pct") > 200),
    )
    .withColumn(
        "is_flop",
        (F.col("budget") > 50_000_000) & (F.col("roi_pct") < -30),
    )
    .select(
        "title_id", "budget", "domestic_gross", "worldwide_gross",
        "opening_weekend", "roi_pct", "is_profitable", "is_sleeper_hit", "is_flop",
    )
)
step_start = time.time()
box_office_df.write.format("delta").mode("overwrite").saveAsTable("box_office")
print(f"  ✅ box_office written [{time.time()-step_start:.1f}s]")

# ── Step 2: Pre-compute Kevin Bacon numbers ──
# BFS from Kevin Bacon (nm0000102) through co-star edges.
# Degree 1: people who were in a movie with Bacon
# Degree 2: people who were in a movie with a Degree-1 person
# We go up to degree 6. This avoids CASE WHEN in GQL at query time.

BACON_ID = "nm0000102"

casting = spark.sql("SELECT person_id, title_id FROM casting_decisions")

print("  Computing Kevin Bacon numbers via BFS (may take 2-3 min on F2)...")
bfs_start = time.time()

# Check if Kevin Bacon is in the dataset
bacon_check = casting.filter(F.col("person_id") == BACON_ID).count()
if bacon_check == 0:
    print("  ⚠️  Kevin Bacon (nm0000102) not in filtered dataset — skipping bacon_number")
    print("     (This happens if Bacon's movies don't meet the 1K+ vote threshold)")
    # Still add the column with nulls so the schema is consistent.
    # Drop first so re-running this cell doesn't create a duplicate column.
    people_updated = (
        spark.sql("SELECT * FROM people")
        .drop("bacon_number")
        .withColumn("bacon_number", F.lit(None).cast("int"))
    )
    people_updated.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("people")
else:
    # Build co-star adjacency: two people share a movie
    # Start BFS from Bacon
    reached = spark.createDataFrame([(BACON_ID, 0)], ["person_id", "bacon_number"])
    all_reached = reached

    for degree in range(1, 7):
        # Find all titles the reached people are in
        reached_titles = (
            reached.select("person_id")
            .join(casting, "person_id", "inner")
            .select("title_id")
            .distinct()
        )
        # Find all people in those titles
        new_people = (
            reached_titles
            .join(casting, "title_id", "inner")
            .select("person_id")
            .distinct()
            .join(all_reached, "person_id", "left_anti")
            .withColumn("bacon_number", F.lit(degree))
            # Materialize each frontier — without this the union's lineage
            # grows per degree and every count() re-evaluates the whole plan.
            .localCheckpoint()
        )
        new_count = new_people.count()
        all_reached = all_reached.union(new_people).localCheckpoint()
        reached = new_people
        print(f"  Bacon degree {degree}: {new_count:,} new people (total: {all_reached.count():,})")
        if new_count == 0:
            break

    # Join bacon_number back to people table.
    # Drop first so re-running this cell doesn't create a duplicate column.
    people_with_bacon = (
        spark.sql("SELECT * FROM people")
        .drop("bacon_number")
        .join(all_reached.select("person_id", "bacon_number"), "person_id", "left")
    )
    people_with_bacon.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("people")
    print(f"  ✅ bacon_number added to people table [{time.time()-bfs_start:.1f}s]")

# ── Step 3: Add cast_experience to titles ──
# Average career_title_count of the top-3 billed cast per title
people_career = spark.sql("SELECT person_id, career_title_count FROM people")
top3_cast = (
    spark.sql("""
        SELECT title_id, person_id, billing_order
        FROM casting_decisions
        WHERE billing_order <= 3
    """)
    .join(people_career, "person_id", "left")
    .groupBy("title_id")
    .agg(F.round(F.avg("career_title_count"), 1).alias("cast_experience"))
)

# Drop first so re-running this cell doesn't create a duplicate column.
titles_updated = (
    spark.sql("SELECT * FROM titles")
    .drop("cast_experience")
    .join(top3_cast, "title_id", "left")
)
titles_updated.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("titles")
print(f"  ✅ cast_experience added to titles table")

# ── Step 4: Validation + graph statistics ──
print()
print("=" * 65)
print("IMDB CASTING GRAPH — SETUP COMPLETE")
print("=" * 65)
for t in ["titles", "people", "casting_decisions", "ratings", "box_office", "genres"]:
    cnt = spark.sql(f"SELECT COUNT(*) c FROM {t}").collect()[0]["c"]
    print(f"  ✅ {t:<25} {cnt:>10,} rows")

print()
print("Graph statistics:")
avg_cast = spark.sql("SELECT ROUND(CAST(COUNT(*) AS DOUBLE) / COUNT(DISTINCT title_id), 1) FROM casting_decisions").collect()[0][0]
avg_titles = spark.sql("SELECT ROUND(CAST(COUNT(*) AS DOUBLE) / COUNT(DISTINCT person_id), 1) FROM casting_decisions").collect()[0][0]
print(f"  Avg casting decisions per title:  {avg_cast}")
print(f"  Avg titles per person:            {avg_titles}")

bacon_titles = spark.sql(f"SELECT career_title_count FROM people WHERE person_id = '{BACON_ID}'").collect()
if bacon_titles:
    print(f"  Kevin Bacon's title count:        {bacon_titles[0][0]}")

bacon_reach = spark.sql("SELECT COUNT(*) FROM people WHERE bacon_number IS NOT NULL").collect()[0][0]
total_people = spark.sql("SELECT COUNT(*) FROM people").collect()[0][0]
pct = round(bacon_reach / total_people * 100, 1) if total_people > 0 else 0
print(f"  People within 6 hops of Bacon:    {bacon_reach:,} ({pct}%)")

top_count = spark.sql("SELECT COUNT(*) FROM titles WHERE title_tier = 'Top'").collect()[0][0]
bot_count = spark.sql("SELECT COUNT(*) FROM titles WHERE title_tier = 'Bottom'").collect()[0][0]
total_titles = spark.sql("SELECT COUNT(*) FROM titles").collect()[0][0]
print(f"  Titles in Top tier (>= 7.5):      {top_count:,} ({round(top_count/total_titles*100,1)}%)")
print(f"  Titles in Bottom tier (< 4.5):     {bot_count:,} ({round(bot_count/total_titles*100,1)}%)")

sleepers = spark.sql("SELECT COUNT(*) FROM box_office WHERE is_sleeper_hit = true").collect()[0][0]
flops = spark.sql("SELECT COUNT(*) FROM box_office WHERE is_flop = true").collect()[0][0]
print(f"  Sleeper hits:                     {sleepers:,}")
print(f"  Flops:                            {flops:,}")

print()
print("Sanity checks (should show genre-differentiated patterns):")
display(spark.sql("""
    SELECT t.primary_genre,
           COUNT(*) AS titles,
           ROUND(AVG(t.avg_rating), 2) AS avg_rating,
           ROUND(AVG(b.roi_pct), 1) AS avg_roi_pct,
           ROUND(AVG(b.budget) / 1000000, 1) AS avg_budget_m
    FROM titles t
    JOIN box_office b ON t.title_id = b.title_id
    WHERE t.primary_genre IS NOT NULL
    GROUP BY t.primary_genre
    HAVING COUNT(*) >= 100
    ORDER BY avg_roi_pct DESC
"""))

print()
print("Bacon number distribution:")
display(spark.sql("""
    SELECT bacon_number, COUNT(*) AS people
    FROM people
    WHERE bacon_number IS NOT NULL
    GROUP BY bacon_number
    ORDER BY bacon_number
"""))

print()
print("Next: Create a bare Semantic Model (tables + relationships, NO DAX)")
print("Then generate the Ontology. See demo/RUNBOOK.md.")

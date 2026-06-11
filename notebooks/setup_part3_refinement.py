# ============================================================
# IMDB Casting Graph — Setup Part 3: Ontology Refinement
# ============================================================
# Paste into a new Cell (run AFTER Part 1 and Part 2).
#
# WHY THIS NOTEBOOK EXISTS
# ------------------------
# Live testing of the published Ontology via the MCP `search_ontology`
# tool revealed that ANY question requiring a traversal THROUGH the
# casting_decisions edge (Person -> CastingDecision -> Title) fails with
# an internal error after ~100s, e.g.:
#   - "names of the cast of the highest-rated movie"
#   - "people who appeared in BOTH a Top-tier and a Bottom-tier title"
# Root cause: the published casting_decisions entity has NO entity key
# (entityIdParts = []), so the engine cannot index the edge and falls
# back to an unindexed/cartesian join that times out.
#
# THE FIX HAS TWO PARTS:
#   3A. STRUCTURAL (portal work — see demo/REFINEMENT.md):
#       set casting_decisions key = cast_id, verify the cast_in /
#       for_title relationships exist with cross-filter = Both,
#       re-publish, then re-run the failing prompts. This is the real fix.
#   3B. SAFETY RAILS (this notebook):
#       pre-compute graph-derived features onto the Person and Title
#       entities so the most common multi-hop questions collapse into
#       single-entity filters. These keep the demo reliable and fast even
#       on a cold capacity, and unlock new question classes.
#
# This notebook ALSO validates that cast_id is unique + non-null, which is
# a prerequisite for step 3A (you cannot set a non-unique column as a key).
#
# Expected runtime: ~30-60 seconds.
# ============================================================

from pyspark.sql import functions as F
from pyspark.sql.window import Window
import time

# ── Step 0: Validate cast_id so it can be set as the entity key ──
# A Fabric Ontology entity key must be unique and non-null. If this
# check fails, FIX IT before setting the key in the Ontology editor.
print("=" * 65)
print("STEP 0 — Validate casting_decisions.cast_id as a key candidate")
print("=" * 65)

cd = spark.sql("SELECT * FROM casting_decisions")
total_rows   = cd.count()
null_cast_id = cd.filter(F.col("cast_id").isNull()).count()
distinct_ids = cd.select("cast_id").distinct().count()
dup_rows     = total_rows - distinct_ids

print(f"  casting_decisions rows:        {total_rows:>10,}")
print(f"  null cast_id:                  {null_cast_id:>10,}")
print(f"  distinct cast_id:              {distinct_ids:>10,}")
print(f"  duplicate cast_id rows:        {dup_rows:>10,}")

if null_cast_id == 0 and dup_rows == 0:
    print("  ✅ cast_id is unique + non-null — safe to set as the entity key.")
else:
    print("  ⚠️  cast_id is NOT a valid key yet. Rebuilding a guaranteed-unique")
    print("     cast_id from (title_id, person_id, billing_order, category)...")
    cd_fixed = cd.withColumn(
        "cast_id",
        F.concat_ws(
            "_",
            F.col("title_id"),
            F.col("person_id"),
            F.coalesce(F.col("billing_order").cast("string"), F.lit("x")),
            F.coalesce(F.col("category"), F.lit("x")),
        ),
    )
    # If still not unique (true duplicate edges), disambiguate by row number.
    w = Window.partitionBy("cast_id").orderBy(F.lit(1))
    cd_fixed = (
        cd_fixed
        .withColumn("_rn", F.row_number().over(w))
        .withColumn(
            "cast_id",
            F.when(F.col("_rn") == 1, F.col("cast_id"))
             .otherwise(F.concat_ws("_", F.col("cast_id"), F.col("_rn").cast("string"))),
        )
        .drop("_rn")
    )
    cd_fixed.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("casting_decisions")
    print("  ✅ casting_decisions rewritten with a unique, non-null cast_id.")

# ── Step 1: Person-level tier-span features ──
# Collapses the failing self-intersection query
#   ("appeared in BOTH a Top-tier AND a Bottom-tier title")
# into a SINGLE-entity filter on Person:  spans_top_and_bottom = true.
#
# CORRECTNESS NOTES:
#   * Count DISTINCT titles, not casting rows — a person can have several
#     casting rows for the same title (actor + producer, multiple roles).
#   * is_lead is sourced from the edge so lead_title_count is "distinct
#     titles where this person had a lead (billing_order <= 3) role".
print()
print("=" * 65)
print("STEP 1 — Person-level tier-span features")
print("=" * 65)

# One row per (person, title) carrying that title's tier + whether the
# person had a lead role in it.
person_title = (
    spark.sql("""
        SELECT person_id, title_id,
               MAX(CASE WHEN is_lead THEN 1 ELSE 0 END) AS had_lead
        FROM casting_decisions
        GROUP BY person_id, title_id
    """)
    .join(
        spark.sql("SELECT title_id, title_tier FROM titles"),
        "title_id",
        "left",
    )
)

person_features = (
    person_title.groupBy("person_id")
    .agg(
        F.countDistinct("title_id").alias("distinct_title_count"),
        F.countDistinct(F.when(F.col("title_tier") == "Top", F.col("title_id"))).alias("top_title_count"),
        F.countDistinct(F.when(F.col("title_tier") == "Middle", F.col("title_id"))).alias("middle_title_count"),
        F.countDistinct(F.when(F.col("title_tier") == "Bottom", F.col("title_id"))).alias("bottom_title_count"),
        F.countDistinct(F.when(F.col("had_lead") == 1, F.col("title_id"))).alias("lead_title_count"),
    )
    # Explicit, NON-NULL booleans (never leave a demo filter column nullable).
    .withColumn("appeared_in_top", F.col("top_title_count") > 0)
    .withColumn("appeared_in_bottom", F.col("bottom_title_count") > 0)
    .withColumn(
        "spans_top_and_bottom",
        (F.col("top_title_count") > 0) & (F.col("bottom_title_count") > 0),
    )
)

# Drop first so re-running this cell doesn't create duplicate columns.
PERSON_FEATURE_COLS = [
    "distinct_title_count", "top_title_count", "middle_title_count",
    "bottom_title_count", "lead_title_count", "appeared_in_top",
    "appeared_in_bottom", "spans_top_and_bottom",
]
people_updated = (
    spark.sql("SELECT * FROM people")
    .drop(*PERSON_FEATURE_COLS)
    .join(person_features, "person_id", "left")
    # People with no casting rows get 0 / false, not null.
    .fillna(
        {
            "distinct_title_count": 0,
            "top_title_count": 0,
            "middle_title_count": 0,
            "bottom_title_count": 0,
            "lead_title_count": 0,
            "appeared_in_top": False,
            "appeared_in_bottom": False,
            "spans_top_and_bottom": False,
        }
    )
)
people_updated.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("people")
print("  ✅ Added: distinct_title_count, top/middle/bottom_title_count,")
print("            lead_title_count, appeared_in_top, appeared_in_bottom,")
print("            spans_top_and_bottom")

# ── Step 2: Title-level cast features ──
# So "who starred in / how many people were cast in movie X" needs no live
# traversal. NAMED COLUMNS ARE EXPLICIT about being TOP-BILLED, not the
# full cast — do not let the agent imply otherwise.
print()
print("=" * 65)
print("STEP 2 — Title-level cast features")
print("=" * 65)

acting = (
    spark.sql("""
        SELECT title_id, person_id, billing_order, is_lead
        FROM casting_decisions
        WHERE category IN ('actor', 'actress')
    """)
    .join(spark.sql("SELECT person_id, name FROM people"), "person_id", "left")
)

title_cast = acting.groupBy("title_id").agg(
    F.size(F.collect_set("person_id")).alias("cast_size"),
    F.size(F.collect_set(F.when(F.col("is_lead"), F.col("person_id")))).alias("lead_count"),
    # Top-3 billed names, ordered by billing_order, as a readable string.
    F.concat_ws(
        ", ",
        F.slice(
            F.transform(
                F.array_sort(
                    F.collect_list(F.struct(F.col("billing_order").alias("b"), F.col("name").alias("n")))
                ),
                lambda s: s["n"],
            ),
            1,
            3,
        ),
    ).alias("top_3_billed_names"),
)

# Drop first so re-running this cell doesn't create duplicate columns.
titles_updated = (
    spark.sql("SELECT * FROM titles")
    .drop("cast_size", "lead_count", "top_3_billed_names")
    .join(title_cast, "title_id", "left")
    .fillna({"cast_size": 0, "lead_count": 0})
)
titles_updated.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("titles")
print("  ✅ Added: cast_size, lead_count, top_3_billed_names (top-billed only)")

# ── Step 3: Validation report ──
# Proves the new columns are correct and reconcile with existing data.
print()
print("=" * 65)
print("STEP 3 — Validation report")
print("=" * 65)

orphan_titles = spark.sql("""
    SELECT COUNT(*) c FROM casting_decisions cd
    LEFT ANTI JOIN titles t ON cd.title_id = t.title_id
""").collect()[0]["c"]
null_tier = spark.sql("""
    SELECT COUNT(*) c FROM titles WHERE title_tier IS NULL
""").collect()[0]["c"]
print(f"  Casting rows with no matching title:  {orphan_titles:,}")
print(f"  Titles with null title_tier:          {null_tier:,}")

dist = spark.sql("""
    SELECT
      SUM(CASE WHEN appeared_in_top AND NOT appeared_in_bottom THEN 1 ELSE 0 END) AS top_only,
      SUM(CASE WHEN appeared_in_bottom AND NOT appeared_in_top THEN 1 ELSE 0 END) AS bottom_only,
      SUM(CASE WHEN spans_top_and_bottom THEN 1 ELSE 0 END) AS both,
      SUM(CASE WHEN NOT appeared_in_top AND NOT appeared_in_bottom THEN 1 ELSE 0 END) AS neither
    FROM people
""").collect()[0]
print(f"  People — Top tier only:               {dist['top_only']:,}")
print(f"  People — Bottom tier only:            {dist['bottom_only']:,}")
print(f"  People — span BOTH Top and Bottom:    {dist['both']:,}")
print(f"  People — neither:                     {dist['neither']:,}")

print()
print("  Sample people who span Top AND Bottom tiers:")
display(spark.sql("""
    SELECT name, top_title_count, bottom_title_count, distinct_title_count
    FROM people
    WHERE spans_top_and_bottom = true
    ORDER BY (top_title_count + bottom_title_count) DESC
    LIMIT 10
"""))

print()
print("  Sample title-level cast features (highest-rated titles):")
display(spark.sql("""
    SELECT primary_title, avg_rating, cast_size, lead_count, top_3_billed_names
    FROM titles
    WHERE cast_size > 0
    ORDER BY avg_rating DESC, num_votes DESC
    LIMIT 10
"""))

print()
print("=" * 65)
print("REFINEMENT DATA WRITTEN.")
print("Next: apply the STRUCTURAL fix (set cast_id as the casting_decisions")
print("entity key + verify relationships) and re-publish. See demo/REFINEMENT.md.")
print("=" * 65)

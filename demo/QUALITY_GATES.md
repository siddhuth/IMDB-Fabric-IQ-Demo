# Quality Gates — Checkpoint Review Framework

Run this prompt against any checkpoint's files before committing. Catches schema drift, GQL safety issues, relationship gaps, and demo-blocking bugs systematically.

## The prompt

Paste the following into Claude Code (or any AI assistant) along with the files you want reviewed:

```
Review these Fabric IQ demo files against 9 quality gates.
For each gate, report PASS, WARN, or FAIL with a one-line explanation.
For each FAIL, provide the specific file:line and a concrete fix.
For each WARN, explain the risk and whether it's demo-blocking.

1. SCHEMA CONSISTENCY
   Do all column names in entity descriptions / config files match
   the actual columns written by the notebook? Check every property
   name, FK reference, and computed column name against the notebook's
   .select() statements. Flag any property mentioned in a description
   that doesn't exist in the notebook output, or vice versa.

2. THRESHOLD ALIGNMENT
   Do all tier/stage/flag thresholds in descriptions match the
   notebook's when/otherwise logic? Check every computed tier cutoff:
   title_tier, career_stage, sentiment_tier, votes_tier, is_lead,
   is_sleeper_hit, is_flop, and any other pre-computed flag.

3. KEY UNIQUENESS
   Is every entity's declared key property actually unique in the
   generated data? Flag any key that could produce duplicates
   (composite keys from non-unique columns, bridge tables where one
   person has multiple roles in the same title, etc.). Trace the
   key generation logic in the notebook and verify.

4. RELATIONSHIP COMPLETENESS
   Are all join paths between entities documented in BOTH the ontology
   entity descriptions AND the semantic model relationship guide?
   Check: cross-filter directions specified for every relationship
   needing bidirectional traversal. Check: manually-added relationships
   (non-matching column names) are explicitly called out.

5. GQL SAFETY
   Are ALL conditional grouping columns pre-computed in the notebook
   and stored as concrete column values? Any column that would require
   CASE WHEN at GQL query time must be pre-materialized. List every
   pre-computed column and confirm it exists in the notebook's
   .select() output. Known GQL limitation: CASE WHEN expressions are
   not supported yet.

6. DEMO QUESTION COVERAGE
   Can every planned demo question (from TALKING_POINTS.md or the demo
   plan) be answered using ONLY the entities, properties, and
   relationships described? Trace each question through the entity
   graph and confirm the required columns and traversal paths exist.

7. NARRATIVE COHERENCE
   Do the entity descriptions tell a story that a non-technical
   audience can follow? Is the "why this matters" clear for each
   entity? Flag descriptions that read like schema documentation
   instead of business explanations. Flag redundant data across
   entities (same column on multiple tables) and verify the canonical
   source is identified.

8. FABRIC COMPATIBILITY
   Does the notebook code use Fabric-compatible patterns? Check:
   - display() instead of .show() for DataFrame output
   - Delta write with mode("overwrite") and saveAsTable
   - Lakehouse file paths use /lakehouse/default/Files/
   - No unsupported Spark features
   - Proper null handling (nullValue="\\N" for IMDB TSVs)
   - No .count() on large unfiltered raw datasets (performance)
   - Step timing with time.time() for follow-along feedback
   - Imports at top of file, not mid-cell

9. REPRODUCIBILITY
   Can someone clone the repo, follow the runbook, and have a working
   demo without debugging? Check:
   - All file references in the runbook match actual file paths
   - Artifact names are consistent across all docs (Lakehouse name,
     Semantic Model name, Ontology name, Data Agent name)
   - No implicit dependencies (all packages available in Fabric
     Spark runtime by default)
   - Re-run safety: mode("overwrite") handles repeat execution
   - Error handling for common failure modes (file already exists,
     Spark session cold start, Kevin Bacon not in filtered dataset)
```

## When to run it

- **After every checkpoint commit** — before pushing, paste the prompt + files into a review pass
- **After any sed/bulk-edit operation** — mechanical replacements create artifacts (double words, orphaned references)
- **Before the live demo** — final pass on the complete repo to catch any cross-file drift
- **When handing off to another builder** — they run the gates on the full repo to validate their starting state

## What it catches (from real bugs found in this project)

| Gate | Bug it would have caught | Where it happened |
|---|---|---|
| Schema consistency | `had_abandoned_ray_session` column name not matching after brand scrub | Streaming demo, Turn 5 |
| Threshold alignment | Flat churn rate across tiers (tier-independent account_status generation) | Streaming demo, review pass C1 |
| Key uniqueness | `cast_id = title_id + person_id` non-unique for actor-directors | IMDB demo, CP1 review C1 |
| Relationship completeness | Missing cross-filter "Both" on subscriber relationships | Streaming demo, review pass C2 |
| GQL safety | CASE WHEN error on multi-cohort comparison queries | MCP testing, live on streaming ontology |
| Demo question coverage | Bonus question referencing dropped `recommendation_slates` entity | Streaming demo, review pass H2 |
| Narrative coherence | "streaming platform platform" double-word from sed artifact | Streaming demo, brand scrub |
| Fabric compatibility | Revenue by Tier measure used SUMMARIZE (table return, not scalar) | Streaming demo, live DAX paste |
| Reproducibility | Raw `.count()` on 60M row principals table hung for 3 min | IMDB demo, CP1 review H1 |

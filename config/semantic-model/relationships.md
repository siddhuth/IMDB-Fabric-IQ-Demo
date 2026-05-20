# Semantic Model Setup — Relationships Only (No DAX)

This demo uses NO DAX measures. The Ontology + GQL handles all aggregation at query time. The Semantic Model exists only as a structural template for Ontology generation.

## Setup steps (Phase 3 in the Runbook, ~5 min)

1. From the Lakehouse ribbon → **New semantic model**
2. Name: `IMDBCastingSM`
3. Select **all 6 tables**: `titles`, `people`, `casting_decisions`, `ratings`, `box_office`, `genres`
4. Click **Confirm**
5. Open in editing mode

## Relationships to verify / create

Most will auto-detect from matching column names. Verify all 5 are present:

| # | From table | From column | To table | To column | Cardinality | Cross-filter | Auto-detect? |
|---|---|---|---|---|---|---|---|
| 1 | `casting_decisions` | `person_id` | `people` | `person_id` | many:1 | **Both** | Yes |
| 2 | `casting_decisions` | `title_id` | `titles` | `title_id` | many:1 | **Both** | Yes |
| 3 | `ratings` | `title_id` | `titles` | `title_id` | 1:1 | Both | Yes |
| 4 | `box_office` | `title_id` | `titles` | `title_id` | 1:1 | Both | Yes |
| 5 | `titles` | `primary_genre` | `genres` | `genre_id` | many:1 | Single | **No — add manually** |

## Critical: Set cross-filter direction

For relationships #1 and #2 (the casting graph edges):
1. Double-click the relationship line in the diagram
2. Change **Cross filter direction** from **Single** to **Both**
3. Click OK

Without bidirectional filtering, the Ontology won't traverse `Title → CastingDecision → Person` in reverse.

## That's it

No DAX measures. No calculated columns. No hierarchies. Save the model and proceed to Ontology generation.

The Semantic Model is a pass-through — its only job is to give the Ontology generator a clean set of tables with typed relationships. All analytical computation happens in the Ontology via GQL at query time.

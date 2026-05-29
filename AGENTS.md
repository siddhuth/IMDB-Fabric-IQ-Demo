# IMDB Fabric IQ — Agent Guide

## Role & domain

You are a movie industry analytics agent querying an IMDB casting graph ontology hosted in
Microsoft Fabric. The graph connects **People** (actors, directors) to **Titles** (movies)
through **CastingDecision** edges that carry role metadata (`billing_order`, `career_stage`,
`was_against_type`).

### Key entity relationships
- **Person → CastingDecision → Title** — the core graph path
- **Title → Rating** — audience reception (real IMDB data)
- **Title → BoxOffice** — financial performance (synthetic but correlated)
- **Title → Genre** — content category

### Pre-computed columns (use these to avoid GQL `CASE WHEN` limitations)
- `title_tier`: `Top` (>= 7.5), `Middle`, `Bottom` (< 4.5)
- `career_stage`: `Newcomer`, `Rising`, `Established`, `Veteran`
- `sentiment_tier`: `Acclaimed`, `Solid`, `Mixed`, `Panned`
- `is_lead`: `billing_order <= 3`
- `was_against_type`: person's dominant genre != title's primary genre
- `bacon_number`: shortest co-star path distance to Kevin Bacon
- `is_sleeper_hit`: budget < $30M AND ROI > 200%
- `is_flop`: budget > $50M AND ROI < -30%

### Answering style
- When answering multi-hop questions, explain which entities you're traversing.
- `GROUP BY` is supported in GQL — use it for aggregations.
- GQL does **not** support `CASE WHEN` — rely on the pre-computed tier/flag columns above
  instead of inline conditionals.

## How to query (Fabric MCP)

Use the `fabric-data-agent` MCP server's two tools:
- `list_ontology_entity_types` — schema discovery (pass `includeProperties: true` for full
  property lists).
- `search_ontology` — natural-language query; set `naturalLanguageResponse: true` for a prose
  summary alongside the raw JSON.

### Query patterns that work reliably
- Single-entity aggregations and filters: counts, `GROUP BY <column>`, averages, ordering.
- Filtering on the pre-computed tier/flag columns.

### Known limitation — casting_decisions traversal (as of 2026-05-29)
The `casting_decisions` bridge entity is currently **not reliably queryable** through the NL
ontology endpoint. In the published ontology it has an empty `entityIdParts` (no entity key)
and no defined relationships to `titles`/`people`, so the query planner cannot bind it and
silently falls back to the `titles` entity (e.g. "count casting_decisions" returns the total
title count; cast-intersection questions return a cross join of all titles).

**Implication:** multi-hop questions that must walk Person → CastingDecision → Title (for
example, "which film connects actor A and actor B, and who else was in it?") cannot be answered
from the ontology until the model is fixed. `bacon_number` still works because it is a
pre-computed property on the `people` entity.

**Fix required in the Fabric ontology model:** define `casting_decisions`'s key (`cast_id`) and
its relationships to `titles` (`title_id`) and `people` (`person_id`), then republish.
Validation test after the fix: the Meryl Streep ↔ Kevin Bacon shared-film query should return a
small set of shared titles instead of all ~42,543 titles.

**Workaround until fixed:** query the underlying Fabric Lakehouse SQL analytics endpoint
directly (`dbo.casting_decisions`, `dbo.titles`, `dbo.people`) and run real `JOIN`/`INTERSECT`
SQL.

## Operations — Fabric MCP token refresh

The `fabric-data-agent` server authenticates with an Entra (Azure AD) bearer token stored in
`~/.copilot/mcp-config.json`. The token is short-lived (~1 hour) and the Copilot CLI does **not**
hot-reload the config, so a session started with an expired token will fail to connect (it falls
back to an OAuth flow that has no cached tokens and gets marked `needs-auth`).

### To (re)connect Fabric — order matters
1. **Refresh the token first** (before launching the CLI):
   ```powershell
   pwsh -File ~/.copilot/refresh-fabric-token.ps1
   ```
   If `az` reports you are logged out, run
   `az login --tenant 89febab3-8e08-4486-899e-5e9eed258ea7` first, then re-run the script.
2. **Fully restart Copilot CLI** — quit the app completely, including the system-tray icon, then
   relaunch so the new session reads the fresh token.
3. **Verify** — ask the agent to confirm `fabric-data-agent` is loaded and that
   `fabric-data-agent-list_ontology_entity_types` and `fabric-data-agent-search_ontology` are
   available.

> Always refresh **before** launching. Launching with a stale token makes the CLI cache a
> `needs-auth` state, requiring another restart.

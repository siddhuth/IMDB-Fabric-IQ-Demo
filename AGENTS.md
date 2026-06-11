# IMDB Fabric IQ — Agent Guide

## Role & domain

You are a movie industry analytics agent querying an IMDB casting graph ontology hosted in
Microsoft Fabric.

**The canonical agent prompt lives in [`config/agent_prompt.md`](config/agent_prompt.md) —
read it first.** It is the single source of truth for the entity graph, the pre-computed
tier/flag columns and their thresholds, the GQL limitations (no `CASE WHEN`; explicit
HAVING phrasing), and the steering rules that route intersection questions to the
materialized columns. The same file is pasted into the Fabric Data Agent (RUNBOOK Phase 5)
and loaded at runtime by the Chainlit web app — do not restate its contents here or in
other docs; link to it, and make threshold/steering changes there only.

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

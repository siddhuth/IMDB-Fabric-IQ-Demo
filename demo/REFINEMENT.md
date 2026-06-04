# Ontology Refinement — Making the Graph Answer Harder Questions

This runbook captures the **Phase 3 refinement** of the IMDB Casting Graph
ontology: what the live limitations were, the fix, and how to verify it. It
also tees up the **Phase 4** Rayfin (Fabric Apps) integration as a scoped spike.

Run it after `demo/RUNBOOK.md` Phases 1–4 are complete and the ontology is
published.

---

## 1. What we measured (live, via the MCP `search_ontology` tool)

| Class | Example prompt | Result | Latency |
|---|---|---|---|
| Single-entity aggregate | "count titles by title_tier" | ✅ OK | ~10s warm / 65s cold |
| Aggregate + explicit HAVING | "...only including genres having more than 100 titles" | ✅ OK, filter applied | ~9s |
| Aggregate + vague HAVING | "genres with at least 100 titles" | ⚠️ filter silently dropped | ~10s |
| **Traversal through the edge** | "names of the cast of the highest-rated movie" | ❌ internal error | ~101s |
| **Self-intersection** | "people who appeared in both a Top-tier and a Bottom-tier title" | ❌ internal error | ~101s |

### Root cause

`list_ontology_entity_types` showed the published `casting_decisions` entity
has **`entityIdParts: []`** — no entity key was actually applied. Without a key
the engine cannot index the edge, so any traversal *through* it degrades to an
unindexed join that times out (~100s). The `entity_descriptions.md` doc *says*
`cast_id` is the key, but it was never set in the published ontology.

The HAVING drop is a separate, phrasing-sensitive NL→GQL issue, not an engine
limit — explicit phrasing fixes it.

---

## 2. The fix (two parts)

### 3A — Structural repair (the real fix; portal/editor work)

1. **Run `notebooks/setup_part3_refinement.py`** (after Parts 1 & 2). Its Step 0
   validates that `casting_decisions.cast_id` is unique + non-null and rebuilds
   it if not — a prerequisite for using it as a key.
2. In the **Ontology editor**, open `CastingDecision` and set the **entity key =
   `cast_id`**. Save.
3. Open the graph view and confirm the two core edges exist with
   **cross-filter = Both**:
   - `Person` —`cast_in`→ `CastingDecision` (1:many, `person_id`)
   - `CastingDecision` —`for_title`→ `Title` (many:1, `title_id`)
   If they are missing, add them manually (see `config/ontology/entity_descriptions.md`).
4. **Re-publish** the ontology.
5. **Re-run the failing prompts** (Section 3 below). They should now succeed.

> This step CANNOT be done from the CLI — it is Fabric portal UI work.

### 3B — Safety rails (data-level; `setup_part3_refinement.py`)

Pre-computes graph-derived features so the most common multi-hop questions
collapse into single-entity filters and stay fast even on a cold capacity:

- **Person:** `distinct_title_count`, `top_title_count`, `middle_title_count`,
  `bottom_title_count`, `lead_title_count`, `appeared_in_top`,
  `appeared_in_bottom`, `spans_top_and_bottom` (all non-null).
- **Title:** `cast_size`, `lead_count`, `top_3_billed_names` (top-billed only —
  NOT the full cast).

After running the notebook, **refresh the semantic model / re-generate the
affected entity properties and re-publish** so `search_ontology` can see the new
columns. Then update the entity Descriptions from
`config/ontology/entity_descriptions.md` (already updated to document these).

> Demo-narrative honesty: when a question is answered by a pre-computed flag,
> say "we materialized common graph-derived features onto the Person entity for
> reliability and latency, while preserving the underlying graph for
> drill-through." Don't claim a flag-answered question used live traversal.

---

## 3. Verification prompts (run after re-publish)

Structural fix (should now work, were failing before):
- "List the names of the cast of the highest-rated movie." → uses `for_title` traversal.
- "How many people appeared in both a Top-tier and a Bottom-tier title?" → can use either traversal OR `spans_top_and_bottom`.

Safety-rail / single-entity (should be fast and reliable):
- "How many people span both Top and Bottom tiers?" → Person filter `spans_top_and_bottom = true`.
- "Who are the top-billed stars of <movie>?" → Title `top_3_billed_names`.
- "What is the average ROI by primary genre, only including genres having more than 100 titles?" → explicit HAVING.

If the endpoint errors with `CapacityNotActive`, resume the capacity first:
```
az fabric capacity resume --capacity-name fskust --resource-group fabric-demo-st
```
Tokens expire ~1h — refresh the MCP server token before testing (see the session
`refresh-fabric-mcp.ps1` helper, server name `fabric-data-agent`).

---

## 4. Phase 4 — Rayfin (Fabric Apps) integration: scoped spike

**Rayfin = Fabric Apps (preview)** — a code-first Backend-as-a-Service. TS
`@entity` models → `rayfin up` deploys a managed SQL DB + GraphQL Data API +
Fabric SSO/Entra auth + static hosting into Fabric.

**Architecture (Option A — governed front door):** the Rayfin app owns app
concerns (web UI, Fabric SSO, a small persistent-state DB for saved questions /
chat history / favorites) and **delegates analytical Q&A server-side to the
ontology `search_ontology` MCP tool**. We do NOT mirror IMDB data into Rayfin's
SQL DB (its DB is app-owned/schema-from-code, not a wrapper over the Lakehouse).

**Resolve these BEFORE building UI (spike):**

1. **Auth model — the biggest risk.** Decide explicitly:
   - *User-delegated* (preserves per-user Fabric governance): requires an
     on-behalf-of / token-exchange flow to obtain a token whose audience is
     `https://api.fabric.microsoft.com` for the ontology MCP endpoint. Confirm
     Rayfin exposes the signed-in Fabric user token server-side.
   - *Service identity* (simpler): one app identity calls the ontology; every
     user sees whatever that identity can access. Must be disclosed as
     app-level access and scoped tightly.
   - Do **not** ship `InteractiveBrowserCredential`-style auth — that is
     local/dev only.
2. **Endpoint reachability** from the Rayfin server runtime to
   `api.fabric.microsoft.com`.
3. **Timeout budget.** Cold calls hit 65s and traversals can run ~100s. Set the
   backend analytical timeout **> 120s**, show progress states, and consider
   caching known demo prompts.
4. **Prereq:** tenant admin enables the "Fabric Apps (preview)" workload and the
   workspace has an assigned capacity.

Scaffold (once the spike clears): `npm create @microsoft/rayfin@latest`,
configure `rayfin.yml`, define persistent-state models in `rayfin/data/`, add a
server route that calls `search_ontology`, deploy with `npx rayfin up`.

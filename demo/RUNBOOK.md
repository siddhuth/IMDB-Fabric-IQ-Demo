# Demo Runbook — IMDB Casting Graph, Zero to Live

Setup guide for building the IMDB Casting Graph demo from a clean Fabric workspace. Designed for a 60-minute customer session with a live Data Agent + Claude-over-MCP model comparison.

**Target state:** A live Ontology answering graph questions via Data Agent AND via Claude (VS Code or the Chainlit web app) through the MCP endpoint.

---

## Phase 0 — Prep (5 min)

1. Pull this repo and open `demo/RUNBOOK.md` in a browser tab
2. Open Fabric portal: https://app.fabric.microsoft.com
3. Have VS Code installed with the MCP server support (for Phase 6)
4. Files you'll reference during setup:
   - `notebooks/setup_part1_imdb.py` → Fabric notebook cell 1
   - `notebooks/setup_part2_boxoffice_bacon.py` → Fabric notebook cell 2
   - `config/ontology/entity_descriptions.md` → Ontology editor paste source
   - `config/semantic-model/relationships.md` → Semantic Model guide
   - `config/agent_prompt.md` → Data Agent instructions paste source (Phase 5)

---

## Phase 1 — Workspace + Lakehouse (5 min)

1. Fabric portal → **Workspaces** → **+ New workspace**
2. Name: `IMDBCastingGraphIQ`
3. Assign to your Fabric capacity
4. Inside the workspace → **+ New item** → **Lakehouse**
5. Name: `IMDBCastingLH`

**Checkpoint:** Empty Lakehouse visible in workspace.

---

## Phase 2 — Data load notebook (10-15 min)

1. From the Lakehouse ribbon → **Open notebook** → **New notebook**
2. Name: `00_imdb_casting_setup`
3. Confirm `IMDBCastingLH` is attached as default Lakehouse
4. **Cell 1:** Paste entire contents of `notebooks/setup_part1_imdb.py`
5. **Cell 2:** Paste entire contents of `notebooks/setup_part2_boxoffice_bacon.py`
6. Click **Run all**

**Expected timeline:**
- Download: ~2-3 min (4 IMDB TSV files, ~500MB total compressed)
- Filter + enrich: ~1-2 min
- Write 5 base tables: ~1 min
- Synthetic BoxOffice: ~30s
- Kevin Bacon BFS: ~2-3 min (prints progress per degree)
- Validation: ~30s

**What you should see at the end:**

```
IMDB CASTING GRAPH — SETUP COMPLETE
═════════════════════════════════════════════════════════════════
  ✅ titles                       ~25,000 rows
  ✅ people                       ~80,000 rows
  ✅ casting_decisions            ~200,000 rows
  ✅ ratings                      ~25,000 rows
  ✅ box_office                   ~25,000 rows
  ✅ genres                       ~20 rows
```

Plus genre-differentiated sanity checks (Horror should show highest ROI, lowest budget) and a Bacon number distribution (most people at degree 2-3).

**If download fails:** IMDB may throttle. Wait 60s, re-run cell 1. The download skips files that already exist.

**If Kevin Bacon is missing:** His movies may not meet the 1K-vote threshold in the filtered set. The notebook handles this gracefully (adds a null `bacon_number` column). The Six Degrees hook still works via the pre-computed column — you just won't have live BFS.

**Checkpoint:** 6 tables visible in Lakehouse. Sanity checks show genre patterns.

---

## Phase 3 — Semantic Model (5 min)

**This is the fastest phase. NO DAX.**

1. From the Lakehouse ribbon → **New semantic model**
2. Name: `IMDBCastingSM`
3. Select **all 6 tables**
4. Click **Confirm**, open in editing mode
5. **Verify these auto-detected relationships:**
   - `casting_decisions.person_id → people.person_id`
   - `casting_decisions.title_id → titles.title_id`
   - `ratings.title_id → titles.title_id`
   - `box_office.title_id → titles.title_id`
6. **Manually add** (won't auto-detect — column names differ):
   - `titles.primary_genre → genres.genre_id` (many:1)
7. **Set cross-filter "Both"** on these relationships (double-click → Cross filter direction → Both):
   - `casting_decisions ↔ people`
   - `casting_decisions ↔ titles`
   - `ratings ↔ titles`
   - `box_office ↔ titles`
8. **Save**

See `config/semantic-model/relationships.md` for the full reference table.

**Checkpoint:** 6 tables, 5 relationships (4 bidirectional). Zero DAX measures.

---

## Phase 4 — Ontology (10 min)

1. In the workspace → **+ New item** → **Ontology (preview)**
2. Name: `IMDBCastingOntology`
3. Click **Generate from Semantic Model** → select `IMDBCastingSM`
4. Expected entities: Title, Person, CastingDecision, Rating, BoxOffice, Genre
5. **For all 6 entities**, paste the description from `config/ontology/entity_descriptions.md` into the **Description** field
6. **Rename relationships** to semantic names if desired:
   - `person_id_relationship` → `cast_in`
   - `title_id_relationship` (on casting_decisions) → `for_title`
   - `title_id_relationship` (on ratings) → `has_rating`
   - `title_id_relationship` (on box_office) → `has_performance`
7. Verify `Title → Genre` relationship exists (via `primary_genre → genre_id`)
8. Click **Publish**

**If generation misses entities:** Use "Generate from OneLake" and manually select tables.

**Checkpoint:** Ontology published with 6 entities. Graph view shows the star schema with CastingDecision at the center connecting Person and Title.

---

## Phase 5 — Data Agent (5 min)

1. **+ New item** → **Data Agent (preview)**
2. Name: `IMDBCastingAgent`
3. Add `IMDBCastingOntology` as data source
4. **Agent instructions** — paste the entire contents of **`config/agent_prompt.md`**.
   That file is the single source of truth for the agent prompt — the Chainlit
   web app loads the same file at runtime, so a threshold or steering change
   only ever needs to be made once.
5. **Add 3 example queries:**
   - "What's the average rating of Top-tier versus Bottom-tier movies?" → simple aggregation on title_tier
   - "How many people span both Top and Bottom rating tiers?" → single-entity filter on the pre-computed spans_top_and_bottom column
   - "What genre has the highest average ROI?" → BoxOffice → Title → Genre traversal
6. Click **Save** → wait 2 min → **Publish**

**Checkpoint:** Agent published. Chat interface visible with ontology in Explorer pane.

---

## Phase 6 — MCP endpoint + VS Code (5 min)

1. Open the Ontology in Fabric → copy the browser URL
2. Extract `<workspace-ID>` and `<ontology-item-ID>` from the URL
3. Form the MCP endpoint:
   ```
   https://api.fabric.microsoft.com/v1/mcp/dataPlane/workspaces/<workspace-ID>/items/<ontology-item-ID>/ontologyEndpoint
   ```
4. In VS Code, create `.vscode/mcp.json`:
   ```json
   {
     "servers": {
       "IMDB Casting Ontology": {
         "url": "<your MCP endpoint URL>",
         "type": "http"
       }
     },
     "inputs": []
   }
   ```
5. Open Chat (`Ctrl+Shift+I`), start the MCP server, authenticate
6. Select **Claude Sonnet** as orchestrator
7. Test: *"How many titles are in the Top tier?"*

**Checkpoint:** VS Code Chat returns data from the ontology via Claude.

---

## Phase 7 — Smoke test (5 min)

Run these 3 queries in the Data Agent to confirm the demo is ready:

1. *"How many titles are in each title_tier?"*
   - Expected: Top ~5-6K, Middle ~17-18K, Bottom ~1.5-2.5K

2. *"Which actors have the highest career_title_count and also appear in Bottom-tier movies?"*
   - Expected: Prolific actors who span the quality spectrum

3. *"What's the average ROI by primary_genre for genres with at least 100 titles?"*
   - Expected: Horror at the top, Documentary/Drama near the bottom

**If queries return empty:** Check entity descriptions are populated (Phase 4 step 5). Wait 2 min for agent initialization.

---

## Fallback plans

### Data Agent slow or unresponsive
- Open the Ontology graph view → narrate the entity model visually
- The graph with CastingDecision as the central edge is visually compelling

### MCP endpoint doesn't connect
- Show the `mcp.json` config and the endpoint URL format
- Run the demo queries in the Data Agent only (still proves Ontology value)
- Narrate the MCP story with the architecture diagram

### Everything is down
- `demo/TALKING_POINTS.md` works as a pure narrative walkthrough

---

## Time budget

| Phase | Minutes | Cumulative | Notes |
|---|---|---|---|
| 0 — Prep | 5 | 5 | Before the session |
| 1 — Workspace + Lakehouse | 5 | 10 | |
| 2 — Data load notebook | 15 | 25 | Mostly waiting on download + BFS |
| 3 — Semantic Model | 5 | 30 | Zero DAX — fastest phase |
| 4 — Ontology | 10 | 40 | Paste descriptions + publish |
| 5 — Data Agent | 5 | 45 | Instructions from `config/agent_prompt.md` |
| 6 — MCP + VS Code | 5 | 50 | |
| 7 — Smoke test | 5 | 55 | Before the customer session |

**Total build time:** ~55 min. Do this BEFORE the customer session, not during.

**The 60-min customer session itself** follows `demo/TALKING_POINTS.md` — no building, just live queries and narration.

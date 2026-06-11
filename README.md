# IMDB Casting Graph — A Microsoft Fabric IQ Ontology Demo

A reproducible reference build that turns a Microsoft Fabric Semantic Model (zero DAX) into a **Fabric IQ Ontology** and exposes it to AI models through the **Model Context Protocol (MCP)**. The same ontology answers questions from the Fabric Data Agent (GPT‑4o), from VS Code with Claude, and from a small Chainlit web app — one graph, any model, any surface.

The dataset is the public IMDB collection: ~25,000 movies, ~80,000 people, ~200,000 casting decisions, with synthetic but genre-correlated box office data and pre-computed Kevin Bacon degrees.

---

## What you can ask once it's built

- *"Which actors appeared in both critically acclaimed and panned movies?"* (multi-hop traversal)
- *"What genre has the highest average ROI? Within that genre, are sleeper hits more common with newcomer or veteran leads?"* (four-entity traversal)
- *"How many hops connect Kevin Bacon to Meryl Streep?"* (graph path)
- *"For Top‑tier movies, compare the career stage distribution of the cast versus Bottom‑tier movies."* (edge-as-entity filtering)

A scripted demo flow with five canonical questions is in [`demo/TALKING_POINTS.md`](demo/TALKING_POINTS.md).

---

## Architecture

```
 ┌──────────────────┐       ┌────────────────────┐
 │ IMDB public TSVs │  ───▶ │  Fabric Lakehouse  │      (notebooks/setup_part1_imdb.py)
 └──────────────────┘       │   (Delta tables)   │      (notebooks/setup_part2_boxoffice_bacon.py)
                            └─────────┬──────────┘
                                      │
                            ┌─────────▼──────────┐
                            │ Semantic Model     │      zero DAX, relationships only
                            │   (IMDBCastingSM)  │      (config/semantic-model/relationships.md)
                            └─────────┬──────────┘
                                      │  Generate from Semantic Model
                            ┌─────────▼──────────┐
                            │ Fabric IQ Ontology │      6 entities, semantic relationships
                            │ (IMDBCastingOntology)     (config/ontology/entity_descriptions.md)
                            └────┬───────┬───────┘
                                 │       │
                  GQL ◀──────────┘       └──────────▶ MCP endpoint
                  │                                   │
        ┌─────────▼─────────┐                ┌────────▼────────────────┐
        │ Fabric Data Agent │                │  Any MCP client         │
        │     (GPT‑4o)      │                │  • VS Code + Claude     │
        └───────────────────┘                │  • Chainlit web app     │
                                             └─────────────────────────┘
```

The agent system prompt is maintained once, in [`config/agent_prompt.md`](config/agent_prompt.md) — the Data Agent instructions are pasted from it and the Chainlit app loads it at runtime, so the entity steering and tier thresholds can never drift between surfaces.

---

## Repository layout

| Path | What's in it |
|---|---|
| `notebooks/` | Three Fabric notebook cells: IMDB ingest + filter, synthetic box office + Kevin Bacon BFS, ontology refinement features |
| `config/agent_prompt.md` | **Canonical agent system prompt** — single source of truth for all surfaces |
| `config/semantic-model/` | Relationship reference table for the Semantic Model |
| `config/ontology/` | Paste-ready entity descriptions for the Ontology editor |
| `webapp/` | Optional Chainlit chat UI: Claude (Anthropic API) + MCP (Azure App Service deployment) |
| `demo/RUNBOOK.md` | Full 7‑phase build guide, ~55 min end-to-end |
| `demo/TALKING_POINTS.md` | The 60‑min live demo script |
| `demo/REFINEMENT.md` | Ontology refinement runbook (entity key fix + materialized graph features) |
| `demo/PHASE4_RAYFIN_PLAN.md` | **Next phase:** Rayfin (Fabric Apps) governed front-door plan |
| `demo/QUALITY_GATES.md` | 9‑point checklist to validate the build before showing it |

---

## Prerequisites

You provide your own Azure / Fabric tenant — nothing in this repo references a specific tenant, workspace, or account.

**Required:**
- Microsoft Fabric capacity (F2 or larger) with the **IQ Ontology (preview)** and **Data Agent (preview)** features enabled
- Permission to create Workspaces, Lakehouses, Semantic Models, Ontologies, and Data Agents in that capacity
- A Fabric workspace assigned to that capacity
- ~500 MB of Lakehouse storage for the filtered IMDB data

**Optional (for the MCP surfaces):**
- VS Code with MCP server support (for the Claude-in-VS-Code path)
- An Anthropic API key (for the Chainlit web app)
- Azure CLI + an Azure subscription (only if deploying the Chainlit app to App Service)

**Cost note:** The build itself runs entirely in your Fabric capacity. IMDB datasets are downloaded once (~500 MB compressed). Anthropic model usage during the demo is small (typically <$1 per session).

---

## Quick start

1. **Clone this repo.**
2. **Open `demo/RUNBOOK.md`** and follow Phases 1 → 7. Total build time ~55 min; do this **before** your demo session, not during.
3. **Validate** by running the three smoke-test queries in Phase 7 of the RUNBOOK.
4. **Run the live demo** using `demo/TALKING_POINTS.md`.

If you only want to see the ontology answer questions (no MCP), Phases 1–5 are sufficient (~45 min).

---

## Configuring it for your environment

All customer-specific values are environment variables or clearly-marked placeholders. Nothing in this repo is pre-wired to a tenant.

| What you need to provide | Where it lives |
|---|---|
| Fabric workspace name (default `IMDBCastingGraphIQ`) | `demo/RUNBOOK.md` Phase 1 — rename freely |
| Lakehouse / Semantic Model / Ontology / Data Agent names | `demo/RUNBOOK.md` Phases 1–5 — rename freely |
| `MCP_ENDPOINT` | Constructed from your workspace + ontology IDs (copy them from the Ontology browser URL after Phase 4); format in `demo/RUNBOOK.md` Phase 6 |
| `ANTHROPIC_API_KEY` | Env var / App Service setting for the web app; see `webapp/.env.example` |
| `ANTHROPIC_MODEL` (optional) | Defaults to `claude-opus-4-8`; see `webapp/.env.example` |

A starter `.env.example` lives in `webapp/`. Copy it to `webapp/.env` and fill in values — `.env` is gitignored.

---

## Customizing the data

This demo is intentionally about movies because the relationships are intuitive. The pattern transfers to any domain:

- **Swap the dataset:** Replace `notebooks/setup_part1_imdb.py` with your own ingest. Keep five-ish entities and one true "edge-as-entity" table (the equivalent of `casting_decisions`).
- **Adjust the filters:** `MIN_YEAR` and `MIN_VOTES` in `setup_part1_imdb.py` control dataset size. Lower them for a richer graph (slower) or raise them for faster iteration.
- **Update the agent instructions:** `config/agent_prompt.md` is the canonical agent prompt for every surface; update entity names and pre-computed columns there to match your data.

The `demo/QUALITY_GATES.md` file documents a 9‑point review prompt you can run against any custom build to catch schema drift, threshold mismatches, GQL-safety issues, and reproducibility gaps before going live.

---

## Security and secrets

- **No real secrets are committed.** Every credential reference in this repo is a placeholder. The web app fails fast with a clear message if a required env var is missing.
- **`.env` is gitignored** in `webapp/`. Use `webapp/.env.example` as a template. A `.dockerignore` at the repo root keeps `.env` files out of Docker images.
- **Fabric auth** in `webapp/app.py` uses `DefaultAzureCredential` — it picks up a Managed Identity or service principal in Azure and falls back to Azure CLI / interactive browser sign-in for local development. See `webapp/DEPLOY.md`.
- **Anthropic API keys** should live in Azure Key Vault or App Service application settings — never in source.

If you fork this repo, run `git log -p` once over your additions to confirm you haven't accidentally captured a token.

---

## Troubleshooting

| Symptom | Likely cause | Where to look |
|---|---|---|
| Notebook download fails / hangs | IMDB throttling | Re-run cell 1 after 60s; it skips files that already downloaded |
| Kevin Bacon BFS finishes but `bacon_number` is all null | His films don't meet the `MIN_VOTES` filter | Expected; the demo still works via pre-computed column. Lower `MIN_VOTES` if you want live BFS. |
| Data Agent returns "no data found" | Empty entity descriptions in the Ontology | `RUNBOOK.md` Phase 4 step 5 — paste from `config/ontology/entity_descriptions.md` |
| MCP endpoint returns 401 | Identity has no role on the Fabric workspace | Grant **Member** role to the user (or service principal) on the workspace |
| GQL `CASE WHEN` error | The Data Agent tried to build a conditional column at query time | Known GQL limitation — the pre-computed columns (`title_tier`, `career_stage`, etc.) exist to avoid this. Make sure your prompt steers the agent toward them. |
| Chainlit app fails on Azure with gunicorn errors | Default startup command is wrong | Set the Chainlit startup command per `webapp/DEPLOY.md` |

If you hit a failure not on this list, the RUNBOOK has a per-phase **Checkpoint** and the QUALITY_GATES doc has a 9‑point review prompt that catches most cross-file inconsistencies.

---

## What's next — Rayfin (Fabric Apps) app layer

The next phase of this demo layers a **governed web app** over the ontology using **Rayfin / Fabric Apps (preview)**: Fabric SSO, per-user saved questions and chat history in a generated SQL DB, and analytical Q&A delegated to the existing ontology through a Python User Data Function. No IMDB data is duplicated — the ontology stays the single analytical source of truth.

The full reviewed plan (architecture, data models, identity decision, step-by-step runbook) is in [`demo/PHASE4_RAYFIN_PLAN.md`](demo/PHASE4_RAYFIN_PLAN.md); the decisions are locked in §9. The app will be scaffolded into a top-level `app/` folder.

---

## Attribution

- IMDB datasets are downloaded from `https://datasets.imdbws.com` and are subject to IMDB's [non-commercial licensing terms](https://developer.imdb.com/non-commercial-datasets/). This demo is for non-commercial educational use only.
- Box office and Kevin Bacon degree values are **synthetic** — computed in `notebooks/setup_part2_boxoffice_bacon.py`. They are correlated with real ratings and genres but are not sourced from any commercial provider.
- "Six Degrees of Kevin Bacon" is used as a familiar narrative hook; no affiliation is implied.

---

## Feedback

If something in the RUNBOOK didn't reproduce cleanly, open an issue with the phase number and the failure mode — the runbook is meant to work from a clean Fabric workspace with no manual workarounds.

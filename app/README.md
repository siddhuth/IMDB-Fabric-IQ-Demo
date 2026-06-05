# IMDB Casting Graph — Ask the Ontology (Rayfin / Fabric App)

A governed web front door over the **IMDB Casting Graph Fabric IQ ontology**.
Users sign in with Fabric SSO, ask the ontology questions in plain English, and
save / revisit their questions and history — all with per-user row-level
security. The ontology stays the single analytical brain; **no IMDB data is
duplicated** into this app.

> Built per `demo/PHASE4_RAYFIN_PLAN.md` (decisions §9): service identity,
> Python User Data Function, starter questions, app in this repo.

## Architecture

```text
Browser (Fabric SSO)
  ├── client.data.*        → Rayfin SQL DB   (SavedQuestion, ChatTurn; per-user RLS)
  └── client.functions.ask_ontology.invoke() → Fabric User Data Function (Python)
                                                  └── search_ontology (ontology MCP) → Lakehouse
```

The browser never holds a Fabric-audience token. The `ask_ontology` UDF holds
the credential (its own managed identity = "service identity") and brokers the
ontology call.

## Run it locally (no Fabric needed)

### Fastest: standalone static preview (no backend at all)

```bash
npm run dev:static   # vite --mode static --host  →  http://localhost:5173/
```

This sets `VITE_STATIC_DEMO=1` (see `.env.static`): auth is bypassed with a demo
user, questions are answered by the local mock (real verified answers for the
starter questions), and saved/history live in memory. The whole Q&A UI renders
and is clickable with zero Fabric setup — ideal for a quick look or a UI demo.

### Full local dev (bundled Rayfin backend)

```bash
npm install        # already done by the scaffolder
npm run test       # vitest — services covered in in-memory/mock mode
npm run build      # tsc + vite production build
```

`npm run dev` runs `rayfin up` / `rayfin env`, which require a Fabric login and a
deployed backend. The scaffold's `MockAuthService` still signs in against the
bundled local backend at `:5168`, so use `npm run dev:static` for offline UI work.

## What's wired vs. what you must do in Fabric

| Done (in this repo, compiles) | You must do (portal / deploy) |
|---|---|
| `SavedQuestion`, `ChatTurn` models + per-user RLS | Enable **Fabric Apps (preview)** (tenant admin) ✔ done |
| Typed `client.functions.ask_ontology` surface | **Publish** `rayfin/functions/ask_ontology/function_app.py` as a Fabric User Data Function named `ask_ontology` |
| Python UDF source + `requirements.txt` | Grant the UDF identity **Viewer** on the ontology workspace |
| Q&A UI: ask, thinking state, save, history, starter Qs | `npx rayfin login` → `npm run rayfin:db` → `npx rayfin up` |
| Local mock so the UI is demoable offline | Grant demo users **Run and interact** on the deployed app |

## Deploy runbook

1. **Resume capacity** `fskust` if paused; ensure the ontology endpoint is live.
2. **Publish the UDF.** Create a User Data Functions item in the ontology
   workspace; use `rayfin/functions/ask_ontology/function_app.py` +
   `requirements.txt`. Name the function `ask_ontology`. Grant its identity
   **Viewer** on the workspace. (Env vars `ONTOLOGY_MCP_ENDPOINT` /
   `ONTOLOGY_ITEM_ID` default to the current ontology — override if it changes.)
3. **Sign in:** `npx rayfin login`.
4. **Apply the DB schema:** `npm run rayfin:db` (creates `SavedQuestion`,
   `ChatTurn` with RLS).
5. **Deploy:** `npx rayfin up`. Note the app URL
   (`https://<app>-app.rayfin.windows.net/`).
6. **Grant access:** give demo users **Run and interact** on the Fabric app.
7. **Smoke test:** open the URL, sign in, click each starter question, confirm
   answers return and history/favorites persist per user.

## Demo safety

The starter questions all reference **precomputed columns** so the NL→GQL engine
never attempts the slow two-hop traversal (see `demo/REFINEMENT.md` §3.1 and
`demo/DEMO_SCRIPT.md`). Keep custom questions in the same style.

## Project structure

```text
rayfin/
  rayfin.yml                       # Fabric service config (auth + data)
  data/
    SavedQuestion.ts               # saved/favorited questions (per-user RLS)
    ChatTurn.ts                    # per-user Q&A history
    schema.ts                      # typed-client schema export
  functions/
    src/types.ts                   # ImdbFunctionsSchema (ask_ontology I/O)
    ask_ontology/
      function_app.py              # Python UDF: brokers search_ontology
      requirements.txt
src/
  pages/HomePage.tsx               # the Q&A UI
  services/
    askOntology.ts                 # invokes the UDF (or mock in local dev)
    savedQuestions.ts              # SavedQuestion CRUD
    chatTurns.ts                   # ChatTurn history
    starterQuestions.ts            # 8 live-verified questions + mock answers
    rayfinClient.ts                # typed client (data + functions generics)
    bootstrap.ts / *AuthService.ts # auth wiring (scaffolded)
```

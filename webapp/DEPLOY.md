# Azure Web App Deployment

The Chainlit app in this folder is an optional surface — a chat UI that calls Claude (Anthropic API) and the Fabric IQ Ontology MCP endpoint. The canonical demo (Data Agent + VS Code MCP) does not require this app.

## What `app.py` actually expects

| Env var | Required | Notes |
|---|---|---|
| `MCP_ENDPOINT` | yes | Ontology MCP URL — see `../README.md` |
| `ANTHROPIC_API_KEY` | yes | Anthropic API key |
| `ANTHROPIC_MODEL` | no | Defaults to `claude-opus-4-8` |
| `AGENT_PROMPT_PATH` | no | Override for the system prompt path |

**System prompt:** the canonical prompt lives at `../config/agent_prompt.md` — it is the single source of truth shared with the Data Agent instructions (RUNBOOK Phase 5). When the app runs from a repo checkout it finds the file automatically. Deployments that ship only the `webapp/` folder must copy it next to `app.py` first (the steps below do this).

**Fabric auth:** `app.py` uses `DefaultAzureCredential`, so in Azure it picks up a Managed Identity or service principal automatically; on a developer machine it falls back to Azure CLI credentials or an interactive browser sign-in. The identity must have **Member** (or higher) role on the Fabric workspace that owns the ontology.

Copy `.env.example` → `.env` and fill in values before running anything below.

## Option 1: Quick deploy (`az webapp up`)

```bash
cd webapp/

# Bundle the canonical prompt with the app (it lives outside webapp/).
# The copy is gitignored — config/agent_prompt.md stays the source of truth.
cp ../config/agent_prompt.md .

# Deploy the code
az webapp up \
  --runtime PYTHON:3.11 \
  --name imdb-casting-graph \
  --resource-group your-rg \
  --sku B1

# CRITICAL: Set startup command (Chainlit, not gunicorn).
# Without this, Azure defaults to gunicorn and the app will not start.
az webapp config set \
  --name imdb-casting-graph \
  --resource-group your-rg \
  --startup-file "chainlit run app.py --host 0.0.0.0 --port 8000"

# Tell Azure which port the container listens on
az webapp config appsettings set \
  --name imdb-casting-graph \
  --resource-group your-rg \
  --settings WEBSITES_PORT=8000

# Push the env vars from your local .env into App Service settings
az webapp config appsettings set \
  --name imdb-casting-graph \
  --resource-group your-rg \
  --settings @.env

# Grant the app's Managed Identity access to Fabric:
# enable a system-assigned identity, then give it Member role on the
# Fabric workspace that owns the ontology.
az webapp identity assign --name imdb-casting-graph --resource-group your-rg
```

## Option 2: Docker container

```bash
# Build from the REPO ROOT (the image needs config/agent_prompt.md)
docker build -t imdb-casting-graph -f webapp/Dockerfile .
docker run -p 8000:8000 --env-file webapp/.env imdb-casting-graph

# For Azure: push to ACR, deploy to App Service
az acr build --registry youracr --image imdb-casting-graph:latest -f webapp/Dockerfile .
az webapp create --name imdb-casting-graph --plan your-plan \
  --deployment-container-image-name youracr.azurecr.io/imdb-casting-graph:latest
```

## Option 3: Local testing

```bash
cd webapp/
pip install -r requirements.txt

# Either: load env from .env via your shell tool of choice
set -a; source .env; set +a

chainlit run app.py
```

Opens at http://localhost:8000. The first request triggers Fabric authentication — Azure CLI credentials if you're logged in (`az login`), otherwise an interactive browser sign-in.

## Pre-demo smoke test

Deploy at least 1 hour before the session. Verify with:
- *"How many titles are in the Top tier?"* (simple — verifies MCP connection)
- *"How many people span both Top and Bottom rating tiers?"* (verifies the pre-computed graph features)

The first request after a cold start is slow (Chainlit boot + MCP init + auth). The second request should be fast. Fabric tokens are cached and refreshed automatically before expiry.

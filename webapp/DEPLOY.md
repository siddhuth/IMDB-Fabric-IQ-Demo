# Azure Web App Deployment

The Chainlit app in this folder is an optional surface — a chat UI that calls Claude (via Databricks Model Serving) and the Fabric IQ Ontology MCP endpoint. The canonical demo (Data Agent + VS Code MCP + Databricks notebook) does not require this app.

## What `app.py` actually expects

| Env var | Required | Notes |
|---|---|---|
| `MCP_ENDPOINT` | yes | Ontology MCP URL — see `../README.md` |
| `DATABRICKS_HOST` | yes | e.g. `https://adb-xxxxx.azuredatabricks.net` |
| `DATABRICKS_TOKEN` | yes | PAT or SP token with access to the model-serving endpoint |
| `DATABRICKS_MODEL` | no | Defaults to `databricks-claude-sonnet-4` |

Fabric auth uses `InteractiveBrowserCredential` — on first run a browser tab opens for sign-in. The signed-in identity must have **Member** (or higher) role on the Fabric workspace that owns the ontology.

> **Production hardening:** Replace `InteractiveBrowserCredential` in `app.py` with `DefaultAzureCredential` (so it can pick up a Managed Identity or service principal) before deploying to a multi-user environment. The interactive flow is for local development and single-operator demos.

Copy `.env.example` → `.env` and fill in values before running anything below.

## Option 1: Quick deploy (`az webapp up`)

```bash
cd webapp/

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
```

## Option 2: Docker container

```bash
cd webapp/
docker build -t imdb-casting-graph .
docker run -p 8000:8000 --env-file .env imdb-casting-graph

# For Azure: push to ACR, deploy to App Service
az acr build --registry youracr --image imdb-casting-graph:latest .
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

Opens at http://localhost:8000. The first request triggers an interactive browser sign-in to Fabric.

## Pre-demo smoke test

Deploy at least 1 hour before the session. Verify with:
- *"How many titles are in the Top tier?"* (simple — verifies MCP connection)
- *"Which actors appeared in both Top and Bottom tier movies?"* (multi-hop — verifies graph traversal)

The first request after a cold start is slow (Chainlit boot + MCP init + browser auth). The second request should be fast.

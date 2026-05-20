# Azure Web App Deployment

## Option 1: Quick deploy (az webapp up)

```bash
cd webapp/

# Create a .env file (do NOT commit this)
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-service-principal-app-id
AZURE_CLIENT_SECRET=your-service-principal-secret
MCP_ENDPOINT=https://api.fabric.microsoft.com/v1/mcp/dataPlane/workspaces/<ws-id>/items/<ont-id>/ontologyEndpoint
EOF

# Deploy
az webapp up \
  --runtime PYTHON:3.11 \
  --name imdb-casting-graph \
  --resource-group your-rg \
  --sku B1

# CRITICAL: Set startup command (Chainlit, not gunicorn)
az webapp config set \
  --name imdb-casting-graph \
  --resource-group your-rg \
  --startup-file "chainlit run app.py --host 0.0.0.0 --port 8000"

# Set the port Azure listens on
az webapp config appsettings set \
  --name imdb-casting-graph \
  --resource-group your-rg \
  --settings WEBSITES_PORT=8000

# Set env vars on the web app
az webapp config appsettings set \
  --name imdb-casting-graph \
  --resource-group your-rg \
  --settings @.env
```

> **Without the startup command, the deployment will fail.** Azure defaults to gunicorn, which doesn't know how to start Chainlit.

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
export ANTHROPIC_API_KEY=sk-ant-...
export AZURE_TENANT_ID=...
export AZURE_CLIENT_ID=...
export AZURE_CLIENT_SECRET=...
export MCP_ENDPOINT=https://api.fabric.microsoft.com/v1/mcp/...
chainlit run app.py
```

Opens at http://localhost:8000

## Service principal setup

The web app authenticates to Fabric via a service principal (not interactive browser auth). Create one:

```bash
# Create the service principal
az ad sp create-for-rbac --name "imdb-casting-graph-sp" --role Reader

# Note the appId, password, and tenant from the output
# These become AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID

# Grant the SP access to the Fabric workspace:
# Fabric portal → Workspace → Manage access → Add → paste the SP app ID → Member role
```

The SP needs **Member** role on the Fabric workspace to query the Ontology MCP endpoint.

## For the demo

Deploy at least 1 hour before the session. Test with:
- "How many titles are in the Top tier?" (simple, verifies MCP connection)
- "Which actors appeared in both Top and Bottom tier movies?" (multi-hop, verifies graph traversal)

If the web app is slow on first request, it's the Chainlit cold start + MCP initialization. Second request should be fast.

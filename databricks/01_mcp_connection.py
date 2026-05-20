# ============================================================
# Databricks — MCP Connection to Fabric IQ Ontology
# ============================================================
# Paste into Cell 1 of a Databricks notebook.
# Connects to the IMDB Casting Ontology MCP endpoint,
# discovers available tools, and sets up the Claude agent loop.
#
# Prerequisites:
#   pip install anthropic mcp azure-identity httpx
#   Anthropic API key stored in Databricks secrets:
#     databricks secrets put-secret --scope anthropic --key api_key
# ============================================================

# %pip install anthropic mcp azure-identity httpx
# Uncomment the line above on first run, then restart the kernel.

import json
import asyncio
from azure.identity import DefaultAzureCredential
from anthropic import Anthropic

# ── Configuration ──
# Replace these with your actual IDs from the Ontology URL:
# https://app.fabric.microsoft.com/groups/<WS_ID>/ontologies/<ONT_ID>
WORKSPACE_ID = "<YOUR-WORKSPACE-ID>"
ONTOLOGY_ID = "<YOUR-ONTOLOGY-ID>"

# Recommended for production: store the Anthropic key in a Databricks secret
# scope and read it here:
#     ANTHROPIC_API_KEY = dbutils.secrets.get("anthropic", "api_key")
# For quick testing, paste directly (but never commit a real key):
ANTHROPIC_API_KEY = "<YOUR-ANTHROPIC-API-KEY>"

# Fail fast if placeholders weren't replaced — avoids a confusing 404 later.
for name, value in [
    ("WORKSPACE_ID", WORKSPACE_ID),
    ("ONTOLOGY_ID", ONTOLOGY_ID),
    ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
]:
    if value.startswith("<") and value.endswith(">"):
        raise ValueError(
            f"{name} is still a placeholder ({value!r}). "
            "Replace it with your actual value before running this cell."
        )

MCP_ENDPOINT = (
    f"https://api.fabric.microsoft.com/v1/mcp/dataPlane/"
    f"workspaces/{WORKSPACE_ID}/items/{ONTOLOGY_ID}/ontologyEndpoint"
)

MODEL = "claude-sonnet-4-6"

print(f"MCP endpoint: {MCP_ENDPOINT}")
print(f"Model: {MODEL}")

# ── Get Entra ID token for Fabric API ──
credential = DefaultAzureCredential()
token = credential.get_token("https://api.fabric.microsoft.com/.default").token
print(f"Entra ID token acquired ({len(token)} chars)")

# ── Discover MCP tools ──
# The Ontology MCP server exposes tools like search_ontology and
# list_ontology_entity_types. We discover them via the MCP protocol.
import httpx

async def discover_mcp_tools():
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        # MCP initialize handshake
        init_payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "databricks-imdb-demo", "version": "1.0"},
            },
            "id": 1,
        }
        resp = await client.post(MCP_ENDPOINT, json=init_payload, headers=headers)
        init_result = resp.json()
        print(f"  MCP initialized: {init_result.get('result', {}).get('serverInfo', {})}")

        # List available tools
        tools_payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2,
        }
        resp = await client.post(MCP_ENDPOINT, json=tools_payload, headers=headers)
        tools_result = resp.json()
        return tools_result.get("result", {}).get("tools", [])

# Run discovery
mcp_tools = asyncio.get_event_loop().run_until_complete(discover_mcp_tools())

print(f"\nDiscovered {len(mcp_tools)} MCP tools:")
for tool in mcp_tools:
    print(f"  - {tool['name']}: {tool.get('description', '')[:80]}")

# Store tools for the agent loop
MCP_TOOL_SCHEMAS = mcp_tools
print("\n✅ MCP connection ready. Run the next cell to query via Claude.")

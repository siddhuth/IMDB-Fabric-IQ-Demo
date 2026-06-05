"""
Fabric User Data Function: ask_ontology
=======================================

Server-side broker between the Rayfin app and the IMDB Casting Graph Fabric IQ
ontology. The browser never holds a Fabric-audience token; this function does
(via its own managed identity — "service identity", per
demo/PHASE4_RAYFIN_PLAN.md §9, Option A).

It receives a natural-language question, calls the ontology's `search_ontology`
MCP tool, and returns the natural-language answer plus the raw result and the
measured latency.

Publish this as a Fabric User Data Functions item in the same workspace as the
ontology, name the function `ask_ontology`, and grant the UDF's identity
**Viewer** on the ontology workspace. The Rayfin app invokes it by name via
`client.functions.ask_ontology.invoke({ question })`.

Local note: this file is the deploy-ready source. It is NOT run by `npm run dev`
— the frontend uses a local mock (src/services/askOntology.ts) until this is
published and bound.
"""

import json
import os
import re
import time

import fabric.functions as fn
import requests
from azure.identity import DefaultAzureCredential

udf = fn.UserDataFunctions()

# The ontology MCP endpoint. Override per environment with an env var; the
# default targets the published IMDBCastingOnt ontology.
WORKSPACE_ID = os.environ.get(
    "FABRIC_WORKSPACE_ID", "0eceeaf8-391b-46d3-b86e-a99ccc4f8c9a"
)
ONTOLOGY_ITEM_ID = os.environ.get(
    "ONTOLOGY_ITEM_ID", "637760d3-d883-4680-83b0-c88d5058a91b"
)
ONTOLOGY_MCP_ENDPOINT = os.environ.get(
    "ONTOLOGY_MCP_ENDPOINT",
    f"https://api.fabric.microsoft.com/v1/mcp/dataPlane/workspaces/"
    f"{WORKSPACE_ID}/items/{ONTOLOGY_ITEM_ID}/ontologyEndpoint",
)

_FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
_credential = DefaultAzureCredential()


def _fabric_token() -> str:
    """Acquire a Fabric-audience token using the function's managed identity."""
    return _credential.get_token(_FABRIC_SCOPE).token


def _parse_mcp_body(text: str) -> dict:
    """MCP responses may arrive as Server-Sent Events (`data: {...}`)."""
    match = re.search(r"data:\s*(\{.*\})", text, re.DOTALL)
    if match:
        text = match.group(1)
    return json.loads(text)


@udf.function()
def ask_ontology(question: str) -> dict:
    """Ask the IMDB Casting Graph ontology a natural-language question.

    Returns: { "answer": str, "latencyMs": int, "raw": dict | None }
    """
    if not question or not question.strip():
        raise ValueError("question must be a non-empty string")

    headers = {
        "Authorization": f"Bearer {_fabric_token()}",
        "Content-Type": "application/json",
        # The ontology endpoint may respond with SSE; accept both.
        "Accept": "application/json, text/event-stream",
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "search_ontology",
            "arguments": {
                "naturalLanguageQuery": question,
                "naturalLanguageResponse": True,
            },
        },
    }

    started = time.monotonic()
    # A degenerate query can run ~100s; keep the timeout above that ceiling.
    resp = requests.post(
        ONTOLOGY_MCP_ENDPOINT, headers=headers, json=payload, timeout=150
    )
    latency_ms = int((time.monotonic() - started) * 1000)
    resp.raise_for_status()

    body = _parse_mcp_body(resp.text)
    if "error" in body and body["error"]:
        raise RuntimeError(f"Ontology error: {body['error']}")

    content = (body.get("result") or {}).get("content") or []
    text = content[0].get("text", "") if content else resp.text

    answer = text
    raw = None
    try:
        parsed = json.loads(text)
        raw = parsed
        answer = parsed.get("naturalLanguageResponse") or text
    except (json.JSONDecodeError, TypeError):
        # Not JSON — return the text as-is.
        pass

    return {"answer": answer, "latencyMs": latency_ms, "raw": raw}

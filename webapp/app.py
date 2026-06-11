# ============================================================
# IMDB Casting Graph — Chainlit Web App
# ============================================================
# Chat interface: Claude (Anthropic API) + Fabric IQ Ontology
# MCP endpoint.
#
# Env vars required:
#   MCP_ENDPOINT        — Ontology MCP URL
#   ANTHROPIC_API_KEY   — Anthropic API key
# Optional:
#   ANTHROPIC_MODEL     — defaults to claude-opus-4-8
#   AGENT_PROMPT_PATH   — path to the system prompt; defaults to
#                         agent_prompt.md beside this file, falling
#                         back to ../config/agent_prompt.md
#
# Fabric auth: DefaultAzureCredential — picks up a Managed Identity,
# service principal, or Azure CLI login in the cloud, and falls back
# to an interactive browser sign-in for local development.
# ============================================================

import asyncio
import itertools
import json
import os
import time
from pathlib import Path

import anthropic
import chainlit as cl
import httpx
from azure.identity import DefaultAzureCredential

# ── Configuration ──

MAX_AGENT_TURNS = 10


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable {name}. "
            "Copy webapp/.env.example to webapp/.env and fill in values."
        )
    return value


def _load_system_prompt() -> str:
    """The canonical prompt lives in config/agent_prompt.md.

    Deployments that ship only the webapp/ folder copy it next to
    app.py (see DEPLOY.md); AGENT_PROMPT_PATH overrides both.
    """
    here = Path(__file__).resolve().parent
    candidates = [
        os.environ.get("AGENT_PROMPT_PATH"),
        here / "agent_prompt.md",
        here.parent / "config" / "agent_prompt.md",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate).read_text(encoding="utf-8")
    raise RuntimeError(
        "Could not find the agent prompt. Expected agent_prompt.md beside "
        "app.py or at ../config/agent_prompt.md, or set AGENT_PROMPT_PATH."
    )


MCP_ENDPOINT = _require_env("MCP_ENDPOINT")
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
SYSTEM_PROMPT = _load_system_prompt()

credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
llm_client = anthropic.AsyncAnthropic()  # reads ANTHROPIC_API_KEY
http_client = httpx.AsyncClient(timeout=120.0)

# ── Fabric token (cached; Entra tokens live ~1h) ──

_token_cache = {"token": "", "expires_on": 0.0}
_token_lock = asyncio.Lock()
_request_ids = itertools.count(1)


async def get_fabric_token() -> str:
    async with _token_lock:
        if _token_cache["expires_on"] - time.time() > 300:
            return _token_cache["token"]
        # credential.get_token is blocking network I/O — keep it off the event loop
        access = await asyncio.to_thread(
            credential.get_token, "https://api.fabric.microsoft.com/.default"
        )
        _token_cache["token"] = access.token
        _token_cache["expires_on"] = access.expires_on
        return access.token


# ── MCP client (JSON-RPC over HTTP) ──


async def mcp_call(method: str, params: dict) -> dict:
    token = await get_fabric_token()
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": next(_request_ids),
    }
    resp = await http_client.post(
        MCP_ENDPOINT,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    if resp.status_code == 401:
        raise RuntimeError(
            "Fabric returned 401 Unauthorized. The signed-in identity needs "
            "Member (or higher) role on the workspace that owns the ontology, "
            "or the token expired — restart the app to re-authenticate."
        )
    resp.raise_for_status()
    return resp.json()


async def discover_tools() -> list[dict]:
    await mcp_call(
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "imdb-casting-webapp", "version": "2.0"},
        },
    )
    result = await mcp_call("tools/list", {})
    return result.get("result", {}).get("tools", [])


async def call_tool(tool_name: str, tool_input: dict) -> dict:
    result = await mcp_call(
        "tools/call", {"name": tool_name, "arguments": tool_input}
    )
    if "error" in result:
        return {"error": result["error"]}
    return result.get("result", {})


def to_anthropic_tools(mcp_tools: list[dict]) -> list[dict]:
    """Convert MCP tool schemas to Anthropic tool format."""
    return [
        {
            "name": t["name"],
            "description": t.get("description", ""),
            "input_schema": t.get("inputSchema", {"type": "object", "properties": {}}),
        }
        for t in mcp_tools
    ]


# ── Agent loop ──


async def run_agent(question: str, tools: list[dict]) -> str:
    messages = [{"role": "user", "content": question}]

    for _ in range(MAX_AGENT_TURNS):
        response = await llm_client.messages.create(
            model=MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        tool_calls = [b for b in response.content if b.type == "tool_use"]

        if not tool_calls:
            text = "\n".join(b.text for b in response.content if b.type == "text")
            return text or "No response generated."

        # Echo the full assistant content (including thinking blocks) back
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            async with cl.Step(name=f"🔧 {tc.name}", type="tool") as step:
                step.input = json.dumps(tc.input, indent=2)
                result = await call_tool(tc.name, tc.input)
                preview = json.dumps(result, indent=2)
                step.output = preview[:500] + ("..." if len(preview) > 500 else "")

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": json.dumps(result),
                }
            )

        messages.append({"role": "user", "content": tool_results})

    return "Agent reached max turns without completing."


# ── Chainlit handlers ──


@cl.on_chat_start
async def start():
    try:
        mcp_tools = await discover_tools()
    except Exception as exc:
        await cl.Message(
            content=f"⚠️ Could not connect to the Fabric MCP endpoint:\n\n`{exc}`"
        ).send()
        return

    cl.user_session.set("tools", to_anthropic_tools(mcp_tools))
    tool_names = [t["name"] for t in mcp_tools]

    await cl.Message(
        content=(
            "## 🎬 IMDB Casting Graph Explorer\n\n"
            "Connected to the Fabric IQ Ontology via MCP. "
            f"Discovered **{len(mcp_tools)}** tools: `{'`, `'.join(tool_names)}`\n\n"
            "Ask me anything about movies, actors, casting decisions, "
            "box office performance, or Kevin Bacon.\n\n"
            "**Try these:**\n"
            "- *How many titles are in the Top tier?*\n"
            "- *How many people span both Top and Bottom rating tiers?*\n"
            "- *Who are the top-billed stars of the highest-rated movie?*\n"
            "- *What is the average ROI by primary genre, only including "
            "genres having more than 100 titles?*"
        )
    ).send()


@cl.on_message
async def main(message: cl.Message):
    tools = cl.user_session.get("tools")
    if not tools:
        await cl.Message(
            content="Not connected to the ontology — start a new chat to retry."
        ).send()
        return

    msg = cl.Message(content="")
    await msg.send()

    try:
        answer = await run_agent(message.content, tools)
    except anthropic.APIStatusError as exc:
        answer = f"⚠️ Anthropic API error ({exc.status_code}): {exc.message}"
    except (httpx.HTTPError, RuntimeError) as exc:
        answer = f"⚠️ Fabric MCP error: {exc}"

    msg.content = answer
    await msg.update()

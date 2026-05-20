# ============================================================
# IMDB Casting Graph — Chainlit Azure Web App
# ============================================================
# Chat interface: Claude (via Databricks Model Serving) +
# Fabric IQ Ontology MCP endpoint.
#
# Env vars required:
#   MCP_ENDPOINT             — Ontology MCP URL
#   DATABRICKS_HOST          — e.g. https://adb-xxxxx.azuredatabricks.net
#   DATABRICKS_TOKEN         — personal access token
#   DATABRICKS_MODEL         — e.g. databricks-claude-sonnet-4
#
# Auth: Uses interactive browser login (same as VS Code).
#       On first run, a browser window opens to sign in.
# ============================================================

import os
import json
import httpx
import chainlit as cl
from azure.identity import InteractiveBrowserCredential
from openai import AsyncOpenAI

# ── Configuration ──
MCP_ENDPOINT = os.environ["MCP_ENDPOINT"]
DATABRICKS_HOST = os.environ["DATABRICKS_HOST"]
DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]
MODEL = os.environ.get("DATABRICKS_MODEL", "databricks-claude-sonnet-4")

# Interactive browser auth — opens a browser window to sign in
# Uses the same Microsoft credentials as VS Code MCP
credential = InteractiveBrowserCredential()

# Databricks Model Serving uses the OpenAI-compatible API
llm_client = AsyncOpenAI(
    api_key=DATABRICKS_TOKEN,
    base_url=f"{DATABRICKS_HOST}/serving-endpoints",
)

SYSTEM_PROMPT = """You are an IMDB casting graph analyst querying a Microsoft Fabric IQ
Ontology via MCP. The graph connects People (actors, directors) to
Titles (movies) through CastingDecision edges.

Entity graph:
  Person --[cast_in]--> CastingDecision --[for_title]--> Title
  Title --[has_rating]--> Rating (real IMDB data)
  Title --[has_performance]--> BoxOffice (synthetic, correlated)
  Title --[in_genre]--> Genre

Pre-computed columns (use instead of conditional logic):
  title_tier: Top / Middle / Bottom
  career_stage: Newcomer / Rising / Established / Veteran
  sentiment_tier: Acclaimed / Solid / Mixed / Panned
  is_lead, was_against_type, bacon_number, is_sleeper_hit, is_flop

When answering:
1. Explain which entities you're traversing
2. If a query fails, split into simpler queries and retry
3. Cite specific numbers
4. Format results as markdown tables when comparing groups
5. Add insight beyond just the numbers"""


# ── MCP client functions ──

def get_fabric_token():
    return credential.get_token("https://api.fabric.microsoft.com/.default").token


async def mcp_call(method, params, request_id=1):
    token = get_fabric_token()
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": request_id,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            MCP_ENDPOINT,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        return resp.json()


async def discover_tools():
    await mcp_call("initialize", {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "imdb-casting-webapp", "version": "1.0"},
    }, request_id=1)
    result = await mcp_call("tools/list", {}, request_id=2)
    return result.get("result", {}).get("tools", [])


async def call_tool(tool_name, tool_input):
    result = await mcp_call("tools/call", {
        "name": tool_name,
        "arguments": tool_input,
    }, request_id=3)
    if "error" in result:
        return {"error": result["error"]}
    return result.get("result", {})


# ── Agent loop using OpenAI-compatible API with tool_use ──

MCP_TOOLS = []


def get_openai_tools():
    """Convert MCP tool schemas to OpenAI function-calling format."""
    tools = []
    for t in MCP_TOOLS:
        schema = t.get("inputSchema", {"type": "object", "properties": {}})
        tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": schema,
            },
        })
    return tools


async def run_agent(question, msg):
    tools = get_openai_tools()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for turn in range(10):
        response = await llm_client.chat.completions.create(
            model=MODEL,
            max_tokens=4096,
            messages=messages,
            tools=tools if tools else None,
        )

        choice = response.choices[0]

        # If no tool calls, return the text answer
        if not choice.message.tool_calls:
            return choice.message.content or "No response generated."

        # Process tool calls
        messages.append(choice.message)

        for tc in choice.message.tool_calls:
            tool_name = tc.function.name
            tool_input = json.loads(tc.function.arguments)

            async with cl.Step(name=f"🔧 {tool_name}", type="tool") as step:
                step.input = json.dumps(tool_input, indent=2)
                result = await call_tool(tool_name, tool_input)
                result_str = json.dumps(result, indent=2)
                step.output = result_str[:500] + ("..." if len(result_str) > 500 else "")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

    return "Agent reached max turns without completing."


# ── Chainlit handlers ──

@cl.on_chat_start
async def start():
    global MCP_TOOLS
    MCP_TOOLS = await discover_tools()
    tool_names = [t["name"] for t in MCP_TOOLS]

    await cl.Message(
        content=(
            "## 🎬 IMDB Casting Graph Explorer\n\n"
            "Connected to the Fabric IQ Ontology via MCP. "
            f"Discovered **{len(MCP_TOOLS)}** tools: `{'`, `'.join(tool_names)}`\n\n"
            "Ask me anything about movies, actors, casting decisions, "
            "box office performance, or Kevin Bacon.\n\n"
            "**Try these:**\n"
            "- *What's the average rating of Top-tier vs Bottom-tier movies?*\n"
            "- *Which actors appeared in both Top and Bottom tier movies?*\n"
            "- *What genre has the highest ROI?*\n"
            "- *How many people are within 3 hops of Kevin Bacon?*"
        )
    ).send()


@cl.on_message
async def main(message: cl.Message):
    msg = cl.Message(content="")
    await msg.send()

    answer = await run_agent(message.content, msg)
    msg.content = answer
    await msg.update()

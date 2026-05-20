# ============================================================
# Databricks — Claude Agent Loop for IMDB Graph Queries
# ============================================================
# Paste into Cell 2. Runs Claude as an agent that calls the
# Ontology MCP tools to answer graph questions.
#
# Prerequisite: Cell 1 must have run successfully
# (MCP_ENDPOINT, token, ANTHROPIC_API_KEY, MCP_TOOL_SCHEMAS,
#  and MODEL must be defined).
# ============================================================

import json
import httpx
import asyncio
from anthropic import Anthropic

client = Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an IMDB casting graph analyst querying a Microsoft Fabric IQ
Ontology via MCP tools. The graph connects People (actors, directors) to
Titles (movies) through CastingDecision edges with role metadata.

Entity graph:
  Person --[cast_in]--> CastingDecision --[for_title]--> Title
  Title --[has_rating]--> Rating
  Title --[has_performance]--> BoxOffice
  Title --[in_genre]--> Genre

Pre-computed columns (use these instead of conditional logic):
  title_tier: Top (>= 7.5) / Middle / Bottom (< 4.5)
  career_stage: Newcomer / Rising / Established / Veteran
  sentiment_tier: Acclaimed / Solid / Mixed / Panned
  is_lead: billing_order <= 3
  was_against_type: person's dominant genre != title's primary genre
  bacon_number: co-star distance to Kevin Bacon (0-6)
  is_sleeper_hit: budget < $30M AND ROI > 200%
  is_flop: budget > $50M AND ROI < -30%

When answering:
1. Explain which entities you're traversing and why
2. If a query fails (e.g. CASE WHEN error), split it into simpler queries
3. Cite specific numbers from the data
4. Note whether observations are correlation or causation"""


def convert_mcp_tools_to_anthropic(mcp_tools):
    """Convert MCP tool schemas to Anthropic tool_use format."""
    anthropic_tools = []
    for tool in mcp_tools:
        anthropic_tools.append({
            "name": tool["name"],
            "description": tool.get("description", ""),
            "input_schema": tool.get("inputSchema", {"type": "object", "properties": {}}),
        })
    return anthropic_tools


async def call_mcp_tool(tool_name, tool_input):
    """Call an MCP tool on the Ontology server and return the result."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": tool_input,
        },
        "id": 3,
    }
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        resp = await http_client.post(MCP_ENDPOINT, json=payload, headers=headers)
        result = resp.json()
        if "error" in result:
            return {"error": result["error"]}
        return result.get("result", {})


def run_agent(question, max_turns=10, verbose=True):
    """Run Claude as an agent that calls MCP tools to answer a question."""
    anthropic_tools = convert_mcp_tools_to_anthropic(MCP_TOOL_SCHEMAS)
    messages = [{"role": "user", "content": question}]

    if verbose:
        print(f"\n{'='*70}")
        print(f"QUESTION: {question}")
        print(f"{'='*70}")

    for turn in range(max_turns):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=anthropic_tools,
            messages=messages,
        )

        # Check if Claude wants to call tools
        tool_calls = [b for b in response.content if b.type == "tool_use"]

        if not tool_calls:
            # Claude is done — extract the text answer
            text_blocks = [b.text for b in response.content if b.type == "text"]
            answer = "\n".join(text_blocks)
            if verbose:
                print(f"\nANSWER:\n{answer}")
            return answer

        # Process tool calls
        tool_results = []
        for tc in tool_calls:
            if verbose:
                print(f"\n  🔧 Calling {tc.name}:")
                print(f"     Input: {json.dumps(tc.input, indent=2)[:200]}")

            result = asyncio.get_event_loop().run_until_complete(
                call_mcp_tool(tc.name, tc.input)
            )

            if verbose:
                result_str = json.dumps(result, indent=2)
                preview = result_str[:300] + "..." if len(result_str) > 300 else result_str
                print(f"     Result: {preview}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": json.dumps(result),
            })

        # Add Claude's response and tool results to the conversation
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return "Agent reached max turns without completing."


# ── Demo queries ──
# Uncomment one at a time and run the cell.

# Q1: Simple aggregation
answer = run_agent(
    "What's the average rating of Top-tier versus Bottom-tier movies, "
    "and how many titles are in each tier?"
)

# # Q2: Multi-hop graph traversal
# answer = run_agent(
#     "Which actors have appeared in both Top-tier and Bottom-tier movies? "
#     "Show me the top 5 by total number of titles."
# )

# # Q3: Edge properties (the comparison question)
# answer = run_agent(
#     "For Top-tier movies, compare the career_stage distribution of the "
#     "cast versus Bottom-tier movies. Are Top-tier casts more experienced?"
# )

# # Q4: Financial + multi-hop
# answer = run_agent(
#     "What genre has the highest average ROI? Within that genre, are "
#     "sleeper hits more common with Newcomer leads or Veteran leads?"
# )

# # Q5: Kevin Bacon connectivity
# answer = run_agent(
#     "What is the distribution of bacon_number values across all people? "
#     "What percentage of people are within 3 hops of Kevin Bacon?"
# )

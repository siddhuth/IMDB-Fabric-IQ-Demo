# Demo Talking Points — IMDB Casting Graph

Five questions to ask live during the 60-minute session. Each proves a specific Fabric IQ + MCP capability. The Kevin Bacon hook opens the session; the model comparison closes it.

---

## HOOK: Six Degrees of Kevin Bacon (0:00)

**Say to the room:** *"Quick — shout out an actor."*

**Type into Data Agent:** *"How many hops connect Kevin Bacon to [audience's actor]? What movies connect them?"*

**If the agent returns a path:**
> *"That's a multi-entity traversal — Person, CastingDecision, Title, CastingDecision, Person — executed in seconds from one sentence. In DAX, that's three nested CALCULATEs and a bridge table. In Fabric IQ, it's one question."*

**If the agent struggles with the path query:**
> Ask the simpler version: *"Which actors have appeared in a movie with Kevin Bacon?"* (1-degree, reliable)
> Then: *"What's Kevin Bacon's bacon_number distribution? How many people are within 3 hops?"*
> Narrate: *"We pre-computed these connections via BFS in the notebook. 94% of people in the database are within 3 hops of Kevin Bacon — that's the power of a connected graph."*

---

## Q1 — Base ontology works (0:10)

**Ask:** *"What's the average rating of Top-tier versus Bottom-tier movies, and how many titles are in each tier?"*

**Expected answer:**
> Top-tier (rating >= 7.5): ~5,000-6,000 titles, avg rating ~7.9
> Bottom-tier (rating < 4.5): ~1,500-2,500 titles, avg rating ~3.5
> The gap is clear and wide — the tier classification is working.

**What it proves:** The ontology's pre-computed `title_tier` column works. No CASE WHEN needed at query time.

**Narrate:** *"Notice we didn't write any DAX to get this. The ontology computed the tiers from the raw data and the agent queried them directly via GQL. Zero measures. Zero formulas."*

---

## Q2 — Multi-hop graph traversal (0:18)

**Ask:** *"Which actors have appeared in both Top-tier and Bottom-tier movies? Show me the top 5 by number of total titles."*

**Expected answer:**
> A list of prolific actors (think Nicolas Cage, Samuel L. Jackson, Bruce Willis types) who span the quality spectrum. The agent traverses Person → CastingDecision → Title → title_tier.

**What it proves:** Multi-hop graph reasoning. The agent joins across three entities to find people whose filmography spans both tiers.

**Narrate:** *"This question required the agent to traverse Person to CastingDecision to Title, filter on title_tier in both directions, and intersect the results. That's a graph pattern — not a table join. Your existing Semantic Model relationships made this possible."*

> ⚠️ **Honesty check:** if the agent answers this via the pre-computed `spans_top_and_bottom` flag instead of a live traversal (likely until the CastingDecision entity-key fix from `demo/REFINEMENT.md` is published), narrate it as a materialized graph feature — *"we pre-computed common graph-derived features for reliability and latency, while preserving the underlying graph for drill-through"* — not as a live multi-hop query.

---

## Q3 — Edge properties matter (0:28)

**Ask:** *"For Top-tier movies, compare the average billing_order and career_stage distribution of the cast versus Bottom-tier movies. Are Top-tier casts more experienced?"*

**Expected answer:**
> Top-tier movies tend to have more Established/Veteran cast members in lead positions. Bottom-tier movies have a higher proportion of Newcomers in lead roles. The was_against_type rate may also differ.

**What it proves:** The CastingDecision entity has its own properties (career_stage, is_lead, was_against_type) that the agent can filter and aggregate on. This is the "edge-as-entity" pattern that separates graph reasoning from flat joins.

**Narrate:** *"In a traditional Semantic Model, casting_decisions is just a bridge table — a many-to-many join you tolerate but never query directly. In the ontology, it's a first-class entity with its own properties. The agent just filtered on the EDGE, not just the nodes. That's what graph modeling gives you."*

---

## Q4 — Financial intelligence via synthetic data (0:38)

**Ask:** *"What genre has the highest average ROI? And within that genre, are sleeper hits more common with Newcomer leads or Veteran leads?"*

**Expected answer:**
> Horror typically shows the highest ROI (low budgets, strong returns). Within Horror, the agent traverses BoxOffice → Title → CastingDecision to check career_stage of leads in sleeper hits.

**What it proves:** Four-entity traversal (BoxOffice → Title → CastingDecision → Person career data) with a compound filter. Also demonstrates that the synthetic financial data has genre-correlated patterns worth analyzing.

**Narrate:** *"The agent just crossed four entities to answer that. BoxOffice for the ROI, Title for the genre, CastingDecision for the lead filter, and the pre-computed career_stage on the edge. One question, four hops, zero SQL."*

---

## Q5 — The model comparison (0:45)

**This is the pivot to Claude + MCP.**

**Say to the room:** *"You just watched the Data Agent answer these questions using GPT-4o and the Ontology's native GQL. Now let me show you the same graph, different model."*

**Switch to either:**
- **VS Code** with the Ontology MCP server connected (Claude as orchestrator)
- **The Chainlit web app** (`webapp/`) with Claude calling search_ontology via MCP

**Ask the same Q3** (career_stage in Top vs Bottom) — the comparison question.

**Watch for and narrate the differences:**
> *"Same ontology. Same data. Same MCP endpoint. But watch the answer — Claude [specific observation: added nuance, suggested a hypothesis, cited the traversal path, added a caveat about correlation vs causation]. That's what model choice gives you. The ontology is the truth layer. The model is the reasoning layer. MCP lets you pick your lens."*

**If the agent hits the CASE WHEN error and self-corrects:**
> *"Did you see that? It hit a GQL limitation — no CASE WHEN support yet — and adapted by splitting the query. That's agentic reasoning. A static dashboard would have just failed."*

---

## Closing (0:53)

**Say:**

> *"What you saw today was one Semantic Model — zero DAX, just tables and relationships — turned into a graph ontology in one click. That ontology answered questions from a Data Agent powered by GPT-4o, and from Claude over the same MCP endpoint. No data migration. No duplicate modeling. No new infrastructure.*
>
> *Your Semantic Models aren't a sunk cost. They're the foundation for graph-based AI. Pick one tomorrow. Generate an ontology. Ask it a question you've never been able to ask before."*

**Share the repo link.**

---

## Backup questions (if time or audience interest)

- *"What's the average budget and ROI for movies where the director also acted? (Clint Eastwood pattern)"* — Tests category filtering on CastingDecision (director + actor for same person)
- *"Show me actors whose average title rating improved by more than 2 points between their first decade and their most recent decade."* — Career trajectory via pre-computed person stats
- *"Which genre has the widest gap between critic-equivalent sentiment (sentiment_tier) and audience popularity (votes_tier)?"* — Cross-entity aggregation on Rating properties
- *"List the top 10 most connected people in the graph by bacon_number = 1 count."* — Direct graph connectivity query

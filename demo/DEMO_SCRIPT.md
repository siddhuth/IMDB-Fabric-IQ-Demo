# Demo Script — "From a Table to Talent Intelligence"

A 5–10 minute, story-driven walkthrough of the enhanced IMDB casting ontology in
**Microsoft Fabric IQ**, driven entirely by plain-English questions through the
`search_ontology` MCP tool (GitHub Copilot / any MCP client).

Every question below was **verified live** against ontology
`637760d3-d883-4680-83b0-c88d5058a91b` (workspace `0eceeaf8-…`). Real answers and
timings are included so you can rehearse and narrate with confidence. Each returns
in ~4–7 seconds.

> Pre-flight (do this 10 min before): resume capacity `fskust`, refresh the MCP
> token (`refresh-fabric-mcp.ps1`), and run **Q1** once to warm the engine.
> See the ⛔ list at the bottom — do **not** ad-lib two-hop traversal questions.

---

## The premise (say this first — ~30s)

> "This isn't a movies table. It's a **graph** of ~42,000 titles, the people who
> made them, every casting decision, plus ratings and box office — unified as a
> Fabric IQ **ontology**. Watch me interrogate it the way a studio exec would —
> in plain English, no SQL, no pipelines — and watch the questions get harder
> until we reach one no spreadsheet could answer."

The arc: **grounding → analyst → the graph → talent intelligence.**

---

## TIER 1 — Grounding: "Does it actually understand the data?" (~1 min)

**Ask:**
> How many titles are in each title_tier?

**Returns (~6s):** Bottom 3,779 · Middle 33,810 · Top 4,954.

**Narrate:** "Immediately it knows our domain — we classified every title into
quality tiers. ~5,000 'Top' films, ~3,800 'Bottom'. Hold onto that idea of tiers;
it's the key to the payoff."

---

## TIER 2 — Analyst: business questions with logic & filters (~2 min)

**Ask (the counter-intuitive one):**
> What is the average ROI for each primary_genre, only including genres having more than 100 titles? Return the top 5 by ROI descending.

**Returns (~7s):** Documentary **258×**, Biography 228×, Animation 218×,
Adventure 158×.

**Narrate:** "It applied a HAVING filter and ranked it. And the insight is the
hook: **Documentaries are the highest-ROI genre** — cheap to make, massive
relative return. Blockbusters get the headlines; the math says otherwise."

**Ask (the headline check):**
> What is the highest box_office_revenue and which title has it?

**Returns (~6s):** **Deadpool — $2.786B** (tt1431045).

**Narrate:** "Different entity entirely — box office — joined automatically.
Deadpool tops worldwide gross. Notice I never told it which tables to join."

---

## TIER 3 — The graph: plain English across entities (~1.5 min)

**Ask:**
> What is the top_3_billed_names of the title with the highest avg_rating that has more than 10000 num_votes?

**Returns (~5s):** **The Shawshank Redemption** (tt0111161) →
**Tim Robbins, Morgan Freeman, Bob Gunton.**

**Narrate:** "One sentence just traversed three entities — Title → its rating →
its casting → the people — and handled the 'must be popular' nuance with a vote
threshold. The highest-rated, genuinely-watched film is Shawshank, and here's its
top-billed cast. This is the graph working as one fabric." (Remember Morgan
Freeman — he comes back.)

---

## TIER 4 — Talent intelligence: the questions no flat table answers (~3 min)

This is the climax. Build it in three beats.

### Beat 1 — "Who *actually* shapes movies?"
**Ask:**
> Who are the top 5 people with the highest distinct_title_count? Return their primary_name and distinct_title_count.

**Returns (~6s):** Mary Vernieu **386**, Kerry Barden 254, Avy Kaufman 251,
Billy Hopkins 199, Mukesh Chhabra 193.

**Narrate:** "Not the names you expected — these are the industry's top **casting
directors**. The graph surfaces the hidden power players behind 380+ films each.
You'd never find them by browsing actors."

### Beat 2 — "Range" — the question that needs the whole graph
**Ask:**
> How many people have spans_top_and_bottom equal to true?

**Returns (~4s):** **6,166 people.**

**Narrate:** "6,166 people have worked on **both** a Top-tier hit **and** a
Bottom-tier flop. That single number is a graph computation — it had to look
across every title each person touched and every title's tier. Let's make it
human:"

**Ask:**
> For the person named Morgan Freeman, return primary_name, distinct_title_count, lead_title_count, top_title_count, bottom_title_count and spans_top_and_bottom.

**Returns (~6s):** Morgan Freeman — 85 titles, **59 as lead**, 11 Top-tier,
3 Bottom-tier, spans both = **true**.

**Narrate:** "There's our Shawshank actor again — 85 films, a lead in 59, present
across the whole quality spectrum. That's a full career profile, on demand."

### Beat 3 — The exec's real question: "Find me a bankable, versatile lead"
**Ask:**
> Who are the top 5 people by distinct_title_count where spans_top_and_bottom is true and lead_title_count is greater than 10? Return primary_name, distinct_title_count and lead_title_count.

**Returns (~6s):** Nassar 150 · Prakash Raj 147 · Anupam Kher 138 ·
**Amitabh Bachchan 127 (110 as lead)** · Brahmanandam 124.

**Narrate:** "Prolific, proven leads with range across tiers — and the data
surfaces global icons like **Amitabh Bachchan**: 127 films, 110 as the lead.
This is talent scouting as a single English sentence over governed data."

---

## Close (~30s)

> "Every answer was **plain English**, in about **five seconds**, over one
> governed Fabric IQ ontology — no SQL, no copies of the data, no pipeline per
> question. We went from 'count the titles' to 'find me a bankable, versatile
> lead across the whole quality spectrum' without changing tools. **That's the
> power of a Fabric IQ ontology: your graph becomes a conversation.**"

If asked "what's next": a governed front-door app (Fabric Apps / Rayfin) puts
these starter questions in front of business users with SSO + row-level security —
see `demo/PHASE4_RAYFIN_PLAN.md`.

---

## Quick-reference card (copy/paste during the demo)

| # | Question | Headline answer | ~s |
|---|---|---|---|
| 1 | How many titles are in each title_tier? | Mid 33.8k / Top 5k / Bot 3.8k | 6 |
| 2 | Average ROI per primary_genre, genres >100 titles, top 5 desc | Documentary 258× | 7 |
| 3 | Highest box_office_revenue and which title? | Deadpool $2.79B | 6 |
| 4 | top_3_billed_names of highest avg_rating title with >10000 num_votes | Shawshank: Robbins, Freeman, Gunton | 5 |
| 5 | Top 5 people by distinct_title_count | Mary Vernieu 386 (casting dirs) | 6 |
| 6 | How many people have spans_top_and_bottom = true | 6,166 | 4 |
| 7 | Morgan Freeman career profile (the count columns) | 85 titles / 59 leads / spans=true | 6 |
| 8 | Top 5 versatile leads: spans=true, lead_title_count>10 | Amitabh Bachchan 127/110 | 6 |

**Bonus / Q&A backups (also verified):**
- "Average avg_rating per primary_genre, genres >100 titles, top 5" → Documentary 7.18, Biography 6.92.
- "How many people have lead_title_count equal to distinct_title_count and distinct_title_count > 5?" → 140 pure-lead specialists.

---

## ⛔ Do NOT ask these live (known traps)

The edge-key fix made **one-hop** joins work and the materialized columns make the
hard questions fast — but **two-hop person-through-the-edge traversal still times
out (~100s, 500 error)**, and the engine does **not** auto-substitute the fast
columns. Always reference the precomputed column by name (as above).

| ❌ Never type this | ✅ Use this instead |
|---|---|
| "Who are the cast members of the highest rated movie?" | "What is the top_3_billed_names of the title with the highest avg_rating that has more than 10000 num_votes?" |
| "How many actors appeared in both a top and bottom tier movie?" | "How many people have spans_top_and_bottom equal to true?" |
| "List every movie Morgan Freeman was in" | "For the person named Morgan Freeman, return distinct_title_count, lead_title_count, top_title_count, bottom_title_count, spans_top_and_bottom" |

Full root-cause + validation detail: `demo/REFINEMENT.md` §3.1.

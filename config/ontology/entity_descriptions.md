# Ontology Entity Descriptions — Paste-Ready (IMDB Casting Graph)

When you create the Ontology in Fabric IQ (RUNBOOK Phase 4), each entity has a **Description** field. The Data Agent and MCP-connected models use these descriptions to reason about entities semantically. Empty descriptions cause agents to ignore entities or return "no data found."

For each entity below, copy the text block verbatim into the Description field in the Ontology editor.

---

## Title

```
A movie in the IMDB database, filtered to theatrical releases from 1970 onward with at least 1,000 audience votes. Central entity in the casting graph — all casting decisions, ratings, and box office data connect through a Title. Key properties: title_id (IMDB tconst identifier), primary_title (movie name), start_year (release year), runtime_minutes, genres_str (comma-separated genre list), avg_rating (IMDB 1-10 scale), num_votes (audience vote count), decade (computed: floor of start_year to nearest 10), title_tier (computed: Top if rating >= 7.5, Bottom if < 4.5, otherwise Middle), votes_tier (computed: Viral if >= 100K votes, Popular if >= 10K, otherwise Niche), primary_genre (first genre from the genres list), cast_experience (computed: average career_title_count of top-3 billed cast — measures how experienced the lead ensemble is). Use title_tier for bimodal "Top vs Bottom" analysis. Use cast_experience to test whether experienced casts predict better outcomes.
```

**Source table:** `titles`
**Key property:** `title_id`

---

## Person

```
An individual in the entertainment industry — actor, director, writer, producer, or other crew. Connected to Titles through CastingDecision edges. Key properties: person_id (IMDB nconst identifier), name (display name), birth_year, death_year, primary_profession (actor, director, writer, etc.), career_title_count (computed: total distinct titles in the filtered dataset), avg_title_rating (computed: average IMDB rating across all titles they appear in), first_title_year, last_title_year, career_span_years (computed: last - first), dominant_genre (computed: most frequent genre across their filmography), is_active (computed: appeared in a title from 2020 onward), bacon_number (computed: shortest path distance to Kevin Bacon through co-star connections, 0 = Bacon himself, 1 = direct co-star, null = unreachable within 6 hops). Use avg_title_rating to identify consistently high- or low-performing talent. Use bacon_number for connectivity and network analysis.
```

**Source table:** `people`
**Key property:** `person_id`

---

## CastingDecision

```
The assignment of a Person to a Title in a specific role — the primary edge in the casting graph. Each row represents one person's involvement in one movie, with metadata about the nature of that involvement. This is where graph reasoning shines: traversing CastingDecision edges lets agents answer questions like "which actors appeared in both Top-tier and Bottom-tier movies" or "do Newcomer leads correlate with higher ratings." Key properties: cast_id (unique identifier: title_id + billing_order), title_id (FK to Title), person_id (FK to Person), category (role type: actor, actress, director, writer, producer, composer, cinematographer, editor, self), billing_order (1 = top-billed, higher = less prominent), character_name (the role played, e.g. "Batman"), is_lead (computed: billing_order <= 3), career_stage (computed at time of this title: Newcomer if <= 2 years in career, Rising if 3-8, Established if 9-25, Veteran if 25+), was_against_type (computed: true if the person's dominant_genre differs from this title's primary_genre — indicates unconventional casting). Filter on is_lead for lead-role analysis. Use career_stage for experience-based segmentation. Use was_against_type to study whether unconventional casting decisions correlate with better or worse outcomes.
```

**Source table:** `casting_decisions`
**Key property:** `cast_id`

---

## Rating

```
Audience reception metrics for a Title, sourced from real IMDB ratings data. One Rating per Title (1:1 relationship). This is the canonical source for rating data — the Title entity also carries avg_rating and num_votes for convenience, but Rating is the authoritative entity for audience reception queries. Key properties: title_id (FK to Title, also the key), avg_rating (IMDB 1-10 scale, real data from IMDB audience votes), num_votes (total vote count — proxy for audience reach), sentiment_tier (computed: Acclaimed if rating >= 7.5, Solid if >= 5.5, Mixed if >= 4.0, Panned if < 4.0), votes_tier (computed: Viral if >= 100K votes, Popular if >= 10K, Niche if < 10K). Use sentiment_tier for group comparisons without triggering CASE WHEN limitations in GQL. The avg_rating and num_votes are real IMDB data — agents can cite specific ratings that the audience can verify against their own knowledge.
```

**Source table:** `ratings`
**Key property:** `title_id`

---

## BoxOffice

```
Financial performance data for a Title. SYNTHETIC data correlated with real IMDB ratings, genres, and decades — not sourced from IMDB. One BoxOffice record per Title (1:1 relationship). Key properties: title_id (FK to Title, also the key), budget (production budget in USD, correlated with genre and decade — Action/Animation have higher budgets, Horror/Documentary lower), domestic_gross (US box office), worldwide_gross (global box office), opening_weekend (first weekend domestic gross), roi_pct (computed: return on investment as percentage — (worldwide_gross - budget) / budget * 100), is_profitable (computed: roi_pct > 0), is_sleeper_hit (computed: budget < $30M AND roi_pct > 200% — low-budget surprise successes), is_flop (computed: budget > $50M AND roi_pct < -30% — high-budget failures). Genre patterns baked in: Horror has low budgets but highest avg ROI; Action has high budgets with moderate ROI; Drama has moderate budgets with lowest ROI but highest ratings. Use is_sleeper_hit and is_flop for bimodal financial analysis.
```

**Source table:** `box_office`
**Key property:** `title_id`

---

## Genre

```
A content genre category — dimension table aggregating statistics across all titles tagged with that genre. IMDB titles can have multiple genres (e.g., "Action,Drama,Thriller"); this table aggregates at the individual genre level after exploding the comma-separated lists. Key properties: genre_id (the genre name, e.g. "Action"), genre_name (display name, same as genre_id), title_count (number of titles in this genre in the filtered dataset), avg_rating (average IMDB rating across all titles in this genre). Use for genre-level benchmarking: "is this Horror movie's 6.8 rating above or below the Horror genre average?"
```

**Source table:** `genres`
**Key property:** `genre_id`

---

## Relationships to verify in the Ontology graph view

After generating the Ontology from the Semantic Model, check that these relationships are present. Add any that are missing manually:

| From | Relationship | To | Cardinality | Join key |
|---|---|---|---|---|
| **Person** | **`cast_in`** | **CastingDecision** | **1:many** | **`person_id`** |
| **CastingDecision** | **`for_title`** | **Title** | **many:1** | **`title_id`** |
| Title | `has_rating` | Rating | 1:1 | `title_id` |
| Title | `has_performance` | BoxOffice | 1:1 | `title_id` |

The bold rows are the core graph edges. The `Person → CastingDecision → Title` path is the backbone of every multi-hop query.

**Relationships that may NOT auto-detect** (different column names):
- `Title.primary_genre → Genre.genre_id` (many:1) — add manually if missing

**Relationship naming:** The Ontology auto-generator creates relationship names based on column names (e.g., `title_id_relationship`). For better agent reasoning, rename them to the semantic names listed above (`cast_in`, `for_title`, `has_rating`, `has_performance`) in the Ontology editor after generation.

**Cross-filter direction:** Set to **Both** on `Person ↔ CastingDecision` and `CastingDecision ↔ Title` so that queries can traverse the graph in both directions (e.g., "given a Title, find all People" AND "given a Person, find all Titles").

---

## Why CastingDecision is modeled as an entity, not just a relationship

In a traditional Semantic Model, `casting_decisions` would be a bridge table — a many-to-many join between People and Titles. In the Ontology, we elevate it to a full entity because it has **its own properties** that agents need to reason about:

- `is_lead` — was this a lead or supporting role?
- `career_stage` — how experienced was this person at the time?
- `was_against_type` — was this an unconventional casting choice?
- `billing_order` — how prominently was this person featured?

These edge properties enable questions like "do Newcomer leads in Top-tier movies outperform Veteran leads in Bottom-tier movies?" — a query that requires filtering on BOTH the edge (CastingDecision properties) AND the nodes (Title tier, Person experience). This is what separates graph reasoning from flat-table joins.

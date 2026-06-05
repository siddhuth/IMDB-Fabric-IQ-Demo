/**
 * The demo's starter questions — every one was verified live against the
 * ontology (see demo/DEMO_SCRIPT.md). They reference the precomputed columns by
 * name so the NL→GQL engine never attempts the slow two-hop traversal.
 *
 * `mock` is the canned answer used in local dev (no Fabric backend), so the UI
 * is fully demoable offline. In a real backend these are answered live by the
 * `ask_ontology` User Data Function.
 */
export interface StarterQuestion {
  tier: string;
  label: string;
  question: string;
  mock: string;
}

export const STARTER_QUESTIONS: StarterQuestion[] = [
  {
    tier: 'Grounding',
    label: 'Titles per quality tier',
    question: 'How many titles are in each title_tier?',
    mock: 'There are 3,779 titles in the Bottom title_tier, 33,810 in the Middle, and 4,954 in the Top title_tier.',
  },
  {
    tier: 'Analyst',
    label: 'Highest-ROI genres',
    question:
      'What is the average ROI for each primary_genre, only including genres having more than 100 titles? Return the top 5 by ROI descending.',
    mock: 'Top genres by average ROI (>100 titles): Documentary 258×, Biography 228×, Animation 218×, Adventure 158×.',
  },
  {
    tier: 'Analyst',
    label: 'Box-office king',
    question: 'What is the highest box_office_revenue and which title has it?',
    mock: 'The highest box office revenue is $2.786B, achieved by "Deadpool" (tt1431045).',
  },
  {
    tier: 'The graph',
    label: 'Cast of the best film',
    question:
      'What is the top_3_billed_names of the title with the highest avg_rating that has more than 10000 num_votes?',
    mock: 'The highest-rated title with >10,000 votes is The Shawshank Redemption (tt0111161); top billed: Tim Robbins, Morgan Freeman, Bob Gunton.',
  },
  {
    tier: 'Talent intelligence',
    label: 'Hidden power players',
    question:
      'Who are the top 5 people with the highest distinct_title_count? Return their primary_name and distinct_title_count.',
    mock: 'Most titles touched: Mary Vernieu 386, Kerry Barden 254, Avy Kaufman 251, Billy Hopkins 199, Mukesh Chhabra 193 — the industry\u2019s top casting directors.',
  },
  {
    tier: 'Talent intelligence',
    label: 'Actors with range',
    question: 'How many people have spans_top_and_bottom equal to true?',
    mock: 'There are 6,166 people who worked on both a Top-tier and a Bottom-tier title.',
  },
  {
    tier: 'Talent intelligence',
    label: 'Morgan Freeman profile',
    question:
      'For the person named Morgan Freeman, return primary_name, distinct_title_count, lead_title_count, top_title_count, bottom_title_count and spans_top_and_bottom.',
    mock: 'Morgan Freeman: 85 titles, 59 as lead, 11 Top-tier, 3 Bottom-tier, spans_top_and_bottom = true.',
  },
  {
    tier: 'Talent intelligence',
    label: 'Bankable versatile leads',
    question:
      'Who are the top 5 people by distinct_title_count where spans_top_and_bottom is true and lead_title_count is greater than 10? Return primary_name, distinct_title_count and lead_title_count.',
    mock: 'Top versatile leads: Nassar 150/26, Prakash Raj 147/56, Anupam Kher 138/42, Amitabh Bachchan 127/110, Brahmanandam 124/11 (titles/leads).',
  },
];

const MOCK_BY_QUESTION = new Map(
  STARTER_QUESTIONS.map((q) => [q.question.trim().toLowerCase(), q.mock])
);

/** Best-effort canned answer for local-dev mode. */
export function mockAnswer(question: string): string {
  const exact = MOCK_BY_QUESTION.get(question.trim().toLowerCase());
  if (exact) return exact;
  return `(local mock) Connect a Fabric backend to answer: "${question}". Tip: reference a precomputed column such as spans_top_and_bottom, distinct_title_count, lead_title_count, top_3_billed_names, or box_office_revenue.`;
}

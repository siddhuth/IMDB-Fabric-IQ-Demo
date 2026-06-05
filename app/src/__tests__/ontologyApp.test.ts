import { describe, expect, it, beforeEach, vi } from 'vitest';

vi.mock('@/services/rayfinClient', () => ({
  isLocalBackend: () => true,
  getRayfinClient: vi.fn(),
}));

import { askOntology } from '@/services/askOntology';
import {
  deleteSavedQuestion,
  getSavedQuestions,
  saveQuestion,
  toggleFavorite,
} from '@/services/savedQuestions';

describe('askOntology (local mock mode)', () => {
  it('returns a canned answer for a known starter question with a latency', async () => {
    const res = await askOntology(
      'How many people have spans_top_and_bottom equal to true?'
    );
    expect(res.answer).toContain('6,166');
    expect(res.latencyMs).toBeGreaterThanOrEqual(0);
  });

  it('falls back to a guidance message for an unknown question', async () => {
    const res = await askOntology('something totally unknown');
    expect(res.answer).toContain('local mock');
  });
});

describe('savedQuestions service (in-memory mode)', () => {
  beforeEach(async () => {
    for (const q of await getSavedQuestions()) {
      await deleteSavedQuestion(q.id);
    }
  });

  it('saves, lists, favorites, and deletes questions', async () => {
    expect(await getSavedQuestions()).toEqual([]);

    const created = await saveQuestion('top 5 genres by ROI');
    expect(created.isFavorite).toBe(false);

    let list = await getSavedQuestions();
    expect(list).toHaveLength(1);

    await toggleFavorite(created.id, true);
    list = await getSavedQuestions();
    expect(list[0]?.isFavorite).toBe(true);

    await deleteSavedQuestion(created.id);
    expect(await getSavedQuestions()).toEqual([]);
  });
});

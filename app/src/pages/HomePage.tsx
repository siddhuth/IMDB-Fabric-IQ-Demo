import { useCallback, useEffect, useRef, useState } from 'react';

import { useAuth } from '@/hooks/AuthContext';
import { askOntology } from '@/services/askOntology';
import {
  addChatTurn,
  getChatTurns,
  type ChatTurnItem,
} from '@/services/chatTurns';
import {
  deleteSavedQuestion,
  getSavedQuestions,
  saveQuestion,
  toggleFavorite,
  type SavedQuestionItem,
} from '@/services/savedQuestions';
import { STARTER_QUESTIONS } from '@/services/starterQuestions';

interface CurrentAnswer {
  question: string;
  answer: string;
  latencyMs: number;
}

export function HomePage() {
  const { signOut, user } = useAuth();
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [current, setCurrent] = useState<CurrentAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<SavedQuestionItem[]>([]);
  const [history, setHistory] = useState<ChatTurnItem[]>([]);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    const [s, h] = await Promise.all([getSavedQuestions(), getChatTurns()]);
    setSaved(s);
    setHistory(h);
  }, []);

  useEffect(() => {
    void refresh();
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [refresh]);

  const ask = useCallback(
    async (q: string) => {
      const trimmed = q.trim();
      if (!trimmed || asking) return;
      setAsking(true);
      setError(null);
      setCurrent(null);
      setElapsed(0);
      const startedAt = Date.now();
      timer.current = setInterval(
        () => setElapsed(Math.floor((Date.now() - startedAt) / 1000)),
        250
      );
      try {
        const res = await askOntology(trimmed);
        setCurrent({
          question: trimmed,
          answer: res.answer,
          latencyMs: res.latencyMs,
        });
        await addChatTurn({
          question: trimmed,
          answer: res.answer,
          latencyMs: res.latencyMs,
        });
        await refresh();
      } catch (e) {
        setError(
          e instanceof Error
            ? e.message
            : 'The ontology call failed. Try again.'
        );
      } finally {
        if (timer.current) clearInterval(timer.current);
        setAsking(false);
      }
    },
    [asking, refresh]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void ask(question);
  };

  const handleStarter = (q: string) => {
    setQuestion(q);
    void ask(q);
  };

  const handleSaveCurrent = async () => {
    if (!current) return;
    await saveQuestion(current.question);
    await refresh();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="flex items-center justify-between border-b border-gray-200 bg-white px-8 py-4">
        <div>
          <h1 className="text-lg font-bold text-gray-900">IMDB Casting Graph</h1>
          <p className="text-xs text-gray-500">
            Ask the Fabric IQ ontology in plain English
          </p>
        </div>
        <div className="flex items-center gap-4">
          {user?.email && (
            <span className="text-sm text-gray-600" title={user.email}>
              {user.email}
            </span>
          )}
          <button
            onClick={() => void signOut()}
            className="text-sm text-gray-400 transition-colors hover:text-gray-600"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="mx-auto grid max-w-5xl grid-cols-1 gap-8 px-4 py-8 lg:grid-cols-[1fr_320px]">
        <section>
          <form onSubmit={handleSubmit} className="mb-4 flex gap-3">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. How many people have spans_top_and_bottom equal to true?"
              className="flex-1 rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={!question.trim() || asking}
              className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-medium text-white shadow-sm transition-all hover:bg-blue-700 disabled:opacity-40"
            >
              {asking ? 'Asking…' : 'Ask'}
            </button>
          </form>

          <div className="mb-6">
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-400">
              Starter questions
            </h2>
            <div className="flex flex-wrap gap-2">
              {STARTER_QUESTIONS.map((q) => (
                <button
                  key={q.question}
                  onClick={() => handleStarter(q.question)}
                  disabled={asking}
                  title={q.question}
                  className="rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-700 shadow-sm transition-colors hover:border-blue-400 hover:text-blue-700 disabled:opacity-40"
                >
                  <span className="mr-1 text-gray-400">{q.tier}:</span>
                  {q.label}
                </button>
              ))}
            </div>
          </div>

          {asking && (
            <div className="rounded-2xl border border-blue-100 bg-blue-50 p-5">
              <div className="flex items-center gap-3 text-blue-700">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-300 border-t-blue-600" />
                <span className="text-sm">Thinking over the graph… {elapsed}s</span>
              </div>
              <p className="mt-2 text-xs text-blue-500">
                Cold capacity can take up to ~60s on the first question.
              </p>
            </div>
          )}

          {error && !asking && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
              {error}
            </div>
          )}

          {current && !asking && (
            <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <p className="mb-1 text-xs font-medium text-gray-400">
                {current.question}
              </p>
              <p className="text-sm leading-relaxed text-gray-900">
                {current.answer}
              </p>
              <div className="mt-4 flex items-center justify-between">
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                  {(current.latencyMs / 1000).toFixed(1)}s
                </span>
                <button
                  onClick={() => void handleSaveCurrent()}
                  className="text-xs font-medium text-blue-600 hover:text-blue-800"
                >
                  ☆ Save question
                </button>
              </div>
            </div>
          )}
        </section>

        <aside className="space-y-8">
          <div>
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
              Saved ({saved.length})
            </h2>
            {saved.length === 0 ? (
              <p className="text-xs text-gray-400">
                Save a question to pin it here.
              </p>
            ) : (
              <ul className="space-y-2">
                {saved.map((s) => (
                  <li
                    key={s.id}
                    className="group flex items-start gap-2 rounded-xl border border-gray-100 bg-white px-3 py-2 shadow-sm"
                  >
                    <button
                      onClick={() =>
                        void toggleFavorite(s.id, !s.isFavorite).then(refresh)
                      }
                      className={
                        s.isFavorite
                          ? 'text-yellow-500'
                          : 'text-gray-300 hover:text-yellow-400'
                      }
                      aria-label="Toggle favorite"
                    >
                      {s.isFavorite ? '★' : '☆'}
                    </button>
                    <button
                      onClick={() => handleStarter(s.question)}
                      className="flex-1 text-left text-xs text-gray-700 hover:text-blue-700"
                    >
                      {s.question}
                    </button>
                    <button
                      onClick={() =>
                        void deleteSavedQuestion(s.id).then(refresh)
                      }
                      className="text-gray-300 opacity-0 transition-opacity hover:text-red-500 group-hover:opacity-100"
                      aria-label="Delete"
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
              History ({history.length})
            </h2>
            {history.length === 0 ? (
              <p className="text-xs text-gray-400">No questions asked yet.</p>
            ) : (
              <ul className="space-y-2">
                {history.slice(0, 12).map((h) => (
                  <li
                    key={h.id}
                    className="rounded-xl border border-gray-100 bg-white px-3 py-2 shadow-sm"
                  >
                    <button
                      onClick={() => handleStarter(h.question)}
                      className="block w-full text-left text-xs font-medium text-gray-700 hover:text-blue-700"
                    >
                      {h.question}
                    </button>
                    <p className="mt-1 line-clamp-2 text-xs text-gray-500">
                      {h.answer}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>
      </main>
    </div>
  );
}

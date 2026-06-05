import { getRayfinClient, isLocalBackend } from './rayfinClient';
import { mockAnswer } from './starterQuestions';

export interface AskResult {
  answer: string;
  latencyMs: number;
  raw?: unknown;
}

/**
 * Ask the IMDB Casting Graph ontology a question.
 *
 * - Local dev (no Fabric backend): returns a canned answer after a short delay
 *   so the UI is fully demoable offline.
 * - Real backend: invokes the `ask_ontology` Fabric User Data Function, which
 *   brokers the call to the ontology's `search_ontology` MCP tool.
 */
export async function askOntology(question: string): Promise<AskResult> {
  const started = performance.now();

  if (isLocalBackend()) {
    await new Promise((r) => setTimeout(r, 600));
    return {
      answer: mockAnswer(question),
      latencyMs: Math.round(performance.now() - started),
    };
  }

  const client = getRayfinClient();
  const out = await client.functions.ask_ontology.invoke({ question });
  return {
    answer: out.answer,
    latencyMs: out.latencyMs ?? Math.round(performance.now() - started),
    raw: out.raw,
  };
}

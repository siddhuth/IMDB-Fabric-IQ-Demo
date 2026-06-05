/** Input accepted by the `ask_ontology` User Data Function. */
export type AskOntologyInput = {
  /** A natural-language question, ideally phrased to reference precomputed columns. */
  question: string;
};

/** Output returned by the `ask_ontology` User Data Function. */
export interface AskOntologyOutput {
  /** The natural-language answer from the ontology's `search_ontology` tool. */
  answer: string;
  /** Server-measured round-trip to the ontology, in milliseconds. */
  latencyMs: number;
  /** The raw structured result (fields + rows), for optional drill-through. */
  raw?: unknown;
}

/**
 * The set of server-side functions this app can invoke via
 * `client.functions.<name>.invoke(...)`. The key MUST match the deployed
 * Fabric User Data Function name (`ask_ontology`).
 */
export type ImdbFunctionsSchema = {
  ask_ontology: { input: AskOntologyInput; output: AskOntologyOutput };
};

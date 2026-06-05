import { entity, role, text, int, date, uuid } from '@microsoft/rayfin-core';

/**
 * One question/answer exchange, persisted per user for history. The `answer`
 * is whatever the `ask_ontology` User Data Function returned; `latencyMs`
 * powers the "watch it think" UX. Per-user row-level security as above.
 */
@entity()
@role('authenticated', '*', {
  policy: (claims, item) => claims.sub.eq(item.user_id),
})
export class ChatTurn {
  @uuid() id!: string;
  @text({ min: 1, max: 500 }) question!: string;
  @text() answer!: string;
  @int() latencyMs!: number;
  @date() createdAt!: Date;
  @text() user_id!: string;
}

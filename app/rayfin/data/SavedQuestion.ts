import { entity, role, text, boolean, date, uuid } from '@microsoft/rayfin-core';

/**
 * A question a user chose to keep or favorite. App state only — no IMDB data
 * lives here. Per-user row-level security: a signed-in user can only see and
 * mutate their own rows (`user_id === claims.sub`).
 */
@entity()
@role('authenticated', '*', {
  policy: (claims, item) => claims.sub.eq(item.user_id),
})
export class SavedQuestion {
  @uuid() id!: string;
  @text({ min: 1, max: 500 }) question!: string;
  @boolean() isFavorite!: boolean;
  @date() createdAt!: Date;
  @text() user_id!: string;
}

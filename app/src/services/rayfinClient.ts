import { RayfinClient } from '@microsoft/rayfin-client';

import type { ImdbAppSchema } from '../../rayfin/data/schema';
import type { ImdbFunctionsSchema } from '../../rayfin/functions/src/types';

export interface RayfinClientConfig {
  baseUrl: string;
  publishableKey: string;
  /** True when the API URL points at localhost. Exposed via {@link isLocalBackend}. */
  localDev: boolean;
}

type AppClient = RayfinClient<ImdbAppSchema, ImdbFunctionsSchema>;

let client: AppClient | null = null;
let localDev = false;

export function initRayfinClient(config: RayfinClientConfig): AppClient {
  if (client) {
    throw new Error('Rayfin client is already initialized.');
  }
  client = new RayfinClient<ImdbAppSchema, ImdbFunctionsSchema>({
    baseUrl: config.baseUrl,
    publishableKey: config.publishableKey,
    useProxy: false,
    authStorage: true,
  });
  localDev = config.localDev;
  return client;
}

export function getRayfinClient(): AppClient {
  if (!client) {
    throw new Error(
      'Rayfin client not initialized. Call bootstrapAuth() first.'
    );
  }
  return client;
}

/** True when the app was bootstrapped against a localhost backend. */
export function isLocalBackend(): boolean {
  return localDev;
}

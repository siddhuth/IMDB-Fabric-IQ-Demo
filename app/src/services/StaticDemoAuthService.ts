import { type AuthUser, type IAuthService } from './IAuthService';

/**
 * Fully offline auth service for a standalone static preview. No backend, no
 * Fabric — returns a fixed demo user so the entire Q&A UI renders and is usable
 * (questions answered by the local mock; saved/history kept in memory).
 *
 * Selected by `bootstrapAuth()` when `VITE_STATIC_DEMO === '1'`. Never used in
 * a real deployment.
 */
export class StaticDemoAuthService implements IAuthService {
  readonly fabricAuthEnabled = false;

  private readonly demoUser: AuthUser = {
    id: 'demo-user',
    email: 'demo@contoso.com',
    name: 'Demo User',
  };

  async signIn(): Promise<AuthUser> {
    return this.demoUser;
  }

  async signOut(): Promise<void> {
    // No-op: the static preview is always "signed in".
  }

  async getCurrentUser(): Promise<AuthUser | null> {
    return this.demoUser;
  }

  async initEmbeddedAuth(): Promise<AuthUser | null> {
    return null;
  }
}

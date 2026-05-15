// auth.service.ts
// Placeholder auth service — wire this up to your real provider. Stays here
// (not in lib/) because the contract is auth-feature-specific.

import type { AuthSession } from '../types/auth.types';

export async function signIn(_email: string, _password: string): Promise<AuthSession> {
  throw new Error('signIn() is a stub — wire your auth provider here.');
}

export async function signOut(): Promise<void> {
  // No-op placeholder.
}

// auth.types.ts
// Types local to the auth feature. Shape these to match the provider you
// pick (Cognito, Auth0, Clerk, plain JWT, etc.).

export interface AuthUser {
  id: string;
  email: string;
  displayName?: string;
}

export interface AuthSession {
  user: AuthUser;
  token: string;
  expiresAt: string;
}

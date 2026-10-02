// SignInForm.tsx
// Placeholder sign-in component. Bare HTML — replace with your design
// system's form components.
//
// The submit handler must always call preventDefault(): a form the browser
// submits natively defaults to GET, which puts the email and password in the
// URL (history, server logs, Referer). method="post" is a second guard in
// case the handler is ever removed.

import { useState, type JSX } from 'react';

import { signIn } from '../services/auth.service';

export function SignInForm(): JSX.Element {
  const [error, setError] = useState<string | null>(null);

  function submit(form: HTMLFormElement): void {
    const data = new FormData(form);
    setError(null);
    signIn(String(data.get('email') ?? ''), String(data.get('password') ?? '')).catch(
      (err: unknown) => setError(err instanceof Error ? err.message : 'Sign-in failed'),
    );
  }

  return (
    <form
      method="post"
      onSubmit={(event) => {
        event.preventDefault();
        submit(event.currentTarget);
      }}
    >
      <label>
        Email
        <input type="email" name="email" autoComplete="username" required />
      </label>
      <label>
        Password
        <input type="password" name="password" autoComplete="current-password" required />
      </label>
      <button type="submit">Sign in</button>
      {error && <p role="alert">{error}</p>}
    </form>
  );
}

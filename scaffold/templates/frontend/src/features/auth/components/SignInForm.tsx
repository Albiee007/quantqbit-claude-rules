// SignInForm.tsx
// Placeholder sign-in component. Bare HTML — replace with your design
// system's form components.

export function SignInForm(): JSX.Element {
  return (
    <form>
      <label>
        Email
        <input type="email" name="email" />
      </label>
      <label>
        Password
        <input type="password" name="password" />
      </label>
      <button type="submit">Sign in</button>
    </form>
  );
}

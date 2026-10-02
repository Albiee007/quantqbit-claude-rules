// SignInForm.test.tsx
// Guards the sign-in placeholder against native form submission, which would
// put the credentials in the URL. Stamped only with --with-auth.

import { describe, it, expect } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { SignInForm } from '../../features/auth/components/SignInForm';

describe('SignInForm', () => {
  it('never submits natively and never puts credentials in the URL', async () => {
    const { container } = render(<SignInForm />);
    const form = container.querySelector('form');
    if (!form) throw new Error('form not rendered');

    expect(form.getAttribute('method')).toBe('post');
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'a@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'hunter2' } });

    // fireEvent returns false when the handler called preventDefault().
    expect(fireEvent.submit(form)).toBe(false);
    expect(await screen.findByRole('alert')).toHaveTextContent('stub');
    expect(window.location.href).not.toContain('hunter2');
  });
});

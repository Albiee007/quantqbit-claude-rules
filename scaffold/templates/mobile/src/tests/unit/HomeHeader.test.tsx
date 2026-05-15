// src/tests/unit/HomeHeader.test.tsx
// Smoke test for the HomeHeader component. Verifies the title prop renders.
// Kept intentionally tiny — it's the canary that proves jest-expo +
// @testing-library/react-native are wired correctly.

import React from 'react';
import { render, screen } from '@testing-library/react-native';
import { HomeHeader } from '../../screens/home/components/HomeHeader';

describe('HomeHeader', () => {
  it('renders the title', () => {
    render(<HomeHeader title="Hello" />);
    expect(screen.getByText('Hello')).toBeTruthy();
  });
});

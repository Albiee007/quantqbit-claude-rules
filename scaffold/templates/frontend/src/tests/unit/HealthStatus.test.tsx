// HealthStatus.test.tsx
// Smoke test for the example health feature. Mocks fetch so the component
// renders the OK branch without a live backend. Kept tiny on purpose — see
// the feature README; do NOT grow this into a network-integration suite.

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { HealthStatus } from '../../features/health/components/HealthStatus';

function renderWithProviders(): void {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <HealthStatus />
    </QueryClientProvider>,
  );
}

describe('HealthStatus', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        statusText: 'OK',
        json: async () => ({ status: 'ok' }),
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders OK once the health query resolves', async () => {
    renderWithProviders();
    expect(screen.getByTestId('health-status')).toHaveTextContent('Loading…');

    await waitFor(() => {
      expect(screen.getByTestId('health-status')).toHaveTextContent('OK');
    });
  });
});

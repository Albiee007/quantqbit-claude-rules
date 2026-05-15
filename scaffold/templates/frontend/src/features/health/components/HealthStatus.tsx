// HealthStatus.tsx
// Tiny example component — renders Loading / OK / Error based on the
// /healthz query. Intentionally minimal: zero external dependencies beyond
// the configured API base URL. Do NOT grow this into an auth/DB demo.

import { useHealth } from '../hooks/useHealth';

export function HealthStatus(): JSX.Element {
  const { data, isLoading, isError } = useHealth();

  if (isLoading) {
    return <p data-testid="health-status">Loading…</p>;
  }

  if (isError) {
    return <p data-testid="health-status">Error</p>;
  }

  return <p data-testid="health-status">OK{data?.status ? ` (${data.status})` : ''}</p>;
}

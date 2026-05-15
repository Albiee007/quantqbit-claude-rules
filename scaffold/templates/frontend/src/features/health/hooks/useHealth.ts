// useHealth.ts
// React Query hook for the health feature. Wraps the service call so any
// component (HealthStatus, a status badge, …) can subscribe without
// duplicating query keys or stale-time configuration.

import { useQuery } from '@tanstack/react-query';

import { fetchHealth } from '../services/health.service';
import type { HealthResponse } from '../types/health.types';

export function useHealth() {
  return useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: fetchHealth,
  });
}

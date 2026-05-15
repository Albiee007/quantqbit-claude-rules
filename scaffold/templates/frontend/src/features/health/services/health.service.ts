// health.service.ts
// Network call for the health feature. Lives in services/ so the component
// + hook don't reach into fetch directly. Returns the validated response.

import { apiFetch } from '../../../lib/api-client';
import type { HealthResponse } from '../types/health.types';

export async function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/healthz');
}

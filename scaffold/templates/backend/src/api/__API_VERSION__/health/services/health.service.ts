// health.service.ts
// Health-feature business logic. Intentionally tiny — no DB, no external
// calls, no auth. Read the feature's README before adding anything here.

import type { HealthResponse } from '../types/health.types';

export function fetchHealth(): HealthResponse {
  return {
    status: 'ok',
    uptime: process.uptime(),
  };
}

// health.types.ts
// Types local to the health feature. If a type ends up needed across two or
// more features, promote it to src/types/shared.ts.

export interface HealthResponse {
  status: string;
  uptimeSec?: number;
  timestamp?: string;
}

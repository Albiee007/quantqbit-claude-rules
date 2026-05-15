// health.controller.ts
// Controller for the health feature. Thin — parses nothing, calls the
// service, returns JSON.

import type { Request, Response } from 'express';
import { fetchHealth } from '../services/health.service';

export function getHealth(_req: Request, res: Response): void {
  const result = fetchHealth();
  res.status(200).json(result);
}

// src/middlewares/requestId.ts
// Assigns a unique request id (uuid v4) to every incoming request and surfaces
// it on `req.id` plus the `X-Request-Id` response header. Honours an incoming
// `X-Request-Id` header when present (chained through gateways / proxies).

import type { Request, Response, NextFunction } from 'express';
import { randomUUID } from 'node:crypto';

export function requestId(req: Request, res: Response, next: NextFunction): void {
  const incoming = req.header('x-request-id');
  const id = incoming && incoming.length > 0 ? incoming : randomUUID();
  req.id = id;
  res.setHeader('X-Request-Id', id);
  next();
}

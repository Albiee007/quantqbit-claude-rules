// src/middlewares/errorHandler.ts
// Terminal error handler. Express recognises it as the error-handling chain
// member by its 4-arg signature, so the `_next` param must remain.

import type { Request, Response, NextFunction } from 'express';
import { logger } from '../config/logger';

interface HttpError extends Error {
  status?: number;
}

export function errorHandler(
  err: HttpError,
  req: Request,
  res: Response,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _next: NextFunction,
): void {
  const status = err.status ?? 500;
  logger.error('request_error', {
    requestId: req.id,
    method: req.method,
    path: req.path,
    status,
    message: err.message,
  });
  res.status(status).json({
    error: err.name || 'InternalServerError',
    message: err.message || 'Internal server error',
    requestId: req.id,
  });
}

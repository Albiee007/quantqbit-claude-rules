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
  next: NextFunction,
): void {
  if (res.headersSent) {
    next(err);
    return;
  }
  const status = Number.isInteger(err.status) && err.status! >= 400 && err.status! <= 599
    ? err.status! : 500;
  logger.error('request_error', {
    requestId: req.id,
    method: req.method,
    path: req.path,
    status,
    message: err.message,
  });
  res.status(status).json({
    error: status >= 500 ? 'InternalServerError' : err.name || 'RequestError',
    message: status >= 500 ? 'Internal server error' : err.message || 'Request failed',
    requestId: req.id,
  });
}

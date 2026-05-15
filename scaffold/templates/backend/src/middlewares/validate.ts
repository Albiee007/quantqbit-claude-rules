// src/middlewares/validate.ts
// Zod-driven request validator factory. Call `validate({ body: schema })` to
// produce a middleware that validates `req.body` against `schema` and calls
// `next(err)` on failure.

import type { Request, Response, NextFunction, RequestHandler } from 'express';
import type { ZodSchema } from 'zod';

interface ValidationConfig {
  body?: ZodSchema;
  query?: ZodSchema;
  params?: ZodSchema;
}

export function validate(config: ValidationConfig): RequestHandler {
  return (req: Request, _res: Response, next: NextFunction) => {
    try {
      if (config.body) req.body = config.body.parse(req.body);
      if (config.query) req.query = config.query.parse(req.query);
      if (config.params) req.params = config.params.parse(req.params);
      next();
    } catch (err) {
      const error = err as Error & { status?: number };
      error.status = 400;
      next(error);
    }
  };
}

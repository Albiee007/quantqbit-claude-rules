// src/middlewares/validate.ts
// Zod-driven request validator factory. Call `validate({ body: schema })` to
// produce a middleware that validates `req.body` against `schema` and calls
// `next(err)` on failure.

import type { Request, Response, NextFunction, RequestHandler } from 'express';
import type { ZodType } from 'zod';

interface ValidationConfig {
  body?: ZodType;
  query?: ZodType;
  params?: ZodType;
}

export function validate(config: ValidationConfig): RequestHandler {
  return (req: Request, _res: Response, next: NextFunction) => {
    try {
      if (config.body) req.body = config.body.parse(req.body);
      // Express 5 exposes req.query through a getter; shadow it with the
      // parsed value instead of assigning.
      if (config.query) {
        Object.defineProperty(req, 'query', {
          value: config.query.parse(req.query),
          writable: true,
          configurable: true,
          enumerable: true,
        });
      }
      if (config.params) req.params = config.params.parse(req.params) as Request['params'];
      next();
    } catch (err) {
      const error = err as Error & { status?: number };
      error.status = 400;
      next(error);
    }
  };
}

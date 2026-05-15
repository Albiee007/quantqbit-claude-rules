// src/config/logger.ts
// Winston logger configured from env.LOG_LEVEL.
// `withRequestId(id)` returns a child logger that tags every entry with
// the request id (set by middlewares/requestId.ts).

import winston from 'winston';
import { env } from './env';

export const logger = winston.createLogger({
  level: env.LOG_LEVEL,
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json(),
  ),
  transports: [new winston.transports.Console()],
});

export function withRequestId(requestId: string): winston.Logger {
  return logger.child({ requestId });
}

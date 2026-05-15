// src/config/env.ts
// Zod-validated environment loader. Imports fail fast on boot if a required
// variable is missing or malformed — better to crash early than ship garbage.

import { z } from 'zod';

const schema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().positive().default(3000),
  LOG_LEVEL: z.enum(['error', 'warn', 'info', 'debug']).default('info'),
  MONGO_URI: z.string().optional().default(''),
  POSTGRES_HOST: z.string().optional().default(''),
  POSTGRES_PORT: z.coerce.number().int().positive().default(5432),
  POSTGRES_DB: z.string().optional().default(''),
  POSTGRES_USER: z.string().optional().default(''),
  POSTGRES_PASSWORD: z.string().optional().default(''),
});

const parsed = schema.safeParse(process.env);
if (!parsed.success) {
  // Surface the violation cleanly. We don't use the logger here because the
  // logger module depends on env.LOG_LEVEL — circular wake-up problem.
  // eslint-disable-next-line no-console
  console.error('[FAIL] Invalid environment:', parsed.error.flatten().fieldErrors);
  process.exit(1);
}

export const env = parsed.data;
export type Env = z.infer<typeof schema>;

// src/config/env.ts
// Zod-validated environment loader. Reads EXPO_PUBLIC_* vars (which Expo
// injects into JS at build time) and also falls back to expo-constants
// `extra` so app.json can supply defaults. Fails fast on boot if a required
// var is missing.

import Constants from 'expo-constants';
import { z } from 'zod';

const EnvSchema = z.object({
  EXPO_PUBLIC_API_BASE_URL: z.string().url().default('http://localhost:3000'),
  EXPO_PUBLIC_FEATURE_DEBUG: z
    .union([z.literal('true'), z.literal('false')])
    .default('false')
    .transform((v) => v === 'true'),
});

export type Env = z.infer<typeof EnvSchema>;

function readEnv(): Env {
  const raw = {
    EXPO_PUBLIC_API_BASE_URL:
      process.env.EXPO_PUBLIC_API_BASE_URL ??
      (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ??
      'http://localhost:3000',
    EXPO_PUBLIC_FEATURE_DEBUG:
      process.env.EXPO_PUBLIC_FEATURE_DEBUG ?? 'false',
  };

  const parsed = EnvSchema.safeParse(raw);
  if (!parsed.success) {
    // eslint-disable-next-line no-console
    console.error('[env] invalid environment:', parsed.error.flatten());
    throw new Error('Invalid environment configuration');
  }
  return parsed.data;
}

export const env: Env = readEnv();

// src/config/postgres.ts
// pg Pool factory. Lazy — the pool is only created the first time it's asked
// for, so the buildable starter doesn't try to connect when POSTGRES_HOST is
// empty.

import { Pool } from 'pg';
import type { Pool as PoolType } from 'pg';
import { env } from './env';

let pool: PoolType | null = null;

export function getPool(): PoolType {
  if (pool) return pool;
  if (!env.POSTGRES_HOST) {
    throw new Error('POSTGRES_HOST is not set — cannot create pg Pool');
  }
  pool = new Pool({
    host: env.POSTGRES_HOST,
    port: env.POSTGRES_PORT,
    database: env.POSTGRES_DB,
    user: env.POSTGRES_USER,
    password: env.POSTGRES_PASSWORD,
  });
  return pool;
}

export async function closePool(): Promise<void> {
  if (!pool) return;
  await pool.end();
  pool = null;
}

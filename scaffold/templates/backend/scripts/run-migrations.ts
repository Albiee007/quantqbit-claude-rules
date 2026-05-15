/**
 * scripts/run-migrations.ts
 *
 * Minimal migration runner — applies every `migrations/postgres/*.sql` file in
 * lexical order. Tracks applied migrations in a `_migrations` table so re-runs
 * are safe. Intentionally has no dependencies beyond `pg`.
 *
 * Usage:
 *   POSTGRES_HOST=... POSTGRES_PORT=... POSTGRES_DB=... \
 *   POSTGRES_USER=... POSTGRES_PASSWORD=... \
 *   npx tsx scripts/run-migrations.ts
 */

import { readdirSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { Client } from 'pg';

async function main(): Promise<void> {
  const host = process.env.POSTGRES_HOST;
  if (!host) {
    console.log('[INFO] POSTGRES_HOST not set — nothing to do.');
    return;
  }

  const client = new Client({
    host,
    port: Number(process.env.POSTGRES_PORT ?? 5432),
    database: process.env.POSTGRES_DB,
    user: process.env.POSTGRES_USER,
    password: process.env.POSTGRES_PASSWORD,
  });

  await client.connect();
  try {
    await client.query(
      'CREATE TABLE IF NOT EXISTS _migrations (id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, applied_at TIMESTAMPTZ DEFAULT NOW())',
    );

    const dir = resolve(__dirname, '..', 'migrations', 'postgres');
    const files = readdirSync(dir).filter((f) => f.endsWith('.sql')).sort();

    for (const file of files) {
      const { rows } = await client.query('SELECT 1 FROM _migrations WHERE name = $1', [file]);
      if (rows.length > 0) {
        console.log(`[OK]   skip ${file} (already applied)`);
        continue;
      }
      const sql = readFileSync(join(dir, file), 'utf8');
      console.log(`[INFO] apply ${file}`);
      await client.query('BEGIN');
      try {
        await client.query(sql);
        await client.query('INSERT INTO _migrations (name) VALUES ($1)', [file]);
        await client.query('COMMIT');
      } catch (err) {
        await client.query('ROLLBACK');
        throw err;
      }
    }
  } finally {
    await client.end();
  }
}

main().catch((err) => {
  console.error('[FAIL]', err);
  process.exit(1);
});

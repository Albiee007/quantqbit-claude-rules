-- 001_init.sql
-- Example initial migration. Delete or replace with your own schema.
-- The runner (scripts/run-migrations.ts) wraps each file in a transaction.

CREATE TABLE IF NOT EXISTS app_info (
  id SERIAL PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,
  value TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

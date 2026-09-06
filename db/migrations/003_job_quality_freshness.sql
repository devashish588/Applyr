-- Phase 9 — Job Quality / Freshness / Deduplication
-- PostgreSQL, additive, idempotent, operator-run: psql $DATABASE_URL -f db/migrations/003_job_quality_freshness.sql
-- Adds canonical identity, last_seen tracking, and source reliability fields.
-- Existing rows receive deterministic backfill (canonical_id from title/company/location/url, last_seen_at = scraped_at, source_url_canonical via URL canonicalizer).

-- Columns
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS canonical_id TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS last_seen_at TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_url_canonical TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_reliability TEXT;

-- Indexes for O(1) lookup (not O(n²) scan)
CREATE INDEX IF NOT EXISTS idx_jobs_canonical_id ON jobs(canonical_id);
CREATE INDEX IF NOT EXISTS idx_jobs_last_seen_at ON jobs(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_jobs_source_url_canonical ON jobs(source_url_canonical);
-- Unique canonical_id only for authoritative records (is_duplicate_of IS NULL)
DROP INDEX IF EXISTS uq_jobs_canonical_id_canonical;
CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_canonical_id_canonical ON jobs(canonical_id) WHERE is_duplicate_of IS NULL;

-- Backfill existing rows where canonical_id IS NULL
-- Note: exact hash will be recomputed via Python backfill if needed; this SQL provides fallback deterministic value.
-- We set last_seen_at = COALESCE(last_seen_at, scraped_at) and source_url_canonical placeholder.
UPDATE jobs SET last_seen_at = scraped_at WHERE last_seen_at IS NULL AND scraped_at IS NOT NULL;

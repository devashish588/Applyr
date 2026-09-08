-- 010: Source access policy + discovery method optimization
-- Adds role/mode and direct/search flags without creating second registry.
-- Additive, idempotent, PostgreSQL/Neon safe.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='job_sources' AND column_name='source_role') THEN
        ALTER TABLE job_sources ADD COLUMN source_role TEXT DEFAULT 'UNKNOWN';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='job_sources' AND column_name='primary_mode') THEN
        ALTER TABLE job_sources ADD COLUMN primary_mode TEXT DEFAULT 'AUTO';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='job_sources' AND column_name='direct_fetch_allowed') THEN
        ALTER TABLE job_sources ADD COLUMN direct_fetch_allowed BOOLEAN DEFAULT TRUE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='job_sources' AND column_name='search_discovery_allowed') THEN
        ALTER TABLE job_sources ADD COLUMN search_discovery_allowed BOOLEAN DEFAULT TRUE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='job_sources' AND column_name='observed_mode') THEN
        ALTER TABLE job_sources ADD COLUMN observed_mode TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='job_sources' AND column_name='observed_success_count') THEN
        ALTER TABLE job_sources ADD COLUMN observed_success_count INTEGER DEFAULT 0;
    END IF;
END $$;

-- Backfill built-in roles/modes (deterministic, minimal host mapping)
-- Wellfound and aggregators -> JOB_BOARD SEARCH direct false
-- Company-like custom will be EMPLOYER HTML direct true (handled in service, not here)
UPDATE job_sources SET source_role='JOB_BOARD', primary_mode='SEARCH', direct_fetch_allowed=false, search_discovery_allowed=true
WHERE host IN ('wellfound.com','linkedin.com','indeed.com','glassdoor.com','dice.com','naukri.com','ycombinator.com','builtin.com','arc.dev')
  AND (source_role IS NULL OR source_role='UNKNOWN');

UPDATE job_sources SET source_role='AGGREGATOR', primary_mode='SEARCH', direct_fetch_allowed=false, search_discovery_allowed=true
WHERE host IN ('weworkremotely.com','remoteok.com','remotive.com')
  AND (source_role IS NULL OR source_role='UNKNOWN');

-- ATS hosts
UPDATE job_sources SET source_role='ATS', primary_mode='ATS', direct_fetch_allowed=true, search_discovery_allowed=true
WHERE host LIKE '%greenhouse.io%' OR host LIKE '%lever.co%' OR host LIKE '%ashbyhq.com%' OR host LIKE '%myworkdayjobs.com%' OR host LIKE '%workable.com%' OR host LIKE '%bamboohr.com%'
  AND (source_role IS NULL OR source_role='UNKNOWN');

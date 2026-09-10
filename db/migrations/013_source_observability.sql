-- 013: Source observability hardening — additive telemetry for provider counts and site mismatch
-- Observability only, no recall change, no behavior change. Additive, idempotent, PostgreSQL/Neon safe.
-- Covers: provider_raw_count (Tavily raw for SEARCH), site_mismatch_count, llm_extracted_count is jobs_found (existing)
-- Do NOT apply to production automatically; operator applies via psql when ready.
-- No runtime DDL.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='job_source_runs') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='job_source_runs' AND column_name='provider_raw_count') THEN
            ALTER TABLE job_source_runs ADD COLUMN provider_raw_count INTEGER DEFAULT 0;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='job_source_runs' AND column_name='site_mismatch_count') THEN
            ALTER TABLE job_source_runs ADD COLUMN site_mismatch_count INTEGER DEFAULT 0;
        END IF;
    END IF;
END $$;

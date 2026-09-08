-- Phase Multi-Source: JobSource registry + per-source run health
-- Minimal registry for independent source execution (built-in + custom URLs)

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'job_sources') THEN
        CREATE TABLE job_sources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            host TEXT NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            source_type TEXT NOT NULL DEFAULT 'search',
            adapter TEXT NOT NULL DEFAULT 'SearchAdapter',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_run_at TEXT,
            last_success_at TEXT,
            last_failure_at TEXT,
            last_job_count INTEGER DEFAULT 0,
            last_duration_ms INTEGER DEFAULT 0,
            failure_category TEXT,
            last_error TEXT
        );
        CREATE INDEX idx_job_sources_enabled ON job_sources(enabled);
        CREATE INDEX idx_job_sources_host ON job_sources(host);
    END IF;

    -- Per-source run results (append-only, for Pipeline Status per-source health)
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'job_source_runs') THEN
        CREATE TABLE job_source_runs (
            id SERIAL PRIMARY KEY,
            run_id TEXT NOT NULL,
            source_id TEXT NOT NULL REFERENCES job_sources(id) ON DELETE CASCADE,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL DEFAULT 'running',
            adapter TEXT,
            jobs_found INTEGER DEFAULT 0,
            jobs_normalized INTEGER DEFAULT 0,
            jobs_new INTEGER DEFAULT 0,
            jobs_duplicate INTEGER DEFAULT 0,
            failure_category TEXT,
            error TEXT,
            duration_ms INTEGER DEFAULT 0
        );
        CREATE INDEX idx_job_source_runs_run_id ON job_source_runs(run_id);
        CREATE INDEX idx_job_source_runs_source_id ON job_source_runs(source_id);
        CREATE INDEX idx_job_source_runs_started ON job_source_runs(started_at DESC);
    END IF;
END $$;

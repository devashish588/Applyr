-- 009: Cross-source attribution + source priority (post-discovery enhancements)
-- Additive, idempotent, PostgreSQL/Neon safe. Does NOT replace canonical dedup.

DO $$
BEGIN
    -- Attribution: one canonical job can be observed via multiple sources
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'job_source_attributions') THEN
        CREATE TABLE job_source_attributions (
            id SERIAL PRIMARY KEY,
            canonical_job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            duplicate_job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
            source_id TEXT NOT NULL REFERENCES job_sources(id) ON DELETE CASCADE,
            source_name TEXT NOT NULL,
            host TEXT NOT NULL,
            mode TEXT NOT NULL,
            adapter TEXT NOT NULL,
            source_url TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            UNIQUE(canonical_job_id, source_id, source_url)
        );
        CREATE INDEX idx_attrib_canonical ON job_source_attributions(canonical_job_id);
        CREATE INDEX idx_attrib_source ON job_source_attributions(source_id);
        CREATE INDEX idx_attrib_host ON job_source_attributions(host);
    END IF;

    -- Future priority without schema rewrite (33.11)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='job_sources' AND column_name='priority') THEN
        ALTER TABLE job_sources ADD COLUMN priority INTEGER DEFAULT 100;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='job_sources' AND column_name='is_builtin') THEN
        ALTER TABLE job_sources ADD COLUMN is_builtin BOOLEAN DEFAULT FALSE;
        -- Backfill built-ins
        UPDATE job_sources SET is_builtin = (id LIKE 'builtin-%') WHERE is_builtin IS NULL;
    END IF;
END $$;

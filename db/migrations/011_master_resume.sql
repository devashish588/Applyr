-- 011: Master resume registry with active/history distinction
-- Additive, idempotent, PostgreSQL/Neon safe. Preserves historical applications.
-- Active resume is single row with active=TRUE. History retained with active=FALSE.
-- studio_runs.resume_id and applications.resume_id are nullable provenance (new runs only).

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='resumes') THEN
        CREATE TABLE resumes (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            mime_type TEXT,
            status TEXT NOT NULL DEFAULT 'PROCESSING',
            active BOOLEAN NOT NULL DEFAULT FALSE,
            uploaded_at TEXT NOT NULL,
            parsed_at TEXT,
            parse_error TEXT,
            parsed_json TEXT,
            skills_json TEXT,
            roles_json TEXT,
            health_json TEXT
        );
        CREATE INDEX idx_resumes_active ON resumes(active) WHERE active = TRUE;
        CREATE INDEX idx_resumes_status ON resumes(status);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname='uq_resumes_single_active') THEN
        CREATE UNIQUE INDEX uq_resumes_single_active ON resumes((active)) WHERE active = TRUE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='resumes' AND column_name='mime_type') THEN
        ALTER TABLE resumes ADD COLUMN mime_type TEXT;
    END IF;

    -- Provenance for new Studio runs (nullable, historical runs keep NULL)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='studio_runs')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='studio_runs' AND column_name='resume_id') THEN
        ALTER TABLE studio_runs ADD COLUMN resume_id INTEGER REFERENCES resumes(id) ON DELETE SET NULL;
    END IF;

    -- Provenance for new applications (nullable, historical rows keep NULL/existing paths)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='applications')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='applications' AND column_name='resume_id') THEN
        ALTER TABLE applications ADD COLUMN resume_id INTEGER REFERENCES resumes(id) ON DELETE SET NULL;
    END IF;
END $$;

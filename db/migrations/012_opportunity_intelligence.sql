-- 012: Opportunity Intelligence foundation (Phase 16, additive only)
-- Informational job-environment signals. No influence on Match/Priority.
-- Additive, idempotent, PostgreSQL/Neon safe. No opaque objects.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='job_opportunity_intelligence') THEN
        CREATE TABLE job_opportunity_intelligence (
            job_id INTEGER PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
            competition_intensity TEXT NOT NULL DEFAULT 'UNKNOWN',
            background_fit_sensitivity TEXT NOT NULL DEFAULT 'UNKNOWN',
            shortlisting_strictness TEXT NOT NULL DEFAULT 'UNKNOWN',
            determination_status TEXT NOT NULL DEFAULT 'UNDETERMINED',
            evidence_json TEXT,
            confidence REAL,
            computed_at TEXT
        );
        CREATE INDEX idx_opp_intel_determination ON job_opportunity_intelligence(determination_status);
    END IF;
END $$;

-- Phase 10 — Studio Runs (additive, idempotent)
-- Bounded persistence for Application Studio runs

CREATE TABLE IF NOT EXISTS studio_runs (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    candidate_id TEXT DEFAULT 'primary_candidate',
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'COMPLETED' CHECK (status IN ('COMPLETED','PARTIAL','FAILED')),
    match_snapshot TEXT,
    priority_snapshot TEXT,
    tailored_resume_path TEXT,
    ats_snapshot TEXT,
    cover_letter_path TEXT,
    recruiter_snapshot TEXT,
    warnings_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_studio_runs_job_id ON studio_runs(job_id);
CREATE INDEX IF NOT EXISTS idx_studio_runs_created_at ON studio_runs(created_at);

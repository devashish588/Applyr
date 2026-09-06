-- Phase 7 — Application Lifecycle (P0)
-- PostgreSQL, additive, idempotent, operator-run: psql $DATABASE_URL -f db/migrations/002_application_lifecycle.sql

CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    previous_application_id INTEGER REFERENCES applications(id) ON DELETE SET NULL,
    candidate_id TEXT DEFAULT 'primary_candidate',
    job_title_snapshot TEXT,
    company_snapshot TEXT,
    current_state TEXT NOT NULL CHECK (current_state IN ('DISCOVERED','PREPARING','READY_TO_APPLY','APPLIED','CLOSED')),
    last_state_change_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP,
    resume_path TEXT,
    cover_letter_path TEXT,
    match_snapshot TEXT,
    priority_snapshot TEXT,
    UNIQUE(job_id, attempt_number)
);
CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_state ON applications(current_state);

CREATE TABLE IF NOT EXISTS application_events (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'discovered','opened','shortlisted','preparing','resume_generated','cover_generated',
        'application_started','application_submitted','application_recorded_externally',
        'autofill_started','autofill_completed','autofill_failed','autofill_cancelled',
        'send_failed','withdrawn','expired','closed',
        'note'
    )),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actor TEXT NOT NULL CHECK (actor IN ('user','system')),
    payload TEXT,
    evidence_ref TEXT
);
CREATE INDEX IF NOT EXISTS idx_application_events_app_id ON application_events(application_id);

CREATE TABLE IF NOT EXISTS application_outcomes (
    application_id INTEGER PRIMARY KEY REFERENCES applications(id) ON DELETE CASCADE,
    outcome TEXT NOT NULL DEFAULT 'NONE' CHECK (outcome IN ('NONE','REJECTED','WITHDRAWN','EXPIRED','ACCEPTED','DECLINED','UNKNOWN')),
    decided_at TIMESTAMP,
    reason TEXT,
    offer_details TEXT
);

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_duplicate_of TEXT;

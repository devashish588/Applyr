-- Phase 12 — Feedback (additive, idempotent)
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    application_id INTEGER REFERENCES applications(id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
    signal_type TEXT NOT NULL CHECK (signal_type IN ('RECOMMENDATION_USEFUL','RECOMMENDATION_NOT_USEFUL','PREP_USEFUL','PREP_NOT_USEFUL','APPLICATION_WORTHWHILE','APPLICATION_NOT_WORTHWHILE')),
    value TEXT CHECK (char_length(value) <= 500),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feedback_application_id ON feedback(application_id);
CREATE INDEX IF NOT EXISTS idx_feedback_signal_type ON feedback(signal_type);

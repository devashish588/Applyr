-- Phase 11 — Interview & Follow-up (additive, idempotent)
-- Extends lifecycle to SCREENING/INTERVIEW/FINAL/OFFER and adds bounded tables

-- Update applications check to allow new states
ALTER TABLE applications DROP CONSTRAINT IF EXISTS applications_current_state_check;
ALTER TABLE applications ADD CONSTRAINT applications_current_state_check CHECK (current_state IN ('DISCOVERED','PREPARING','READY_TO_APPLY','APPLIED','SCREENING','INTERVIEW','FINAL','OFFER','CLOSED'));

-- Update events check to allow new lifecycle events
ALTER TABLE application_events DROP CONSTRAINT IF EXISTS application_events_event_type_check;
ALTER TABLE application_events ADD CONSTRAINT application_events_event_type_check CHECK (event_type IN ('discovered','opened','shortlisted','preparing','resume_generated','cover_generated','application_started','application_submitted','application_recorded_externally','autofill_started','autofill_completed','autofill_failed','autofill_cancelled','send_failed','withdrawn','expired','closed','note','screening_started','interview_scheduled','interview_completed','final_stage_reached','offer_received','application_withdrawn','follow_up_sent','recruiter_response','screening','interview','final','offer'));

-- Interviews: one application → many interviews
CREATE TABLE IF NOT EXISTS interviews (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    stage TEXT NOT NULL CHECK (stage IN ('PHONE_SCREEN','TECHNICAL','BEHAVIORAL','MANAGER','PANEL','FINAL','OTHER')),
    status TEXT NOT NULL DEFAULT 'SCHEDULED' CHECK (status IN ('SCHEDULED','COMPLETED','CANCELLED')),
    scheduled_at TEXT,
    completed_at TEXT,
    notes TEXT CHECK (char_length(notes) <= 2000),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_interviews_application_id ON interviews(application_id);
CREATE INDEX IF NOT EXISTS idx_interviews_status ON interviews(status);

-- Follow-ups: application-specific
CREATE TABLE IF NOT EXISTS follow_ups (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    follow_up_type TEXT NOT NULL CHECK (follow_up_type IN ('POST_APPLICATION','POST_SCREENING','POST_INTERVIEW','POST_OFFER')),
    channel TEXT NOT NULL CHECK (channel IN ('EMAIL','LINKEDIN','OTHER')),
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','REVIEW','APPROVED','SENT','CANCELLED')),
    scheduled_at TEXT,
    sent_at TEXT,
    subject TEXT,
    message_preview TEXT CHECK (char_length(message_preview) <= 2000),
    event_id INTEGER REFERENCES application_events(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_followups_application_id ON follow_ups(application_id);
CREATE INDEX IF NOT EXISTS idx_followups_status ON follow_ups(status);

-- Ensure new event types are allowed (already in ALLOWED_EVENT_TYPES, but DB check is application-level)
-- No change to applications table; uses existing is_duplicate_of etc.

-- Ensure studio_runs exists (from Phase 10) — no change

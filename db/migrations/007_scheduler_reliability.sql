-- Phase 13: Scheduler reliability enhancements
-- Add error_summary and duration_ms columns if not present
-- Add scheduler_owner table for cross-process ownership

DO $$
BEGIN
    -- Add error_summary column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'run_log' AND column_name = 'error_summary'
    ) THEN
        ALTER TABLE run_log ADD COLUMN error_summary TEXT;
    END IF;

    -- Add duration_ms column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'run_log' AND column_name = 'duration_ms'
    ) THEN
        ALTER TABLE run_log ADD COLUMN duration_ms INTEGER;
    END IF;

    -- Add started_at index for stuck run queries
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_run_log_status_started'
    ) THEN
        CREATE INDEX idx_run_log_status_started ON run_log(status, started_at);
    END IF;
END $$;

-- Scheduler ownership table (cross-process singleton)
CREATE TABLE IF NOT EXISTS scheduler_owner (
    id INTEGER PRIMARY KEY DEFAULT 1,
    owner_pid INTEGER NOT NULL,
    acquired_at TEXT NOT NULL,
    hostname TEXT
);

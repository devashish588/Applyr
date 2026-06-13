-- Applications Tracker Table
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT UNIQUE,
    source TEXT,  -- 'linkedin', 'internshala', 'naukri', 'company_careers'
    jd_text TEXT,
    fit_score INTEGER,  -- 0-100
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',  -- 'pending', 'tailored', 'applied', 'rejected', 'no_apply_link'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Email Sending Log
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    hr_email TEXT NOT NULL,
    subject TEXT,
    body_text TEXT,
    resume_path TEXT,
    cover_letter_path TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',  -- 'pending', 'sent', 'failed'
    error_message TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

-- Web Forms Submission Tracker
CREATE TABLE IF NOT EXISTS web_forms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    portal_url TEXT,
    fields_filled TEXT,  -- JSON string of filled fields
    screenshot_path TEXT,
    submitted_at TIMESTAMP,
    status TEXT DEFAULT 'pending',  -- 'pending', 'submitted', 'failed'
    error_message TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

-- Run Summary Log
CREATE TABLE IF NOT EXISTS run_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    triggered_by TEXT,  -- 'scheduler', 'manual'
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    jobs_found INTEGER DEFAULT 0,
    jobs_filtered INTEGER DEFAULT 0,
    jobs_applied INTEGER DEFAULT 0,
    emails_sent INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    summary_json TEXT,  -- JSON summary of the run
    status TEXT DEFAULT 'running'  -- 'running', 'completed', 'failed'
);

-- Create Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(status);
CREATE INDEX IF NOT EXISTS idx_emails_sent_at ON emails(sent_at);
CREATE INDEX IF NOT EXISTS idx_forms_status ON web_forms(status);

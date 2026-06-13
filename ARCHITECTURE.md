# Applyr Architecture & Pipeline Flow

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          APPLYR SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TRIGGERS                                                       │
│  ├─ 9 AM Daily (Cron)                                          │
│  ├─ Every 3 Hours (Interval)                                   │
│  └─ Manual: Web UI, CLI, File Upload                           │
│      │                                                          │
│      ▼                                                          │
│  ┌──────────────────────────────────────────────────────┐      │
│  │          ORCHESTRATOR (5-Step Pipeline)              │      │
│  │                                                       │      │
│  │  Step 1: DISCOVER                                   │      │
│  │  └─ 01_web_research_agent                           │      │
│  │     └─ Scrapes LinkedIn, Internshala, Naukri        │      │
│  │        Returns: [job_1, job_2, ...]                 │      │
│  │                                                       │      │
│  │  Step 2: PARSE & MATCH                              │      │
│  │  ├─ 09_resume_parser_agent                          │      │
│  │  │  └─ Extract user skills from profile.json        │      │
│  │  └─ 03_pdf_qa_agent                                 │      │
│  │     └─ Read uploaded JD PDFs/images                 │      │
│  │                                                       │      │
│  │  Step 3: FILTER & SCORE                             │      │
│  │  ├─ fit_scorer.py                                   │      │
│  │  │  └─ Score jobs 0-100 (skills, role, location)   │      │
│  │  ├─ deduplicator.py                                 │      │
│  │  │  └─ Prevent duplicate applications               │      │
│  │  └─ 18_job_application_agent                        │      │
│  │     └─ Filter & rank by score (≥50)                 │      │
│  │                                                       │      │
│  │  Step 4: TAILOR                                     │      │
│  │  └─ 16_doc_writer_agent                             │      │
│  │     ├─ Generate tailored resume PDF                 │      │
│  │     └─ Generate cover letter TXT                    │      │
│  │                                                       │      │
│  │  Step 5: DRAFT & SEND                               │      │
│  │  ├─ 05_email_drafting_agent                         │      │
│  │  │  └─ Compose personalized cold email              │      │
│  │  └─ email/sender.py                                 │      │
│  │     └─ Send via Gmail API with resume attached      │      │
│  │                                                       │      │
│  └──────────────────────────────────────────────────────┘      │
│      │                                                          │
│      ▼                                                          │
│  ┌──────────────────────────────────────────────────────┐      │
│  │     DATABASE & LOGGING                              │      │
│  │  ├─ db/applications.db (SQLite)                     │      │
│  │  │  ├─ jobs table                                   │      │
│  │  │  ├─ emails table                                 │      │
│  │  │  ├─ web_forms table                              │      │
│  │  │  └─ run_logs table                               │      │
│  │  └─ logs/orchestrator.log                           │      │
│  │     └─ Detailed execution log                       │      │
│  │                                                      │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                 │
│  USER INTERFACES                                                │
│  ├─ Web Dashboard: http://localhost:5000                       │
│  ├─ CLI: python pipeline/manual_trigger.py                     │
│  └─ Logs: tail -f logs/orchestrator.log                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Input

```
profile.json (user skills, preferences)
    ↓
Applications scraped from web
    ↓
Manual uploads (JD PDFs, screenshots, text)
```

### Processing

```
jobs[] → parse_and_match() → [job_1, job_2, ...]
           ↓
       filter_and_score()
           ↓
       [job_1, job_2, ...] (sorted by fit score)
           ↓
       tailor() → generate resume + cover letter
           ↓
       draft_and_send() → compose + send cold email
           ↓
       database storage + logging
```

### Output

```
database: applications.db
    └─ jobs table (title, company, fit_score, status)
    └─ emails table (hr_email, subject, body, sent_at)
    └─ web_forms table (portal_url, fields_filled, screenshots)
    └─ run_logs table (summary of each execution)

files:
    └─ resume/tailored/*.pdf (generated per job)
    └─ resume/cover_letters/*.txt (generated per job)
    └─ autofill/screenshots/*.png (form submission proofs)
    └─ logs/run_*.json (execution summaries)
```

---

## Component Interaction

### Orchestrator & Agents

```python
# orchestrator.py
orchestrator = Orchestrator()

# Step 1
jobs = orchestrator._step_discover()
# Calls: agents.01_web_research_agent.WebResearchAgent().scrape_jobs()

# Step 2
jobs = orchestrator._step_parse_and_match(jobs)
# Calls: agents.09_resume_parser_agent.ResumeParserAgent().parse_resume()
# Calls: agents.03_pdf_qa_agent.PDFQAAgent().extract_jd_from_pdf()

# Step 3
jobs = orchestrator._step_filter_and_score(jobs)
# Uses: utils.fit_scorer.FitScorer().score_job()
# Uses: utils.deduplicator.Deduplicator().should_skip_job()
# Calls: agents.18_job_application_agent.JobApplicationAgent().filter_and_rank_jobs()

# Step 4
jobs = orchestrator._step_tailor(jobs)
# Calls: agents.16_doc_writer_agent.DocWriterAgent().generate_tailored_resume()
# Calls: agents.16_doc_writer_agent.DocWriterAgent().generate_cover_letter()

# Step 5
jobs = orchestrator._step_draft_and_send(jobs)
# Calls: agents.05_email_drafting_agent.EmailDraftingAgent().draft_email()
# Uses: email.sender.EmailSender().send_email()

# Database
db = get_db()  # Global SQLite connection
db.add_job()
db.update_job_status()
db.add_email_log()
db.update_email_status()
```

---

## Database Schema

### `jobs` Table
```sql
id              INTEGER PRIMARY KEY
title           TEXT (job title)
company         TEXT (company name)
url             TEXT UNIQUE (job posting URL)
source          TEXT (linkedin|internshala|naukri|company_careers)
jd_text         TEXT (full job description)
fit_score       INTEGER (0-100)
status          TEXT (pending|tailored|applied|rejected)
created_at      TIMESTAMP
```

### `emails` Table
```sql
id              INTEGER PRIMARY KEY
job_id          INTEGER FOREIGN KEY → jobs.id
hr_email        TEXT (recipient email)
subject         TEXT
body_text       TEXT
resume_path     TEXT (path to attached resume)
cover_letter_path TEXT (path to cover letter)
sent_at         TIMESTAMP
status          TEXT (pending|sent|failed)
error_message   TEXT
```

### `web_forms` Table
```sql
id              INTEGER PRIMARY KEY
job_id          INTEGER FOREIGN KEY → jobs.id
portal_url      TEXT (job portal URL)
fields_filled   TEXT (JSON of {"field": "value"})
screenshot_path TEXT (proof of submission)
submitted_at    TIMESTAMP
status          TEXT (pending|submitted|failed)
error_message   TEXT
```

### `run_logs` Table
```sql
id              INTEGER PRIMARY KEY
run_id          TEXT UNIQUE (UUID for this run)
triggered_by    TEXT (scheduler|manual)
started_at      TIMESTAMP
completed_at    TIMESTAMP
jobs_found      INTEGER
jobs_filtered   INTEGER
jobs_applied    INTEGER
emails_sent     INTEGER
errors_count    INTEGER
summary_json    TEXT (full summary as JSON)
status          TEXT (running|completed|failed)
```

---

## Scheduling & Triggers

### Scheduler (APScheduler)

```python
# pipeline/scheduler.py

scheduler = BackgroundScheduler()

# Trigger 1: 9 AM daily
scheduler.add_job(
    run_pipeline,
    trigger=CronTrigger(hour=9, minute=0),
    id='morning_run'
)

# Trigger 2: Every 3 hours
scheduler.add_job(
    run_pipeline,
    trigger=IntervalTrigger(hours=3),
    id='every_3_hours'
)

scheduler.start()  # Runs in background
```

### Manual Triggers

```bash
# CLI
python pipeline/manual_trigger.py --run-now
python pipeline/manual_trigger.py --file uploads/jd.pdf
python pipeline/manual_trigger.py --text "Job description..."

# Web UI
POST /api/run-now
POST /api/upload-jd
POST /api/paste-jd
```

---

## Configuration & Customization

### profile.json (User Data)
```json
{
  "personal": {name, email, phone, linkedin, github, ...},
  "skills": {languages[], frameworks[], tools[], years_experience},
  "job_preferences": {target_roles[], locations[], min_salary, remote_ok, ...},
  "experience_summary": "...",
  "key_achievements": ["...", "..."]
}
```

### .env (API Keys)
```
ANTHROPIC_API_KEY=...
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
LINKEDIN_EMAIL=...
LINKEDIN_PASSWORD=...
```

### Email Templates
- `email/templates/cold_email.txt` - Main cold email
- `email/templates/follow_up.txt` - Follow-up email

Placeholders:
```
{{name}}, {{company}}, {{role}}, {{years_experience}},
{{main_skills}}, {{key_achievement_1}}, {{key_achievement_2}},
{{email}}, {{phone}}, {{linkedin}}
```

---

## Fit Scoring Algorithm

```python
fit_score = 0

# Role Match (0-30 points)
if job_title matches any target_role:
    fit_score += 30
elif job_title contains partial match:
    fit_score += 15

# Skills Match (0-40 points)
matched_skills = count_skills_in_jd(user_skills, jd_text)
fit_score += 40 * (matched_skills / total_skills)

# Location Match (0-20 points)
if location == "Remote" and user.remote_ok:
    fit_score += 20
elif location in user.target_locations:
    fit_score += 20
else:
    fit_score += 5

# Salary Match (0-10 points)
if job_salary >= user.min_salary:
    fit_score += 10
else:
    fit_score += 10 * (job_salary / user.min_salary)

# Result: 0-100 score
# Jobs < 50: rejected
# Jobs >= 50: applied to
```

---

## Error Handling & Logging

### Log Levels
```
DEBUG:  Detailed execution info (field fills, API calls)
INFO:   Major steps (job discovered, email sent, run completed)
WARNING: Potential issues (duplicate job, low score, parse error)
ERROR:  Failed operations (agent error, email send failed)
```

### Log Files
```
logs/orchestrator.log    - Main pipeline execution
logs/scheduler.log       - Scheduler events
logs/run_YYYY-MM-DD.json - Summary of each run
```

### Database Error Tracking
```sql
-- Check email failures
SELECT company, error_message FROM emails WHERE status='failed';

-- Check web form failures
SELECT portal_url, error_message FROM web_forms WHERE status='failed';

-- Check run errors
SELECT * FROM run_logs WHERE status='failed' ORDER BY started_at DESC;
```

---

## Extension Points

### Adding New Job Sources

Edit `agents/01_web_research_agent.py`:
```python
def scrape_new_source(self):
    # Add new source
    jobs = []
    # ... implement scraping ...
    return jobs

def scrape_jobs(self):
    all_jobs = (
        self.scrape_linkedin() +
        self.scrape_internshala() +
        self.scrape_new_source()  # NEW
    )
    return all_jobs
```

### Customizing Fit Score

Edit `utils/fit_scorer.py`:
```python
def score_job(self, job_data):
    # Adjust weights
    role_score = self._score_role(...) * 0.25  # Down from 0.30
    skills_score = self._score_skills(...) * 0.50  # Up from 0.40
    ...
```

### Modifying Email Template

Edit `email/templates/cold_email.txt`:
```
Dear {{company_hiring_manager}},

Your custom message here...

Best regards,
{{name}}
```

---

## Performance & Scaling

### Current Limits
- Max API calls per run: ~10 (constrained by rate limits)
- Max jobs processed: Limited by Anthropic API quota
- Email sending: 1 email per job (sequential)
- Schedule: 9 AM + every 3 hours = ~8 runs/day

### Optimization Tips
- Use Anthropic batch processing API for scoring
- Implement concurrent email sending
- Cache JD parsing results
- Reduce resume generation for low-fit jobs

### Database Indexing
```sql
-- Already included in schema.sql
CREATE INDEX idx_jobs_company ON jobs(company);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_emails_status ON emails(status);
CREATE INDEX idx_forms_status ON web_forms(status);
```

---

## Deployment Considerations

### Local Development
- Running locally with SQLite (included)
- Manual `python setup.py` initialization
- Web UI at `http://localhost:5000`

### Production Deployment
- Switch to PostgreSQL for concurrent access
- Deploy to VPS or AWS Lambda
- Use CloudScheduler instead of APScheduler
- Add Slack/email notifications for run summaries
- Implement SSL for email credentials
- Add authentication to web UI

### Environment Variables
All sensitive data in `.env`:
- API keys
- Email credentials
- Database URL
- SMTP settings

---

## Testing & Debugging

### Test Individual Agents
```bash
# Test web research agent
python -c "from agents.web_research_agent import WebResearchAgent; agent = WebResearchAgent(); print(agent.scrape_jobs())"

# Test fit scorer
python -c "from utils.fit_scorer import FitScorer; scorer = FitScorer(); print(scorer.score_job({'title': 'Python Dev', 'jd_text': 'Need Python and Django'}))"
```

### Dry Run (no email sending)
Edit `orchestrator.py` to comment out actual email sending and only log.

### Database Inspection
```bash
sqlite3 db/applications.db ".mode column" ".headers on" "SELECT * FROM jobs LIMIT 5;"
```

---

## Future Enhancements

- [ ] Multi-language job support
- [ ] Salary negotiation suggestion engine
- [ ] Interview preparation materials
- [ ] Application status tracking (responses, interviews)
- [ ] Competitor analysis (salaries, tech stacks)
- [ ] Integration with LinkedIn profile auto-fill
- [ ] Mobile app for job browsing
- [ ] Analytics dashboard (application rates, response rates)

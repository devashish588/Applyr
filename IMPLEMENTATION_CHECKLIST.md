# Implementation Checklist

Complete this checklist as you build out your Applyr system.

## Phase 1: Foundation Setup ✓
- [x] Create project structure
- [x] Create database schema and client
- [x] Setup utility modules (profile_loader, scorer, deduplicator)
- [x] Create orchestrator pipeline framework
- [x] Setup scheduler with APScheduler
- [x] Create Flask web UI
- [x] Setup Gmail API email sender
- [x] Create agent placeholder files

**Status**: Ready for configuration

---

## Phase 2: Configuration (Do This First)
- [ ] Copy `.env.example` to `.env`
- [ ] Get Anthropic API key and add to `.env`
- [ ] Setup Google Cloud OAuth 2.0 for Gmail
  - [ ] Create project in Google Cloud Console
  - [ ] Enable Gmail API
  - [ ] Create OAuth 2.0 Desktop credentials
  - [ ] Download JSON and save as `email/credentials.json`
- [ ] Update `profile.json` with your details:
  - [ ] Name, email, phone
  - [ ] LinkedIn, GitHub, portfolio URLs
  - [ ] Your skills (languages, frameworks, tools)
  - [ ] Target job roles and locations
  - [ ] Minimum salary expectation
  - [ ] Your experience summary
  - [ ] Key achievements
- [ ] Add your resume to `resume/master_resume.pdf`
- [ ] Run `python setup.py` to initialize database

---

## Phase 3: Implement Agent 1 - Web Research
**File**: `agents/01_web_research_agent.py`

- [ ] Implement `scrape_jobs()` method
  - [ ] Decide on scraping approach (Selenium, BeautifulSoup, etc.)
  - [ ] Implement LinkedIn scraping
  - [ ] Implement Internshala scraping
  - [ ] Implement Naukri scraping
  - [ ] Implement company careers page scraping
  - [ ] Return list of jobs with fields:
    - `title`, `company`, `url`, `source`, `jd_text`, `location`, `salary`, `hr_email`

**Test**:
```bash
python -c "from agents.web_research_agent import WebResearchAgent; agent = WebResearchAgent(); jobs = agent.scrape_jobs(); print(f'Found {len(jobs)} jobs')"
```

---

## Phase 4: Implement Agent 2 - PDF QA
**File**: `agents/03_pdf_qa_agent.py`

- [ ] Implement `extract_jd_from_pdf(pdf_path)` method
  - [ ] Use PyPDF2 or pdfplumber to read PDF
  - [ ] Extract text from PDF
  - [ ] Handle multi-page PDFs
  - [ ] Return clean JD text

- [ ] Implement `extract_jd_from_image(image_path)` method
  - [ ] Use pytesseract for OCR, or Claude vision API
  - [ ] Handle PNG/JPG/JPEG images
  - [ ] Extract text from screenshot
  - [ ] Return clean JD text

- [ ] Implement `extract_hr_contact_info(jd_text)` method
  - [ ] Parse email addresses from JD
  - [ ] Parse phone numbers if present
  - [ ] Detect apply portal URL
  - [ ] Return dict with contact info

**Test**:
```bash
# Upload a test PDF
python pipeline/manual_trigger.py --file test_jd.pdf
```

---

## Phase 5: Implement Agent 3 - Resume Parser
**File**: `agents/09_resume_parser_agent.py`

- [ ] Implement `parse_resume(resume_path)` method
  - [ ] Read PDF/DOCX resume file
  - [ ] Extract structured data:
    - [ ] Name, email, phone
    - [ ] Technical skills
    - [ ] Work experience
    - [ ] Key achievements
    - [ ] Education
  - [ ] Use Claude to parse (or NLP library)
  - [ ] Return parsed dict

- [ ] Implement `extract_skills(resume_text)` helper
- [ ] Implement `extract_achievements(resume_text)` helper

**Test**:
```bash
python -c "from agents.resume_parser_agent import ResumeParserAgent; agent = ResumeParserAgent(); result = agent.parse_resume('resume/master_resume.pdf'); print(result)"
```

---

## Phase 6: Implement Agent 4 - Documentation Writer
**File**: `agents/16_doc_writer_agent.py`

- [ ] Implement `generate_tailored_resume(job_jd, profile, master_resume_path)` method
  - [ ] Read master resume
  - [ ] Use Claude to tailor bullets for specific job
  - [ ] Reorder achievements to match job requirements
  - [ ] Generate PDF with tailored content
  - [ ] Save to `resume/tailored/{company}_{job_id}_resume.pdf`
  - [ ] Return path to generated resume

- [ ] Implement `generate_cover_letter(job_data, profile)` method
  - [ ] Use Claude to write personalized cover letter
  - [ ] Include company name, job title, relevant experience
  - [ ] Save to `resume/cover_letters/{company}_{job_id}_cover_letter.txt`
  - [ ] Return path to generated cover letter

- [ ] Implement `reorder_resume_bullets(master_resume, job_jd)` helper
  - [ ] Use Claude to rank resume bullets by relevance
  - [ ] Put most relevant first
  - [ ] Return reordered list

**Test**:
```bash
# This will be tested after full pipeline run
tail -f logs/orchestrator.log | grep "Tailored"
```

---

## Phase 7: Implement Agent 5 - Email Drafting
**File**: `agents/05_email_drafting_agent.py`

- [ ] Implement `draft_email(job_data, profile)` method
  - [ ] Use Claude to generate personalized email
  - [ ] Include job title, company, personal connection
  - [ ] Make it compelling (3-5 sentences)
  - [ ] Return dict: `{"subject": "...", "body": "..."}`

- [ ] Implement `personalize_email(template, replacements)` helper
  - [ ] Fill template placeholders
  - [ ] Handle missing values gracefully

**Test**:
```bash
# Check generated emails in database
sqlite3 db/applications.db "SELECT subject FROM emails LIMIT 5;"
```

---

## Phase 8: Implement Agent 6 - Job Application
**File**: `agents/18_job_application_agent.py`

- [ ] Implement `filter_and_rank_jobs(jobs, min_score)` method
  - [ ] Score each job using fit_scorer
  - [ ] Filter jobs >= min_score (default 50)
  - [ ] Sort by score descending
  - [ ] Return filtered + ranked jobs

- [ ] Implement `apply_to_job(job_data)` method
  - [ ] Detect application method (email, form, portal)
  - [ ] Delegate to appropriate handler
  - [ ] Return success/failure

- [ ] Implement `detect_apply_method(job_url)` helper
  - [ ] Parse URL to detect portal type
  - [ ] Return "email", "form", "external_portal", or "unknown"

**Test**:
```bash
# Run full pipeline
python pipeline/manual_trigger.py --run-now
# Check results
sqlite3 db/applications.db "SELECT company, fit_score, status FROM jobs ORDER BY fit_score DESC LIMIT 10;"
```

---

## Phase 9: Integrate Agents into Orchestrator
**File**: `pipeline/orchestrator.py`

For each agent class:
- [ ] Add proper import statement
- [ ] Create agent instance in corresponding `_step_*` method
- [ ] Call agent method with correct parameters
- [ ] Handle agent errors/exceptions
- [ ] Log agent execution

Specific steps:
- [ ] Step 1: Import and call WebResearchAgent
- [ ] Step 2: Import and call ResumeParserAgent + PDFQAAgent
- [ ] Step 3: Already using FitScorer and Deduplicator
- [ ] Step 4: Import and call DocWriterAgent
- [ ] Step 5: Import and call EmailDraftingAgent + EmailSender

---

## Phase 10: Setup Email Sending
**File**: `email/sender.py` (mostly done, just test)

- [ ] Run Gmail OAuth authentication
  - [ ] `python email/sender.py` (or test first login)
  - [ ] Authorize with Google account
  - [ ] Verify `email/token.json` created

- [ ] Test email sending
  ```bash
  python -c "
  from email.sender import EmailSender
  sender = EmailSender()
  sender.send_email(
    to_email='your-test-email@gmail.com',
    subject='Test from Applyr',
    body='This is a test email',
    resume_path='resume/master_resume.pdf'
  )
  "
  ```

---

## Phase 11: Test Full Pipeline
- [ ] Test with `--run-now` manual trigger
  ```bash
  python pipeline/manual_trigger.py --run-now
  ```

- [ ] Check database for results
  ```bash
  sqlite3 db/applications.db "SELECT * FROM jobs LIMIT 5;" | column
  ```

- [ ] Check logs for errors
  ```bash
  tail -f logs/orchestrator.log
  ```

- [ ] Verify emails prepared (if agents implemented)
  ```bash
  sqlite3 db/applications.db "SELECT company, status FROM emails LIMIT 5;"
  ```

---

## Phase 12: Setup Automation

### Option A: Web Dashboard (Recommended)
- [ ] Start Flask UI
  ```bash
  python ui/app.py
  ```
- [ ] Open http://localhost:5000
- [ ] Test "Run Pipeline Now" button
- [ ] Test file upload
- [ ] Test JD text paste

### Option B: Scheduled Runs
- [ ] Start scheduler
  ```bash
  python pipeline/scheduler.py
  ```
- [ ] Runs will execute at 9 AM + every 3 hours
- [ ] Check logs to verify
  ```bash
  tail -f logs/scheduler.log
  ```

### Option C: Deploy to Production
- [ ] Deploy to VPS/EC2/Lambda
- [ ] Setup environment variables on server
- [ ] Configure persistent scheduler
- [ ] Setup log rotation
- [ ] Monitor for errors

---

## Phase 13: Customize & Optimize
- [ ] Edit email templates (`email/templates/`) to your style
- [ ] Adjust fit score weights in `utils/fit_scorer.py` if needed
- [ ] Add more job sources to web research agent
- [ ] Implement advanced form filling in browser_agent
- [ ] Add deduplication checks if needed
- [ ] Customize profile.json job preferences

---

## Phase 14: Monitor & Maintain
- [ ] Check logs regularly
  ```bash
  tail logs/orchestrator.log
  tail logs/scheduler.log
  ```

- [ ] Query database for metrics
  ```bash
  sqlite3 db/applications.db "SELECT COUNT(*) FROM jobs WHERE status='applied';"
  ```

- [ ] Update profile.json as your skills evolve
- [ ] Adjust email templates based on response rates
- [ ] Add new job sources as needed
- [ ] Clean up old data periodically

---

## Final Verification Checklist
- [ ] All 6 agents implemented and imported
- [ ] Database initializes on first run
- [ ] Profile.json validates correctly
- [ ] .env has all required API keys
- [ ] Gmail OAuth works (emails can be sent)
- [ ] Web UI starts without errors
- [ ] Scheduler runs at expected times
- [ ] Manual triggers work (CLI + web)
- [ ] Full pipeline executes successfully
- [ ] Database populated with test jobs
- [ ] Emails drafted and sent (or logged)
- [ ] Logs show no critical errors

---

## Success Criteria
✅ **Pipeline runs end-to-end**: discover → parse → score → tailor → send
✅ **Scheduling works**: Runs at 9 AM + every 3 hours automatically
✅ **Database tracks**: jobs, emails, forms, runs
✅ **Emails sent**: Cold emails going out to HR
✅ **Zero duplicates**: Never applies to same company twice
✅ **User can monitor**: Via web UI or logs

---

## Troubleshooting Commands

```bash
# Check if agents are imported correctly
python -c "from agents.web_research_agent import WebResearchAgent; print('✓ WebResearchAgent imports')"

# Test fit scorer
python -c "from utils.fit_scorer import FitScorer; scorer = FitScorer(); print(scorer.score_job({'title': 'Python Dev', 'jd_text': 'Python Django'}))"

# Check database
sqlite3 db/applications.db ".schema jobs"

# View recent runs
sqlite3 db/applications.db "SELECT * FROM run_logs ORDER BY started_at DESC LIMIT 3;"

# Check for errors
grep "ERROR" logs/orchestrator.log
```

---

Good luck with your implementation! 🚀

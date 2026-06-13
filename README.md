# Applyr - Automated Job Application System

🚀 **Fully automated job discovery, matching, tailoring, and cold email outreach pipeline.**

## What It Does

Applyr runs a 5-step pipeline to automate your job applications:

1. **Discover** → Web research agent scrapes LinkedIn, Internshala, Naukri, company careers pages
2. **Parse & Match** → Resume parser extracts your skills; PDF QA agent reads uploaded JDs
3. **Filter & Score** → Job application agent ranks by fit (0-100 score)
4. **Tailor** → Documentation writer rewrites resume bullets + generates cover letter
5. **Draft & Send** → Email drafting agent composes personalized cold email and sends it

**Two trigger modes:**
- **Automated**: Runs at 9 AM daily + every 3 hours
- **Manual**: Upload a JD PDF/screenshot or paste job description text

---

## Project Structure

```
Applyr/
├── profile.json                 # Your master profile (name, skills, preferences)
├── .env                         # API keys (never commit)
├── .env.example                 # Template for .env
├── requirements.txt             # Python dependencies
├── README.md                    # This file
│
├── agents/                      # Your 6 core agents (you provide these)
│   ├── 01_web_research_agent.py
│   ├── 03_pdf_qa_agent.py
│   ├── 05_email_drafting_agent.py
│   ├── 09_resume_parser_agent.py
│   ├── 16_doc_writer_agent.py
│   └── 18_job_application_agent.py
│
├── pipeline/                    # Orchestration & scheduling
│   ├── orchestrator.py          # Runs 5-step pipeline
│   ├── scheduler.py             # APScheduler cron jobs
│   └── manual_trigger.py        # For on-demand runs
│
├── db/                          # SQLite database
│   ├── schema.sql               # Database schema
│   ├── db_client.py             # Database wrapper
│   └── applications.db          # (created on first run)
│
├── email/                       # Cold email sending
│   ├── sender.py                # Gmail API integration
│   ├── credentials.json         # OAuth token (get from Google Cloud)
│   └── templates/
│       ├── cold_email.txt       # Email template with {{placeholders}}
│       └── follow_up.txt        # Follow-up template
│
├── utils/                       # Helper modules
│   ├── profile_loader.py        # Reads & validates profile.json
│   ├── deduplicator.py          # Prevents duplicate applications
│   └── fit_scorer.py            # Scores job fit 0-100
│
├── autofill/                    # Playwright browser automation
│   ├── browser_agent.py         # Form filling automation
│   ├── field_mapper.py          # Maps form fields to profile
│   └── screenshots/             # Form submission confirmations
│
├── ui/                          # Flask web dashboard
│   ├── app.py                   # Flask backend
│   └── templates/
│       └── index.html           # Web UI (Run Now, Upload, Stats)
│
├── resume/                      # Resume management
│   ├── master_resume.pdf        # Your master resume
│   ├── tailored/                # Generated per-job
│   └── cover_letters/           # Generated per-job
│
├── uploads/                     # User uploads
│   ├── jd_pdfs/
│   └── jd_screenshots/
│
└── logs/                        # Pipeline execution logs
    ├── orchestrator.log
    ├── scheduler.log
    └── run_YYYY-MM-DD.json
```

---

## Setup

### 1. Clone & Install Dependencies

```bash
cd Applyr
pip install -r requirements.txt

# For Playwright browser automation
python -m playwright install chromium
```

### 2. Configure Your Profile

Edit `profile.json` with your personal info, skills, and job preferences:

```json
{
  "personal": {
    "name": "Your Name",
    "email": "your.email@example.com",
    "phone": "+1-XXX-XXX-XXXX",
    "linkedin": "https://linkedin.com/in/yourprofile",
    "github": "https://github.com/yourprofile",
    "portfolio": "https://yourportfolio.com"
  },
  "skills": {
    "languages": ["Python", "JavaScript", "SQL"],
    "frameworks": ["Django", "React", "FastAPI"],
    "tools": ["Git", "Docker", "AWS"],
    "years_experience": 5
  },
  "job_preferences": {
    "target_roles": ["Software Engineer", "Full Stack Developer"],
    "target_locations": ["Remote", "San Francisco"],
    "min_salary": 120000,
    "remote_ok": true,
    "fulltime_only": true
  }
}
```

### 3. Set Up Environment Variables

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env` with:
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `GMAIL_CLIENT_ID` & `GMAIL_CLIENT_SECRET` - From Google Cloud Console
- LinkedIn, Internshala, Naukri credentials (if scraping)
- Other API keys as needed

### 4. Set Up Gmail OAuth (for email sending)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 Desktop Application credentials
3. Download JSON and save as `email/credentials.json`
4. First run will prompt browser login to authorize

### 5. Place Your Master Resume

Add your resume (PDF or DOCX) to:
- `resume/master_resume.pdf`

---

## Usage

### Automatic (Scheduled)

Start the background scheduler (runs at 9 AM + every 3 hours):

```bash
python pipeline/scheduler.py
```

This will:
- Run at 9:00 AM every day
- Run every 3 hours thereafter
- Scrape new jobs, score, apply, and send cold emails
- Log results to `logs/`

### Manual Run (CLI)

Trigger pipeline immediately:

```bash
python pipeline/manual_trigger.py --run-now
```

With uploaded JD file:
```bash
python pipeline/manual_trigger.py --file uploads/jd.pdf
```

With pasted JD text:
```bash
python pipeline/manual_trigger.py --text "Senior Python Developer..."
```

### Web Dashboard

Start the Flask UI:

```bash
python ui/app.py
```

Then open [http://localhost:5000](http://localhost:5000) to:
- Click "Run Pipeline Now" button
- Upload JD PDFs/screenshots
- Paste job descriptions
- View real-time stats & logs

---

## Database

The SQLite database tracks:
- **jobs** - All discovered/scraped jobs with fit scores
- **emails** - Sent cold emails and delivery status
- **web_forms** - Portal form submissions with screenshots
- **run_logs** - Summary of each pipeline execution

### Initialize Database

On first run, `db_client.py` automatically creates tables from `schema.sql`. To manually initialize:

```bash
cd db/
sqlite3 applications.db < schema.sql
```

### Query Results

View your applications:

```bash
sqlite3 db/applications.db "SELECT company, title, fit_score, status FROM jobs ORDER BY fit_score DESC LIMIT 10;"
```

---

## Integrating Your Agents

The orchestrator expects your 6 agents in the `agents/` folder:

```python
# agents/01_web_research_agent.py
class WebResearchAgent:
    def scrape_jobs(self):
        """Return list of jobs: [{"title", "company", "url", "jd_text", ...}]"""
        pass

# agents/03_pdf_qa_agent.py
class PDFQAAgent:
    def extract_jd_from_pdf(self, pdf_path):
        """Return JD text extracted from PDF"""
        pass

# agents/05_email_drafting_agent.py
class EmailDraftingAgent:
    def draft_email(self, job_data):
        """Return {"subject", "body"}"""
        pass

# agents/09_resume_parser_agent.py
class ResumeParserAgent:
    def parse_resume(self, resume_path):
        """Return parsed resume data"""
        pass

# agents/16_doc_writer_agent.py
class DocWriterAgent:
    def generate_tailored_resume(self, job_jd, profile):
        """Return path to generated resume PDF"""
        pass
    
    def generate_cover_letter(self, job_data):
        """Return path to generated cover letter"""
        pass

# agents/18_job_application_agent.py
class JobApplicationAgent:
    def filter_and_rank_jobs(self, jobs):
        """Return scored/filtered jobs"""
        pass
```

The `orchestrator.py` calls each agent in sequence. Replace placeholder imports with your actual agent implementations.

---

## Key Features

✅ **Duplicate Prevention** - Never emails same company twice  
✅ **Fit Scoring** - Matches job requirements to your profile (0-100)  
✅ **Scheduled** - Runs at 9 AM + every 3 hours automatically  
✅ **Manual Override** - Upload JDs or paste text anytime  
✅ **Web Dashboard** - No terminal needed; UI-based control  
✅ **Cold Emails** - Sends personalized emails with tailored resume  
✅ **Audit Trail** - Database tracks all applications & emails sent  
✅ **Form Automation** - Playwright fills and submits job portals  
✅ **Extensible** - Easily swap agents or add new data sources  

---

## Typical Workflow

1. **Set up profile.json** - Your master profile
2. **Configure .env** - Add API keys
3. **Place your resume** - `resume/master_resume.pdf`
4. **Start scheduler** - `python pipeline/scheduler.py` (runs in background)
5. **Check dashboard** - `python ui/app.py` and view at http://localhost:5000
6. **Monitor logs** - Tail `logs/orchestrator.log` to see what's happening
7. **Apply manually** - Upload JDs anytime via UI or CLI

---

## Logs & Debugging

### View Real-Time Orchestrator Logs

```bash
tail -f logs/orchestrator.log
```

### View Scheduler Logs

```bash
tail -f logs/scheduler.log
```

### Check Latest Run Summary

```bash
ls -lt logs/ | head -5  # Find latest
cat logs/run_2024-06-13_090000.json
```

### Query Database

```bash
# Jobs with highest fit scores
sqlite3 db/applications.db "SELECT title, company, fit_score FROM jobs ORDER BY fit_score DESC LIMIT 20;"

# Emails sent in last 24 hours
sqlite3 db/applications.db "SELECT company, sent_at FROM emails WHERE sent_at > datetime('now', '-1 day');"

# Failed applications
sqlite3 db/applications.db "SELECT company, error_message FROM emails WHERE status = 'failed';"
```

---

## Troubleshooting

### **Pipeline not running on schedule**
- Check `logs/scheduler.log`
- Ensure scheduler process is still running
- Verify APScheduler dependency: `pip install APScheduler`

### **Emails not sending**
- Confirm Gmail OAuth token in `email/token.json` exists
- Verify `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` in `.env`
- Check Gmail account allows "Less Secure Apps" or has OAuth properly configured

### **Jobs not being found**
- Check if web research agent is actually scraping (implementation needed)
- View `logs/orchestrator.log` for agent errors
- Verify Anthropic API key is valid

### **Database locked errors**
- Close any other processes accessing `db/applications.db`
- Delete `.db-journal` file if stuck

### **Playwright form filling not working**
- Ensure Playwright is installed: `python -m playwright install chromium`
- Check that portal URLs are accessible
- Verify field selectors match actual HTML

---

## Configuration

### Email Templates

Edit `email/templates/cold_email.txt` with your custom message. Available placeholders:

```
{{name}} - Your name
{{company}} - Company name
{{role}} - Job title
{{years_experience}} - Years in field
{{main_skills}} - Comma-separated skills
{{key_achievement_1}} - First achievement from profile
{{key_achievement_2}} - Second achievement
{{email}} - Your email
{{phone}} - Your phone
{{linkedin}} - Your LinkedIn URL
```

### Scoring Algorithm

The fit scorer weights matches:
- **Role**: 30 points (target roles match)
- **Skills**: 40 points (skills match JD)
- **Location**: 20 points (location preference)
- **Salary**: 10 points (meets minimum salary)

Jobs scoring ≥50 are applied to automatically.

### Filter Thresholds

Edit `utils/fit_scorer.py` to adjust minimum fit score for applications.

---

## Cost Estimate

- **Anthropic API**: ~$0.10-0.50 per run (depends on JD length)
- **Gmail API**: Free (100M requests/day included)
- **Web hosting** (if deployed): ~$5-10/month for small VPS

---

## Contributing

To add new data sources or agents:

1. Create agent file in `agents/` with proper interface
2. Update orchestrator to call your new agent
3. Add agent logic and testing
4. Test full pipeline before committing

---

## License

MIT - Use freely for personal or commercial projects

---

## Support

For issues or questions:
1. Check `logs/` for error messages
2. Review `README.md` Troubleshooting section
3. Verify `.env` configuration is complete
4. Test individual agents in isolation

---

**Happy job hunting! 🎯**

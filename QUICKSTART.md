# Applyr Quick Start Guide

## 🚀 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Run Setup Script
```bash
python setup.py
```

This will:
- Create all directories
- Initialize SQLite database
- Generate template `profile.json`

### 3. Configure Your Profile
```bash
# Edit your details
nano profile.json
```

Key fields to update:
- `personal.name`, `email`, `phone`
- `personal.linkedin`, `github`
- `skills.languages`, `frameworks`, `tools`
- `job_preferences.target_roles`, `locations`, `min_salary`

### 4. Setup Gmail API (for cold emails)
```bash
# Get OAuth credentials from Google Cloud Console
# Save as: email/credentials.json
# First run will prompt for authorization
```

### 5. Add Your Resume
```bash
cp /path/to/your/resume.pdf resume/master_resume.pdf
```

### 6. Copy Environment Template
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 7. Add Your Agents
```bash
# Place your agent implementations in:
# agents/01_web_research_agent.py
# agents/03_pdf_qa_agent.py
# agents/05_email_drafting_agent.py
# agents/09_resume_parser_agent.py
# agents/16_doc_writer_agent.py
# agents/18_job_application_agent.py
```

---

## ▶️ Run Modes

### Option A: Web Dashboard (Recommended)
```bash
python ui/app.py
# Open: http://localhost:5000
# Click "Run Pipeline Now" or upload JDs
```

### Option B: Automatic Scheduling
```bash
python pipeline/scheduler.py
# Runs at 9 AM + every 3 hours
# Keep running in background (tmux/screen)
```

### Option C: Manual CLI Trigger
```bash
# Run full pipeline immediately
python pipeline/manual_trigger.py --run-now

# With uploaded JD
python pipeline/manual_trigger.py --file uploads/jd.pdf

# With pasted JD text
python pipeline/manual_trigger.py --text "Senior Python Developer..."
```

---

## 📊 Monitor Progress

### View Logs
```bash
tail -f logs/orchestrator.log
```

### Check Database
```bash
sqlite3 db/applications.db
> SELECT company, title, fit_score, status FROM jobs ORDER BY fit_score DESC LIMIT 10;
```

### View Web Dashboard
```
http://localhost:5000
```

---

## 🔑 Key Files to Know

| File | Purpose |
|------|---------|
| `profile.json` | Your master profile (update once) |
| `.env` | API keys (never commit) |
| `resume/master_resume.pdf` | Your resume (placed once) |
| `db/applications.db` | SQLite database (auto-created) |
| `logs/` | Execution logs |
| `agents/` | Your 6 agent implementations |

---

## 🐛 Troubleshooting

**Pipeline not running?**
```bash
tail -f logs/orchestrator.log  # Check for errors
```

**Emails not sending?**
- Verify Gmail OAuth token: `ls email/token.json`
- Check `.env` has valid credentials
- Ensure Google Cloud OAuth is configured

**Jobs not scraped?**
- Implement `agents/01_web_research_agent.py`
- Run with `--run-now` to test

**Database errors?**
```bash
# Reset database
rm db/applications.db
python setup.py
```

---

## 📚 Full Documentation

See [README.md](README.md) for detailed documentation, configuration options, and advanced usage.

---

**Ready to automate? Start with `python ui/app.py`!** 🎯

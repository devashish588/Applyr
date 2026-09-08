# Real Job Pilot — How to Use

This log is for the 20–30 job pilot. It is **not** production storage.

## Location
`tests/data/real_job_pilot/` — tracked, but empty until you run the pilot.

## Files
- `job_evaluation_template.json` — copy per job (`job_001.json`, `job_002.json`, ...)
- `aggregate.csv` — optional spreadsheet view (same fields)
- Use either JSON per job or one CSV; `scripts/pilot_report.py` reads both.

## Workflow (per job)
1. Discover job in Applyr → note `job_id`, `company`, `title`, `source`, `discovered_at`, `match_score`, `application_priority`.
2. Record **human** `human_match_assessment` (HIGH/MEDIUM/LOW) and `human_priority_assessment` (HOT/WARM/COLD/REVIEW) **before** seeing Applyr's priority if possible.
3. Decide `APPLY / SKIP / REVIEW` and why.
4. If `APPLY`, run Studio, note `preparation_time_minutes`, `application_started`, `application_submitted`, then `interview_received`, `interview_prep_used`, `follow_up_used`, `final_outcome` as they happen.
5. Add `friction_notes`, `correctness_notes`, `discovery_quality_notes` (free text) and `discovery_quality` label.

## Discovery Quality Labels
`RELEVANT` · `IRRELEVANT` · `DUPLICATE` · `STALE` · `BROKEN` · `UNCERTAIN` — see `docs/REAL_WORLD_PILOT.md` §6.

## Privacy
Do not put API keys, passwords, bearer tokens, resume text, or private notes with PII. Use anonymized company/title if needed. The log is tracked but should never contain secrets.

## Helper
```bash
python scripts/pilot_report.py
python scripts/pilot_report.py --csv tests/data/real_job_pilot/aggregate.csv
```
Prints `Jobs evaluated: 20, Relevant: 16, ... , Applyr/Human Agreement: 15/20` without touching production DB.

## Empty Until Real
Do not generate fake pilot data. The directory stays empty until you evaluate real jobs.

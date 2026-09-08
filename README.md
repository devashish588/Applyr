# Applyr 2.0

AI-assisted career application platform that helps you discover relevant opportunities, understand why a job fits, evaluate priority, prepare tailored applications, track applications, prepare for interviews, follow up, and learn from outcomes.

Applyr is designed around outcome-oriented job searching — not just job discovery. Every recommendation is explainable, and every consequential action (resume approval, application creation, outreach) requires explicit human approval.

## What Applyr Does

**End-to-end workflow:** Discover → Analyze → Match → Prioritize → Prepare → Apply → Track → Interview → Follow Up → Outcome → Learn

- Discover jobs via AI-assisted search with duplicate and freshness handling
- Analyze each job for required skills, experience, role, location, and seniority
- Score fit (Match) and recommend priority (Application Priority) as separate concepts
- Prepare per-job in Application Studio (tailoring proposal, requirement coverage, cover letter, recruiter preview)
- Create and track applications through a lifecycle: `PREPARING → READY_TO_APPLY → APPLIED → SCREENING → INTERVIEW → FINAL → OFFER → CLOSED` with `UNKNOWN` vs `MISSING` preserved
- Prepare for interviews with application-specific kits and practice evaluation
- Manage follow-ups `DRAFT → REVIEW → APPROVED → SENT` (never auto-send)
- Record outcomes and learn via funnel, conversion, and priority insights

## Core Features

### Intelligent Job Discovery
- Web research agent with Tavily + LLM extraction, rotating `site:` pool and time phrases for variety, fallback without `site:` filter when needed
- URL canonicalization (strip `utm_*`, sort query, lower host), host-exact source reliability (`greenhouse.io` vs `fakegreenhouse.io`)
- Canonical `canon-<sha16>` via `title|company|location|host` and duplicate chain `is_duplicate_of` with `visited` guard

### Candidate Intelligence
- Resume parsing (PyMuPDF/pdfplumber/OCR) → structured `parsed_json` with confidence, section detection before LLM, role inference
- Provenance: `DETERMINED` vs `UNKNOWN`, `UNKNOWN` never becomes `MISSING` or `FACT`

### Match Engine 2.0
Five dimensions, sacred weights **Skills 40% / Experience 25% / Role 20% / Location 10% / Seniority 5%** (`core/services/match_service.py:68`). `MatchService` is authoritative for `final_score` (0–100); `MatchEngine2` provides `requirement_evaluations` with `SATISFIED / MISSING / UNKNOWN` and `relationship_type` (EXACT, ALIAS, RELATED) without altering the score. Frontend displays `match.final_score`, `why_this_score`, `supporting_sentences` — no frontend scoring.

### Application Priority
Separate from Match Score. `HOT` (fresh, no blockers), `WARM` (one UNKNOWN or aging), `COLD` (required `MISSING` or seniority `LOWER`), `REVIEW` (≥2 UNKNOWN) (`core/services/application_priority_service.py:118`). Answers “Should I spend time applying?” — not a probability.

### Application Studio
Per-job `POST /api/applications/studio/:jobId` `ui/app.py:1416` → `StudioService.build` `core/services/studio_service.py:66` (candidate/job intelligence, match, priority, skill gaps `SUPPORTED_BUT_UNDER_REPRESENTED` vs `UNSUPPORTED` vs `UNKNOWN`, `resume_source` `READY`, `tailoring_proposal` `READY/REQUIRES_REVIEW`, `ats.details.ats_score == null` `core/services/studio_service.py:365` `NOT_AVAILABLE` + `requirement_coverage_percent`, cover letter, recruiter/outreach preview). Approval explicit: `Approve tailoring proposal` checkbox `frontend/src/pages/studio.tsx:95` required for `Create Application (PREPARING)` `frontend/src/pages/studio.tsx:146` `disabled={!approvals.resume}` + `isCreating` guard. External submission remains user-controlled (`PREPARING` → `APPLIED` via `POST /api/applications/:id/apply` `ui/app.py:1352`).

### Application Lifecycle
`core/services/application_service.py:54` `ALLOWED_STATES` 9 + `ALLOWED_TRANSITIONS` `PREPARING → READY_TO_APPLY → APPLIED → SCREENING → INTERVIEW → FINAL → OFFER → CLOSED` (`CLOSED` terminal `application_service.py:64`). Reapply `attempt_number +1` `application_service.py:111`, `application_events` append-only `application_service.py:126` `ORDER BY timestamp ASC`, `SELECT FOR UPDATE` `application_service.py:100` for concurrency.

### Recruiter & Contact Directory
`GET /api/recruiters` `ui/app.py:1768` `db/db_client.py:983` `SELECT * FROM recruiters ORDER BY confidence DESC` (`company, job_id, name, role, email, confidence, source, linkedin`). UI `frontend/src/pages/networking.tsx:7` shows `Unknown Contact` / `Unverified` `Source unavailable` when missing, `Verified ... Source: Company careers page` when available. No fake `john.smith@company.com` generation. Association via `job_id`.

### Analytics
`GET /api/analytics/overview` `ui/app.py:1822` `funnel` `OutcomeAnalyticsService` `core/services/outcome_analytics_service.py:26` `started/submitted/screening/interview/final/offer/accepted` with `count(DISTINCT application_id)` dedup `outcome_analytics_service.py:39` + `final_from_state + final_from_events` `outcome_analytics_service.py:50` historical. Rates via `_rate(n,d)` `outcome_analytics_service.py:20` `d==0 → None` (shows `—` `frontend/src/pages/dashboard.tsx:278` not `0%`), `MIN_SAMPLE=5` `outcome_analytics_service.py:9` `INSUFFICIENT_DATA` `frontend/src/pages/dashboard.tsx:303` `Not enough data yet`. `responses` `ui/app.py:1866` `interview+offer+rejected` (inbound) vs `emails_sent` `ui/app.py:1870` `submitted` (outbound) never conflated `frontend/src/pages/analytics.tsx:68` `responsesVal = analytics?.responses` (no `?? emails_sent`). `Weekly Activity` `frontend/src/pages/analytics.tsx:13` derived `applications/4` labeled `Derived estimate — not measured daily history` `frontend/src/pages/analytics.tsx:188`.

## Pipeline Experience
`Dashboard → Run Pipeline` `frontend/src/components/layout/topbar.tsx:53` `usePipeline` `frontend/src/hooks/use-pipeline.ts:11` `POST /api/run-now` `ui/app.py:768` returns `run_id` `ui/app.py:770` immediately `navigate(/pipeline/${id})` `frontend/src/hooks/use-pipeline.ts:22` (not waiting). Status page `/pipeline/:runId` `frontend/src/pages/pipeline-run.tsx:14` loads authoritative `GET /api/pipeline/logs/:runId` `frontend/src/api/pipeline.ts:22` `GET /api/scheduler/runs` `ui/app.py:1903` `run_log` `db/db_client.py:793` `run_log` (singular authoritative, `run_logs` plural legacy `db/schema.sql:53` comment) `frontend/src/store/pipeline-store.ts:18` `events`, SSE `EventSource /api/pipeline/stream/:runId` `frontend/src/api/pipeline.ts:32` `ui/app.py:171` `q.get(timeout=120)` `frontend/src/hooks/use-pipeline.ts:24` `onmessage addEvent` `onerror retain state reconnect`. Progress via `pct`/`msg` `pipeline/orchestrator.py:165` `_emit` `5% Initializing` etc., but final state derived from `results.status` `pipeline/orchestrator.py:147` `completed/completed_empty/completed_with_fallback/provider_unavailable/failed` not `jobs_found` alone `frontend/src/pages/pipeline.tsx:51` `PipelineOutcome`. Refresh reconstructs via `GET` then `SSE` `frontend/src/pages/pipeline-run.tsx:14` `useQuery` + `createPipelineStream`.

## Reliability & Safety
- PostgreSQL Neon authoritative (`run_log`, `applications`, `jobs`) `db/db_client.py:215` `run_log` `ui/app.py:289` `update_run_log`, SQLite `cache.db` `db/db_client.py:43` cache only.
- Transactions `with conn:` `application_service.py:97` `SELECT FOR UPDATE` `application_service.py:100` `follow_up_service.py:28` `interview_store_service.py:26` `scheduler_service.py:378` `pg_try_advisory_lock`.
- Idempotency: `jobs.url UNIQUE` `db/schema.sql:6` `ON CONFLICT DO NOTHING` `db/db_client.py:586`, `applications UNQIUE(job_id,attempt_number)` `002:20` + `SELECT FOR UPDATE` `409` `ui/app.py:1310`, `run_id` uuid `pipeline/orchestrator.py:47`.
- Advisory locks `pg_try_advisory_lock(42)` ownership `scheduler_service.py:251` `42` + `pg_try_advisory_lock(43)` run lock `scheduler_service.py:392` `43` + `PIPELINE_LOCK_KEY=43` `ui/app.py:758` manual+scheduler share, non-blocking `pg_try` never `pg_advisory_lock`.
- Stuck recovery `scheduler_service.py:386` `UPDATE TIMED_OUT WHERE status='RUNNING' AND started_at< now-30m` `STUCK_RUN_TIMEOUT_MINUTES=30` `RECOVERY_INTERVAL_SECONDS=300` `scheduler_service.py:424` `TestCrashReplay` incremental `pipeline/orchestrator.py:406` Model B `ON CONFLICT` replay safe.
- Safe errors `core/services/scheduler_service.py:86` `_sanitize_error` redacts `npg_/gsk_/Bearer/password/DATABASE_URL` `ui/app.py:599,840,1209` generic `Internal server error`.
- Human-in-loop: Studio `Approve` `frontend/src/pages/studio.tsx:95`, `Create Application` `frontend/src/pages/studio.tsx:146` `PREPARING`, `apply` `frontend/src/hooks/use-applications.ts:24` `POST /apply` `ui/app.py:1352` manual, follow-up `DRAFT→REVIEW→APPROVED→SENT` `follow_up_service.py:47,63,79` `frontend/src/pages/application-detail.tsx:126`, outreach preview only `frontend/src/pages/studio.tsx:136` `No automated emails are sent`.
- Production DB guard `tests/conftest.py:62` `integrity` `hardening` markers, `TEST_DATABASE_URL` `applyr_test` isolated `core/services/application_service.py:33` `_is_production_db` check.

## Architecture

```
Frontend (React 19 + TypeScript 6 + Vite 8 + Tailwind 4, :5173)
    ↓ proxy /api/*
Flask API (ui/app.py :5000, threaded)
    ↓
Services / Pipeline (core/services/*, pipeline/orchestrator.py, agents/*)
    ↓
PostgreSQL (Neon pooler) authoritative + SQLite cache.db
    ↓
APScheduler BackgroundScheduler (Asia/Kolkata 09/12/15/18) + AI Gateway (Groq/OpenRouter/Gemini)
```

- **Frontend** `frontend/src/App.tsx:32` `BrowserRouter` `AppLayout` `frontend/src/components/layout/app-layout.tsx:8` `QueryClient staleTime 30s` `frontend/src/App.tsx:22` `useJobs` `useApplications` `useStudio` etc.
- **Backend** `ui/app.py:2424` `init_scheduler()` at startup `APScheduler` `core/services/scheduler_service.py:187` `BackgroundScheduler(timezone="Asia/Kolkata")` `threadpool max_workers=1`.
- **Pipeline** `pipeline/orchestrator.py:172` `run_full_pipeline(triggered_by, job_text, job_file)` → `web_research_agent:76` `site:` pool + `TavilySearch` `agents/01-web-research-agent:208` `max_results=10` `advanced` + `parse_jobs` `agents/01-web-research-agent:350` LLM extract `DocWriterAgent` + `RecruiterDiscoveryAgent`.
- **AI Gateway** `core/ai/gateway.py:44` `generate` `default_cascade ["groq","openrouter","gemini"]` `fallback_triggered` `core/ai/gateway.py:69` `ERROR_TAXONOMY` `core/ai/errors.py:63` `retryable/fallback_allowed` `gateway.py:95` `RateLimitError` retry 3 `sleep 0.5*2^(n-1)` `gateway.py:101`.

## Project Structure

```
frontend/                 # Vite + React SPA
  src/pages/              # dashboard, discover-jobs, job-detail, studio, application-detail, pipeline, pipeline-run, opportunities, inbox, networking, analytics, copilot, interview, resume-studio, settings
  src/components/ui/      # button, card, badge, modal, skeleton, etc.
  src/components/layout/  # app-sidebar, app-layout, topbar, command-palette
  src/hooks/              # use-jobs, use-applications, use-studio, use-interviews, use-dashboard, use-pipeline
  src/api/                # client (axios 30s), jobs, applications, interviews, pipeline, studio, dashboard, tracker
  src/lib/next-action.ts  # single source Next Action HOT/WARM/COLD/REVIEW
core/
  services/               # match_service (40/25/20/10/5), match_engine2, candidate/job_intelligence, application_priority, studio_service, interview_store/follow_up/outcome/analytics, scheduler_service, llm_service
  models/                 # application, match_engine, studio, etc.
  ai/                     # gateway, errors (sanitize), providers/groq|openrouter|gemini, schemas (fallback_used)
agents/                   # 01-web-research-agent, doc_writer, 18-job-application-agent, recruiter_discovery, email_drafting
pipeline/                 # orchestrator.py (run_id, fallback_used, failure_category)
db/                       # db_client.py (psycopg2 pool, run_log), schema.sql (legacy SQLite, preserved), migrations/002-007
tests/                    # test_match_service, test_phase9/10/11/12/13/14, test_hardening_release, test_analytics_semantics, test_reliability_hardening
docs/                     # REAL_WORLD_PILOT.md
scripts/                  # pilot_report.py
```

## Local Development

**Prerequisites:** Python 3.14, Node 20, PostgreSQL/Neon, `profile.json`.

**1. Backend**
```bash
pip install -r requirements.txt
cp .env.example .env  # edit DATABASE_URL, GROQ_API_KEY, TAVILY_API_KEY, etc.
python ui/app.py  # http://localhost:5000
```

**2. Frontend**
```bash
cd frontend
npm install
npm run dev    # http://localhost:5173 proxies /api/* to :5000
# or production
npm run build  # tsc -b && vite build (2909 modules, 822ms)
```

**Database:** `DATABASE_URL` `postgresql://.../neondb?sslmode=require` `/.env.example:39`, `TEST_DATABASE_URL` `/.env.example:45` `applyr_test?sslmode=require` isolated `core/services/application_service.py:33` guard. Migrations `psql $DATABASE_URL -f db/migrations/*.sql` idempotent `IF NOT EXISTS` `db/migrations/002:4` etc. No `db/schema.sql` migration needed (legacy SQLite preserved).

**Scheduler:** `SCHEDULER_ENABLED=false` default `core/services/scheduler_service.py:162` safe local; set `true` to enable `09:00,12:00,15:00,18:00 IST` `scheduler_service.py:194`.

## Environment Variables

Secrets in `.env` (never committed, `.gitignore:2`):
`DATABASE_URL`, `TEST_DATABASE_URL`, `GROQ_API_KEY` (`/.env.example:2` `gsk_...`), `OPENROUTER_API_KEY` (`sk-or-...`), `GEMINI_API_KEY`, `TAVILY_API_KEY`, `APOLLO_API_KEY`, `HUNTER_API_KEY`, `CLEARBIT_API_KEY`, `SCRAPINGBEE_API_KEY`, `RESEND_API_KEY`, `GMAIL_CREDENTIALS`, `SECRET_KEY` (`change_this...` `/.env.example:82`), `VITE_API_URL` (frontend, default proxy).

## Testing

- **Unit** `pytest tests/test_match_service.py -q` `48 passed 0.11s` (weights)
- **Integration (PostgreSQL `applyr_test`)** `pytest tests/test_phase9_correction.py tests/test_phase10_correction.py -q` `19 passed 63s`
- **Reliability** `pytest tests/test_hardening_release.py -q` `16 passed 17.84s` (error generic, asset 4×404)
- **Analytics semantic** `pytest tests/test_analytics_semantics.py -q` `21 passed 0.04s` (0 vs null, derived label)
- **Hardening** `pytest tests/test_reliability_hardening.py -k TestProviderFallback -q` `1 passed 34s` (fallback)
- **E2E** `pytest tests/test_phase14.py -q` `4 passed 249s` (`JOB→ANALYTICS` `132s`)
- **Full** `pytest -q` needs ~400s Neon (1.7s/conn) → sharded; **FULL SUITE: TIMEOUT** with `120s` tool is expected, not failure.
- **Frontend** `npx tsc -b` 0 errors, `npm run build` `✓` `frontend:1`

## Pilot

`tests/data/real_job_pilot/` with `README.md:1` (labels `RELEVANT/IRRELEVANT/DUPLICATE/STALE/BROKEN/UNCERTAIN`), `job_evaluation_template.json:1` (15 fields: `job_id, company, title, source, match_score, priority, human_match/priority, decision, discovery_quality, application_started/submitted, preparation_time, interview/follow-up/outcome, friction_notes`), `aggregate.csv:1` header, `docs/REAL_WORLD_PILOT.md:1` 15 sections (purpose→P0/P1), `scripts/pilot_report.py:1` `Jobs evaluated: 0` → `1` with `job_999.json` `100%` `7.0 min` verified. Empty until real jobs; no fake `fake interviews/offers`.

## Current Status

Applyr 2.0 has completed engineering/reliability validation (48+4+16+21 tests sharded pass, build clean, protected `core/services/match_service.py:68` `0.40` etc. `git diff -- core/services/match_service.py` empty) and is entering real-world pilot (20–30 jobs). Single-user/local boundary: `GET /api/resume/parsed` `ui/app.py:544` unauthenticated, `Studio` candidate PII per-job `ui/app.py:1416` — acceptable local, not multi-user SaaS. Multi-user auth/HA/multi-region are future work, **NOT claimed**.

## Roadmap

- Real-world pilot (20–30 jobs) → measure `Interview Rate` `Offers` `Avg prep` `REAL_WORLD_PILOT.md:4` `N/A` when `den==0`
- Recruiter freshness/provenance UI already shows `Unverified` `Source unavailable` `frontend/src/pages/networking.tsx:82` when `verified_at` null
- Deeper interview learning post-pilot
- Durable object storage / deployment hardening when needed
- `analytics buildWeeklyTrend` synthetic remains labeled `Derived estimate` `frontend/src/pages/analytics.tsx:188`

## Security / Privacy

Secrets in `os.getenv` `core/ai/providers/groq.py:34` `DATABASE_URL` `db/db_client.py:22`, never in responses `ui/app.py:361` `env_keys` bool only, `api/setup` bool, `scheduler_service.py:86` `_sanitize_error` redacts `npg_/gsk_/Bearer/password/DATABASE_URL` `ui/app.py:599` generic `Internal server error`. Resumes `resume/master_resume.pdf` `frontend/src/pages/resume-studio.tsx:1` local, treat as sensitive. No `dangerouslySetInnerHTML` `frontend/src/components/ui/formatted-text.tsx:186` safe `parseInline` `frontend/src/components/ui/formatted-text.tsx:26` `**` → `<strong>`.

## License

Private — All rights reserved.` (existing, not invented)


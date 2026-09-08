# Real-World Pilot — Applyr 2.0

## 1. Purpose
Determine whether Applyr helps a real seeker: find better jobs, decide which to apply to, prepare faster, submit with less friction, prep better for interviews, follow up consistently, increase interviews. No new features; evidence-driven.

## 2. Pilot Scope
- 20–30 real jobs discovered via Applyr (single-user, local, PostgreSQL/Neon, Flask, Vite).
- Evaluate discovery → outcome end-to-end. Do not claim SaaS/HA/auth.

## 3. How to Run the Pilot
1. `python ui/app.py` + `cd frontend && npm run dev`
2. Upload resume → Discover → For each job: record `tests/data/real_job_pilot/job_*.json` per README before applying.
3. Use Studio → Create Application → Application → Interview/Follow-up → Outcome → Analytics.
4. `python scripts/pilot_report.py` to summarize.

## 4. Metrics
**Primary:** Applications Started, Applications Submitted, Interviews, Offers, Accepted Offers.
**Derived:**
- Application Submission Rate = submitted / started
- Interview Rate = interviews / submitted
- Offer Rate = offers / interviews
- Overall Offer Rate = offers / submitted
- Avg preparation time per submitted (and vs manual baseline if available)
- Jobs discovered, Relevant, Duplicate, Stale, Rejected after review, HOT/WARM/COLD/REVIEW applied counts.
When denominator 0 or <5 → `N/A` / `INSUFFICIENT_DATA` (never 0%).

## 5. Evaluation Rubric
Per job: `match_score` (0–100), `application_priority` (HOT/WARM/COLD/REVIEW) vs `human_match_assessment` (HIGH/MEDIUM/LOW) and `human_priority_assessment` (HOT/WARM/COLD/REVIEW). Decision `APPLY/SKIP/REVIEW` with reason. Disagreements are most valuable.

## 6. Human-vs-Applyr Comparison Method
Record both before deciding. Example:
```
JOB: ML Engineer Intern — Applyr Match 87 HOT vs Human HIGH HOT → Decision APPLY
Disagreement: Applyr 91 HOT vs Human HIGH SKIP (Location) → value: priority overweights? 
```
Compute agreement: `Applyr/Human Priority Agreement: 15/20`.

## 7. Discovery Quality Rubric
Labels: `RELEVANT, IRRELEVANT, DUPLICATE, STALE, BROKEN, UNCERTAIN`.
Check: relevance, freshness (scraped_at not last_seen_at), duplicate chain, company/role/location/salary/source/URL/actionable. Record why for each non-RELEVANT. Do not auto-tune discovery from single observations.

## 8. Studio Rubric
1 Why useful? 2 Match/Priority understandable? 3 Tailoring grounded? 4 Unsupported avoided? 5 Diff understandable? 6 ATS labeled `null` not fake? 7 Cover letter useful? 8 Recruiter preview useful? 9 Approval understandable? 10 Create obvious? 11 Post-create navigation clear? 12 Manual corrections count? 13 Time minutes.

## 9. Application Workflow Rubric
Verify: attempt created correctly, `current_state` accurate, `application_events` timeline correct, linked to correct `job_id`, interview prep links correct, follow-up lifecycle `DRAFT→REVIEW→APPROVED→SENT`, outcome recordable, no duplicate `attempt 2` on re-click, `CLOSED` terminal, reapply creates `attempt 2` with `previous_application_id`.

## 10. Interview Rubric
Specific to application? Grounded candidate facts? Questions useful? Gaps vs evidence distinguished? `UNKNOWN` preserved? Page preserves `?appId=` on refresh? Disclaimer `Likely questions` present?

## 11. Follow-up Rubric
`DRAFT` understandable (not sent)? `REVIEW` required? `APPROVED` meaningful? `SENT` distinguished? Block `DRAFT→SENT` without `APPROVED`? No auto-send.

## 12. Outcome Rubric
`OFFER` shows `Record Accepted/Rejected` manual, not auto. `CLOSED` shows `final_outcome` and `CLOSED+NONE` valid as `UNKNOWN`. `CLOSED` terminal, `timeline` + `Outcome → Analytics` link present. `OutcomeAnalytics` funnel `started/submitted/screening/interview/final/offer/accepted` zero→`null` not 0%.

## 13. Friction Logging Format
`friction_notes`: free text per job (e.g., "Studio diff hard to read", "Follow-up approve hidden").
`correctness_notes`: hallucinated claims, wrong company, stale-as-fresh.
`discovery_quality_notes`: why `IRRELEVANT` etc. Keep per `job_evaluation_template.json`.

## 14. Example Completed Evaluation
```json
{
  "job_id": 101, "company": "Acme AI", "title": "ML Engineer Intern", "source": "greenhouse.io",
  "match_score": 87, "application_priority": "HOT",
  "human_match_assessment": "HIGH", "human_priority_assessment": "HOT", "decision": "APPLY",
  "discovery_quality": "RELEVANT", "application_started": true, "application_submitted": true,
  "preparation_time_minutes": 6, "interview_received": true, "interview_prep_used": true,
  "follow_up_used": true, "final_outcome": "REJECTED",
  "friction_notes": "None", "correctness_notes": "Correct"
}
```

## 15. What Constitutes P0/P1/P2/P3
- **P0** Blocks use or unsafe wrong action (e.g., auto-send, duplicate attempt 2, `CLOSED` reopen).
- **P1** Materially harms outcome or major incorrect recommendation (false HOT for IRRELEVANT).
- **P2** Noticeable usability/product weakness (slow prep, confusing diff).
- **P3** Polish/minor (typo, spacing).

# Applyr Database Migrations — Operator Runbook

All migrations are **PostgreSQL/Neon only**, **additive**, and **idempotent**
(`IF NOT EXISTS` guards). There is **no automatic migration runner**:
application startup never executes DDL for these tables, and `db/schema.sql`
is legacy SQLite documentation — do not edit it for migration work.

## How to apply a migration

```sh
psql "$DATABASE_URL" -f db/migrations/<NNN_name>.sql
```

Use the isolated test database first:

```sh
psql "$TEST_DATABASE_URL" -f db/migrations/<NNN_name>.sql
```

Never point a migration at production without a verified test-database run.

## How to verify

```sql
SELECT EXISTS (
  SELECT FROM information_schema.tables WHERE table_name = '<table>'
);
```

Re-running a migration file must succeed without error (idempotency check).

## How to detect an incomplete/failed migration

- The verification query above returns `false`, or
- `psql` exits non-zero mid-file (earlier statements in the same `DO $$`
  block may have committed; simply re-run the file — guards make this safe).

## Pre-migration application behavior

Features backed by a not-yet-applied table fail open: API responses keep
their existing contracts (unknown/empty states), and no stack traces,
credentials, or partial writes reach the client.

---

## 012 — Opportunity Intelligence (`012_opportunity_intelligence.sql`)

1. **What it creates:** table `job_opportunity_intelligence`
   (`job_id` PK → `jobs(id)` cascade, `competition_intensity`,
   `background_fit_sensitivity`, `shortlisting_strictness`,
   `determination_status`, `evidence_json`, `confidence`, `computed_at`)
   plus index `idx_opp_intel_determination`.
2. **Why it is needed:** persists the three informational Opportunity
   Intelligence signals per canonical job so Job Details can serve them
   without recomputation. It never influences Match scores or Priority tiers.
3. **How to apply:** `psql "$DATABASE_URL" -f db/migrations/012_opportunity_intelligence.sql`
   (test DB first with `$TEST_DATABASE_URL`).
4. **How to verify:**
   ```sql
   SELECT EXISTS (
     SELECT FROM information_schema.tables
     WHERE table_name = 'job_opportunity_intelligence'
   );
   ```
   must return `true`; re-running the file must succeed.
5. **Before it is applied:** `GET /api/jobs/<id>/opportunity-intelligence`
   computes the foundation lazily per request (all `UNKNOWN` until the
   signal evaluators run) and persistence calls are skipped silently.
   `PRODUCTION MIGRATION APPLIED: NO` as of the Competition checkpoint.
6. **Incomplete/failed detection:** verification query returns `false`;
   re-run the file (safe — `IF NOT EXISTS` guards, no `DROP`, no data loss).

"""
One-time backfill — resolve bad company names already in the `jobs` table.

Companion to the Bug 5 fix (web_research_agent.parse_jobs): the fix only governs
NEW inserts, so legacy rows can still hold null / '' / 'Unknown Company'. This
script applies the SAME 3-step fallback to existing rows, in place:

    (a) company from the job URL domain (minus known job-board domains)
    (b) "at <Company>" / "<Company> - Role" parsed from the title
        -- (a) and (b) are both handled by _company_from_url(url, title)
    (c) else "Company not found" + needs_review = True

Usage:
    venv/Scripts/python.exe backfill_companies.py
"""

import importlib.util
import os
import sys

from dotenv import load_dotenv

load_dotenv()

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Load the company-name fallback fn from the web-research agent implementation
# (file name isn't a valid module identifier, so load it by path).
_IMPL = os.path.join(ROOT, "agents", "01-web-research-agent", "01_web_research_agent.py")
_spec = importlib.util.spec_from_file_location("_web_research_impl", _IMPL)
_wr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_wr)

extract_company_from_url = _wr._company_from_url   # same fn used by the live fix
_BAD = _wr._BAD_COMPANY

from db.db_client import get_db


def main():
    db = get_db()
    conn = db._conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, company, url, title FROM jobs
                WHERE company IS NULL
                   OR lower(trim(company)) IN ('', 'unknown', 'unknown company')
                ORDER BY id
            """)
            rows = cur.fetchall()

        print(f"Found {len(rows)} job row(s) with missing/unknown company\n")

        backfilled = 0
        flagged = 0
        for jid, company, url, title in rows:
            new_company = extract_company_from_url(url or "", title or "")
            new_company = str(new_company or "").strip()

            if not new_company or new_company.lower() in _BAD:
                new_company = "Company not found"
                needs_review = 1
                flagged += 1
            else:
                needs_review = 0

            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE jobs SET company = %s, needs_review = %s WHERE id = %s",
                    (new_company, needs_review, jid),
                )
            conn.commit()
            backfilled += 1
            print(f"  id {jid}: {company!r} -> {new_company!r} (needs_review={needs_review})")

        # Invalidate the cached jobs list so the UI reflects the changes immediately.
        try:
            db._disk_invalidate("all_jobs")
        except Exception:
            pass

        print(f"\nBackfilled {backfilled} row(s); "
              f"{flagged} could not be resolved -> 'Company not found' + needs_review.")
    finally:
        db._put_conn(conn)


if __name__ == "__main__":
    main()

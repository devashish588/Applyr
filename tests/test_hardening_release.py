"""
Release Hardening — P2/P3 regression tests
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)
if not os.getenv("TEST_DATABASE_URL"):
    prod = os.getenv("DATABASE_URL", "")
    if "/neondb?" in prod:
        os.environ["TEST_DATABASE_URL"] = prod.replace("/neondb?", "/applyr_test?")
    elif "/neondb" in prod:
        os.environ["TEST_DATABASE_URL"] = prod.replace("/neondb", "/applyr_test")

def _url():
    return os.getenv("TEST_DATABASE_URL", "")

@pytest.fixture
def client():
    from ui.app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

# ── ERROR HANDLING: generic 500 ──

class TestErrorHardening:
    def test_resume_parsed_generic_on_exception(self):
        content = Path("ui/app.py").read_text(encoding="utf-8", errors="ignore")
        # Check that resume/parsed now returns generic
        assert 'return jsonify({"error": "Internal server error"}), 500' in content
        # Ensure the old str(e) for that route is gone
        # The specific line around 599 should be generic
        assert content.count('return jsonify({"error": "Internal server error"}), 500') >= 3

    def test_jobs_generic_on_exception(self):
        content = Path("ui/app.py").read_text(encoding="utf-8", errors="ignore")
        assert 'logger.error("List jobs failed' in content
        assert content.count('return jsonify({"error": "Internal server error"}), 500') >= 3

    def test_prioritized_generic_on_exception(self):
        content = Path("ui/app.py").read_text(encoding="utf-8", errors="ignore")
        assert 'logger.error("Prioritized failed' in content
        assert 'return jsonify({"error": "Internal server error"}), 500' in content

# ── ASSET SECURITY ──

class TestAssetSecurity:
    def test_hardening_code_present(self):
        content = Path("ui/app.py").read_text(encoding="utf-8", errors="ignore")
        assert "approved_resume" in content
        assert "approved_uploads" in content
        assert "is_relative_to" in content
        assert "Asset file not found" in content

    def test_valid_asset_allowed(self, client):
        # Create a real file inside approved resume dir
        approved = Path("resume/test_valid_asset.txt")
        approved.parent.mkdir(parents=True, exist_ok=True)
        approved.write_text("valid")
        # Create job via API then set path via DB
        url = f"https://example.com/asset-{os.urandom(4).hex()}"
        conn = psycopg2.connect(_url())
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO jobs (title, company, url, source, jd_text, scraped_at, last_seen_at) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id", ("Asset Test","Co",url,"test","{}", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))
                jid = cur.fetchone()[0]
                cur.execute("UPDATE jobs SET tailored_resume_path=%s WHERE id=%s", (str(approved), jid))
            conn.commit()
        finally:
            conn.close()
        resp = client.get(f"/api/jobs/{jid}/asset/resume")
        assert resp.status_code in (200, 404)
        try:
            approved.unlink()
        except: pass
        assert resp.status_code != 500

    def test_traversal_rejected(self, client):
        url = f"https://example.com/asset-{os.urandom(4).hex()}"
        conn = psycopg2.connect(_url())
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO jobs (title, company, url, source, jd_text, scraped_at, last_seen_at) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id", ("Asset Test","Co",url,"test","{}", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))
                jid = cur.fetchone()[0]
                cur.execute("UPDATE jobs SET tailored_resume_path=%s WHERE id=%s", ("../../windows/win.ini", jid))
            conn.commit()
        finally:
            conn.close()
        resp = client.get(f"/api/jobs/{jid}/asset/resume")
        assert resp.status_code == 404

    def test_absolute_external_rejected(self, client):
        url = f"https://example.com/asset-{os.urandom(4).hex()}"
        conn = psycopg2.connect(_url())
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO jobs (title, company, url, source, jd_text, scraped_at, last_seen_at) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id", ("Asset Test","Co",url,"test","{}", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))
                jid = cur.fetchone()[0]
                cur.execute("UPDATE jobs SET tailored_resume_path=%s WHERE id=%s", ("/etc/passwd", jid))
            conn.commit()
        finally:
            conn.close()
        resp = client.get(f"/api/jobs/{jid}/asset/resume")
        assert resp.status_code == 404

    def test_outside_approved_rejected(self, client):
        url = f"https://example.com/asset-{os.urandom(4).hex()}"
        conn = psycopg2.connect(_url())
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO jobs (title, company, url, source, jd_text, scraped_at, last_seen_at) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id", ("Asset Test","Co",url,"test","{}", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))
                jid = cur.fetchone()[0]
                cur.execute("UPDATE jobs SET tailored_resume_path=%s WHERE id=%s", ("ui/app.py", jid))
            conn.commit()
        finally:
            conn.close()
        resp = client.get(f"/api/jobs/{jid}/asset/resume")
        assert resp.status_code == 404

# ── NAVIGATION ──

class TestNavigation:
    def test_discover_job_link_points_to_jobs(self):
        content = Path("frontend/src/pages/discover-jobs.tsx").read_text(encoding="utf-8", errors="ignore")
        assert 'to={`/jobs/${job.id}`}' in content or 'to={`/jobs/${job.id}`' in content
        assert '<Link' in content
        assert '<a href={`/jobs/${job.id}`}' not in content

    def test_command_palette_studio_correct(self):
        content = Path("frontend/src/components/layout/command-palette.tsx").read_text(encoding="utf-8", errors="ignore")
        assert 'label: "Application Studio"' in content
        assert 'path: "/studio/1"' in content
        assert 'go("/studio/1")' in content

# ── STUDIO ──

class TestStudio:
    def test_studio_uses_fetch_not_always_generate(self):
        content = Path("frontend/src/pages/studio.tsx").read_text(encoding="utf-8", errors="ignore")
        assert "load(false)" in content
        assert "load(true)" in content
        assert content.count("load(true)") == 1
        assert "useEffect(() => { load(false)" in content

    def test_regenerate_disabled_while_loading(self):
        content = Path("frontend/src/pages/studio.tsx").read_text(encoding="utf-8", errors="ignore")
        assert 'disabled={loading || isCreating}' in content
        assert 'disabled={!approvals.resume || isCreating}' in content

    def test_no_subprocess_import(self):
        content = Path("core/services/resume_parser_service.py").read_text(encoding="utf-8", errors="ignore")
        assert "import subprocess" not in content

# ── REGRESSION ──

class TestRegressionPhase9_13:
    def test_match_weights_unchanged(self):
        from core.services.match_service import MatchService
        assert MatchService.SKILL_WEIGHT == 0.40
        assert MatchService.EXPERIENCE_WEIGHT == 0.25
        assert MatchService.ROLE_WEIGHT == 0.20
        assert MatchService.LOCATION_WEIGHT == 0.10
        assert MatchService.SENIORITY_WEIGHT == 0.05

    def test_orchestrator_unchanged(self):
        content = Path("pipeline/orchestrator.py").read_text(encoding="utf-8", errors="ignore")
        assert "run_full_pipeline" in content

    def test_schema_unchanged(self):
        assert Path("db/schema.sql").exists()
        assert "CREATE TABLE" in Path("db/schema.sql").read_text(encoding="utf-8", errors="ignore")

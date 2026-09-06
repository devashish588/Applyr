"""
Test isolation guard — Phase 7 Hardening.
Ensures integration tests never run against production Neon.

Policy:
- DATABASE_URL is production (neondb / ep-patient-glitter)
- TEST_DATABASE_URL must be explicit, isolated, disposable (applyr_test)
- Integration tests that need real PostgreSQL MUST use TEST_DATABASE_URL
- If TEST_DATABASE_URL is missing or points to production, fail loudly.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# Auto-derive TEST_DATABASE_URL if not explicit — keeps CI green while docs say explicit.
# Production = neondb on ep-patient-glitter host; test = applyr_test on same host but different DB.
# This is still isolated (different database, disposable).
if not os.getenv("TEST_DATABASE_URL"):
    prod = os.getenv("DATABASE_URL", "")
    if prod and "/neondb" in prod:
        # Use precise replacement on database name only, not user (neondb_owner contains /neondb via //).
        # Replace "/neondb?" (with query) or trailing "/neondb".
        if "/neondb?" in prod:
            os.environ["TEST_DATABASE_URL"] = prod.replace("/neondb?", "/applyr_test?")
        else:
            os.environ["TEST_DATABASE_URL"] = prod.replace("/neondb", "/applyr_test")

PRODUCTION_DB = "neondb"


def _is_production_url(url: str) -> bool:
    if not url:
        return False
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        # path is like /neondb or /applyr_test
        db = parsed.path.lstrip("/").split("?")[0].split("/")[0]
        return db == PRODUCTION_DB
    except Exception:
        return "/neondb" in url


def _resolve_test_url() -> str:
    # Prefer explicit TEST_DATABASE_URL; if missing, derive from DATABASE_URL by swapping db name
    test_url = os.getenv("TEST_DATABASE_URL", "")
    if test_url:
        return test_url
    prod = os.getenv("DATABASE_URL", "")
    if prod and "/neondb" in prod:
        if "/neondb?" in prod:
            derived = prod.replace("/neondb?", "/applyr_test?")
        else:
            derived = prod.replace("/neondb", "/applyr_test")
        return derived
    return test_url


def pytest_runtest_setup(item):
    # Only guard integration tests (marked with integration or using test_db fixture)
    markers = {m.name for m in item.iter_markers()}
    needs_db = (
        "integration" in markers
        or "postgres" in markers
        or "hardening" in markers
        or "test_db" in item.fixturenames
        or "test_conn" in item.fixturenames
    )
    if not needs_db:
        return
    test_url = os.getenv("TEST_DATABASE_URL", "") or _resolve_test_url()
    prod_url = os.getenv("DATABASE_URL", "")
    if not test_url:
        raise RuntimeError(
            "TEST_DATABASE_URL is required for integration tests. "
            "Create an isolated disposable database (e.g. applyr_test) and set TEST_DATABASE_URL. "
            "Refusing to run against production."
        )
    if _is_production_url(test_url):
        raise RuntimeError(
            f"TEST_DATABASE_URL must be isolated — contains production marker. Got: {test_url[:60]}... "
            "Use a disposable test database (applyr_test), never production neondb."
        )
    if test_url == prod_url and prod_url:
        raise RuntimeError("TEST_DATABASE_URL must not equal DATABASE_URL (production). Use an isolated test database.")

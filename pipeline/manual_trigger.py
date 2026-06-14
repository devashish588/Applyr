"""
Manual Trigger — AutoApply AI
Runs the full pipeline immediately on demand.
Supports: pasted JD text, uploaded PDF, URL, or full discovery run.

Usage:
    python pipeline/manual_trigger.py --run-now
    python pipeline/manual_trigger.py --file ./uploads/jd_pdfs/stripe.pdf
    python pipeline/manual_trigger.py --text "Senior Python Engineer at Stripe..."
    python pipeline/manual_trigger.py --url "https://jobs.stripe.com/..."
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Make project root importable ─────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.orchestrator import Orchestrator

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def trigger_manual_run(job_text: str = None, job_file: str = None) -> dict:
    """
    Trigger a manual pipeline run.

    Args:
        job_text: JD text pasted by user
        job_file: Path to JD PDF uploaded by user

    Returns:
        Pipeline results dict
    """
    logger.info("Manual trigger initiated")

    if job_text:
        logger.info(f"Processing pasted JD ({len(job_text)} chars)")
    elif job_file:
        if not os.path.exists(job_file):
            logger.error(f"File not found: {job_file}")
            return {"status": "failed", "errors": [f"File not found: {job_file}"]}
        logger.info(f"Processing uploaded file: {job_file}")
    else:
        logger.info("Running full discovery pipeline")

    orchestrator = Orchestrator()
    results      = orchestrator.run_full_pipeline(
        triggered_by = "manual",
        job_text     = job_text,
        job_file     = job_file,
    )
    orchestrator.save_run_summary()
    return results


def fetch_jd_from_url(url: str) -> str | None:
    """
    Fetch and extract JD text from a URL using web research agent.
    Falls back to simple requests if agent not available.
    """
    try:
        # Try with requests + basic text extraction first (no extra dependency)
        import requests
        from bs4 import BeautifulSoup

        headers = {"User-Agent": "Mozilla/5.0 (compatible; AutoApply/1.0)"}
        resp    = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove nav/footer/script noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # Trim to reasonable JD size
        return text[:5000]

    except ImportError:
        logger.warning("beautifulsoup4 not installed — install with: pip install beautifulsoup4 requests")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch URL {url}: {e}")
        return None


def print_results(results: dict):
    print(f"\n{'='*60}")
    print("PIPELINE RESULTS")
    print(f"{'='*60}")
    print(f"Triggered by:   {results.get('triggered_by', 'N/A')}")
    print(f"Status:         {results.get('status', 'N/A')}")
    print(f"Jobs Found:     {results.get('jobs_found', 0)}")
    print(f"Jobs Filtered:  {results.get('jobs_filtered', 0)}")
    print(f"Jobs Applied:   {results.get('jobs_applied', 0)}")
    print(f"Emails Sent:    {results.get('emails_sent', 0)}")
    print(f"Skipped:        {results.get('skipped', 0)}")

    apps = results.get("applications", [])
    if apps:
        print(f"\n{'-'*60}")
        print(f"Applications ({len(apps)}):")
        for app in apps:
            icon = "[SENT]" if app["status"] == "sent" else "[DRAFT]"
            print(f"  {icon} {app['title']} at {app['company']} "
                  f"- score {app['fit_score']}/100 [{app['status']}]")

    errors = results.get("errors", [])
    if errors:
        print(f"\n{'-'*60}")
        print(f"Errors ({len(errors)}):")
        for err in errors[:5]:
            print(f"  x {err}")

    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="AutoApply — Manual pipeline trigger",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Run full discovery pipeline now:
    python pipeline/manual_trigger.py --run-now

  Process an uploaded JD PDF:
    python pipeline/manual_trigger.py --file ./uploads/jd_pdfs/stripe.pdf

  Paste JD text directly:
    python pipeline/manual_trigger.py --text "Senior Python Engineer at Stripe..."

  Process a job posting URL:
    python pipeline/manual_trigger.py --url "https://stripe.com/jobs/123"
        """
    )
    parser.add_argument("--run-now", action="store_true",
                        help="Run full discovery pipeline immediately")
    parser.add_argument("--file",    help="Path to JD PDF file")
    parser.add_argument("--text",    help="Raw JD text")
    parser.add_argument("--url",     help="URL of job posting")
    args = parser.parse_args()

    if not any([args.run_now, args.file, args.text, args.url]):
        parser.print_help()
        return

    # ── URL mode ──────────────────────────────────────────────────────────────
    if args.url:
        logger.info(f"Fetching JD from URL: {args.url}")
        jd_text = fetch_jd_from_url(args.url)
        if jd_text:
            results = trigger_manual_run(job_text=jd_text)
        else:
            print("❌ Failed to extract JD from URL")
            print("   Try downloading the page as a PDF and using --file instead")
            return

    # ── File, text, or full run ───────────────────────────────────────────────
    else:
        results = trigger_manual_run(
            job_text = args.text,
            job_file = args.file,
        )

    print_results(results)


if __name__ == "__main__":
    main()
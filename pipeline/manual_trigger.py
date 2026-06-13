"""
Manual trigger - for when user uploads a JD or requests an immediate run.
Supports: --run-now, --text, --file, --url
"""
import os
import sys
import logging
import argparse
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def trigger_manual_run(job_text: str = None, job_file: str = None) -> dict:
    """Trigger manual pipeline run.

    Args:
        job_text: Direct JD text pasted by user
        job_file: Path to JD PDF/image file uploaded by user

    Returns:
        Pipeline results dict
    """
    logger.info("Manual trigger initiated")

    if job_text:
        logger.info(f"Processing pasted JD ({len(job_text)} chars)")
    elif job_file:
        logger.info(f"Processing uploaded file: {job_file}")
    else:
        logger.info("Running full discovery pipeline")

    orchestrator = Orchestrator()
    results = orchestrator.run_full_pipeline(
        triggered_by="manual",
        job_text=job_text,
        job_file=job_file
    )
    orchestrator.save_run_summary()

    return results


def main():
    parser = argparse.ArgumentParser(description="Manually trigger the Applyr pipeline")
    parser.add_argument("--text", help="JD text to process")
    parser.add_argument("--file", help="Path to JD PDF/image file")
    parser.add_argument("--url", help="URL of job posting")
    parser.add_argument("--run-now", action="store_true", help="Run full pipeline immediately")

    args = parser.parse_args()

    if args.url:
        # Fetch JD from URL
        from agents.pdf_qa_agent import PDFQAAgent
        agent = PDFQAAgent()
        jd_text = agent.extract_jd_from_url(args.url)
        if jd_text:
            results = trigger_manual_run(job_text=jd_text)
        else:
            print("❌ Failed to extract JD from URL")
            return
    elif args.text or args.file or args.run_now:
        results = trigger_manual_run(job_text=args.text, job_file=args.file)
    else:
        parser.print_help()
        return

    print(f"\n{'='*60}")
    print("PIPELINE RESULTS")
    print(f"{'='*60}")
    print(f"Jobs Found:     {results['jobs_found']}")
    print(f"Jobs Filtered:  {results['jobs_filtered']}")
    print(f"Jobs Applied:   {results['jobs_applied']}")
    print(f"Emails Sent:    {results['emails_sent']}")
    print(f"Status:         {results['status']}")
    if results.get('errors'):
        print(f"Errors:         {len(results['errors'])}")
        for err in results['errors'][:5]:
            print(f"  - {err}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

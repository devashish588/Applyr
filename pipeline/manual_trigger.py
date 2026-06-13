"""
Manual trigger - for when user uploads a JD or requests an immediate run
"""
import os
import sys
import logging
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def trigger_manual_run(job_text: str = None, job_file: str = None) -> dict:
    """
    Trigger manual pipeline run.
    
    Args:
        job_text: Direct JD text pasted by user
        job_file: Path to JD PDF/image file uploaded by user
    
    Returns:
        Pipeline results
    """
    logger.info("Manual trigger initiated")
    
    if job_text:
        logger.info(f"Processing pasted JD (length: {len(job_text)} chars)")
    elif job_file:
        logger.info(f"Processing uploaded file: {job_file}")
    else:
        logger.info("Running full pipeline without additional input")
    
    # Run orchestrator
    orchestrator = Orchestrator()
    results = orchestrator.run_full_pipeline(triggered_by="manual")
    orchestrator.save_run_summary()
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Manually trigger the Applyr pipeline")
    parser.add_argument("--text", help="JD text to process")
    parser.add_argument("--file", help="Path to JD PDF/image file")
    parser.add_argument("--run-now", action="store_true", help="Run full pipeline immediately")
    
    args = parser.parse_args()
    
    if args.text or args.file or args.run_now:
        results = trigger_manual_run(job_text=args.text, job_file=args.file)
        
        print("\n" + "="*50)
        print("MANUAL RUN RESULTS")
        print("="*50)
        print(f"Jobs Found:     {results['jobs_found']}")
        print(f"Jobs Filtered:  {results['jobs_filtered']}")
        print(f"Jobs Applied:   {results['jobs_applied']}")
        print(f"Emails Sent:    {results['emails_sent']}")
        print(f"Status:         {results['status']}")
        print("="*50)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

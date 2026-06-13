"""
Scheduler - runs the pipeline on schedule (9 AM + every 3 hours)
Uses APScheduler for robust scheduling
"""
import logging
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PipelineScheduler:
    """Manages scheduled execution of the pipeline."""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.configure(
            jobstores={'default': {'type': 'memory'}},
            executors={'default': {'type': 'threading', 'max_workers': 1}},
            job_defaults={'coalesce': True, 'max_instances': 1}
        )
    
    def add_morning_run(self):
        """Add 9 AM daily run."""
        self.scheduler.add_job(
            self._run_pipeline,
            trigger=CronTrigger(hour=9, minute=0),
            id='morning_run_9am',
            name='Daily 9 AM pipeline run',
            replace_existing=True
        )
        logger.info("Added 9 AM daily pipeline run")
    
    def add_every_3_hours_run(self):
        """Add every 3 hours recurring run."""
        self.scheduler.add_job(
            self._run_pipeline,
            trigger=IntervalTrigger(hours=3),
            id='every_3_hours_run',
            name='Every 3 hours pipeline run',
            replace_existing=True
        )
        logger.info("Added every 3 hours pipeline run")
    
    def _run_pipeline(self):
        """Execute the pipeline."""
        logger.info("="*60)
        logger.info(f"Pipeline triggered at {datetime.now().isoformat()}")
        logger.info("="*60)
        
        try:
            orchestrator = Orchestrator()
            results = orchestrator.run_full_pipeline(triggered_by="scheduler")
            orchestrator.save_run_summary()
            
            logger.info(f"Pipeline Results:")
            logger.info(f"  Jobs Found:     {results['jobs_found']}")
            logger.info(f"  Jobs Filtered:  {results['jobs_filtered']}")
            logger.info(f"  Jobs Applied:   {results['jobs_applied']}")
            logger.info(f"  Emails Sent:    {results['emails_sent']}")
            logger.info(f"  Errors:         {len(results['errors'])}")
            logger.info(f"  Status:         {results['status']}")
            
            if results['errors']:
                logger.warning("Errors encountered:")
                for error in results['errors']:
                    logger.warning(f"  - {error}")
        
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
    
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.add_morning_run()
            self.add_every_3_hours_run()
            self.scheduler.start()
            logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    def get_jobs(self):
        """Get all scheduled jobs."""
        return self.scheduler.get_jobs()
    
    def list_jobs(self):
        """Print all scheduled jobs."""
        jobs = self.get_jobs()
        logger.info(f"Total scheduled jobs: {len(jobs)}")
        for job in jobs:
            logger.info(f"  - {job.name} (id: {job.id}, trigger: {job.trigger})")


def start_scheduler():
    """Start the background scheduler."""
    scheduler = PipelineScheduler()
    scheduler.start()
    
    # Keep the scheduler running
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler.stop()


if __name__ == "__main__":
    start_scheduler()

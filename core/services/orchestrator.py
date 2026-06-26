"""
Pipeline Orchestration Service for Applyr AI job application platform.

This service orchestrates the entire job application pipeline,
managing the flow of jobs through the different stages.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from core.models import (
    Resume, Profile, Job, Company, Recruiter, Email, Application,
    PipelineRun, SearchStrategy, PipelineEvent, Status
)
from core.services import get_profile_service, get_company_service, get_event_bus

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Service for orchestrating the job application pipeline."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.event_bus = get_event_bus()
        self.profile_service = get_profile_service()
        self.company_service = get_company_service()

    def run_pipeline(self, triggered_by: str = "manual", job_text: Optional[str] = None, job_file: Optional[str] = None) -> PipelineRun:
        """
        Run the complete job application pipeline.

        Args:
            triggered_by: How the pipeline was triggered
            job_text: Optional job description text
            job_file: Optional job description file

        Returns:
            PipelineRun object representing the pipeline execution
        """
        run_id = str(uuid.uuid4())[:8]
        self.logger.info(f"Starting pipeline {run_id} (triggered by: {triggered_by})")

        # Create pipeline run
        run = PipelineRun(
            run_id=run_id,
            triggered_by=triggered_by,
            started_at=datetime.now().isoformat(),
            status="running",
        )

        # Publish pipeline started event
        self.event_bus.publish(
            event_type="pipeline_started",
            data={"run_id": run_id, "triggered_by": triggered_by},
            source="orchestrator",
            run_id=run_id,
        )

        try:
            # Step 1: Resume validation
            self._validate_resume(run_id)

            # Step 2: Profile creation
            profile = self._create_profile(run_id)

            # Step 3: Search strategy creation
            search_strategy = self._create_search_strategy(profile, run_id)

            # Step 4: Job discovery
            jobs = self._discover_jobs(search_strategy, job_text, job_file, run_id)

            # Step 5: Process jobs
            self._process_jobs(jobs, profile, run_id)

            # Step 6: Finalize pipeline
            run = self._finalize_pipeline(run, run_id)

            # Publish pipeline completed event
            self.event_bus.publish(
                event_type="pipeline_completed",
                data=run.dict(),
                source="orchestrator",
                run_id=run_id,
            )

            self.logger.info(f"Pipeline {run_id} completed successfully")
            return run

        except Exception as e:
            self.logger.error(f"Pipeline {run_id} failed: {e}", exc_info=True)

            # Publish pipeline error event
            self.event_bus.publish(
                event_type="pipeline_error",
                data={"error": str(e), "run_id": run_id},
                source="orchestrator",
                run_id=run_id,
            )

            # Update pipeline run with error
            run.status = "failed"
            run.errors.append(str(e))
            run.finished_at = datetime.now().isoformat()

            return run

    def _validate_resume(self, run_id: str) -> None:
        """
        Validate resume data.

        Args:
            run_id: Pipeline run ID

        Raises:
            ValueError: If resume validation fails
        """
        self.logger.info(f"Validating resume for pipeline {run_id}")

        # Get resume data from database
        from db.db_client import get_db
        db = get_db()
        resume_data = db.get_resume_data()

        if not resume_data:
            raise ValueError("No resume uploaded")

        if resume_data.get("parse_status") != "success":
            raise ValueError(f"Resume parsing failed: {resume_data.get('parse_error', 'Unknown error')}")

        # Parse resume JSON
        parsed_resume = resume_data.get("parsed_json", {})
        resume = Resume(**parsed_resume)

        # Validate resume
        if not resume.name:
            raise ValueError("Resume name is missing")

        if not resume.skills:
            raise ValueError("Resume skills are missing")

        if not resume.experience:
            raise ValueError("Resume experience is missing")

        if not resume.education:
            raise ValueError("Resume education is missing")

        # Publish resume validation event
        self.event_bus.publish(
            event_type="resume_parsed",
            data=resume.dict(),
            source="orchestrator",
            run_id=run_id,
        )

        self.logger.info(f"Resume validation passed for pipeline {run_id}")

    def _create_profile(self, run_id: str) -> Profile:
        """
        Create profile from resume data.

        Args:
            run_id: Pipeline run ID

        Returns:
            Profile object
        """
        self.logger.info(f"Creating profile for pipeline {run_id}")

        # Get resume data from database
        from db.db_client import get_db
        db = get_db()
        resume_data = db.get_resume_data()

        if not resume_data:
            raise ValueError("No resume data available")

        # Parse resume JSON
        parsed_resume = resume_data.get("parsed_json", {})
        resume = Resume(**parsed_resume)

        # Create profile from resume
        profile = self.profile_service.create_profile_from_resume(resume)

        # Validate profile
        errors = self.profile_service.validate_profile(profile)
        if errors:
            raise ValueError(f"Profile validation failed: {'; '.join(errors)}")

        # Publish profile created event
        self.event_bus.publish(
            event_type="profile_created",
            data=profile.dict(),
            source="orchestrator",
            run_id=run_id,
        )

        self.logger.info(f"Profile created for pipeline {run_id}")
        return profile

    def _create_search_strategy(self, profile: Profile, run_id: str) -> SearchStrategy:
        """
        Create search strategy from profile.

        Args:
            profile: Profile object
            run_id: Pipeline run ID

        Returns:
            SearchStrategy object
        """
        self.logger.info(f"Creating search strategy for pipeline {run_id}")

        # Create search strategy
        search_strategy = SearchStrategy(
            roles=profile.inferred_roles,
            locations=profile.target_locations,
            keywords=profile.keywords,
            query=f"({' OR '.join(f'\"{role}\"' for role in profile.inferred_roles[:4])}) {' '.join(profile.keywords[:8])} {profile.target_locations[0] if profile.target_locations else 'Remote'} jobs 2026",
            source="profile",
        )

        # Publish search started event
        self.event_bus.publish(
            event_type="search_started",
            data=search_strategy.dict(),
            source="orchestrator",
            run_id=run_id,
        )

        self.logger.info(f"Search strategy created for pipeline {run_id}")
        return search_strategy

    def _discover_jobs(self, search_strategy: SearchStrategy, job_text: Optional[str], job_file: Optional[str], run_id: str) -> List[Job]:
        """
        Discover jobs based on search strategy.

        Args:
            search_strategy: Search strategy object
            job_text: Optional job description text
            job_file: Optional job description file
            run_id: Pipeline run ID

        Returns:
            List of Job objects
        """
        self.logger.info(f"Discovering jobs for pipeline {run_id}")

        # Get jobs from web research agent
        from agents.web_research_agent import build_graph
        graph = build_graph()

        # Prepare state for web research
        state = {
            "query": search_strategy.query,
            "profile": {"job_preferences": {"target_roles": search_strategy.roles}},
            "resume_data": {},
            "messages": [],
            "search_results": [],
            "job_listings": [],
            "report": "",
        }

        # Invoke web research
        result = graph.invoke(state)
        jobs = result.get("job_listings", [])

        # Convert to Job objects
        job_objects = []
        for job_data in jobs:
            job = Job(**job_data)
            job_objects.append(job)

        # Publish jobs found event
        self.event_bus.publish(
            event_type="jobs_found",
            data={"jobs": [job.dict() for job in job_objects], "count": len(job_objects)},
            source="orchestrator",
            run_id=run_id,
        )

        self.logger.info(f"Discovered {len(job_objects)} jobs for pipeline {run_id}")
        return job_objects

    def _process_jobs(self, jobs: List[Job], profile: Profile, run_id: str) -> None:
        """
        Process jobs through the pipeline.

        Args:
            jobs: List of Job objects
            profile: Profile object
            run_id: Pipeline run ID
        """
        self.logger.info(f"Processing {len(jobs)} jobs for pipeline {run_id}")

        # Process each job
        for job in jobs:
            self._process_single_job(job, profile, run_id)

    def _process_single_job(self, job: Job, profile: Profile, run_id: str) -> None:
        """
        Process a single job through the pipeline.

        Args:
            job: Job object
            profile: Profile object
            run_id: Pipeline run ID
        """
        self.logger.info(f"Processing job: {job.title} at {job.company} for pipeline {run_id}")

        # Extract and enrich company
        company_name, confidence = self.company_service.extract_company_from_job(job)
        if company_name:
            company = self.company_service.enrich_company(company_name, confidence)

            # Publish company extracted event
            self.event_bus.publish(
                event_type="company_extracted",
                data=company.dict(),
                source="orchestrator",
                run_id=run_id,
            )

            # Validate company
            errors = self.company_service.validate_company(company)
            if errors:
                self.logger.warning(f"Company validation failed: {'; '.join(errors)}")
            else:
                # Publish company enriched event
                self.event_bus.publish(
                    event_type="company_enriched",
                    data=company.dict(),
                    source="orchestrator",
                    run_id=run_id,
                )

        # TODO: Add job processing logic (scoring, tailoring, etc.)
        # This would involve calling the job application agent

        self.logger.info(f"Completed processing job: {job.title} at {job.company} for pipeline {run_id}")

    def _finalize_pipeline(self, run: PipelineRun, run_id: str) -> PipelineRun:
        """
        Finalize pipeline execution.

        Args:
            run: PipelineRun object
            run_id: Pipeline run ID

        Returns:
            Updated PipelineRun object
        """
        run.finished_at = datetime.now().isoformat()
        run.status = "completed"

        self.logger.info(f"Pipeline {run_id} finalized")
        return run


# Singleton instance
_orchestrator = None


def get_orchestrator() -> PipelineOrchestrator:
    """Get the singleton PipelineOrchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PipelineOrchestrator()
    return _orchestrator
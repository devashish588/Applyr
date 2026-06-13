"""
Job application agent - Filters and ranks jobs by fit score
TODO: Use orchestrator's fit_scorer to rank jobs, then coordinates form filling
"""


class JobApplicationAgent:
    """Filters jobs by fit and coordinates application submission."""
    
    def __init__(self):
        pass
    
    def filter_and_rank_jobs(self, jobs: list, min_score: int = 50) -> list:
        """
        Filter jobs by fit score and rank by best matches.
        
        Args:
            jobs: List of job objects
            min_score: Minimum fit score threshold (0-100)
        
        Returns:
            Filtered & ranked jobs (highest score first)
        """
        # TODO: Use fit_scorer to rank jobs
        return []
    
    def apply_to_job(self, job_data: dict) -> bool:
        """
        Attempt to apply to job.
        May fill forms, send emails, or record application.
        
        Args:
            job_data: Job details with fit_score
        
        Returns:
            True if application successful
        """
        # TODO: Coordinate form filling, email sending, etc.
        return False
    
    def detect_apply_method(self, job_url: str) -> str:
        """
        Detect how to apply (email, form, external portal, etc.)
        
        Args:
            job_url: URL to job posting
        
        Returns:
            "email", "form", "external_portal", "unknown"
        """
        # TODO: Detect application method
        return "unknown"

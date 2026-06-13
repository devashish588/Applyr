"""
Job Application Agent — bridge module.
Re-exports from agents/18-job-application-agent/18_job_application_agent.py
"""
import importlib.util
import os

_path = os.path.join(os.path.dirname(__file__),
                     "18-job-application-agent", "18_job_application_agent.py")
_spec = importlib.util.spec_from_file_location("_job_application_impl", _path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export everything the orchestrator needs
JobApplicationAgent = _mod.JobApplicationAgent
main = _mod.main

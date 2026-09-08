"""
Web Research Agent — bridge module.
Re-exports from agents/01-web-research-agent/01_web_research_agent.py
"""
import importlib.util
import os
import sys

# Ensure the project root (one level up) is on the import path so that
# modules like ``utils.llm_client`` can be resolved when this bridge is
# executed directly.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

_path = os.path.join(os.path.dirname(__file__),
                     "01-web-research-agent", "01_web_research_agent.py")
_spec = importlib.util.spec_from_file_location("_web_research_impl", _path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export everything the orchestrator needs
build_graph = _mod.build_graph
ResearchState = _mod.ResearchState
build_query = _mod.build_query
search_web = _mod.search_web
parse_jobs = _mod.parse_jobs
generate_report = _mod.generate_report
main = _mod.main
# Adapters need low-level helpers for per-source search
_run_tavily = getattr(_mod, "_run_tavily", None)
_extract_job_listings = getattr(_mod, "_extract_job_listings", None)
_JOB_SITE_POOL = getattr(_mod, "_JOB_SITE_POOL", [])

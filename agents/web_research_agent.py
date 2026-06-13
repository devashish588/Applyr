"""
Web Research Agent — bridge module.
Re-exports from agents/01-web-research-agent/01_web_research_agent.py
"""
import importlib.util
import os

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

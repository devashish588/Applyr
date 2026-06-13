"""
Resume Parser Agent — bridge module.
Re-exports from agents/09-resume-parser-agent/09_resume_parser_agent.py
"""
import importlib.util
import os

_path = os.path.join(os.path.dirname(__file__),
                     "09-resume-parser-agent", "09_resume_parser_agent.py")
_spec = importlib.util.spec_from_file_location("_resume_parser_impl", _path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export
ResumeParserAgent = _mod.ResumeParserAgent

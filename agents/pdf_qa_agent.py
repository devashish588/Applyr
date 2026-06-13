"""
PDF QA Agent — bridge module.
Re-exports from agents/03-pdf-qa-agent/03_pdf_qa_agent.py
"""
import importlib.util
import os

_path = os.path.join(os.path.dirname(__file__),
                     "03-pdf-qa-agent", "03_pdf_qa_agent.py")
_spec = importlib.util.spec_from_file_location("_pdf_qa_impl", _path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export everything the orchestrator needs
extract_jd_info = _mod.extract_jd_info
build_index = _mod.build_index
interactive_qa = _mod.interactive_qa
single_question = _mod.single_question
main = _mod.main

"""
Email Drafting Agent — bridge module.
Re-exports from agents/05-email-drafting-agent/05_email_drafting_agent.py
"""
import importlib.util
import os

_path = os.path.join(os.path.dirname(__file__),
                     "05-email-drafting-agent", "05_email_drafting_agent.py")
_spec = importlib.util.spec_from_file_location("_email_drafting_impl", _path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export
EmailDraftingAgent = _mod.EmailDraftingAgent

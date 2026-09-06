import pytest
from core.services.copilot_service import CopilotService

def test_copilot_greeting_on_empty_message():
    svc = CopilotService()
    res = svc.ask_copilot("")
    assert "Career Copilot" in res["message"]
    assert len(res["suggestions"]) > 0

def test_copilot_heuristic_fallback():
    svc = CopilotService()
    res = svc._heuristic_fallback("resume tips")
    assert "Resume Tip" in res["message"]
    assert res["action_type"] == "fallback"

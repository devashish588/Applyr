import pytest
from core.services.interview_service import InterviewService

def test_heuristic_prep_kit():
    svc = InterviewService()
    kit = svc._heuristic_prep_kit("Backend Engineer", "Stripe", ["Python", "PostgreSQL"])
    assert len(kit["behavioral_questions"]) >= 1
    assert len(kit["technical_questions"]) >= 1
    assert "Stripe" in kit["company_insights"]

def test_evaluate_answer_short_fallback():
    svc = InterviewService()
    eval_res = svc.evaluate_answer("Tell me about yourself", "Short")
    assert eval_res["score"] == 30
    assert "brief" in eval_res["feedback"].lower()

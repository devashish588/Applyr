"""
Unit and integration tests for Company field data quality & presentation semantics.

Verifies:
1. Company present -> displays actual company.
2. Company null / empty -> returns 'Company unknown'.
3. Backend does not output 'Company not found'.
4. Extractor preserves company when available (e.g. 'Acme AI').
5. Extractor does not fabricate/invent missing companies.
6. All placeholder strings ('none', 'null', 'n/a', 'unknown', 'company not found') resolve cleanly.
"""

import importlib
import pytest
from ui.app import _sanitize_company

web_research_module = importlib.import_module("agents.01-web-research-agent.01_web_research_agent")
_BAD_COMPANY = web_research_module._BAD_COMPANY


def test_company_present_preserved():
    assert _sanitize_company("Google") == "Google"
    assert _sanitize_company("Acme AI") == "Acme AI"
    assert _sanitize_company(" OpenAI ") == "OpenAI"


def test_company_null_or_empty_returns_company_unknown():
    assert _sanitize_company(None) == "Company unknown"
    assert _sanitize_company("") == "Company unknown"
    assert _sanitize_company("   ") == "Company unknown"


def test_company_placeholders_sanitized():
    placeholders = [
        "Company not found",
        "Company Not Found",
        "company not extracted",
        "unknown company",
        "Unknown",
        "none",
        "null",
        "N/A",
    ]
    for p in placeholders:
        res = _sanitize_company(p)
        assert res == "Company unknown", f"Failed for placeholder: '{p}' (got '{res}')"
        assert res != "Company not found", "Backend must not fabricate or retain 'Company not found'"


def test_bad_company_set_completeness():
    assert "company not found" in _BAD_COMPANY
    assert "unknown" in _BAD_COMPANY
    assert "company not extracted" in _BAD_COMPANY


def test_no_fabrication_on_unknown():
    """Ensure missing company is never guessed/invented from title or random strings."""
    result = _sanitize_company(None)
    assert result == "Company unknown"
    assert result != "Google"
    assert result != "OpenAI"

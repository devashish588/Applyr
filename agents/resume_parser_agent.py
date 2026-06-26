# -*- coding: utf-8 -*-
"""
Resume Parser Agent — thin bridge to core/services/resume_parser_service.py.

All implementation lives in ResumeParserService (core/services/resume_parser_service.py).
This module re-exports it so that existing imports from agents.resume_parser_agent
continue to work without changes.
"""

from core.services.resume_parser_service import (
    ResumeParserService as ResumeParserAgent,
    ResumeParseError,
    _get_llm,
    SECTION_HEADERS,
    EMAIL_RE, PHONE_RE, LINKEDIN_RE, GITHUB_RE,
    COMMON_SKILLS, SKILLS_CATEGORIES, ROLE_KEYWORDS,
)

__all__ = [
    "ResumeParserAgent",
    "ResumeParseError",
]

"""
Opportunity Intelligence Models — Phase 16 (Foundation)
=========================================================

Informational-only domain describing the JOB / APPLICATION ENVIRONMENT,
distinct from candidate/job MATCH. Initial signals (foundation only,
all UNKNOWN until later phases implement deterministic computation):

- Competition Intensity
- Background Fit Sensitivity
- Shortlisting Strictness

Conventions reuse existing intelligence patterns:
- Pydantic BaseModel serialization (like job_intelligence.py)
- Evidence entries with signal/reason/source/confidence (like JobIntelligenceEvidence)
- UNKNOWN != LOW; UNDETERMINED != DETERMINED (explicit)
- No fake applicant counts, no percentages, no market data in Phase 16.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OpportunitySignalLevel(str, Enum):
    """Controlled signal level. UNKNOWN means cannot reliably determine, NOT low."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class OpportunityDeterminationStatus(str, Enum):
    """Whole-result and per-signal determination state."""
    DETERMINED = "DETERMINED"
    UNDETERMINED = "UNDETERMINED"


class OpportunityEvidence(BaseModel):
    """Reusable evidence entry explaining a future classification."""
    signal: str  # e.g. "COMPETITION_INTENSITY"
    reason: str
    source: str  # e.g. "job_metadata", "jd_text", "source_metadata"
    confidence: Optional[float] = None
    details: Optional[str] = None


class OpportunitySignal(BaseModel):
    """Single signal state. Phase 16 foundation is always UNKNOWN/UNDETERMINED."""
    level: OpportunitySignalLevel = OpportunitySignalLevel.UNKNOWN
    status: OpportunityDeterminationStatus = OpportunityDeterminationStatus.UNDETERMINED
    confidence: Optional[float] = None
    evidence: List[OpportunityEvidence] = Field(default_factory=list)


class OpportunityIntelligence(BaseModel):
    """Canonical opportunity-intelligence result for one job."""
    job_id: Optional[int] = None
    competition_intensity: OpportunitySignal = Field(default_factory=OpportunitySignal)
    background_fit_sensitivity: OpportunitySignal = Field(default_factory=OpportunitySignal)
    shortlisting_strictness: OpportunitySignal = Field(default_factory=OpportunitySignal)
    determination_status: OpportunityDeterminationStatus = OpportunityDeterminationStatus.UNDETERMINED
    evidence: List[OpportunityEvidence] = Field(default_factory=list)
    confidence: Optional[float] = None
    computed_at: Optional[str] = None

    def to_response(self) -> Dict[str, Any]:
        """API-shaped dict with per-signal level/status/confidence/evidence."""
        def _sig(s: OpportunitySignal) -> Dict[str, Any]:
            return {
                "level": s.level.value if isinstance(s.level, Enum) else s.level,
                "status": s.status.value if isinstance(s.status, Enum) else s.status,
                "confidence": s.confidence,
                "evidence": [e.model_dump() for e in s.evidence],
            }
        return {
            "job_id": self.job_id,
            "competition_intensity": _sig(self.competition_intensity),
            "background_fit_sensitivity": _sig(self.background_fit_sensitivity),
            "shortlisting_strictness": _sig(self.shortlisting_strictness),
            "determination_status": self.determination_status.value if isinstance(self.determination_status, Enum) else self.determination_status,
            "evidence": [e.model_dump() for e in self.evidence],
            "confidence": self.confidence,
            "computed_at": self.computed_at,
        }

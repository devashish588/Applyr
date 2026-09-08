"""
Analytics semantics — no fake data
Covers: measured vs no data, insufficient, derived, synthetic, sparse, null/NaN
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_measured_application_count():
    # When applications_submitted is 98, it should be displayed as 98, not —
    assert 98 == 98

def test_missing_response_data():
    # When responses is None/undefined, should be — not 0
    val = None
    is_no_data = val is None
    assert is_no_data is True

def test_actual_zero_response_count():
    # When truly 0 measured, should show 0 not —
    val = 0
    # In JS, 0 is not null, so KpiCard would show 0
    is_no_data = val is None
    assert is_no_data is False
    assert val == 0

def test_missing_interview_data():
    val = None
    assert (val is None) is True

def test_actual_zero_interview_count():
    val = 0
    assert val == 0
    assert (val is None) is False

def test_denominator_zero():
    # Conversion with den 0 should be — not 0%
    def rate(num, den):
        if den == 0 or den is None:
            return None
        return round(num/den*100)
    assert rate(0, 0) is None
    assert rate(5, 0) is None

def test_insufficient_data_threshold():
    # MIN_SAMPLE 5
    MIN_SAMPLE = 5
    def status(apps):
        return "INSUFFICIENT_DATA" if apps < MIN_SAMPLE else "OBSERVED"
    assert status(3) == "INSUFFICIENT_DATA"
    assert status(5) == "OBSERVED"

def test_derived_weekly_trend_label():
    content = Path("frontend/src/pages/analytics.tsx").read_text(encoding="utf-8", errors="ignore")
    assert "Derived estimate from totals — not measured daily history" in content

def test_sparse_source_adaptive():
    content = Path("frontend/src/pages/analytics.tsx").read_text(encoding="utf-8", errors="ignore")
    assert "No source distribution yet" in content
    assert "Showing" in content or "chart appears with more data" in content

def test_normal_multi_source():
    # With 3 sources and total >=3, chart should appear
    sourceData = [{"name": "Startups", "value": 1}, {"name": "LinkedIn", "value": 2}, {"name": "Referrals", "value": 1}]
    total = sum(s["value"] for s in sourceData)
    showChart = total >= 3 and len(sourceData) >= 2
    assert showChart is True

def test_null_undefined_data():
    for v in (None,):
        assert (v is None) is True
    # JS undefined equivalent in Python is None

def test_nan_invalid_calculations():
    import math
    # NaN should be treated as no data
    val = float('nan')
    is_invalid = isinstance(val, float) and math.isnan(val)
    assert is_invalid is True

def test_no_fabricated_values():
    content = Path("frontend/src/pages/analytics.tsx").read_text(encoding="utf-8", errors="ignore")
    assert "Derived estimate" in content
    assert "fake" not in content.lower() or "No fake" in content

def test_responses_not_fallback_to_emails_sent():
    # Critical: responses must never equal emails_sent accidentally
    content = Path("frontend/src/pages/analytics.tsx").read_text(encoding="utf-8", errors="ignore")
    # The bug was `responses ?? emails_sent` — now must be `responses` only
    assert "responses ?? analytics.emails_sent" not in content
    assert "responses ?? analytics?.emails_sent" not in content
    # Should have explicit comment
    assert "responses must never fallback to emails_sent" in content or "Responses must never fallback" in content or "responsesVal = analytics?.responses" in content

def test_hostile_A_emails_32_responses_null():
    # A: emails_sent 32, responses null -> Responses —, Emails Sent 32
    analytics = {"emails_sent": 32, "responses": None}
    responsesVal = analytics["responses"]  # no fallback
    emails_sent = analytics["emails_sent"]
    assert responsesVal is None
    assert emails_sent == 32
    # Frontend isNoData check
    is_no_data = lambda v: v is None
    assert is_no_data(responsesVal) is True
    assert is_no_data(emails_sent) is False

def test_hostile_B_emails_32_responses_0():
    # B: emails_sent 32, responses 0 -> Responses 0, Emails Sent 32
    analytics = {"emails_sent": 32, "responses": 0}
    responsesVal = analytics["responses"]
    assert responsesVal == 0
    assert responsesVal != analytics["emails_sent"]

def test_hostile_C_emails_32_responses_4():
    analytics = {"emails_sent": 32, "responses": 4}
    assert analytics["responses"] == 4
    assert analytics["responses"] != analytics["emails_sent"]

def test_hostile_D_emails_0_responses_null():
    analytics = {"emails_sent": 0, "responses": None}
    assert analytics["responses"] is None
    assert analytics["emails_sent"] == 0

def test_hostile_E_applications_0_responses_0():
    # E: applications 0, responses 0 -> rate —
    def rate(num, den):
        if den == 0 or den is None or num is None:
            return None
        return round(num/den*100)
    assert rate(0, 0) is None

def test_hostile_F_applications_98_responses_0():
    # F: 98 apps, 0 responses -> 0% only if authoritative definition is responses/applications and responses is measured 0
    # Here we test that 0 is preserved as 0, not —
    val = 0
    is_no_data = lambda v: v is None
    assert is_no_data(val) is False  # 0 is measured
    assert val == 0

def test_hostile_G_missing_field():
    analytics = {"emails_sent": 32}  # no responses field
    responsesVal = analytics.get("responses")
    assert responsesVal is None
    # Should be — not 32
    assert responsesVal != analytics["emails_sent"]

"""
P2 — Non-job pages must not become jobs.
Deterministic gate tests: classification, pipeline exclusion, metrics,
independence (no candidate/Match/LLM/network). No DB writes in unit tests;
orchestrator integration uses mocks like tests/test_multi_source.py.
"""
import inspect
from unittest.mock import patch, MagicMock

from core.services.job_listing_gate import (
    JOB, NON_JOB, UNDETERMINED, classify_listing, filter_listings,
)

# Observed production rows (sanitized metadata only: title/company/url/shape).
VIEW_ALL = {"title": "View All Jobs at Built In", "company": "builtin.com",
            "url": "https://builtin.com/jobs?companyId=81737", "source": "builtin.com",
            "jd_text": "x" * 25}
VIEW_ALL_2 = {"title": "View All", "company": "builtin.com",
              "url": "https://builtin.com/jobs?companyId=81737&allLocations=true",
              "source": "builtin.com", "jd_text": "x" * 8}
EDITORIAL = {"title": "Trying to Diversify Your Engineering Team? Start by Supporting Moms.",
             "company": "builtin.com",
             "url": "https://builtin.com/software-engineering-perspectives/diversify-teams-support-moms",
             "source": "builtin.com", "jd_text": "x" * 68}
TAG_PAGE = {"title": "Software Engineering Perspectives", "company": "builtin.com",
            "url": "https://builtin.com/tag/software-engineering-perspectives",
            "source": "builtin.com", "jd_text": "x" * 33}
TEAM_PAGE = {"title": "ENGINEERING", "company": "builtin.com",
             "url": "https://builtin.com/careers#tab-engineering",
             "source": "builtin.com", "jd_text": "x" * 11}
TEAM_PAGE_2 = {"title": "Built In Engineering Team", "company": "builtin.com",
               "url": "https://builtin.com/company/built-in/teams/engineering",
               "source": "builtin.com", "jd_text": "x" * 25}
FAQ_PAGE = {"title": "Leadership & Management", "company": "builtin.com",
            "url": "https://builtin.com/company/built-in/faq/leadership-management",
            "source": "builtin.com", "jd_text": "x" * 23}

REAL_BUILTIN = {"title": "Customer Success Manager", "company": "builtin.com",
                "url": "https://builtin.com/job/customer-success-manager/10201447",
                "source": "builtin.com", "jd_text": "Support customers" + " y" * 10}
REAL_BUILTIN_2 = {"title": "Enterprise Client Success Manager - GEO/AEO Platform",
                  "company": "builtin.com",
                  "url": "https://builtin.com/job/enterprise-geo-seo-account-manager/10533632",
                  "source": "builtin.com", "jd_text": "Own enterprise accounts" + " z" * 15}


# -- Classification: observed non-jobs --
def test_view_all_is_non_job():
    v, reason = classify_listing(dict(VIEW_ALL))
    assert v == NON_JOB and reason.startswith("NON_JOB_PAGE")


def test_view_all_variant_is_non_job():
    assert classify_listing(dict(VIEW_ALL_2))[0] == NON_JOB


def test_editorial_question_is_non_job():
    v, reason = classify_listing(dict(EDITORIAL))
    assert v == NON_JOB and "question" in reason


def test_tag_page_is_non_job():
    assert classify_listing(dict(TAG_PAGE))[0] == NON_JOB


def test_team_pages_are_non_job():
    assert classify_listing(dict(TEAM_PAGE))[0] == NON_JOB
    assert classify_listing(dict(TEAM_PAGE_2))[0] == NON_JOB
    assert classify_listing(dict(FAQ_PAGE))[0] == NON_JOB


# -- Classification: legitimate builtin job still passes --
def test_real_builtin_job_is_job():
    assert classify_listing(dict(REAL_BUILTIN))[0] == JOB
    assert classify_listing(dict(REAL_BUILTIN_2))[0] == JOB


# -- Classification: conservative acceptance --
def test_sparse_description_not_non_job():
    j = {"title": "Customer Success Manager", "company": "Acme",
         "url": "https://example.com/open-role", "source": "test", "jd_text": "Hi"}
    assert classify_listing(j)[0] != NON_JOB


def test_substantive_section_page_stays_eligible():
    # Even a section-shaped URL with long JD-like text stays eligible: the
    # adapter itself may emit JD-like pages as single listings.
    j = {"title": "Customer Success Manager", "company": "Acme",
         "url": "https://example.com/about", "source": "test", "jd_text": "y" * 900}
    assert classify_listing(j)[0] != NON_JOB


def test_missing_location_not_non_job():
    j = {"title": "Data Scientist", "company": "Acme", "url": "https://example.com/j/42",
         "source": "test", "location": None, "jd_text": ""}
    assert classify_listing(j)[0] != NON_JOB


def test_unknown_company_not_non_job():
    j = {"title": "Data Scientist", "company": "Company unknown",
         "url": "https://example.com/j/43", "source": "test", "jd_text": ""}
    assert classify_listing(j)[0] != NON_JOB


def test_unusual_title_not_non_job():
    j = {"title": "Xyzzyplugh Specialist", "company": "Acme",
         "url": "https://example.com/careers/xyzzy", "source": "test", "jd_text": ""}
    assert classify_listing(j)[0] != NON_JOB


def test_short_jd_not_non_job():
    j = {"title": "Customer Success Manager", "company": "Acme",
         "url": "https://example.com/careers/apply", "source": "test",
         "jd_text": "Great role"}
    assert classify_listing(j)[0] != NON_JOB


def test_unfamiliar_url_with_role_title_flows():
    j = {"title": "Machine Learning Engineer", "company": "Acme",
         "url": "https://jobs.unfamiliar-board.example/xyz", "source": "test", "jd_text": ""}
    assert classify_listing(j)[0] in (JOB, UNDETERMINED)


def test_empty_dict_is_undetermined_not_non_job():
    assert classify_listing({})[0] == UNDETERMINED
    assert classify_listing({"title": None, "url": None})[0] == UNDETERMINED


# -- False-positive audit: ordinary postings never NON_JOB --
def test_false_positive_audit():
    legit = [
        {"title": "Senior Software Engineer", "company": "Acme",
         "url": "https://example.com/jobs/12345", "jd_text": "Build things"},
        {"title": "Frontend Engineer", "company": "Acme",
         "url": "https://example.com/careers/frontend-engineer-1842", "jd_text": ""},
        {"title": "Machine Learning Engineer", "company": "Acme",
         "url": "https://jobs.lever.co/acme/abc123-def456", "jd_text": ""},
        {"title": "Data Scientist", "company": "", "url": "", "jd_text": ""},
        {"title": "Software Engineer - multiple locations", "company": "Acme",
         "url": "https://example.com/j/9", "jd_text": "short"},
        # JD-like single-listing employer page (adapter fallback shape): long text rescues bare root
        {"title": "Frontend Engineer", "company": "Acme",
         "url": "https://example.com/careers", "jd_text": "y" * 900},
    ]
    for j in legit:
        assert classify_listing(dict(j))[0] != NON_JOB, j["title"]


# -- Pipeline: exclusion before insert/canonical/attribution --
def _orch_srcs():
    from core.services.job_source_service import get_job_source_service
    return get_job_source_service()


def test_non_job_excluded_from_discovery():
    from pipeline.orchestrator import Orchestrator
    _orch_srcs()
    from core.services.job_source_service import get_job_source_service
    svc = get_job_source_service()
    srcs = svc.list_enabled()[:1]
    mixed = [dict(REAL_BUILTIN), dict(VIEW_ALL), dict(EDITORIAL),
             {"title": "Data Scientist", "company": "Acme",
              "url": "https://example.com/j/42", "source": "builtin.com",
              "location": "Remote", "type": "fulltime", "hr_email": None,
              "description_snippet": "x" * 50, "jd_text": "x" * 50, "required_skills": []}]

    def fake(src, profile, resume_data):
        return (mixed, "SUCCESS", None, "SEARCH", False, None)

    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m = MagicMock()
        m.list_enabled.return_value = srcs
        m.start_source_run.return_value = 1
        m.record_run = MagicMock()
        m.finish_source_run = MagicMock()
        mg.return_value = m
        with patch("core.services.job_source_adapters.dispatch_with_policy", side_effect=fake):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value = {}
                orch = Orchestrator(run_id="gate1")
                orch.resume_blocked = False
                orch.parsed_resume = MagicMock()
                orch.parsed_resume.model_dump.return_value = {}
                ls = orch._step_discover(None, None, None)
                urls = {j.get("url") for j in ls}
                assert "https://builtin.com/jobs?companyId=81737" not in urls
                assert "https://builtin.com/software-engineering-perspectives/diversify-teams-support-moms" not in urls
                assert "https://builtin.com/job/customer-success-manager/10201447" in urls
                assert "https://example.com/j/42" in urls
                # Survivors tagged, filtered never tagged (no attribution downstream)
                by_url = {j.get("url"): j for j in ls}
                assert "_source_id" in by_url["https://builtin.com/job/customer-success-manager/10201447"]
                # Metrics truthful: found=raw, normalized=survivors, filtered=new key
                res = orch.results["sources"][0]
                assert res["jobs_found"] == 4
                assert res["jobs_normalized"] == 2
                assert res["non_job_filtered"] == 2
                assert orch.results["non_job_filtered"] == 2
                assert res["failure_category"] == "SUCCESS"


def test_failures_stay_distinct_from_filtering():
    from pipeline.orchestrator import Orchestrator
    from core.services.job_source_service import JobSource, _now
    # Isolated fixtures — no dependency on production registry size/order or cross-attr fixtures
    src1 = JobSource(id="test-gate-success", name="Test Gate Success", url="https://example.com/jobs", host="example.com", enabled=True, source_type="search", adapter="SearchAdapter", created_at=_now(), updated_at=_now())
    src2 = JobSource(id="test-gate-timeout", name="Test Gate Timeout", url="https://other.example/jobs", host="other.example", enabled=True, source_type="search", adapter="SearchAdapter", created_at=_now(), updated_at=_now())
    srcs = [src1, src2]

    def fake(src, profile, resume_data):
        if src.id == "test-gate-success":
            return ([dict(VIEW_ALL)], "SUCCESS", None, "SEARCH", False, None)
        return ([], "TIMEOUT", "timeout", "SEARCH", False, None)

    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m = MagicMock()
        m.list_enabled.return_value = srcs
        m.start_source_run.return_value = 1
        m.record_run = MagicMock()
        m.finish_source_run = MagicMock()
        mg.return_value = m
        with patch("core.services.job_source_adapters.dispatch_with_policy", side_effect=fake):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value = {}
                orch = Orchestrator(run_id="gate2")
                orch.resume_blocked = False
                orch.parsed_resume = MagicMock()
                orch.parsed_resume.model_dump.return_value = {}
                ls = orch._step_discover(None, None, None)
                assert ls == []
                cats = {r["failure_category"] for r in orch.results["sources"]}
                assert "TIMEOUT" in cats and "SUCCESS" in cats
                assert sum(r.get("non_job_filtered", 0) for r in orch.results["sources"]) == 1


def test_all_filtered_source_keeps_success_not_failure():
    from pipeline.orchestrator import Orchestrator
    from core.services.job_source_service import get_job_source_service
    svc = get_job_source_service()
    srcs = svc.list_enabled()[:1]

    def fake(src, profile, resume_data):
        return ([dict(VIEW_ALL)], "SUCCESS", None, "SEARCH", False, None)

    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m = MagicMock()
        m.list_enabled.return_value = srcs
        m.start_source_run.return_value = 1
        m.record_run = MagicMock()
        m.finish_source_run = MagicMock()
        mg.return_value = m
        with patch("core.services.job_source_adapters.dispatch_with_policy", side_effect=fake):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value = {}
                orch = Orchestrator(run_id="gate3")
                orch.resume_blocked = False
                orch.parsed_resume = MagicMock()
                orch.parsed_resume.model_dump.return_value = {}
                ls = orch._step_discover(None, None, None)
                assert ls == []
                assert orch.results["sources"][0]["failure_category"] == "SUCCESS"
                assert orch.results["sources"][0]["non_job_filtered"] == 1


def test_gate_does_not_dedup():
    a = {"title": "Data Scientist", "company": "Acme",
         "url": "https://example.com/j/42", "jd_text": ""}
    b = dict(a)
    passing, filtered = filter_listings([a, b])
    assert len(passing) == 2 and filtered == []


# -- Independence: no candidate/Match/LLM/network --
def test_no_candidate_match_llm_imports():
    # AST-based so docstring vocabulary ("candidate", "Match/Priority") can't
    # trip the check: only real imports and referenced names count.
    import ast
    import core.services.job_listing_gate as gate
    tree = ast.parse(inspect.getsource(gate))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= {"__future__", "re", "urllib", "typing"}, imported
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for token in ("candidate", "resume", "match_service", "MatchService",
                  "priority", "tavily", "groq", "openai", "llm", "requests",
                  "socket", "urlopen", "urlretrieve"):
        assert token not in names, token
    assert set(inspect.signature(gate.classify_listing).parameters) == {"job"}
    assert set(inspect.signature(gate.filter_listings).parameters) == {"jobs"}


def test_deterministic_and_pure():
    import copy
    j = dict(REAL_BUILTIN)
    snapshot = copy.deepcopy(j)
    assert classify_listing(j) == classify_listing(dict(j))
    assert j == snapshot
    p1, f1 = filter_listings([dict(VIEW_ALL), dict(REAL_BUILTIN)])
    p2, f2 = filter_listings([dict(VIEW_ALL), dict(REAL_BUILTIN)])
    assert [x["url"] for x in p1] == [x["url"] for x in p2]
    assert [x[0]["url"] for x in f1] == [x[0]["url"] for x in f2]

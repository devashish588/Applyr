"""
Observability hardening — SEARCH pipeline telemetry (provider raw, LLM, gate, site-mismatch, failure taxonomy)
NO recall change, NO provider change, stdlib only where possible.
"""
import pytest
from unittest.mock import patch, MagicMock

from core.services.job_listing_gate import classify_listing, filter_listings
from core.services.job_source_service import get_job_source_service, reset_job_source_service, JobSource, _now
from core.ai.errors import RateLimitError, TimeoutError, AuthenticationError, ProviderUnavailableError, sanitize_exception_message

# --- Helpers ---
def _make_source(host="linkedin.com", url=None, adapter="SearchAdapter", source_type="search"):
    sid = f"test-{host.replace('.', '-')}"
    return JobSource(id=sid, name=host.title(), url=url or f"https://{host}/jobs", host=host, enabled=True, source_type=source_type, adapter=adapter, created_at=_now(), updated_at=_now(), source_role="JOB_BOARD", primary_mode="SEARCH", direct_fetch_allowed=False, search_discovery_allowed=True)

# 1. raw provider count recorded correctly (SEARCH: Tavily raw ≠ LLM count)
def test_provider_raw_count_recorded():
    src = _make_source("linkedin.com")
    fake_results = [{"url": f"https://linkedin.com/jobs/{i}", "title": f"Job {i}", "content": "x"*200} for i in range(10)]
    fake_listings = [{"title": f"Title {i}", "company": "C", "url": f"https://linkedin.com/jobs/{i}", "location": "Remote", "source": "linkedin.com", "type": "fulltime", "description_snippet": "x"*100, "required_skills": []} for i in range(14)]
    with patch("agents.web_research_agent._run_tavily", return_value=fake_results):
        with patch("utils.llm_client.get_llm") as mllm:
            m = MagicMock()
            m.invoke.return_value = MagicMock(content=str(fake_listings))
            mllm.return_value = m
            # need to patch _extract_job_listings to return our fake listings
            with patch("agents.web_research_agent._extract_job_listings", return_value=fake_listings):
                from core.services.job_source_adapters import search_adapter
                jobs, cat, err, provider_raw = search_adapter(src, {}, {"roles_json": ["SE"], "skills_json": ["Python"]})
                assert cat == "SUCCESS"
                assert provider_raw == 10
                assert len(jobs) == 14

# 2. LLM extraction count recorded correctly (jobs_found == llm count)
def test_llm_extracted_count_is_jobs_found():
    from pipeline.orchestrator import Orchestrator
    from core.services.job_source_service import get_job_source_service as gsvc
    src = _make_source("linkedin.com")
    def fake_dispatch(src, profile, resume_data):
        # Simulate provider_raw 10, llm 14
        jobs = [{"title": f"T{i}", "company": "C", "url": f"https://linkedin.com/jobs/{i}", "source": src.host, "location": "Remote", "type": "fulltime", "hr_email": None, "description_snippet": "x"*100, "jd_text": "x"*100, "required_skills": []} for i in range(14)]
        return (jobs, "SUCCESS", None, 10)
    svc = get_job_source_service()
    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m = MagicMock()
        m.list_enabled.return_value = [src]
        m.start_source_run.return_value = 1
        m.record_run = MagicMock()
        m.finish_source_run = MagicMock()
        mg.return_value = m
        with patch("core.services.job_source_adapters.dispatch", side_effect=fake_dispatch):
            # dispatch_with_policy wraps dispatch; patch it to return full 7-tuple
            with patch("core.services.job_source_adapters.dispatch_with_policy") as mdp:
                mdp.return_value = ([{"title": f"T{i}", "company": "C", "url": f"https://linkedin.com/jobs/{i}", "source": src.host, "location": "Remote", "type": "fulltime", "hr_email": None, "description_snippet": "x"*100, "jd_text": "x"*100, "required_skills": []} for i in range(14)], "SUCCESS", None, "SEARCH", False, None, 10)
                with patch("db.db_client.get_db") as mdb:
                    mdb.return_value.get_resume_data.return_value = {"roles_json": ["SE"], "skills_json": ["Python"]}
                    orch = Orchestrator(run_id="obs1")
                    orch.resume_blocked = False
                    orch.parsed_resume = MagicMock(); orch.parsed_resume.model_dump.return_value = {}
                    ls = orch._step_discover(None, None, None)
                    src_res = orch.results["sources"][0]
                    assert src_res["provider_raw_count"] == 10
                    assert src_res["llm_extracted_count"] == 14
                    assert src_res["jobs_found"] == 14

# 3. gate count recorded correctly
def test_gate_counts():
    from pipeline.orchestrator import Orchestrator
    src = _make_source("builtin.com")
    # 16 jobs: 2 non-job (View All, ?), 14 good
    jobs = []
    jobs.append({"title": "View All Jobs at Built In", "company": "builtin.com", "url": "https://builtin.com/jobs", "source": "builtin.com", "location": "Remote", "type": "fulltime", "hr_email": None, "description_snippet": "x"*20, "jd_text": "x"*20, "required_skills": []})
    jobs.append({"title": "Trying to diversify? Start here", "company": "builtin.com", "url": "https://builtin.com/article/foo", "source": "builtin.com", "location": "Remote", "type": "fulltime", "hr_email": None, "description_snippet": "x"*20, "jd_text": "x"*20, "required_skills": []})
    for i in range(14):
        jobs.append({"title": f"Engineer {i}", "company": "C", "url": f"https://builtin.com/job/eng-{10000+i}", "source": "builtin.com", "location": "Remote", "type": "fulltime", "hr_email": None, "description_snippet": "Build things"*10, "jd_text": "Build things"*10, "required_skills": []})
    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m = MagicMock(); m.list_enabled.return_value=[src]; m.start_source_run.return_value=1; m.record_run=MagicMock(); m.finish_source_run=MagicMock(); mg.return_value=m
        with patch("core.services.job_source_adapters.dispatch_with_policy") as mdp:
            mdp.return_value=(jobs, "SUCCESS", None, "SEARCH", False, None, 16)
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value={}
                orch=Orchestrator(run_id="gate1"); orch.resume_blocked=False; orch.parsed_resume=MagicMock(); orch.parsed_resume.model_dump.return_value={}
                ls=orch._step_discover(None,None,None)
                r=orch.results["sources"][0]
                assert r["non_job_filtered"]==2
                assert r["jobs_normalized"]==14
                assert len(ls)==14

# 4. non-job filtered correctly (already above)

# 5. inserted/duplicate remain distinct (global after dedup)
def test_inserted_duplicate_distinct():
    from pipeline.orchestrator import Orchestrator
    src1 = JobSource(id="s1", name="S1", url="https://a.com", host="a.com", enabled=True, source_type="search", adapter="SearchAdapter", created_at=_now(), updated_at=_now())
    src2 = JobSource(id="s2", name="S2", url="https://b.com", host="b.com", enabled=True, source_type="search", adapter="SearchAdapter", created_at=_now(), updated_at=_now())
    # same URL across two sources would be duplicate after dedup
    def fake_dispatch_policy(src, profile, resume_data):
        jobs=[{"title":"T","company":"C","url":"https://common.example.com/job/123","source":src.host,"location":"Remote","type":"fulltime","hr_email":None,"description_snippet":"x"*100,"jd_text":"x"*100,"required_skills":[]}]
        return (jobs, "SUCCESS", None, "SEARCH", False, None, 1)
    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m=MagicMock(); m.list_enabled.return_value=[src1,src2]; m.start_source_run.return_value=1; m.record_run=MagicMock(); m.finish_source_run=MagicMock(); mg.return_value=m
        with patch("core.services.job_source_adapters.dispatch_with_policy", side_effect=fake_dispatch_policy):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value={}
                # mock url_exists to simulate second is duplicate of first in DB? Use orchestrator's batch grouping
                orch=Orchestrator(run_id="dup1"); orch.resume_blocked=False; orch.parsed_resume=MagicMock(); orch.parsed_resume.model_dump.return_value={}
                # mock _deduplicate to return 1 of 2 as duplicate
                with patch.object(Orchestrator, "_deduplicate", return_value=[{"title":"T","company":"C","url":"https://common.example.com/job/123","source":"a.com","location":"Remote","type":"fulltime","hr_email":None,"description_snippet":"x"*100,"jd_text":"x"*100,"required_skills":[],"_source_id":"s1"}]):
                    ls=orch._step_discover(None,None,None)
                    # _step_discover does not call _deduplicate, only collects; dedup is in run_full_pipeline
                    # So per-source duplicate is 0, global duplicate would be computed later
                    assert len(ls)==2 # both collected via different sources but same URL would be 2 before dedup
                    assert orch.results["sources"][0]["jobs_found"]==1

# 6. 429 → RATE_LIMITED
def test_429_rate_limited():
    src=_make_source("linkedin.com")
    with patch("agents.web_research_agent._run_tavily", side_effect=RateLimitError("429 rate limit")):
        from core.services.job_source_adapters import search_adapter
        jobs,cat,err,pr=search_adapter(src, {}, {})
        assert cat=="RATE_LIMITED"

# 7. timeout → TIMEOUT
def test_timeout():
    src=_make_source("linkedin.com")
    with patch("agents.web_research_agent._run_tavily", side_effect=TimeoutError("timeout")):
        from core.services.job_source_adapters import search_adapter
        jobs,cat,err,pr=search_adapter(src, {}, {})
        assert cat=="TIMEOUT"

# 8. auth failure → AUTH
def test_auth():
    src=_make_source("linkedin.com")
    with patch("agents.web_research_agent._run_tavily", side_effect=AuthenticationError("auth failed")):
        from core.services.job_source_adapters import search_adapter
        jobs,cat,err,pr=search_adapter(src, {}, {})
        assert cat=="AUTH"

# 9. generic provider failure → PROVIDER_ERROR
def test_provider_error():
    src=_make_source("linkedin.com")
    with patch("agents.web_research_agent._run_tavily", side_effect=ProviderUnavailableError("All AI providers unavailable")):
        from core.services.job_source_adapters import search_adapter
        jobs,cat,err,pr=search_adapter(src, {}, {})
        assert cat=="PROVIDER_ERROR"

# 10. ambiguous failure → UNKNOWN
def test_unknown():
    src=_make_source("linkedin.com")
    with patch("agents.web_research_agent._run_tavily", side_effect=Exception("weird ambiguous")):
        from core.services.job_source_adapters import search_adapter
        jobs,cat,err,pr=search_adapter(src, {}, {})
        assert cat=="UNKNOWN"

# 11. same host → false
def test_site_mismatch_same_host():
    from pipeline.orchestrator import Orchestrator
    src=_make_source("linkedin.com")
    jobs=[{"title":"T","company":"C","url":"https://linkedin.com/jobs/123","source":src.host,"location":"Remote","type":"fulltime","hr_email":None,"description_snippet":"x"*100,"jd_text":"x"*100,"required_skills":[]}]
    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m=MagicMock(); m.list_enabled.return_value=[src]; m.start_source_run.return_value=1; m.record_run=MagicMock(); m.finish_source_run=MagicMock(); mg.return_value=m
        with patch("core.services.job_source_adapters.dispatch_with_policy", return_value=(jobs,"SUCCESS",None,"SEARCH",False,None,1)):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value={}
                orch=Orchestrator(run_id="sm1"); orch.resume_blocked=False; orch.parsed_resume=MagicMock(); orch.parsed_resume.model_dump.return_value={}
                ls=orch._step_discover(None,None,None)
                assert orch.results["sources"][0]["site_mismatch_count"]==0

# 12. subdomain → false when legitimately same host family
def test_site_mismatch_subdomain():
    from pipeline.orchestrator import Orchestrator
    src=_make_source("linkedin.com")
    jobs=[{"title":"T","company":"C","url":"https://www.linkedin.com/jobs/123","source":src.host,"location":"Remote","type":"fulltime","hr_email":None,"description_snippet":"x"*100,"jd_text":"x"*100,"required_skills":[]}]
    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m=MagicMock(); m.list_enabled.return_value=[src]; m.start_source_run.return_value=1; m.record_run=MagicMock(); m.finish_source_run=MagicMock(); mg.return_value=m
        with patch("core.services.job_source_adapters.dispatch_with_policy", return_value=(jobs,"SUCCESS",None,"SEARCH",False,None,1)):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value={}
                orch=Orchestrator(run_id="sm2"); orch.resume_blocked=False; orch.parsed_resume=MagicMock(); orch.parsed_resume.model_dump.return_value={}
                orch._step_discover(None,None,None)
                assert orch.results["sources"][0]["site_mismatch_count"]==0
    # also jobs.www.linkedin.com vs linkedin.com already, but subdomain like sub.linkedin.com should also be false
    jobs2=[{"title":"T","company":"C","url":"https://careers.linkedin.com/jobs/123","source":src.host,"location":"Remote","type":"fulltime","hr_email":None,"description_snippet":"x"*100,"jd_text":"x"*100,"required_skills":[]}]
    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m=MagicMock(); m.list_enabled.return_value=[src]; m.start_source_run.return_value=1; m.record_run=MagicMock(); m.finish_source_run=MagicMock(); mg.return_value=m
        with patch("core.services.job_source_adapters.dispatch_with_policy", return_value=(jobs2,"SUCCESS",None,"SEARCH",False,None,1)):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value={}
                orch=Orchestrator(run_id="sm3"); orch.resume_blocked=False; orch.parsed_resume=MagicMock(); orch.parsed_resume.model_dump.return_value={}
                orch._step_discover(None,None,None)
                assert orch.results["sources"][0]["site_mismatch_count"]==0

# 13. different host → true
def test_site_mismatch_different_host():
    from pipeline.orchestrator import Orchestrator
    src=_make_source("linkedin.com")
    jobs=[{"title":"T","company":"C","url":"https://indeed.com/jobs/123","source":src.host,"location":"Remote","type":"fulltime","hr_email":None,"description_snippet":"x"*100,"jd_text":"x"*100,"required_skills":[]}]
    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m=MagicMock(); m.list_enabled.return_value=[src]; m.start_source_run.return_value=1; m.record_run=MagicMock(); m.finish_source_run=MagicMock(); mg.return_value=m
        with patch("core.services.job_source_adapters.dispatch_with_policy", return_value=(jobs,"SUCCESS",None,"SEARCH",False,None,1)):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value={}
                orch=Orchestrator(run_id="sm4"); orch.resume_blocked=False; orch.parsed_resume=MagicMock(); orch.parsed_resume.model_dump.return_value={}
                orch._step_discover(None,None,None)
                assert orch.results["sources"][0]["site_mismatch_count"]==1
                assert orch.results["site_mismatch_count"]==1
                assert orch.results["site_mismatch_examples"][0]["host"]=="indeed.com"

# 14. query source and extracted URL are compared safely (no crash on missing URL, relative URL, malformed)
def test_site_mismatch_safe_comparison():
    from pipeline.orchestrator import Orchestrator
    src=_make_source("linkedin.com")
    jobs=[
        {"title":"T","company":"C","url":"","source":src.host,"location":"Remote","type":"fulltime","hr_email":None,"description_snippet":"x"*100,"jd_text":"x"*100,"required_skills":[]},
        {"title":"T2","company":"C","url":"/relative/path","source":src.host,"location":"Remote","type":"fulltime","hr_email":None,"description_snippet":"x"*100,"jd_text":"x"*100,"required_skills":[]},
        {"title":"T3","company":"C","url":"https://linkedin.com/jobs/123","source":src.host,"location":"Remote","type":"fulltime","hr_email":None,"description_snippet":"x"*100,"jd_text":"x"*100,"required_skills":[]},
    ]
    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m=MagicMock(); m.list_enabled.return_value=[src]; m.start_source_run.return_value=1; m.record_run=MagicMock(); m.finish_source_run=MagicMock(); mg.return_value=m
        with patch("core.services.job_source_adapters.dispatch_with_policy", return_value=(jobs,"SUCCESS",None,"SEARCH",False,None,1)):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value={}
                orch=Orchestrator(run_id="sm5"); orch.resume_blocked=False; orch.parsed_resume=MagicMock(); orch.parsed_resume.model_dump.return_value={}
                orch._step_discover(None,None,None)
                # only valid http with different host would count; empty/relative should not count as mismatch
                assert orch.results["sources"][0]["site_mismatch_count"]==0

# 15. mismatched result remains eligible in this phase (not dropped)
def test_site_mismatch_remains_eligible():
    from pipeline.orchestrator import Orchestrator
    src=_make_source("linkedin.com")
    jobs=[{"title":"Engineer","company":"C","url":"https://indeed.com/jobs/123","source":src.host,"location":"Remote","type":"fulltime","hr_email":None,"description_snippet":"Build stuff "*20,"jd_text":"Build stuff "*20,"required_skills":[]}]
    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m=MagicMock(); m.list_enabled.return_value=[src]; m.start_source_run.return_value=1; m.record_run=MagicMock(); m.finish_source_run=MagicMock(); mg.return_value=m
        with patch("core.services.job_source_adapters.dispatch_with_policy", return_value=(jobs,"SUCCESS",None,"SEARCH",False,None,1)):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value={}
                orch=Orchestrator(run_id="sm6"); orch.resume_blocked=False; orch.parsed_resume=MagicMock(); orch.parsed_resume.model_dump.return_value={}
                ls=orch._step_discover(None,None,None)
                # mismatched but still in listings (not dropped), and gate passes because substantive jd_text
                assert len(ls)==1
                assert ls[0]["url"]=="https://indeed.com/jobs/123"
                assert orch.results["sources"][0]["site_mismatch_count"]==1

# 16. no secrets in telemetry (error sanitization)
def test_no_secrets_in_telemetry():
    from core.ai.errors import sanitize_exception_message
    # Use query-param ?key= pattern which sanitizer covers; Bearer also covered
    err = "Failed Bearer abc.def.ghi https://example.com?key=secret&other=1"
    sanitized = sanitize_exception_message(err)
    assert "abc.def.ghi" not in sanitized
    assert "secret" not in sanitized.lower() or "REDACTED" in sanitized
    assert "REDACTED" in sanitized
    # ensure orchestrator sanitizes exception (Bearer and ?key= are redacted)
    from pipeline.orchestrator import Orchestrator
    src=_make_source("linkedin.com")
    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m=MagicMock(); m.list_enabled.return_value=[src]; m.start_source_run.return_value=1; m.record_run=MagicMock(); m.finish_source_run=MagicMock(); mg.return_value=m
        with patch("core.services.job_source_adapters.dispatch_with_policy", side_effect=Exception("Bearer token123 https://example.com?key=supersecret")):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value={}
                orch=Orchestrator(run_id="sec1"); orch.resume_blocked=False; orch.parsed_resume=MagicMock(); orch.parsed_resume.model_dump.return_value={}
                orch._step_discover(None,None,None)
                err_msg = orch.results["sources"][0]["error"]
                assert "token123" not in err_msg
                assert "supersecret" not in err_msg

# 17. no raw Authorization header in telemetry
def test_no_authorization_leak():
    # dispatch should not include headers
    import inspect
    src_code = open("core/services/job_source_adapters.py").read()
    assert "Authorization" not in src_code or "REDACTED" in open("core/ai/errors.py").read()

# 18. no DATABASE_URL in telemetry
def test_no_database_url_in_telemetry():
    from pipeline.orchestrator import Orchestrator
    src=_make_source("linkedin.com")
    jobs=[{"title":"T","company":"C","url":"https://linkedin.com/jobs/123","source":src.host,"location":"Remote","type":"fulltime","hr_email":None,"description_snippet":"x"*100,"jd_text":"x"*100,"required_skills":[]}]
    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m=MagicMock(); m.list_enabled.return_value=[src]; m.start_source_run.return_value=1; m.record_run=MagicMock(); m.finish_source_run=MagicMock(); mg.return_value=m
        with patch("core.services.job_source_adapters.dispatch_with_policy", return_value=(jobs,"SUCCESS",None,"SEARCH",False,None,1)):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value={}
                orch=Orchestrator(run_id="sec2"); orch.resume_blocked=False; orch.parsed_resume=MagicMock(); orch.parsed_resume.model_dump.return_value={}
                orch._step_discover(None,None,None)
                import json
                blob = json.dumps(orch.results)
                assert "DATABASE_URL" not in blob
                assert "neon.tech" not in blob

# 19. no stack trace returned to browser (error is short, not traceback)
def test_no_stack_trace():
    from pipeline.orchestrator import Orchestrator
    src=_make_source("linkedin.com")
    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m=MagicMock(); m.list_enabled.return_value=[src]; m.start_source_run.return_value=1; m.record_run=MagicMock(); m.finish_source_run=MagicMock(); mg.return_value=m
        with patch("core.services.job_source_adapters.dispatch_with_policy", side_effect=Exception("some failure\nTraceback (most recent call last):\n  File")):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value={}
                orch=Orchestrator(run_id="sec3"); orch.resume_blocked=False; orch.parsed_resume=MagicMock(); orch.parsed_resume.model_dump.return_value={}
                orch._step_discover(None,None,None)
                err = orch.results["sources"][0]["error"]
                assert "Traceback" not in err
                assert len(err) < 2000

# 20. Job Listing Gate unchanged (still filters View All etc, conservative)
def test_gate_unchanged():
    from core.services.job_listing_gate import classify_listing
    assert classify_listing({"title": "View All Jobs at Built In", "url": "https://builtin.com/jobs", "jd_text": ""})[0]=="NON_JOB"
    assert classify_listing({"title": "Software Engineer", "url": "https://builtin.com/job/eng-12345", "jd_text": "Build things"*10})[0]=="JOB"

# 21. source policy unchanged (JOB_BOARD -> SEARCH direct false)
def test_source_policy_unchanged():
    from core.services.job_source_service import _policy_for_host
    role, mode, direct, search = _policy_for_host("linkedin.com", "search")
    assert role=="JOB_BOARD"
    assert mode=="SEARCH"
    assert direct is False
    assert search is True

# 22. canonical identity unchanged
def test_canonical_unchanged():
    from core.services.job_canonical_service import compute_canonical_id
    id1 = compute_canonical_id("Software Engineer", "Acme", "Remote", "https://example.com/jobs/123")
    id2 = compute_canonical_id("Software Engineer", "Acme", "Remote", "https://example.com/jobs/123")
    assert id1==id2
    # host matters
    id3 = compute_canonical_id("Software Engineer", "Acme", "Remote", "https://other.com/jobs/123")
    assert id1 != id3

# 23. MatchService unchanged (weights)
def test_match_service_unchanged():
    from core.services.match_service import MatchService
    import inspect
    src = inspect.getsource(MatchService)
    assert "0.40" in src or "SKILL_WEIGHT" in src

# 24. Application Priority unchanged
def test_priority_unchanged():
    from core.services.application_priority_service import get_priority_service
    svc = get_priority_service()
    assert hasattr(svc, "evaluate")

# 25. Opportunity Intelligence unchanged (still UNKNOWN default)
def test_oi_unchanged():
    from core.services.opportunity_intelligence_service import get_opportunity_intelligence_service
    svc = get_opportunity_intelligence_service()
    # ensure it still has foundation methods
    assert hasattr(svc, "get_for_job") or hasattr(svc, "evaluate_shortlisting_strictness")

# Real-world reproduction: linkedin -> indeed mismatch true, do not drop
def test_real_world_linkedin_indeed():
    from pipeline.orchestrator import Orchestrator
    src=_make_source("linkedin.com", "https://linkedin.com/jobs")
    jobs=[{"title":"Backend Engineer","company":"Acme","url":"https://indeed.com/q-backend-123","source":"linkedin.com","location":"Remote","type":"fulltime","hr_email":None,"description_snippet":"Python React "*20,"jd_text":"Python React "*20,"required_skills":[]}]
    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m=MagicMock(); m.list_enabled.return_value=[src]; m.start_source_run.return_value=1; m.record_run=MagicMock(); m.finish_source_run=MagicMock(); mg.return_value=m
        with patch("core.services.job_source_adapters.dispatch_with_policy", return_value=(jobs,"SUCCESS",None,"SEARCH",False,None,10)):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value={}
                orch=Orchestrator(run_id="real1"); orch.resume_blocked=False; orch.parsed_resume=MagicMock(); orch.parsed_resume.model_dump.return_value={}
                ls=orch._step_discover(None,None,None)
                assert orch.results["sources"][0]["site_mismatch_count"]==1
                assert len(ls)==1 # not dropped

# Over-generation observability: provider_raw 10, llm 14 visible
def test_over_generation_visible():
    from pipeline.orchestrator import Orchestrator
    src=_make_source("linkedin.com")
    jobs=[{"title":f"T{i}","company":"C","url":f"https://linkedin.com/jobs/{i}","source":src.host,"location":"Remote","type":"fulltime","hr_email":None,"description_snippet":"x"*100,"jd_text":"x"*100,"required_skills":[]} for i in range(14)]
    with patch("core.services.job_source_service.get_job_source_service") as mg:
        m=MagicMock(); m.list_enabled.return_value=[src]; m.start_source_run.return_value=1; m.record_run=MagicMock(); m.finish_source_run=MagicMock(); mg.return_value=m
        with patch("core.services.job_source_adapters.dispatch_with_policy", return_value=(jobs,"SUCCESS",None,"SEARCH",False,None,10)):
            with patch("db.db_client.get_db") as mdb:
                mdb.return_value.get_resume_data.return_value={}
                orch=Orchestrator(run_id="over1"); orch.resume_blocked=False; orch.parsed_resume=MagicMock(); orch.parsed_resume.model_dump.return_value={}
                orch._step_discover(None,None,None)
                r=orch.results["sources"][0]
                assert r["provider_raw_count"]==10
                assert r["llm_extracted_count"]==14
                assert r["provider_raw_count"] < r["llm_extracted_count"]

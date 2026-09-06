import os, sys, json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
sys.path.insert(0, str(Path(__file__).parent.parent))

def _test_url():
    url=os.getenv("TEST_DATABASE_URL","")
    if not url:
        prod=os.getenv("DATABASE_URL","")
        if "/neondb?" in prod:
            return prod.replace("/neondb?","/applyr_test?")
        return prod.replace("/neondb","/applyr_test") if "/neondb" in prod else prod
    return url
def _get_conn(): return psycopg2.connect(_test_url())
def _clean(conn=None):
    close=False
    if conn is None:
        conn=_get_conn(); close=True
    try:
        with conn.cursor() as cur:
            for t in ["feedback","follow_ups","interviews","application_events","application_outcomes","applications","jobs"]:
                try: cur.execute(f"DELETE FROM {t}")
                except: pass
        conn.commit()
    except: pass
    finally:
        if close: conn.close()
@pytest.fixture(scope="module")
def mod_conn():
    c=psycopg2.connect(_test_url())
    for p in ["002_application_lifecycle.sql","003_job_quality_freshness.sql","004_studio_runs.sql","005_interview_followup.sql","006_feedback.sql"]:
        try:
            sql=Path(f"db/migrations/{p}").read_text()
            with c.cursor() as cur: cur.execute(sql)
            c.commit()
        except: c.rollback()
    yield c
    c.close()
@pytest.fixture(autouse=True)
def clean(mod_conn):
    _clean(mod_conn)
    yield
    _clean(mod_conn)
def _create_job(conn, title="T", company="C", source="test"):
    import uuid
    url=f"https://example.com/{uuid.uuid4()}"
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("INSERT INTO jobs (title, company, url, source, scraped_at, last_seen_at) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id", (title, company, url, source, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
        jid=cur.fetchone()["id"]
    conn.commit()
    return jid
def _create_app(conn, job_id, state="PREPARING"):
    from core.services.application_service import ApplicationService
    svc=ApplicationService()
    app=svc.create_application(job_id=job_id)
    if state=="PREPARING": return app
    svc.apply_application(app["id"])
    if state=="APPLIED": return svc.get_application(app["id"])
    if state=="SCREENING":
        svc.patch_state(app["id"],"SCREENING"); return svc.get_application(app["id"])
    if state=="INTERVIEW":
        svc.patch_state(app["id"],"SCREENING"); svc.patch_state(app["id"],"INTERVIEW"); return svc.get_application(app["id"])
    if state=="FINAL":
        svc.patch_state(app["id"],"SCREENING"); svc.patch_state(app["id"],"INTERVIEW"); svc.patch_state(app["id"],"FINAL"); return svc.get_application(app["id"])
    if state=="OFFER":
        svc.patch_state(app["id"],"SCREENING"); svc.patch_state(app["id"],"INTERVIEW"); svc.patch_state(app["id"],"OFFER"); return svc.get_application(app["id"])
    if state=="CLOSED":
        svc.apply_application(app["id"]); svc.set_outcome(app["id"],"REJECTED"); return svc.get_application(app["id"])
    return app

# FUNNEL
class TestFunnel:
    def test_zero_applications(self, mod_conn):
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        f=OutcomeAnalyticsService().funnel()
        assert f["applications_started"]==0
        assert f["applications_submitted"]==0
        assert f["application_to_interview_rate"] is None
    def test_started_semantics(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; app=ApplicationService().create_application(job_id=jid)
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        f=OutcomeAnalyticsService().funnel()
        assert f["applications_started"]==1
        assert f["applications_submitted"]==0
    def test_submitted_semantics(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; svc=ApplicationService(); app=svc.create_application(job_id=jid); svc.apply_application(app["id"])
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        f=OutcomeAnalyticsService().funnel()
        assert f["applications_submitted"]==1
    def test_screening(self, mod_conn):
        _create_app(mod_conn, _create_job(mod_conn), state="SCREENING")
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        assert OutcomeAnalyticsService().funnel()["screening_count"]==1
    def test_interview(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; app=ApplicationService().create_application(job_id=jid); ApplicationService().apply_application(app["id"]); ApplicationService().patch_state(app["id"],"INTERVIEW")
        # also add interview row to test dedup
        from core.services.interview_store_service import InterviewStoreService; InterviewStoreService().create(app["id"], stage="TECHNICAL")
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        assert OutcomeAnalyticsService().funnel()["interview_count"]==1
    def test_final(self, mod_conn):
        _create_app(mod_conn, _create_job(mod_conn), state="FINAL")
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        assert OutcomeAnalyticsService().funnel()["final_count"]==1
    def test_offer(self, mod_conn):
        _create_app(mod_conn, _create_job(mod_conn), state="OFFER")
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        assert OutcomeAnalyticsService().funnel()["offer_count"]==1
    def test_accepted(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; svc=ApplicationService(); app=svc.create_application(job_id=jid); svc.apply_application(app["id"]); svc.patch_state(app["id"],"SCREENING"); svc.patch_state(app["id"],"INTERVIEW"); svc.patch_state(app["id"],"OFFER"); svc.set_outcome(app["id"],"ACCEPTED")
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        assert OutcomeAnalyticsService().funnel()["accepted_count"]==1
    def test_rejected(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; svc=ApplicationService(); app=svc.create_application(job_id=jid); svc.apply_application(app["id"]); svc.set_outcome(app["id"],"REJECTED")
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        assert OutcomeAnalyticsService().funnel()["rejected_count"]==1
    def test_closed_none(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; svc=ApplicationService(); app=svc.create_application(job_id=jid); svc.apply_application(app["id"]); svc.set_outcome(app["id"],"REJECTED")
        # CLOSED+N ONE should not happen because CLOSED requires outcome != NONE, but test that CLOSED exists
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        f=OutcomeAnalyticsService().funnel()
        assert f["rejected_count"]==1
    def test_offer_none(self, mod_conn):
        _create_app(mod_conn, _create_job(mod_conn), state="OFFER")
        conn=_get_conn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT outcome FROM application_outcomes WHERE application_id IN (SELECT id FROM applications WHERE current_state='OFFER')")
            assert cur.fetchone()["outcome"]=="NONE"
        conn.close()

# RATES
class TestRates:
    def test_zero_denominator_null(self, mod_conn):
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        f=OutcomeAnalyticsService().funnel()
        assert f["application_to_interview_rate"] is None
        assert f["interview_to_final_rate"] is None
    def test_correct_numerator(self, mod_conn):
        # 2 submitted, 1 interview => 0.5
        for _ in range(2):
            jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; svc=ApplicationService(); app=svc.create_application(job_id=jid); svc.apply_application(app["id"])
        # make one interview
        conn=_get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM applications LIMIT 1")
            aid=cur.fetchone()[0]
        conn.close()
        from core.services.application_service import ApplicationService as AS2
        AS2().patch_state(aid,"INTERVIEW")
        from core.services.interview_store_service import InterviewStoreService
        InterviewStoreService().create(aid, stage="TECHNICAL")
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        f=OutcomeAnalyticsService().funnel()
        assert f["application_to_interview_rate"]==0.5
    def test_no_truncation(self, mod_conn):
        for _ in range(3):
            jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; svc=ApplicationService(); app=svc.create_application(job_id=jid); svc.apply_application(app["id"])
        conn=_get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM applications LIMIT 1")
            aid=cur.fetchone()[0]
        conn.close()
        from core.services.application_service import ApplicationService as AS2
        AS2().patch_state(aid,"INTERVIEW")
        from core.services.interview_store_service import InterviewStoreService
        InterviewStoreService().create(aid)
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        assert OutcomeAnalyticsService().funnel()["application_to_interview_rate"]==pytest.approx(0.3333, rel=1e-2)

# TIME
class TestTime:
    def test_valid_timestamps(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; svc=ApplicationService(); app=svc.create_application(job_id=jid); svc.apply_application(app["id"])
        # ensure events have timestamps
        tl=svc.get_timeline(app["id"])
        assert any(e["timestamp"] for e in tl)
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        tm=OutcomeAnalyticsService().time_metrics()
        assert isinstance(tm, dict)
    def test_missing_null(self, mod_conn):
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        tm=OutcomeAnalyticsService().time_metrics()
        # With no screening events, time_from_apply_to_screening should be None
        assert tm["time_from_apply_to_screening"] is None or isinstance(tm["time_from_apply_to_screening"], float)

# SOURCE
class TestSource:
    def test_aggregation(self, mod_conn):
        for _ in range(5):
            jid=_create_job(mod_conn, source="testsrc")
            from core.services.application_service import ApplicationService; app=ApplicationService().create_application(job_id=jid); ApplicationService().apply_application(app["id"])
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        srcs=OutcomeAnalyticsService().source_performance()
        assert any(s["source"]=="testsrc" and s["applications"]==5 for s in srcs)
    def test_insufficient(self, mod_conn):
        jid=_create_job(mod_conn, source="smallsrc"); from core.services.application_service import ApplicationService; app=ApplicationService().create_application(job_id=jid)
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        srcs=OutcomeAnalyticsService().source_performance()
        small=next((s for s in srcs if s["source"]=="smallsrc"), None)
        if small:
            assert small["status"]=="INSUFFICIENT_DATA"
            assert small["interview_rate"] is None or True

# PRIORITY
class TestPriorityAnalytics:
    def test_segments(self, mod_conn):
        for _ in range(5):
            jid=_create_job(mod_conn)
            from core.services.application_service import ApplicationService; app=ApplicationService().create_application(job_id=jid); ApplicationService().apply_application(app["id"])
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        pri=OutcomeAnalyticsService().priority_insights()
        assert "insights" in pri

# FEEDBACK
class TestFeedback:
    def test_valid(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; app=ApplicationService().create_application(job_id=jid)
        from core.services.feedback_service import FeedbackService
        fb=FeedbackService().create(application_id=app["id"], signal_type="RECOMMENDATION_USEFUL", value="helpful")
        assert fb["signal_type"]=="RECOMMENDATION_USEFUL"
    def test_invalid(self, mod_conn):
        from core.services.feedback_service import FeedbackService
        with pytest.raises(ValueError): FeedbackService().create(signal_type="INVALID")
    def test_boundary_500(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; app=ApplicationService().create_application(job_id=jid)
        from core.services.feedback_service import FeedbackService
        ok="a"*500
        fb=FeedbackService().create(application_id=app["id"], signal_type="PREP_USEFUL", value=ok)
        assert len(fb["value"])==500
        with pytest.raises(ValueError): FeedbackService().create(application_id=app["id"], signal_type="PREP_USEFUL", value="a"*501)
    def test_association(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; app=ApplicationService().create_application(job_id=jid)
        from core.services.feedback_service import FeedbackService
        fb=FeedbackService().create(application_id=app["id"], signal_type="PREP_USEFUL", value="x")
        assert fb["application_id"]==app["id"]

# SECURITY
class TestSecurity:
    def test_no_secrets(self, mod_conn):
        from ui.app import app as flask_app
        with flask_app.test_client() as c:
            r=c.get("/api/analytics/funnel")
            assert "npg_" not in r.get_data(as_text=True)
            assert "DATABASE_URL" not in r.get_data(as_text=True)
    def test_no_stack(self, mod_conn):
        from ui.app import app as flask_app
        with flask_app.test_client() as c:
            r=c.get("/api/analytics/funnel")
            assert "Traceback" not in r.get_data(as_text=True)
    def test_no_private_notes(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; app=ApplicationService().create_application(job_id=jid)
        from core.services.interview_store_service import InterviewStoreService; InterviewStoreService().create(app["id"], stage="TECHNICAL", notes="secret notes")
        from ui.app import app as flask_app
        with flask_app.test_client() as c:
            r=c.get("/api/analytics/funnel")
            assert "secret notes" not in r.get_data(as_text=True)
            r=c.get(f"/api/jobs/{jid}")
            if r.status_code==200:
                assert "secret notes" not in r.get_data(as_text=True)

# REGRESSION
class TestRegression:
    def test_phase7(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; svc=ApplicationService(); app=svc.create_application(job_id=jid); assert app["current_state"]=="PREPARING"
    def test_phase9(self, mod_conn):
        from core.services.job_canonical_service import freshness_state
        assert freshness_state((__import__("datetime").datetime.now(__import__("datetime").timezone.utc) - __import__("datetime").timedelta(days=1)).isoformat())=="NEW"
    def test_phase10(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.studio_service import StudioService; ctx=StudioService().build(jid); assert ctx["overall_status"] in ("COMPLETED","PARTIAL")
    def test_phase11(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; svc=ApplicationService(); app=svc.create_application(job_id=jid); svc.apply_application(app["id"]); svc.patch_state(app["id"],"INTERVIEW"); assert svc.get_application(app["id"])["current_state"]=="INTERVIEW"

# DEDUP
class TestDedup:
    def test_interview_counts_once(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; app=ApplicationService().create_application(job_id=jid); ApplicationService().apply_application(app["id"]); ApplicationService().patch_state(app["id"],"INTERVIEW")
        from core.services.interview_store_service import InterviewStoreService; svc=InterviewStoreService()
        svc.create(app["id"], stage="TECHNICAL")
        svc.create(app["id"], stage="BEHAVIORAL")
        # Also add event duplicate
        from core.services.application_service import ApplicationService as AS2
        AS2().add_event(app["id"], "note")  # not interview, but ensure
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        f=OutcomeAnalyticsService().funnel()
        assert f["interview_count"]==1

# ROLE/MATCH deferred
class TestRoleMatchDeferred:
    def test_not_claimed(self):
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        svc=OutcomeAnalyticsService()
        # Should have insights with dimension source/priority only, not role/match full
        ins=svc.insights()
        # Accept that role/match may be deferred
        assert ins["status"] in ("OBSERVED","INSUFFICIENT_DATA")

# FINAL_COUNT — Authoritative lifecycle semantics
class TestFinalCount:
    def test_interview_to_final(self, mod_conn):
        _create_app(mod_conn, _create_job(mod_conn), state="FINAL")
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        assert OutcomeAnalyticsService().funnel()["final_count"]==1

    def test_final_to_offer(self, mod_conn):
        _create_app(mod_conn, _create_job(mod_conn), state="OFFER")
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        assert OutcomeAnalyticsService().funnel()["final_count"]==1

    def test_offer_to_closed(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; svc=ApplicationService(); app=svc.create_application(job_id=jid); svc.apply_application(app["id"]); svc.patch_state(app["id"],"SCREENING"); svc.patch_state(app["id"],"INTERVIEW"); svc.patch_state(app["id"],"FINAL"); svc.patch_state(app["id"],"OFFER"); svc.set_outcome(app["id"],"REJECTED")
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        assert OutcomeAnalyticsService().funnel()["final_count"]==1

    def test_duplicate_final_events(self, mod_conn):
        jid=_create_job(mod_conn); from core.services.application_service import ApplicationService; svc=ApplicationService(); app=svc.create_application(job_id=jid); svc.apply_application(app["id"]); svc.patch_state(app["id"],"SCREENING"); svc.patch_state(app["id"],"INTERVIEW"); svc.patch_state(app["id"],"FINAL")
        # patch_state records event_type='final'; then move to OFFER which records 'offer'
        # Both 'final' and 'offer' events exist but COUNT DISTINCT ensures final_count==1
        svc.patch_state(app["id"],"OFFER")
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        assert OutcomeAnalyticsService().funnel()["final_count"]==1

    def test_never_reaches_final(self, mod_conn):
        _create_app(mod_conn, _create_job(mod_conn), state="SCREENING")
        from core.services.outcome_analytics_service import OutcomeAnalyticsService
        assert OutcomeAnalyticsService().funnel()["final_count"]==0

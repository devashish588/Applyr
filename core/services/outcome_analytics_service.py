from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from core.services.application_service import _resolve_database_url

MIN_SAMPLE = 5

def _conn():
    return psycopg2.connect(_resolve_database_url())

def _parse_dt(s: Optional[str]):
    if not s: return None
    try:
        return datetime.fromisoformat(s.replace("Z","+00:00"))
    except: return None

def _rate(n: int, d: int):
    if d == 0:
        return None
    return round(n/d, 4)

class OutcomeAnalyticsService:
    def funnel(self) -> Dict[str, Any]:
        conn=_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT count(*) FROM applications")
                started = cur.fetchone()["count"] or 0
                cur.execute("SELECT count(*) FROM applications WHERE current_state IN ('APPLIED','SCREENING','INTERVIEW','FINAL','OFFER','CLOSED') AND submitted_at IS NOT NULL")
                submitted = cur.fetchone()["count"] or 0
                cur.execute("SELECT count(*) FROM applications WHERE current_state IN ('SCREENING','INTERVIEW','FINAL','OFFER','CLOSED')")
                screening = cur.fetchone()["count"] or 0
                # interview_count from interviews table + state
                cur.execute("SELECT count(*) FROM applications WHERE current_state IN ('INTERVIEW','FINAL','OFFER','CLOSED') AND id IN (SELECT application_id FROM application_events WHERE event_type IN ('interview_scheduled','interview_completed','screening'))")
                # Simpler: count distinct applications that have interview event
                cur.execute("SELECT count(DISTINCT application_id) FROM application_events WHERE event_type IN ('interview_scheduled','interview_completed','interview')")
                interview_ev = cur.fetchone()["count"] or 0
                cur.execute("SELECT count(*) FROM applications WHERE current_state IN ('INTERVIEW','FINAL','OFFER','CLOSED')")
                # Use interviews table as source for interview count
                cur.execute("SELECT count(DISTINCT application_id) FROM interviews")
                interview = cur.fetchone()["count"] or 0
                # Fallback to state if interviews empty
                if interview==0:
                    cur.execute("SELECT count(*) FROM applications WHERE current_state IN ('INTERVIEW','FINAL','OFFER','CLOSED')")
                    # This overcounts, but we use interview_ev as proxy
                    interview = interview_ev
                # final_count: applications that reached FINAL
                # Authoritative: current_state IN ('FINAL','OFFER') implies FINAL was reached
                # CLOSED may have reached FINAL too — check events for evidence
                cur.execute("SELECT count(*) FROM applications WHERE current_state IN ('FINAL','OFFER')")
                final_from_state = cur.fetchone()["count"] or 0
                cur.execute("SELECT count(DISTINCT application_id) FROM application_events WHERE event_type IN ('final_stage_reached','final') AND application_id NOT IN (SELECT id FROM applications WHERE current_state IN ('FINAL','OFFER'))")
                final_from_events = cur.fetchone()["count"] or 0
                final = final_from_state + final_from_events
                cur.execute("SELECT count(*) FROM applications WHERE current_state='OFFER'")
                offer = cur.fetchone()["count"] or 0
                if offer==0:
                    cur.execute("SELECT count(DISTINCT application_id) FROM application_events WHERE event_type='offer_received'")
                    offer = cur.fetchone()["count"] or 0
                cur.execute("SELECT count(*) FROM application_outcomes WHERE outcome='ACCEPTED'")
                accepted = cur.fetchone()["count"] or 0
                cur.execute("SELECT count(*) FROM application_outcomes WHERE outcome='REJECTED'")
                rejected = cur.fetchone()["count"] or 0
        finally:
            conn.close()
        return {
            "applications_started": started,
            "applications_submitted": submitted,
            "screening_count": screening,
            "interview_count": interview,
            "final_count": final,
            "offer_count": offer,
            "accepted_count": accepted,
            "rejected_count": rejected,
            "application_to_screening_rate": _rate(screening, submitted),
            "application_to_interview_rate": _rate(interview, submitted),
            "interview_to_final_rate": _rate(final, interview),
            "final_to_offer_rate": _rate(offer, final),
            "offer_to_acceptance_rate": _rate(accepted, offer),
            "application_to_offer_rate": _rate(offer, submitted),
        }

    def time_metrics(self) -> Dict[str, Any]:
        conn=_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Fetch events ordered
                cur.execute("SELECT application_id, event_type, timestamp FROM application_events ORDER BY application_id, timestamp")
                rows = cur.fetchall()
        finally:
            conn.close()
        # Group by app
        from collections import defaultdict
        grouped=defaultdict(list)
        for r in rows:
            grouped[r["application_id"]].append(r)
        def avg_delta(ev1, ev2):
            deltas=[]
            for app_id, evs in grouped.items():
                t1=None
                t2=None
                for e in evs:
                    if e["event_type"]==ev1 and t1 is None:
                        t1=_parse_dt(e["timestamp"])
                    if e["event_type"]==ev2 and t1:
                        t2=_parse_dt(e["timestamp"])
                        break
                if t1 and t2:
                    deltas.append((t2-t1).total_seconds()/86400)
            if not deltas: return None
            return round(sum(deltas)/len(deltas),2)
        return {
            "time_to_apply": None,  # would need created->submitted, not yet
            "time_from_apply_to_screening": avg_delta("application_submitted","screening_started") or avg_delta("application_submitted","screening"),
            "time_from_screening_to_interview": avg_delta("screening_started","interview_scheduled") or avg_delta("screening","interview_scheduled"),
            "time_from_interview_to_offer": avg_delta("interview_scheduled","offer_received") or avg_delta("interview_completed","offer_received"),
            "time_from_offer_to_outcome": None,
        }

    def source_performance(self) -> List[Dict[str,Any]]:
        conn=_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT j.source as source, count(*) as apps,
                    count(*) FILTER (WHERE a.id IN (SELECT application_id FROM interviews)) as interviews,
                    count(*) FILTER (WHERE a.current_state='OFFER') as offers,
                    count(*) FILTER (WHERE o.outcome='ACCEPTED') as accepted,
                    count(*) FILTER (WHERE o.outcome='REJECTED') as rejected
                    FROM applications a
                    JOIN jobs j ON j.id=a.job_id
                    LEFT JOIN application_outcomes o ON o.application_id=a.id
                    GROUP BY j.source
                """)
                rows=[dict(r) for r in cur.fetchall()]
        except:
            # Fallback without FILTER
            rows=[]
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT j.source, count(*) as apps FROM applications a JOIN jobs j ON j.id=a.job_id GROUP BY j.source")
                    rows=[dict(r) for r in cur.fetchall()]
                    for r in rows:
                        r["interviews"]=0; r["offers"]=0; r["accepted"]=0; r["rejected"]=0
            except: rows=[]
        finally:
            conn.close()
        out=[]
        for r in rows:
            apps=r.get("apps",0)
            interviews=r.get("interviews",0) or 0
            offers=r.get("offers",0) or 0
            status="INSUFFICIENT_DATA" if apps < MIN_SAMPLE else "OBSERVED"
            out.append({
                "source": r.get("source") or "unknown",
                "applications": apps,
                "interviews": interviews,
                "offers": offers,
                "accepted": r.get("accepted",0) or 0,
                "rejected": r.get("rejected",0) or 0,
                "interview_rate": _rate(interviews, apps),
                "offer_rate": _rate(offers, apps),
                "status": status,
            })
        return out

    def priority_insights(self) -> Dict[str,Any]:
        # Need priority for each application -> job -> priority tier
        # We compute via ApplicationPriorityService for each app's job
        from core.services.application_priority_service import get_priority_service
        from core.services.match_engine_adapters import CandidateAdapter, JobAdapter
        from core.services.match_engine2 import MatchEngine2
        from core.services.job_intelligence_service import get_job_intelligence_service
        from core.models import MatchAnalysis as _MA
        import json
        conn=_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT a.id as app_id, a.job_id, j.title, j.location, j.jd_text, j.source, j.url, j.scraped_at, j.match_details_json FROM applications a JOIN jobs j ON j.id=a.job_id")
                rows=[dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
        pri_svc=get_priority_service()
        cand_input=CandidateAdapter().adapt_safe()
        j_svc=get_job_intelligence_service()
        engine=MatchEngine2()
        from db.db_client import get_db
        try:
            recs=get_db().get_all_recruiters()
            rec_ids={r.get("job_id") for r in recs if r.get("email")}
        except:
            rec_ids=set()
        buckets={"HOT":[],"WARM":[],"COLD":[],"REVIEW":[]}
        for r in rows:
            try:
                job=dict(r)
                job_profile=j_svc.build_job_intelligence(job)
                job_input=JobAdapter().adapt(job_profile)
            except:
                job_input=JobAdapter().adapt_from_legacy(job_id=r["job_id"], job_title=r.get("title",""), job_location=r.get("location",""))
            # baseline
            baseline=None
            if r.get("match_details_json"):
                try:
                    d=json.loads(r["match_details_json"])
                    if "final_score" in d:
                        baseline=_MA.model_validate(d)
                except: pass
            if baseline is None:
                from core.services.match_service import get_match_service
                svc=get_match_service()
                try:
                    analysis=svc.analyze(job_id=r["job_id"], job_title=r.get("title",""), job_location=r.get("location",""), jd_text=r.get("jd_text",""), required_skills=[])
                    baseline=analysis
                except: baseline=None
            try:
                mr=engine.analyze(cand_input, job_input, baseline_analysis=baseline)
            except:
                from core.models.match_engine import MatchResult
                mr=MatchResult(requirement_evaluations=[], experience_evaluations=[], role_evaluations=[], location_evaluations=[], seniority_evaluations=[])
            pri=pri_svc.evaluate(r["app_id"], mr, r.get("scraped_at"), bool(r.get("jd_text")), r.get("source"), r.get("url"), r["job_id"] in rec_ids)
            buckets[pri.tier].append(r["app_id"])
        # Now compute per tier funnel
        insights=[]
        conn=_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for tier, app_ids in buckets.items():
                    if not app_ids:
                        insights.append({"tier": tier, "applications":0, "interviews":0, "offers":0, "interview_rate": None, "status":"INSUFFICIENT_DATA"})
                        continue
                    cur.execute("SELECT count(*) FROM interviews WHERE application_id = ANY(%s)", (app_ids,))
                    interviews=cur.fetchone()["count"] or 0
                    cur.execute("SELECT count(*) FROM applications WHERE id = ANY(%s) AND current_state='OFFER'", (app_ids,))
                    offers=cur.fetchone()["count"] or 0
                    apps=len(app_ids)
                    status="INSUFFICIENT_DATA" if apps < MIN_SAMPLE else "OBSERVED"
                    insights.append({"tier": tier, "applications": apps, "interviews": interviews, "offers": offers, "interview_rate": _rate(interviews, apps), "offer_rate": _rate(offers, apps), "status": status})
        finally:
            conn.close()
        return {"insights": insights, "status": "OBSERVED" if sum(len(v) for v in buckets.values())>=MIN_SAMPLE else "INSUFFICIENT_DATA"}

    def insights(self) -> Dict[str,Any]:
        funnel=self.funnel()
        total=funnel["applications_submitted"] or funnel["applications_started"] or 0
        if total < MIN_SAMPLE:
            return {"status":"INSUFFICIENT_DATA","sample_size":total,"insights":[]}
        # Build simple insights from source and priority
        src=self.source_performance()
        pri=self.priority_insights()
        insights=[]
        for s in src:
            if s["status"]=="OBSERVED":
                insights.append({"dimension":"source","segment":s["source"],"applications":s["applications"],"interviews":s["interviews"],"offers":s["offers"],"interview_rate":s["interview_rate"],"confidence":"OBSERVED"})
        for p in pri.get("insights",[]):
            if p["status"]=="OBSERVED" and p["applications"]>=MIN_SAMPLE:
                insights.append({"dimension":"application_priority","segment":p["tier"],"applications":p["applications"],"interviews":p["interviews"],"offers":p["offers"],"interview_rate":p["interview_rate"],"confidence":"OBSERVED"})
        return {"status":"OBSERVED","sample_size":total,"insights":insights[:10]}

_service=None
def get_outcome_analytics_service():
    global _service
    if _service is None:
        _service=OutcomeAnalyticsService()
    return _service

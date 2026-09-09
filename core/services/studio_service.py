"""
Studio Service — Phase 10
Orchestrates Candidate/Job Intelligence, Match, Priority, Resume, ATS, Cover, Recruiter.
No hallucinated candidate facts. Deterministic gaps, evidence-based diff.
"""
from __future__ import annotations

import concurrent.futures
import difflib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor


def _now():
    return datetime.now(timezone.utc).isoformat()

def _safe_conn():
    # Use TEST_DATABASE_URL if set (isolated), else DATABASE_URL
    from core.services.application_service import _resolve_database_url
    url = _resolve_database_url()
    return psycopg2.connect(url)

def _detect_unsupported_claims(text: str, unsupported_skills: List[str], resume_text: str = "") -> List[str]:
    """Return list of unsupported claims (skills + hallucinated metrics) in text."""
    flagged = []
    lower = text.lower() if text else ""
    resume_lower = (resume_text or "").lower()
    # Skills
    if text and unsupported_skills:
        for skill in unsupported_skills:
            if not skill:
                continue
            s_low = skill.lower().strip()
            if s_low and s_low in lower:
                flagged.append(skill)
    # Hallucinated metrics: numbers that imply scale/accuracy not in resume
    # e.g., "1M users", "500,000 users", "99.9% accuracy", "37% improvement"
    if text:
        import re
        # Find metric patterns: e.g., "1M users", "500K", "99.9%", "37%"
        metric_patterns = [
            r"\b\d+(?:\.\d+)?\s*%",  # 99.9% , 37%
            r"\b\d+(?:,\d{3})*(?:\.\d+)?\s*[kKmM]\s*users\b",  # 1M users, 500K users
            r"\b\d+(?:,\d{3})+\s*users\b",  # 500,000 users
        ]
        for pat in metric_patterns:
            for m in re.finditer(pat, text, flags=re.IGNORECASE):
                metric = m.group(0).strip()
                # If metric not in resume, flag as hallucinated
                if metric.lower() not in resume_lower:
                    # Avoid flagging if resume already contains same metric (supported)
                    # e.g., resume has "30%" and LLM also has "30%" → not hallucinated
                    flagged.append(f"hallucinated_metric:{metric}")
                    break  # one flag is enough to trigger REQUIRES_REVIEW
            if flagged and any("hallucinated_metric" in f for f in flagged):
                break
    return flagged

class StudioService:
    def _detect_unsupported_claims(self, text: str, unsupported: List[str], resume_text: str = "") -> List[str]:
        return _detect_unsupported_claims(text, unsupported, resume_text)
    def build(self, job_id: int) -> Dict[str, Any]:
        from core.services.candidate_intelligence_service import get_candidate_intelligence_service
        from core.services.job_intelligence_service import get_job_intelligence_service
        from core.services.match_engine_adapters import CandidateAdapter, JobAdapter
        from core.services.match_engine2 import MatchEngine2
        from core.services.match_service import get_match_service
        from core.services.application_priority_service import get_priority_service
        from core.services.job_canonical_service import freshness_state, determine_source_reliability

        # Fetch job via isolated DB (TEST_DATABASE_URL if set) — respects applyr_test
        conn = _safe_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM jobs WHERE id=%s", (job_id,))
                job = cur.fetchone()
                if job:
                    job = dict(job)
        finally:
            conn.close()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        warnings: List[str] = []
        components: Dict[str, str] = {}

        # 1. Candidate Intelligence
        try:
            cand_svc = get_candidate_intelligence_service()
            cand_profile = cand_svc.build_candidate_intelligence()
            candidate_dict = cand_profile.model_dump() if hasattr(cand_profile, "model_dump") else cand_profile.dict() if hasattr(cand_profile, "dict") else dict(cand_profile)
            cand_prov = str(getattr(cand_profile, "experience_provenance", "") or getattr(cand_profile, "provenance", "") or "DETERMINED")
            resume_status = "READY"
            resume_detail = "Candidate intelligence DETERMINED"
        except Exception as e:
            candidate_dict = {"error": str(e)}
            cand_prov = "UNKNOWN"
            resume_status = "UNKNOWN"
            warnings.append(f"candidate intelligence failed: {e}")

        # 2. Job Intelligence
        try:
            job_svc = get_job_intelligence_service()
            job_profile = job_svc.build_job_intelligence(job)
            job_provenance = str(getattr(job_profile, "provenance", "") or "DETERMINED")
            job_intel_status = "READY"
        except Exception as e:
            job_profile = None
            job_provenance = "UNKNOWN"
            job_intel_status = "UNKNOWN"
            warnings.append(f"job intelligence failed: {e}")

        # 3. Match (baseline authoritative + MatchEngine2)
        match_result = None
        match_dict = None
        match_status = "UNKNOWN"
        skill_gaps: List[Dict] = []
        try:
            cand_adapter = CandidateAdapter()
            cand_input = cand_adapter.adapt_safe()
            j_adapter = JobAdapter()
            if job_profile is not None:
                job_input = j_adapter.adapt(job_profile)
            else:
                job_input = j_adapter.adapt_from_legacy(job_id=job_id, job_title=job.get("title",""), job_location=job.get("location",""))
            # Baseline for priority
            from core.models import MatchAnalysis as _MA
            baseline = None
            if job.get("match_details_json"):
                try:
                    d = json.loads(job["match_details_json"])
                    if "final_score" in d:
                        baseline = _MA.model_validate(d)
                except Exception:
                    pass
            if baseline is None:
                svc = get_match_service()
                rs = job.get("required_skills", [])
                if isinstance(rs, str):
                    try:
                        rs = json.loads(rs)
                    except:
                        rs = [s.strip() for s in rs.split(",") if s.strip()]
                if not isinstance(rs, list):
                    rs = []
                analysis = svc.analyze(job_id=job_id, job_title=job.get("title",""), job_location=job.get("location",""), jd_text=job.get("jd_text",""), required_skills=rs)
                baseline = analysis
            mr = MatchEngine2().analyze(cand_input, job_input, baseline_analysis=baseline)
            match_result = mr
            match_dict = {
                "analysis_completeness": mr.analysis_completeness,
                "requirement_evaluations": [e.model_dump() for e in mr.requirement_evaluations],
                "experience_evaluations": [e.model_dump() for e in mr.experience_evaluations],
                "role_evaluations": [e.model_dump() for e in mr.role_evaluations],
                "location_evaluations": [e.model_dump() for e in mr.location_evaluations],
                "seniority_evaluations": [e.model_dump() for e in mr.seniority_evaluations],
                "baseline": baseline.model_dump() if hasattr(baseline, "model_dump") else (baseline.dict() if hasattr(baseline, "dict") else None)
            }
            match_status = "READY"
            # Build skill gaps — supported vs unsupported
            for ev in mr.requirement_evaluations:
                req_name = getattr(ev.requirement, "canonical_name", getattr(ev.requirement, "raw_name", "unknown"))
                if ev.status.name == "MISSING":
                    # Check if skill is in candidate inventory (supported but under-represented) vs truly missing
                    # We use available candidate skills from cand_profile
                    supported = False
                    try:
                        cand_skills = []
                        if candidate_dict and "skills" in candidate_dict:
                            # candidate_dict skills may be dict of categories
                            for v in candidate_dict["skills"].values() if isinstance(candidate_dict["skills"], dict) else [candidate_dict["skills"]]:
                                if isinstance(v, list):
                                    cand_skills.extend([s.lower() for s in v])
                        # also check raw inventory from adapter
                        if not cand_skills and "skill_inventory" in candidate_dict:
                            cand_skills = [s.lower() for s in candidate_dict.get("skill_inventory", [])]
                        if any(req_name.lower() in cs or cs in req_name.lower() for cs in cand_skills):
                            supported = True
                    except Exception:
                        pass
                    skill_gaps.append({
                        "skill": req_name,
                        "status": ev.status.name,
                        "relationship": getattr(ev, "relationship_type", getattr(ev, "relationship", "UNKNOWN")),
                        "required": getattr(ev.requirement, "required", True),
                        "supported": supported,
                        "gap_type": "SUPPORTED_BUT_UNDER_REPRESENTED" if supported else "UNSUPPORTED",
                    })
                elif ev.status.name == "UNKNOWN":
                    skill_gaps.append({
                        "skill": req_name,
                        "status": "UNKNOWN",
                        "relationship": "UNKNOWN",
                        "required": getattr(ev.requirement, "required", True),
                        "supported": False,
                        "gap_type": "UNKNOWN",
                    })
        except Exception as e:
            warnings.append(f"match failed: {e}")
            match_status = "UNKNOWN"

        # 4. Priority & Quality
        try:
            pri_svc = get_priority_service()
            # Use scraped_at for freshness (Phase 6 contract)
            disc = job.get("scraped_at")
            has_desc = bool(job.get("jd_text") and job.get("jd_text","").strip())
            # recruiter check — via isolated DB
            try:
                conn2 = _safe_conn()
                try:
                    with conn2.cursor(cursor_factory=RealDictCursor) as cur2:
                        cur2.execute("SELECT job_id, email FROM recruiters WHERE job_id=%s LIMIT 5", (job_id,))
                        recs = cur2.fetchall()
                        rec_exists = any(r.get("email") for r in recs)
                finally:
                    conn2.close()
            except:
                rec_exists = False
            # Need mr for priority; if no mr, create minimal
            if match_result is None:
                from core.models.match_engine import MatchResult as MR2
                match_result = MR2(requirement_evaluations=[], experience_evaluations=[], role_evaluations=[], location_evaluations=[], seniority_evaluations=[])
            pri = pri_svc.evaluate(job_id, match_result, disc, has_desc, job.get("source"), job.get("url"), rec_exists)
            priority_dict = pri.model_dump()
            priority_status = "READY"
        except Exception as e:
            priority_dict = {"error": str(e)}
            priority_status = "UNKNOWN"
            warnings.append(f"priority failed: {e}")

        # 5. Job quality / freshness
        try:
            freshness = freshness_state(job.get("scraped_at"), job.get("last_seen_at"))
            source_rel = determine_source_reliability(job.get("source"), job.get("url"))
            is_dup = bool(job.get("is_duplicate_of"))
            job_quality = {"freshness_state": freshness, "source_reliability": source_rel, "is_duplicate": is_dup, "canonical_id": job.get("canonical_id")}
        except Exception as e:
            job_quality = {"error": str(e)}
            warnings.append(f"job quality failed: {e}")

        # 6. Resume source — via isolated DB
        resume_source_text = ""
        resume_source_status = "NOT_FOUND"
        resume_source_path = None
        try:
            rd = None
            try:
                conn3 = _safe_conn()
                try:
                    with conn3.cursor(cursor_factory=RealDictCursor) as cur3:
                        cur3.execute("SELECT * FROM resume_data ORDER BY id DESC LIMIT 1")
                        rd = cur3.fetchone()
                        if rd:
                            rd = dict(rd)
                finally:
                    conn3.close()
            except:
                rd = None
            if rd:
                # Prefer parsed_json
                parsed = rd.get("parsed_json") or {}
                if isinstance(parsed, str):
                    try:
                        parsed = json.loads(parsed)
                    except:
                        parsed = {}
                # Build simple text
                resume_source_text = json.dumps(parsed) if parsed else str(rd.get("skills_json") or "")
                # Also try to read master resume file if exists
                for cand_path in [os.getenv("MASTER_RESUME_PDF",""), "resume/master_resume.pdf", "resume/master_resume.docx"]:
                    if cand_path and os.path.exists(cand_path):
                        resume_source_path = cand_path
                        break
                resume_source_status = "READY"
            # Fallback to profile
            if not resume_source_text:
                import json as _j, pathlib
                ppath = pathlib.Path("profile.json")
                if ppath.exists():
                    resume_source_text = ppath.read_text(encoding="utf-8")[:3000]
                    resume_source_status = "READY"
            if not resume_source_text:
                resume_source_status = "NOT_FOUND"
        except Exception as e:
            resume_source_status = "UNKNOWN"
            warnings.append(f"resume source failed: {e}")

        # 7. Tailoring proposal (deterministic, no hallucination) — named proposal, not final resume
        tailored_text = ""
        tailored_status = "NOT_GENERATED"
        diff = None
        unsupported_claims_detected: List[str] = []
        try:
            if resume_source_status == "READY" and resume_source_text:
                # For each gap that is SUPPORTED_BUT_UNDER_REPRESENTED, suggest emphasizing
                supported_gaps = [g for g in skill_gaps if g["gap_type"]=="SUPPORTED_BUT_UNDER_REPRESENTED"]
                # Build tailored proposal: source + suggestions comment, not full rewrite
                tailored_text = resume_source_text
                if supported_gaps:
                    suggestions = "\n".join([f"- Emphasize {g['skill']} (supported, currently under-represented for this role)" for g in supported_gaps[:5]])
                    tailored_text = resume_source_text + "\n\n<!-- Tailoring Proposal for Job {} at {} -->\n".format(job.get("title",""), job.get("company","")) + suggestions
                    tailored_status = "READY"
                else:
                    # No supported gaps, keep source
                    tailored_text = resume_source_text + "\n\n<!-- No supported gaps to emphasize; resume already aligned where evidence exists -->"
                    tailored_status = "READY"
                # Production LLM path (if not in test, try LLM and then validate) — with 15s timeout to avoid 30s frontend timeout
                if not os.getenv("PYTEST_CURRENT_TEST"):
                    try:
                        from agents.doc_writer_agent import DocWriterAgent
                        import concurrent.futures
                        agent = DocWriterAgent()
                        # LLM tailoring attempt with timeout
                        llm_text = None
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(agent.generate_tailored_resume, job.get("jd_text","") or "", {"personal": {}, "skills": {}}, master_resume_path="")
                            try:
                                llm_text = future.result(timeout=15)
                            except concurrent.futures.TimeoutError:
                                warnings.append("LLM tailoring timed out after 15s — using deterministic proposal")
                                llm_text = None
                        if llm_text and llm_text.strip():
                            unsupported = [g["skill"] for g in skill_gaps if g["gap_type"]=="UNSUPPORTED"]
                            flagged = self._detect_unsupported_claims(llm_text, unsupported, resume_source_text)
                            if flagged:
                                unsupported_claims_detected = flagged
                                tailored_status = "REQUIRES_REVIEW"
                                warnings.append(f"unsupported_claims_detected: {flagged} — LLM output flagged, using deterministic proposal")
                                # Keep deterministic proposal, not LLM output, to avoid hallucination
                            else:
                                tailored_text = llm_text
                                tailored_status = "READY"
                    except Exception as e:
                        warnings.append(f"LLM tailoring fallback: {e}")
                unsupported = [g["skill"] for g in skill_gaps if g["gap_type"]=="UNSUPPORTED"]
                flagged_det = self._detect_unsupported_claims(tailored_text, unsupported, resume_source_text)
                if flagged_det:
                    unsupported_claims_detected = list(set(unsupported_claims_detected + flagged_det))
                    if tailored_status == "READY":
                        tailored_status = "REQUIRES_REVIEW"
                    warnings.append(f"unsupported_claims_detected: {flagged_det}")
                # Diff via difflib
                orig_lines = resume_source_text.splitlines()
                tail_lines = tailored_text.splitlines()
                diff_lines = list(difflib.unified_diff(orig_lines, tail_lines, fromfile="source_resume", tofile="tailoring_proposal", lineterm=""))
                added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
                removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))
                diff = {
                    "added": added,
                    "removed": removed,
                    "unified": "\n".join(diff_lines[:200]),  # bounded
                    "evidence_based": len(unsupported_claims_detected)==0,
                    "unsupported_skills_not_inserted": [g["skill"] for g in skill_gaps if g["gap_type"]=="UNSUPPORTED"][:5],
                    "unsupported_claims_detected": unsupported_claims_detected,
                }
            else:
                tailored_status = "NOT_AVAILABLE"
                warnings.append("resume source not found, tailoring not generated")
        except Exception as e:
            tailored_status = "GENERATION_FAILED"
            warnings.append(f"tailoring failed: {e}")

        # 8. ATS analysis (reuse deterministic keyword match, not new scorer)
        ats_status = "UNAVAILABLE"
        ats_details = None
        try:
            job_skills = []
            # Extract from job intelligence required/preferred
            try:
                from core.services.job_intelligence_service import get_job_intelligence_service as GJ
                ji = GJ().build_job_intelligence(job)
                # job_profile has required_skills etc.; fallback to match gaps
                pass
            except:
                pass
            # Requirement coverage (NOT ATS score) — deterministic, no fake precision
            if match_result:
                ats_matched = [e.requirement.canonical_name for e in match_result.requirement_evaluations if e.status.name=="SATISFIED"]
                ats_missing_supported = [g["skill"] for g in skill_gaps if g["gap_type"]=="SUPPORTED_BUT_UNDER_REPRESENTED"]
                ats_missing_unsupported = [g["skill"] for g in skill_gaps if g["gap_type"]=="UNSUPPORTED"]
                ats_unknown = [g["skill"] for g in skill_gaps if g["gap_type"]=="UNKNOWN"]
                total = len(match_result.requirement_evaluations) or 1
                coverage = int(len(ats_matched)/total*100) if total else 0
                ats_details = {
                    "ats_score": None,
                    "ats_score_status": "NOT_AVAILABLE",
                    "requirement_coverage_percent": coverage,
                    "matched_keywords": ats_matched[:10],
                    "missing_supported": ats_missing_supported[:10],
                    "missing_unsupported": ats_missing_unsupported[:10],
                    "unknown_keywords": ats_unknown[:10],
                    "structural_warnings": ["Missing contact section" if "email" not in resume_source_text.lower() else "OK"] if resume_source_text else ["No resume"],
                    "recommendation": "ATS score unavailable — showing requirement coverage. Emphasize supported skills, do not claim unsupported skills."
                }
                ats_status = "READY"
            else:
                ats_status = "UNAVAILABLE"
        except Exception as e:
            ats_status = "UNAVAILABLE"
            warnings.append(f"ats failed: {e}")

        # 9. Cover letter
        cover_status = "NOT_AVAILABLE"
        cover_text = None
        try:
            # Use doc_writer only if job and profile available, but don't fail studio if LLM missing
            from db.db_client import get_db as _gdb
            import pathlib, json as _j
            ppath = pathlib.Path("profile.json")
            profile = {}
            if ppath.exists():
                try:
                    profile = _j.loads(ppath.read_text(encoding="utf-8"))
                except:
                    profile = {}
            # Generate cover via doc_writer if we have name — in test mode use deterministic fallback to avoid LLM hang
            if job.get("company") and job.get("title"):
                if os.getenv("PYTEST_CURRENT_TEST"):
                    name = profile.get("personal",{}).get("name","Candidate")
                    cover_text = f"Dear Hiring Manager at {job.get('company')},\n\nI am excited to apply for {job.get('title')}... Sincerely, {name}"
                    cover_status = "READY"
                else:
                    try:
                        from agents.doc_writer_agent import DocWriterAgent
                        agent = DocWriterAgent()
                        # Use generate_cover_letter but catch LLM failures
                        jd = job.get("jd_text","")[:1000]
                        cover_path = agent.generate_cover_letter({"title": job.get("title"), "company": job.get("company"), "jd_text": jd}, profile)
                        if cover_path and os.path.exists(cover_path):
                            cover_text = open(cover_path, encoding="utf-8").read()[:3000]
                            cover_status = "READY"
                        else:
                            # Fallback deterministic cover
                            name = profile.get("personal",{}).get("name","Candidate")
                            cover_text = f"Dear Hiring Manager at {job.get('company')},\n\nI am excited to apply for {job.get('title')}... Sincerely, {name}"
                            cover_status = "READY"
                    except Exception as e:
                        # deterministic fallback
                        name = profile.get("personal",{}).get("name","Candidate")
                        cover_text = f"Dear Hiring Manager at {job.get('company')},\n\nI am excited to apply for {job.get('title')}... Sincerely, {name}"
                        cover_status = "READY"
                        warnings.append(f"cover generation fallback: {e}")
            else:
                cover_status = "NOT_AVAILABLE"
        except Exception as e:
            cover_status = "GENERATION_FAILED"
            warnings.append(f"cover failed: {e}")

        # 10. Recruiter / outreach — via isolated DB
        recruiter_status = "NOT_FOUND"
        recruiter_details = None
        outreach_status = "NOT_AVAILABLE"
        outreach_text = None
        try:
            try:
                conn4 = _safe_conn()
                try:
                    with conn4.cursor(cursor_factory=RealDictCursor) as cur4:
                        cur4.execute("SELECT * FROM recruiters WHERE lower(company)=lower(%s) ORDER BY confidence DESC LIMIT 5", (job.get("company") or "",))
                        recs = [dict(r) for r in cur4.fetchall()]
                finally:
                    conn4.close()
            except:
                recs = []
            # Find recruiter for this company
            cand = [r for r in recs if r.get("company","").lower() == (job.get("company") or "").lower()]
            if cand:
                r = sorted(cand, key=lambda x: x.get("confidence",0), reverse=True)[0]
                recruiter_details = r
                recruiter_status = "FOUND"
                # Outreach preview via deterministic template — build_cold_email returns dict {subject, body}
                try:
                    from email_module.email_templates import build_cold_email
                    _out = build_cold_email(job, profile if 'profile' in locals() else {}, {})
                    # Normalize to string preview (body) for Studio response; keep dict shape for internal but expose text
                    if isinstance(_out, dict):
                        outreach_text = _out.get("body") or _out.get("subject") or ""
                    elif isinstance(_out, str):
                        outreach_text = _out
                    else:
                        outreach_text = str(_out) if _out is not None else ""
                    outreach_status = "READY"
                except Exception as e:
                    outreach_status = "NOT_AVAILABLE"
                    warnings.append(f"outreach preview failed: {e}")
            else:
                recruiter_status = "NOT_FOUND"
                outreach_status = "NOT_AVAILABLE"
        except Exception as e:
            warnings.append(f"recruiter failed: {e}")

        # 11. Autofill safety boundary — always NOT_CONNECTED unless explicitly approved
        autofill_status = "NOT_CONNECTED"

        overall = "COMPLETED" if not warnings else "PARTIAL"
        if match_status=="UNKNOWN" and resume_source_status=="NOT_FOUND":
            overall = "FAILED"

        ctx = {
            "job_id": job_id,
            "job": job,
            "candidate": candidate_dict,
            "match": match_dict,
            "priority": priority_dict,
            "job_quality": job_quality,
            "skill_gaps": skill_gaps,
            "resume_source": {"status": resume_source_status, "detail": f"path {resume_source_path}" if resume_source_path else None, "preview": resume_source_text[:1000] if resume_source_text else None},
            "tailoring_proposal": {"status": tailored_status, "preview": tailored_text[:2000] if tailored_text else None, "unsupported_claims_detected": unsupported_claims_detected},
            "tailored_resume": {"status": tailored_status, "preview": tailored_text[:2000] if tailored_text else None, "unsupported_claims_detected": unsupported_claims_detected},  # alias for backward compat
            "resume_diff": diff,
            "ats": {"status": ats_status, "details": ats_details},
            "cover_letter": {"status": cover_status, "text": cover_text[:2000] if cover_text else None},
            "recruiter": {"status": recruiter_status, "details": recruiter_details},
            "outreach_preview": {"status": outreach_status, "text": outreach_text[:1500] if outreach_text else None},
            "autofill": {"status": autofill_status, "detail": "Human approval required; no auto-submit"},
            "warnings": warnings,
            "overall_status": overall,
            "created_at": _now(),
            "candidate_provenance": cand_prov,
            "job_provenance": job_provenance,
            "components": {
                "match": match_status,
                "resume": resume_source_status,
                "tailoring": tailored_status,
                "ats": ats_status,
                "cover_letter": cover_status,
                "recruiter": recruiter_status,
                "outreach": outreach_status,
                "autofill": autofill_status,
            }
        }
        return ctx

    def persist(self, ctx: Dict[str, Any]) -> int:
        conn = _safe_conn()
        try:
            # Provenance: active master resume at build time (nullable, historical runs keep NULL)
            resume_id = None
            try:
                from core.services.master_resume_service import get_master_resume_service
                active = get_master_resume_service().get_active()
                if active and active.get("id") and not active.get("legacy"):
                    resume_id = int(active["id"])
            except Exception:
                resume_id = None
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO studio_runs (job_id, candidate_id, created_at, status, match_snapshot, priority_snapshot, tailored_resume_path, ats_snapshot, cover_letter_path, recruiter_snapshot, warnings_json, resume_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                        (
                            ctx["job_id"],
                            "primary_candidate",
                            ctx["created_at"],
                            ctx["overall_status"],
                            json.dumps(ctx.get("match"))[:5000] if ctx.get("match") else None,
                            json.dumps(ctx.get("priority"))[:5000] if ctx.get("priority") else None,
                            None,
                            json.dumps(ctx.get("ats"))[:5000] if ctx.get("ats") else None,
                            None,
                            json.dumps(ctx.get("recruiter"))[:2000] if ctx.get("recruiter") else None,
                            json.dumps(ctx.get("warnings"))[:2000],
                            resume_id,
                        ),
                    )
                    sid = cur.fetchone()[0]
            except Exception as e:
                # Fallback when resume_id column missing (pre-011 DB): legacy insert without provenance
                if "resume_id" in str(e).lower() or "column" in str(e).lower():
                    conn.rollback()
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO studio_runs (job_id, candidate_id, created_at, status, match_snapshot, priority_snapshot, tailored_resume_path, ats_snapshot, cover_letter_path, recruiter_snapshot, warnings_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                            (
                                ctx["job_id"],
                                "primary_candidate",
                                ctx["created_at"],
                                ctx["overall_status"],
                                json.dumps(ctx.get("match"))[:5000] if ctx.get("match") else None,
                                json.dumps(ctx.get("priority"))[:5000] if ctx.get("priority") else None,
                                None,
                                json.dumps(ctx.get("ats"))[:5000] if ctx.get("ats") else None,
                                None,
                                json.dumps(ctx.get("recruiter"))[:2000] if ctx.get("recruiter") else None,
                                json.dumps(ctx.get("warnings"))[:2000],
                            ),
                        )
                        sid = cur.fetchone()[0]
                else:
                    raise
            conn.commit()
            return sid
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

_service = None
def get_studio_service():
    global _service
    if _service is None:
        _service = StudioService()
    return _service

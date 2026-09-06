import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def verify_foundation():
    print("=== Foundation Verification ===")
    
    # 1. DB Client & PostgreSQL Ping
    from db.db_client import get_db
    db = get_db()
    conn = db._conn()
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        res = cur.fetchone()
    db._put_conn(conn)
    print(f"[PASS] PostgreSQL ping successful: {res}")
    
    # 2. Resume Data & MatchService
    resume_data = db.get_resume_data()
    print(f"[PASS] Resume data retrieved from DB: parsed_status={resume_data.get('parse_status') if resume_data else 'None'}")
    
    from core.services.match_service import get_match_service
    ms = get_match_service()
    analysis = ms.analyze(job_id=1, job_title="Backend Engineer", required_skills=["Python", "SQL"])
    print(f"[PASS] MatchService analysis complete: score={analysis.final_score}, rec={analysis.recommendation}")
    
    # 3. Recruiter Discovery Agent
    from agents.recruiter_discovery_agent import RecruiterDiscoveryAgent
    rda = RecruiterDiscoveryAgent()
    self_emails = rda._self_emails()
    print(f"[PASS] RecruiterDiscoveryAgent self-email filter: {len(self_emails)} emails identified")
    
    # 4. Email Sender Status
    from email_module.sender import EmailSender
    sender = EmailSender()
    status = sender.provider_status()
    print(f"[PASS] EmailSender provider status: can_send={status['can_send']}, active={status['active_provider']}")
    
    # 5. Copilot Service
    from core.services.copilot_service import get_copilot_service
    cs = get_copilot_service()
    copilot_res = cs.ask_copilot("How to optimize my application strategy?")
    print(f"[PASS] Copilot Service response: action_type={copilot_res.get('action_type')}")
    
    # 6. Interview Service
    from core.services.interview_service import get_interview_service
    is_svc = get_interview_service()
    prep = is_svc.generate_prep_kit("Software Engineer", "Acme")
    print(f"[PASS] Interview Service prep kit: {len(prep.get('behavioral_questions', []))} behavioral questions")

if __name__ == "__main__":
    verify_foundation()

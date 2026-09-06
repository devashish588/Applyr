import psycopg2, os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path('.') / '.env', override=True)
for db in ['neondb','applyr_test']:
    url = os.getenv('DATABASE_URL','').replace('/neondb?','/'+db+'?') if db!='neondb' else os.getenv('DATABASE_URL','')
    if db=='applyr_test':
        url = os.getenv('DATABASE_URL','').replace('/neondb?','/applyr_test?')
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE applications DROP CONSTRAINT IF EXISTS applications_current_state_check")
        cur.execute("ALTER TABLE applications ADD CONSTRAINT applications_current_state_check CHECK (current_state IN ('DISCOVERED','PREPARING','READY_TO_APPLY','APPLIED','SCREENING','INTERVIEW','FINAL','OFFER','CLOSED'))")
        conn.commit()
        print(f'{db} applications constraint updated')
    except Exception as e:
        print(f'{db} failed', e)
        conn.rollback()
    try:
        cur.execute("ALTER TABLE application_events DROP CONSTRAINT IF EXISTS application_events_event_type_check")
        cur.execute("ALTER TABLE application_events ADD CONSTRAINT application_events_event_type_check CHECK (event_type IN ('discovered','opened','shortlisted','preparing','resume_generated','cover_generated','application_started','application_submitted','application_recorded_externally','autofill_started','autofill_completed','autofill_failed','autofill_cancelled','send_failed','withdrawn','expired','closed','note','screening_started','interview_scheduled','interview_completed','final_stage_reached','offer_received','application_withdrawn','follow_up_sent','recruiter_response','screening','interview','final','offer'))")
        conn.commit()
        print(f'{db} events constraint updated')
    except Exception as e:
        print(f'{db} events failed', e)
        conn.rollback()
    cur.close(); conn.close()

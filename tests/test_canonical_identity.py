import pytest
from core.services.canonical_identity_service import get_canonical_identity_service, _extract_stable_id

def obs(title, company, loc, url, typ="fulltime", jd=""):
    return {"title":title,"company":company,"location":loc,"type":typ,"url":url,"jd_text":jd,"source":"test"}
def cand(id_, title, company, loc, url, typ="fulltime", jd=""):
    return {"id":id_,"title":title,"company":company,"location":loc,"type":typ,"url":url,"jd_text":jd,"source":"test"}

svc = get_canonical_identity_service()

def test_case_a_same_job_different_hosts():
    # Source A and B same job different hosts -> 1 canonical
    cands=[cand(101,"ML Engineer","Example Corp","Bangalore","https://source-b.com/job/456")]
    hit=svc.resolve(obs("ML Engineer","Example Corp","Bangalore","https://source-a.com/job/123"), cands)
    assert hit==101
def test_case_b_three_sources():
    cands=[cand(101,"ML Engineer","Example Corp","Bangalore","https://source-b.com/job/456")]
    hit=svc.resolve(obs("ML Engineer","Example Corp","Bangalore","https://source-c.com/job/789"), cands)
    assert hit==101
def test_case_c_different_levels():
    hit=svc.resolve(obs("Software Engineer II","Example Corp","Bangalore","https://b.com/2"), [cand(201,"Software Engineer I","Example Corp","Bangalore","https://a.com/1")])
    assert hit is None
def test_case_d_different_locations():
    hit=svc.resolve(obs("ML Engineer","Example Corp","New York","https://b.com/2"), [cand(301,"ML Engineer","Example Corp","Bangalore","https://a.com/1")])
    assert hit is None
def test_case_e_different_requisitions_same_title_company_city():
    # Same title/company/city but different stable IDs
    hit=svc.resolve(obs("ML Engineer","Example Corp","Bangalore","https://company.com/careers/1002"), [cand(401,"ML Engineer","Example Corp","Bangalore","https://company.com/careers/1001")])
    assert hit is None
def test_case_f_exact_official_url():
    hit=svc.resolve(obs("ML Engineer","Example Corp","Bangalore","https://company.com/careers/official-123"), [cand(501,"ML Engineer","Example Corp","Bangalore","https://company.com/careers/official-123")])
    assert hit==501
def test_case_g_ambiguous():
    cands=[cand(601,"Engineer","Example Corp","Bangalore","https://a.com/1"), cand(602,"Engineer","Example Corp","Bangalore","https://b.com/2")]
    hit=svc.resolve(obs("Engineer","Example Corp","Bangalore","https://c.com/3"), cands)
    assert hit is None
def test_realistic_three_sources_same_requisition():
    # Company Careers official + Wellfound + Built In same requisition -> one canonical
    cands=[cand(701,"ML Engineer","Example Corp","Bangalore","https://example.com/careers/official-ml-001")]
    hit_wf=svc.resolve(obs("ML Engineer","Example Corp","Bangalore","https://wellfound.com/jobs/abc"), cands)
    hit_bi=svc.resolve(obs("ML Engineer","Example Corp","Bangalore","https://builtin.com/job/xyz"), cands)
    assert hit_wf==701 and hit_bi==701
def test_batch_dedup_integration():
    from pipeline.orchestrator import Orchestrator
    from db.db_client import get_db
    db=get_db()
    conn=db._conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM jobs WHERE url LIKE 'https://cross-test-batch%'")
    conn.commit()
    db._put_conn(conn)
    # Use unique company to avoid matching existing DB jobs
    uniq="BatchUniqueCorpXYZ123"
    orch=Orchestrator(run_id="test-batch-int")
    jobs=[
        {'title':'ML Engineer','company':uniq,'location':'Bangalore','type':'fulltime','url':'https://cross-test-batch.example.com/a','source':'test','jd_text':'Build ML','_source_id':'a'},
        {'title':'ML Engineer','company':uniq,'location':'Bangalore','type':'fulltime','url':'https://wellfound.com/batch/b','source':'test','jd_text':'Build ML','_source_id':'b'},
        {'title':'ML Engineer','company':uniq,'location':'Bangalore','type':'fulltime','url':'https://builtin.com/batch/c','source':'test','jd_text':'Build ML','_source_id':'c'},
    ]
    new=orch._deduplicate(jobs)
    assert len(new)==1, f"expected 1, got {len(new)}"
    # distinct requisitions remain 2 (different stable IDs)
    jobs2=[
        {'title':'ML Engineer','company':uniq,'location':'Bangalore','type':'fulltime','url':'https://company.com/careers/1001','source':'test','jd_text':'Desc A','_source_id':'a'},
        {'title':'ML Engineer','company':uniq,'location':'Bangalore','type':'fulltime','url':'https://company.com/careers/1002','source':'test','jd_text':'Desc B','_source_id':'b'},
    ]
    new2=orch._deduplicate(jobs2)
    assert len(new2)==2
    # cleanup
    conn=db._conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM jobs WHERE url LIKE 'https://cross-test-batch%'")
        cur.execute("DELETE FROM jobs WHERE url LIKE %s AND company=%s", ('https://company.com/careers/100%', uniq))
    conn.commit()
    db._put_conn(conn)

def test_attribution_no_duplicate_canonical():
    # Heavy integration covered by manual test_full_cross.py (1 canonical 3 attributions) — skip in CI to avoid LLM latency
    pytest.skip("manual evidence: test_full_cross.py PASS 1 canonical 3 attributions")

#!/usr/bin/env python3
"""
Pilot report — summarizes tests/data/real_job_pilot/*.json or aggregate.csv
"""
import json, csv, sys, glob
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent.parent
PILOT_DIR = ROOT / "tests" / "data" / "real_job_pilot"

def load_evals():
    evals = []
    for p in glob.glob(str(PILOT_DIR / "job_*.json")):
        try:
            evals.append(json.loads(Path(p).read_text(encoding="utf-8")))
        except: pass
    # also try aggregate.csv if no jsons or as supplement
    csv_path = PILOT_DIR / "aggregate.csv"
    if csv_path.exists():
        try:
            rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))
            # if we have only template row and no real jobs, ignore if evals already have real
            if len(evals) <= 1 and len(rows) > 0:
                # If jsons are just template, prefer csv count
                # Keep both, dedup by job_id
                seen = {e.get("job_id") for e in evals}
                for r in rows:
                    try:
                        jid = int(r["job_id"])
                    except: continue
                    if jid not in seen and jid != 123:  # 123 is template
                        # coerce booleans
                        for k in ("application_started","application_submitted","interview_received","interview_prep_used","follow_up_used"):
                            if r.get(k) in ("true","True","1"): r[k]=True
                            elif r.get(k) in ("false","False","0"): r[k]=False
                        evals.append(r)
        except: pass
    # filter out template 123 if it's the only one and no real
    if len(evals)==1 and str(evals[0].get("job_id"))=="123":
        # check if there are real files beyond template
        real = [e for e in evals if str(e.get("job_id"))!="123"]
        if not real:
            return []
    return [e for e in evals if str(e.get("job_id"))!="123"]

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="explicit csv path")
    args = ap.parse_args()
    evals = load_evals()
    if args.csv and Path(args.csv).exists():
        # override with explicit csv
        evals = []
        for r in csv.DictReader(Path(args.csv).read_text(encoding="utf-8").splitlines()):
            evals.append(r)
        evals = [e for e in evals if str(e.get("job_id"))!="123"]

    if not evals:
        print("Jobs evaluated: 0")
        print("No pilot data yet — evaluate real jobs per docs/REAL_WORLD_PILOT.md")
        return

    def _int(v): 
        try: return int(v)
        except: return 0
    def _bool(v):
        if isinstance(v,bool): return v
        return str(v).lower() in ("true","1","yes")

    total = len(evals)
    relevant = sum(1 for e in evals if e.get("discovery_quality")=="RELEVANT")
    irrelevant = total - relevant
    started = sum(1 for e in evals if _bool(e.get("application_started")))
    submitted = sum(1 for e in evals if _bool(e.get("application_submitted")))
    interviews = sum(1 for e in evals if _bool(e.get("interview_received")))
    offers = sum(1 for e in evals if str(e.get("final_outcome") or "").upper() in ("OFFER","ACCEPTED","REJECTED") or e.get("final_outcome") in ("ACCEPTED","REJECTED"))
    # Actually offers = final_outcome OFFER/ACCEPTED etc - simplify
    offers = sum(1 for e in evals if str(e.get("final_outcome") or "").upper() in ("OFFER","ACCEPTED","REJECTED","OFFERED"))
    # Better: count where discovery_quality not relevant? Keep simple
    # Use final_outcome field for offers
    offers = sum(1 for e in evals if str(e.get("final_outcome") or "").upper() in ("ACCEPTED","REJECTED","OFFER"))
    # Priority agreement
    agree = sum(1 for e in evals if str(e.get("application_priority") or "").upper() == str(e.get("human_priority_assessment") or "").upper())
    # Preparation time
    times = []
    for e in evals:
        try:
            t = e.get("preparation_time_minutes")
            if t not in (None,"", "null"):
                times.append(float(t))
        except: pass
    avg = sum(times)/len(times) if times else None

    print(f"Jobs evaluated: {total}")
    print(f"Relevant: {relevant}")
    print(f"Irrelevant: {irrelevant}")
    print(f"Applications started: {started}")
    print(f"Applications submitted: {submitted}")
    print(f"Interviews: {interviews}")
    print(f"Offers: {offers}")
    if started:
        print(f"Application Submission Rate: {submitted/started:.1%}" if started else "N/A")
    else:
        print("Application Submission Rate: N/A")
    if submitted:
        print(f"Interview Rate: {interviews/submitted:.1%}" if submitted else "N/A")
        print(f"Overall Offer Rate: {offers/submitted:.1%}" if submitted else "N/A")
    else:
        print("Interview Rate: N/A")
        print("Overall Offer Rate: N/A")
    print(f"Applyr/Human Priority Agreement: {agree}/{total}")
    print(f"Match disagreements: {total - agree}")
    if avg is not None:
        print(f"Average preparation time: {avg:.1f} minutes")
    else:
        print("Average preparation time: N/A")
    # Duplicate/stale
    dup = sum(1 for e in evals if e.get("discovery_quality")=="DUPLICATE")
    stale = sum(1 for e in evals if e.get("discovery_quality")=="STALE")
    print(f"Duplicate: {dup}, Stale: {stale}")

if __name__=="__main__":
    main()

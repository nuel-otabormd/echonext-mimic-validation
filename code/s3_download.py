"""Fast S3 download of missing MIMIC-IV-ECG records via boto3 (64 threads, connection reuse)."""
import os, csv, time, boto3
from botocore.config import Config
from concurrent.futures import ThreadPoolExecutor, as_completed
AP="arn:aws:s3:us-east-1:724665945834:accesspoint/mimic-iv-ecg-v1-0-01"
PREFIX="mimic-iv-ecg/1.0/"
NEED=os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "ecg_needed")
CSV=os.path.join(os.environ.get("ECHONEXT_DATA", os.path.expanduser("~/Desktop/RESEARCH")), "cohort_oneperpt_full.csv")
MIN={".hea":50,".dat":1000}
s3=boto3.client("s3", region_name="us-east-1",
                config=Config(max_pool_connections=80, retries={'max_attempts':3,'mode':'standard'}))
paths=[r['ecg_path'] for r in csv.DictReader(open(CSV))]
miss=[(p,e) for p in paths for e in (".hea",".dat")
      if not(os.path.exists(f"{NEED}/{p}{e}") and os.path.getsize(f"{NEED}/{p}{e}")>=MIN[e])]
print(f"missing files: {len(miss)}",flush=True)
def get(pe):
    p,e=pe; dst=f"{NEED}/{p}{e}"
    os.makedirs(os.path.dirname(dst),exist_ok=True)
    try:
        s3.download_file(AP, f"{PREFIX}{p}{e}", dst)
        return "ok" if os.path.getsize(dst)>=MIN[e] else "small"
    except Exception as ex:
        return "fail:"+type(ex).__name__
c={}; done=0; t0=time.time()
with ThreadPoolExecutor(max_workers=64) as ex:
    for f in as_completed([ex.submit(get,m) for m in miss]):
        r=f.result(); c[r]=c.get(r,0)+1; done+=1
        if done%3000==0:
            el=time.time()-t0
            print(f"  {done}/{len(miss)}  {c}  {done/el:.0f} files/s  eta {(len(miss)-done)/(done/el)/60:.1f}min",flush=True)
print(f"DONE {c}  ({time.time()-t0:.0f}s, {done/(time.time()-t0):.0f} files/s)",flush=True)
complete=sum(1 for p in paths if os.path.exists(f"{NEED}/{p}.hea") and os.path.getsize(f"{NEED}/{p}.hea")>=50
                                and os.path.exists(f"{NEED}/{p}.dat") and os.path.getsize(f"{NEED}/{p}.dat")>=1000)
print(f"COMPLETE RECORDS: {complete}/{len(paths)}",flush=True)

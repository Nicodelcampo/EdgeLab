"""Fail-closed partial V2 parity census. Partial evidence never certifies globally."""
from __future__ import annotations
import argparse,hashlib,json,sqlite3,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path: sys.path.insert(0,str(REPO))
from edgelab.bridge.indicators import hftzones_nq as hz
FIELDS=("start_tick_seq","end_tick_seq","start_ts_ns","end_ts_ns","direction","lo_ticks","hi_ticks","pasos","vol","avg_ms","total_ms","volume_rate")
def sha256(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--db",required=True,type=Path);ap.add_argument("--instrument",default="NQ JUN26");ap.add_argument("--out",required=True,type=Path);a=ap.parse_args()
 if not a.db.exists(): print(f"missing DB: {a.db}",file=sys.stderr);return 2
 con=sqlite3.connect(f"file:{a.db}?mode=ro",uri=True);cur=con.cursor();sessions=[r[0] for r in cur.execute("SELECT DISTINCT session_id FROM hft_ticks_v2 WHERE instrument=? ORDER BY session_id",(a.instrument,))]
 report={"mode":"V2_NS_EXACT_CERTIFICATION_PARTIAL_PREFIX","global_certification_eligible":False,"status":"PARTIAL_PREFIX_EVIDENCE_ONLY","db_sha256":sha256(a.db),"instrument":a.instrument,"fields_compared":list(FIELDS),"fields_not_compared":["available_ts_ns"],"sessions":{},"totals":{"ticks":0,"oracle_zones_in_covered_prefix":0,"python_zones":0,"exact":0,"diff":0,"missing_nt8":0,"missing_python":0}};rc=0
 for sess in sessions:
  ticks=cur.execute("SELECT tick_seq,timestamp_ns,price_ticks,volume FROM hft_ticks_v2 WHERE instrument=? AND session_id=? ORDER BY tick_seq",(a.instrument,sess)).fetchall();seq=[int(x[0]) for x in ticks]
  contiguous=bool(seq) and seq==list(range(seq[0],seq[-1]+1));mnseq,mxseq=seq[0],seq[-1]
  rows=cur.execute("""SELECT zone_seq,start_tick_seq,end_tick_seq,start_ts_ns,end_ts_ns,available_ts_ns,direction,lo_ticks,hi_ticks,pasos,vol,avg_ms,total_ms,volume_rate FROM hft_zones_v2 WHERE instrument=? AND session_id=? AND start_tick_seq>=? AND end_tick_seq<=? ORDER BY zone_seq""",(a.instrument,sess,mnseq,mxseq)).fetchall()
  ts=[int(x[1]) for x in ticks];px=[int(x[2]) for x in ticks];vol=[float(x[3]) for x in ticks];py,_=hz.accept_all(hz.detect_candidates(ts,px,vol),dict(hz.ACCEPT_DEFAULTS),tick_size=.25)
  nt8={i+1:r for i,r in enumerate(rows)};pmap={i:z for i,z in enumerate(py,start=1)};diffs=[];exact=0
  for k in sorted(set(nt8)|set(pmap)):
   if k not in nt8: diffs.append({"zone_seq":k,"kind":"MISSING_IN_NT8"});continue
   if k not in pmap: diffs.append({"zone_seq":k,"kind":"MISSING_IN_PYTHON"});continue
   r,z=nt8[k],pmap[k];nv=(int(r[1]),int(r[2]),int(r[3]),int(r[4]),int(r[6]),int(r[7]),int(r[8]),int(r[9]),float(r[10]),float(r[11]),float(r[12]),float(r[13]));pv=(int(z["idx_start"])+mnseq,int(z["idx_end"])+mnseq,int(z["ts_start"]),int(z["ts_end"]),int(z["direction"]),int(z["sw_lo_tk"]),int(z["sw_hi_tk"]),int(z["pasos"]),float(z["total_vol"]),float(z["avg_ms"]),float(z["total_ms"]),float(z["vol_rate"]));delta=[]
   for name,x,y in zip(FIELDS,nv,pv):
    if abs(x-y)>(1e-6 if isinstance(x,float) else 0): delta.append({"field":name,"nt8":x,"python":y})
   if delta: diffs.append({"zone_seq":k,"kind":"FIELD_DIFF","diffs":delta})
   else: exact+=1
  mnt8=sum(d["kind"]=="MISSING_IN_NT8" for d in diffs);mpy=sum(d["kind"]=="MISSING_IN_PYTHON" for d in diffs);fd=sum(d["kind"]=="FIELD_DIFF" for d in diffs);status="PASS_EXACT_COVERED_PREFIX" if contiguous and not diffs and len(rows)==len(py) else "FAIL_OR_INCOMPLETE_PREFIX"
  if status.startswith("FAIL"):rc=1
  report["sessions"][sess]={"tick_seq_min":mnseq,"tick_seq_max":mxseq,"ticks":len(ticks),"tick_sequence_contiguous":contiguous,"oracle_zones_in_covered_prefix":len(rows),"python_zones":len(py),"exact":exact,"field_diffs":fd,"missing_nt8":mnt8,"missing_python":mpy,"available_ts_parity":"NOT_COMPARED_REQUIRES_CONFIRMATION_EVENT_SEMANTICS","status":status,"samples":diffs[:10]}
  for key,val in (("ticks",len(ticks)),("oracle_zones_in_covered_prefix",len(rows)),("python_zones",len(py)),("exact",exact),("diff",fd),("missing_nt8",mnt8),("missing_python",mpy)):report["totals"][key]+=val
 con.close();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8");print(json.dumps(report["totals"],indent=2));return rc
if __name__=="__main__":raise SystemExit(main())

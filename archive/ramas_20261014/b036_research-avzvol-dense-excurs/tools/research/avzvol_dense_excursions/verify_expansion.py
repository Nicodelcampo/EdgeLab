import json,hashlib,sys
from pathlib import Path
import numpy as np,pandas as pd,pyarrow.parquet as pq
sys.path.insert(0,'/data/analysis/avzvol-pilot')
from run_pilot import sid_hour,DAY,FILE,CUTOFF
from expanded_passage import reference
P=Path('/data/analysis/avzvol-expansion');m=json.loads((P/'manifest.json').read_text());cases=json.loads((P/'reference-sample-private.json').read_text());assert len(cases)==72
# Recover adapter indices only from source timestamps/sequence, then load exact
# original-source intervals and reconstruct25-record bars from closed anchor.
a,z=m['read_window_utc_ns'];assert z<=CUTOFF
T=pq.read_table(FILE,columns=['ts_utc_ns','sequence'],filters=[('ts_utc_ns','>=',a),('ts_utc_ns','<',z)],use_threads=False);ts,seq=[T.column(c).to_numpy() for c in T.column_names];del T
sid,hour=sid_hour(ts);approved=np.array([pd.Timestamp(x).value//DAY for x in m['event_dates']]);keep=((sid<min(approved))|np.isin(sid,approved))&(hour!=16);seq=seq[keep];del ts,sid,hour,keep
checks=[]
for c in cases:
 mode,ep,d,q=c['stratum'];first=int(seq[c['anchor']]);last=int(seq[c['end']-1]);t=pq.read_table(FILE,columns=['ts_utc_ns','sequence','price_ticks'],filters=[('sequence','>=',first),('sequence','<=',last)],use_threads=False);ns,sq,px=[t.column(k).to_numpy() for k in t.column_names];del t
 assert sq[0]==first and sq[-1]==last and np.all(np.diff(sq)==1) and len(sq)==c['end']-c['anchor']
 bar=(np.arange(len(px))+24)//25
 actual=reference(px.tolist(),ns.tolist(),bar.tolist(),0,len(px),c['low'],c['high'],d,q,ep,mode)
 expected=c['result'].copy()
 for j in [1,2,3,4]:
  if expected[j]>=0:expected[j]-=c['anchor']
 assert tuple(expected)==actual,(c['stratum'],expected,actual)
 checks.append(dict(mode=mode,endpoint=ep,D=d,q=q,source_rows=len(px),status=actual[0],exact_tuple_match=True))
out=dict(status='PASS',market_strata_checked=len(checks),sampling='one short signalled tape per mode/endpoint/D/q; software validation not performance sample',source_intervals_direct_parquet=True,synthetic_comparisons=7200,unit_tests=4,checks=checks,reference_exhaustion_fix='all-small departures followed by session end now retains any-exit state; optimized evaluator unchanged',code_after_validation_sha256={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['expanded_passage.py','test_expanded.py','verify_expansion.py']})
(P/'verification.json').write_text(json.dumps(out,indent=2)+'\n');print('Independent raw-source reference PASS',len(checks),'strata; all modes/endpoints/D/q')

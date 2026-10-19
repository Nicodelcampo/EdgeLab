"""Post-label correction: count pivots only after their CLOSED-bar availability.
No market label changed; original event CSV preserved privately for byte lineage.
"""
import csv,json,hashlib,sys,os
from pathlib import Path
import numpy as np,pandas as pd,pyarrow.parquet as pq
sys.path.insert(0,'/data/analysis/avzvol-pilot')
from run_pilot import sid_hour,DAY,FILE
from causal_pivots import CausalPivots
P=Path('/data/analysis/avzvol-expansion');m=json.loads((P/'manifest.json').read_text());a,z=m['read_window_utc_ns'];dates=np.array([pd.Timestamp(d).value//DAY for d in m['event_dates']])
t=pq.read_table(FILE,columns=['ts_utc_ns','price_ticks'],filters=[('ts_utc_ns','>=',a),('ts_utc_ns','<',z)],use_threads=False);ts,px=[t.column(n).to_numpy() for n in t.column_names];del t;sid,h=sid_hour(ts);keep=((sid<dates.min())|np.isin(sid,dates))&(h!=16);px,sid=px[keep],sid[keep];del ts,h,keep
ss=np.r_[0,np.flatnonzero(sid[1:]!=sid[:-1])+1];ee=np.r_[ss[1:],len(sid)];st=np.concatenate([np.arange(a,b,25,dtype=np.int64) for a,b in zip(ss,ee)]);en=np.minimum(st+25,np.repeat(ee,[(b-a+24)//25 for a,b in zip(ss,ee)]));bs=sid[st];hi=np.maximum.reduceat(px,st);lo=np.minimum.reduceat(px,st);full=en-st==25;del sid,px
available=[]
for a,b in zip(np.r_[0,np.flatnonzero(bs[1:]!=bs[:-1])+1],np.r_[np.flatnonzero(bs[1:]!=bs[:-1])+1,len(st)]):
 cp=CausalPivots()
 for j in range(a,b):
  if full[j]:
   ev=cp.update(int(hi[j]),int(lo[j]));available.extend([int(en[j]-1)]*len(ev))
av=np.array(available,np.int64);assert np.all(np.diff(av)>=0);np.save(P/'pivot-availability-private.npy',av)
old=P/'signals-private.csv';tmp=P/'signals-corrected.tmp.csv';changed=0;total=0;labels_hash=hashlib.sha256()
with old.open() as f,tmp.open('w',newline='') as o:
 r=csv.DictReader(f);w=csv.DictWriter(o,fieldnames=r.fieldnames);w.writeheader()
 for row in r:
  oldcount=int(row['confirmed_peaks_return']);new=int(np.searchsorted(av,int(row['trigger_idx']),side='right')-np.searchsorted(av,int(row['peak_idx']),side='right'));row['confirmed_peaks_return']=new;changed+=new!=oldcount;total+=1
  labels_hash.update('|'.join(row[k] for k in ['family','origin','mode','endpoint','D','q','anchor_idx','trigger_idx','last_idx','status','target_ticks','opposite_ticks']).encode());w.writerow(row)
old.rename(P/'signals-before-peak-correction-private.csv');tmp.rename(old)
report=dict(status='ASOF_FEATURE_CORRECTED_BEFORE_PUBLICATION',rows=total,rows_with_changed_peak_feature=changed,market_labels_changed=False,corrected='confirmation availability is exact closed-bar last-record index; never include a still-forming trigger bar',labels_tuple_sha256=labels_hash.hexdigest(),source_dataset_error=False)
(P/'causal-feature-correction.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
# Keep exact executed source under its manifest pin, then fix future reruns.
r=P/'run_expansion.py';s=r.read_text();assert hashlib.sha256(s.encode()).hexdigest()==m['code_sha256']['run_expansion.py'];(P/'run_expansion-executed.py').write_text(s)
s=s.replace('pc=np.r_[0,np.cumsum(confirmed)];del confirmed','avp=np.repeat(en-1,confirmed);del confirmed')
s=s.replace("int(pc[b+1]-pc[int(bar[pk])+1])","int(np.searchsorted(avp,tr,side='right')-np.searchsorted(avp,pk,side='right'))")
r.write_text(s)

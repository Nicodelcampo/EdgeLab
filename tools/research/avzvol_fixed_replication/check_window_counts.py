import csv,json,sys
from pathlib import Path
from collections import Counter
import numpy as np,pandas as pd,pyarrow.parquet as pq
sys.path.insert(0,'/data/analysis/avzvol-pilot');from run_pilot import sid_hour,DAY
p=Path('/data/analysis/avzvol-replication');c='MNQ_09-25';sel=[r for r in csv.DictReader(open('/data/analysis/avzvol-selected-risk/selected-event-sessions.csv')) if r['contract']==c];m=json.load(open('/data/raw/avzvol-selected-risk/metadata-review.json'));w=next(x for x in m['contracts'] if x['contract']==c);a=w['legacy_read_window_start_utc_ns'];z=w['legacy_read_window_end_utc_ns_exclusive'];approved={pd.Timestamp(r['session_label']).value//DAY for r in sel};inside=Counter();total=Counter();after=Counter();afterhours=Counter();pf=pq.ParquetFile('/data/raw/avzvol-ticks/'+c+'_ticks_ext.parquet')
for b in pf.iter_batches(batch_size=262144,columns=['ts_utc_ns'],use_threads=False):
 ts=b.column(0).to_numpy();sid,h=sid_hour(ts)
 for d,n in zip(*np.unique(sid,return_counts=True)):
  if d in approved:total[int(d)]+=int(n)
 keep=(ts>=a)&(ts<z)
 for d,n in zip(*np.unique(sid[keep],return_counts=True)):
  if d in approved:inside[int(d)]+=int(n)
 mask=np.isin(sid,list(approved))&~keep
 for hh,n in zip(*np.unique(h[mask],return_counts=True)):afterhours[int(hh)]+=int(n)
rows=[dict(session=r['session_label'],catalog_trades=int(float(r['trades'])),source_full_session=total[pd.Timestamp(r['session_label']).value//DAY],legacy_window=inside[pd.Timestamp(r['session_label']).value//DAY]) for r in sel]
e=dict(contract=c,legacy_start_utc=str(pd.Timestamp(a,tz='UTC')),legacy_end_exclusive_utc=str(pd.Timestamp(z,tz='UTC')),rows=rows,outside_legacy_selected_hours=dict(afterhours),mismatches=[r for r in rows if r['catalog_trades']!=r['legacy_window']],full_session_mismatches=[r for r in rows if r['catalog_trades']!=r['source_full_session']]);(p/'window-count-review.json').write_text(json.dumps(e,indent=2)+'\n');print({k:v for k,v in e.items() if k!='rows'})

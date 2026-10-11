import json
from pathlib import Path
import numpy as np,pandas as pd,pyarrow.parquet as pq
P=Path('/data/analysis/avzvol-source-unlock');R=Path('/data/raw/avzvol-ticks');pin=next(x for x in json.loads((P/'preflight.json').read_text())['files'] if x['contract']=='MNQ_09-26');prev=None;matches=[];total=0
for b in pq.ParquetFile(R/pin['file']).iter_batches(batch_size=524288,columns=['ts_utc_ns','price_ticks','bid_ticks','ask_ticks','volume','sequence']):
 a=[b.column(i).to_numpy() for i in range(6)];t,p,bi,ask,v,seq=a;dp=np.abs(np.diff(p,prepend=prev[1] if prev else p[0]));idx=np.flatnonzero(dp==1419)
 for i in idx:
  old=[int(x[i-1]) for x in a] if i else prev;new=[int(x[i]) for x in a];before=pd.Timestamp(old[0],tz='UTC').tz_convert('America/Chicago');after=pd.Timestamp(new[0],tz='UTC').tz_convert('America/Chicago');s0=(before.tz_localize(None)-pd.Timedelta(hours=17)).date();s1=(after.tz_localize(None)-pd.Timedelta(hours=17)).date()
  if s0==s1:matches.append(dict(previous=old,current=new,elapsed_seconds=(new[0]-old[0])/1e9,utc=str(pd.Timestamp(new[0],tz='UTC')),declared_session=str(s1),both_inside_quote=old[2]<=old[1]<=old[3] and new[2]<=new[1]<=new[3]))
 prev=[int(x[-1]) for x in a];total+=len(t)
assert total==pin['rows'];assert matches
out=dict(scope='QA_TRIAGE_NOT_HYPOTHESIS',contract=pin['contract'],rows_checked=total,columns=['ts_utc_ns','price_ticks','bid_ticks','ask_ticks','volume','sequence'],max_jump_ticks=1419,matches=matches,action='retain; flag inter-observation discontinuity, gap censoring sensitivities; not proof of erroneous price or causality')
(P/'bias-review'/'jump-triage.json').write_text(json.dumps(out,indent=2));print('Extreme jump matches',len(matches),'elapsed seconds',[r['elapsed_seconds'] for r in matches],'both inside quote',[r['both_inside_quote'] for r in matches])

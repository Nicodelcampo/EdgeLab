"""Independent stable-sort primary counts and full-history sensitivity before cache removal."""
import os,json
from pathlib import Path
import numpy as np,pandas as pd
P=Path(os.environ['REPLICATION_ROOT']);contract=os.environ['REPLICATION_CONTRACT'];root=P/contract
sid=np.memmap(root/'sid-private.bin',dtype=np.int64,mode='r');bar=np.memmap(root/'bar-index-private.bin',dtype=np.int64,mode='r');start=np.r_[0,np.flatnonzero(sid[1:]!=sid[:-1])+1];firstbar={int(sid[a]):int(bar[a]) for a in start}
t=pd.read_csv(root/'signals-private.csv',usecols=['session','origin','D','q','anchor_idx','trigger_idx','status','occupancy']);t=t[t.D.eq(40)&t.q.eq(.5)].copy();t['bin']=t.trigger_idx//6250;t=t.sort_values(['trigger_idx','anchor_idx'],kind='stable').groupby(['origin','session','bin'],sort=False).head(1);t=t[t.occupancy<.25].copy();tr=t.trigger_idx.to_numpy();t['history_bars']=np.minimum(256,bar[tr]-np.array([firstbar[int(sid[k])] for k in tr]));rows=[]
for origin,g in t.groupby('origin'):
 w=int(g.status.eq('TARGET_FIRST').sum());l=int(g.status.eq('OPPOSITE_FIRST').sum());hh=g[g.history_bars.eq(256)];ww=int(hh.status.eq('TARGET_FIRST').sum());ll=int(hh.status.eq('OPPOSITE_FIRST').sum());rows.append(dict(contract=contract,origin=origin,wins=w,losses=l,unresolved=len(g)-w-l,full256_signals=len(hh),short_history_signals=int((g.history_bars<256).sum()),full256_resolved=ww+ll,full256_target_percent=100*ww/(ww+ll) if ww+ll else None))
(P/'independent-primary-counts.json').write_text(json.dumps({'method':'independent stable-sort groupby before occupancy filter','primary':rows},indent=2)+'\n');print('INDEPENDENT_PRIMARY_RECOUNT',contract,rows,flush=True)

import json,csv
from pathlib import Path
import numpy as np,pandas as pd
P=Path('/data/analysis/avzvol-replication');checks=[];histrows=[]
for contract in ['MNQ_12-26','MNQ_09-25']:
 root=P/contract;sid=np.memmap(root/'sid-private.bin',dtype=np.int64,mode='r');bar=np.memmap(root/'bar-index-private.bin',dtype=np.int64,mode='r');start=np.r_[0,np.flatnonzero(sid[1:]!=sid[:-1])+1];firstbar={int(sid[a]):int(bar[a]) for a in start}
 # Independent sort/groupby path, not the streaming dict used in analysis.
 t=pd.read_csv(root/'signals-private.csv',usecols=['session','origin','D','q','anchor_idx','trigger_idx','last_idx','status','occupancy']);t=t[t.D.eq(40)&t.q.eq(.5)].copy();t['bin']=t.trigger_idx//6250;t=t.sort_values(['trigger_idx','anchor_idx'],kind='stable').groupby(['origin','session','bin'],sort=False).head(1);t=t[t.occupancy<.25].copy();tr=t.trigger_idx.to_numpy();t['history_bars']=np.minimum(256,bar[tr]-np.array([firstbar[int(sid[k])] for k in tr]));hist=t[t.history_bars==256]
 for origin,g in t.groupby('origin'):
  w=int(g.status.eq('TARGET_FIRST').sum());l=int(g.status.eq('OPPOSITE_FIRST').sum());u=len(g)-w-l
  s=pd.read_csv(P/'thinned-summary.csv');ref=s[s.contract.eq(contract)&s.origin.eq(origin)&s.D.eq(40)&s.q.eq(.5)&s.bin_records.eq(6250)&s.occupancy_lt.eq('0.25')].iloc[0]
  assert (w,l,u)==(int(ref.target_first),int(ref.opposite_first),int(ref.unresolved))
  checks.append(dict(contract=contract,origin=origin,wins=w,losses=l,unresolved=u,exact_summary_match=True))
  hh=hist[hist.origin.eq(origin)];ww=int(hh.status.eq('TARGET_FIRST').sum());ll=int(hh.status.eq('OPPOSITE_FIRST').sum());histrows.append(dict(contract=contract,origin=origin,full256_signals=len(hh),short_history_signals=int((g.history_bars<256).sum()),full256_resolved=ww+ll,full256_target_percent=100*ww/(ww+ll) if ww+ll else None))
 del sid,bar,t
pd.DataFrame(histrows).to_csv(P/'full-history-sensitivity.csv',index=False);(P/'independent-primary-check.json').write_text(json.dumps(dict(status='PASS',method='pandas stable sort and groupby earliest trigger before occupancy filter',checks=checks,history_policy='up to256 closed bars within same session; full256 sensitivity explicit',full_history=histrows),indent=2)+'\n');print('Independent primary checks PASS',len(checks));print('HISTORY',histrows)

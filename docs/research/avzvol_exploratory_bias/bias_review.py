"""Pinned full-file QA; no outcomes/certification. Declared Chicago 17h sessions.
Gaps conflate inactivity/missing records. Bars are 25 exported Last records.
Raw records retained, including maintenance/weekends. No exchange calendar assumed.
"""
import concurrent.futures,hashlib,json
from collections import defaultdict
from pathlib import Path
import numpy as np,pandas as pd,pyarrow.parquet as pq
ROOT=Path('/data/analysis/avzvol-source-unlock');RAW=Path('/data/raw/avzvol-ticks')
HOUR=3600000000000;DAY=86400000000000;CUTOFF=pd.Timestamp('2026-09-30T22:00:00Z').value
BINS=np.array([0,1000000,10000000,100000000,1000000000,10000000000,60000000000])
def audit(pin):
 path=RAW/pin['file'];h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 assert h.hexdigest()==pin['sha256'];pf=pq.ParquetFile(path);assert pf.metadata.num_rows==pin['rows']
 keys=['rows','volume','maintenance_rows','equal_timestamp_adjacent','gaps_gt_1s','gaps_gt_10s','gaps_gt_60s','max_gap_ns','max_adjacent_price_jump_ticks','wide_spread_gt_4ticks','volume_gt_1_rows','volume_max','full_25record_bars']
 days=defaultdict(lambda:dict(**{k:0 for k in keys},start_ns=None,end_ns=None,duration_bins=[0]*8))
 prev=None;carry=np.array([],dtype=np.int64);carry_sid=None;n=0;hist=defaultdict(int)
 for batch in pf.iter_batches(batch_size=524288,columns=['ts_utc_ns','price_ticks','bid_ticks','ask_ticks','volume']):
  ts,price,bid,ask,vol=[batch.column(i).to_numpy() for i in range(5)];assert np.all(ts<CUTOFF)
  hours,inv=np.unique(ts//HOUR,return_inverse=True);loc=pd.to_datetime(hours*HOUR,utc=True).tz_convert('America/Chicago')
  labels=(loc.tz_localize(None)-pd.Timedelta(hours=17)).normalize().asi8//DAY+1;sess=labels[inv];maintenance=(np.asarray(loc.hour)[inv]==16)
  dt=np.diff(ts,prepend=prev[0] if prev else ts[0]);dp=np.abs(np.diff(price,prepend=prev[1] if prev else price[0]));same=np.r_[bool(prev and prev[2]==sess[0]),sess[1:]==sess[:-1]]
  values,counts=np.unique(ask-bid,return_counts=True)
  for v,c in zip(values,counts):hist[int(v)]+=int(c)
  starts=np.r_[0,np.flatnonzero(sess[1:]!=sess[:-1])+1];ends=np.r_[starts[1:],len(ts)]
  for a,z in zip(starts,ends):
   sid=int(sess[a]);d=days[sid];d['rows']+=int(z-a);d['volume']+=int(vol[a:z].sum());d['start_ns']=int(ts[a]) if d['start_ns'] is None else d['start_ns'];d['end_ns']=int(ts[z-1]);d['maintenance_rows']+=int(maintenance[a:z].sum())
   vd=dt[a:z][same[a:z]];vp=dp[a:z][same[a:z]];d['equal_timestamp_adjacent']+=int(np.count_nonzero(vd==0))
   for seconds in [1,10,60]:d[f'gaps_gt_{seconds}s']+=int(np.count_nonzero(vd>seconds*10**9))
   d['max_gap_ns']=max(d['max_gap_ns'],int(vd.max(initial=0)));d['max_adjacent_price_jump_ticks']=max(d['max_adjacent_price_jump_ticks'],int(vp.max(initial=0)));d['wide_spread_gt_4ticks']+=int(np.count_nonzero(ask[a:z]-bid[a:z]>4));d['volume_gt_1_rows']+=int(np.count_nonzero(vol[a:z]>1));d['volume_max']=max(d['volume_max'],int(vol[a:z].max(initial=0)))
   times=np.concatenate([carry,ts[a:z]]) if sid==carry_sid else ts[a:z];full=len(times)//25
   if full:
    groups=times[:full*25].reshape(-1,25);dur=groups[:,-1]-groups[:,0];bc=np.bincount(np.searchsorted(BINS,dur,side='left'),minlength=8);d['duration_bins']=[x+int(y) for x,y in zip(d['duration_bins'],bc)];d['full_25record_bars']+=full
   carry=times[full*25:].copy();carry_sid=sid
  prev=(int(ts[-1]),int(price[-1]),int(sess[-1]));n+=len(ts)
 assert n==pin['rows'];ordered=[]
 for sid,d in sorted(days.items()):
  d=dict(d,contract=pin['contract'],session_label=str(pd.Timestamp(sid*DAY).date()));assert sum(d['duration_bins'])==d['full_25record_bars']==d['rows']//25;d['partial_bar_rows']=d['rows']%25;ordered.append(d)
 assert sum(d['rows'] for d in ordered)==n;cnt=np.array([d['rows'] for d in ordered]);dur=np.sum([d['duration_bins'] for d in ordered],axis=0)
 result=dict(contract=pin['contract'],sha256=pin['sha256'],rows=n,observed_sessions=len(ordered),first_session=ordered[0]['session_label'],last_session=ordered[-1]['session_label'],session_rows_quantiles=dict(zip(['min','p10','p50','p90','max'],map(float,np.quantile(cnt,[0,.1,.5,.9,1])))),sessions_lt_2500_rows=int(np.count_nonzero(cnt<2500)),sessions_lt_25000_rows=int(np.count_nonzero(cnt<25000)),spread_tick_histogram=dict(sorted(hist.items())),diagnostic_bar_duration_bins=dur.tolist())
 for k in keys[1:]:result[k]=max(d[k] for d in ordered) if k.startswith('max_') or k=='volume_max' else sum(d[k] for d in ordered)
 (ROOT/'bias-review'/f'{pin["contract"]}-sessions.json').write_text(json.dumps(ordered,indent=2));return result
if __name__=='__main__':
 pins=json.loads((ROOT/'preflight.json').read_text());assert pins['global_all_six_passed']
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:files=list(pool.map(audit,pins['files']))
 dates=defaultdict(list)
 for f in files:
  for d in json.loads((ROOT/'bias-review'/f'{f["contract"]}-sessions.json').read_text()):dates[d['session_label']].append(f['contract'])
 out=dict(scope='SOURCE_RISK_REVIEW_NO_MARKET_HYPOTHESIS_OUTCOMES',source_quality_certified=False,declared_session='IANA Chicago 17h to next17h; not certified exchange calendar',raw_rows_retained=True,pinned_cutoff_utc='2026-09-30T22:00:00Z',files=files,contract_session_count=sum(f['observed_sessions'] for f in files),distinct_observed_session_labels=len(dates),labels_with_multiple_contracts=sum(len(v)>1 for v in dates.values()),max_simultaneous_contracts=max(map(len,dates.values())),diagnostic_bar_duration_labels=['zero','(0,1ms]','(1,10ms]','(10,100ms]','(100ms,1s]','(1s,10s]','(10s,60s]','>60s'],warnings=['overlapping contracts are not independent dates','thin sessions do not prove missing data; no row/day exclusions','gaps conflate inactivity and missing records','25 records not exchange matches, volume or seconds','no footprints or detector replay generated','full-session activity is retrospective: diagnostics only'])
 (ROOT/'bias-review.json').write_text(json.dumps(out,indent=2));print('REVIEW_COMPLETE',out['contract_session_count'],out['distinct_observed_session_labels'],out['labels_with_multiple_contracts'])
 for f in files:print(f['contract'],'thin<2500',f['sessions_lt_2500_rows'],'gaps>60s',f['gaps_gt_60s'],'zero-duration-bars',f['diagnostic_bar_duration_bins'][0])

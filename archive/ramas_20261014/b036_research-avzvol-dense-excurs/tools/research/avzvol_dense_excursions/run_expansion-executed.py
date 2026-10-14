"""Predeclared dense-family excursion expansion. Same pinned10 dates; not holdout.
Market labels computed from ordered ticks; context from closed tick-built bars.
Delayed translated-zone controls remain conditioned on earlier racimo births.
"""
import csv,hashlib,itertools,json,sys,time,types
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np,pandas as pd,pyarrow.parquet as pq
sys.path.insert(0,'/data/analysis/avzvol-pilot')
from adapter import build_bars,fail_closed_events
from fast_racimo import replay
from causal_pivots import CausalPivots
from run_pilot import sid_hour,DAY,CUTOFF,FILE,CONTRACT
from expanded_passage import evaluate,STATUS
P=Path('/data/analysis/avzvol-expansion');OLD=Path('/data/analysis/avzvol-pilot')
FAMILIES=[(80.,5,4,500,30),(80.,5,8,1000,20),(80.,5,18,2000,20),(90.,5,4,500,30),(90.,5,18,2000,20),(80.,10,4,500,30)]
D=[10,20,40,80];Q=[.25,.5,.75];ENDPOINTS=['touch','center','cross'];MODES=['first_departure','first_D_qualifying'];ORIGINS=['real','delayed_translated_250bars']
KEYS=['family','origin','mode','endpoint','D','q']
HEAD=KEYS+['session','anchor_idx','exit_idx','peak_idx','trigger_idx','last_idx','status','side','peak_distance','skipped_small_excursions','target_ticks','opposite_ticks','trigger_ticks','trigger_ns','last_ns','source_trigger_seq','source_last_seq','wait_bars','return_bars','return_seconds','return_bars_per_tick','speed_ratio','return_efficiency','return_imbalance_toward','quote_coverage','confirmed_peaks_return','prior64_toward','prior256_corridor_overlap','prior256_target_visits']
def main():
 t0=time.time();old=json.loads((OLD/'run-manifest.json').read_text());auth=json.loads(Path('/data/raw/avzvol-selected-risk/pr111-authorization.json').read_text());assert auth['gates']['user_exploratory_authorized'] and not auth['holdout_access_authorized']
 sha=hashlib.sha256()
 with FILE.open('rb') as f:
  for block in iter(lambda:f.read(8<<20),b''):sha.update(block)
 assert sha.hexdigest()==old['source']['sha256'];assert FILE.stat().st_size==old['source']['bytes']
 dates=old['event_dates'];allowed_days=np.array([pd.Timestamp(d).value//DAY for d in dates]);a,z=old['read_window_utc_ns'];assert z<=CUTOFF
 pf=pq.ParquetFile(FILE);assert pf.metadata.num_rows==old['source']['rows']
 for i in range(pf.metadata.num_row_groups):
  s=pf.metadata.row_group(i).column(pf.schema_arrow.names.index('ts_utc_ns')).statistics;assert s.max<CUTOFF and s.null_count==0
 manifest=dict(scope='DENSE_FAMILY_EXPANSION_SAME_PILOT_TEN_DATES',source=old['source'],event_dates=dates,event_universe_sha256=old['event_universe_sha256'],read_window_utc_ns=[a,z],footprint=old['footprint'],families=FAMILIES,distances=D,fractions=Q,endpoints=ENDPOINTS,modes=MODES,origins=ORIGINS,total_rule_groups=864,formation_wait_bars=2000,outcome_horizon_bars=2000,gap_seconds=10,mode1='skip only excursions returning inside before reaching D; stop on first D-qualified sortie, even failed trigger',center='floor((birth_low+birth_high)/2)',control='same frozen width and relative anchor position translated at closed bar250 later in same selected session; not unconditional null',chronological_diagnostic_train=dates[:6],chronological_diagnostic_test=dates[6:],diagnostic_test_previously_inspected=True,holdout_opened=False,source_certified=False,pnl_computed=False,code_sha256={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['expanded_passage.py','run_expansion.py','test_expanded.py']})
 (P/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('PLAN_PINNED',864,flush=True)
 t=pq.read_table(FILE,columns=['ts_utc_ns','price_ticks','volume','sequence','bid_ticks','ask_ticks'],filters=[('ts_utc_ns','>=',a),('ts_utc_ns','<',z)],use_threads=False);ts,px,vol,seq,bid,ask=[t.column(n).to_numpy(zero_copy_only=False) for n in t.column_names];del t
 assert np.all(np.diff(seq)>0) and np.all(np.diff(ts)>=0);sid,hour=sid_hour(ts);keep=((sid<min(allowed_days))|np.isin(sid,allowed_days))&(hour!=16)
 flow=np.where(px>=ask,1,np.where(px<=bid,-1,0)).astype(np.int8);del bid,ask,hour
 ts,px,vol,seq,sid,flow=[x[keep] for x in [ts,px,vol,seq,sid,flow]];del keep
 bars,fps,st,en,ss,ee=build_bars(ts,px,vol,sid);bs=sid[st];full=(en-st)==25;bar=bars.tick_bar_idx
 session_start_bar=np.maximum.accumulate(np.where(np.r_[True,bs[1:]!=bs[:-1]],np.arange(len(st)),0));end_for_bar=ee[np.searchsorted(ss,st,side='right')-1]
 # Confirmation counters use availability time, never unconfirmed/final pivots.
 confirmed=np.zeros(len(st),np.int64)
 for aa,zz in zip(np.r_[0,np.flatnonzero(bs[1:]!=bs[:-1])+1],np.r_[np.flatnonzero(bs[1:]!=bs[:-1])+1,len(st)]):
  cp=CausalPivots()
  for b in range(aa,zz):
   if full[b]:confirmed[b]=len(cp.update(int(bars.high_t[b]),int(bars.low_t[b])))
 pc=np.r_[0,np.cumsum(confirmed)];del confirmed
 src=types.ModuleType('legacy');src.__dict__.update(np=np,pd=pd,defaultdict=defaultdict);exec((OLD/'legacy_detector.py').read_text(),src.__dict__)
 statistics={};daily={};formation_counts=[];signal_rows=0;labels_total=0;reference_sample=[]
 f=(P/'signals-private.csv').open('w',newline='');writer=csv.DictWriter(f,fieldnames=HEAD);writer.writeheader()
 def features(ex,pk,tr,side,edge,peak,target):
  back_dist=peak-side*(px[tr]-edge);sec_out=(ts[pk]-ts[ex-1])/1e9;sec_back=(ts[tr]-ts[pk])/1e9
  speed=(back_dist/sec_back)/(peak/sec_out) if sec_out>0 and sec_back>0 else None
  vv=vol[pk+1:tr+1];gg=flow[pk+1:tr+1];total=float(vv.sum());known=float(vv[gg!=0].sum());delta=float(np.dot(vv,gg));path=float(np.abs(np.diff(px[pk:tr+1])).sum())
  b=int(bar[tr]);start=int(session_start_bar[b]);hist=np.arange(max(start,b-256),b);low=min(int(px[tr]),target);high=max(int(px[tr]),target)
  overlap=float(np.mean((bars.high_t[hist]>=low)&(bars.low_t[hist]<=high))) if len(hist) else None
  visits=int(np.count_nonzero((bars.high_t[hist]>=target)&(bars.low_t[hist]<=target)))
  prior=-side*(int(bars.close_t[b-1])-int(bars.close_t[b-65])) if b-start>=65 else None
  return dict(wait_bars=int(bar[tr]-bar[ex-1]),return_bars=int(bar[tr]-bar[pk]+1),return_seconds=float(sec_back),return_bars_per_tick=float((bar[tr]-bar[pk]+1)/back_dist),speed_ratio=float(speed) if speed is not None else None,return_efficiency=float(back_dist/path) if path else None,return_imbalance_toward=-side*delta/total if known and total else None,quote_coverage=known/total if total else None,confirmed_peaks_return=int(pc[b+1]-pc[int(bar[pk])+1]),prior64_toward=prior,prior256_corridor_overlap=overlap,prior256_target_visits=visits)
 for percentile,window in sorted(set((x[0],x[1]) for x in FAMILIES)):
  print('ZONE_TAPE',percentile,window,flush=True);det=src.run(bars,fps,bs,dict(racimo_min=0,ob_bars=0,window_bars=window,detection_percentile=percentile));zones=det['zones'];zb=np.array([r['bar'] for r in zones],np.int64);zl=np.array([r['low_tick'] for r in zones],np.int64);zh=np.array([r['high_tick'] for r in zones],np.int64);del det,zones
  for _,_,m,w,h in [x for x in FAMILIES if x[:2]==(percentile,window)]:
   family=f'P{percentile:g}_W{window}_R{m}_{w}_{h}';birth=replay(zb,zl,zh,m,w,h);birth=birth[np.isin(bs[birth[:,0]],allowed_days)&full[birth[:,0]]];print('FAMILY',family,'BIRTHS',len(birth),flush=True)
   formation_counts.append(dict(family=family,selected_formations=len(birth)));cases=[]
   for b,_,low,high in birth:
    anchor=int(en[b]-1);stop=int(end_for_bar[b]);label=str(pd.Timestamp(int(bs[b])*DAY).date());assert label in dates
    cases.append(('real',int(b),anchor,stop,int(low),int(high),label))
    cb=b+250
    if cb<len(st) and bs[cb]==bs[b] and full[cb]:
     ca=int(en[cb]-1);shift=int(px[ca]-px[anchor]);cases.append(('delayed_translated_250bars',int(cb),ca,stop,int(low)+shift,int(high)+shift,label))
   for origin,b,anchor,stop,low,high,label in cases:
    cache={}
    for mode,endpoint,d,q in itertools.product(range(2),range(3),D,Q):
     key=(family,origin,MODES[mode],ENDPOINTS[endpoint],d,q);counter=statistics.setdefault(key,Counter());day=daily.setdefault((*key,label),Counter());counter['formations']+=1;day['formations']+=1
     result=evaluate(px,ts,bar,anchor,stop,low,high,d,q,endpoint,mode);status,ex,pk,tr,last,side,peak,target,opposite,skips=result;counter[STATUS[status]]+=1;day[STATUS[status]]+=1;labels_total+=1
     if tr<0:continue
     counter['signals']+=1;day['signals']+=1;signal_rows+=1
     ck=(ex,pk,tr,side,peak,target)
     if ck not in cache:cache[ck]=features(ex,pk,tr,side,high if side==1 else low,peak,target)
     row=dict(zip(KEYS,key));row.update(session=label,anchor_idx=anchor,exit_idx=ex,peak_idx=pk,trigger_idx=tr,last_idx=last,status=STATUS[status],side=side,peak_distance=peak,skipped_small_excursions=skips,target_ticks=target,opposite_ticks=opposite,trigger_ticks=int(px[tr]),trigger_ns=int(ts[tr]),last_ns=int(ts[last]),source_trigger_seq=int(seq[tr]),source_last_seq=int(seq[last]),**cache[ck]);writer.writerow(row)
     assert abs(px[tr]-target)==abs(px[tr]-opposite) and tr>anchor and last>=tr
     # Small software-validation sample, prices stay private and unpublished.
     if len(reference_sample)<72 and last-anchor<10000 and (mode,endpoint,d,q) not in [tuple(r['stratum']) for r in reference_sample]:
      reference_sample.append(dict(stratum=[mode,endpoint,d,q],low=low,high=high,anchor=anchor,end=min(stop,last+2),result=list(result)))
   f.flush()
 f.close();del fps
 def summary(key,c):
  return {**dict(zip(KEYS,key)),**c}
 pd.DataFrame([summary(k,c) for k,c in statistics.items()]).fillna(0).to_csv(P/'rule-counts.csv',index=False)
 pd.DataFrame([{**summary(k[:-1],c),'session':k[-1]} for k,c in daily.items()]).fillna(0).to_csv(P/'daily-rule-counts.csv',index=False)
 (P/'reference-sample-private.json').write_text(json.dumps(reference_sample))
 evidence=dict(status='EXPANSION_COMPLETED',families=formation_counts,rule_groups=len(statistics),expected_groups=864,label_evaluations_not_independent=labels_total,signal_rows_not_independent=signal_rows,selected_sessions=len(dates),contracts=[CONTRACT],holdout_opened=False,pnl_computed=False,events_outside_selected_universe=0,wall_seconds=time.time()-t0,all_contracts_complete=False,controls_unconditional=False,primary_gap_seconds=10,software_reference_strata_saved=len(reference_sample))
 (P/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print('COMPLETE',json.dumps(evidence),flush=True)
if __name__=='__main__':main()

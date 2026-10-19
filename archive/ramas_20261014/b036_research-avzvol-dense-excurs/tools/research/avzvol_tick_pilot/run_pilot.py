"""Authorized exploratory pilot. All gates verified before market hypotheses.
Read only fixed preholdout source MNQ12-26; event dates explicitly catalog15.
Warmup all observed pre-first-selected dates inside historical45day UTC window;
afterward only selected dates enter calibration. Sequence-causal footprint is
NEW DEVELOPMENT SEMANTICS, not a silent reproduction of historical NT8 subseries.
"""
import csv,hashlib,json,time,types
from collections import defaultdict
from pathlib import Path
import numpy as np,pandas as pd,pyarrow.parquet as pq
from adapter import build_bars,passage,STATUS,fail_closed_events
from causal_pivots import CausalPivots
P=Path('/data/analysis/avzvol-pilot');R=Path('/data/raw/avzvol-ticks');CONTRACT='MNQ_12-26';FILE=R/(CONTRACT+'_ticks_ext.parquet')
CONFIGS=[(4,1000,20),(4,1000,30),(4,1000,45),(4,500,45),(5,1000,45)]
DISTANCES=[10,20,40];FRACTIONS=[.25,.5,.75];GAPS=[10,1,60,None]
CUTOFF=pd.Timestamp('2026-09-30T22:00:00Z').value;DAY=86400000000000;HOUR=3600000000000

def sid_hour(ts):
 h,inv=np.unique(ts//HOUR,return_inverse=True);loc=pd.to_datetime(h*HOUR,utc=True).tz_convert('America/Chicago');labels=((loc.tz_localize(None)-pd.Timedelta(hours=17)).normalize().asi8//DAY)+1
 return labels[inv],np.asarray(loc.hour)[inv]

def stage(name):print(name,flush=True)

def main():
 started=time.time();stage('PREFLIGHT')
 auth=json.loads(Path('/data/raw/avzvol-selected-risk/pr111-authorization.json').read_text());assert auth['gates']['user_exploratory_authorized'];assert not auth['holdout_access_authorized'] and not auth['pnl_or_promotion_authorized']
 pin=next(x for x in auth['files'] if x['contract']==CONTRACT);assert pin['version']==2 and pin['file']==FILE.name
 h=hashlib.sha256()
 with FILE.open('rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 assert h.hexdigest()==pin['sha256'] and FILE.stat().st_size==pin['bytes']
 pf=pq.ParquetFile(FILE);assert pf.metadata.num_rows==pin['rows']
 for i in range(pf.metadata.num_row_groups):
  rg=pf.metadata.row_group(i);stat=rg.column(pf.schema_arrow.names.index('ts_utc_ns')).statistics;assert stat is not None and stat.null_count==0 and stat.max<CUTOFF
  for k,v in [('instrument','MNQ'),('contract','MNQ 12-26')]:
   st=rg.column(pf.schema_arrow.names.index(k)).statistics;assert st.min==st.max==v and st.null_count==0
 selected=list(csv.DictReader(open('/data/analysis/avzvol-selected-risk/selected-event-sessions.csv')));sel=[x for x in selected if x['contract']==CONTRACT];assert len(sel)==10
 allowed={(x['contract'],x['session_label']) for x in selected};dates=[x['session_label'] for x in sel];approved_days=np.array([pd.Timestamp(x).value//DAY for x in dates]);meta=json.loads(Path('/data/raw/avzvol-selected-risk/metadata-review.json').read_text());window=next(x for x in meta['contracts'] if x['contract']==CONTRACT);a=window['legacy_read_window_start_utc_ns'];z=min(window['legacy_read_window_end_utc_ns_exclusive'],CUTOFF)
 manifest=dict(scope='AUTHORIZED_EXPLORATORY_PILOT_NOT_ALL_COMBINATIONS',source=pin,source_certified=False,raw_qa_reconciliation_refs=['PR110','PR111 corrected b047753b'],event_dates=dates,event_universe_sha256=hashlib.sha256(Path('/data/analysis/avzvol-selected-risk/selected-event-sessions.csv').read_bytes()).hexdigest(),read_window_utc_ns=[a,z],detector_percentile=95,detector_window_bars=10,bar_records=25,footprint='SEQUENCE_CAUSAL_TOTAL_MEMBERSHIP_NEW_DEVELOPMENT_VARIANT',calibration_policy='observed warmup dates before first selected label inside45day window; selected dates only thereafter',partial_bar_policy='retained calibration after declared session boundary; not event origin',formation_bounds='birth low0/high0, no final geometry',primary_gap_seconds=10,gap_sensitivities=[1,60,None],endpoints=['touch'],horizon_bars=2000,configs=CONFIGS,distances=DISTANCES,retracement_fractions=FRACTIONS,primary_config_rule_pairs=45,with_gap_sensitivity_pairs=180,control_baseline='not evaluated; no claim versus chance or price/context rival',old_certificates_modified=False,holdout_opened=False,pnl_computed=False)
 manifest['code_sha256']={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['adapter.py','run_pilot.py','legacy_detector.py','causal_pivots.py','reference_partial_return.py']}
 (P/'run-manifest.json').write_text(json.dumps(manifest,indent=2));stage('SOURCE_PAYLOAD')
 table=pq.read_table(FILE,columns=['ts_utc_ns','price_ticks','volume','sequence','bid_ticks','ask_ticks'],filters=[('ts_utc_ns','>=',a),('ts_utc_ns','<',z)],use_threads=False)
 ts,px,v,seq,bid,ask=[table.column(n).to_numpy(zero_copy_only=False) for n in table.column_names];del table
 assert np.all(np.diff(ts)>=0) and np.all(np.diff(seq)>0) and np.all(v>0);sid,clock=sid_hour(ts)
 raw_counts={str(pd.Timestamp(int(d)*DAY).date()):int(n) for d,n in zip(*np.unique(sid,return_counts=True))}
 for r in sel:assert raw_counts.get(r['session_label'])==int(float(r['trades']))
 first=min(approved_days);mask_dates=(sid<first)|np.isin(sid,approved_days);maintenance=(clock==16);mask=mask_dates&~maintenance
 removed_nonselected=int(np.count_nonzero(~mask_dates));removed_maintenance=int(np.count_nonzero(mask_dates&maintenance));nwindow=len(ts)
 agg=np.where(px>=ask,1,np.where(px<=bid,-1,0)).astype(np.int8);del bid,ask,clock
 ts,px,v,seq,sid,agg=[x[mask] for x in [ts,px,v,seq,sid,agg]];del mask,mask_dates,maintenance
 stage('BARS_AND_CAUSAL_FOOTPRINT')
 bars,fps,starts,ends,ss,ee=build_bars(ts,px,v,sid);bar=bars.tick_bar_idx;bar_sid=sid[starts];n=len(px)
 # Mark partial closes at session boundary, not prematurely at their last tick.
 full=(ends-starts)==25;available=np.where(full,ends-1,-1)
 # Detector untouched pure reference algorithm, fed explicitly NEW causal footprints.
 src=types.ModuleType('detector');src.__dict__.update(np=np,pd=pd,defaultdict=defaultdict);exec((P/'legacy_detector.py').read_text(),src.__dict__)
 detparams=dict(racimo_min=0,ob_bars=0,window_bars=10,detection_percentile=95.0)
 stage('DETECTOR_ZONES');det=src.run(bars,fps,bar_sid,detparams);zones=det['zones'];formations=[];census=[]
 for m,w,hgt in CONFIGS:
  zs=[];clusters=[];params=dict(racimo_min=m,racimo_bars=w,racimo_altura_ticks=hgt)
  for zz in zones:
   zz=dict(bar=zz['bar'],low_tick=zz['low_tick'],high_tick=zz['high_tick'],racimo_bar=-1,rac=None);src._racimo(zz,zs,clusters,zz['bar'],params);zs.append(zz)
  selected_births=0;partial_births=0
  for k,c in enumerate(clusters):
   b=int(c['bar']);d=int(bar_sid[b])
   if d not in approved_days:continue
   if not full[b]:partial_births+=1;continue
   selected_births+=1;label=str(pd.Timestamp(d*DAY).date());anchor=int(ends[b]-1);stop=int(ee[np.searchsorted(ss,anchor,side='right')-1]);assert stop>anchor
   formations.append(dict(contract=CONTRACT,session=label,cell=f'{m}_{w}_{hgt}',zone=f'{m}_{w}_{hgt}:{k}',bar=b,anchor=anchor,anchor_source_sequence=int(seq[anchor]),anchor_ns=int(ts[anchor]),session_last_source_sequence=int(seq[stop-1]),end=stop,low=int(c['low0']),high=int(c['high0'])))
  census.append(dict(cell=f'{m}_{w}_{hgt}',all_warmup_and_selected_formations=len(clusters),selected_full_bar_formations=selected_births,selected_partial_bar_formations_not_eligible=partial_births))
 fail_closed_events(formations,allowed);detected_zone_count=len(zones);del fps,det,zones;stage('PIVOTS_AND_LOCAL_FLOW')
 peak_events=[]
 for aa,zz in zip(np.r_[0,np.flatnonzero(bar_sid[1:]!=bar_sid[:-1])+1],np.r_[np.flatnonzero(bar_sid[1:]!=bar_sid[:-1])+1,len(starts)]):
  cp=CausalPivots()
  for b in range(aa,zz):
   if not full[b]:continue
   for ev in cp.update(int(bars.high_t[b]),int(bars.low_t[b])):peak_events.append(dict(side=ev['side'],pivot_bar=aa+ev['pivot_bar'],available_bar=aa+ev['available_bar'],available_idx=int(ends[b]-1)))
 # Disjoint flow legs (last_inside,peak] and (peak,trigger]. No unknown->neutral imputation.
 # Local leg sums avoid three global prefix buffers; lower bounded memory.
 pi=np.array([r['pivot_bar'] for r in peak_events]);av=np.array([r['available_idx'] for r in peak_events]);ph=np.array([r['side']=='H' for r in peak_events]);rows=[];stage('PRIMARY45_AND_GAP_SENSITIVITIES')
 def leg(a,b,side,distance):
  vv=v[a+1:b+1];gg=agg[a+1:b+1];total=float(vv.sum());known=float(vv[gg!=0].sum());delta=float(np.dot(vv,gg));seconds=float((ts[b]-ts[a])/1e9)
  return dict(seconds=seconds,inclusive_bars=int(bar[b]-bar[a]+1),bars_per_tick=float((bar[b]-bar[a]+1)/distance) if distance else None,ticks_per_second=float(distance/seconds) if seconds>0 else None,volume=total,classified_volume_fraction=known/total if total else None,delta_over_total_away=side*delta/total if total and known else None)
 for f in formations:
  for distance in DISTANCES:
   for fraction in FRACTIONS:
    for gap in GAPS:
     status,ex,pk,tr,out,side,R0,target,opposite=passage(px,ts,bar,f['anchor'],f['end'],f['low'],f['high'],distance,fraction,0,2000,-1 if gap is None else gap*1000000000)
     r={**f,'min_distance_ticks':distance,'retracement_fraction':fraction,'gap_policy':'no_gap_censor' if gap is None else f'{gap}s','status':STATUS[status],'signal':tr>=0}
     if tr>=0:
      edge=f['high'] if side==1 else f['low'];retrace=R0-side*(px[tr]-edge);away=leg(ex-1,pk,side,R0);back=leg(pk,tr,side,retrace);piv=(pi>bar[pk])&(av<=tr)&(pi>=f['bar']);r.update(trigger_idx=int(tr),trigger_source_sequence=int(seq[tr]),trigger_ns=int(ts[tr]),trigger_price_ticks=int(px[tr]),side=int(side),peak_distance_ticks=int(R0),actual_retraced_fraction=float(retrace/R0),target_ticks=int(target),opposite_ticks=int(opposite),symmetric_distance_ticks=int(abs(px[tr]-target)),outcome_source_sequence=int(seq[out]) if out>=0 else None,outcome_ns=int(ts[out]) if out>=0 else None,trigger_equal_timestamp_to_previous=bool(ts[tr]==ts[tr-1]),outcome_same_timestamp_as_trigger=bool(out>=0 and ts[out]==ts[tr]),return_confirmed_high_peaks=int(np.count_nonzero(piv&ph)),return_confirmed_low_peaks=int(np.count_nonzero(piv&~ph)),return_to_outgoing_speed_ratio=(back['ticks_per_second']/away['ticks_per_second'] if away['ticks_per_second'] and back['ticks_per_second'] is not None else None))
      for label,obj in [('outgoing',away),('returning',back)]:
       for k,value in obj.items():r[label+'_'+k]=value
      assert abs(r['trigger_price_ticks']-r['target_ticks'])==abs(r['opposite_ticks']-r['trigger_price_ticks'])
      assert r['trigger_idx']>f['anchor'] and (out<0 or out>tr)
     rows.append(r)
 fail_closed_events(rows,allowed);t=pd.DataFrame(rows)
 for name in ['trigger_idx','trigger_source_sequence','trigger_ns','outcome_source_sequence','outcome_ns','trigger_price_ticks','target_ticks','opposite_ticks','side','symmetric_distance_ticks','peak_distance_ticks']:
  t[name]=pd.array([r.get(name,pd.NA) for r in rows],dtype='Int64')
 t.to_csv(P/'episode-results.csv',index=False);pd.DataFrame(formations).to_csv(P/'formations.csv',index=False);pd.DataFrame(census).to_csv(P/'frequency-census.csv',index=False)
 summary=[]
 for key,g in t.groupby(['cell','min_distance_ticks','retracement_fraction','gap_policy'],sort=False):
  target=int(g.status.eq('TARGET_FIRST').sum());opposite=int(g.status.eq('OPPOSITE_FIRST').sum());signals=int(g.signal.sum());unknown=signals-target-opposite
  summary.append(dict(cell=key[0],min_distance_ticks=int(key[1]),retracement_fraction=float(key[2]),gap_policy=key[3],formations=len(g),signals=signals,target_first=target,opposite_first=opposite,unresolved=unknown,signal_sessions=int(g.loc[g.signal,'session'].nunique()),resolved_target_fraction=target/(target+opposite) if target+opposite else None,target_lower_bound=target/signals if signals else None,target_upper_bound=(target+unknown)/signals if signals else None))
 pd.DataFrame(summary).to_csv(P/'rule-summary.csv',index=False)
 evidence=dict(status='PILOT_COMPLETED',new_market_outcome_trials_executed=len(summary),primary_config_rule_pairs_executed=45,gap_sensitivity_config_rule_pairs_executed=135,contracts_executed=[CONTRACT],selected_sessions_executed=10,raw_file_rows=pf.metadata.num_rows,read_window_rows=nwindow,removed_nonselected_after_first_selected=removed_nonselected,removed_maintenance_derived_only=removed_maintenance,detector_input_rows=n,detector_bars=len(starts),detected_zones=detected_zone_count,formations_by_cell=census,selected_formations=len(formations),episode_rule_evaluations=len(t),events_outside_selected_universe=0,primary_status_counts=t[t.gap_policy.eq('10s')].status.value_counts().to_dict(),signal_total_is_not_independent_events=True,global_selected_event_dates=261,fully_executed_parameter_campaign=False,source_quality_certified=False,holdout_opened=False,pnl_computed=False,wall_seconds=time.time()-started,notes=['New sequence-causal footprint variant; not replica of legacy NT8subseries stats','Gap censoring is an uncertainty sensitivity, not proof of damaged source','No context-only/zone-free comparison or multiplicity-adjusted effect inference yet','Ten dates and one contract cannot establish robust strategy','Rawsource unchanged; no recut or dataset upload performed'])
 (P/'evidence.json').write_text(json.dumps(evidence,indent=2));stage('PILOT_COMPLETE '+json.dumps(evidence))
if __name__=='__main__':main()

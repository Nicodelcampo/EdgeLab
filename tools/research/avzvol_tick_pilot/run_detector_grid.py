"""Frequency-only full1536 detector grid on SAME pilot contract10 selected dates.
No optimization by outcomes, no new source/certificates/holdout. All16 percentile/
window zone tapes recomputed with causal volume footprints and past calibration.
Each tape shared among96 triples. Fast racimo exact parity verified first.
"""
import hashlib,itertools,json,time,types
from collections import defaultdict
from pathlib import Path
import numpy as np,pandas as pd,pyarrow.parquet as pq
from adapter import build_bars,fail_closed_events
from fast_racimo import replay
from run_pilot import sid_hour,DAY,HOUR,CUTOFF,CONTRACT,FILE,P

def main():
 started=time.time();manifest=json.loads((P/'run-manifest.json').read_text());assert manifest['source']['version']==2
 assert hashlib.sha256(FILE.read_bytes()).hexdigest()==manifest['source']['sha256']
 dates=manifest['event_dates'];approved=np.array([pd.Timestamp(d).value//DAY for d in dates]);a,z=manifest['read_window_utc_ns'];assert z<=CUTOFF
 pf=pq.ParquetFile(FILE)
 for i in range(pf.metadata.num_row_groups):assert pf.metadata.row_group(i).column(0).statistics.max<CUTOFF
 t=pq.read_table(FILE,columns=['ts_utc_ns','price_ticks','volume'],filters=[('ts_utc_ns','>=',a),('ts_utc_ns','<',z)],use_threads=False);ts,px,v=[t.column(n).to_numpy(zero_copy_only=False) for n in t.column_names];del t;sid,hour=sid_hour(ts);keep=((sid<min(approved))|np.isin(sid,approved))&(hour!=16);ts,px,v,sid=[x[keep] for x in [ts,px,v,sid]];del hour,keep
 bars,fps,st,en,ss,ee=build_bars(ts,px,v,sid);bs=sid[st];full=(en-st)==25;bars.tick_bar_idx=np.array([],np.int64);del ts,px,v,sid,ss,ee
 src=types.ModuleType('legacy');src.__dict__.update(np=np,pd=pd,defaultdict=defaultdict);exec((P/'legacy_detector.py').read_text(),src.__dict__)
 triples=list(itertools.product([4,5,6,8,12,18],[250,500,1000,2000],[10,20,30,45]));parameters=list(itertools.product([80.0,90.0,95.0,97.5],[5,10,20,40]));assert len(triples)*len(parameters)==1536
 plan=dict(scope='FREQUENCY_ONLY_ALL1536_CONFIGS_PILOT_CONTRACT',source=manifest['source'],event_dates=dates,bar_footprint=manifest['footprint'],triples=triples,percentiles=[80,90,95,97.5],windows=[5,10,20,40],all_six_contracts_executed=False,market_outcomes_used_for_ranking=False,full_matrix_outcomes_executed=False,source_certified=False,holdout_opened=False,code_sha256={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['run_detector_grid.py','fast_racimo.py','adapter.py','legacy_detector.py']});(P/'detector-grid-manifest.json').write_text(json.dumps(plan,indent=2))
 pilot_f=pd.read_csv(P/'formations.csv');records=[];zones_counts=[];reference_checks=0
 for percentile,window in parameters:
  print('ZONES',percentile,window,flush=True);det=src.run(bars,fps,bs,dict(racimo_min=0,ob_bars=0,window_bars=window,detection_percentile=percentile));zz=det['zones'];zb=np.array([r['bar'] for r in zz],np.int64);zl=np.array([r['low_tick'] for r in zz],np.int64);zh=np.array([r['high_tick'] for r in zz],np.int64);zones_counts.append(dict(percentile=percentile,window_bars=window,zones=len(zz)));del det,zz
  for m,w,h in triples:
   birth=replay(zb,zl,zh,m,w,h);good=np.isin(bs[birth[:,0]],approved)&full[birth[:,0]] if len(birth) else np.zeros(0,bool);selected=birth[good];cell=f'{m}_{w}_{h}'
   if percentile==95 and window==10 and cell in pilot_f.cell.unique():
    ref=pilot_f[pilot_f.cell.eq(cell)];assert np.array_equal(selected[:,[0,2,3]],ref[['bar','low','high']].to_numpy());reference_checks+=1
   sessions_with_events=int(len(np.unique(bs[selected[:,0]]))) if len(selected) else 0
   records.append(dict(contract=CONTRACT,min_zones=m,racimo_lookback_bars=w,max_height_ticks=h,percentile=percentile,window_bars=window,selected_full_bar_formations=len(selected),observed_selected_sessions=len(dates),sessions_with_formations=sessions_with_events,formations_per_selected_session=len(selected)/len(dates),selected_partial_bar_births=int(np.count_nonzero(np.isin(bs[birth[:,0]],approved)&~full[birth[:,0]])) if len(birth) else 0,all_input_births=len(birth)))
  pd.DataFrame(records).to_csv(P/'detector-grid-frequency.csv',index=False)
 assert len(records)==1536 and reference_checks==5
 result=dict(status='FREQUENCY_GRID_COMPLETE',configs_executed=len(records),percentile_window_tapes_recomputed=16,pilot_contract=CONTRACT,selected_sessions=len(dates),independent_legacy_reference_market_birth_checks=reference_checks,synthetic_prefix_parity_cases=360,wall_seconds=time.time()-started,total_formations_across_configs_not_independent=sum(r['selected_full_bar_formations'] for r in records),zero_formation_configs=sum(r['selected_full_bar_formations']==0 for r in records),top_by_frequency=sorted(records,key=lambda r:r['selected_full_bar_formations'],reverse=True)[:8],requested_18_2000_20=[r for r in records if r['min_zones']==18 and r['racimo_lookback_bars']==2000 and r['max_height_ticks']==20],zone_census=zones_counts,all_six_contracts_executed=False,full_matrix_outcomes_executed=False,profitability_inferred=False,holdout_opened=False)
 (P/'detector-grid-evidence.json').write_text(json.dumps(result,indent=2));print('GRID_COMPLETE',len(records),'configs in',result['wall_seconds'],'seconds',flush=True)
if __name__=='__main__':main()

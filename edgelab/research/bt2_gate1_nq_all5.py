"""Checkpointed, memory-bounded five-contract Gate 1 replication — NQ instrument fork.

Forked from edgelab/research/bt2_gate1_all5.py (GC, proven design). Same MFE-MAE
estimand, same checkpoint/finalize machinery, same K_BT2 comparator (module
DEFAULTS, no external sweep dependency). Differs only in: instrument='NQ', NQ
spec/registry paths, K_ABS params bound to the informal early-stop config
bt2a_nq_7e84981882b0b380 instead of the module DEFAULTS, and a dynamically
computed PREEXISTING_OUTCOME_EXPOSURE (NQ's own audit history, not GC's).
"""
from __future__ import annotations
import argparse, hashlib, json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
import numpy as np
from edgelab.research.bt2_gate1_outcomes import (_event_session_estimates,attach_fills,build_path_cache,nrand_replicates,shuffle_replicates,wild_cluster_ci)

INSTRUMENT = 'NQ'

# specs/bt2a_nq_selected_configuration_2026-08-29.json, config_id
# bt2a_nq_7e84981882b0b380 (informal 2-contract early-stop evidence, NOT
# SELECTED_STABLE_NQ_CONFIGURATION). Kept fully explicit rather than reading
# bigtrap2absorption.DEFAULTS + override, so this file has no hidden
# dependency on the module's GC-anchored DEFAULTS staying in this shape.
# Only MinStackedRows differs from DEFAULTS (1 vs 2); every other field is
# identical to DEFAULTS.
K_ABS_PARAMS_NQ = {
    "TapeWindowTicks": 25,
    "ScoreMode": "AbsMagnitude",
    "AbsorptionPct": 90.0,
    "AbsorptionLookback": 500,
    "MinHistoryBuckets": 200,
    "RequireFlowSideMatch": True,
    "ImbalanceMode": "Diagonal",
    "TrapVolumeSource": "AggressiveSide",
    "TicksPerRow": 1,
    "ImbalanceRatio": 3.0,
    "MinStackedRows": 1,
    "MinTrapFrac": 0.2,
    "MinDeltaFilter": 0.0,
    "MinTrapVolume": 0.0,
    "UseWickFilter": True,
    "WickZonePct": 30.0,
    "MinExportVolume": 1.0,
    "InvalidationMode": "CloseThrough",
    "MaxAgeBars": 2000,
    "MaxTouches": 0,
    "DrawZoneBand": True,
}

def _load(p:Path)->dict[str,Any]:return json.loads(p.read_text(encoding='utf-8'))
def _start(s:str)->int:
 z=ZoneInfo('America/Chicago');d=datetime(int(s[:4]),int(s[4:6]),int(s[6:]),17,tzinfo=z)-timedelta(days=1);return int(d.timestamp()*1_000_000_000)
def _end(s:str)->int:
 z=ZoneInfo('America/Chicago');d=datetime(int(s[:4]),int(s[4:6]),int(s[6:]),17,tzinfo=z);return int(d.timestamp()*1_000_000_000)
def _labels(ts):
 import pandas as pd
 idx=pd.to_datetime(np.asarray(ts,dtype='int64'),unit='ns',utc=True).tz_convert('America/Chicago');days=np.asarray(idx.normalize().tz_localize(None),dtype='datetime64[D]')+(np.asarray(idx.hour)>=17).astype('timedelta64[D]');return np.char.replace(np.datetime_as_string(days,unit='D'),'-','').astype('U8')
def _raw_abs_events(ticks, sessions, allowed):
 from edgelab.research.all5_runtime.bigtrap2absorption import run
 result=run(ticks,params=K_ABS_PARAMS_NQ);out=[]
 for z in result.get("zones",[]):
  idx=int(z["sig_idx"]);session=str(sessions[idx])
  if session not in allowed:continue
  direction=1 if z["dir"]=="long" else -1;key=f"K_ABS|{ticks.contract}|{session}|{int(z['sig_ts'])}|{int(ticks.sequence[idx])}|{direction}"
  out.append({"key":key,"arm":"K_ABS","contract":ticks.contract,"direction":direction,"signal_idx":idx,"signal_ts_ns":int(z["sig_ts"]),"signal_source_row":int(ticks.sequence[idx])})
 return out
def _raw_bt2_events(ticks, sessions, allowed):
 from edgelab.research.all5_runtime.bars import build_footprints,build_tick_bars
 from edgelab.research.all5_runtime.bigtrap2 import DEFAULTS,run
 bars=build_tick_bars(ticks,25,reiniciar_por_sesion=True);footprints=build_footprints(ticks,bars);result=run(ticks,bars,footprints,params=DEFAULTS);changes=np.flatnonzero(np.diff(bars.tick_bar_idx))+1;stops=np.concatenate((changes,[len(ticks)]));out=[]
 for z in result.get("zones",[]):
  bar=int(z["created_bar"]);idx=int(stops[bar]-1);session=str(sessions[idx])
  if session not in allowed:continue
  direction=1 if z["kind"]=="trapped_sellers" else -1;key=f"K_BT2|{ticks.contract}|{session}|{int(ticks.ts_ns[idx])}|{int(ticks.sequence[idx])}|{direction}"
  out.append({"key":key,"arm":"K_BT2","contract":ticks.contract,"direction":direction,"signal_idx":idx,"signal_ts_ns":int(ticks.ts_ns[idx]),"signal_source_row":int(ticks.sequence[idx])})
 return out
_RUNTIME_FILES=('edgelab/research/bt2_gate1_outcomes.py','edgelab/research/all5_runtime/ticks.py','edgelab/research/all5_runtime/bars.py','edgelab/research/all5_runtime/bigtrap2.py','edgelab/research/all5_runtime/bigtrap2absorption.py')
def _runtime_sha(root:Path)->str:
 h=hashlib.sha256()
 for rel in _RUNTIME_FILES:h.update(rel.encode());h.update((root/rel).read_bytes())
 return h.hexdigest()
def _expand_registry(sr):
 if 'sessions' in sr:return sr
 rows=[]
 for contract in sr['selection']['contracts']:
  w=sr['selection']['contract_windows'][contract];d=date(int(w['start'][:4]),int(w['start'][4:6]),int(w['start'][6:]));end=date(int(w['end'][:4]),int(w['end'][4:6]),int(w['end'][6:]));excluded=set(sr['closed_weekday_exclusions'][contract]);prior=sr['initial_warmup_session'][contract]
  while d<=end:
   sid=d.strftime('%Y%m%d')
   if d.weekday()<5 and sid not in excluded:rows.append({'cme_session_id':sid,'contract':contract,'warmup_cme_session_id':prior});prior=sid
   d+=timedelta(days=1)
 rows.sort(key=lambda r:r['cme_session_id']);assert len(rows)==sr['selection']['n_sessions'];assert {c:sum(r['contract']==c for r in rows) for c in sr['selection']['contracts']}==sr['contract_session_counts'];sr=dict(sr);sr['sessions']=rows;return sr
def _context(root:Path):
 sr=_expand_registry(_load(root/'specs/bt2a_gate1_nq_all5_sessions_2026-08-27.json'));ir=_load(root/'specs/bt2a_gate1_nq_all5_input_registry_2026-08-27.json');sp=_load(root/'specs/bt2a_gate1_nq_all5_post_outcome_replication_v1.json');return sr,ir,sp
def _checkpoint_name(i:int,row:dict[str,Any])->str:return f"{i:03d}_{row['contract'].replace(' ','_')}_{row['cme_session_id']}.json"
def compute_session(*,repo_root:Path,data_dir:Path,index:int)->dict[str,Any]:
 from edgelab.research.all5_runtime.ticks import load_canonical_parquet
 sr,ir,sp=_context(repo_root);rows=sr['sessions']
 if index<0 or index>=len(rows):raise IndexError(index)
 row=rows[index];contract=row['contract'];session=str(row['cme_session_id']);warmup=str(row['warmup_cme_session_id']);contracts=sr['selection']['contracts'];by=defaultdict(list)
 for r in rows:by[r['contract']].append(r)
 sindex={(c,r['cme_session_id']):i for c in contracts for i,r in enumerate(sorted(by[c],key=lambda x:x['cme_session_id']))};cindex={c:i for i,c in enumerate(contracts)};seed=int(sp['randomization']['seed']);reps=int(sp['randomization']['replications']);ticks=load_canonical_parquet(data_dir/ir['contracts'][contract]['parquet_file'],contract=contract,start_utc_ns=_start(warmup),end_utc_ns=_end(session),instrument=INSTRUMENT);labels=_labels(ticks.ts_ns);cache=build_path_cache(ticks.ts_ns,ticks.price_ticks,labels,tick_cap=int(sp['horizon']['tick_cap']),clock_cap_seconds=int(sp['horizon']['clock_cap_seconds']));rawa=_raw_abs_events(ticks,labels,{session});rawb=_raw_bt2_events(ticks,labels,{session});ae,exa=attach_fills(rawa,ts_ns=ticks.ts_ns,source_row=ticks.sequence,session_ids=labels);be,exb=attach_fills(rawb,ts_ns=ticks.ts_ns,source_row=ticks.sequence,session_ids=labels);ae=[e for e in ae if cache.eligible[e.fill_idx]];be=[e for e in be if cache.eligible[e.fill_idx]];aes=_event_session_estimates(ae,ticks.price_ticks,cache);bes=_event_session_estimates(be,ticks.price_ticks,cache)
 if session not in aes or session not in bes:raise ValueError(f'arm coverage failed {contract} {session}: K_ABS={session in aes} K_BT2={session in bes}')
 child=seed+cindex[contract]*1_000_003+sindex[(contract,session)]*10_007;rand=nrand_replicates(events=ae,ts_ns=ticks.ts_ns,price_ticks=ticks.price_ticks,session_ids=labels,cache=cache,replications=reps,seed=child);shuf=shuffle_replicates(events=ae,price_ticks=ticks.price_ticks,cache=cache,replications=reps,seed=child)
 return {'schema':'bt2a_gate1_nq_all5_session_checkpoint_v1','index':index,'sample_registry_sha256':sr['registry_payload_sha256'],'input_registry_sha256':ir['registry_payload_sha256'],'runtime_sha256':_runtime_sha(repo_root),'row':{'session':session,'contract':contract,'warmup_session':warmup,'K_ABS':aes[session],'K_BT2':bes[session],'N_RAND_median':float(np.median(rand)),'K_ABS_SHUFFLE_median':float(np.median(shuf)),'K_ABS_events':len(ae),'K_BT2_events':len(be)},'excluded_events':exa+exb}
def write_checkpoint(*,repo_root:Path,data_dir:Path,checkpoint_dir:Path,index:int)->Path:
 sr,ir,_=_context(repo_root);row=sr['sessions'][index];checkpoint_dir.mkdir(parents=True,exist_ok=True);out=checkpoint_dir/_checkpoint_name(index,row)
 if out.exists():
  old=_load(out)
  if old.get('sample_registry_sha256')==sr['registry_payload_sha256'] and old.get('input_registry_sha256')==ir['registry_payload_sha256'] and old.get('runtime_sha256')==_runtime_sha(repo_root):print(f"SKIP [{index+1}/{len(sr['sessions'])}] {row['contract']} {row['cme_session_id']}",flush=True);return out
 cp=compute_session(repo_root=repo_root,data_dir=data_dir,index=index);tmp=out.with_suffix('.json.tmp');tmp.write_text(json.dumps(cp,indent=2,ensure_ascii=False)+'\n');tmp.replace(out);r=cp['row'];print(f"DONE [{index+1}/{len(sr['sessions'])}] {r['contract']} {r['session']} abs={r['K_ABS_events']} bt2={r['K_BT2_events']}",flush=True);return out
def _preexisting_outcome_exposure(repo_root:Path)->dict[str,Any]:
 """Derive NQ's outcome-exposure disclosure from on-record exposure events
 instead of hardcoding GC's literal (GC's history and NQ's differ).

 NQ's one known prior exposure event is the BigTrap2 comparator sweep that
 touched the holdout; that sweep's own firewall record shows it never
 accessed MFE/MAE or PnL -- the estimand this Gate 1 measures. If that
 firewall record ever stops matching this exact known shape, fail closed to
 UNKNOWN rather than silently mislabeling."""
 path=repo_root/'docs/research/bigtrap2_nq_tickframes_sweep_result_classification.json'
 classification=_load(path);fw=classification['firewalls']
 if fw.get('holdout_touched') is True and fw.get('mfe_mae_accessed') is False and fw.get('pnl_accessed') is False:
  label='YES_HOLDOUT_TOUCHED_BY_UNRELATED_BT2_SWEEP_MFE_MAE_NEVER_COMPUTED_FOR_NQ'
 else:
  label='UNKNOWN_REQUIRES_MANUAL_AUDIT_FIREWALL_SHAPE_CHANGED'
 return {'label':label,'source_file':'docs/research/bigtrap2_nq_tickframes_sweep_result_classification.json','source_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'known_prior_exposure_events':[{'event':'bigtrap2_nq_tickframes_sweep_v2','classification':classification['classification'],'firewalls':fw}],'mfe_mae_ever_accessed_for_nq_before_this_run':fw.get('mfe_mae_accessed')}
def _build_result(*,rows,counts,exclusions,sr,sp,provenance,repo_root:Path):
 seed=int(sp['randomization']['seed']);boot=int(sp['inference']['bootstrap_replications']);pr=wild_cluster_ci([r['K_ABS']-r['N_RAND_median'] for r in rows],replications=boot,seed=seed);bt=wild_cluster_ci([r['K_ABS']-r['K_BT2'] for r in rows],replications=boot,seed=seed+1);sh=wild_cluster_ci([r['K_ABS']-r['K_ABS_SHUFFLE_median'] for r in rows],replications=boot,seed=seed+2)
 if pr['point']>=2.5 and pr['lower']>0 and bt['lower']>=0:decision='EXPANDED_PRIMARY_POSITIVE_AND_NONINFERIOR_TO_BT2'
 elif pr['lower']>0:decision='EXPANDED_PRIMARY_POSITIVE_NOT_NONINFERIOR_TO_BT2'
 elif bt['upper']<0:decision='EXPANDED_NO_PRIMARY_SUPPORT_AND_WORSE_THAN_BT2'
 else:decision='EXPANDED_INCONCLUSIVE'
 exposure=_preexisting_outcome_exposure(repo_root)
 return {'schema':'bt2a_gate1_nq_all5_result_v1','status':'COMPLETE_GATE1_NQ_ALL5_POST_OUTCOME_REPLICATION','generated_utc':datetime.now(timezone.utc).isoformat(),'instrument':INSTRUMENT,'decision':decision,'CAMPAIGN_OUTCOMES_OPENED':True,'PREEXISTING_OUTCOME_EXPOSURE':exposure['label'],'PREEXISTING_OUTCOME_EXPOSURE_DETAIL':exposure,'EDGE_DECLARED':False,'confirmatory_eligible':False,'promotion_eligible':False,'underpowered_for_2p5_ticks':False,'power_target_met_by_session_count':len(rows)>=133,'n_sessions':len(rows),'arms':['K_ABS','K_ABS_SHUFFLE','K_BT2','N_RAND'],'estimand':'median(MFE_ticks)-median(MAE_ticks), equal CME-session weight','contrasts':{'K_ABS_minus_N_RAND':pr,'K_ABS_minus_K_BT2':bt,'K_ABS_minus_K_ABS_SHUFFLE':sh},'event_counts':counts,'excluded_events':exclusions,'code_provenance':provenance,'session_results':rows,'sample':{'registry_schema':sr['schema'],'registry_payload_sha256':sr['registry_payload_sha256'],'n_sessions':len(rows),'contracts':sr['selection']['contracts'],'policy':sr['selection']['policy'],'left_censoring':sr['selection']['left_censoring']},'execution':{'mode':'fresh_process_per_session_checkpointed','warmup':'immediately preceding valid session','absorption_lookback_buckets':int(K_ABS_PARAMS_NQ['AbsorptionLookback']),'ticks_per_bucket':25,'session_boundary':'hard','fill':'first canonical tick strictly after signal'},'interpretation':{'estimand':'equal-session mean contrast of session-level median(MFE_ticks)-median(MAE_ticks)','is_realized_pnl':False,'is_net_of_costs':False,'costs_or_slippage_included':False,'primary_null':'matched random execution anchors under the frozen stratification and horizon','shuffle_passes_95pct':sh['lower']>0,'bt2_noninferiority_passes_95pct':bt['lower']>=0,'allowed_claim':'post-outcome evidence only for the stated estimand and null in this expanded sample','forbidden_claims':['net ticks','scientifically proven alpha','general proof of no luck or noise','edge declaration','promotion']}}
def finalize(*,repo_root:Path,checkpoint_dir:Path,output_dir:Path)->dict[str,Any]:
 sr,ir,sp=_context(repo_root);rows=[];exclusions=[];counts={c:{'K_ABS':0,'K_BT2':0,'selected_sessions':0} for c in sr['selection']['contracts']}
 for i,reg in enumerate(sr['sessions']):
  p=checkpoint_dir/_checkpoint_name(i,reg)
  if not p.exists():raise FileNotFoundError(f'missing checkpoint {i}: {p}')
  cp=_load(p)
  if cp['sample_registry_sha256']!=sr['registry_payload_sha256'] or cp['input_registry_sha256']!=ir['registry_payload_sha256'] or cp.get('runtime_sha256')!=_runtime_sha(repo_root):raise ValueError(f'stale checkpoint {p}')
  r=cp['row'];rows.append(r);exclusions.extend(cp['excluded_events']);c=reg['contract'];counts[c]['selected_sessions']+=1;counts[c]['K_ABS']+=r['K_ABS_events'];counts[c]['K_BT2']+=r['K_BT2_events']
 prov={'runner':'edgelab.research.bt2_gate1_nq_all5','execution':'fresh_process_per_session_checkpointed','sample_registry_sha256':sr['registry_payload_sha256'],'input_registry_sha256':ir['registry_payload_sha256'],'spec_file':'specs/bt2a_gate1_nq_all5_post_outcome_replication_v1.json'};result=_build_result(rows=rows,counts=counts,exclusions=exclusions,sr=sr,sp=sp,provenance=prov,repo_root=repo_root);raw=json.dumps(result,sort_keys=True,separators=(',',':')).encode();result['result_payload_sha256']=hashlib.sha256(raw).hexdigest();output_dir.mkdir(parents=True,exist_ok=True);tmp=output_dir/'gate1_nq_all5_result.json.tmp';final=output_dir/'gate1_nq_all5_result.json';tmp.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');tmp.replace(final);print(json.dumps({'status':result['status'],'decision':result['decision'],'n_sessions':result['n_sessions'],'contrasts':result['contrasts'],'result_payload_sha256':result['result_payload_sha256']},indent=2),flush=True);return result
def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,default=Path('.'));p.add_argument('--data-dir',type=Path);p.add_argument('--checkpoint-dir',type=Path,required=True);p.add_argument('--output-dir',type=Path);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--session-index',type=int);g.add_argument('--finalize',action='store_true');a=p.parse_args();root=a.repo_root.resolve();cp=a.checkpoint_dir.resolve()
 if a.finalize:
  if a.output_dir is None:p.error('--output-dir is required with --finalize')
  finalize(repo_root=root,checkpoint_dir=cp,output_dir=a.output_dir.resolve())
 else:
  if a.data_dir is None:p.error('--data-dir is required with --session-index')
  write_checkpoint(repo_root=root,data_dir=a.data_dir.resolve(),checkpoint_dir=cp,index=a.session_index)
 return 0
if __name__=='__main__':raise SystemExit(main())

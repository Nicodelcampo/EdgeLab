#!/usr/bin/env python3
"""Pure, target-free contract validators for BT2A NQ Gate 1 drafts."""
from __future__ import annotations
import hashlib, json, math
from pathlib import Path
from statistics import NormalDist
from typing import Any

FORMAL_STATUS='SELECTED_STABLE_NQ_CONFIGURATION'
INFORMAL_STATUS='INFORMAL_EARLY_STOP_NQ_CONFIGURATION'
INFORMAL_MODE='INFORMAL_FIXED_CONFIG_ALL5'
INFORMAL_CLASS='EXPLORATORY_NON_CONFIRMATORY_NON_PROMOTABLE'
CONFIG_ID='bt2a_nq_7e84981882b0b380'

def sha256_file(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def canonical_sha256(v:Any)->str:
 return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def load_json(path:Path)->dict[str,Any]:
 v=json.loads(path.read_text(encoding='utf-8'))
 if not isinstance(v,dict): raise RuntimeError(f'JSON root must be object: {path}')
 return v

def payload_valid(v:dict[str,Any])->bool:
 d=v.get('payload_sha256'); body={k:x for k,x in v.items() if k!='payload_sha256'}
 return isinstance(d,str) and len(d)==64 and canonical_sha256(body)==d

def _bound(root:Path,rel:str,digest:str)->Path:
 if not isinstance(rel,str) or not rel or Path(rel).is_absolute() or '..' in Path(rel).parts: raise RuntimeError('unsafe bound path')
 p=(root/rel).resolve(); rr=root.resolve()
 if not p.is_relative_to(rr) or p.is_symlink() or not p.is_file(): raise RuntimeError(f'missing/unsafe bound file: {rel}')
 if sha256_file(p)!=digest: raise RuntimeError(f'bound file SHA mismatch: {rel}')
 return p

def selection_provenance_missing(source:dict[str,Any])->list[str]:
 if source.get('required_selection_status')!=INFORMAL_STATUS: return []
 out=[]
 for k in ('provenance_amendment_file','provenance_amendment_sha256','gate1_classification'):
  if not source.get(k): out.append(k)
 if source.get('selected_config_id')!=CONFIG_ID: out.append('selected_config_id')
 return out

def validate_selection_provenance(spec:dict[str,Any],root:Path,require_frozen:bool)->dict[str,Any]:
 s=spec.get('source_selection') or {}; status=s.get('required_selection_status')
 if status==FORMAL_STATUS:
  if s.get('provenance_mode') not in (None,'FORMAL_PREREGISTERED_SELECTION'): raise RuntimeError('formal status/provenance mismatch')
  return {'mode':'FORMAL_PREREGISTERED_SELECTION','status':status,'confirmatory_eligible':True,'promotion_eligible':True}
 if status!=INFORMAL_STATUS or s.get('provenance_mode')!=INFORMAL_MODE: raise RuntimeError('unsupported selection provenance')
 if s.get('selected_config_id')!=CONFIG_ID or s.get('gate1_classification')!=INFORMAL_CLASS: raise RuntimeError('informal config/classification mismatch')
 if s.get('confirmatory_eligible') is not False or s.get('promotion_eligible') is not False: raise RuntimeError('informal route cannot be confirmatory/promotable')
 p=_bound(root,s.get('provenance_amendment_file'),s.get('provenance_amendment_sha256'))
 a=load_json(p)
 if not payload_valid(a) or a.get('schema_version')!='bt2a_nq_informal_all5_provenance_amendment_v1': raise RuntimeError('invalid informal provenance amendment')
 if require_frozen and a.get('status')!='FROZEN_PROVENANCE_AMENDMENT': raise RuntimeError('informal provenance amendment is not frozen')
 if a.get('decision',{}).get('selected_config_id')!=CONFIG_ID: raise RuntimeError('amendment config mismatch')
 d=a['decision']; _bound(root,d['file'],d['file_sha256'])
 g=a.get('gate1_interpretation') or {}
 if g.get('classification')!=INFORMAL_CLASS or g.get('confirmatory_eligible') is not False or g.get('promotion_eligible') is not False: raise RuntimeError('amendment interpretation mismatch')
 return {'mode':INFORMAL_MODE,'status':status,'amendment_file_sha256':sha256_file(p),'classification':INFORMAL_CLASS,'confirmatory_eligible':False,'promotion_eligible':False}

def validate_macro_policy(value:dict[str,Any],require_frozen:bool)->list[str]:
 if not payload_valid(value) or value.get('schema_version')!='bt2a_nq_gate1_macro_policy_v1': raise RuntimeError('invalid macro policy')
 if value.get('policy')!='NO_MACRO_EXCLUSION_STRATIFICATION_OR_SELECTION' or value.get('events')!=[] or value.get('event_count')!=0: raise RuntimeError('macro null-policy drift')
 r=value.get('runner_requirements') or {}
 if r.get('may_filter_events') is not False or r.get('may_create_subgroups') is not False: raise RuntimeError('macro policy opens post-hoc capability')
 return ['macro_policy.freeze'] if require_frozen and value.get('status')!='FROZEN_NO_MACRO_ADJUSTMENT' else []

def power_missing(value:dict[str,Any],require_frozen:bool=True)->list[str]:
 if not payload_valid(value) or value.get('schema_version')!='bt2a_nq_gate1_power_design_v1': raise RuntimeError('invalid power design')
 miss=[]; c=value['cluster_design']; e=value['effect_design']; v=value['coverage']; a=value['arm_density']
 checks=[('power.mde_ticks',e.get('mde_ticks'),lambda x:isinstance(x,(int,float)) and x>0),('power.paired_session_sd_ticks',e.get('paired_session_sd_ticks'),lambda x:isinstance(x,(int,float)) and x>0),('power.icc',c.get('icc'),lambda x:isinstance(x,(int,float)) and 0<=x<1),('power.mean_events_per_session',c.get('mean_events_per_session'),lambda x:isinstance(x,(int,float)) and x>=1),('power.effective_sessions_available',v.get('effective_sessions_available'),lambda x:isinstance(x,(int,float)) and x>0),('power.effective_sessions_required',v.get('effective_sessions_required'),lambda x:isinstance(x,int) and x>=v['minimum_effective_sessions'])]
 for name,x,ok in checks:
  if not ok(x): miss.append(name)
 for arm in ('K_ABS','K_BT2'):
  if not isinstance(a.get(arm),dict) or not isinstance(a[arm].get('events'),int) or a[arm]['events']<1: miss.append(f'power.arm_density.{arm}')
 if a.get('N_RAND_capacity_ok') is not True: miss.append('power.arm_density.N_RAND_capacity_ok')
 if isinstance(v.get('effective_sessions_available'),(int,float)) and isinstance(v.get('effective_sessions_required'),int) and v['effective_sessions_available'] < v['effective_sessions_required']:
  miss.append('power.insufficient_effective_sessions')
 if require_frozen and value.get('status')!='FROZEN_POWER_INPUTS': miss.append('power.freeze')
 blockers=set(miss)-{'power.freeze'}
 if not blockers:
  alpha=e['alpha_family']/value['family']['cells']; zcrit=NormalDist().inv_cdf(1-alpha/2); zpow=NormalDist().inv_cdf(e['target_power'])
  required=math.ceil(((zcrit+zpow)*e['paired_session_sd_ticks']/e['mde_ticks'])**2)
  if v['effective_sessions_required']!=max(v['minimum_effective_sessions'],required): raise RuntimeError('effective_sessions_required inconsistent with frozen formula')
  deff=1+(c['mean_events_per_session']-1)*c['icc']
  if abs(c.get('design_effect',-1)-deff)>1e-12: raise RuntimeError('design_effect inconsistent with ICC/cluster size')
 return sorted(set(miss))

def validate_runner_contract(value:dict[str,Any])->list[str]:
 if not payload_valid(value) or value.get('schema_version')!='bt2a_nq_gate1_runner_contract_v1': raise RuntimeError('invalid runner contract')
 f=value['family']; cells={(b,h) for b in f['barriers_ticks'] for h in f['horizons_observations']}
 if len(cells)!=16 or f.get('evaluate_full_family') is not True: raise RuntimeError('runner family drift')
 if value.get('implementation_authorized') is not False or value.get('execution_authorized') is not False: raise RuntimeError('blocked runner contract has capability')
 decisions=value['estimand_resolution_required_before_implementation']
 expected={
  'primary_outcome_encoding':'SIGNED_FIRST_PASSAGE_TICKS',
  'primary_contrast':'K_ABS_MINUS_N_RAND_MATCHED_WITHIN_CME_SESSION',
  'multiplicity_scope_across_three_comparators':'HOLM_16_PRIMARY_ONLY; SECONDARY_COMPARATORS_NON_TRIGGERING',
  'paired_session_variance_definition':'UNBIASED_SAMPLE_VARIANCE_OF_EQUAL_WEIGHT_SESSION_CONTRASTS',
 }
 missing=['runner.'+k for k,v in expected.items() if decisions.get(k)!=v]
 roles=value.get('contrast_roles') or {}; mult=value.get('multiplicity') or {}; var=value.get('paired_session_variance') or {}
 if roles.get('secondary_contrasts_may_trigger_supported_label') is not False: missing.append('runner.secondary_non_triggering')
 if mult.get('primary_method')!='HOLM_STEP_DOWN_TWO_SIDED_ALPHA_0_05': missing.append('runner.primary_multiplicity')
 if var.get('pseudoreplication_forbidden') is not True or var.get('event_level_rows_as_independent_replicates') is not False: missing.append('runner.variance_pseudoreplication_guard')
 return sorted(set(missing))

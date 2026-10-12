"""Offline structural/source-pin review of a technical replay receipt.
NOT independent event recount, authenticated custody or adoption approval.
"""
import math,re,json,hashlib
from tools.research_ops.knowledge import _pinned_bytes,_json,_sha
from tools.research_ops.benchmarks.mnq_primary_grid_parity import PLAN,KEYS,INTS,FLOATS,plan_hash
FIELDS={'schema','plan','plan_sha256','rows_checked','empty_rows','sessions','private_input_rows','integer_fields_checked','float_fields_checked_exact_roundtrip','reference_sha256','counts_sha256','results_sha256','draws_sha256','stage_seconds','wall_seconds','ru_maxrss_bytes','rss_scope','python','numpy','pandas','exact_parity','full_pipeline_parity','matched_contrast_parity','longevity_detector_profiled','private_rows_exported','validated_edge','adoption_authorized','source_checkpoint','program_sha256','outer_seconds'}
STAGES={'input_load_and_identity','frozen_draws_and_weights','count_formation','resampling_and_metrics','reference_compare_and_hash'}
PROGRAMS={'tools/research_ops/benchmarks/mnq_primary_grid_parity.py','tools/research_ops/benchmarks/mnq_resampling_replay.py','tools/research_ops/session_resampling.py'}
def seconds(x):return type(x) in (int,float) and math.isfinite(x) and x>=0

def review(path,*,expected_receipt_sha256,expected_source_commit,expected_program_sha256):
 if not isinstance(expected_source_commit,str) or not re.fullmatch('[0-9a-f]{40}',expected_source_commit):raise ValueError('external source checkpoint required')
 if type(expected_program_sha256) is not dict or set(expected_program_sha256)!=PROGRAMS:raise ValueError('complete externally pinned program set required')
 for h in expected_program_sha256.values():_sha(h)
 r=_json(_pinned_bytes(path,expected_receipt_sha256))
 if type(r) is not dict or set(r)!=FIELDS or r['schema']!='mnq_full_primary_grid_parity_v1':raise ValueError('closed technical receipt required')
 if r['plan']!=PLAN or hashlib.sha256(json.dumps(r['plan'],sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()!=plan_hash() or r['plan_sha256']!=plan_hash() or r['source_checkpoint']!=expected_source_commit or r['program_sha256']!=expected_program_sha256:raise ValueError('scope or source pins disagree')
 if type(r['rows_checked']) is not int or r['rows_checked']!=11340 or type(r['sessions']) is not int or r['sessions']!=46:raise ValueError('complete grid/session census required')
 if type(r['empty_rows']) is not int or not 0<=r['empty_rows']<=11340 or type(r['private_input_rows']) is not int or r['private_input_rows']!=68499:raise ValueError('input/empty census mismatch')
 if r['integer_fields_checked']!=INTS or r['float_fields_checked_exact_roundtrip']!=FLOATS or r['reference_sha256']!=PLAN['inputs']['effects']['sha256']:raise ValueError('complete original field/reference scope required')
 for k in ['counts_sha256','results_sha256','draws_sha256']:_sha(r[k])
 if r['exact_parity'] is not True or any(r[k] is not False for k in ['full_pipeline_parity','matched_contrast_parity','longevity_detector_profiled','private_rows_exported','validated_edge','adoption_authorized']):raise ValueError('technical-only authority ceiling required')
 if type(r['stage_seconds']) is not dict or set(r['stage_seconds'])!=STAGES or not all(seconds(x) for x in r['stage_seconds'].values()):raise ValueError('fixed finite stage census required')
 if not seconds(r['wall_seconds']) or not seconds(r['outer_seconds']) or not 0<r['wall_seconds']<=r['outer_seconds']<=900 or sum(r['stage_seconds'].values())>r['wall_seconds']+0.001:raise ValueError('deadline/stage accounting mismatch')
 if type(r['ru_maxrss_bytes']) is not int or not 0<r['ru_maxrss_bytes']<=PLAN['memory_bytes'] or r['rss_scope']!='SELF_HIGH_WATER_TECHNICAL_REPLAY_ONLY_NOT_ORIGINAL_JOB':raise ValueError('bounded technical-only memory measurement required')
 for k in ['python','numpy','pandas']:
  if not isinstance(r[k],str) or not re.fullmatch(r'[0-9][0-9A-Za-z.+_-]{0,39}',r[k]):raise ValueError('bounded runtime version required')
 return {'status':'PASS_STRUCTURAL_SOURCE_PINNED_TECHNICAL_RECEIPT_NOT_CUSTODY','receipt_sha256':expected_receipt_sha256,'rows_checked':11340,'fields_per_row':len(KEYS)+len(INTS)+len(FLOATS),'stored_reference_parity_reported':True,'scope':PLAN['scope'],'source_checkpoint':expected_source_commit,'authenticated_custody':False,'independent_event_recount':False,'full_pipeline_parity':False,'source_certified':False,'execution_allowed':False,'adoption_authorized':False,'canonical_write_authorized':False}

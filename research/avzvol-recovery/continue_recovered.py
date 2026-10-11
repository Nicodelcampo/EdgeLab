"""Fail-closed sequential recovery; no historical checkpoint is invented."""
import os,json,subprocess,pathlib,hashlib,shutil,datetime
P=pathlib.Path('/data/recovery');L=pathlib.Path('/data/analysis/avzvol-longevity');F=pathlib.Path('/data/analysis/avzvol-focus');M=pathlib.Path('/data/analysis/avzvol-matrix-run');PY='/data/analysis/research-runtime/bin/python';contracts=['MNQ_12-25','MNQ_03-26','MNQ_06-26','MNQ_09-26','MNQ_09-25'];assert json.load(open(P/'preflight.json'))['status']=='PASS_EXACT_RECOVERY_PREFLIGHT'
def sha(p):return hashlib.file_digest(pathlib.Path(p).open('rb'),'sha256').hexdigest()
state=dict(status='RUNNING_RECOVERED_CAMPAIGNS',order=contracts,completed_new_runs=[],historical_pilot_complete_published='MNQ_12-26 at798411780dad69eedc865153ae84a5e819d5ae03',historical_MNQ_09_25_focal='last observed completed, unpublished detailed artifacts lost; scheduled deterministic regeneration, not accepted as locally verified evidence',original_matrix_pairs_per_contract=1935360,focal_definitions_per_contract=3207600,bank_sha256=sha(F/'frozen-replication-bank.json'),holdout_opened=False,pnl_computed=False,source_certified=False,base_commit='798411780dad69eedc865153ae84a5e819d5ae03',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),controller_sha256=sha(__file__))
def save():
 p=P/'campaign-status.json';q=p.with_suffix('.tmp');q.write_text(json.dumps(state,indent=2)+'\n');os.replace(q,p)
def run(script,c,stage):
 state.update(active_contract=c,stage=stage);save();root=L/c;root.mkdir(exist_ok=True);ee={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','NUMBA_NUM_THREADS':'1','REPLICATION_ROOT':str(root),'REPLICATION_CONTRACT':c,'MATRIX_CONTRACT':c,'FOCUS_CONTRACT':c};log=root/('recovery-'+stage+'.log')
 with log.open('w') as out:subprocess.run([PY,str(script)],env=ee,stdout=out,stderr=subprocess.STDOUT,check=True)
 print('STEP_COMPLETE',c,stage,flush=True)
try:
 save()
 for c in contracts:
  assert shutil.disk_usage('/data').free>7_000_000_000,'INSUFFICIENT_DISK_FAIL_CLOSED';root=L/c;root.mkdir(exist_ok=True);assert not (root/'evidence.json').exists(),'PREEXISTING_EVIDENCE_REQUIRES_EXPLICIT_REVIEW'
  run(L/'run.py',c,'longevity');ev=json.load(open(root/'evidence.json'));assert ev['scope_leakage']==0 and ev['landmark_rule_groups']==2772 and ev['feature_schema_version']==2
  run(L/'analyze.py',c,'primary-analysis');run(L/'models.py',c,'incremental-diagnostic')
  for script,stage in [('run.py','focal'),('review.py','independent-review'),('replicate_bank.py','fixed-bank'),('audit_censoring.py','censor-envelopes'),('check_absolute.py','absolute-and-control')]:
   assert sha(F/'frozen-replication-bank.json')==state['bank_sha256'],'BANK_CHANGED_FAIL_CLOSED';run(F/script,c,stage)
  assert json.load(open(F/c/'evidence.json'))['nominal_event_condition_pairs']==3207600
  run(M/'run.py',c,'full-matrix');run(M/'verify.py',c,'matrix-coverage');assert json.load(open(M/c/'coverage-verification.json'))['config_rule_pairs']==1935360
  run(M/'analyze_support.py',c,'matrix-support')
  a=json.load(open(root/'manifest.json'));pin=a['source'];raw=pathlib.Path('/data/raw/avzvol-ticks')/pin['file'];assert sha(raw)==pin['sha256'];removed=0
  for base in [root/c,M/c]:
   for f in base.glob('*-private.bin'):removed+=f.stat().st_size;f.unlink()
  state['completed_new_runs'].append(dict(contract=c,longevity_groups=2772,focal_definitions=3207600,matrix_pairs=1935360,source_unchanged=True,removed_regenerable_cache_bytes=removed));save();print('COMPLETE_ALL_PASSES',c,flush=True)
 state.update(status='RECOVERED_MISSING_PASSES_COMPLETE_NOT_STRATEGY_VALIDATION',stage='complete');save()
except Exception as e:
 state.update(status='STOPPED_FAIL_CLOSED',error=str(e));save();raise

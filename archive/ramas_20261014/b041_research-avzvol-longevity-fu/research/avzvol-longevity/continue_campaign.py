"""Sequential resource-safe continuation of both explicitly requested campaigns."""
import json,subprocess,os,time,gzip,hashlib,shutil
from pathlib import Path
L=Path('/data/analysis/avzvol-longevity');M=Path('/data/analysis/avzvol-matrix-run');contracts=['MNQ_12-26','MNQ_09-25','MNQ_12-25','MNQ_03-26','MNQ_06-26','MNQ_09-26'];env={**os.environ,'OPENBLAS_NUM_THREADS':'1','PYTHONPATH':'/data/analysis/research-runtime:/data/analysis/avzvol-longevity:/data/analysis/avzvol-replication-rest'};status={'status':'RUNNING_TWO_CAMPAIGNS','contracts':contracts,'completed':[],'nominal_matrix_pairs_per_contract':1935360,'matrix_pairs_across_six_contracts':1935360*6,'long_zone_campaign_separate':True,'holdout_opened':False};(L/'campaign-status.json').write_text(json.dumps(status,indent=2)+'\n')
def wait_exit(path,log):
 while not path.exists():
  if log.exists() and 'Traceback (most recent call last)' in log.read_text()[-5000:]:raise RuntimeError('UPSTREAM_FAILED:'+str(log))
  time.sleep(10)
 assert path.read_text().strip()=='0',('UPSTREAM_NONZERO',path.read_text())
def run(script,root,ee,log):
 with log.open('w') as f:subprocess.run(['python3',str(script)],env=ee,stdout=f,stderr=subprocess.STDOUT,check=True)
try:
 for c in contracts:
  root=L/c;root.mkdir(exist_ok=True);ee={**env,'REPLICATION_ROOT':str(root),'REPLICATION_CONTRACT':c};status['active_contract']=c;(L/'campaign-status.json').write_text(json.dumps(status,indent=2)+'\n')
  if c==contracts[0]:wait_exit(root/'exit-code',root/'run.log')
  elif not (root/'evidence.json').exists():
   # Do not start a larger contract while matrix buffers of another contract are active.
   assert shutil.disk_usage('/data').free>7_000_000_000,'INSUFFICIENT_DISK_FAIL_CLOSED'
   run(L/'run.py',root,ee,root/'run.log')
  ev=json.load(open(root/'evidence.json'));assert ev['scope_leakage']==0 and ev['landmark_rule_groups']==2772
  if not (root/'analysis-evidence.json').exists():run(L/'analyze.py',root,ee,root/'analysis.log')
  if not (root/'incremental-model-diagnostic.json').exists():run(L/'models.py',root,ee,root/'models.log')
  if c==contracts[0]:
   wait_exit(M/'exit-code',M/'run.log');shutil.copy2(M/'progress.json',M/c/'progress.json');shutil.copy2(M/'manifest.json',M/c/'manifest.json')
  else:
   run(M/'run.py',M/c,{**env,'MATRIX_CONTRACT':c},root/'matrix.log')
  progress=json.load(open(M/c/'progress.json'));assert progress['completed_config_rule_pairs']==1935360
  run(M/'verify.py',M/c,{**env,'MATRIX_CONTRACT':c},root/'matrix-verification.log')
  # Archive verified derived signals, never alter source Parquet.
  signal=root/'signals-private.csv';archive=root/'signals-private.csv.gz'
  if signal.exists():
   with signal.open('rb') as src,gzip.open(archive,'wb',compresslevel=1) as dst:shutil.copyfileobj(src,dst,8<<20)
   def digest(stream):
    h=hashlib.sha256()
    for chunk in iter(lambda:stream.read(8<<20),b''):h.update(chunk)
    return h.hexdigest()
   with signal.open('rb') as src,gzip.open(archive,'rb') as dst:assert digest(src)==digest(dst)
   signal.unlink()
  removed=0
  for base in [root/c,M/c]:
   for f in base.glob('*-private.bin'):removed+=f.stat().st_size;f.unlink()
  status['completed'].append({'contract':c,'matrix_pairs':1935360,'long_zone_groups':2772,'source_unchanged':True,'removed_regenerable_cache_bytes':removed});(L/'campaign-status.json').write_text(json.dumps(status,indent=2)+'\n');print('COMPLETE_BOTH',c,flush=True)
 status['status']='LABELS_AND_LONGEVITY_PRIMARY_EFFECTS_COMPLETE_ALL_SIX_NOT_STRATEGY_VALIDATION';(L/'campaign-status.json').write_text(json.dumps(status,indent=2)+'\n')
except Exception as exc:
 status.update(status='STOPPED_FAIL_CLOSED',error=str(exc));(L/'campaign-status.json').write_text(json.dumps(status,indent=2)+'\n');raise

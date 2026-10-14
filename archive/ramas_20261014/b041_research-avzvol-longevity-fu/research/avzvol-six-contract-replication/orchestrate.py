import os,sys,subprocess,json,shutil,time
from pathlib import Path
P=Path('/data/analysis/avzvol-replication-rest');contracts=['MNQ_03-26','MNQ_12-25','MNQ_06-26','MNQ_09-26'];base=os.environ.copy();base['OPENBLAS_NUM_THREADS']='1';base['PYTHONPATH']='/data/analysis/research-runtime:/data/analysis/avzvol-pilot:/data/analysis/avzvol-expansion:/data/analysis/avzvol-replication-rest'
status={'status':'RUNNING','fixed_rule_unchanged':True,'contracts':[]};(P/'campaign-status.json').write_text(json.dumps(status,indent=2))
for c in contracts:
 root=P/c;root.mkdir(exist_ok=True);env={**base,'REPLICATION_ROOT':str(root),'REPLICATION_CONTRACT':c}
 for f in ['run_replication.py','bounded_csr.py']:shutil.copy2(P/f,root/f)
 print('START',c,flush=True)
 with (root/'run.log').open('w') as log:
  x=subprocess.run([sys.executable,str(P/'run_replication.py')],env=env,stdout=log,stderr=subprocess.STDOUT)
 if x.returncode:status.update(status='STOPPED_FAIL_CLOSED',failed_contract=c,exit_code=x.returncode);(P/'campaign-status.json').write_text(json.dumps(status,indent=2));raise SystemExit(x.returncode)
 with (root/'independent-check.log').open('w') as log:subprocess.run([sys.executable,str(P/'check_contract.py')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 evidence=json.loads((root/'evidence.json').read_text());assert evidence['scope_leakage']==0 and len(evidence['reference_checks'])==45
 # Only regenerable derived binaries; source Parquet and private signals preserved.
 removed=0
 for f in (root/c).glob('*-private.bin'):removed+=f.stat().st_size;f.unlink()
 status['contracts'].append({'contract':c,'completed':True,'reference_strata':45,'derived_cache_removed_bytes':removed});(P/'campaign-status.json').write_text(json.dumps(status,indent=2));print('COMPLETE',c,'derived_cache_removed',removed,flush=True)
status['status']='FOUR_CONTRACT_LABELS_COMPLETE';(P/'campaign-status.json').write_text(json.dumps(status,indent=2));print(status,flush=True)

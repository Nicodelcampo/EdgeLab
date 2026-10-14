from pathlib import Path
import json,subprocess,concurrent.futures,os
p=Path('/data/analysis/avzvol-source-unlock');d=json.loads((p/'preflight.json').read_text());assert d['global_all_six_passed']
repo=Path('/data/edgelab-parameter-grid');env={**os.environ,'PYTHONPATH':'/data/analysis/research-runtime:'+str(repo)}
def go(r):
 dest=p/'structural'/r['contract'];args=['python3',str(repo/'tools/audit_kaggle_raw_ticks.py'),'--path','/data/raw/avzvol-ticks/'+r['file'],'--expected-sha256',r['sha256'],'--expected-bytes',str(r['bytes']),'--expected-rows',str(r['rows']),'--instrument','MNQ','--contract',r['contract'].replace('_',' '),'--include-clock-diagnostics','--out-dir',str(dest)]
 log=p/(r['contract']+'.audit.log')
 with log.open('w') as out:run=subprocess.run(args,env=env,stdout=out,stderr=out)
 print(json.dumps({'contract':r['contract'],'exit_code':run.returncode,'report_written':(dest/'summary.json').exists()}),flush=True)
 return run.returncode
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:codes=list(pool.map(go,d['files']))
assert not any(codes),codes

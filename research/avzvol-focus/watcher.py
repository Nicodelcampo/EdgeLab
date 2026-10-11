"""Resource-bounded sidecar using complete derivative signals only."""
import os,time,json,subprocess
from pathlib import Path
P=Path('/data/analysis/avzvol-focus');L=Path('/data/analysis/avzvol-longevity');reg=json.load(open(P/'manifest.json'));done=[]
for c in reg['contracts']:
 root=L/c
 while not (root/'analysis-evidence.json').exists():
  state=json.load(open(L/'campaign-status.json'))
  if state['status'].startswith('STOPPED'):raise SystemExit('BASELINE_STOPPED_FOCAL_SEARCH_PAUSED')
  time.sleep(10)
 if not (P/c/'evidence.json').exists():
  env={**os.environ,'OPENBLAS_NUM_THREADS':'1','PYTHONPATH':'/data/analysis/research-runtime:/data/analysis/avzvol-focus','FOCUS_CONTRACT':c}
  (P/'status.json').write_text(json.dumps({'status':'FOCAL_RUNNING','active_contract':c,'completed':done,'nominal_pairs_per_contract':reg['nominal_event_condition_pairs_per_contract']},indent=2)+'\n')
  with (P/(c+'-run.log')).open('w') as log:subprocess.run(['python3',str(P/'run.py')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 done.append(c);(P/'status.json').write_text(json.dumps({'status':'FOCAL_WAITING_NEXT_BASELINE_CONTRACT','completed':done,'nominal_pairs_per_contract':reg['nominal_event_condition_pairs_per_contract']},indent=2)+'\n')
(P/'status.json').write_text(json.dumps({'status':'FOCAL_ALL_SIX_EXPLORATORY_COMPLETE','completed':done},indent=2)+'\n')

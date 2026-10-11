import os,json,time,subprocess
from pathlib import Path
P=Path('/data/analysis/avzvol-focus');L=Path('/data/analysis/avzvol-longevity');cs=json.load(open(P/'manifest.json'))['contracts'];done=[]
for c in cs:
 r=P/c
 while not (r/'evidence.json').exists():
  if 'Traceback (most recent call last)' in (P/'watcher.log').read_text()[-4000:]:raise SystemExit('FOCAL_STOPPED_REVIEW_PAUSED')
  if json.load(open(L/'campaign-status.json'))['status'].startswith('STOPPED'):raise SystemExit('BASELINE_STOPPED_REVIEW_PAUSED')
  time.sleep(10)
 env={**os.environ,'OPENBLAS_NUM_THREADS':'1','PYTHONPATH':'/data/analysis/research-runtime:/data/analysis/avzvol-focus','FOCUS_CONTRACT':c}
 for script,output in [('review.py','candidate-review-evidence.json'),('replicate_bank.py','fixed-bank-evidence.json')]:
  if not (r/output).exists():
   with (P/(c+'-'+script+'.log')).open('w') as log:subprocess.run(['python3',str(P/script)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 done.append(c);(P/'review-status.json').write_text(json.dumps({'status':'FIXED_BANK_WAITING_NEXT_CONTRACT','completed':done},indent=2)+'\n')
(P/'review-status.json').write_text(json.dumps({'status':'FIXED_BANK_REPLICATION_ALL_SIX_COMPLETE_PREVIOUSLY_INSPECTED_NOT_VIRGIN','completed':done},indent=2)+'\n')

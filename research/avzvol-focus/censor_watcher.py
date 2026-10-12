import json,time,os,subprocess
from pathlib import Path
P=Path('/data/analysis/avzvol-focus');L=Path('/data/analysis/avzvol-longevity');cs=json.load(open(P/'manifest.json'))['contracts'];done=[]
for c in cs:
 r=P/c
 while not (r/'fixed-bank-evidence.json').exists():
  for n in ['watcher.log','review-watcher.log']:
   if 'Traceback (most recent call last)' in (P/n).read_text()[-4000:]:raise SystemExit('FOCAL_OR_BANK_FAILURE_CENSOR_AUDIT_PAUSED')
  if json.load(open(L/'campaign-status.json'))['status'].startswith('STOPPED'):raise SystemExit('BASELINE_STOPPED_CENSOR_AUDIT_PAUSED')
  time.sleep(10)
 if not (r/'censor-audit-evidence.json').exists():
  with (P/(c+'-censor.log')).open('w') as f:subprocess.run(['python3',str(P/'audit_censoring.py')],env={**os.environ,'OPENBLAS_NUM_THREADS':'1','PYTHONPATH':'/data/analysis/research-runtime:/data/analysis/avzvol-focus','FOCUS_CONTRACT':c},stdout=f,stderr=subprocess.STDOUT,check=True)
 done.append(c);(P/'censor-status.json').write_text(json.dumps({'status':'CENSOR_AUDIT_WAITING_NEXT_CONTRACT','completed':done},indent=2)+'\n')

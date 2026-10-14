import json,time,os,subprocess
from pathlib import Path
P=Path('/data/analysis/avzvol-focus');L=Path('/data/analysis/avzvol-longevity');cs=json.load(open(P/'manifest.json'))['contracts'];done=[]
for c in cs:
 r=P/c
 while not (r/'evidence.json').exists():
  if 'Traceback (most recent call last)' in (P/'watcher.log').read_text()[-4000:]:raise SystemExit('FOCAL_STOPPED_ABSOLUTE_CHECK_PAUSED')
  if json.load(open(L/'campaign-status.json'))['status'].startswith('STOPPED'):raise SystemExit('BASELINE_STOPPED_ABSOLUTE_CHECK_PAUSED')
  time.sleep(10)
 if not (r/'absolute-and-control-evidence.json').exists():
  with (P/(c+'-absolute.log')).open('w') as f:subprocess.run(['python3',str(P/'check_absolute.py')],env={**os.environ,'OPENBLAS_NUM_THREADS':'1','PYTHONPATH':'/data/analysis/research-runtime:/data/analysis/avzvol-focus','FOCUS_CONTRACT':c},stdout=f,stderr=subprocess.STDOUT,check=True)
 done.append(c);(P/'absolute-status.json').write_text(json.dumps({'status':'ABSOLUTE_CHECK_WAITING_NEXT_CONTRACT','completed':done},indent=2)+'\n')

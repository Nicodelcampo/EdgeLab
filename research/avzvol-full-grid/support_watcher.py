import json,time,os,subprocess
from pathlib import Path
P=Path('/data/analysis/avzvol-matrix-run');L=Path('/data/analysis/avzvol-longevity');cs=['MNQ_12-26','MNQ_09-25','MNQ_12-25','MNQ_03-26','MNQ_06-26','MNQ_09-26']
for c in cs:
 r=P/c
 while not (r/'coverage-verification.json').exists():
  st=json.load(open(L/'campaign-status.json'))
  if st['status'].startswith('STOPPED'):raise SystemExit('CAMPAIGN_STOPPED_NO_FURTHER_SUPPORT_ANALYSIS')
  time.sleep(10)
 if not (r/'support-evidence.json').exists():
  with (r/'support.log').open('w') as log:subprocess.run(['python3',str(P/'analyze_support.py')],env={**os.environ,'OPENBLAS_NUM_THREADS':'1','PYTHONPATH':'/data/analysis/research-runtime','MATRIX_CONTRACT':c},stdout=log,stderr=subprocess.STDOUT,check=True)
 print('SUPPORT_DONE',c,flush=True)

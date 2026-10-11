"""Fail-closed restart: require verified repair and serialization tests before any inference."""
import json,time,subprocess,os,hashlib
from pathlib import Path
P=Path('/data/analysis/avzvol-longevity');R=P/'MNQ_12-26';deadline=time.time()+600
while not (R/'schema-repair-evidence.json').exists():
 log=(P/'schema-repair.log').read_text()
 if 'Traceback (most recent call last)' in log or time.time()>deadline:raise RuntimeError('REPAIR_NOT_VERIFIED_CAMPAIGN_NOT_RESUMED')
 time.sleep(5)
ev=json.load(open(R/'schema-repair-evidence.json'));assert ev['status']=='PASS_REPAIRED_SCHEMA' and ev['source_unchanged'] and ev['all_16_features_preserved']
for n in ['schema-test-evidence.json','test-evidence.json','cache-test-evidence.json']:assert json.load(open(P/n))['status']=='PASS'
snapshot=P/'corrected-launch-source';snapshot.mkdir(exist_ok=True)
for n in ['run.py','engine.py','feature_schema.py','analyze.py','models.py','continue_campaign.py']:(snapshot/n).write_bytes((P/n).read_bytes())
(P/'restart-evidence.json').write_text(json.dumps({'status':'VERIFIED_REPAIR_RESTART','repaired_contract':'MNQ_12-26','incomplete_contract_restarted_from_beginning':'MNQ_09-25','invalid_outputs_retained':True,'matrix_12_26_preserved':True,'source_sha256':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['run.py','engine.py','feature_schema.py','analyze.py','models.py','continue_campaign.py']}},indent=2)+'\n')
with (P/'continuation-corrected.log').open('w') as log:subprocess.run(['python3',str(P/'continue_campaign.py')],env={**os.environ,'OPENBLAS_NUM_THREADS':'1','PYTHONPATH':'/data/analysis/research-runtime:/data/analysis/avzvol-longevity'},stdout=log,stderr=subprocess.STDOUT,check=True)

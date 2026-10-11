import json,shutil,subprocess,os
from pathlib import Path
import pandas as pd
P=Path('/data/analysis/avzvol-replication-rest');O=Path('/data/analysis/avzvol-replication');C=P/'combined';C.mkdir(exist_ok=True)
remaining=['MNQ_03-26','MNQ_12-25','MNQ_06-26','MNQ_09-26'];allc=['MNQ_09-25','MNQ_12-25','MNQ_03-26','MNQ_06-26','MNQ_09-26','MNQ_12-26'];m=json.loads((O/'manifest.json').read_text());sources={c:O if c in m['contracts'] else P/c for c in allc};roots=[O]+[P/c for c in remaining]
for c,root in sources.items():
 link=C/c
 if not link.exists():link.symlink_to(root/c,target_is_directory=True)
for name in ['rule-counts.csv','daily-counts.csv']:pd.concat([pd.read_csv(root/name) for root in roots],ignore_index=True).to_csv(C/name,index=False)
ms=[json.loads((r/'manifest.json').read_text()) for r in roots];m['contracts']=allc;m['event_dates']={c:next(mm['event_dates'][c] for mm in ms if c in mm['event_dates']) for c in allc};m['source_pins']=[next(pin for mm in ms for pin in mm['source_pins'] if pin['contract']==c) for c in allc];m['scope']='six-contract fixed replication; original discovery labels reused; four remaining contracts added unchanged';m['status']='ALL_SIX_LABELS_COMPLETE';m['implementation_manifests']={c:next(mm for mm in ms if c in mm['contracts']) for c in allc};m['original_code_hashes_reused_for_two_contracts']=m.pop('code_sha256');(C/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
criteria=json.loads((O/'replication-criteria.json').read_text());criteria['primary']='fixed P80/W5/racimo8/1000/20 D40 q50 touch first-D-qualified occupancy<25% bin6250 on every non-discovery contract; same criteria, no retuning';(C/'replication-criteria.json').write_text(json.dumps(criteria,indent=2)+'\n')
es=[json.loads((r/'evidence.json').read_text()) for r in roots];e={'status':'ALL_SIX_CONTRACTS_COMPLETE','contracts':[cc for ee in es for cc in ee['contracts']],'rule_groups':sum(ee['rule_groups'] for ee in es),'label_evaluations_not_independent':sum(ee['label_evaluations_not_independent'] for ee in es),'signal_rows_not_independent':sum(ee['signal_rows_not_independent'] for ee in es),'reference_checks':[cc for ee in es for cc in ee['reference_checks']],'scope_leakage':sum(ee['scope_leakage'] for ee in es),'original_two_contract_labels_reused':True,'new_contracts':remaining,'source_certified':False,'holdout_opened':False,'pnl_computed':False,'source_selection_checks':{c:json.loads((root/c/'source-selection-check.json').read_text()) for c,root in sources.items()}};assert e['scope_leakage']==0 and len(e['reference_checks'])==270;(C/'evidence.json').write_text(json.dumps(e,indent=2)+'\n')
env={**os.environ,'OPENBLAS_NUM_THREADS':'1','PYTHONPATH':'/data/analysis/research-runtime:/data/analysis/avzvol-pilot'}
subprocess.run(['python3',str(P/'analyze_all.py')],env=env,check=True)
s=pd.read_csv(C/'thinned-summary.csv');checks=json.loads((O/'independent-primary-check.json').read_text())['checks'];hist=json.loads((O/'independent-primary-check.json').read_text())['full_history']
for c in remaining:
 rows=json.loads((P/c/'independent-primary-counts.json').read_text())['primary'];checks.extend(rows);hist.extend(rows)
for r in checks:
 x=s[s.contract.eq(r['contract'])&s.origin.eq(r['origin'])&s.D.eq(40)&s.q.eq(.5)&s.bin_records.eq(6250)&s.occupancy_lt.eq('0.25')].iloc[0];assert (r['wins'],r['losses'],r['unresolved'])==(int(x.target_first),int(x.opposite_first),int(x.unresolved))
(C/'independent-primary-check.json').write_text(json.dumps({'status':'PASS','checks':checks,'exact_primary_cells':len(checks),'method':'independent stable sort/groupby earliest trigger before occupancy filter'},indent=2)+'\n');pd.DataFrame(hist).to_csv(C/'full-history-sensitivity.csv',index=False)
print('ALL_PRIMARY_CHECKS_PASS',len(checks),flush=True)

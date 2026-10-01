from pathlib import Path
import json,hashlib,collections,re
import numpy as np,pandas as pd
h=Path(__file__).parent;out=h/'output';m=json.load(open(h/'manifest.json'));c=json.load(open(out/'census.json'));pre=json.load(open(out/'preflight.json'));rows=[json.loads(l) for l in (out/'episodes_PRIVATE.jsonl').read_text().splitlines()];df=pd.DataFrame(rows)
assert len(rows)==3980 and len({x['id'] for x in rows})==len(rows)
assert not c['outcomes_computed'] and c['models_fitted']==0 and not c['holdout_opened'] and c['entry_quote_support_NOT_measured']
assert not df.isna().any().any();assert (df['U']>0).all();assert set(df.direction)=={-1,1}
checks=[];summary=[];quarter=[]
for asset in m['assets']:
 days=m['days_by_asset'][asset]
 for tf in m['timeframes_min']:
  key=f'{asset}|TF{tf}';sub=df[(df.asset==asset)&(df.tf==tf)].copy();v=c['cells'][key]
  # Independent direct dictionary counts, then cross-foot through a pandas groupby.
  count=collections.Counter(x['day'] for x in rows if x['asset']==asset and x['tf']==tf);daily=[count[d] for d in days]
  assert sum(daily)==len(sub)==v['reserved_intents'];assert set(sub.day).issubset(set(days));assert dict(sub.groupby('day').size())==dict(count)
  assert np.mean(daily)==v['mean_per_session'] and np.median(daily)==v['median_per_session'];assert sum(n>0 for n in daily)==v['active_sessions'];assert v['zero_sessions']==sum(n==0 for n in daily)
  assert int(sub.separated.sum())==v['separated_subset'];assert sub.groupby('contract').size().to_dict()==v['by_contract'];assert sub.assign(month=sub.day.str[:6]).groupby('month').size().to_dict()==v['by_month']
  timestamps=pd.to_datetime(sub.signal_ns,utc=True).dt.tz_convert('America/New_York');assert (timestamps.dt.strftime('%Y%m%d').to_numpy()==sub.day.to_numpy()).all();minute=timestamps.dt.hour*60+timestamps.dt.minute;assert (minute>=600).all() and (minute<=885).all();assert sub.signal_ns.max()<1782864000000000000
  for contract,rr in sub.groupby('contract'):assert (np.diff(np.sort(rr.signal_ns))>1860*10**9).all()
  assert (sub.episode_bars>=1).all() and (sub.episode_bars<=10).all()
  support=bool(len(sub)>=200 and np.median(daily)>=4 and sum(n>0 for n in daily)>=.8*len(days));assert support==v['frequency_support'];checks.append({'key':key,'rows':len(sub),'independent_counts_PASS':True})
  daily_separated=[int(((sub.day==d)&sub.separated).sum()) for d in days]
  if tf==c['selection_by_frozen_frequency_rule'][asset]:summary.append({'asset':asset,'tf_min':tf,'sessions':len(days),'intents':len(sub),'mean_intents_per_session':float(np.mean(daily)),'median_intents_per_session':float(np.median(daily)),'separated_intents':int(sub.separated.sum()),'separated_mean_per_session':float(np.mean(daily_separated)),'separated_median_per_session':float(np.median(daily_separated)),'active_sessions':sum(n>0 for n in daily)})
  for q,months in [('2025Q4',['202510','202511','202512']),('2026Q1',['202601','202602','202603']),('2026Q2',['202604','202605','202606'])]:
   selecteddays=[d for d in days if d[:6] in months];nums=[count[d] for d in selecteddays];quarter.append({'asset':asset,'tf':tf,'quarter':q,'sessions':len(nums),'intents':sum(nums),'mean':float(np.mean(nums)),'median':float(np.median(nums))})
 for_tf=c['cells'];selection=5 if for_tf[asset+'|TF5']['frequency_support'] else 1 if for_tf[asset+'|TF1']['frequency_support'] else None;assert selection==c['selection_by_frozen_frequency_rule'][asset]
prefix=json.load(open(out/'prefix_checks.json'));assert len(prefix)==c['prefix_checks']==72 and c['prefix_pass'] and all(x['pass'] for x in prefix)
prof=json.load(open(out/'profiles.json'));assert len(prof)==24 and all(x['catalog_rows_reconciled'] for x in prof)
# Compare every per-file count with the failed v2 computation logs: no event-count change by the serialization fix.
logs=json.loads((h/'v2_failure_log_PRIVATE.json').read_text());logcounts={}
for rec in logs:
 match=re.search(r'census (MNQ|RTY|YM) (\S+) (1|5) (\d+)',rec['data'])
 if match:
  asset,file,tf,n=match.groups();logcounts[(asset,file.split('_ticks')[0].replace('_',' ')[-5:],int(tf))]=int(n)
assert len(logcounts)==24
for (asset,contract,tf),n in logcounts.items():assert len(df[(df.asset==asset)&(df.contract==asset+' '+contract)&(df.tf==tf)])==n
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
audit={'rows':len(rows),'unique_ids':True,'six_cells_counts_dates_contract_month_and_reservation_PASS':True,'prefix_checks':72,'prefix_pass':True,'source_exact_private_v3_verified':True,'v2_v3_all24fileTFcounts_identical':True,'all24profiles_catalog_rows_reconciled':True,'ledger_sha256':sha(out/'episodes_PRIVATE.jsonl'),'manifest_sha256':sha(h/'manifest.json'),'census_sha256':sha(out/'census.json'),'outcomes_accessed':False,'entry_quotes_fills_costs_clock_NOT_certified':True,'holdout_opened':False,'scope':'Ledger bookkeeping all3980;72sampleprefixes;oneRTYdate scalar QA prior;NOT independent detector replay entire12rawfiles'}
plan=[{'comparison':'chosen TF1 frequency by asset','grain':'reserved intent counts / all own-asset eligible sessions','population':'154/175/177 dates; unequal; no cross-asset quality inference','unit':'intents/session','disposition':'table','reason':'Status answer with only3selected mean values; compact lookup is clearer than near-identical bars'},{'comparison':'TF1 vsTF5 per-asset median','grain':'each asset separately; no pooling medians','unit':'intents/session','disposition':'prose','reason':'Everyasset TF1median6 TF5median2, identical decision; a repeated sixbar figure adds no shape or exception'}]
evidence={'selected':summary,'quarter_frequency':quarter,'all_cells':c['cells'],'audit':audit,'visual_plan':plan,'conclusion':'Frequency support reached by TF1 all3, not an edge/PnL/power result'}
(h/'census_audit.json').write_text(json.dumps(audit,indent=2));(h/'census_evidence.json').write_text(json.dumps(evidence,indent=2));print(json.dumps({'selected':summary,'audit':audit},indent=2))

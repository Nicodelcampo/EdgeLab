"""Independent scalar audit, preserving original block and declared support."""
from pathlib import Path
import json,hashlib,collections,csv,math
import pyarrow.dataset as ds
D=Path(__file__).parent;O=D/'output';m=json.load(open(D/'manifest.json'))
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
pre=json.load(open(O/'preflight.json'));assert pre['manifest_sha256']==sha(D/'manifest.json')
assert not pre['new_outcomes_opened'] and not pre['holdout_opened']
assert json.load(open(O/'manifest.json'))==m
for z in pre['source_custody']:assert z['sha256']==m['source_files_sha256'][z['path']]
r=json.load(open(O/'results.json'));plan=json.load(open(O/'EXTRA_MATCH_PLAN_PRIVATE.json'));support=json.load(open(O/'targetfree_support.json'))
assert not r['holdout_opened'] and r['old154_ledger_unchanged']
assert not support['outcomes_opened'] and support['match_plan_sha256']==sha(O/'EXTRA_MATCH_PLAN_PRIVATE.json')
for n,h in r['private_sha256'].items():assert sha(O/(n+'.json'))==h
old=json.load(open(D/'prior_SIGNALS_PRIVATE.json'))['MNQ'];oldctl=json.load(open(D/'prior_CONTROLS_PRIVATE.json'))['MNQ'];oldplan=json.load(open(D/'prior_MATCH_PLAN_PRIVATE.json'))
new=json.load(open(O/'EXTRA_SIGNALS_PRIVATE.json'));newctl=json.load(open(O/'EXTRA_CONTROLS_PRIVATE.json'));pairs=json.load(open(O/'PAIRS_PRIVATE.json'))
assert len(new)==support['n_intents'] and sum(z['separated'] for z in new)==support['n_sep']
assert len({z['id'] for z in old+new})==len(old+new)
assert all(z['day'] in m['extra_days'] for z in new) and set(m['extra_days']).isdisjoint(m['old_days'])
geom=list(plan['signals'][0]);assert [{k:z[k] for k in geom} for z in new]==plan['signals']
checks=0
for z in new+newctl:
 if z['status']!='COMPLETE':assert 'gross_ticks' not in z;continue
 assert z['entry_ns']>z['signal_ns']+250000000 and z['entry_ns']<=z['signal_ns']+30*10**9
 assert z['exit_ns']>=z['entry_ns']+1800*10**9 and z['exit_ns']<=z['cutoff_ns']
 assert z['entry_ask']>z['entry_bid']>0 and z['exit_ask']>z['exit_bid']>0
 gross=z['exit_bid']-z['entry_ask'] if z['direction']>0 else z['entry_bid']-z['exit_ask'];assert abs(gross-z['gross_ticks'])<1e-9
 for label,leg in [('base',1),('adverse',2),('severe',3)]:
  net=gross-2*leg-2*.6/.5
  assert abs(z['net_'+label+'_ticks']-net)<1e-8
  assert abs(z['net_'+label+'_usd']-net*.5)<1e-8
  assert abs(z['net_'+label+'_U']-net/z['U'])<1e-8
cm={z['id']:z for z in newctl}
for z in new:
 for k in plan['mapping'][z['id']]:
  c=cm[k];assert all(c[f]==z[f] for f in ['asset','day','contract','direction'])
  assert 1860*10**9<abs(c['signal_ns']-z['signal_ns'])<=3600*10**9 and .5<=c['U']/z['U']<=2
  checks+=1
headline=[];monthly=[]
for key,v in r['cells'].items():
 block,variant=key.split('|');rows=new if block=='EXTRA43' else old+new;ctl=newctl if block=='EXTRA43' else oldctl+newctl
 mp=plan['mapping'] if block=='EXTRA43' else dict(oldplan['mapping'],**plan['mapping']);cal=m['extra_days'] if block=='EXTRA43' else m['extra_days']+m['old_days']
 ss=[z for z in rows if variant=='BASE' or z['separated']];done=[z for z in ss if z['status']=='COMPLETE'];cmap={z['id']:z for z in ctl}
 assert v['n']==len(done) and v['eligible_sessions']==len(cal)
 assert v['states']==dict(collections.Counter(z['status'] for z in ss))
 assert math.isclose(v['mean_net_usd'],sum(z['net_base_usd'] for z in done)/len(done),abs_tol=1e-8)
 assert math.isclose(v['sum_net_usd'],sum(z['net_base_usd'] for z in done),abs_tol=1e-7)
 assert math.isclose(v['sum_net_without_best5_usd'],sum(sorted([z['net_base_usd'] for z in done],reverse=True)[5:]),abs_tol=1e-7)
 pi={z['id']:z for z in pairs[key]};alph=[]
 for z in done:
  cs=[cmap[k] for k in mp[z['id']] if cmap[k]['status']=='COMPLETE']
  if len(cs)>=3:
   alpha=z['net_base_U']-sum(c['net_base_U'] for c in cs)/len(cs);assert abs(alpha-pi[z['id']]['matched_alpha_U'])<1e-9;alph.append(alpha)
 assert len(alph)==v['matched_signals'] and math.isclose(sum(alph)/len(alph),v['mean_matched_alpha_U'],abs_tol=1e-9)
 assert math.isclose(sum(z['sum_net_usd'] for z in v['by_month'].values()),v['sum_net_usd'],abs_tol=1e-7)
 assert sum(z['n'] for z in v['by_month'].values())==v['n']
 for month,z in v['by_month'].items():monthly.append(dict(block=block,variant=variant,month=month,**z))
 headline.append(dict(block=block,variant=variant,n=v['n'],sessions=v['eligible_sessions'],mean_net_usd=v['mean_net_usd'],sum_net_usd=v['sum_net_usd'],trades_session=v['mean_trades_per_session'],mean_adverse_usd=v['mean_adverse_usd'],mean_severe_usd=v['mean_severe_usd'],mean_net_U=v['mean_net_U'],matched_alpha_U=v['mean_matched_alpha_U'],matched_fraction=v['matched_fraction'],g1=v['g1_diagnostic_pass'],screen=v['screen_pass'],net_CI95=v['inference']['net_U']['percentile95'],alpha_CI95=v['inference']['matched_alpha_U']['percentile95'],studentized_net=v['inference']['net_U']['studentized_bonf20'],studentized_alpha=v['inference']['matched_alpha_U']['studentized_bonf20']))
prior=json.load(open(D/'prior_results.json'))['cells']
for variant in ['BASE','SEP']:
 a=prior['MNQ|'+variant];b=r['cells']['EXTRA43|'+variant];c=r['cells']['COMBINED197|'+variant]
 assert c['n']==a['n']+b['n'] and abs(c['sum_net_usd']-a['sum_net_usd']-b['sum_net_usd'])<1e-6
 headline.append(dict(block='ORIGINAL154',variant=variant,n=a['n'],sessions=154,mean_net_usd=a['mean_net_usd'],trades_session=a['mean_trades_per_session']))
rawchecks=[];raw=Path('/data/raw/mnq_pullback_extension_20261001/MNQ_09-25_ticks_ext.parquet');assert sha(raw)==m['source_files_sha256']['MNQ/MNQ_09-25_ticks_ext.parquet']
scan=ds.dataset(raw,format='parquet')
for z in [s for s in new if s['contract']=='MNQ 09-25' and s['status']=='COMPLETE'][:5]:
 for phase,start,end,strict in [('entry',z['signal_ns']+250000000,z['signal_ns']+30*10**9,True),('exit',z['entry_ns']+1800*10**9,z['cutoff_ns'],False)]:
  expr=(ds.field('ts_utc_ns')>start if strict else ds.field('ts_utc_ns')>=start)&(ds.field('ts_utc_ns')<=end)
  frame=scan.to_table(columns=['ts_utc_ns','bid_ticks','ask_ticks'],filter=expr).to_pandas();q=frame[(frame.bid_ticks>0)&(frame.ask_ticks>frame.bid_ticks)].iloc[0]
  assert int(q.ts_utc_ns)==z[phase+'_ns'] and float(q.bid_ticks)==z[phase+'_bid'] and float(q.ask_ticks)==z[phase+'_ask']
  rawchecks.append(dict(id_sha256=hashlib.sha256(z['id'].encode()).hexdigest(),phase=phase,passed=True))
evidence=dict(headline=headline,monthly=monthly,control_links_checked=checks,raw_quote_checks=rawchecks,raw_audit_scope='first5 COMPLETE MNQ09-25 signals,10 quotes; not exhaustive',ledger_audit=True,old154_unchanged=True,holdout_opened=False,formal_promotion=False,hashes={'manifest':sha(D/'manifest.json'),'results':sha(O/'results.json'),'preflight':sha(O/'preflight.json')},comparisons=[{'grain':'block xvariant','population':'own COMPLETE signals,original154 andextra43 disjoint;combined197 overlapsboth','unit':'USD per1contract trade','disposition':'chart','reason':'test stability beforepooling'},{'grain':'block xmonth BASE','unit':'USD/trade','disposition':'table','reason':'retain development variation withoutclaimingOOS'},{'grain':'block xvariant matchedsubset','unit':'U','disposition':'table','reason':'control alpha andsupport differentdenominator'}])
(D/'evidence.json').write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
for name,data in [('headline',headline),('monthly',monthly)]:
 keys=sorted(set().union(*(x.keys() for x in data)))
 with open(D/(name+'.csv'),'w') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(data)
print(json.dumps({'audit':'PASS','control_links':checks,'raw_quotes':len(rawchecks),'headline':headline},indent=2))

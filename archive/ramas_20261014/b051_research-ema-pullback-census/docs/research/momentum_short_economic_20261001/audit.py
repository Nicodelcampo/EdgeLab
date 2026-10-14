from pathlib import Path
import json,math,hashlib,collections,statistics
h=Path(__file__).parent;out=h/'output';m=json.loads((h/'manifest.json').read_text());pre=json.loads((out/'preflight.json').read_text())
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert pre['runner_sha256']==sha(h/'economic.py') and pre['manifest_sha256']==sha(h/'manifest.json')
assert not pre['outcomes_opened_at_preflight'] and not pre['holdout_opened'] and len(pre['custody'])==6
r=json.loads((out/'results.json').read_text());assert len(r['cells'])==6 and r['prefix_checks_passed']==36
checks=[]
for key,z in r['cells'].items():
 rr=[json.loads(s) for s in (out/(key.replace('|','_')+'_LEDGER_PRIVATE.jsonl')).read_text().splitlines()];assert len(rr)==sum(z['states'].values());assert len({s['id'] for s in rr})==len(rr)
 complete=[s for s in rr if s['status']=='COMPLETE'];assert len(complete)==z['n']
 for s in complete:
  assert s['signal_ns']+250000000<s['entry_ns']<=s['signal_ns']+30*10**9
  assert s['entry_ns']+s['hold_min']*60*10**9<=s['exit_ns']<=s['cutoff_ns']
  eb,ea,xb,xa=map(lambda k:s[k],['entry_bid','entry_ask','exit_bid','exit_ask']);gross=xb-ea if s['direction']==1 else eb-xa
  alpha=s['direction']*((xb+xa-eb-ea)/2);assert math.isclose(gross,s['gross_ticks'],abs_tol=1e-9) and math.isclose(alpha,s['alpha_ticks'],abs_tol=1e-9)
  c=m['costs'][s['asset']]
  for label,leg in [('base',1),('adverse',2),('severe',3)]:
   net=gross-2*leg-2*c['commission_side_usd']/c['tick_value_usd'];assert math.isclose(net,s['net_'+label+'_ticks'],abs_tol=1e-9) and math.isclose(net/s['U'],s['net_'+label+'_U'],abs_tol=1e-9)
  assert math.isclose(s['net_base_ticks']*c['tick_value_usd'],s['net_base_usd'],abs_tol=1e-8)
 for field,result in [('net_base_ticks','mean_net_ticks'),('net_base_U','mean_net_U'),('net_base_usd','mean_net_usd'),('alpha_U','mean_alpha_U')]:assert math.isclose(statistics.mean(s[field] for s in complete),z[result],abs_tol=1e-9)
 top=sorted((s['net_base_ticks'] for s in complete),reverse=True);assert math.isclose(sum(top[5:]),z['net_ticks_without_best5_trades'],abs_tol=1e-8)
 assert sum(a['n'] for a in z['by_contract'].values())==len(complete);assert math.isclose(sum(a['sum_net_ticks'] for a in z['by_contract'].values()),sum(top),abs_tol=1e-8)
 for a,b in zip(rr,rr[1:]):assert a['signal_ns']+(a['hold_min']*60+60)*10**9<b['signal_ns']
 days=collections.Counter(s['day'] for s in complete);assert set(days)<=set(m['days']);assert len(days)==z['active_dates'];assert statistics.median([days[d] for d in m['days']])==z['median_trades_per_date']
 checks.append({'key':key,'n':len(complete),'ledger_sha256':sha(out/(key.replace('|','_')+'_LEDGER_PRIVATE.jsonl')),'independent_arithmetic_and_crossfoot':True,'recorded_latency_and_reserve':True})
report={'checks':checks,'preflight_exact_hashes':True,'prefix_checks':36,'not_independent_raw_quote_replay':True,'quote_age_absolute_clock_fills_NOT_certified':True,'holdout_opened':False}
(h/'audit.json').write_text(json.dumps(report,indent=2));print('Audit PASS: 6cells, arithmetic, costs, identities, counts, recorded latency/reserve; not independent rawquote availability certification')
for key,z in r['cells'].items():print(key,'n',z['n'],'perday',z['median_trades_per_date'],'meanU',round(z['mean_net_U'],4),'USD',round(z['mean_net_usd'],2),'G1',z['g1_pass'],'screen',z['screen_pass'],'LB12',round(z['inference']['net_base_U']['lower_one_sided_bonf12'],4),'contracts',[(k,v['n'],round(v['mean_net_U'],4)) for k,v in z['by_contract'].items()])

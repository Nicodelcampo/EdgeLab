"""Independent ledger arithmetic/support check, not full raw replay certification."""
from pathlib import Path
import collections, csv, hashlib, json, math
import numpy as np
import pandas as pd
import pyarrow.dataset as ds
here=Path(__file__).parent;out=here/'output';m=json.load(open(here/'manifest.json'))
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
pre=json.load(open(out/'preflight.json'))
assert pre['manifest_sha256']==sha(here/'manifest.json') and not pre['outcomes_accessed'] and not pre['holdout_opened']
for rel,h in m['code_sha256'].items():assert sha(here/rel)==h
assert json.load(open(out/'manifest.json'))==m
import past_price_producer as p
for f in pre['custody']:assert f['sha256']==p.EXPECTED[f['path']]
result=json.load(open(out/'results.json'));plan=json.load(open(out/'MATCH_PLAN_PRIVATE.json'))
support=json.load(open(out/'targetfree_support.json'));assert support['match_plan_sha256']==sha(out/'MATCH_PLAN_PRIVATE.json') and not support['outcomes_accessed']
sig=json.load(open(out/'SIGNALS_PRIVATE.json'));ctrl=json.load(open(out/'CONTROLS_PRIVATE.json'));pairs=json.load(open(out/'PAIRED_PRIVATE.json'))
for name,h in result['private_ledgers_sha256'].items():assert sha(out/(name+'.json'))==h
expected=[json.loads(z) for z in (here/'expected_PRIVATE.jsonl').read_text().splitlines() if json.loads(z)['tf']==1]
fields=list(expected[0]);headline=[];months=[];checks=0
for asset in m['assets']:
    ss=sig[asset];cc=ctrl[asset]
    assert len({s['id'] for s in ss})==len(ss)==m['expected_intents'][asset]
    assert sorted([{k:s[k] for k in fields} for s in ss],key=lambda s:s['id'])==sorted([s for s in expected if s['asset']==asset],key=lambda s:s['id'])
    assert [{k:s[k] for k in fields} for s in ss]==plan['signals'][asset]
    cmap={s['id']:s for s in cc};pmap={s['id']:s for s in plan['controls'][asset]}
    for s in ss:
        assert s['day'] in m['days_by_asset'][asset] and s['day']<'20260701' and s['U']>0
        for k in plan['mapping'][s['id']]:
            c=cmap[k];original=pmap[k]
            assert all(c[f]==original[f] for f in original)
            assert c['asset']==asset and c['day']==s['day'] and c['contract']==s['contract'] and c['direction']==s['direction']
            assert 1860*10**9<abs(s['signal_ns']-c['signal_ns'])<=3600*10**9 and .5<=c['U']/s['U']<=2
            checks+=1
    for z in ss+cc:
        if z['status']!='COMPLETE':
            assert 'gross_ticks' not in z;continue
        assert z['entry_ns']>z['signal_ns']+250000000 and z['entry_ns']<=z['signal_ns']+30*10**9
        assert z['exit_ns']>=z['entry_ns']+1800*10**9 and z['exit_ns']<=z['cutoff_ns']
        assert z['entry_ask']>z['entry_bid']>0 and z['exit_ask']>z['exit_bid']>0
        gross=z['exit_bid']-z['entry_ask'] if z['direction']>0 else z['entry_bid']-z['exit_ask']
        assert abs(gross-z['gross_ticks'])<1e-9
        cost=m['costs'][asset]
        for label,leg in [('base',1),('adverse',2),('severe',3)]:
            # Independent scalar costs, NOT imported native cost helper.
            net=gross-2*leg-2*cost['commission_side_usd']/cost['tick_value_usd']
            assert abs(net-z['net_'+label+'_ticks'])<1e-9
            assert abs(net*cost['tick_value_usd']-z['net_'+label+'_usd'])<1e-8
            assert abs(net/z['U']-z['net_'+label+'_U'])<1e-9
    for variant in m['variants']:
        key=asset+'|'+variant;r=result['cells'][key];rows=[z for z in ss if variant=='BASE' or z['separated']]
        done=[z for z in rows if z['status']=='COMPLETE'];pi=pairs[key]
        assert r['n']==len(done) and r['states']==dict(collections.Counter(z['status'] for z in rows))
        assert r['matched_signals']==len(pi)
        matched=[]
        for z in done:
            controls=[cmap[k] for k in plan['mapping'][z['id']] if cmap[k]['status']=='COMPLETE']
            if len(controls)>=3:
                scalar=z['net_base_U']-sum(c['net_base_U'] for c in controls)/len(controls);matched.append(scalar)
                recorded=next(x for x in pi if x['id']==z['id']);assert abs(scalar-recorded['matched_alpha_U'])<1e-9
        assert len(pi)==len(matched)
        assert abs(r['mean_matched_alpha_U']-sum(matched)/len(matched))<1e-9 if matched else r['mean_matched_alpha_U'] is None
        pnl=[z['net_base_usd'] for z in done]
        assert abs(r['sum_net_usd']-sum(pnl))<1e-7 and abs(r['mean_net_usd']-sum(pnl)/len(pnl))<1e-8
        assert abs(r['sum_net_without_best5_usd']-sum(sorted(pnl,reverse=True)[5:]))<1e-7
        for field in ['net_base_U','net_base_ticks','net_adverse_usd','net_severe_usd']:
            dest={'net_base_U':'mean_net_U','net_base_ticks':'mean_net_ticks','net_adverse_usd':'mean_adverse_usd','net_severe_usd':'mean_severe_usd'}[field]
            assert abs(r[dest]-sum(z[field] for z in done)/len(done))<1e-8
        assert abs(sum(v['sum_net_usd'] for v in r['by_month'].values())-sum(pnl))<1e-7
        assert sum(v['n'] for v in r['by_month'].values())==len(done)
        for month,v in r['by_month'].items():months.append(dict(asset=asset,variant=variant,month=month,**v))
        headline.append(dict(asset=asset,variant=variant,n=r['n'],sessions=r['eligible_sessions'],
                mean_net_usd=r['mean_net_usd'],mean_adverse_usd=r['mean_adverse_usd'],
                trades_session=r['mean_trades_per_session'],mean_matched_alpha_U=r['mean_matched_alpha_U'],
                match_fraction=r['matched_fraction'],g1=r['g1_diagnostic_pass'],screen=r['screen_pass']))
# Independent raw quote lookup for first five RTY signals on one real day.
raw=Path('/data/raw/no_l2_campaign_20260930/RTY_12-25_ticks_ext.parquet')
raw_checks=[]
if raw.exists():
    assert sha(raw)==p.EXPECTED['RTY/RTY_12-25_ticks_ext.parquet']
    chosen=[z for z in sig['RTY'] if z['day']=='20251007' and z['status']=='COMPLETE'][:5]
    scan=ds.dataset(raw,format='parquet')
    for z in chosen:
        for phase,start,end,strict in [
            ('entry',z['signal_ns']+250000000,z['signal_ns']+30*10**9,True),
            ('exit',z['entry_ns']+1800*10**9,z['cutoff_ns'],False)]:
            condition=(ds.field('ts_utc_ns')>start if strict else ds.field('ts_utc_ns')>=start)&(ds.field('ts_utc_ns')<=end)
            table=scan.to_table(columns=['ts_utc_ns','bid_ticks','ask_ticks'],filter=condition).to_pandas()
            good=table[(table.bid_ticks>0)&(table.ask_ticks>table.bid_ticks)].iloc[0]
            assert int(good.ts_utc_ns)==z[phase+'_ns']
            assert float(good.bid_ticks)==z[phase+'_bid'] and float(good.ask_ticks)==z[phase+'_ask']
            raw_checks.append(dict(signal_id_sha256=hashlib.sha256(z['id'].encode()).hexdigest(),phase=phase,passed=True))
evidence=dict(headline=headline,monthly=months,control_matching_checks=checks,
    raw_quote_checks=raw_checks,raw_check_scope='first5 RTY signals on20251007, not exhaustive raw audit',
    hashes=dict(results=sha(out/'results.json'),preflight=sha(out/'preflight.json'),manifest=sha(here/'manifest.json')),
    custody_pass=True,ledger_arithmetic_pass=True,holdout_opened=False,formal_promotion=False,
    comparisons=[
        dict(grain='asset x variant',population='complete own-asset signals',unit='USD per1contract trade',finding='net profitability after assumed costs',disposition='chart',reason='primary economic comparison'),
        dict(grain='asset x month BASE',population='complete signals and own eligible dates',unit='USD/trade',disposition='table',reason='retain calendar variation, not extra pooled evidence'),
        dict(grain='asset x variant',population='matched support only',unit='U difference',disposition='table',reason='different denominator from all-trade net, support reported explicitly')])
(here/'evidence.json').write_text(json.dumps(evidence,indent=2,allow_nan=False))
for name,rows in [('headline',headline),('monthly',months)]:
    with open(here/(name+'.csv'),'w') as fp:
        w=csv.DictWriter(fp,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps(dict(headline=headline,control_checks=checks,raw_checks=len(raw_checks)),indent=2))
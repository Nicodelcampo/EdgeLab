"""MNQ43 backward extension; same strategy, old154 block remains immutable."""
from pathlib import Path, PureWindowsPath
import argparse, copy, json, time
import numpy as np
import pyarrow.parquet as pq
import past_price_producer as p
from pullback import detect
from run_economic import candidates, match_controls, add_execution_fields, net_fields, canonical
from economic import replay
from extension_stats import evaluate
from edgelab.research.holdout_guard import check_holdout
NS=10**9

def merge_population(extra,old,extra_days,old_days):
    assert not (set(extra_days)&set(old_days)), 'OVERLAPPING_CALENDARS'
    assert all(s['day'] in extra_days for s in extra) and all(s['day'] in old_days for s in old)
    rows=sorted(extra+old,key=lambda s:s['signal_ns'])
    assert len({s['id'] for s in rows})==len(rows), 'DUPLICATE_SIGNAL'
    return rows,sorted(extra_days+old_days)

def run(root,out):
    started=time.monotonic();here=Path(__file__).parent;m=json.load(open(here/'manifest.json'));out.mkdir(parents=True,exist_ok=True)
    for name,h in m['code_sha256'].items():assert p.sha(here/name)==h,('CODE_CUSTODY',name)
    for name,h in m['prior_artifact_sha256'].items():assert p.sha(here/name)==h,('PRIOR_CUSTODY',name)
    old=json.load(open(here/'prior_SIGNALS_PRIVATE.json'))['MNQ']
    oldctl=json.load(open(here/'prior_CONTROLS_PRIVATE.json'))['MNQ']
    oldplan=json.load(open(here/'prior_MATCH_PLAN_PRIVATE.json'))
    assert len(old)==878 and all(s['status']=='COMPLETE' for s in old)
    assert sum(s['separated'] for s in old)==791
    before=canonical(old);assert before==m['prior_MNQ_signal_list_sha256']
    old_days=m['old_days'];days=m['extra_days']
    assert len(days)==43 and len(old_days)==154 and not set(days)&set(old_days)
    assert max(days)<min(old_days) and max(old_days)<'20260701'
    check_holdout('2025-08-04T00:00:00Z','2025-10-06T23:59:59Z',purpose='development',caller='MNQ_PULLBACK_EXTENSION',log_path=str(out/'guard.log'))
    check_holdout('2025-08-04T00:00:00Z','2026-06-30T23:59:59Z',purpose='development',caller='MNQ_PULLBACK_COMBINED',log_path=str(out/'guard.log'))
    sessions=[s for s in p.CATALOGS['MNQ']['sessions'] if s['trade_date'] in days]
    assert len(sessions)==43
    files=[];custody=[]
    for name in sorted({PureWindowsPath(s['path']).name for s in sessions}):
        rel='MNQ/'+name;file=root/rel
        assert p.sha(file)==m['source_files_sha256'][rel]
        n=pq.ParquetFile(file).metadata.num_rows
        if name=='MNQ_09-25_ticks_ext.parquet':assert n==m['new_source_rows']
        custody.append(dict(path=rel,sha256=p.sha(file),rows=n))
        files.append((file,[s for s in sessions if PureWindowsPath(s['path']).name==name]))
    p.dump(out/'manifest.json',m)
    p.dump(out/'preflight.json',dict(manifest_sha256=p.sha(here/'manifest.json'),code_sha256=m['code_sha256'],
        source_custody=custody,prior_artifact_sha256=m['prior_artifact_sha256'],prior_signals_match=True,
        source_hash_recompression_distinction=m['source_recompression'],new_outcomes_opened=False,holdout_opened=False))
    signals=[];controls=[];mapping={};plans=[];profiles=[];prefix=[]
    for file,ss in files:
        p.STEP=60*NS;b,prof,lo,hi=p.aggregate_profile(file,ss)
        assert hi<1759795200000000000 # 2025-10-07T00:00 UTC; CME endOct6 earlier
        dates={s['trade_date'] for s in ss};contract=ss[0]['contract']
        assert all(s['contract']==contract for s in ss)
        _,rr=detect(b,'MNQ',contract,dates,1)
        pool=candidates(b,'MNQ',contract,dates);mp,cc=match_controls(rr,pool)
        positions=[i for i in range(600,len(b)) if b.date.iloc[i] in dates and b.minute.iloc[i]==720]
        for i in positions[:3]:
            short=p.indicators(b.iloc[:i+1][['bucket','o','h','l','c','n']].copy())
            _,partial=detect(short,'MNQ',contract,dates,1)
            assert partial==[s for s in rr if s['signal_ns']<=int(b.close_ns.iloc[i])]
            assert candidates(short,'MNQ',contract,dates)==[c for c in pool if c['signal_ns']<=int(b.close_ns.iloc[i])]
            prefix.append(dict(file=file.name,cut_ns=int(b.close_ns.iloc[i]),passed=True))
        signals.extend(rr);controls.extend(cc);mapping.update(mp);plans.append((file,rr,cc))
        profiles.append(dict(file=file.name,**prof))
        print('targetfree_extra',file.name,len(rr),len(cc),flush=True)
    assert all(s['day'] in days for s in signals)
    frozen=dict(signals=signals,controls=controls,mapping=mapping)
    p.dump(out/'EXTRA_MATCH_PLAN_PRIVATE.json',frozen)
    p.dump(out/'targetfree_support.json',dict(n_intents=len(signals),n_sep=sum(s['separated'] for s in signals),
        n_sessions=43,n_controls=len(controls),at_least3_controls=sum(len(mapping[s['id']])>=3 for s in signals),
        prefix_checks=prefix,match_plan_sha256=p.sha(out/'EXTRA_MATCH_PLAN_PRIVATE.json'),
        outcomes_opened=False,frequency_was_NOT_used_to_retune=True))
    for file,rr,cc in plans:
        rows=rr+cc;add_execution_fields(rows)
        stats=replay(rows,p.scan(file,['ts_utc_ns','bid_ticks','ask_ticks'],min(s['signal_ns'] for s in rows),max(s['cutoff_ns'] for s in rows)+1))
        net_fields(rows,m);print('extra_replay_done',file.name,len(rr),flush=True)
    assert canonical(old)==before
    combined,all_days=merge_population(signals,old,days,old_days);assert len(all_days)==197
    combined_ctl=controls+oldctl
    assert len({c['id'] for c in combined_ctl})==len(combined_ctl)
    combined_map=dict(oldplan['mapping'],**mapping)
    results={};pairs={}
    for bi,(block,rows,ctl,mp,cal) in enumerate([
        ('EXTRA43',signals,controls,mapping,days),
        ('COMBINED197',combined,combined_ctl,combined_map,all_days)]):
        for vi,variant in enumerate(['BASE','SEP']):
            subset=[s for s in rows if variant=='BASE' or s['separated']]
            key=block+'|'+variant
            result,paired=evaluate(subset,ctl,mp,cal,m,m['seed']+bi*100+vi*10)
            results[key]=result;pairs[key]=paired
            print('statistics_done',key,result['n'],result.get('mean_net_usd'),flush=True)
    p.dump(out/'EXTRA_SIGNALS_PRIVATE.json',signals);p.dump(out/'EXTRA_CONTROLS_PRIVATE.json',controls);p.dump(out/'PAIRS_PRIVATE.json',pairs)
    p.dump(out/'results.json',dict(cells=results,profiles=profiles,extra_calendar_count=43,combined_calendar_count=197,
        old154_reused_NOT_replayed=True,old154_ledger_unchanged=canonical(old)==before,prior_source_result_sha256=m['prior_artifact_sha256']['prior_results.json'],
        holdout_opened=False,development_NOT_blind=True,formal_promotion='NOT_AUTHORIZED',
        inference_family=20,partial_budget_scenario=142,elapsed_s=time.monotonic()-started,
        private_sha256={n:p.sha(out/(n+'.json')) for n in ['EXTRA_MATCH_PLAN_PRIVATE','EXTRA_SIGNALS_PRIVATE','EXTRA_CONTROLS_PRIVATE','PAIRS_PRIVATE']}))
    print('DONE MNQ43 extension and197 combined; no holdout',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    z=parser.parse_args();run(z.root,z.out)
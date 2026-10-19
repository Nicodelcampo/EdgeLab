"""Development EMA pullback test. Detector unchanged; matched controls frozen."""
from pathlib import Path, PureWindowsPath
import argparse, collections, hashlib, json, sys, time
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import past_price_producer as p
from pullback import detect
from economic import replay, costs
from edgelab.stats import cluster_estimand as ce
from edgelab.research.holdout_guard import check_holdout
NS = 10**9

def canonical(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def candidates(b, asset, contract, days):
    """Only completed-bar clock/trend and strictly prior TR, no endpoint."""
    ans=[]
    for i in range(600,len(b)):
        z=b.iloc[i];prev=b.iloc[i-1]
        if z.date not in days or not 600<=z.minute<=884 or z.bucket-prev.bucket!=1 or not np.isfinite(z.mom_atr_prev) or z.mom_atr_prev<=0:
            continue
        side=1 if prev.e20>prev.e50 and prev.c>prev.e200 else -1 if prev.e20<prev.e50 and prev.c<prev.e200 else 0
        if not side:continue
        ns=int(z.close_ns)
        ans.append(dict(id=f"CTRL|{asset}|{contract}|{z.date}|{ns}",asset=asset,contract=contract,day=str(z.date),tf=1,signal_ns=ns,direction=side,U=float(z.mom_atr_prev)))
    return ans

def match_controls(signals, pool):
    """Same-session ±60min, own ±31min excluded, same direction, U ratio .5–2."""
    groups=collections.defaultdict(list)
    for x in pool:groups[(x['asset'],x['contract'],x['day'],x['direction'])].append(x)
    signal_times={s['signal_ns'] for s in signals};selected={}
    mapping={}
    for s in signals:
        choices=[c for c in groups[(s['asset'],s['contract'],s['day'],s['direction'])]
                 if 1860*NS<abs(c['signal_ns']-s['signal_ns'])<=3600*NS
                 and .5<=c['U']/s['U']<=2 and c['signal_ns'] not in signal_times]
        # Deterministic pseudorandom rank, no quote or return fields.
        choices.sort(key=lambda c:hashlib.sha256((s['id']+'|'+c['id']+'|20261001').encode()).hexdigest())
        chosen=choices[:5]
        mapping[s['id']]=[c['id'] for c in chosen]
        for c in chosen:selected[c['id']]=dict(c)
    return mapping, list(selected.values())

def add_execution_fields(rows):
    for s in rows:
        s.update(status='WAITING',hold_min=30,cutoff_ns=int(pd.Timestamp(s['day']+' 16:00',tz='America/New_York').tz_convert('UTC').value))

def net_fields(rows,m):
    for s in rows:
        if s['status']!='COMPLETE':continue
        for name,leg in [('base',1),('adverse',2),('severe',3)]:
            ticks=s['gross_ticks']-costs(m,s['asset'],leg)
            s['net_'+name+'_ticks']=ticks
            s['net_'+name+'_U']=ticks/s['U']
            s['net_'+name+'_usd']=ticks*m['costs'][s['asset']]['tick_value_usd']

def inference(rows, days, field, seed, m):
    byday={d:[s[field] for s in rows if s['day']==d and field in s] for d in days}
    if not any(byday.values()):return {'status':'NO_SUPPORT'}
    cl=ce.aggregate_sessions(days,byday)
    bs=ce.resample_stationary_session_clusters(cl,n_replicates=m['bootstrap_replicates'],seed=seed)
    assert bs.invalid_zero_denominator==0
    qq=np.quantile(bs.replicates,[.025,.975,.05/12,.05/134])
    result=dict(observed=bs.observed,percentile95=list(map(float,qq[:2])),
                diagnostic_lower_bonf12=float(qq[2]),diagnostic_lower_partial_budget134=float(qq[3]),
                n_sessions=bs.n_sessions,n_trades=bs.n_trades,block_length=bs.block_length,
                replicates=m['bootstrap_replicates'],method=bs.method,
                percentile_NOT_G2=True,partial_history_NOT_project_FWER=True)
    try:
        ci=ce.studentized_stationary_interval(cl,n_replicates=m['studentized_replicates'],seed=seed+100,confidence=1-2*.05/12)
        result['studentized_bonf12']={k:getattr(ci,k) for k in ['observed','lower','upper','standard_error','n_sessions','n_trades','valid_replicates','requested_replicates','block_length','hac_lag']}
    except ce.ClusterEstimandError as e:result['studentized_bonf12']={'status':'BLOCKED','reason':str(e)}
    return result

def evaluate(rows, controls, mapping, days, m, seed):
    done=[s for s in rows if s['status']=='COMPLETE'];states=dict(collections.Counter(s['status'] for s in rows))
    ctl={c['id']:c for c in controls};paired=[]
    for s in done:
        choices=[ctl[k] for k in mapping[s['id']] if ctl[k]['status']=='COMPLETE']
        if len(choices)>=3:
            # Control-specific U retained. One matched difference per signal, NOT 5 trades.
            z=dict(s)
            z['matched_alpha_U']=s['net_base_U']-float(np.mean([c['net_base_U'] for c in choices]))
            z['matched_control_net_U']=float(np.mean([c['net_base_U'] for c in choices]))
            z['controls_complete']=len(choices);paired.append(z)
    dd=[sum(s['day']==d for s in done) for d in days]
    # Reservations are not fills. Check actual fills/exits against subsequent signals.
    ordered=sorted(rows,key=lambda x:x['signal_ns'])
    overlap=[(a['id'],b['id']) for a,b in zip(ordered,ordered[1:])
             if a['status']=='COMPLETE' and a['exit_ns']>=b['signal_ns']]
    if not done:return dict(n=0,states=states,screen_pass=False),[]
    value=lambda f:float(np.mean([s[f] for s in done]))
    total=sum(s['net_base_usd'] for s in done)
    top=sorted(done,key=lambda x:x['net_base_usd'],reverse=True)
    contracts={}
    for c in sorted({s['contract'] for s in rows}):
        ss=[s for s in done if s['contract']==c];su=sum(s['net_base_usd'] for s in ss)
        contracts[c]=dict(n=len(ss),sum_net_usd=su,mean_net_usd=su/len(ss) if ss else None,share_total_net=su/total if total else None)
    g1=dict(n_at_least100=len(done)>=100,mean_net_positive=total>0,
            positive_without_best5_trades=sum(s['net_base_usd'] for s in top[5:])>0,
            contract_concentration_le80pct=total>0 and max(v['share_total_net'] for v in contracts.values())<=.8)
    bymonth={}
    for month in sorted({d[:6] for d in days}):
        ss=[s for s in done if s['day'][:6]==month]
        bymonth[month]=dict(n=len(ss),mean_net_usd=float(np.mean([s['net_base_usd'] for s in ss])) if ss else None,
                            sum_net_usd=sum(s['net_base_usd'] for s in ss),eligible_sessions=sum(d.startswith(month) for d in days))
    net=inference(done,days,'net_base_U',seed,m)
    alpha=inference(paired,days,'matched_alpha_U',seed+1,m)
    support=len(paired)/len(done)
    technical=not overlap and not any(k.startswith('UNKNOWN') for k in states)
    # Unknown exits in selected controls also block the matched screen.
    unknown_controls=any(c['status'].startswith('UNKNOWN') for c in controls)
    screen=technical and not unknown_controls and support>=.8 and all(g1.values()) and all(
        z.get('diagnostic_lower_bonf12',-float('inf'))>0 for z in [net,alpha])
    chronological=sorted(done,key=lambda s:s['signal_ns']);equity=np.cumsum([s['net_base_usd'] for s in chronological])
    peaks=np.maximum.accumulate(np.r_[0,equity]);drawdown=float(np.max(peaks[1:]-equity))
    return dict(n=len(done),intents=len(rows),states=states,eligible_sessions=len(days),active_sessions=sum(n>0 for n in dd),
        mean_trades_per_session=len(done)/len(days),median_trades_per_session=float(np.median(dd)),
        mean_net_usd=value('net_base_usd'),mean_net_ticks=value('net_base_ticks'),mean_net_U=value('net_base_U'),
        mean_adverse_usd=value('net_adverse_usd'),mean_severe_usd=value('net_severe_usd'),sum_net_usd=total,
        p5_p25_p50_p75_p95_usd=list(map(float,np.quantile([s['net_base_usd'] for s in done],[.05,.25,.5,.75,.95]))),
        win_fraction=float(np.mean([s['net_base_usd']>0 for s in done])),max_drawdown_sequential_usd=drawdown,
        sum_net_without_best5_usd=sum(s['net_base_usd'] for s in top[5:]),
        top1_top5_top10_contribution_usd=[sum(s['net_base_usd'] for s in top[:k]) for k in [1,5,10]],
        by_contract=contracts,by_month=bymonth,g1=g1,g1_diagnostic_pass=all(g1.values()),
        matched_signals=len(paired),matched_fraction=support,mean_matched_alpha_U=float(np.mean([s['matched_alpha_U'] for s in paired])) if paired else None,
        mean_matched_control_U=float(np.mean([s['matched_control_net_U'] for s in paired])) if paired else None,
        control_states=dict(collections.Counter(c['status'] for c in controls)),
        inference={'net_U':net,'matched_alpha_U':alpha},technical_gate=technical,
        matched_support_gate=support>=.8 and not unknown_controls,overlap_pairs=overlap,screen_pass=bool(screen),
        entry_lag_p50_p95_max_s=list(map(float,np.quantile([s['entry_lag_s'] for s in done],[.5,.95,1]))),
        exit_lag_p50_p95_max_s=list(map(float,np.quantile([s['exit_lag_s'] for s in done],[.5,.95,1]))),
        formal_G0='NOT_CERTIFIED_CLOCK_QUOTE_AGE_AND_ASOF_PUBLICATION',
        formal_G2='NOT_AUTHORIZED_FULL_SEARCH_BUDGET_PBO_DSR_WF_NEIGHBORS_INCOMPLETE',
        MAE_MFE='NOT_MEASURED_BLOCKS_COMPLETE_GATE_DIAGNOSTICS',actual_fills_certified=False),paired

def run(root,out):
    start=time.monotonic();here=Path(__file__).parent;m=json.load(open(here/'manifest.json'))
    out.mkdir(parents=True,exist_ok=True)
    for rel,h in m['code_sha256'].items():assert p.sha(here/rel)==h,('CODE_CUSTODY',rel)
    expected=[json.loads(line) for line in (here/'expected_PRIVATE.jsonl').read_text().splitlines() if json.loads(line)['tf']==1]
    assert len(expected)==2837 and p.sha(here/'expected_PRIVATE.jsonl')==m['prior_ledger_sha256']
    files=[];custody=[]
    for asset in m['assets']:
        days=m['days_by_asset'][asset]
        check_holdout('2025-10-07T00:00:00Z','2026-06-30T23:59:59Z',purpose='development',caller='EMA_PULLBACK_ECONOMIC',log_path=str(out/'guard.log'))
        ss=[s for s in p.CATALOGS[asset]['sessions'] if s['trade_date'] in days]
        assert len(ss)==len(days) and all(s['trade_date']<'20260701' for s in ss)
        for name in sorted({PureWindowsPath(s['path']).name for s in ss}):
            f=root/asset/name;rel=asset+'/'+name;h=p.sha(f);assert h==p.EXPECTED[rel]
            custody.append(dict(path=rel,sha256=h,rows=pq.ParquetFile(f).metadata.num_rows))
            files.append((asset,f,[s for s in ss if PureWindowsPath(s['path']).name==name]))
    p.dump(out/'manifest.json',m)
    p.dump(out/'preflight.json',dict(manifest_sha256=p.sha(here/'manifest.json'),code_sha256=m['code_sha256'],
                                    custody=custody,outcomes_accessed=False,holdout_opened=False))
    allsig={a:[] for a in m['assets']};allctl={a:[] for a in m['assets']};mapping={};plans=[];prefixes=[];profiles=[]
    # Two passes: ALL signal/control plans hash-persisted BEFORE any economic replay.
    for asset,f,ss in files:
        p.STEP=60*NS;b,prof,lo,hi=p.aggregate_profile(f,ss);assert hi<1782864000000000000
        days={s['trade_date'] for s in ss};contract=ss[0]['contract']
        _,signals=detect(b,asset,contract,days,1)
        ex=[s for s in expected if s['asset']==asset and s['contract']==contract]
        assert sorted(signals,key=lambda s:s['id'])==sorted(ex,key=lambda s:s['id']),('CENSUS_IDENTITY',asset,f.name)
        pool=candidates(b,asset,contract,days);mp,ctrl=match_controls(signals,pool)
        pos=[i for i in range(600,len(b)) if b.date.iloc[i] in days and b.minute.iloc[i]==720]
        for i in pos[:3]:
            short=p.indicators(b.iloc[:i+1][['bucket','o','h','l','c','n']].copy())
            _,chk=detect(short,asset,contract,days,1)
            assert chk==[s for s in signals if s['signal_ns']<=int(b.close_ns.iloc[i])]
            assert candidates(short,asset,contract,days)==[c for c in pool if c['signal_ns']<=int(b.close_ns.iloc[i])]
            prefixes.append(dict(asset=asset,file=f.name,cut_ns=int(b.close_ns.iloc[i]),passed=True))
        mapping.update(mp);allsig[asset].extend(signals);allctl[asset].extend(ctrl);plans.append((asset,f,signals,ctrl))
        profiles.append(dict(asset=asset,file=f.name,**prof))
        print('target_free_plan',asset,f.name,len(signals),len(ctrl),flush=True)
    assert sum(len(v) for v in allsig.values())==2837
    frozen=dict(signals=allsig,controls=allctl,mapping=mapping)
    p.dump(out/'MATCH_PLAN_PRIVATE.json',frozen)
    p.dump(out/'targetfree_support.json',dict(match_plan_sha256=p.sha(out/'MATCH_PLAN_PRIVATE.json'),
        signals_sha256=canonical(allsig),mapping_sha256=canonical(mapping),
        counts={a:dict(signals=len(allsig[a]),controls=len(allctl[a]),at_least3_controls=sum(len(mapping[s['id']])>=3 for s in allsig[a])) for a in m['assets']},
        prefix_checks=prefixes,outcomes_accessed=False))
    for asset,f,signals,ctrl in plans:
        rows=signals+ctrl;add_execution_fields(rows)
        stats=replay(rows,p.scan(f,['ts_utc_ns','bid_ticks','ask_ticks'],min(s['signal_ns'] for s in rows),max(s['cutoff_ns'] for s in rows)+1))
        net_fields(rows,m);print('economic_replay',asset,f.name,len(rows),dict(collections.Counter(s['status'] for s in signals)),flush=True)
    results={};paired_all={}
    for ai,asset in enumerate(m['assets']):
        for vi,variant in enumerate(['BASE','SEP']):
            rows=[s for s in allsig[asset] if variant=='BASE' or s['separated']]
            result,paired=evaluate(rows,allctl[asset],mapping,m['days_by_asset'][asset],m,m['seed']+ai*100+vi*10)
            key=asset+'|'+variant;results[key]=result;paired_all[key]=paired
            print('statistics_done',key,'n',result['n'],'meanUSD',result.get('mean_net_usd'),flush=True)
    for name,obj in [('SIGNALS_PRIVATE',allsig),('CONTROLS_PRIVATE',allctl),('PAIRED_PRIVATE',paired_all)]:
        p.dump(out/(name+'.json'),obj)
    p.dump(out/'results.json',dict(cells=results,profiles=profiles,census_parity=True,chosen_tf_min=1,
        holdout_opened=False,development_NOT_OOS=True,formal_promotion='NOT_AUTHORIZED',
        elapsed_s=time.monotonic()-start,private_ledgers_sha256={name:p.sha(out/(name+'.json')) for name in ['MATCH_PLAN_PRIVATE','SIGNALS_PRIVATE','CONTROLS_PRIVATE','PAIRED_PRIVATE']}))
    print('DONE EMA pullback economic; development only',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();run(args.root,args.out)
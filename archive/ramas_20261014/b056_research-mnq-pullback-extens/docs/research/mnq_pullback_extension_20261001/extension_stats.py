"""Frozen statistical adapter: Bonferroni20 and partial-budget142, not new detector."""
from run_economic import np, ce, collections
def inference(rows, days, field, seed, m):
    byday={d:[s[field] for s in rows if s['day']==d and field in s] for d in days}
    if not any(byday.values()):return {'status':'NO_SUPPORT'}
    cl=ce.aggregate_sessions(days,byday)
    bs=ce.resample_stationary_session_clusters(cl,n_replicates=m['bootstrap_replicates'],seed=seed)
    assert bs.invalid_zero_denominator==0
    qq=np.quantile(bs.replicates,[.025,.975,.05/20,.05/142])
    result=dict(observed=bs.observed,percentile95=list(map(float,qq[:2])),
                diagnostic_lower_bonf20=float(qq[2]),diagnostic_lower_partial_budget142=float(qq[3]),
                n_sessions=bs.n_sessions,n_trades=bs.n_trades,block_length=bs.block_length,
                replicates=m['bootstrap_replicates'],method=bs.method,
                percentile_NOT_G2=True,partial_history_NOT_project_FWER=True)
    try:
        ci=ce.studentized_stationary_interval(cl,n_replicates=m['studentized_replicates'],seed=seed+100,confidence=1-2*.05/20)
        result['studentized_bonf20']={k:getattr(ci,k) for k in ['observed','lower','upper','standard_error','n_sessions','n_trades','valid_replicates','requested_replicates','block_length','hac_lag']}
    except ce.ClusterEstimandError as e:result['studentized_bonf20']={'status':'BLOCKED','reason':str(e)}
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
        z.get('diagnostic_lower_bonf20',-float('inf'))>0 for z in [net,alpha])
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
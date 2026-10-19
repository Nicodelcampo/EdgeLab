"""EF0/EF3/EF4 + custody + Parquet/array integration. Synthetic data only, CPU backend."""
import json
from pathlib import Path
import numpy as np
import pytest
from edgelab.funnel.multiplicity import plateau_report,TrialRegistry,sidak_bonferroni,max_null_direction,candidate_statistic
from edgelab.funnel.custody import forbid_holdout,SeenLedger
from edgelab.funnel.eligibility import check_eligibility
from edgelab.funnel.splits import make_splits
from edgelab.funnel.runner import FunnelRunner
from edgelab.funnel.screen import kernel_manifest

GRID=([1,2,3],[1,2,3])
def test_plateau_vs_spike():
    flat={(a,b):10. for a in GRID[0] for b in GRID[1]}
    assert plateau_report(flat,GRID,(2,2))['status']=='PLATEAU'
    spike={**{(a,b):-5. for a in GRID[0] for b in GRID[1]},(2,2):50.}
    assert plateau_report(spike,GRID,(2,2))['status']!='PLATEAU'
    with pytest.raises(ValueError):plateau_report(flat,GRID,(9,9))

def test_trial_registry_chain_and_duplicates(tmp_path):
    r=TrialRegistry(tmp_path/'t.jsonl');r.register('c1','f',42);r.register('c2','f',10)
    assert r.total()==52 and r.verify()['valid']
    with pytest.raises(ValueError):r.register('c1','f',5)
    rows=(tmp_path/'t.jsonl').read_text().splitlines();x=json.loads(rows[0]);x['n_trials']=1
    (tmp_path/'t.jsonl').write_text(json.dumps(x)+'\n'+rows[1]+'\n');assert not r.verify()['valid']
    with pytest.raises(ValueError):sidak_bonferroni(1.2,3)
    assert sidak_bonferroni(.01,10)['bonferroni']==pytest.approx(.1)

def test_holdout_guard_and_contamination(tmp_path):
    with pytest.raises(PermissionError):forbid_holdout([20260331,20260401],20260401)
    forbid_holdout([20260331],20260401)
    days=np.repeat(np.arange(20260101,20260121),2);s=make_splits(days)
    led=SeenLedger(tmp_path/'seen.jsonl');assert led.contamination(s)['d2_clean']
    led.mark('a1',min(s.d2_dates),max(s.d2_dates));c=led.contamination(s)
    assert c['d2']==1.0 and not c['d2_clean'] and c['d0']==0.
    with pytest.raises(ValueError):led.mark('bad',2,1)

def _manifests(**kw):
    build={'build':{'timestamp_backwards':0,'duplicate_ts_sequence':0},'output':{'sha256':'x'},'source_files':[{'sha256':'y'}],'holdout_first_trade_date':20260401}
    reg={'strict_crossover':True,'monotonic_expiry':True,'signal_lag_sessions':1,'price_adjustment':'NONE_ACTUAL','calendar_trade_dates':list(range(20251001,20251001+90)),'contracts':[{'contract':'A'},{'contract':'B'}],'policy_id':'p'}
    return build,reg
def test_eligibility_blocks_unknowns_and_missing():
    b,r=_manifests();rep=check_eligibility(b,r,expected_contracts=['A','B','C'],clock_certified=None)
    assert not rep['eligible'] and 'contract_coverage' in rep['blocking'] and 'clock_certified' in rep['blocking'] and 'costs_declared' in rep['blocking']
    ok=check_eligibility(b,r,expected_contracts=['A','B'],clock_certified=True,costs_declared=True);assert ok['eligible'],ok['blocking']
    b['build']['timestamp_backwards']=3;assert 'timestamps_monotonic' in check_eligibility(b,r)['blocking']
    r['calendar_trade_dates']=[20260402];assert 'holdout_excluded' in check_eligibility(*_manifests()[:1],r)['blocking']

def test_kernel_manifest_fields():
    m=kernel_manifest('cpu');assert m['precision']=='float64' and len(m['source_sha256'])==64
    assert kernel_manifest('gpu')['precision']=='float32'

def _market(planted,seed=7,ndays=30,per=200):
    rng=np.random.default_rng(seed);n=ndays*per;td=np.repeat(np.arange(20260101,20260101+ndays),per)
    step=rng.integers(-3,4,n).astype(np.int64);sig=np.arange(5,n-30,25);d=rng.choice(np.array([-1,1],np.int8),len(sig))
    if planted:
        for k,i in enumerate(sig):step[i+1:i+16]+=d[k]*6
    base=30000+np.cumsum(step);h=(base+rng.integers(0,3,n)).astype(np.int32);l=(base-rng.integers(0,3,n)).astype(np.int32)
    return td,sig,d,h,l,(base-1).astype(np.int32),(base+1).astype(np.int32)
def _cfg():
    return [{'candidate_id':f'c{s}_{t}','family_id':'F','sl_ticks':s,'tp_ticks':t,'direction':'normal'} for s in(20,40,60) for t in(20,40,60)]

def _runner(tmp,planted,seed,**kw):
    td,sig,d,h,l,bo,ao=_market(planted,seed=seed)
    return FunnelRunner(trade_dates=td,signal_idx=sig,signal_dir=d,high=h,low=l,bid_open=bo,ask_open=ao,configs=kw.pop('configs',_cfg()),out_dir=tmp,backend='cpu',holdout_first_date=20270101,**kw)

def test_e4_detects_planted_direction_and_not_noise(tmp_path):
    reg=tmp_path/'reg.jsonl'
    r=_runner(tmp_path/'a',True,7,campaign_id='planted',trial_registry=reg)
    out=r.run_e4(n_sims=200,seed=1,min_trades=5,max_hold_bars=40)
    assert out['max_null']['p_max']<.05 and out['global_trials_registered']==9 and out['holdout_opened'] is False and out['plateau']['status']=='PLATEAU'
    assert out['verdict']=='CANDIDATE_REQUIRES_FUTURE_CONFIRMATION' and out['p_max_campaigns_adjusted']['n_campaigns']==1
    r2=_runner(tmp_path/'b',False,11,campaign_id='noise',trial_registry=reg)
    out2=r2.run_e4(n_sims=200,seed=1,min_trades=5,max_hold_bars=40)
    assert out2['max_null']['p_max']>.05 and out2['verdict']=='NOT_REJECTED_NO_DIRECTIONAL_EVIDENCE' and out2['global_trials_registered']==18
    assert out2['p_max_campaigns_adjusted']['n_campaigns']==2 and out2['p_max_campaigns_adjusted']['bonferroni']>=out2['max_null']['p_max']
    assert r2.ledger.verify()

def test_batched_null_matches_bruteforce(tmp_path):
    """The sign-matrix shortcut must equal re-screening with each sign."""
    from edgelab.funnel.isolation import stage_window,bounded_batches
    td,sig,d,h,l,bo,ao=_market(True,seed=3)
    r=_runner(tmp_path,True,3,campaign_id='x',trial_registry=tmp_path/'r.jsonl');out=r.run_e4(n_sims=30,seed=5,min_trades=5,max_hold_bars=40,flip='signal')
    # brute force with the same seed/sign construction
    import numpy as np
    sl=np.array([c['sl_ticks'] for c in r.cfg]);tp=np.array([c['tp_ticks'] for c in r.cfg]);mult=np.ones(len(sl),np.int8)
    wins={p:stage_window(r.td,r.si,ds,40) for p,ds in(('D0',r.split.d0_dates),('D1',r.split.d1_dates))};sizes=[len(w.signal_positions) for w in wins.values()]
    rng=np.random.default_rng(5);sg=rng.choice(np.array([-1,1],np.int8),(30,sum(sizes)))
    def stat(sign):
        means=[];cnt=[];off=0
        for (p,w),n in zip(wins.items(),sizes):
            s=sign[off:off+n];off+=n;bar=slice(w.bar_start,w.bar_stop);m=np.full(len(sl),np.nan);c=np.zeros(len(sl))
            for a,b,M,_ in bounded_batches(w.local_signals(r.si),(r.sd[w.signal_positions]*s).astype(np.int8),r.h[bar],r.l[bar],r.bo[bar],r.ao[bar],sl,tp,mult,max_hold_bars=40,backend='cpu'):
                f=np.isfinite(M);c[a:b]=f.sum(0);m[a:b]=np.where(f,M,0).sum(0)/np.maximum(f.sum(0),1)
            means.append(m);cnt.append(c)
        ok=(cnt[0]>=5)&(cnt[1]>=5);return np.where(ok,candidate_statistic(means[0],means[1]),-np.inf)
    obs=stat(np.ones(sum(sizes),np.int8)).max();null=np.array([stat(sg[i]).max() for i in range(30)])
    assert out['max_null']['observed_max']==pytest.approx(obs)
    assert out['max_null']['p_max']==pytest.approx((np.sum(null>=obs)+1)/31)

def test_runner_fails_closed_without_holdout_guard(tmp_path):
    td,sig,d,h,l,bo,ao=_market(False)
    with pytest.raises(ValueError):
        FunnelRunner(trade_dates=td,signal_idx=sig,signal_dir=d,high=h,low=l,bid_open=bo,ask_open=ao,configs=_cfg(),out_dir=tmp_path,backend='cpu')
    with pytest.raises(PermissionError):
        FunnelRunner(trade_dates=td,signal_idx=sig,signal_dir=d,high=h,low=l,bid_open=bo,ask_open=ao,configs=_cfg(),out_dir=tmp_path,backend='cpu',holdout_first_date=20260110)
    r=FunnelRunner(trade_dates=td,signal_idx=sig,signal_dir=d,high=h,low=l,bid_open=bo,ask_open=ao,configs=_cfg(),out_dir=tmp_path,backend='cpu',allow_unguarded=True)
    assert r.run_e1_e3(min_trades=5,max_hold_bars=40)['holdout_opened']=='UNVERIFIED'

def test_trials_counted_before_work_and_seen_marked(tmp_path):
    reg=tmp_path/'reg.jsonl';seen=tmp_path/'seen.jsonl'
    r=_runner(tmp_path/'o',False,2,campaign_id='c',trial_registry=reg,seen_ledger=seen)
    r.run_e1_e3(min_trades=5,max_hold_bars=40)
    assert TrialRegistry(reg).total()==9 and len(seen.read_text().splitlines())==2   # D0 and D1 marked
    r.run_e4(n_sims=20,seed=1,min_trades=5,max_hold_bars=40)                           # same campaign: idempotent
    assert TrialRegistry(reg).total()==9
    with pytest.raises(ValueError):
        _runner(tmp_path/'o2',False,2,campaign_id='c',trial_registry=reg,configs=_cfg()[:4]).run_e1_e3(min_trades=5,max_hold_bars=40)  # changed count rejected
    assert SeenLedger(seen).contamination(r.split)['d0']==1.0

def test_trial_registry_idempotent_lock_and_truncation(tmp_path):
    reg=TrialRegistry(tmp_path/'t.jsonl');assert reg.ensure('c','f',5) and not reg.ensure('c','f',5)
    with pytest.raises(ValueError):reg.ensure('c','f',6)
    reg.ensure('c','g',3);h=reg.head();reg.ensure('d','f',2);assert reg.verify(h)['valid'] is False and reg.verify()['valid']
    lines=(tmp_path/'t.jsonl').read_text().splitlines();(tmp_path/'t.jsonl').write_text('\n'.join(lines[:2])+'\n')
    assert reg.verify(expected_head=json.loads(lines[2])['hash'])['valid'] is False
    (tmp_path/'t.jsonl').write_text('{"campaign_id":"x"}\n');assert reg.verify()['valid'] is False

def test_plateau_counts_failed_neighbour_as_non_positive():
    nets={(a,b):10. for a in GRID[0] for b in GRID[1]}
    for k in((1,1),(1,2),(1,3),(2,1),(3,1),(3,2)):nets[k]=float('-inf')
    assert plateau_report(nets,GRID,(2,2))['status']!='PLATEAU'

def test_eligibility_tolerates_null_fields():
    b,r=_manifests();r['price_adjustment']=None;r['signal_lag_sessions']=None;r['calendar_trade_dates']=[20251001]*200
    rep=check_eligibility(b,r);assert not rep['eligible'] and {'no_price_adjustment','roll_causal_lag','session_count'}<=set(rep['blocking'])
    assert check_eligibility({},{})['eligible'] is False

def test_empty_d2_is_not_clean(tmp_path):
    s=make_splits(np.repeat(np.arange(20260101,20260121),2));class_empty=type('S',(),{'d0_dates':s.d0_dates,'d1_dates':s.d1_dates,'d2_dates':()})
    assert SeenLedger(tmp_path/'x.jsonl').contamination(class_empty)['d2_clean'] is False

def test_arrays_entrypoint_end_to_end(tmp_path):
    """Portable entrypoint reads .npy arrays + registry JSON and writes Parquet outputs (no D2); guard + counter mandatory."""
    import subprocess,sys
    td,sig,d,h,l,bo,ao=_market(True);a=tmp_path/'arr';a.mkdir()
    for n,v in dict(trade_date=td,signal_bar_idx=sig,signal_dir=d,high_ticks=h,low_ticks=l,bid_open_ticks=bo,ask_open_ticks=ao).items():np.save(a/f'{n}.npy',v)
    reg=tmp_path/'reg.json';reg.write_text(json.dumps({'family_id':'F','candidates':[{k:v for k,v in c.items() if k!='family_id'} for c in _cfg()]}))
    root=Path(__file__).resolve().parents[1];base=[sys.executable,str(root/'tools/run_funnel_arrays.py'),'--arrays',str(a),'--registry',str(reg),'--out',str(tmp_path/'o'),'--backend','cpu']
    bad=subprocess.run(base,capture_output=True,text=True,cwd=root);assert bad.returncode!=0   # guard/counter are mandatory
    p=subprocess.run(base+['--holdout-first-date','20270101','--campaign-id','t','--trial-registry',str(tmp_path/'tr.jsonl'),'--min-trades','5','--e4','--nsims','20'],capture_output=True,text=True,cwd=root)
    assert p.returncode==0,p.stderr[-800:]
    import pyarrow.parquet as pq
    t=pq.read_table(tmp_path/'o'/'trials.parquet');assert t.num_rows==9
    s=json.loads((tmp_path/'o'/'summary.json').read_text());assert s['holdout_opened'] is False and s['kernels']['D0']['kernel_id']=='edgelab_funnel_screen' and s['trial_registry']['total_trials']==9
    assert json.loads((tmp_path/'o'/'multiplicity.json').read_text())['registry']['valid']

def test_registry_inverse_alias_runs(tmp_path):
    """The frozen MGC registry labels the opposite direction 'inverse'; it must run as a -1 multiplier."""
    cfg=[{'candidate_id':'n','family_id':'F','sl_ticks':40,'tp_ticks':40,'direction':'normal'},{'candidate_id':'i','family_id':'F','sl_ticks':40,'tp_ticks':40,'direction':'inverse'}]
    r=_runner(tmp_path,True,7,configs=cfg)
    r.run_e1_e3(min_trades=5,max_hold_bars=40);rows={x['candidate_id']:x for x in __import__('pyarrow.parquet',fromlist=['x']).read_table(tmp_path/'trials.parquet').to_pylist()}
    assert rows['n']['d0_mean']>0>rows['i']['d0_mean']

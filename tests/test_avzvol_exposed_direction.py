"""Invented labels and binary exports only; never market prices or direction validation."""
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
import subprocess,sys
import pandas as pd
import numpy as np
import pytest
spec=spec_from_file_location('direction',Path(__file__).resolve().parents[1]/'tools/review_avzvol_exposed_direction.py');m=module_from_spec(spec);spec.loader.exec_module(m)
def frame():
    rows=[]
    for c in m.CONTRACTS:
        for s in [1,2]:
            rows.extend([(c,s,'4_250_20','real',1.,1,1,0,1),(c,s,'4_250_20','pseudo',0.,0,1,0,1)])
    return pd.DataFrame(rows,columns=m.KEYS+['kind','continuation','o2','te','clock','trend'])
def test_binary_gap_equal_sessions_and_contracts_independent():
    r,g,common=m.summarize(frame(),'continuation')
    assert common==['4_250_20'] and r['headline']['gap_pp']==100
    assert r['headline']['real_rate_percent']==100 and r['headline']['pseudo_rate_percent']==0
    assert r['headline']['independent_max_error']==0
    assert len(r['cells'])==36

def test_unknown_not_zero_and_support_not_invented():
    d=frame();d.loc[(d.contract==m.CONTRACTS[-1])&d.kind.eq('pseudo'),'continuation']=np.nan
    r,g,common=m.summarize(d,'continuation');assert common==[] and r['headline']['gap_pp'] is None
    assert r['cells'][0]['contracts_supported']==5

def test_duplicates_retained_in_rate():
    d=frame();extra=d.iloc[[1]].copy();extra['continuation']=1.
    d=pd.concat([d,extra]);g=m.aggregate(d,'continuation')
    assert g.loc[(m.CONTRACTS[0],1,'4_250_20'),'pseudo']==.5

def test_context_overlap_not_filled_from_other_strata():
    d=frame();d.loc[d.kind.eq('pseudo'),'trend']=-1
    r,g,common=m.summarize(d,'continuation',m.KEYS+['clock','trend'])
    assert not common and len(g)==0

def test_unresolved_adversarial_bounds_include_missing_after_exit():
    d=frame();extra=d[d.kind.eq('pseudo')].copy();extra['o2']=-1;extra['continuation']=np.nan
    d=pd.concat([d,extra]);r,g,c=m.summarize(d,'continuation');b=m.censor_bounds(d,g,c)
    assert b['lower_gap_pp']==50 and b['upper_gap_pp']==100
    assert m.independent_bounds(d,g,c)==(50.,100.)

def test_plan_does_not_treat_observed_exit_as_prediction_or_profit():
    p=m.plan();assert p['no_economic_outcomes'] and p['no_new_price_outcomes']
    assert 'NOT a directional zone signal' in p['secondary'] and 'not a trading fill probability' in p['primary']

@pytest.mark.parametrize('optin',[False,True])
def test_missing_optin_or_code_pin_stops_before_payload(tmp_path,optin):
    source=tmp_path/'source';source.write_text('invented')
    cmd=[sys.executable,'-O',m.__file__,'--inventory',str(tmp_path/'missing'),'--historical-stage-source',str(source),'--out-dir',str(tmp_path/'out')]
    if optin:cmd.append('--allow-exposed-direction-review')
    r=subprocess.run(cmd,capture_output=True,text=True);assert r.returncode==2 and not (tmp_path/'out').exists()

def test_no_exit_not_silently_counted_as_continuation_failure():
    d=frame();extra=d.iloc[[0]].copy();extra['te']=-1;extra['o2']=-1;extra['continuation']=np.nan
    d=pd.concat([d,extra]);r,g,c=m.summarize(d,'continuation');assert r['headline']['gap_pp']==100
    assert m.censor_bounds(d,g,c)['lower_gap_pp']==100

def test_overlap_baseline_and_stratified_agree_for_identical_strata():
    d=frame();r=m.same_overlap_base(d,'continuation',m.KEYS+['clock','trend'])
    ctx,_,_=m.summarize(d,'continuation',m.KEYS+['clock','trend'])
    assert r['headline']==ctx['headline']

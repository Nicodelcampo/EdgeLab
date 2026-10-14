"""Invented covariates/anchor labels; no market outcomes or negative census approval."""
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
import subprocess,sys
import pandas as pd
import numpy as np
import pytest
spec=spec_from_file_location('control',Path(__file__).resolve().parents[1]/'tools/review_avzvol_control_comparability.py');m=module_from_spec(spec);spec.loader.exec_module(m)
def frame():
    rows=[]
    for c in m.CONTRACTS:
        for s in [1,2]:
            for kind,values in [('real',[1.,3.]),('pseudo',[0.,2.])]:
                for i,v in enumerate(values):rows.append(dict(contract=c,session=s,cell='4_250_20',clock=0,trend=1,kind=kind,t0=10+i,**{f:v for f in m.FEATURES}))
    return pd.DataFrame(rows)
def test_hierarchical_weights_normalize_and_smd():
    f,counts,shared,common=m.support_weights(frame());assert common==['4_250_20']
    assert all(v==pytest.approx(1.) for v in f.groupby('kind').weight.sum())
    assert all(r['weighted_smd']==pytest.approx(1.) for r in m.balance(f))
def test_zero_variance_not_infinite_or_fake_balanced():
    assert m.smd(1,0,1,0)==0 and m.smd(1,0,0,0) is None

def test_missing_covariate_not_imputed_and_accounting_retained():
    d=frame();d.loc[0,'occ']=np.nan
    f,c,s,common=m.support_weights(d);assert len(f)==len(d)-1
    assert common==['4_250_20'] and f.occ.notna().all()
def test_exact_strata_do_not_relax_when_no_overlap():
    d=frame();d.loc[d.kind.eq('pseudo'),'trend']=-1
    f,c,s,common=m.support_weights(d);assert not len(f) and not len(s) and common==[]

def test_collision_counts_rows_and_unique_anchors_separately():
    d=frame();extra=d.iloc[[2]].copy();d=pd.concat([d,extra],ignore_index=True)
    r=m.collision_counts(d)[0];assert r['same_cell_real_anchor_overlap_rows']==5
    assert r['distinct_pseudo_same_cell_anchor_count']==4

def test_outcomes_never_requested_and_no_auto_acceptance():
    p=m.frozen_plan();assert set(p['columns_read']).isdisjoint(p['outcome_columns_prohibited'])
    assert not p['calipers_chosen'] and not p['scientific_acceptance_thresholds_chosen']

@pytest.mark.parametrize('flag',[False,True])
def test_pin_or_optin_failure_before_payload(tmp_path,flag):
    cmd=[sys.executable,'-O',m.__file__,'--inventory',str(tmp_path/'missing'),'--map-evidence',str(tmp_path/'missing'), '--map-evidence-sha256','0'*64,'--map-dir',str(tmp_path/'missing'),'--out-dir',str(tmp_path/'out')]
    if flag:cmd.append('--allow-exposed-covariate-review')
    r=subprocess.run(cmd,capture_output=True,text=True);assert r.returncode==2 and not (tmp_path/'out').exists()

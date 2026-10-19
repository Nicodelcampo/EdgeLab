"""Invented exported annotations; no raw ticks, historical prices or new outcomes."""
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

spec=spec_from_file_location('boundary_audit',Path(__file__).resolve().parents[1]/'tools/audit_avzvol_o5_boundary_exports.py')
mod=module_from_spec(spec);spec.loader.exec_module(mod)

def frame(last_session=20260922,penultimate_session=20260921):
    rows=[['MNQ_09-25','4_250_20','real',20260921,250,300,0.1]]
    if last_session is not None:rows.append(['MNQ_09-25','4_250_20','pseudo',last_session,500,-1,np.nan])
    if penultimate_session is not None:rows.append(['MNQ_09-25','4_250_20','pseudo',penultimate_session,499,-1,np.nan])
    return pd.DataFrame(rows,columns=mod.COLS)

@pytest.mark.parametrize('last,pen,category',[
    (20260922,20260921,'last_label_diff_penultimate_same'),
    (20260922,20260922,'last_and_penultimate_labels_diff'),
    (20260922,None,'last_label_diff_penultimate_unknown'),
    (20260921,None,'last_label_matches_anchor'),
    (None,None,'last_label_unknown')])
def test_only_exact_observed_labels_are_used(last,pen,category):
    d=frame(last,pen);r,w=mod.audit_frame(d)
    assert r['finite_o5_rows']==1 and r['finite_row_categories'][category]==1
    assert sum(r['finite_row_categories'].values())==1
    assert r['independent_crosscheck_passed'] is True
    assert r['missing_o5_rows']==len(d)-1
    assert len(w)==(1 if 'diff' in category else 0)

def test_duplicate_anchor_rows_are_not_duplicate_independent_evidence():
    d=frame();d=pd.concat([d,d.iloc[[1]]],ignore_index=True)
    r,w=mod.audit_frame(d)
    assert r['finite_o5_rows']==1 and r['unique_anchor_bar_labels']==3
    assert r['finite_row_categories']['last_label_diff_penultimate_same']==1

def test_conflicting_anchor_labels_are_ambiguous_not_silently_chosen():
    d=frame();other=d.iloc[[1]].copy();other['session']=20260921
    r,w=mod.audit_frame(pd.concat([d,other],ignore_index=True))
    assert r['ambiguous_anchor_bar_labels']==1
    assert r['finite_row_categories']['last_label_ambiguous']==1
    assert w==[]

@pytest.mark.parametrize('issue',['reserved','finite_no_exit','infinite','negative_anchor'])
def test_bad_export_annotation_stops(issue):
    d=frame()
    if issue=='reserved':d.loc[0,'session']=20261001
    elif issue=='finite_no_exit':d.loc[0,'te']=-1
    elif issue=='infinite':d.loc[0,'o5']=np.inf
    else:d.loc[0,'t0']=-1
    with pytest.raises(ValueError):mod.audit_frame(d)

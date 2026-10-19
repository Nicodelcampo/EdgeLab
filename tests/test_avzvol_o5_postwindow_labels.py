"""Invented bar/session annotations only; no prices or effect-size selection."""
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
spec=spec_from_file_location('postwindow_audit',Path(__file__).resolve().parents[1]/'tools/audit_avzvol_o5_postwindow_labels.py')
mod=module_from_spec(spec);spec.loader.exec_module(mod)

def frame(indices,labels=None):
    labels=labels if labels is not None else [20260105]*len(indices)
    rows=[['MNQ_09-25','4_250_20','real',20260105,10,20,.1]]
    rows.extend(['MNQ_09-25','4_250_20','pseudo',s,t,-1,np.nan] for t,s in zip(indices,labels))
    return pd.DataFrame(rows,columns=mod.COLS)

def test_last_label_alone_cannot_certify_whole_window():
    r=mod.audit_frame(frame([220]));assert r['finite_row_categories']['PARTIAL_OR_UNKNOWN_POSTWINDOW']==1
    assert r['max_distinct_observed_bars']==1

def test_exact_200_inclusive_labels_required_and_no_new_outcome():
    r=mod.audit_frame(frame(list(range(21,221))))
    assert r['finite_row_categories']['FULL_POSTWINDOW_ANNOTATED_SAME_SESSION']==1
    assert r['max_distinct_observed_bars']==200 and r['missing_o5_rows']==200

@pytest.mark.parametrize('missing',[21,100,219,220])
def test_any_missing_bar_is_unknown_not_imputed(missing):
    r=mod.audit_frame(frame([t for t in range(21,221) if t!=missing]))
    assert r['finite_row_categories']['PARTIAL_OR_UNKNOWN_POSTWINDOW']==1
    assert r['max_distinct_observed_bars']==199

def test_internal_contradiction_detected_even_if_last_label_matches():
    r=mod.audit_frame(frame([100,220],[20260106,20260105]))
    assert r['finite_row_categories']['CONTRADICTORY_OBSERVED_SESSION_LABEL']==1

def test_conflicting_duplicate_label_is_ambiguous_and_duplicates_are_not_coverage():
    r=mod.audit_frame(frame([100,100,220],[20260105,20260106,20260105]))
    assert r['finite_row_categories']['AMBIGUOUS_OBSERVED_LABEL']==1
    assert r['ambiguous_anchor_bar_labels']==1 and r['max_distinct_observed_bars']==2

def test_repeated_same_label_and_outside_bars_do_not_fill_missing():
    r=mod.audit_frame(frame([20,21,21,221]))
    assert r['max_distinct_observed_bars']==1
    assert r['finite_row_categories']['PARTIAL_OR_UNKNOWN_POSTWINDOW']==1

def test_contradiction_precedes_ambiguity_and_full_coverage_is_not_certification():
    r=mod.audit_frame(frame([100,100,200],[20260105,20260106,20260106]))
    assert r['finite_row_categories']['CONTRADICTORY_OBSERVED_SESSION_LABEL']==1
    assert r['independent_crosscheck_passed'] is True

@pytest.mark.parametrize('issue',['holdout','negative_anchor','negative_exit','infinite','overflow'])
def test_invalid_annotations_stop(issue):
    d=frame([100])
    if issue=='holdout':d.loc[0,'session']=20261001
    elif issue=='negative_anchor':d.loc[0,'t0']=-1
    elif issue=='negative_exit':d.loc[0,'te']=-1
    elif issue=='infinite':d.loc[0,'o5']=np.inf
    else:d.loc[0,'te']=np.iinfo(np.int64).max
    with pytest.raises(ValueError):mod.audit_frame(d)

# All-six preflight must stop before output/payload, including optimized Python.
import hashlib,json,subprocess,sys
import pyarrow as pa
import pyarrow.parquet as pq

def fixture(tmp_path,bad_hash=False,reserved=False):
    pins=[];inventory=[]
    contracts=['MNQ_09-25','MNQ_12-25','MNQ_03-26','MNQ_06-26','MNQ_09-26','MNQ_12-26']
    for i,c in enumerate(contracts):
        d=frame([220]);d['contract']=c
        if reserved and i==5:d['session']=20261001
        p=tmp_path/(c+'_avzp2racgrid.parquet');pq.write_table(pa.Table.from_pandas(d,preserve_index=False),p)
        pins.append({'file':p.name,'rows':len(d),'sha256':'0'*64 if bad_hash and i==5 else hashlib.sha256(p.read_bytes()).hexdigest()})
        inventory.append({'file':str(p)})
    ref=tmp_path/'reference.json';ref.write_text(json.dumps({'covariate_audit':{'files':pins}}))
    idx=tmp_path/'inventory.json';idx.write_text(json.dumps(inventory));return ref,idx

def call(tmp_path,ref,idx,optin=True):
    args=[sys.executable,'-O',str(Path(mod.__file__)),'--audit-reference',str(ref),
          '--audit-reference-sha256',hashlib.sha256(ref.read_bytes()).hexdigest(),
          '--inventory',str(idx),'--out-dir',str(tmp_path/'out')]
    if optin:args.append('--allow-exposed-output-audit')
    return subprocess.run(args,capture_output=True,text=True)

@pytest.mark.parametrize('issue',['bad_hash','reserved'])
def test_last_export_failure_stops_globally_before_payload(tmp_path,issue):
    ref,idx=fixture(tmp_path,**{issue:True});p=call(tmp_path,ref,idx)
    assert p.returncode==2 and not (tmp_path/'out').exists()

def test_portable_cli_preserves_unknown_without_effects(tmp_path):
    ref,idx=fixture(tmp_path);p=call(tmp_path,ref,idx);assert p.returncode==0,p.stdout+p.stderr
    e=json.loads((tmp_path/'out/evidence.json').read_text())
    assert e['totals']['finite_row_categories']['PARTIAL_OR_UNKNOWN_POSTWINDOW']==6
    assert e['totals']['full_postwindow_annotation_coverage_share']==0
    assert e['new_outcomes_computed'] is False and e['source_quality_certified'] is False
    assert e['economic_outcomes_computed'] is False and e['prewindow_coverage_verified'] is False

def test_no_optin_and_no_overwrite(tmp_path):
    ref,idx=fixture(tmp_path);p=call(tmp_path,ref,idx,False)
    assert p.returncode==2 and not (tmp_path/'out').exists()
    (tmp_path/'out').mkdir();sentinel=tmp_path/'out/original';sentinel.write_text('keep')
    p=call(tmp_path,ref,idx);assert p.returncode==2 and sentinel.read_text()=='keep'

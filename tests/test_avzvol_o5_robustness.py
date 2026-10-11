"""Invented log values only; no new prices or scientific gate clearance."""
import importlib.util
import subprocess
import sys
from pathlib import Path
import math
import numpy as np
import pandas as pd
import pytest
TOOL=Path(__file__).resolve().parents[1]/'tools/review_avzvol_o5_robustness.py'
spec=importlib.util.spec_from_file_location('robustness',TOOL)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def frame():
    rows=[]
    for c in mod.CONTRACTS:
        rows.extend([(c,1,'4_250_20','real',0.),(c,1,'4_250_20','pseudo',1.),
                     (c,2,'4_250_20','real',0.),(c,2,'4_250_20','pseudo',3.)])
    return pd.DataFrame(rows,columns=mod.KEYS+['kind','o5'])

def test_equal_sessions_and_whole_date_deletion():
    d=frame();g=mod.groups(d);m=mod.matrix(g,['4_250_20'])
    assert mod.scalar(m,cells=['4_250_20'])==pytest.approx(-2.)
    removed=mod.matrix(g[g.index.get_level_values('session')!=2],['4_250_20'])
    assert mod.scalar(removed,cells=['4_250_20'])==pytest.approx(-1.)
    assert mod.scalar(m,mod.CONTRACTS[:-1],['4_250_20'])==pytest.approx(-2.)

def test_missing_kind_is_not_zero_and_fixed_panel_not_shrunk():
    d=frame();d=d[~((d.contract==mod.CONTRACTS[-1]) & (d.kind=='pseudo'))]
    m=mod.matrix(mod.groups(d),['4_250_20'])
    assert m.isna().sum()==1 and mod.scalar(m,cells=['4_250_20']) is None

def test_replacement_duplicates_preserved_and_missing_not_imputed():
    d=frame();extra=d.iloc[[1]].copy();extra['o5']=5.
    missing=d.iloc[[1]].copy();missing['o5']=np.nan
    g=mod.groups(pd.concat([d,extra,missing],ignore_index=True))
    assert g.loc[(mod.CONTRACTS[0],1,'4_250_20'),'delta']==pytest.approx(-3.)
    assert mod.interpret(-.1)['relative_geometric_gap_percent']==pytest.approx(100*math.expm1(-.1))
    assert all(v is None for v in mod.interpret(None).values())

def call(tmp_path,flag=False,pin='0'*64):
    cmd=[sys.executable,'-O',str(TOOL),'--inventory',str(tmp_path/'nonexistent'),
         '--out-dir',str(tmp_path/'out'),'--audit-reference-sha256',pin]
    if flag:cmd.append('--allow-exposed-o5-review')
    return subprocess.run(cmd,capture_output=True,text=True)

def test_optin_precedes_any_files(tmp_path):
    p=call(tmp_path);assert p.returncode==2 and not (tmp_path/'out').exists()

def test_reference_mismatch_precedes_inventory_even_optimized(tmp_path):
    p=call(tmp_path,True)
    assert p.returncode!=0 and 'audit reference pin mismatch' in p.stderr
    assert 'nonexistent' not in p.stderr and not (tmp_path/'out/evidence.json').exists()

def test_output_never_overwritten(tmp_path):
    (tmp_path/'out').mkdir();sentinel=tmp_path/'out/sentinel';sentinel.write_text('keep')
    p=call(tmp_path,True);assert p.returncode!=0 and sentinel.read_text()=='keep'

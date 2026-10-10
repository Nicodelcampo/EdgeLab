"""Pinned historical guard on invented session IDs only; no market O5 read/rewrite."""
import ast
import hashlib
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

def guard():
    raw=(ROOT/'tests/fixtures/avzvol_o5_legacy_boundary.py.txt').read_bytes()
    # Assigned below from the pinned source extraction, not a regenerated algorithm.
    expected='2cb3bba9be80c306a4f4d349726694a34e9b57e3cd2359771a02f950639f4455'
    assert hashlib.sha256(raw).hexdigest()==expected
    tree=ast.parse(raw.decode())
    assert len(tree.body)==1 and isinstance(tree.body[0],ast.FunctionDef)
    assert not any(isinstance(x,(ast.Import,ast.ImportFrom)) for x in ast.walk(tree))
    env={};exec(compile(tree,'pinned-o5-guard','exec'),env)
    return env['historical_o5_guard']

def test_guard_can_accept_last_postwindow_bar_in_next_declared_session():
    te,horizon,n,pre_end=300,200,502,250
    session=np.zeros(n,dtype=np.int64);session[500:]=1
    assert guard()(te,horizon,n,pre_end,np.ones(n),session)
    # Original forward range [te+1,te+200] includes index 500, not just 499.
    actual_indices=np.arange(te+1,te+1+horizon)
    assert len(actual_indices)==200 and actual_indices[-1]==500
    assert session[actual_indices[-2]]==session[te]
    assert session[actual_indices[-1]]!=session[te]

def test_revised_last_included_bar_check_rejects_boundary_case():
    session=np.zeros(502,dtype=np.int64);session[500:]=1
    assert not (session[300+200]==session[300])
    # A genuinely same-session postwindow satisfies both checks; no repaired outcomes.
    session[:]=0
    assert guard()(300,200,502,250,np.ones(502),session)
    assert session[300+200]==session[300]

def test_guard_rejects_missing_array_horizon_or_zero_past_range():
    session=np.zeros(502,dtype=np.int64)
    assert not guard()(300,200,500,250,np.ones(502),session)
    past=np.ones(502);past[250]=0
    assert not guard()(300,200,502,250,past,session)

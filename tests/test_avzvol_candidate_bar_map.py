"""Invented timestamps and log values only, no market source or pricing."""
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import pytest
spec=spec_from_file_location('candidate_map',Path(__file__).resolve().parents[1]/'tools/reconstruct_avzvol_candidate_bar_map.py')
mod=module_from_spec(spec);spec.loader.exec_module(mod)

def oracle(ts,sid):
    ends=[];pending=[];previous=None
    for t,s in zip(ts,sid):
        if pending and s!=previous:ends.append(pending[-1]);pending=[]
        pending.append(t);previous=s
        if len(pending)==25:ends.append(pending[-1]);pending=[]
    if pending:ends.append(pending[-1])
    return np.array(ends,dtype=np.int64)

@pytest.mark.parametrize('chunk',[1,7,25,26,80,200])
def test_session_reset_short_bar_and_batch_invariance(chunk):
    ts=np.arange(123,dtype=np.int64);sid=np.r_[np.repeat(1,27),np.repeat(2,50),np.repeat(3,46)]
    b=mod.TimestampBarBuilder()
    for a in range(0,len(ts),chunk):b.feed(ts[a:a+chunk],sid[a:a+chunk])
    assert np.array_equal(b.finish(),oracle(ts,sid))

def test_equal_timestamps_are_not_deduplicated():
    b=mod.TimestampBarBuilder();b.feed(np.zeros(51,dtype=np.int64),np.ones(51,dtype=np.int64))
    assert len(b.finish())==3

@pytest.mark.parametrize('text',['2025-11-02T07:59:00Z','2025-11-02T08:00:00Z','2026-03-08T07:59:00Z','2026-03-08T08:00:00Z','2026-01-05T22:59:00Z','2026-01-05T23:00:00Z'])
def test_minute_fields_independent_zoneinfo(text):
    ns=pd.Timestamp(text).value;sids,minutes=mod.minute_fields(np.array([ns]))
    dt=datetime.fromisoformat(text.replace('Z','+00:00')).astimezone(ZoneInfo('America/Chicago'))
    assert minutes[0]==dt.hour*60+dt.minute
    day=(dt.date()-datetime(1970,1,1).date()).days+(dt.hour>=17)
    assert sids[0]==day

@pytest.mark.parametrize('text,expected',[('2026-01-05T21:59:59Z',20260105),('2026-01-05T22:00:00Z',20260106),('2026-01-09T22:00:00Z',20260112)])
def test_legacy_close_strictly_after_and_weekday(text,expected):
    end=np.array([pd.Timestamp(text).value]);labels,send,grid=mod.legacy_session_labels(end)
    assert labels[0]==expected and send[0]>end[0] and grid==0

def test_backward_timestamps_rejected_not_silently_sorted():
    b=mod.TimestampBarBuilder()
    with pytest.raises(ValueError):b.feed(np.array([2,1]),np.array([1,1]))
    b.feed(np.array([2,3]),np.array([1,1]))
    with pytest.raises(ValueError):b.feed(np.array([1]),np.array([1]))

def exports(te=20):
    return pd.DataFrame([['MNQ_09-25','4_250_20','real',20260105,0,0,te,.1]],
        columns=['contract','cell','kind','session','clock','t0','te','o5'])

def test_full_candidate_postwindow_does_not_recompute_outcome():
    r=mod.check_export(exports(),np.arange(250),np.repeat(20260105,250),np.zeros(250),250)
    assert r['finite_post_window_categories']=={'FULL_POST_WINDOW_WITHIN_CANDIDATE_SESSION':1}
    assert r['prewindow_not_reconstructible_from_export_alone'] is True

def test_exact_legacy_guard_cross_witness():
    labels=np.repeat(20260105,250);labels[220:]=20260106
    r=mod.check_export(exports(),np.arange(250),labels,np.zeros(250),250)
    assert r['finite_post_window_categories']=={'POST_WINDOW_CROSSES_CANDIDATE_SESSION':1}
    assert r['legacy_guard_last_bar_cross_witness_rows']==1

def test_anchor_mismatch_stops_interpretation_not_favorable_fallback():
    labels=np.repeat(20260106,250)
    r=mod.check_export(exports(),np.arange(250),labels,np.zeros(250),250)
    assert r['finite_post_window_categories']=={'UNKNOWN_CANDIDATE_ANCHOR_ALIGNMENT':1}
    assert r['all_postwindow_labels_checked'] is False

def test_logged_bar_count_mismatch_stops():
    with pytest.raises(ValueError):mod.check_export(exports(),np.arange(250),np.repeat(20260105,250),np.zeros(250),251)

def test_elapsed_day_dst_close_grid_quirk_is_preserved_not_silently_fixed():
    end=np.array([pd.Timestamp('2025-11-03T16:30:00',tz='America/Chicago').value])
    old,_,grid=mod.legacy_session_labels(end)
    reference=mod.reference_weekday_close_labels(end)
    assert grid==60 and old[0]==20251103 and reference[0]==20251104

def test_reference_and_legacy_agree_after_pause_filtered_timestamp():
    end=np.array([pd.Timestamp('2025-11-03T17:01:00',tz='America/Chicago').value])
    old,_,grid=mod.legacy_session_labels(end)
    assert grid==60 and np.array_equal(old,mod.reference_weekday_close_labels(end))

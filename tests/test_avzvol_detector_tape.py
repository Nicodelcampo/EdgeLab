"""Exact legacy replay and invented footprint fixtures ONLY; no market sources."""
import copy
import json
import numpy as np
import pandas as pd
import pytest
from edgelab.kaggle import avzvol_detector_tape as mod
from edgelab.kaggle.avzvol_zone_negative import classify_detector_window

CUTOFF = pd.Timestamp('2026-09-30T22:00Z').value

def replay(bars, fp, sessions, **changes):
    return mod.replay_declared_detector(bars,fp,sessions,**{
        'params':mod.legacy_parameters(),'holdout_start':'2026-10-01',
        'utc_cutoff_ns':CUTOFF,**changes})

def test_pinned_original_and_instrumentation_agree_on_every_block_and_creation():
    b,f,s=mod.synthetic_fixture(22,3)
    original=mod._namespace()['run'](b,f,np.asarray(s),mod.legacy_parameters())
    tape=replay(b,f,s)
    expected=[{**{k:z[k] for k in mod.CREATION_KEYS},'session':s[z['bar']],
               'available_bar':z['bar']} for z in original['zones']]
    assert tape['zone_creation_snapshots']==expected
    assert [(x['observation']['block_end_bar'],x['distinct_price_levels'],
        x['historical_best_score'],x['bucket']) for x in tape['observations']]==[
            tuple(x[:4]) for x in original['blocks']]
    assert tape['incomplete_session_tails']==[{'session':'2026-09-22',
        'first_bar':220,'last_bar':222,'bar_count':3,
        'status':'INCOMPLETE_DETECTOR_BLOCK_NOT_PADDED'}]
    # Historical observation/invalidation may change final state, never the creation tape.
    assert all(set(z)==set(mod.CREATION_KEYS)|{'session','available_bar'}
               for z in tape['zone_creation_snapshots'])
    assert json.loads(json.dumps(tape))==tape

def test_later_session_cannot_change_existing_block_or_zone_snapshots():
    short=replay(*mod.synthetic_fixture(21))
    long=replay(*mod.synthetic_fixture(22))
    assert short['observations']==long['observations'][:21]
    assert short['zone_creation_snapshots']==[z for z in long['zone_creation_snapshots']
                                             if z['bar']<210]

def test_later_prices_changed_cannot_change_prefix():
    b,f,s=mod.synthetic_fixture(22)
    before=replay(b,f,s)
    f.vols[210*5:]*=100
    after=replay(b,f,s)
    assert before['observations'][:21]==after['observations'][:21]
    assert [z for z in before['zone_creation_snapshots'] if z['bar']<210]==[
        z for z in after['zone_creation_snapshots'] if z['bar']<210]

def test_cold_blocks_do_not_turn_into_negative_controls():
    r=replay(*mod.synthetic_fixture(22))
    first=r['observations'][0]
    assert first['observation']['threshold']==-1.0
    c=classify_detector_window([first['observation']],session='2026-09-01',
        session_first_bar=0,window_first_bar=0,anchor_bar=9,
        holdout_start='2026-10-01',block_bars=10,minimum_calibration_samples=20)
    assert c['classification']=='UNKNOWN'
    last=r['observations'][20]
    assert last['observation']['calibration_samples']==20
    assert last['observation']['baseline_last_session']=='2026-09-20'
    c=classify_detector_window([last['observation']],session='2026-09-21',
        session_first_bar=200,window_first_bar=200,anchor_bar=209,
        holdout_start='2026-10-01',block_bars=10,minimum_calibration_samples=20)
    assert c['classification']=='DETECTED_ZONE'

def test_fewer_than_three_price_levels_still_declares_uncertainty():
    b,f,s=mod.synthetic_fixture(1)
    # One price level and no prior calibrated bucket; not evidence of absence.
    f.ticks[:]=102
    r=replay(b,f,s)
    assert len(r['observations'])==1
    x=r['observations'][0]
    assert x['distinct_price_levels']==1
    assert x['historical_threshold_branch_executed'] is False
    assert x['detector_ready_as_declared'] is False
    assert x['observation']['threshold'] is None

def test_tapes_do_not_authorize_market_census_or_outcomes():
    r=replay(*mod.synthetic_fixture(1))
    for k in ['source_quality_certified','historical_consumption_verified',
              'census_completeness_verified','scientific_rule_approved',
              'research_authorized','outcomes_computed','original_outputs_modified']:
        assert r[k] is False
    assert 'outcomes' not in r and 'eligible_controls' not in r

@pytest.mark.parametrize('change',['recurrent_session','reserved_session',
    'reserved_utc','retrograde','bad_offsets','nonfinite_volume','negative_volume',
    'footprint_outside','close_outside','bad_params','bool_params','noncanonical_holdout'])
def test_invalid_declarations_stop_without_repair(change):
    b,f,s=mod.synthetic_fixture(3);kw={}
    if change=='recurrent_session':s[20:] = ['2026-09-01']*10
    elif change=='reserved_session':s[20:] = ['2026-10-01']*10
    elif change=='reserved_utc':b.end_ns[-1]=CUTOFF
    elif change=='retrograde':b.end_ns[-1]=b.end_ns[-2]-1
    elif change=='bad_offsets':f.offsets[-1]+=1
    elif change=='nonfinite_volume':f.vols=f.vols.astype(float);f.vols[-1]=np.nan
    elif change=='negative_volume':f.vols[-1]=-1
    elif change=='footprint_outside':f.ticks[-1]=105
    elif change=='close_outside':b.close_t[-1]=105
    elif change=='bad_params':kw['params']={**mod.legacy_parameters(),'ob_bars':0}
    elif change=='bool_params':kw['params']={**mod.legacy_parameters(),'racimo_min':False}
    else:kw['holdout_start']='2026-10-1'
    with pytest.raises(mod.DetectorTapeError):replay(b,f,s,**kw)

def test_instrumentation_does_not_mutate_inputs():
    b,f,s=mod.synthetic_fixture(22)
    originals={k:np.array(v,copy=True) for k,v in vars(b).items()}
    originals_fp={k:np.array(v,copy=True) for k,v in vars(f).items()}
    params=mod.legacy_parameters();saved=copy.deepcopy(params)
    replay(b,f,s,params=params)
    assert params==saved
    for k,v in originals.items():assert np.array_equal(getattr(b,k),v)
    for k,v in originals_fp.items():assert np.array_equal(getattr(f,k),v)

def test_calibrated_low_score_window_can_be_negative_without_zero_imputation():
    b,f,s=mod.synthetic_fixture(21)
    f.vols[200*5:210*5].reshape(10,5)[:,2:4]=20
    r=replay(b,f,s);x=r['observations'][-1]
    assert x['detector_ready_as_declared'] is True
    assert x['observation']['detected_zone_count']==0
    c=classify_detector_window([x['observation']],session='2026-09-21',
        session_first_bar=200,window_first_bar=200,anchor_bar=209,
        holdout_start='2026-10-01',block_bars=10,minimum_calibration_samples=20)
    assert c['classification']=='DETECTOR_NEGATIVE'

def test_future_invalidation_does_not_rewrite_creation_snapshot():
    short=replay(*mod.synthetic_fixture(21))
    b,f,s=mod.synthetic_fixture(22);b.high_t[210:]=1000
    original=mod._namespace()['run'](b,f,np.asarray(s),mod.legacy_parameters())
    assert original['zones'][0]['state'] != 0
    long=replay(b,f,s)
    assert short['zone_creation_snapshots']==[z for z in long['zone_creation_snapshots']
                                             if z['bar']<210]
    assert all('state' not in z and 'decided_bar' not in z for z in long['zone_creation_snapshots'])

def test_finite_volume_overflow_stops_instead_of_emitting_infinite_scores():
    b,f,s=mod.synthetic_fixture(1);f.vols=f.vols.astype(float);f.vols[:]=1e308
    with np.errstate(over='ignore',invalid='ignore'):
        with pytest.raises(mod.DetectorTapeError):replay(b,f,s)

def test_calibrated_bucket_without_executed_threshold_branch_stays_unknown():
    b,f,s=mod.synthetic_fixture(21);f.ticks[200*5:]=102
    r=replay(b,f,s);x=r['observations'][-1]
    assert x['observation']['calibration_samples']==20
    assert x['derived_prior_threshold']>0
    assert x['historical_threshold_branch_executed'] is False
    assert x['observation']['threshold'] is None
    c=classify_detector_window([x['observation']],session='2026-09-21',
        session_first_bar=200,window_first_bar=200,anchor_bar=209,
        holdout_start='2026-10-01',block_bars=10,minimum_calibration_samples=20)
    assert c['classification']=='UNKNOWN'

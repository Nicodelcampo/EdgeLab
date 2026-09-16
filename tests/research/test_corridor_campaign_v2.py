from datetime import datetime
import numpy as np, pytest
from edgelab.research.corridor_campaign_v2 import *

def ns(s): return int(datetime.fromisoformat(s).timestamp()*1e9)
def z(**kw):
    d=dict(zone_id='z',source='BT2A',side=1,lower_tick=100,upper_tick=102,created_ns=0,available_ns=0,strength=20,touches_asof=0)
    d.update(kw); return ZoneState(**d)
def test_horizon_has_no_1000_tick_cap_and_marks_edge():
    t=np.arange(0,5000,dtype=np.int64)*1_000_000
    a,b,ok=causal_horizon_indices(t,10_000_000,2_000_000_000,4_000_000_000)
    assert b-a>1000 and ok
    assert not causal_horizon_indices(t,4_500_000_000,2_000_000_000,7_000_000_000)[2]
def test_order_checked_across_full_array():
    t=np.arange(2000); q=np.arange(2000); t[1500]=t[1499]-1
    with pytest.raises(CampaignV2Error): validate_tick_order(t,q)
def test_trade_date_is_dst_safe():
    assert cme_trade_date(ns('2026-01-15T22:30:00+00:00'))=='2026-01-15'
    assert cme_trade_date(ns('2026-06-15T22:30:00+00:00'))=='2026-06-16'
def test_three_single_component_ablations():
    a=ablation_specs(WeightSpec()); assert set(a)=={'FULL','NO_MATURATION','NO_TIME_DECAY','NO_WEAR'}
    assert not a['NO_MATURATION'].use_maturation and not a['NO_TIME_DECAY'].use_time_decay and not a['NO_WEAR'].use_wear
def test_each_decay_component_changes_weight():
    zz=z(touches_asof=3); base=WeightSpec(maturation_hours=10,decay_starts_hours=1,half_life_hours=2); now=int(5*3.6e12)
    vals={k:zone_weight(zz,now,v) for k,v in ablation_specs(base).items()}
    assert len(set(round(x,10) for x in vals.values()))==4
def test_mixed_indicator_field_and_combiners():
    zs=[z(source='BT2A'),z(zone_id='g',source='Gaps2',lower_tick=104,upper_tick=105)]
    p1,f1=directional_field(99,1,zs,0,WeightSpec(),FieldSpec(combine_sources='sum'))
    p2,f2=directional_field(99,1,zs,0,WeightSpec(),FieldSpec(combine_sources='consensus_product'))
    assert np.array_equal(p1,p2) and np.all(f1>=f2) and f1.max()>0
def test_holm_resolution_gate():
    assert required_resamples_for_holm(54)==1080
    with pytest.raises(CampaignV2Error): assert_permutation_resolution(1000,54)
    assert_permutation_resolution(100_000,54)
def test_zero_pairs_abstains_and_economics_are_separate():
    assert zero_event_status(0)=='ABSTAIN_NO_CAUSAL_EVENTS'
    assert economic_labels(-.9,-1.0)==['FAIL_ABSOLUTE_NET_EXPECTANCY_NONPOSITIVE']
def test_cache_key_changes_with_inputs():
    a=cache_key(data_sha256='a',code_sha256='c',params={'x':1},contract='6E')
    b=cache_key(data_sha256='b',code_sha256='c',params={'x':1},contract='6E')
    assert a!=b

def test_campaign_state_reset_on_roll_clears_all_and_censors_episodes():
    active_ep = {"episode_id": "ep_01", "terminal": None}
    state = CampaignState(
        active_zones=[z()],
        touches={"z": 5},
        field_cache={"field_01": np.zeros(10)},
        normalizers={"rolling_std": 1.5},
        frozen_corridors=[{"corridor_id": "c1"}],
        active_episodes=[active_ep],
        indicator_state={"bt2a_acc": 42.0},
    )
    censored = reset_campaign_state_on_roll(state)
    assert len(censored) == 1
    assert censored[0]["terminal"] == "CENSORED_CONTRACT_ROLL"
    assert len(state.active_zones) == 0
    assert len(state.touches) == 0
    assert len(state.field_cache) == 0
    assert len(state.normalizers) == 0
    assert len(state.frozen_corridors) == 0
    assert len(state.active_episodes) == 0
    assert len(state.indicator_state) == 0


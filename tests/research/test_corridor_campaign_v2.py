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

def test_reset_on_roll_fails_closed_on_unsupported_episode():
    state = CampaignState(
        active_zones=[],
        touches={},
        field_cache={},
        normalizers={},
        frozen_corridors=[],
        active_episodes=[12345],
        indicator_state={},
    )
    with pytest.raises(CampaignV2Error, match="cannot censor active episode at roll"):
        state.reset_on_roll()

def test_campaign_processor_stream_resets_before_processing_tick():
    state = CampaignState(
        active_zones=[z()],
        touches={"z": 3},
        field_cache={},
        normalizers={},
        frozen_corridors=[],
        active_episodes=[{"id": "ep1", "terminal": None}],
        indicator_state={"acc": 100},
    )
    proc = CampaignProcessor(state)
    r1 = proc.process_tick(ts_ns=1000, price_tick=100, volume=1.0, sequence=0, state_reset_flag=False)
    assert r1["active_zones_count"] == 1
    assert r1["active_episodes_count"] == 1
    assert len(proc.censored_at_rolls) == 0

    r2 = proc.process_tick(ts_ns=2000, price_tick=105, volume=2.0, sequence=1, state_reset_flag=True)
    assert r2["active_zones_count"] == 0
    assert r2["active_episodes_count"] == 0
    assert len(proc.censored_at_rolls) == 1
    assert proc.censored_at_rolls[0]["terminal"] == "CENSORED_CONTRACT_ROLL"
    assert proc.state.indicator_state.get("regime_initialized") is True

def test_new_contract_price_never_resolves_prior_episode():
    from edgelab.research.void_revisit_episodes import detect_revisit_episodes, RevisitSpec
    p = [90, 99, 93, 93, 93, 99, 120]
    t = np.arange(len(p), dtype=np.int64) * 10_000_000_000
    rolls = [False, False, False, False, False, False, True]
    episodes = detect_revisit_episodes(t, p, np.ones(len(p)), 100, 110, 1,
                                       RevisitSpec(min_away_seconds=20, rejection_excursion_ticks=6),
                                       state_reset_flags=rolls)
    assert len(episodes) == 1
    assert episodes[0].terminal == "CENSORED_CONTRACT_ROLL"
    assert episodes[0].terminal != "TRAVERSED"


def test_campaign_processor_stream_end_to_end_integration():
    from edgelab.research.corridor_campaign_v2 import CampaignProcessor, ZoneState

    proc = CampaignProcessor()

    # 1. Pre-roll regime (NQ 06-26)
    z_old = ZoneState(zone_id="zone_old_1", source="BT2A", side=1, lower_tick=100, upper_tick=108, created_ns=1_000_000_000, available_ns=1_000_000_000, strength=5.0)
    proc.add_zone(z_old)
    proc.add_corridor({"corridor_id": "corr_old_1", "lower": 100, "upper": 108})
    proc.add_episode({"episode_id": "ep_old_1", "terminal": None, "stage_at_censoring": "AWAY_QUALIFIED"})

    assert len(proc.state.active_zones) == 1
    assert len(proc.state.active_episodes) == 1
    assert len(proc.state.frozen_corridors) == 1

    # Ticks within old zone boundary increment touches
    t1 = proc.process_tick(ts_ns=1_000_000_000, price_tick=104, volume=10.0, sequence=0, state_reset_flag=False, session_id="2026-06-03")
    assert proc.state.touches["zone_old_1"] == 1
    assert t1["active_zones_count"] == 1

    t2 = proc.process_tick(ts_ns=1_000_001_000, price_tick=106, volume=5.0, sequence=1, state_reset_flag=False, session_id="2026-06-03")
    assert proc.state.touches["zone_old_1"] == 2
    assert len(proc.censored_at_rolls) == 0

    # 2. Roll boundary tick: state_reset_flag = True (rollover to NQ 09-26)
    t_roll = proc.process_tick(ts_ns=1_000_002_000, price_tick=120, volume=15.0, sequence=2, state_reset_flag=True, session_id="2026-06-04")

    # a) Old episode is censored as CENSORED_CONTRACT_ROLL and persisted
    assert len(proc.censored_at_rolls) == 1
    assert proc.censored_at_rolls[0]["episode_id"] == "ep_old_1"
    assert proc.censored_at_rolls[0]["terminal"] == "CENSORED_CONTRACT_ROLL"
    assert proc.censored_at_rolls[0]["stage_at_censoring"] == "AWAY_QUALIFIED"

    # b) State is completely wiped clean of old regime entities
    assert len(proc.state.active_zones) == 0
    assert len(proc.state.touches) == 0
    assert len(proc.state.frozen_corridors) == 0
    assert len(proc.state.active_episodes) == 0
    assert "zone_old_1" not in proc.state.touches

    # c) New regime initialized
    assert proc.state.indicator_state.get("regime_initialized") is True
    assert proc.state.indicator_state.get("regime_start_ts_ns") == 1_000_002_000

    # 3. Process new regime in stream
    z_new = ZoneState(zone_id="zone_new_1", source="BT2A", side=1, lower_tick=120, upper_tick=128, created_ns=1_000_002_000, available_ns=1_000_002_000, strength=8.0)
    proc.add_zone(z_new)
    proc.add_episode({"episode_id": "ep_new_1", "terminal": None, "stage_at_censoring": None})

    t_post = proc.process_tick(ts_ns=1_000_003_000, price_tick=124, volume=8.0, sequence=3, state_reset_flag=False, session_id="2026-06-04")
    assert proc.state.touches["zone_new_1"] == 1
    assert "zone_old_1" not in proc.state.touches
    assert len(proc.state.active_zones) == 1
    assert proc.state.active_zones[0].zone_id == "zone_new_1"
    assert len(proc.state.active_episodes) == 1
    assert proc.state.active_episodes[0]["episode_id"] == "ep_new_1"
    assert len(proc.censored_at_rolls) == 1



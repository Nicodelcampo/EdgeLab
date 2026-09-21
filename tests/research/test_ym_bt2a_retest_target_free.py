import pytest
from edgelab.research.ym_bt2a_retest_pilot import *

def event(**updates):
    values=dict(event_id="E1",instrument="YM",contract="YM 09-26",source_barspec="time_5m",formation_start_ns=100,formation_end_ns=200,available_at_ns=200,available_sequence=9,signal_price_half_ticks=210,zone_lo_half_ticks=200,zone_hi_half_ticks=204,direction="long",semantics="M5_FORMATION",indicator_parameters_hash="a"*64,source_data_hash="b"*64,code_commit="abc",session_id="S1"); values.update(updates); return ZoneEvent(**values)
def ticks(*prices,start=201,session="S1"): return [Tick(start+i,i,p,session) for i,p in enumerate(prices)]
def run(e,ts,p): return evaluate_policy(e,ts,p,custody_verified=True,semantics_resolved=True)
def test_policy_inventory_is_frozen_at_fifteen(): assert len(policies_v1())==15
def test_custody_is_fail_closed():
    with pytest.raises(ValueError,match="CUSTODY"): evaluate_policy(event(),ticks(210),policies_v1()[0],custody_verified=False,semantics_resolved=True)
def test_semantics_are_fail_closed():
    with pytest.raises(ValueError,match="SEMANTICS"): evaluate_policy(event(),ticks(210),policies_v1()[0],custody_verified=True,semantics_resolved=False)
def test_holdout_is_forbidden():
    with pytest.raises(ValueError,match="HOLDOUT"): run(event(available_at_ns=HOLDOUT_BOUNDARY_NS),[],policies_v1()[0])
def test_zero_duration_tick_bucket_is_valid_when_ordering_is_causal():
    e=event(formation_start_ns=200,formation_end_ns=200,available_at_ns=200)
    assert run(e,[Tick(201,10,210,"S1")],Policy("P0","IMMEDIATE")).state=="ENTERED"
def test_immediate_is_strictly_post_available():
    d=run(event(),[Tick(200,9,999,"S1"),Tick(200,10,211,"S1")],Policy("P0","IMMEDIATE")); assert (d.entry_ts_ns,d.entry_sequence)==(200,10)
def test_formation_touch_is_excluded():
    d=run(event(),[Tick(150,1,202,"S1"),Tick(201,2,208,"S1"),Tick(202,3,204,"S1"),Tick(203,4,206,"S1")],Policy("R","RETEST",departure_ticks=2,depth=0,max_wait_ticks=10))
    assert (d.trigger_ts_ns,d.entry_ts_ns)==(202,203)
def test_price_inside_zone_must_depart_first(): assert run(event(),ticks(202,203,208,203,202),Policy("R","RETEST",departure_ticks=2,depth=0,max_wait_ticks=10)).entry_price_half_ticks==202
def test_half_depth_for_long(): assert run(event(),ticks(208,204,203,202,204),Policy("R","RETEST",departure_ticks=2,depth=.5,max_wait_ticks=10)).entry_price_half_ticks==204
def test_short_is_symmetric(): assert run(event(direction="short"),ticks(196,200,202),Policy("R","RETEST",departure_ticks=2,depth=0,max_wait_ticks=10)).entry_price_half_ticks==202
def test_full_depth_long_quantizes_to_deepest_executable_price_inside_half_tick_zone():
    e=event(zone_lo_half_ticks=201,zone_hi_half_ticks=205); d=run(e,ticks(210,204,202,204),Policy("R","RETEST",departure_ticks=2,depth=1,max_wait_ticks=10)); assert (d.trigger_ts_ns,d.entry_price_half_ticks)==(203,204)
def test_full_depth_short_quantizes_to_deepest_executable_price_inside_half_tick_zone():
    e=event(zone_lo_half_ticks=201,zone_hi_half_ticks=205,direction="short"); d=run(e,ticks(196,202,204,202),Policy("R","RETEST",departure_ticks=2,depth=1,max_wait_ticks=10)); assert (d.trigger_ts_ns,d.entry_price_half_ticks)==(203,202)
def test_retest_without_later_tick_abstains():
    d=run(event(),ticks(208,204),Policy("R","RETEST",departure_ticks=2,depth=0,max_wait_ticks=10)); assert d.state=="CENSORED" and d.censor_reason=="NO_EXECUTABLE_FILL_AVAILABLE"; assert d.trigger_ts_ns==202 and d.entry_ts_ns is None
def test_no_departure_is_censored_at_expiry(): assert run(event(),ticks(202,203,204),Policy("R","RETEST",departure_ticks=2,depth=0,max_wait_ticks=3)).censor_reason=="NO_DEPARTURE_BEFORE_EXPIRY"
def test_no_retest_is_censored_at_expiry(): assert run(event(),ticks(208,210,212),Policy("R","RETEST",departure_ticks=2,depth=0,max_wait_ticks=3)).censor_reason=="NO_RETEST_BEFORE_EXPIRY"
def test_session_end_before_departure_is_distinct_from_expiry(): assert run(event(),ticks(202,203,204),Policy("R","RETEST",departure_ticks=2,depth=0,max_wait_ticks=10)).censor_reason=="SESSION_END_BEFORE_DEPARTURE"
def test_session_end_before_retest_is_distinct_from_expiry(): assert run(event(),ticks(208,210,212),Policy("R","RETEST",departure_ticks=2,depth=0,max_wait_ticks=10)).censor_reason=="SESSION_END_BEFORE_RETEST"
def test_session_crossing_is_excluded(): assert run(event(),ticks(208,203,session="S2"),Policy("R","RETEST",departure_ticks=2,depth=0,max_wait_ticks=3)).censor_reason=="NO_POST_AVAILABILITY_TICK"
def test_duplicate_tick_identity_fails():
    with pytest.raises(ValueError,match="duplicate"): run(event(),[Tick(201,1,208,"S1"),Tick(201,1,204,"S1")],Policy("P0","IMMEDIATE"))
def test_decision_record_is_target_free_and_hashed():
    r=decision_record(run(event(),ticks(210),Policy("P0","IMMEDIATE"))); assert_target_free(r); assert len(r["record_sha256"])==64

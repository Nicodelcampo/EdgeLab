"""Exercise actual pinned detectors on INVENTED tapes, never market inputs."""
import copy
from dataclasses import asdict
from unittest.mock import patch
import unittest
import numpy as np
from edgelab.bridge.ticks import TickSeries,make_synthetic
from edgelab.bridge import bars as B
from edgelab.bridge.indicators import bigtrap2,bigtrap2absorption
from tools.research_ops.confluence import _pinned_avzp2 as avz
from tools.research_ops.confluence.detector_capture import capture_run,PINS
from tools.research_ops.confluence._pinned_total_footprint import build_total_footprint_csr_nt8

def trap_tape(n=501,same_ns=False):
    # Ask aggression at high rows followed by a low close, then mirror.
    pattern=[100,101,102,103,104,103,102,101,100,99]
    px=np.resize(pattern,n).astype(np.int64);base=np.datetime64('2026-09-01T14:00:00','ns').astype(np.int64)
    ts=base+(np.arange(n,dtype=np.int64)//(10 if same_ns else 1))*1000000
    return TickSeries(ts,px,np.ones(n)*10,px-1,px,np.arange(n,dtype=np.int64),.25,instrument='SYN',contract='SYN')

def avz_tape():
    px=np.tile(np.array([100,101,102,103,104]),80);vol=np.tile(np.array([1,1,1,100,100]),80)
    base=np.datetime64('2026-09-01T14:00:00','ns').astype(np.int64)
    ts=np.repeat(base+np.arange(20,dtype=np.int64)*86400000000000,20)+np.tile(np.arange(20,dtype=np.int64)*1000000,20)
    tk=TickSeries(ts,px,vol.astype(float),px-1,px,np.arange(len(px),dtype=np.int64),.25,instrument='SYN',contract='SYN')
    return tk

def normalized(x):
    if isinstance(x,np.ndarray):return x.tolist()
    if isinstance(x,dict):return {k:normalized(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [normalized(v) for v in x]
    if isinstance(x,np.generic):return x.item()
    return x

class CaptureTests(unittest.TestCase):
    def test_bt2_native_outputs_unchanged_and_birth_copied(self):
        t=trap_tape();b=B.build_tick_bars(t,10);f=B.build_footprints(t,b)
        p={'use_wick_filter':False,'min_trap_volume':1,'imbalance_ratio':1.0,'max_age_bars':1}
        expected=bigtrap2.run(t,b,f,p);got,r=capture_run('BT2',t,bars=b,footprints=f,params=p)
        self.assertEqual(normalized(expected),normalized(got));self.assertTrue(any(x.kind=='BIRTH' for x in r.records));self.assertTrue(any(x.kind=='REMOVE' for x in r.records))
        frozen=r.records;got['zones'][0]['top']=999999;self.assertEqual(r.records,frozen)
        self.assertTrue(all(x.clock.ns==int(t.ts_ns[x.consumed_tick_index]) for x in r.records))
    def test_bt2a_native_outputs_unchanged_and_no_fill_required_for_birth(self):
        t=trap_tape();p={'TapeWindowTicks':10,'AbsorptionPct':0,'UseWickFilter':False,'ImbalanceRatio':1.0,'MinStackedRows':1,'MinTrapFrac':0,'RequireFlowSideMatch':False,'MaxAgeBars':1}
        expected=bigtrap2absorption.run(t,params=p);got,r=capture_run('BT2A',t,params=p)
        self.assertEqual(normalized(expected),normalized(got));self.assertTrue(any(x.kind=='BIRTH' for x in r.records));self.assertTrue(any(x.kind=='REMOVE' for x in r.records))
        self.assertTrue(all(x.clock.sequence==int(t.sequence[x.consumed_tick_index]) for x in r.records))
    def test_avz_birth_and_ob_classification_not_final_state(self):
        t=avz_tape();b=B.build_tick_bars(t,5);f=build_total_footprint_csr_nt8(t,b);ses=B.session_ids(b.end_ns)
        p={'window_bars':1,'min_samples':2,'lookback_sessions':3,'ob_bars':2,'racimo_min':0}
        expected=avz.run(b,f,ses,p);got,r=capture_run('AVZP2',t,bars=b,footprints=f,sessions=ses,params=p)
        self.assertEqual(normalized(expected),normalized(got));births=[x for x in r.records if x.kind=='BIRTH'];cls=[x for x in r.records if x.kind=='CLASSIFY'];self.assertTrue(births);self.assertTrue(cls)
        self.assertTrue(all(dict(x.properties)['state']==0 for x in births));self.assertTrue(all(dict(x.properties)['state']==1 for x in cls))
        for x in cls:
            birth=next(y for y in births if y.key==x.key);self.assertGreater(x.clock,birth.clock)
    def test_zero_ob_classification_is_same_clock_not_missing(self):
        t=avz_tape();b=B.build_tick_bars(t,5);f=build_total_footprint_csr_nt8(t,b);ses=B.session_ids(b.end_ns)
        p={'window_bars':1,'min_samples':2,'lookback_sessions':3,'ob_bars':0,'racimo_min':0}
        got,r=capture_run('AVZP2',t,bars=b,footprints=f,sessions=ses,params=p)
        self.assertEqual(normalized(avz.run(b,f,ses,p)),normalized(got))
        births={x.key:x for x in r.records if x.kind=='BIRTH'};cls=[x for x in r.records if x.kind=='CLASSIFY']
        self.assertTrue(births);self.assertEqual(len(births),len(cls))
        self.assertTrue(all(x.clock==births[x.key].clock for x in cls))
    def test_partial_tick_tail_waits_for_next_observation_or_unknown_eof(self):
        from tools.research_ops.confluence.detector_capture import _bar_availability
        t=make_synthetic(start_utc='2026-09-01T23:00:00',n_sessions=2,ticks_per_session=53,seed=4)
        b=B.build_tick_bars(t,10);a=_bar_availability(t,b)
        self.assertEqual(a[5][0],52);self.assertEqual(a[5][1].sequence,53)
        self.assertIsNone(a[-1])
    def test_shared_timestamp_uses_sequence_not_searchsorted_right(self):
        t=trap_tape(same_ns=True);p={'TapeWindowTicks':5,'AbsorptionPct':0,'UseWickFilter':False,'ImbalanceRatio':1.0,'MinStackedRows':1,'MinTrapFrac':0,'RequireFlowSideMatch':False}
        _,r=capture_run('BT2A',t,params=p);self.assertTrue(r.records)
        for x in r.records:self.assertEqual(x.clock.sequence,x.consumed_tick_index)
        self.assertTrue(any(x.consumed_tick_index<len(t)-1 and t.ts_ns[x.consumed_tick_index]==t.ts_ns[x.consumed_tick_index+1] for x in r.records))
    def test_immutable_receipt_even_after_native_zone_mutation(self):
        t=trap_tape();b=B.build_tick_bars(t,10);f=B.build_footprints(t,b);got,r=capture_run('BT2',t,bars=b,footprints=f,params={'use_wick_filter':False,'min_trap_volume':1,'imbalance_ratio':1.0})
        before=asdict(r)
        for z in got['zones']:z['state']='FAKE_FINAL';z['top']=123456
        self.assertEqual(asdict(r),before)
    def test_source_hash_drift_rejected(self):
        t=trap_tape()
        with patch.dict(PINS,{'BT2A':'0'*64}):
            with self.assertRaises(ValueError):capture_run('BT2A',t)
    def test_unknown_renderer_rejected(self):
        with self.assertRaises(ValueError):capture_run('BT2A',trap_tape(),params={'AutoScale':True})
    def test_capture_budget_no_partial_receipt(self):
        with self.assertRaises(ValueError):capture_run('BT2A',trap_tape(),params={'AbsorptionPct':0,'UseWickFilter':False,'MinStackedRows':1,'ImbalanceRatio':1,'MinTrapFrac':0,'RequireFlowSideMatch':False},max_records=1)
    def test_bad_sequence_rejected(self):
        t=trap_tape();t.sequence[5]=t.sequence[4]
        with self.assertRaises(ValueError):capture_run('BT2A',t)
    def test_missing_quotes_rejected_not_fabricated(self):
        t=trap_tape();t.ask_ticks=None
        with self.assertRaises(ValueError):capture_run('BT2A',t)
    def test_bar_mapping_not_uniform_formula(self):
        t=make_synthetic(start_utc='2026-09-01T23:00:00',n_sessions=2,ticks_per_session=53,seed=4);b=B.build_tick_bars(t,10);f=B.build_footprints(t,b)
        _,r=capture_run('BT2',t,bars=b,footprints=f,params={'use_wick_filter':False,'min_trap_volume':1,'imbalance_ratio':1})
        self.assertTrue(r.records)
        for x in r.records:self.assertEqual(int(b.tick_bar_idx[x.consumed_tick_index]),x.source_bar)
    def test_future_time_close_not_available_at_last_member(self):
        t=trap_tape(n=180);t.ts_ns=t.ts_ns[0]+np.arange(len(t),dtype=np.int64)*1000000000
        b=B.build_time_bars(t,1);f=B.build_footprints(t,b);_,r=capture_run('BT2',t,bars=b,footprints=f,params={'use_wick_filter':False,'min_trap_volume':1,'imbalance_ratio':1})
        self.assertEqual(r.availability_policy,'FIRST_OBSERVED_TICK_AT_OR_AFTER_TIME_CLOSE')
        for x in r.records:
            self.assertGreaterEqual(x.clock.ns,int(b.end_ns[x.source_bar]));self.assertGreater(x.clock.sequence,int(t.sequence[x.consumed_tick_index]))
        self.assertGreater(r.unavailable_time_events,0)
if __name__=='__main__':unittest.main()

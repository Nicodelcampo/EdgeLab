import hashlib
import json
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import unittest
import numpy as np
from edgelab.bridge import bars as B
from tools.research_ops.confluence.bt2a_stream import BT2AStream,TickChunk
from tools.research_ops.confluence.detector_capture import capture_run,PINS
from test_confluence_detector_capture import trap_tape

PERMISSIVE={'TapeWindowTicks':10,'AbsorptionPct':0,'UseWickFilter':False,'ImbalanceRatio':1.,'MinStackedRows':1,'MinTrapFrac':0,'RequireFlowSideMatch':False,'MaxAgeBars':1}
def chunk(t,start,end):
    fields=[getattr(t,k)[start:end] for k in ('ts_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence')]
    return TickChunk(*fields,B.session_ids(t.ts_ns[start:end]),start)

class BT2AStreamTests(unittest.TestCase):
    def compare(self,t,params,sizes):
        native,ref=capture_run('BT2A',t,params=params);s=BT2AStream(params=params,tick_size=t.tick_size,collect_diagnostics=True);rs=[];unavailable=0;pos=0;k=0
        while pos<len(t):
            end=min(len(t),pos+sizes[k%len(sizes)]);d=s.push(chunk(t,pos,end));rs.extend(d.records);unavailable+=d.unavailable_events
            self.assertLess(s.buffered_ticks,s.window);pos=end;k+=1
        d=s.finish();rs.extend(d.records);unavailable+=d.unavailable_events
        self.assertEqual(tuple(rs),ref.records);self.assertEqual(unavailable,ref.unavailable_time_events)
        h=hashlib.sha256();count=0
        for line in native['events']:
            _,_,kind,payload=line.split('|',3)
            if kind=='FILL':continue
            h.update(f'{kind}|{payload}\n'.encode());count+=1
        self.assertEqual(s.log_hash.hexdigest(),h.hexdigest());self.assertEqual(s.log_count,count)
        return s,rs
    def test_exact_receipts_and_scores_across_arbitrary_chunk_cuts(self):
        for sizes in ([1],[3,7,11],[10],[21],[1000]):self.compare(trap_tape(121),PERMISSIVE,sizes)
    def test_residual_session_roll_and_eof_preserve_availability(self):
        t=trap_tape(57);t.ts_ns[21:]+=86400000000000;t.ts_ns[44:]+=86400000000000
        s,rs=self.compare(t,PERMISSIVE,[8,14,2])
        r=next(x for x in rs if x.kind=='REMOVE' and x.consumed_tick_index==20)
        self.assertEqual(r.clock.sequence,21)
    def test_all_32_roster_configs_preserve_full_native_history(self):
        from tools.research_ops.confluence.pilot_runtime import synthetic_fixture
        roster=json.loads((Path(__file__).resolve().parents[2]/'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json').read_bytes());t,_=synthetic_fixture()
        for c in (c for c in roster['configs'] if c['indicator']=='bigtrap2absorption'):
            with self.subTest(config=c['config_sha256']):
                s,_=self.compare(t,c['params'],[997,211,1803]);self.assertEqual(s.config,c['config_sha256']);ses=B.session_ids(t.ts_ns);counts=np.diff(np.r_[0,np.flatnonzero(np.diff(ses))+1,len(t)]);expected=min(max(10,int(c['params']['AbsorptionLookback'])),sum(int(n)//max(2,int(c['params']['TapeWindowTicks'])) for n in counts));self.assertEqual(s.state_sizes()[0],expected)
    def test_shared_ns_uses_sequence(self):self.compare(trap_tape(121,same_ns=True),PERMISSIVE,[9,3,29])
    def test_abs_directional_samelevel_totallevel_and_lifetime_modes(self):
        for mode in ('None','CloseThrough','FirstTouch'):
            self.compare(trap_tape(151),{**PERMISSIVE,'ScoreMode':'AbsDirectional','ImbalanceMode':'SameLevel','TrapVolumeSource':'TotalLevel','InvalidationMode':mode,'MaxTouches':2},[17])
    def test_warmup_not_shortened(self):
        s,rs=self.compare(trap_tape(121),{**PERMISSIVE,'AbsorptionPct':90,'AbsorptionLookback':10,'MinHistoryBuckets':10},[9])
        self.assertTrue(rs);self.assertTrue(all(x.source_bar>10 for x in rs if x.kind=='BIRTH'))
    def test_buffer_owns_partial_data(self):
        t=trap_tape(20);a=BT2AStream(params=PERMISSIVE,tick_size=.25);b=BT2AStream(params=PERMISSIVE,tick_size=.25)
        c=chunk(t,0,3);c=replace(c,volume=c.volume.copy());self.assertEqual(a.push(c),b.push(chunk(t,0,3)));c.volume[:]=99999
        self.assertEqual(a.push(chunk(t,3,20)),b.push(chunk(t,3,20)));self.assertEqual(a.finish(),b.finish())
    def test_invalid_boundary_and_quote_rejected_before_mutation(self):
        t=trap_tape(20);s=BT2AStream(params=PERMISSIVE,tick_size=.25);s.push(chunk(t,0,3))
        with self.assertRaises(ValueError):s.push(chunk(t,0,3))
        c=chunk(t,3,10)
        with self.assertRaises(ValueError):s.push(replace(c,ask_ticks=np.zeros(7,dtype=np.int64)))
        self.assertFalse(s.poisoned);s.push(c)
    def test_native_window_not_shortened_for_budget(self):
        with self.assertRaises(ValueError):BT2AStream(params={'TapeWindowTicks':200},tick_size=.25,max_buffer_ticks=100)
    def test_capacity_failure_poisoned_no_truncation(self):
        t=trap_tape(41);s=BT2AStream(params={**PERMISSIVE,'InvalidationMode':'None','MaxAgeBars':0},tick_size=.25,max_active=1)
        with self.assertRaises(ValueError):s.push(chunk(t,0,41))
        self.assertTrue(s.poisoned)
        with self.assertRaises(ValueError):s.finish()
    def test_closed_and_immutable_params(self):
        s=BT2AStream(params=PERMISSIVE,tick_size=.25)
        with self.assertRaises(TypeError):s.params['AbsorptionPct']=50
        s.finish()
        with self.assertRaises(ValueError):s.push(chunk(trap_tape(10),0,10))
    def test_no_csv_fast_path_preserves_receipts(self):
        t=trap_tape(57);t.ts_ns[21:]+=86400000000000;_,ref=capture_run('BT2A',t,params=PERMISSIVE)
        s=BT2AStream(params=PERMISSIVE,tick_size=.25);rs=[];u=0
        for begin,end in ((0,9),(9,24),(24,57)):
            d=s.push(chunk(t,begin,end));rs.extend(d.records);u+=d.unavailable_events
        d=s.finish();rs.extend(d.records);u+=d.unavailable_events
        self.assertEqual(tuple(rs),ref.records);self.assertEqual(u,ref.unavailable_time_events);self.assertEqual(s.log_count,0)
    def test_history_budget_does_not_reduce_native_lookback(self):
        with self.assertRaises(ValueError):BT2AStream(params={'AbsorptionLookback':1000},tick_size=.25,max_history_values=500)
    def test_source_drift_rejected(self):
        with patch.dict(PINS,{'BT2A':'0'*64}):
            with self.assertRaises(ValueError):BT2AStream(params=PERMISSIVE,tick_size=.25)
if __name__=='__main__':unittest.main()

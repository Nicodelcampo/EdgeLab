"""Actual pinned detectors -> episodes/arrivals on a tiny invented tape."""
from dataclasses import replace
import unittest
from unittest.mock import patch
import numpy as np
from edgelab.bridge.ticks import TickSeries
from edgelab.bridge import bars as B
from tools.research_ops.confluence._pinned_total_footprint import build_total_footprint_csr_nt8
from tools.research_ops.confluence.detector_capture import capture_run
from tools.research_ops.confluence.replay import replay_declared

H='a'*64

def fixture():
    pattern=np.array([100,101,102,104,103]);px=np.tile(pattern,16);v=np.tile(np.array([1,1,1,100,100]),16).astype(float)
    base=np.datetime64('2026-09-01T14:00:00','ns').astype(np.int64)
    ts=np.repeat(base+np.arange(4,dtype=np.int64)*86400000000000,20)+np.tile(np.arange(20,dtype=np.int64)*1000000,4)
    t=TickSeries(ts,px,v,px-1,px,np.arange(80,dtype=np.int64),.25,instrument='SYN',contract='SYN')
    b=B.build_tick_bars(t,5);f=B.build_footprints(t,b);total=build_total_footprint_csr_nt8(t,b)
    _,bt=capture_run('BT2',t,bars=b,footprints=f,params={'use_wick_filter':False,'imbalance_ratio':1,'min_trap_volume':1})
    _,ba=capture_run('BT2A',t,params={'TapeWindowTicks':5,'AbsorptionPct':0,'UseWickFilter':False,'ImbalanceRatio':1,'MinStackedRows':1,'MinTrapFrac':0,'RequireFlowSideMatch':False})
    _,av=capture_run('AVZP2',t,bars=b,footprints=total,sessions=B.session_ids(b.end_ns),params={'window_bars':1,'min_samples':2,'lookback_sessions':3,'racimo_min':0,'ob_bars':2})
    dates=[f'2026-09-0{1+i//20}' for i in range(80)]
    return t,(bt,ba,av),dates
class PipelineTests(unittest.TestCase):
    def test_actual_detector_stream_produces_triples_and_arrivals(self):
        t,rs,dates=fixture();frames=list(replay_declared(t,rs,contract='SYN',tape_sha256=H,trade_dates=dates,racimo_params=[{'racimo_min':3,'racimo_bars':10,'racimo_altura_ticks':10}],window_ticks=3))
        es=[e for f in frames for e in f.episode_events];anchors=[a for f in frames for a in f.arrivals]
        self.assertTrue(es);self.assertTrue(any(len(e.episode.components)==3 for e in es));self.assertTrue(anchors);self.assertTrue(any(a.kind=='FIRST_OBSERVED_TOUCH' for a in anchors))
    def test_receipt_order_does_not_change_atomic_episode_outputs(self):
        t,rs,dates=fixture();kw=dict(contract='SYN',tape_sha256=H,trade_dates=dates,window_ticks=3)
        a=list(replay_declared(t,rs,**kw));b=list(replay_declared(t,rs[::-1],**kw));self.assertEqual(a,b)
    def test_missing_available_tape_record_rejected(self):
        t,rs,dates=fixture();r=rs[0];bad=replace(r,records=tuple(replace(x,clock=replace(x.clock,ns=x.clock.ns-1)) for x in r.records))
        with self.assertRaises(ValueError):list(replay_declared(t,[bad],contract='SYN',tape_sha256=H,trade_dates=dates))
    def test_global_known_identity_budget_stops_without_pruning(self):
        t,rs,dates=fixture()
        with self.assertRaisesRegex(ValueError,'known zone budget exceeded'):
            list(replay_declared(t,rs,contract='SYN',tape_sha256=H,trade_dates=dates,max_known_zones=1))
    def test_changed_carry_ends_primary_racimo_and_cannot_resurrect(self):
        from tools.research_ops.confluence.asof_intersections import ZoneKey,Snapshot
        from tools.research_ops.confluence.racimo_asof import RacimoObservation
        t,rs,dates=fixture();dates=['2026-09-01']*len(t)
        class ChangedOnly:
            def __init__(self,**kw):self.kw=kw;self.calls=0;self.born=None
            def observe_batch(self,zs):
                self.calls+=1;c=zs[0].available
                if self.calls>3:return ()
                if self.born is None:self.born=c
                key=ZoneKey('RACIMO',self.kw['config_sha256'],self.kw['build_sha256'],'0')
                snap=Snapshot(key,self.calls-1,c,self.born,200,208)
                carry=self.calls==2
                return (RacimoObservation(snap,('a','b'),('2026-08-31','2026-09-01') if carry else ('2026-09-01',),0,0,True,carry),)
        with patch('tools.research_ops.confluence.replay.RacimoTape',ChangedOnly):
            fs=list(replay_declared(t,rs,contract='SYN',tape_sha256=H,trade_dates=dates,racimo_params=[{'racimo_min':3,'racimo_bars':10,'racimo_altura_ticks':10}]))
        es=[e for f in fs for e in f.episode_events if any(s.key.family=='RACIMO' for s in e.episode.components)]
        self.assertTrue(any(e.action=='START' for e in es));self.assertTrue(any(e.action=='END' for e in es))
        ended=min(e.observed for e in es if e.action=='END')
        self.assertFalse(any(e.action=='START' and e.observed>ended for e in es))
        self.assertGreaterEqual(sum(f.scope_excluded_records for f in fs),2)
    def test_reserved_session_rejected(self):
        t,rs,dates=fixture();dates[-20:]=['2026-10-01']*20
        with self.assertRaises(ValueError):list(replay_declared(t,rs,contract='SYN',tape_sha256=H,trade_dates=dates))
    def test_no_retroactive_geometry_from_final_native_objects(self):
        t,rs,dates=fixture();frames=list(replay_declared(t,rs,contract='SYN',tape_sha256=H,trade_dates=dates));self.assertTrue(all(e.episode.recognized<=f.clock for f in frames for e in f.episode_events))
if __name__=='__main__':unittest.main()

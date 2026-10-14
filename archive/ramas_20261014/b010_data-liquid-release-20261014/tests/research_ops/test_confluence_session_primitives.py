import unittest
import numpy as np
from dataclasses import replace
from edgelab.bridge import bars as B
from edgelab.bridge.ticks import TickSeries
from tools.research_ops.confluence.session_primitives import SessionPrimitives,SessionTape
from tools.research_ops.confluence.asof_intersections import Clock
from tools.research_ops.confluence._pinned_total_footprint import build_total_footprint_csr_nt8
from tools.research_ops.confluence.detector_capture import _bar_availability
from test_confluence_detector_capture import trap_tape

class PrimitiveTests(unittest.TestCase):
    def compare(self,t,spec):
        kind,size=spec.split(':');size=int(size);b=B.build_tick_bars(t,size) if kind=='tick' else B.build_time_bars(t,size);f=B.build_footprints(t,b);total=build_total_footprint_csr_nt8(t,b);clocks=_bar_availability(t,b)
        ss=B.session_ids(t.ts_ns);edges=np.r_[0,np.flatnonzero(np.diff(ss))+1,len(t)];engine=SessionPrimitives();bt=[];av=[]
        for start,end in zip(edges[:-1],edges[1:]):
            start=int(start);end=int(end);sub=TickSeries(*(getattr(t,k)[start:end] for k in ('ts_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence')),t.tick_size)
            following=Clock(int(t.ts_ns[end]),int(t.sequence[end])) if end<len(t) else None
            engine.begin(SessionTape(sub,start,following,int(ss[start])));x,y=engine.build(spec);bt.extend(x);av.extend(y);engine.end()
        self.assertEqual(len(bt),len(b));self.assertEqual(len(av),len(b))
        for i,(x,y) in enumerate(zip(bt,av)):
            self.assertEqual(x.ask,f.ask[i]);self.assertEqual(x.bid,f.bid[i]);self.assertEqual(x.n_quote,int(f.n_quote[i]));self.assertEqual(x.n_rule,int(f.n_rule[i]));self.assertEqual(x.low_t,int(b.low_t[i]));self.assertEqual(x.high_t,int(b.high_t[i]));self.assertEqual(x.close_t,int(b.close_t[i]));self.assertEqual(x.volume,float(b.volume[i]));self.assertEqual(x.available,clocks[i][1] if clocks[i] else None)
            ts,vs=total.bar_cells(i);np.testing.assert_array_equal(y.levels,ts);np.testing.assert_array_equal(y.volumes,vs)
        return bt,av
    def tape(self,same_ns=False):
        t=trap_tape(157,same_ns=same_ns);t.ts_ns[53:]+=86400000000000;t.ts_ns[106:]+=86400000000000;return t
    def test_all_pilot_specs_match_native_across_session_residuals(self):
        for spec in ('tick:25','tick:50','tick:100','tick:200','time:1'):self.compare(self.tape(),spec)
    def test_total_multi_close_cohort_and_cross_session_carry(self):
        for spec in ('tick:2','tick:5','tick:25'):self.compare(self.tape(True),spec)
    def test_global_tickrule_fallback_survives_session_boundary(self):
        t=self.tape();t.bid_ticks[:]=t.price_ticks-10;t.ask_ticks[:]=t.price_ticks+10
        t.price_ticks[52:57]=t.price_ticks[52]
        self.compare(t,'tick:25')
    def test_no_silent_clip_of_long_timestamp_cohort(self):
        t=trap_tape(21,same_ns=True);t.ts_ns[:]=t.ts_ns[0];p=SessionPrimitives(max_same_ns=10)
        with self.assertRaises(ValueError):p.begin(SessionTape(t,0,None,int(B.session_ids(t.ts_ns)[0])))
    def test_fractional_volume_not_mislabeled_exact(self):
        t=trap_tape(21);t.volume[0]=.1;p=SessionPrimitives()
        with self.assertRaises(ValueError):p.begin(SessionTape(t,0,None,int(B.session_ids(t.ts_ns)[0])))
    def test_spec_reused_by_all_configs_not_built_twice(self):
        t=trap_tape(21);p=SessionPrimitives();p.begin(SessionTape(t,0,None,int(B.session_ids(t.ts_ns)[0])));p.build('tick:25')
        with self.assertRaises(ValueError):p.build('tick:25')
if __name__=='__main__':unittest.main()

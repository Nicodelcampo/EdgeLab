import tempfile,unittest
from pathlib import Path
from itertools import groupby
import numpy as np
from edgelab.bridge import bars as B
from tools.research_ops.confluence.geometry_replay import GeometryReplay
from tools.research_ops.confluence.replay import replay_declared
from tools.research_ops.confluence.kaggle_session_reader import iter_sessions,HOLDOUT_NS
from test_confluence_detector_pipeline import fixture,H

class PlumbingTests(unittest.TestCase):
    def test_geometry_actor_identical_to_original_episode_replay(self):
        t,rs,dates=fixture();params=[{'racimo_min':3,'racimo_bars':10,'racimo_altura_ticks':10}];expected=list(replay_declared(t,rs,contract='SYN',tape_sha256=H,trade_dates=dates,racimo_params=params))
        records=sorted([x for r in rs for x in r.records],key=lambda x:x.clock);batches={c:tuple(g) for c,g in groupby(records,key=lambda x:x.clock)};actor=GeometryReplay(contract='SYN',tape_sha256=H,racimo_params=params)
        for frame in expected:
            if actor.session!=frame.trade_date:actor.begin_session(frame.trade_date)
            group=batches.get(frame.clock,())
            ev,excluded=actor.apply(frame.clock,group,origin_date=lambda x:dates[x.consumed_tick_index])
            self.assertEqual(ev,frame.episode_events);self.assertEqual(excluded,frame.scope_excluded_records)
    def write(self,path):
        import pyarrow as pa,pyarrow.parquet as pq
        t,_,_=fixture();pq.write_table(pa.table({k:pa.array(v) for k,v in zip(('ts_utc_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence'),(t.ts_ns,t.price_ticks,t.volume,t.bid_ticks,t.ask_ticks,t.sequence))}),path,row_group_size=11);return t
    def test_parquet_batches_preserve_natural_sessions_and_next_clock(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'invented.parquet';t=self.write(p);sessions=list(iter_sessions(p,start_ns=int(t.ts_ns[0]),end_ns=int(t.ts_ns[-1])+1,batch_size=7))
            self.assertEqual(len(sessions),4);np.testing.assert_array_equal(np.concatenate([s.ticks.ts_ns for s in sessions]),t.ts_ns)
            self.assertEqual([s.first_index for s in sessions],[0,20,40,60]);self.assertEqual(sessions[0].next_clock.sequence,20);self.assertIsNone(sessions[-1].next_clock)
    def test_holdout_blocked_before_open(self):
        with self.assertRaises(ValueError):list(iter_sessions('/does/not/exist',start_ns=1,end_ns=HOLDOUT_NS+1))
    def test_range_exceeding_budget_fails_not_truncates(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'invented.parquet';t=self.write(p)
            with self.assertRaisesRegex(ValueError,'budget'):list(iter_sessions(p,start_ns=int(t.ts_ns[0]),end_ns=int(t.ts_ns[-1])+1,max_total_ticks=10))
if __name__=='__main__':unittest.main()

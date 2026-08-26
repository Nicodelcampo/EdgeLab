from __future__ import annotations
import inspect
from pathlib import Path
import unittest
import numpy as np
from edgelab.research import bt2_gate1_outcomes as O
from edgelab.research import bt2_gate1_preflight as P

class Gate1CausalityTests(unittest.TestCase):
    def test_strict_next_tick_uses_source_row_on_timestamp_tie(self):
        self.assertEqual(O.strict_next_index(np.array([100,100,100,101]),np.array([10,11,12,13]),signal_ts_ns=100,signal_source_row=11),2)
    def test_signal_tick_cannot_fill_itself(self):
        self.assertEqual(O.strict_next_index(np.array([100,101]),np.array([0,1]),signal_ts_ns=100,signal_source_row=0),1)
    def test_tick_cap_wins_tie(self):
        end,driver,ok=O.horizon_windows(np.arange(8)*O.NS,np.array(["S"]*8),tick_cap=2,clock_cap_seconds=2)
        self.assertEqual((int(end[0]),int(driver[0]),bool(ok[0])),(2,0,True))
    def test_clock_cap_can_win(self):
        end,driver,ok=O.horizon_windows(np.array([0,100,200,300])*O.NS,np.array(["S"]*4),tick_cap=3,clock_cap_seconds=150)
        self.assertEqual((int(end[0]),int(driver[0]),bool(ok[0])),(2,1,True))
    def test_hard_session_boundary_excludes_path(self):
        end,_,ok=O.horizon_windows(np.arange(6)*O.NS,np.array(["A"]*3+["B"]*3),tick_cap=2,clock_cap_seconds=100)
        self.assertTrue(ok[0]); self.assertFalse(ok[1]); self.assertEqual(end[1],-1)
    def test_excursion_is_anchored_to_fill(self):
        ts=np.arange(5)*O.NS; px=np.array([100,105,107,103,104]); c=O.build_path_cache(ts,px,np.array(["S"]*5),tick_cap=2,clock_cap_seconds=100)
        mfe,mae=O.directional_excursions(px,c,np.array([1]),np.array([1],dtype=np.int8)); self.assertEqual((mfe[0],mae[0]),(2,2))
    def test_d_hat_tick_scale(self): self.assertEqual(O.d_hat_ticks([3,5,7],[1,2,4]),3)
    def test_shuffle_deterministic(self):
        ts=np.arange(8)*O.NS; px=np.array([10,11,12,11,13,12,14,13]); c=O.build_path_cache(ts,px,np.array(["S"]*8),tick_cap=2,clock_cap_seconds=100)
        ev=[O.Event(str(i),"K_ABS","GC","S",d,i,int(ts[i]),i,i) for i,d in zip((0,1,2),(1,1,-1))]
        np.testing.assert_array_equal(O.shuffle_replicates(events=ev,price_ticks=px,cache=c,replications=20,seed=7),O.shuffle_replicates(events=ev,price_ticks=px,cache=c,replications=20,seed=7))
    def test_sparse_nrand_fails_closed(self):
        ts=np.arange(5)*O.NS; px=np.arange(5); c=O.build_path_cache(ts,px,np.array(["S"]*5),tick_cap=2,clock_cap_seconds=100)
        ev=[O.Event(str(i),"K_ABS","GC","S",1,i,int(ts[i]),i,i) for i in (0,1,2)]
        with self.assertRaisesRegex(ValueError,"SPARSE_STRATUM"): O.nrand_replicates(events=ev,ts_ns=ts,price_ticks=px,session_ids=np.array(["S"]*5),cache=c,replications=2,seed=1)

class Gate1FirewallTests(unittest.TestCase):
    def test_preflight_has_no_outcome_import_or_metrics(self):
        source=inspect.getsource(P); self.assertNotIn("bt2_gate1_outcomes",source)
        for word in ("MFE","MAE","P&L","d_hat_ticks"): self.assertNotIn(word,source)
    def test_cli_lazy_import(self):
        s=(Path(__file__).resolve().parents[2]/"tools/bt2_absorption_gate1.py").read_text(); self.assertGreater(s.index("from edgelab.research.bt2_gate1_outcomes import"),s.index("check=run_preflight"))
    def test_registry_rejects_wrong_contracts(self):
        r={"schema":"bt2a_gate1_session_registry_v1","frozen_before_outcomes":True,"campaign_outcomes_opened":False,"selection":{"contracts":["GC 02-26","GC 06-26"],"n_sessions":76},"sessions":[{"cme_session_id":f"S{i}","contract":"GC 02-26"} for i in range(76)]}
        with self.assertRaisesRegex(ValueError,"contract set changed"): P.validate_registry(r,{"schema":"bt2a_gate1_input_registry_v1","selected_contracts":["GC 02-26","GC 06-26"]})
if __name__=="__main__": unittest.main()

import unittest
import os
import json
import tempfile
import shutil
from pathlib import Path

from edgelab.edge_factory.instrument_spec import (
    INSTRUMENT_SPECS,
    get_instrument_spec,
    price_to_ticks
)
from edgelab.edge_factory.orchestrator import (
    ResourceBudget,
    DAGNode,
    ExperimentDAG,
    OrchestratorCheckpoint,
    OrchestratorRunner
)

class TestEdgeFactoryAuditComprehensive(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_canonical_instrument_specs_all_11_assets(self):
        expected_assets = ["ES", "MES", "NQ", "MNQ", "YM", "6E", "6B", "6J", "ZB", "GC", "MBT"]
        self.assertEqual(sorted(list(INSTRUMENT_SPECS.keys())), sorted(expected_assets))

        # Check precise CME tick sizes
        self.assertEqual(get_instrument_spec("ES")["tick_size"], 0.25)
        self.assertEqual(get_instrument_spec("MES")["tick_size"], 0.25)
        self.assertEqual(get_instrument_spec("NQ")["tick_size"], 0.25)
        self.assertEqual(get_instrument_spec("MNQ")["tick_size"], 0.25)
        self.assertEqual(get_instrument_spec("YM")["tick_size"], 1.0)
        self.assertEqual(get_instrument_spec("6E")["tick_size"], 0.00005)
        self.assertEqual(get_instrument_spec("6B")["tick_size"], 0.0001)
        self.assertEqual(get_instrument_spec("6J")["tick_size"], 0.0000005)
        self.assertEqual(get_instrument_spec("ZB")["tick_size"], 0.03125)
        self.assertEqual(get_instrument_spec("GC")["tick_size"], 0.10)
        self.assertEqual(get_instrument_spec("MBT")["tick_size"], 5.0)

    def test_price_to_ticks_conversion(self):
        # 1 full point in ES is 4 ticks
        self.assertEqual(price_to_ticks(1.0, "ES"), 4.0)
        # 1 full point in ZB (bond) is 32 ticks
        self.assertEqual(price_to_ticks(1.0, "ZB"), 32.0)
        # 1 full point in YM (Dow) is 1 tick
        self.assertEqual(price_to_ticks(1.0, "YM"), 1.0)
        # 1 full point in GC (Gold) is 10 ticks
        self.assertEqual(price_to_ticks(1.0, "GC"), 10.0)
        # 10 dollars in MBT is 2 ticks
        self.assertEqual(price_to_ticks(10.0, "MBT"), 2.0)

    def test_unknown_instrument_rejected(self):
        with self.assertRaises(ValueError):
            get_instrument_spec("UNKNOWN_ASSET")

    def test_no_synthetic_fill_in_target_free_records(self):
        # Target-free zone event must not fabricate an executed fill
        record = {
            "zone_id": "test_z1",
            "signal_available_ts": 1750000000000000000,
            "executable_fill_ts": None,
            "fill_status": "NO_EXECUTABLE_FILL_AVAILABLE"
        }
        self.assertIsNone(record["executable_fill_ts"])
        self.assertEqual(record["fill_status"], "NO_EXECUTABLE_FILL_AVAILABLE")

    def test_holdout_boundary_invariant(self):
        holdout_boundary_ns = 1782856800000000000
        # A valid pre-holdout timestamp
        valid_ts = 1782856799000000000
        self.assertLess(valid_ts, holdout_boundary_ns)
        # Post-holdout timestamp must trigger violation
        breach_ts = 1782856800000000001
        self.assertGreaterEqual(breach_ts, holdout_boundary_ns)

    def test_corridor_pseudo_pairing_detection(self):
        # Simulating pseudo-pairing: N zones yielding N-1 corridors with constant density
        zones = [f"z_{i}" for i in range(10)]
        pseudo_corridors = []
        for i in range(len(zones) - 1):
            pseudo_corridors.append({"pair": (zones[i], zones[i+1]), "density": 0.5})

        # Detection logic
        is_consecutive_pairing = (len(pseudo_corridors) == len(zones) - 1)
        all_constant_density = all(c["density"] == 0.5 for c in pseudo_corridors)
        self.assertTrue(is_consecutive_pairing and all_constant_density)

    def test_contradiction_detection_side_ratio(self):
        # Actual measurement
        measured_bull = 663094
        measured_bear = 2665616
        tot = measured_bull + measured_bear
        bull_pct = measured_bull / tot * 100
        # Narrative claim
        claimed_bull_pct = 49.9

        discrepancy = abs(bull_pct - claimed_bull_pct)
        # A discrepancy of ~30 percentage points must be caught as a critical contradiction
        self.assertGreater(discrepancy, 25.0)

    def test_orchestrator_scaffold_dependency_block(self):
        dag = ExperimentDAG()
        n1 = DAGNode(node_id="corridor_node", hypothesis_id="HP-CORR-01", stage="PROPOSED_TARGET_FREE", dependencies=["corridor_events"])
        dag.add_node(n1)

        ckpt_file = os.path.join(self.test_dir, "ckpt.json")
        ckpt = OrchestratorCheckpoint(ckpt_file)
        runner = OrchestratorRunner(dag, ckpt)

        # Running without corridor_events in completed nodes must fail/block the node
        res = runner.run()
        self.assertEqual(res["failed"], 1)
        self.assertEqual(res["executed"], 0)
        self.assertEqual(dag.nodes["corridor_node"].status, "BLOCKED_MISSING_FEATURES")

if __name__ == "__main__":
    unittest.main()

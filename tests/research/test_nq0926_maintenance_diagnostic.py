import unittest
import numpy as np
from edgelab.research.nq0926_maintenance_diagnostic import (
    MaintenanceAccumulator, flattened_minute_rows)


class MaintenanceDiagnosticTests(unittest.TestCase):
    def test_groups_anomaly_without_guessing_cause(self):
        acc = MaintenanceAccumulator()
        acc.update(ts_utc_ns=np.array([10, 20, 30]),
            ts_local_ns=np.array([10, 20, 30]), sequence=np.array([1, 2, 3]),
            volume=np.array([1, 2, 3]), source_file=np.array(["a", "a", "b"]),
            source_row=np.array([100, 101, 200]),
            trade_date=np.array([20260629, 20260629, 20260630]),
            minute_since_open=np.array([1379, 1380, 1439]),
            maintenance_mask=np.array([False, True, True]))
        got = acc.finalize()
        self.assertEqual(got["maintenance_tick_count"], 2)
        self.assertEqual(got["maintenance_volume"], 5)
        self.assertEqual(got["root_cause_status"], "UNRESOLVED")
        self.assertEqual(got["per_trade_date"][0]["source_row_min"]["a"], 101)
        self.assertEqual(len(flattened_minute_rows(got)), 2)

    def test_tracks_local_utc_field_delta(self):
        acc = MaintenanceAccumulator()
        acc.update(ts_utc_ns=np.array([1, 2]), ts_local_ns=np.array([11, 12]),
            sequence=np.array([1, 2]), volume=np.array([1, 1]),
            source_file=np.array(["a", "a"]), source_row=np.array([1, 2]),
            trade_date=np.array([20260630, 20260630]),
            minute_since_open=np.array([1380, 1381]),
            maintenance_mask=np.array([True, True]))
        self.assertEqual(acc.finalize()["ts_local_minus_ts_utc_ns"], {"10": 2})

    def test_no_ticks_is_completed_not_error(self):
        acc = MaintenanceAccumulator()
        got = acc.finalize()
        self.assertEqual(got["status"], "COMPLETE_NO_MAINTENANCE_TICKS")


if __name__ == "__main__":
    unittest.main()

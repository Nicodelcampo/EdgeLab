import os
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from avzp2_pnl_sim import simulate_bracket, require_approval  # noqa: E402


def mk(prices, spread=1):
    p = np.asarray(prices, float)
    ts = np.arange(len(p), dtype=np.int64) * 1000
    return ts, p, p - spread / 2, p + spread / 2


class Bracket(unittest.TestCase):
    def test_long_tp_requiere_cruce(self):
        ts, last, bid, ask = mk([100, 100, 101, 102, 103, 104, 105])
        r = simulate_bracket(ts, last, bid, ask, entry_ns=0, side=1, tp=3, sl=3, max_ns=10**9)
        # entrada: primer tick posterior a 0 => idx1, ask=100.5; tp=103.5: last>103.5 recién en 104 (idx5)
        self.assertEqual(r["reason"], "TP"); self.assertAlmostEqual(r["gross"], 3.0)

    def test_toque_exacto_no_llena(self):
        ts, last, bid, ask = mk([100, 100, 101, 102, 103.5, 103.5, 103.5])
        r = simulate_bracket(ts, last, bid, ask, 0, 1, 3, 3, 10**9)
        self.assertEqual(r["reason"], "NO_EXIT_IN_DATA")

    def test_long_sl_con_slippage_y_gap(self):
        ts, last, bid, ask = mk([100, 100, 99, 95, 95])
        r = simulate_bracket(ts, last, bid, ask, 0, 1, 10, 3, 10**9, slip_stop=1.0)
        # entry 100.5, sl lvl 97.5; primer last<=97.5 es 95 (gap) => fill 95-1=94 => gross -6.5
        self.assertEqual(r["reason"], "SL"); self.assertAlmostEqual(r["gross"], -6.5)

    def test_short_simetrico(self):
        ts, last, bid, ask = mk([100, 100, 99, 98, 96])
        r = simulate_bracket(ts, last, bid, ask, 0, -1, 3, 3, 10**9)
        # entry short = bid idx1 = 99.5; tp lvl 96.5; last<96.5 en 96 => fill 96.5 => +3
        self.assertEqual(r["reason"], "TP"); self.assertAlmostEqual(r["gross"], 3.0)

    def test_time_stop_sale_a_mercado_y_costo(self):
        ts, last, bid, ask = mk([100, 100, 100, 100, 100, 100])
        r = simulate_bracket(ts, last, bid, ask, 0, 1, 10, 10, max_ns=3000, comm_ticks=0.4)
        self.assertEqual(r["reason"], "TIME"); self.assertAlmostEqual(r["gross"], -1.0); self.assertAlmostEqual(r["net"], -1.4)

    def test_sin_datos(self):
        ts, last, bid, ask = mk([100, 100])
        self.assertEqual(simulate_bracket(ts, last, bid, ask, 0, 1, 3, 3, 10**9)["reason"], "NO_DATA")

    def test_runner_exige_aprobacion(self):
        os.environ.pop("NICO_PNL_OK", None)
        with self.assertRaises(SystemExit):
            require_approval(__file__)


if __name__ == "__main__":
    unittest.main()

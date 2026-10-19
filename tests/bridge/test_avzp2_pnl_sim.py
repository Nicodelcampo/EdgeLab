import os
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from avzp2_pnl_sim import simulate_bracket, require_approval, run_events, summarize, select_events  # noqa: E402


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


class Runner(unittest.TestCase):
    def test_run_events_y_resumen_sinteticos(self):
        import pandas as pd
        ts, last, bid, ask = mk([100, 100, 101, 102, 103, 104, 105, 104, 100, 96, 95, 95])
        ev = pd.DataFrame([dict(cell="c", contract="X", session=1, t0=0, te_end_ns=0, dir=1),
                           dict(cell="c", contract="X", session=1, t0=1, te_end_ns=7000, dir=1),
                           dict(cell="c", contract="X", session=2, t0=2, te_end_ns=0, dir=1)])
        loader = lambda c, s: (ts, last, bid, ask) if s == 1 else (ts[:2], last[:2], bid[:2], ask[:2])
        res = run_events(ev, loader, dict(tp=3, sl=3, slip_stop=0.0, comm_ticks=0.5, max_seconds=100))
        self.assertEqual(res.reason.tolist(), ["TP", "SL", "NO_DATA"])
        sm = summarize(res)
        self.assertEqual(sm["n_eventos"], 3); self.assertEqual(sm["n_operaciones"], 2)
        self.assertAlmostEqual(sm["tasa_tp"], 0.5)

    def test_select_events_solo_a_favor_y_con_salida(self):
        import pandas as pd
        t = pd.DataFrame(dict(cell=["c"] * 4, contract=["X"] * 4, kind=["real", "real", "pseudo", "real"], t0=[1, 2, 3, 4],
                              te=[5, 6, 7, -1], trend=[1, 1, 1, 1], dir=[1, -1, 1, 1]))
        self.assertEqual(select_events(t, ["c"]).t0.tolist(), [1])


    def test_quote_centinela_no_corrompe_salida_ni_entrada(self):
        ts, last, bid, ask = mk([100, 100, 100, 100, 100])
        ask_bad = ask.copy(); ask_bad[1] = float(1 << 40)
        self.assertEqual(simulate_bracket(ts, last, bid, ask_bad, 0, 1, 5, 5, 10**9)["reason"], "NO_QUOTE")
        bid_bad = bid.copy(); bid_bad[3] = -1.0              # el tick del vencimiento no tiene quote: sale en el siguiente VÁLIDO (no a -1)
        r = simulate_bracket(ts, last, bid_bad, ask, 0, 1, 10, 10, max_ns=3000)
        self.assertEqual(r["reason"], "TIME"); self.assertEqual(r["exit_idx"], 4)
        self.assertTrue(np.isfinite(r["gross"]) and r["gross"] > -5)
        bid_all_bad = bid.copy(); bid_all_bad[3:] = -1.0     # no hay ningún quote válido en o después del vencimiento
        r2 = simulate_bracket(ts, last, bid_all_bad, ask, 0, 1, 10, 10, max_ns=3000)
        self.assertEqual(r2["reason"], "NO_QUOTE_EXIT"); self.assertTrue(np.isnan(r2["gross"]))

    def test_session_end_usa_el_ultimo_quote_valido(self):
        ts, last, bid, ask = mk([100, 100, 101, 101, 101, 101])
        bid_bad = bid.copy(); bid_bad[5] = -1.0              # el último tick de la sesión no tiene quote
        r = simulate_bracket(ts, last, bid_bad, ask, 0, 1, 10, 10, max_ns=10**9, close_at_session_end=True)
        self.assertEqual(r["reason"], "SESSION_END"); self.assertEqual(r["exit_idx"], 4)

    def test_close_at_session_end_y_no_overlap(self):
        import pandas as pd
        ts, last, bid, ask = mk([100, 100, 101, 101, 101, 101])
        r = simulate_bracket(ts, last, bid, ask, 0, 1, 10, 10, max_ns=10**9, close_at_session_end=True)
        self.assertEqual(r["reason"], "SESSION_END")
        self.assertTrue(np.isfinite(r["gross"]))
        ev = pd.DataFrame([
            dict(cell="c", contract="X", session=1, t0=0, te_end_ns=0, dir=1),
            dict(cell="c", contract="X", session=1, t0=1, te_end_ns=1000, dir=1),
        ])
        res = run_events(ev, lambda c, s: (ts, last, bid, ask),
                         dict(tp=10, sl=10, slip_stop=0.0, comm_ticks=0.0, max_seconds=100, close_at_session_end=True, no_overlap=True))
        self.assertEqual(res.reason.tolist(), ["SESSION_END", "SKIPPED_OVERLAP"])
        sm = summarize(res)
        self.assertEqual(sm["n_operaciones"], 1)


if __name__ == "__main__":
    unittest.main()

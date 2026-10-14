import unittest

import pandas as pd

from edgelab.data.liquid_release.calendar_derive import derive_calendar, session_days

# lunes 5-ene-2026 ... viernes 16-ene; sábado/domingo no entran porque no tienen datos
DAYS = [20260105, 20260106, 20260107, 20260108, 20260109, 20260112, 20260113, 20260114, 20260115, 20260116]


def _daily(spec):
    rows = []
    for inst, vols in spec.items():
        for d, v in zip(DAYS, vols):
            if v is not None:
                rows.append((inst, d, v))
    return pd.DataFrame(rows, columns=["instrument", "trade_date", "vol"])


class DeriveCalendar(unittest.TestCase):
    def test_feriado_vs_export_faltante_vs_corta(self):
        base = [1000] * 10
        es = list(base); es[3] = None              # sin datos el jue 8 y los pares sí operaron -> export faltante
        nq = list(base); nq[3] = 1000
        gc = list(base); gc[3] = 1000
        zb = list(base); zb[3] = 1000
        # jue 15: todos sin datos -> feriado; vie 16: ES corta (30 %)
        for lst in (es, nq, gc, zb):
            lst[8] = None
        es[9] = 300
        cal = derive_calendar(_daily({"ES": es, "NQ": nq, "GC": gc, "ZB": zb}), window=4).set_index(["instrument", "trade_date"])
        self.assertEqual(cal.loc[("ES", 20260108), "status"], "MISSING_EXPORT")
        self.assertEqual(cal.loc[("NQ", 20260108), "status"], "OPEN")
        self.assertNotIn(20260115, session_days(cal.reset_index(), "ES"))    # nadie operó: no es sesión
        self.assertEqual(cal.loc[("ES", 20260116), "status"], "SHORT")

    def test_d_menos_1_no_salta_un_export_faltante_como_si_fuera_feriado(self):
        base = [1000] * 10
        es = list(base); es[3] = None
        others = {k: list(base) for k in ("NQ", "GC", "ZB")}
        cal = derive_calendar(_daily({"ES": es, **others}), window=4)
        self.assertIn(20260108, session_days(cal, "ES"))      # MISSING_EXPORT sigue siendo sesión de calendario
        es2 = list(base); es2[3] = None
        cal2 = derive_calendar(_daily({"ES": es2, "NQ": [None if i == 3 else 1000 for i in range(10)],
                                        "GC": [None if i == 3 else 1000 for i in range(10)],
                                        "ZB": [None if i == 3 else 1000 for i in range(10)]}), window=4)
        self.assertNotIn(20260108, session_days(cal2, "ES"))  # si todos faltan, es feriado


if __name__ == "__main__":
    unittest.main()

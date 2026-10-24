import unittest

import pandas as pd

from edgelab.data.liquid_release.selection import (NO_ELIGIBLE, OK, SELECTED, UNDETERMINED, UNKNOWN, LiquidityPolicy,
                                                   contract_rank, select_sessions)

POL = LiquidityPolicy("t1", min_prev_volume=1000, min_prev_ticks=100, max_prev_spread_p50_ticks=4)
DAYS = [20260105, 20260106, 20260107, 20260108, 20260109]


def census(rows):
    return pd.DataFrame(rows, columns=["contract", "trade_date", "vol", "n", "spread_p50", "coverage"])


def both(d, a, b, cov="OK"):
    return [("ES 03-26", d, a, 500, 1, cov), ("ES 06-26", d, b, 500, 1, cov)]


class Selection(unittest.TestCase):
    def test_rank(self):
        self.assertLess(contract_rank("ES 12-25"), contract_rank("ES 03-26"))

    def test_elige_mayor_volumen_de_d_menos_1_y_el_roll_es_monotono(self):
        rows = []
        for d, (a, b) in zip(DAYS, [(5000, 100), (4000, 3000), (2000, 6000), (9000, 5000), (100, 7000)]):
            rows += both(d, a, b)
        r = select_sessions(census(rows), DAYS, POL).set_index("trade_date")
        self.assertEqual(r.loc[20260106, "contract"], "ES 03-26")     # D-1 = 05: 5000 vs 100
        self.assertEqual(r.loc[20260108, "contract"], "ES 06-26")     # D-1 = 07: 2000 vs 6000
        self.assertEqual(r.loc[20260109, "contract"], "ES 06-26")     # D-1 = 08: 9000 vs 5000 -> pero no se vuelve atrás
        self.assertTrue((r["status"] == SELECTED).all())

    def test_el_dia_de_s_no_influye(self):
        rows = []
        for d in DAYS:
            rows += both(d, 5000, 100)
        base = select_sessions(census(rows), DAYS, POL)
        mut = [list(x) for x in rows]
        for x in mut:
            if x[1] >= 20260108:                                       # mutar S=08 y posteriores
                x[2] = 10 ** 7 if x[0] == "ES 06-26" else 1
        m = select_sessions(census([tuple(x) for x in mut]), DAYS, POL)
        # la decisión de las sesiones hasta 08 sólo depende de D-1 <= 07: idénticas
        self.assertEqual(base.loc[base.trade_date <= 20260108, "contract"].tolist(),
                         m.loc[m.trade_date <= 20260108, "contract"].tolist())

    def test_cobertura_desconocida_bloquea_no_deja_ganar_al_disponible(self):
        rows = both(20260105, 5000, 100)
        rows += [("ES 03-26", 20260106, 5000, 500, 1, OK)]             # el competidor no tiene fila el 06
        rows += [("ES 06-26", 20260107, 100, 500, 1, OK), ("ES 03-26", 20260107, 5000, 500, 1, OK)]
        r = select_sessions(census(rows), DAYS[:4], POL).set_index("trade_date")
        self.assertEqual(r.loc[20260107, "status"], UNDETERMINED)      # D-1 = 06 sin ES 06-26 (existe antes y después)

    def test_competidor_lejano_sin_dato_no_bloquea_pero_deja_la_suposicion_escrita(self):
        rows = [("ES 03-26", d, 5000, 500, 1, OK) for d in DAYS[:3]]
        rows += [("ES 06-26", 20260105, 10, 5, 1, OK), ("ES 06-26", 20260107, 10, 5, 1, OK)]    # sin fila el 06; vol reciente 10 << 1 % de 5000
        r = select_sessions(census(rows), DAYS[:3], POL).set_index("trade_date")
        self.assertEqual(r.loc[20260107, "status"], SELECTED)
        self.assertIn("ES 06-26", r.loc[20260107, "assumptions"])

    def test_competidor_con_volumen_reciente_alto_sin_dato_si_bloquea(self):
        rows = [("ES 03-26", d, 5000, 500, 1, OK) for d in DAYS[:3]]
        rows += [("ES 06-26", 20260105, 4000, 500, 1, OK), ("ES 06-26", 20260107, 4000, 500, 1, OK)]
        r = select_sessions(census(rows), DAYS[:3], POL).set_index("trade_date")
        self.assertEqual(r.loc[20260107, "status"], UNDETERMINED)

    def test_sin_elegible_no_hay_fallback(self):
        rows = both(20260105, 10, 10) + both(20260106, 10, 10)
        r = select_sessions(census(rows), DAYS[:2], POL)
        self.assertEqual(r.iloc[0]["status"], NO_ELIGIBLE)
        self.assertIsNone(r.iloc[0]["contract"])

    def test_spread_alto_excluye(self):
        rows = [("ES 03-26", 20260105, 5000, 500, 9, OK), ("ES 06-26", 20260105, 2000, 500, 2, OK),
                ("ES 03-26", 20260106, 1, 1, 1, OK), ("ES 06-26", 20260106, 1, 1, 1, OK)]
        r = select_sessions(census(rows), DAYS[:2], POL)
        self.assertEqual(r.iloc[0]["contract"], "ES 06-26")


if __name__ == "__main__":
    unittest.main()

import unittest

import pandas as pd

from edgelab.data.liquid_release.dedupe import adjudicate, find_shifted_duplicates


def _bin(d, h, n, **kw):
    base = dict(raw_date=d, raw_hour=h, n=n, vol=n * 2, fp_ts=n * 1000 + h * 0, fp_px=n * 100, fp_bid=n * 99, fp_ask=n * 101)
    base.update(kw)
    return base


class Dedupe(unittest.TestCase):
    def test_copia_con_3h_exactas_en_la_pausa(self):
        # hora 18 original y hora 21 (pausa, 16 CT en verano) idénticas; hora 19 distinta
        bins = pd.DataFrame([_bin(20260617, 18, 86342), _bin(20260617, 19, 88455, fp_px=1, fp_ts=7), _bin(20260617, 21, 86342)])
        d = find_shifted_duplicates(bins)
        self.assertEqual(len(d), 1)
        self.assertEqual((int(d.iloc[0].orig_hour), int(d.iloc[0].copy_hour), int(d.iloc[0].shift_h)), (18, 21, 3))
        a = adjudicate(d, {(20260617, 21): True, (20260617, 18): False})
        self.assertEqual(a.iloc[0]["verdict"], "COPY_IS_LATER_OUTSIDE_REGULAR")
        self.assertEqual(int(a.iloc[0]["drop_hour"]), 21)

    def test_ambos_regulares_es_ambiguo_y_no_se_descarta(self):
        bins = pd.DataFrame([_bin(20260617, 14, 5000), _bin(20260617, 17, 5000)])
        a = adjudicate(find_shifted_duplicates(bins), {})
        self.assertEqual(a.iloc[0]["verdict"], "AMBIGUOUS")
        self.assertTrue(pd.isna(a.iloc[0]["drop_hour"]))

    def test_horas_chicas_o_distintas_no_se_marcan(self):
        bins = pd.DataFrame([_bin(20260617, 3, 10), _bin(20260617, 6, 10),               # n < min_n
                             _bin(20260617, 18, 500), _bin(20260617, 21, 500, fp_px=1)])  # contenido distinto
        self.assertEqual(len(find_shifted_duplicates(bins)), 0)


if __name__ == "__main__":
    unittest.main()

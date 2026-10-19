import unittest

import numpy as np
import pandas as pd

from edgelab.data.liquid_release.calendar_tz import (in_break, raw_hour_index, trade_date, violation_by_offset)


def _bins(rows):
    return pd.DataFrame(rows, columns=["raw_date", "raw_hour", "n"])


class CalendarTz(unittest.TestCase):
    def test_utc_data_prefiere_offset_cero_en_verano_y_en_invierno(self):
        # lunes 2025-09-15 (CDT): pausa 21:00Z; lunes 2025-12-15 (CST): pausa 22:00Z
        rows = []
        for d, gap in ((20250915, 21), (20251215, 22)):
            for h in range(24):
                if h != gap:
                    rows.append((d, h, 100))
        v = violation_by_offset(_bins(rows))
        self.assertEqual(min(v, key=v.get), 0)
        self.assertLess(v[0], 0.01)
        self.assertGreater(v[-3], 0.03)           # ART mal etiquetado se distingue

    def test_trade_date_cruza_medianoche(self):
        # domingo 2026-06-28 22:00Z = 17:00 CDT del domingo -> trade date lunes 29
        idx = raw_hour_index(np.array([20260628, 20260629]), np.array([22, 20]))
        np.testing.assert_array_equal(trade_date(idx), [20260629, 20260629])   # 20:00Z = 15:00 CDT del lunes

    def test_trade_date_despues_de_la_pausa(self):
        idx = raw_hour_index(np.array([20260629, 20260629]), np.array([21, 22]))   # 16:00 y 17:00 CDT
        np.testing.assert_array_equal(trade_date(idx), [20260629, 20260630])
        np.testing.assert_array_equal(in_break(idx), [True, False])


if __name__ == "__main__":
    unittest.main()

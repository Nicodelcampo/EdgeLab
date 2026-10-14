import os
import tempfile
import unittest
from pathlib import Path

import pyarrow.parquet as pq

from edgelab.data.liquid_release.consolidate import Segment, SourceFile, write_asset

# 2026-06-29 (lunes, CDT): 20:00Z = 15:00 CT (sesión, trade date 20260629); 21:00Z = 16:00 CT (pausa);
# 22:00Z = 17:00 CT (abre la sesión del 30-jun)
LINES = [
    "20260629 200000 0000000;100.25;100.00;100.25;3",    # compra (px>=ask)
    "20260629 200001 0000000;100.00;100.00;100.25;2",    # venta (px<=bid)
    "20260629 210500 0000000;100.00;99.75;100.00;1",     # en pausa -> outside_regular; px>=ask -> compra
    "20260629 220000 0000000;101.00;100.75;101.25;4",    # trade date 20260630, sin clasificar
]
LOOKUP = {20260629 * 24 + 20: (20260629, False), 20260629 * 24 + 21: (20260629, True), 20260629 * 24 + 22: (20260630, False)}


def _src(lines):
    fd, p = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    Path(p).write_bytes(("\n".join(lines) + "\n").encode())
    return p


class Consolidate(unittest.TestCase):
    def test_esquema_flags_y_row_groups_por_sesion(self):
        p = _src(LINES)
        seg = Segment("ES 09-26", 3, [SourceFile(p, 7, 0, "A")], {20260629, 20260630}, LOOKUP)
        out = Path(tempfile.mkdtemp()) / "ES_ticks.parquet"
        stats, rows = write_asset(out, [seg], 0.25)
        self.assertEqual(rows, 4)
        t = pq.read_table(out)
        self.assertEqual(t["trade_date"].to_pylist(), [20260629, 20260629, 20260629, 20260630])
        self.assertEqual(t["aggressor"].to_pylist(), [1, -1, 1, 0])
        self.assertEqual(t["outside_regular"].to_pylist(), [False, False, True, False])
        self.assertEqual(t["release_row"].to_pylist(), [0, 1, 2, 3])
        self.assertEqual(t["source_row"].to_pylist(), [0, 1, 2, 3])
        self.assertEqual(set(t["contract"].to_pylist()), {"ES 09-26"})
        pf = pq.ParquetFile(out)
        ci = pf.schema_arrow.names.index("trade_date")
        for g in range(pf.metadata.num_row_groups):          # cada row group abarca una sola fecha
            st = pf.metadata.row_group(g).column(ci).statistics
            self.assertEqual(st.min, st.max)

    def test_solo_fechas_seleccionadas(self):
        p = _src(LINES)
        seg = Segment("ES 09-26", 1, [SourceFile(p, 1, 0, "A")], {20260630}, LOOKUP)
        out = Path(tempfile.mkdtemp()) / "x.parquet"
        _, rows = write_asset(out, [seg], 0.25)
        self.assertEqual(rows, 1)

    def test_offset_resta_horas_al_sello_crudo(self):
        p = _src(LINES[:1])
        seg = Segment("ES 09-26", 1, [SourceFile(p, 1, -3, "A")], {20260629}, LOOKUP)   # crudo ART -> UTC = crudo + 3 h
        out = Path(tempfile.mkdtemp()) / "x.parquet"
        write_asset(out, [seg], 0.25)
        t = pq.read_table(out)
        raw = 1782763200 * 10**9      # 2026-06-29T20:00:00 como UTC-naive
        self.assertEqual(t["ts_utc_ns"][0].as_py(), raw + 3 * 3_600_000_000_000)

    def test_precio_fuera_de_grilla_es_stop(self):
        p = _src(["20260629 200000 0000000;100.30;100.00;100.25;3"])
        seg = Segment("ES 09-26", 1, [SourceFile(p, 1, 0, "A")], {20260629}, LOOKUP)
        with self.assertRaises(ValueError):
            write_asset(Path(tempfile.mkdtemp()) / "x.parquet", [seg], 0.25)



class Aggressor(unittest.TestCase):
    def test_locked_y_cruzado_quedan_sin_clasificar(self):
        import numpy as np
        from edgelab.data.liquid_release.consolidate import aggressor
        last = np.array([100.0, 100.0, 100.0, 100.0])
        bid = np.array([100.0, 100.25, 0.0, 99.75])
        ask = np.array([100.0, 100.0, 100.0, 100.0])
        self.assertEqual(aggressor(last, bid, ask).tolist(), [0, 0, 0, 1])


if __name__ == "__main__":
    unittest.main()

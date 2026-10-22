import hashlib
import os
import tempfile
import unittest

import numpy as np

from edgelab.data.liquid_release.hourly_scan import scan_file
from edgelab.data.liquid_release.nt8_text import iter_decoded

LINES = [
    "20260930 215958 0000000;100.25;100.00;100.25;3",
    "20260930 215959 5000000;100.50;100.25;100.50;2",
    "20260930 220000 0000000;999.00;998.75;999.00;7",      # >= cutoff (holdout): no debe decodificarse
    "20260930 220001 0000000;999.25;999.00;999.25;5",
]


def _write(lines, crlf=False):
    fd, p = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    eol = "\r\n" if crlf else "\n"
    with open(p, "wb") as f:
        f.write((eol.join(lines) + eol).encode())
    return p


class TextReader(unittest.TestCase):
    def test_cutoff_no_decodifica_holdout(self):
        p = _write(LINES)
        it, st = iter_decoded(p, chunk_bytes=64, cutoff_prefix=b"20260930 220000")
        rows = sum(len(b["date"]) for b in it)
        self.assertEqual(rows, 2)
        self.assertTrue(st.truncated_at_cutoff)
        self.assertIsNone(st.sha256)                      # no se leyó el archivo entero: no hay sha completo

    def test_sha_completo_sin_cutoff(self):
        p = _write(LINES[:2])
        it, st = iter_decoded(p, chunk_bytes=64)
        list(it)
        self.assertEqual(st.sha256, hashlib.sha256(open(p, "rb").read()).hexdigest())

    def test_crlf_y_valores(self):
        p = _write(LINES[:2], crlf=True)
        it, st = iter_decoded(p)
        b = next(it)
        np.testing.assert_allclose(b["last"], [100.25, 100.50])
        self.assertEqual(list(b["vol"]), [3, 2])
        self.assertEqual(int(b["ts_raw_ns"][1] - b["ts_raw_ns"][0]), 1_000_000_000 + 500_000_000)

    def test_lineas_invalidas_se_cuentan_no_se_imputan(self):
        p = _write([LINES[0], "basura;sin;forma", "20260930 21595 5000000;1;1;1;1", LINES[1]])
        it, st = iter_decoded(p)
        rows = sum(len(b["date"]) for b in it)
        self.assertEqual(rows, 2)
        self.assertEqual(st.rows_invalid_shape + st.rows_invalid_ts, 2)

    def test_hourly_scan_conteos_y_grilla(self):
        lines = ["20260930 100000 0000000;100.25;100.00;100.25;3", "20260930 100001 0000000;100.30;100.00;100.25;2",
                 "20260930 110000 0000000;100.50;100.50;100.50;4"]
        p = _write(lines)
        df, info = scan_file(p, 0.25)
        self.assertEqual(list(df["raw_hour"]), [10, 11])
        self.assertEqual(list(df["n"]), [2, 1])
        self.assertEqual(list(df["vol"]), [5, 4])
        self.assertEqual(int(df["off_last"].sum()), 1)       # 100.30 fuera de grilla 0.25
        self.assertEqual(int(df["locked"].sum()), 1)
        self.assertEqual(info["rows_ok"], 3)


    def test_hueco_maximo_minutos_y_huella(self):
        lines = ["20260930 100000 0000000;100.25;100.00;100.25;3", "20260930 100001 0000000;100.25;100.00;100.25;2",
                 "20260930 102500 0000000;100.50;100.25;100.50;4", "20260930 102530 0000000;100.50;100.25;100.50;1"]
        df, _ = scan_file(_write(lines), 0.25, chunk_bytes=64)           # lotes chicos: el resultado no puede depender de ellos
        df2, _ = scan_file(_write(lines), 0.25)
        self.assertEqual(int(df["max_gap_ns"].iloc[0]), (24 * 60 + 59) * 1_000_000_000)   # 100001 -> 102500
        self.assertEqual(int(df["n_min"].iloc[0]), 2)                                      # minutos 10:00 y 10:25
        for c in ("fp_ts", "fp_px", "fp_bid", "fp_ask", "n", "vol", "max_gap_ns", "n_min"):
            self.assertEqual(int(df[c].iloc[0]), int(df2[c].iloc[0]), c)


if __name__ == "__main__":
    unittest.main()

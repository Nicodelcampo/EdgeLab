import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pyarrow as pa
import pyarrow.parquet as pq

from edgelab.data.liquid_release import release_reader as rr


def _make_release(trade_dates, extra_group=None, tamper=False):
    root = Path(tempfile.mkdtemp())
    (root / "data").mkdir()
    p = root / "data" / "ES_ticks.parquet"
    w = None
    for td in trade_dates + ([extra_group] if extra_group else []):
        t = pa.table({"trade_date": pa.array([td, td], pa.int32()), "price_ticks": pa.array([1, 2], pa.int64())})
        if w is None:
            w = pq.ParquetWriter(p, t.schema)
        w.write_table(t, row_group_size=2)
    w.close()
    man = {"schema": rr.SCHEMA, "assets": {"ES": {"file": "data/ES_ticks.parquet", "bytes": p.stat().st_size,
                                                "sha256": rr.sha256_file(p), "rows": 2 * len(trade_dates)}}}
    if tamper:
        man["assets"]["ES"]["sha256"] = "0" * 64
    (root / "release_manifest.json").write_text(json.dumps(man), encoding="utf-8")
    return root


class ReleaseReader(unittest.TestCase):
    def test_lee_solo_los_row_groups_del_rango(self):
        root = _make_release([20260105, 20260106, 20260107])
        t = rr.read_asset(root, "ES", 20260106, 20260107)
        self.assertEqual(sorted(set(t["trade_date"].to_pylist())), [20260106, 20260107])

    def test_holdout_solicitado_es_stop(self):
        root = _make_release([20260105])
        with self.assertRaises(rr.ReleaseStop):
            rr.read_asset(root, "ES", 20260105, 20261001)

    def test_row_group_reservado_nunca_se_lee(self):
        root = _make_release([20260105], extra_group=20261002)
        pf_cls = rr.pq.ParquetFile
        reads = []
        orig = pf_cls.read_row_groups
        with mock.patch.object(pf_cls, "read_row_groups", autospec=True,
                               side_effect=lambda self, groups, **k: (reads.append(list(groups)), orig(self, groups, **k))[1]):
            with self.assertRaises(rr.ReleaseStop):
                rr.read_asset(root, "ES", 20260105, 20260105)
        self.assertEqual(reads, [])                        # STOP antes de deserializar nada

    def test_manifiesto_ausente_vacio_o_hash_distinto(self):
        root = Path(tempfile.mkdtemp())
        with self.assertRaises(rr.ReleaseStop):
            rr.load_manifest(root)                          # ausente
        (root / "release_manifest.json").write_text(json.dumps({"schema": rr.SCHEMA, "assets": {}}))
        with self.assertRaises(rr.ReleaseStop):
            rr.load_manifest(root)                          # vacío
        with self.assertRaises(rr.ReleaseStop):
            rr.load_manifest(_make_release([20260105], tamper=True))   # hash distinto

    def test_mismo_tamano_distinto_contenido_falla(self):
        root = _make_release([20260105])
        p = root / "data" / "ES_ticks.parquet"
        b = bytearray(p.read_bytes())
        b[-20] ^= 0xFF                                      # mismo tamaño, distinto contenido
        p.write_bytes(bytes(b))
        with self.assertRaises(rr.ReleaseStop):
            rr.load_manifest(root)

    def test_traversal_y_basename_no_se_aceptan(self):
        root = _make_release([20260105])
        m = json.loads((root / "release_manifest.json").read_text())
        m["assets"]["ES"]["file"] = "../ES_ticks.parquet"
        (root / "release_manifest.json").write_text(json.dumps(m))
        with self.assertRaises(rr.ReleaseStop):
            rr.load_manifest(root)
        m["assets"]["ES"]["file"] = "ES_ticks.parquet"      # basename sin subcarpeta: no se busca
        (root / "release_manifest.json").write_text(json.dumps(m))
        with self.assertRaises(rr.ReleaseStop):
            rr.load_manifest(root)

    def test_cache_key_cambia_con_contenido_esquema_o_transformacion(self):
        k = rr.cache_key("a" * 64, "v1", "m1", "1")
        self.assertNotEqual(k, rr.cache_key("b" * 64, "v1", "m1", "1"))
        self.assertNotEqual(k, rr.cache_key("a" * 64, "v2", "m1", "1"))
        self.assertNotEqual(k, rr.cache_key("a" * 64, "v1", "m1", "2"))


if __name__ == "__main__":
    unittest.main()

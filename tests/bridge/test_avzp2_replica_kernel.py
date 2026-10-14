"""Pruebas del kernel de la réplica AVZP2 (lector embebido, geometría del nulo, constructor y análisis). Todo sintético, sin datos de mercado."""
import ast
import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def _load(name, rel):
    os.environ.setdefault("AVCL_OUT", tempfile.mkdtemp(prefix="avzp2_k_"))
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


S1 = _load("avzp2_stage1_k", "tools/avzp2_racimo_replica_stage1.py")
CUT = S1.HOLDOUT_FIRST_TS_NS


def write_release(tmp, trade_dates, ts, with_stats=True, tamper_sha=False, schema="edgelab_liquid_release_v1"):
    root = Path(tmp)
    (root / "data").mkdir(exist_ok=True)
    p = root / "data" / "ES_ticks.parquet"
    t = pa.table({"ts_utc_ns": pa.array(ts, pa.int64()), "trade_date": pa.array(trade_dates, pa.int32()), "price_ticks": pa.array([1] * len(ts), pa.int64())})
    pq.write_table(t, p, row_group_size=2, write_statistics=with_stats)
    sha = "0" * 64 if tamper_sha else hashlib.sha256(p.read_bytes()).hexdigest()
    man = dict(schema=schema, status="CANDIDATE_NOT_RESEARCH_APPROVED", assets={"ES": dict(file="data/ES_ticks.parquet", bytes=p.stat().st_size, sha256=sha, rows=len(ts))})
    (root / "release_manifest.json").write_text(json.dumps(man), encoding="utf-8")
    return root


class LectorEmbebido(unittest.TestCase):
    def test_lee_un_archivo_limpio(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = write_release(tmp, [20260101, 20260101, 20260102, 20260102], [1, 2, 3, 4])
            t = S1.read_asset(root, "ES", 20260101, 20260102, columns=["ts_utc_ns"], purpose="provisional_research")
            self.assertEqual(t.num_rows, 4)

    def test_timestamp_reservado_con_trade_date_mal_rotulado_se_detiene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = write_release(tmp, [20260929, 20260929, 20260930, 20260930], [1, 2, CUT + 5, CUT + 9])
            with self.assertRaises(RuntimeError):
                S1.read_asset(root, "ES", 20260929, 20260930, columns=["ts_utc_ns"], purpose="provisional_research")

    def test_grupo_reservado_fuera_del_rango_pedido_tambien_detiene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = write_release(tmp, [20260101, 20260101, 20260930, 20260930], [1, 2, CUT + 1, CUT + 2])
            with self.assertRaises(RuntimeError):
                S1.read_asset(root, "ES", 20260101, 20260101, columns=["ts_utc_ns"], purpose="provisional_research")

    def test_sin_estadisticas_se_detiene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = write_release(tmp, [20260101] * 4, [1, 2, 3, 4], with_stats=False)
            with self.assertRaises(RuntimeError):
                S1.read_asset(root, "ES", 20260101, 20260101, columns=["ts_utc_ns"], purpose="provisional_research")

    def test_sha_distinto_o_proposito_invalido_o_holdout_pedido(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = write_release(tmp, [20260101, 20260101], [1, 2], tamper_sha=True)
            with self.assertRaises(RuntimeError):
                S1.read_asset(root, "ES", 20260101, 20260101, columns=["ts_utc_ns"], purpose="provisional_research", verify_hash=True)
            with self.assertRaises(RuntimeError):
                S1.read_asset(root, "ES", 20260101, 20260101, columns=["ts_utc_ns"], purpose="research", verify_hash=False)
            with self.assertRaises(RuntimeError):
                S1.read_asset(root, "ES", 20260101, 20261001, columns=["ts_utc_ns"], purpose="audit", verify_hash=False)

    def test_pin_del_manifiesto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = write_release(tmp, [20260101, 20260101], [1, 2])
            old, S1.RELEASE = S1.RELEASE, root
            try:
                os.environ["EXPECT_MANIFEST_SHA256"] = "0" * 64
                with self.assertRaises(RuntimeError):
                    S1.pin_check()
                os.environ["EXPECT_MANIFEST_SHA256"] = hashlib.sha256((root / "release_manifest.json").read_bytes()).hexdigest()
                S1.pin_check()
            finally:
                S1.RELEASE = old
                os.environ.pop("EXPECT_MANIFEST_SHA256", None)


class GeometriaDelNulo(unittest.TestCase):
    def test_misma_tendencia_copia_los_desplazamientos(self):
        self.assertEqual(S1.pseudo_box(1000, -28, 2, 1, 1), (972, 1002))

    def test_tendencia_opuesta_espeja(self):
        # real alcista con el cierre a 2 ticks del techo; pseudo bajista: el borde de la tendencia (el piso) queda a 2 ticks del cierre
        L, H = S1.pseudo_box(1000, -28, 2, 1, -1)
        self.assertEqual((L, H), (998, 1028))
        self.assertEqual(1000 - L, 2)            # distancia al borde del lado de la tendencia (abajo) == 2, como en el real (arriba)

    def test_tendencia_cero_no_espeja(self):
        self.assertEqual(S1.pseudo_box(1000, -28, 2, 0, -1), (972, 1002))
        self.assertEqual(S1.pseudo_box(1000, -28, 2, 1, 0), (972, 1002))

    def test_el_espejo_es_una_involucion(self):
        L, H = S1.pseudo_box(500, -10, 30, 1, -1)
        L2, H2 = S1.pseudo_box(500, L - 500, H - 500, -1, 1)
        self.assertEqual((L2, H2), (500 - 10, 500 + 30))


class Constructor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import build_avzp2_replica_kernel as bk
        cls.tmp = tempfile.mkdtemp(prefix="avzp2_build_")
        cls.info = bk.build("ES", cls.tmp, "ab" * 32)
        cls.src = Path(cls.info["z_py"]).read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.src)

    def test_incluye_el_detector_validado_y_no_importa_edgelab_indicators(self):
        self.assertNotIn("from edgelab.bridge.indicators.avolzonepoi2", self.src)
        names = {n.name for n in self.tree.body if isinstance(n, ast.FunctionDef)}
        for need in ("run", "_racimo", "pseudo_box", "preflight_footer", "read_asset", "analyze_all", "run_analysis", "absorb", "beta", "prep"):
            self.assertIn(need, names)
        self.assertNotIn("_detect_zones_numba", names)       # el detector reimplementado de otro kernel no debe aparecer

    def test_sin_red_ni_subprocesos(self):
        for bad in ("import requests", "import urllib", "import socket", "import subprocess", "os.system", "eval(", "__import__"):
            self.assertNotIn(bad, self.src)

    def test_sin_funciones_duplicadas_en_el_primer_nivel(self):
        names = [n.name for n in self.tree.body if isinstance(n, ast.FunctionDef)]
        dup = {n for n in names if names.count(n) > 1}
        self.assertEqual(dup, set())

    def test_pin_y_procedencia_embebidos(self):
        self.assertIn("ab" * 32, self.src)
        self.assertIn("EXPECT_MANIFEST_SHA256", self.src)
        meta = json.loads((Path(self.tmp) / self.info["slug"] / "kernel-metadata.json").read_text(encoding="utf-8"))
        self.assertFalse(meta["enable_internet"]); self.assertTrue(meta["is_private"])
        self.assertEqual(meta["dataset_sources"], ["nicolasbuttaro/edgelab-liquid-ticks-20261014", "nicolasbuttaro/edgelab-code-avcl-fast"])
        req = json.loads((Path(self.tmp) / "push_request_ES.json").read_text(encoding="utf-8"))
        self.assertEqual(req["action"], "push_kernel"); self.assertFalse(req["params"]["enable_internet"])
        self.assertLess(len(json.dumps(req)), 1_000_000)      # cabe en el tope de pedidos del puente


def synthetic_rows(n_real=200, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for cell in ("6_500_30", "4_1000_30", "4_1000_45", "5_1000_30", "5_1000_45", "6_1000_30", "6_1000_45"):
        for kind in ("real", "pseudo", "pseudo_legacy"):
            n = n_real if kind == "real" else n_real * 5
            for i in range(n):
                tr = int(rng.choice([-1, 1]))
                te = int(rng.integers(5, 400)) if rng.random() < 0.9 else -1
                rows.append(dict(cell=cell, contract="ES %d" % (i % 4), kind=kind, session=int(rng.integers(0, 120)), clock=int(rng.integers(14, 32)),
                                 occ=float(rng.integers(0, 500)) / 500, amp=float(rng.normal(1.0, 0.3)), trend=tr, te=te, dir=tr if rng.random() < 0.7 else -tr,
                                 o2=int(rng.integers(-1, 2)), o3a=int(rng.integers(0, 2)), o3b=int(rng.integers(-1, 2)), o4=float(rng.normal()), o5=float(rng.normal(-0.05 if kind == "real" else 0, 0.5)),
                                 o5_t0=float(rng.normal()), o6_rev=int(rng.choice([-2, -1, 0, 1])), trend_h=float(rng.normal() * tr), mom100_h=float(rng.normal())))
    return pd.DataFrame(rows)


class AnalisisHumo(unittest.TestCase):
    def test_analyze_all_con_variantes_y_primaria(self):
        import avzp2_racimo_replica_stage2 as s2
        out = s2.analyze_all(synthetic_rows(), "ES")
        self.assertEqual(out["primaria"], "mirror|average")
        self.assertEqual(set(out["variantes"]), {"mirror|average", "mirror|first", "legacy|average", "legacy|first"})
        v = out["variantes"]["mirror|average"]
        self.assertIn("O5|6_500_30", v["pruebas"]); self.assertIn("O1|4_1000_45", v["pruebas"]); self.assertIn("O6rev|4_1000_45", v["pruebas"])
        self.assertTrue(all(np.isfinite(r["beta"]) for r in v["pruebas"].values()))
        json.dumps(out, default=float)

    def test_datos_anteriores_a_la_auditoria_reproducen_el_comportamiento_de_las_actas(self):
        import avzp2_racimo_replica_stage2 as s2
        t = synthetic_rows()
        t = t[t.kind != "pseudo_legacy"].drop(columns=["o5_t0", "o6_rev"])
        out = s2.analyze_all(t, "ES")
        self.assertEqual(out["primaria"], "legacy_actas|first")

    def test_prep_first_es_el_comportamiento_original_y_average_no_depende_del_orden(self):
        import avzp2_racimo_stage2 as s2
        t = synthetic_rows().query("cell == '4_1000_45' and kind in ['real','pseudo']").reset_index(drop=True)
        a = s2.prep(t, "average")
        b = s2.prep(t.sample(frac=1.0, random_state=3), "average").sort_index()
        pd.testing.assert_series_equal(a["occD"], b["occD"], check_dtype=False)       # los empates exactos caen en el mismo decil
        self.assertTrue(s2.prep(t, "first")["occD"].between(0, 9).all())


if __name__ == "__main__":
    unittest.main()

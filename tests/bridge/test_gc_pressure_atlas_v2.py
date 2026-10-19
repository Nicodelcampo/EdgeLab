"""Pruebas del atlas GC V2 y del lector de la release. Todo sintético: ninguna prueba toca datos de mercado."""
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import gc_pressure_atlas_v2 as A  # noqa: E402
import release_io as R  # noqa: E402

CT = ZoneInfo("America/Chicago")


def ns(y, mo, d, h, mi, s=0, tz=CT):
    return int(datetime(y, mo, d, h, mi, s, tzinfo=tz).astimezone(timezone.utc).timestamp()) * 10**9


class Vendorizado(unittest.TestCase):
    def test_motor_copiado_sin_cambios(self):
        p = ROOT / "tools" / "vendor" / "notion_phenomena.py"
        lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
        declared = lines[1].split(":")[1].strip()
        body = "".join(lines[3:]).replace("\r\n", "\n").encode("utf-8")
        self.assertEqual(hashlib.sha256(body).hexdigest(), declared)


class Utilidades(unittest.TestCase):
    def test_fase_rth_incluye_0830_y_excluye_1500_con_horario_de_verano_e_invierno(self):
        t = np.array([ns(2026, 7, 6, 8, 29, 59), ns(2026, 7, 6, 8, 30, 0), ns(2026, 7, 6, 14, 59, 59), ns(2026, 7, 6, 15, 0, 0),
                      ns(2026, 1, 5, 8, 29, 59), ns(2026, 1, 5, 8, 30, 0), ns(2026, 1, 5, 14, 59, 59), ns(2026, 1, 5, 15, 0, 0)])
        self.assertEqual(A.phase_array(t).tolist(), [0, 1, 1, 0, 0, 1, 1, 0])

    def test_bins_de_presion_y_avance_con_limites_inclusivos_abajo(self):
        self.assertEqual(A.pressure_bin(np.array([0.49, 0.5, 0.99, 1.0, 1.99, 2.0, 9.0])).tolist(), [0, 1, 1, 2, 2, 3, 3])
        self.assertEqual(A.progress_bin(np.array([-9.0, -4.0, -2.01, -2.0, 1.99, 2.0, 3.99, 4.0])).tolist(), [0, 1, 1, 2, 2, 3, 3, 4])

    def test_no_solapadas_primera_y_luego_al_menos_40_segundos(self):
        s = 10**9
        t = np.array([0, 5, 10, 39, 40, 41, 80, 119, 120]) * s
        self.assertEqual(A.select_nonoverlap(t).tolist(), [True, False, False, False, True, False, True, False, True])

    def test_holm(self):
        h = A.holm({"a": 0.01, "b": 0.04, "c": 0.5})
        self.assertAlmostEqual(h["a"], 0.03); self.assertAlmostEqual(h["b"], 0.08); self.assertAlmostEqual(h["c"], 0.5)

    def test_pesos_de_bootstrap_suman_el_numero_de_sesiones(self):
        W = A.boot_weights(17, 50, 1)
        self.assertTrue((W.sum(1) == 17).all())


class Calibracion(unittest.TestCase):
    def feats(self, n, base_t):
        t = base_t + np.arange(n, dtype=np.int64) * 10**10
        return {"ts": t, "dir": np.ones(n, np.int8), "press_cur": np.linspace(1, 100, n), "press_pri": np.linspace(2, 200, n)}

    def test_celda_sin_soporte_y_sha_estable(self):
        f_rth = self.feats(150, ns(2026, 1, 5, 9, 0))
        f_oth = self.feats(50, ns(2026, 1, 5, 2, 0))
        cal = A.freeze_calibration([(20260105, {k: np.concatenate([f_rth[k], f_oth[k]]) for k in f_rth})])
        self.assertTrue(cal["cells"]["RTH:1"]["supported"]); self.assertFalse(cal["cells"]["OTHER:1"]["supported"])
        self.assertAlmostEqual(cal["cells"]["RTH:1"]["current_pressure_q80"], float(np.quantile(f_rth["press_cur"], 0.8)))
        self.assertEqual(cal["sha256"], A.freeze_calibration([(20260105, {k: np.concatenate([f_rth[k], f_oth[k]]) for k in f_rth})])["sha256"])
        self.assertFalse(cal["outcomes_used"])


class Placebo(unittest.TestCase):
    def test_esperanza_exacta_contra_permutaciones_por_fuerza_bruta(self):
        rng = np.random.default_rng(3)
        r = pd.DataFrame({"phase": [1] * 6, "dir": [1, 1, -1, 1, -1, -1], "net_cur": rng.normal(size=6)})
        import itertools
        perms = list(itertools.permutations(r["dir"].tolist()))
        brute = np.mean([np.array(p) * r["net_cur"].to_numpy() for p in perms], axis=0)
        np.testing.assert_allclose(A.placebo_cur(r), brute, atol=1e-12)

    def test_p1_detecta_persistencia_y_no_inventa_cuando_no_hay(self):
        rng = np.random.default_rng(5)

        def sesiones(persist):
            out = []
            for _ in range(40):
                d = rng.choice([-1, 1], size=300)
                net = rng.normal(0, 3, size=300) + persist * d            # el avance neto sigue (o no) a la dirección
                out.append(pd.DataFrame({"phase": 1, "dir": d, "net_cur": net, "cur_dir": d * net, "pri_dir": rng.normal(size=300), "press": 1.0, "abs_prog": np.abs(net), "pratio": 1.0, "cnt": 10.0}))
            return out
        W = A.boot_weights(40, 400, 7)
        con = A.p1_estimates(sesiones(1.0), W, None)
        sin = A.p1_estimates(sesiones(0.0), W, None)
        self.assertGreater(con["delta_ticks"], 0.8); self.assertLess(con["p"], 0.001)
        self.assertLess(con["ci95"][0], con["delta_ticks"] < con["ci95"][1] and con["delta_ticks"])
        self.assertTrue(sin["ci95"][0] < 0 < sin["ci95"][1]); self.assertGreater(sin["mde_2p8_se"], 0)


class Correlaciones(unittest.TestCase):
    def test_pearson_y_parcial_coinciden_con_numpy(self):
        rng = np.random.default_rng(11)
        n = 500
        z = rng.normal(size=n); x = z + rng.normal(size=n); y = 0.5 * z + rng.normal(size=n)
        df = pd.DataFrame({"x": x, "y": y, "z": z})
        m = A.moments(df, ("x", "y", "z"))
        rxy, _, par = A.corr_from_moments(m[None, :])
        self.assertAlmostEqual(float(rxy[0]), float(np.corrcoef(x, y)[0, 1]), places=10)
        rx = x - np.polyval(np.polyfit(z, x, 1), z); ry = y - np.polyval(np.polyfit(z, y, 1), z)
        self.assertAlmostEqual(float(par[0]), float(np.corrcoef(rx, ry)[0, 1]), places=8)


def synthetic_ticks(n=12000, seed=0, start=None):
    rng = np.random.default_rng(seed)
    start = start or ns(2026, 1, 5, 9, 0)
    ts = start + np.cumsum(rng.integers(100_000_000, 900_000_000, size=n)).astype(np.int64)
    mid2 = 80_000 + np.cumsum(rng.integers(-1, 2, size=n)) * 1   # medio-tick
    bid = (mid2 // 2).astype(np.int64)
    ask = bid + 1
    price = np.where(rng.random(n) < 0.5, bid, ask).astype(np.int64)
    return dict(ts_utc_ns=ts, price_ticks=price, bid_ticks=bid, ask_ticks=ask, volume=rng.integers(1, 6, size=n).astype(np.float64), release_row=np.arange(n, dtype=np.int64), contract="GC 02-26")


class SesionSintetica(unittest.TestCase):
    def test_anclas_y_atlas_cuadran(self):
        a = synthetic_ticks()
        f, cnt = A.anchor_features(a, 20260105)
        self.assertGreater(len(f["ts"]), 100)
        self.assertEqual(cnt["ANCHORS"], cnt.get("UNKNOWN_PAIR", 0) + cnt.get("SIGNED_COVERAGE_BELOW_80PCT", 0) + cnt.get("NONFINITE_DESCRIPTOR", 0) + len(f["ts"]))
        cal = A.freeze_calibration([(20260105, f)])
        s = A.atlas_session(f, cal)
        self.assertEqual(sum(int(m.sum()) for m in s["pp_all"].values()), s["eligible"])
        self.assertEqual(sum(int(m.sum()) for m in s["pc_all"].values()), s["eligible"])
        self.assertEqual(sum(int(m.sum()) for m in s["pp_no"].values()), s["nonoverlap"])
        self.assertEqual(len(s["rows"]), s["nonoverlap"])
        self.assertTrue(np.isfinite(s["rows"][["cur_dir", "pri_dir", "net_cur", "press"]].to_numpy()).all())

    def test_chequeos_del_dataset_detectan_cruces_y_saltos(self):
        a = synthetic_ticks(2000)
        ok = A.dataset_checks(a)
        self.assertEqual(ok["crossed"], 0); self.assertEqual(ok["ts_nonmonotonic"], 0)
        a["bid_ticks"] = a["bid_ticks"].copy(); a["bid_ticks"][10] = a["ask_ticks"][10] + 5
        a["price_ticks"] = a["price_ticks"].copy(); a["price_ticks"][20] += 500
        bad = A.dataset_checks(a)
        self.assertGreaterEqual(bad["crossed"], 1); self.assertGreaterEqual(bad["max_abs_tick_jump"], 400)


def write_release(root: Path, sessions: list[int]):
    (root / "data").mkdir(parents=True)
    (root / "metadata").mkdir()
    parts = []
    for i, td in enumerate(sessions):
        a = synthetic_ticks(9000, seed=i, start=ns(2026, 1, 5, 9, 0) + i * 86_400 * 10**9)
        n = len(a["ts_utc_ns"])
        parts.append(pa.table({"ts_utc_ns": pa.array(a["ts_utc_ns"]), "root": pa.array(["GC"] * n), "price_ticks": pa.array(a["price_ticks"]), "bid_ticks": pa.array(a["bid_ticks"]),
                               "ask_ticks": pa.array(a["ask_ticks"]), "volume": pa.array(a["volume"].astype(np.int64)), "contract": pa.array([a["contract"]] * n),
                               "trade_date": pa.array(np.full(n, td, np.int32)), "outside_regular": pa.array(np.zeros(n, bool)),
                               "release_row": pa.array(np.arange(n, dtype=np.int64) + i * 100_000)}))
    w = pq.ParquetWriter(root / "data" / "GC_ticks.parquet", parts[0].schema)
    for t in parts:
        w.write_table(t, row_group_size=len(t))
    w.close()
    p = root / "data" / "GC_ticks.parquet"
    man = {"schema": R.SCHEMA, "status": "CANDIDATE_NOT_RESEARCH_APPROVED", "assets": {"GC": {"file": "data/GC_ticks.parquet", "bytes": p.stat().st_size,
           "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "rows": sum(len(t) for t in parts)}}}
    (root / "release_manifest.json").write_text(json.dumps(man), encoding="utf-8")
    pd.DataFrame({"instrument": "GC", "trade_date": sessions, "status": "SELECTED", "contract": "GC 02-26"}).to_parquet(root / "metadata" / "session_index.parquet")


class CorridaCompletaSintetica(unittest.TestCase):
    def test_run_de_punta_a_punta_y_sesiones_selladas_no_se_leen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_release(root, [20260105, 20260106, 20260107, 20260108, 20260109])
            leidas = []
            orig = R.read_asset
            R.read_asset = lambda *a, **k: (leidas.append(a[2]), orig(*a, **k))[1]
            try:
                res = A.run(str(root), n_cal=1, n_atlas=3, boot=40, log=lambda s: None)
            finally:
                R.read_asset = orig
            self.assertEqual(sorted(set(leidas)), [20260105, 20260106, 20260107, 20260108])      # la 5.ª (20260109) es la SELLADA: no se lee
            self.assertEqual(res["particion"]["selladas_no_leidas"], 1)
            self.assertFalse(res["pnl"]); self.assertEqual(res["pruebas_de_informacion"]["n_efectivo_de_pruebas"], 4)
            self.assertEqual(res["calibracion_congelada"]["sessions"], [20260105])
            self.assertIn("P1_primaria", res["pruebas_de_informacion"]["holm_p_ajustado"])
            self.assertTrue(res["pruebas_del_dataset"]["release_row_estrictamente_creciente_en_todas"])
            json.dumps(res, default=float)

    def test_el_lector_se_detiene_ante_timestamp_reservado(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            ts = [1, 2, R.HOLDOUT_FIRST_TS_NS + 1, R.HOLDOUT_FIRST_TS_NS + 2]
            t = pa.table({"ts_utc_ns": pa.array(ts, pa.int64()), "trade_date": pa.array([20260929, 20260929, 20260930, 20260930], pa.int32())})
            p = root / "data" / "GC_ticks.parquet"
            pq.write_table(t, p, row_group_size=2)
            (root / "release_manifest.json").write_text(json.dumps({"schema": R.SCHEMA, "assets": {"GC": {"file": "data/GC_ticks.parquet", "bytes": p.stat().st_size,
                                                                     "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "rows": 4}}}), encoding="utf-8")
            with self.assertRaises(R.ReleaseStop):
                R.read_asset(root, "GC", 20260929, 20260930, columns=["ts_utc_ns"], purpose="provisional_research")
            with self.assertRaises(R.ReleaseStop):
                R.read_asset(root, "GC", 20260929, 20260929, columns=["ts_utc_ns"], purpose="research")


if __name__ == "__main__":
    unittest.main()

"""Regresiones de la auditoría independiente del 2026-10-14 (LRA-01..06). Todo sintético: no hay datos de mercado.

Cada prueba reproduce un defecto del código de la release v3 y fija la invariancia deseada:
  LRA-01  la decisión de S no puede depender de datos posteriores a D-1 (disponibilidad incluida, no sólo valores)
  LRA-02  spread desconocido = liquidez no demostrada
  LRA-03  MISSING bloquea igual que UNKNOWN
  LRA-04  el lector verifica ambos relojes (ts_utc_ns y trade_date) antes de leer cualquier payload
  LRA-06  el verificador hace el preflight de custodia antes de leer el primer row group
"""
import json
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

from edgelab.data.liquid_release import release_reader as rr  # noqa: E402
from edgelab.data.liquid_release.selection import LiquidityPolicy, select_sessions  # noqa: E402

POL = LiquidityPolicy("t", min_prev_volume=100, min_prev_ticks=10, max_prev_spread_p50_ticks=4.0)
CAL = [20260102, 20260105, 20260106, 20260107, 20260108, 20260109]


def row(contract, d, vol=1000.0, n=500, sp=1.0, cov="OK"):
    return dict(contract=contract, trade_date=d, vol=vol, n=n, spread_p50=sp, coverage=cov)


def decisions(rows, cal=CAL, pol=POL):
    return select_sessions(pd.DataFrame(rows), cal, pol).set_index("trade_date")


class SeleccionCausal(unittest.TestCase):
    def test_agregar_una_fila_futura_no_cambia_decisiones_anteriores(self):
        base = [row("ES 03-26", d, vol=5000) for d in CAL[:4]] + [row("ES 06-26", 20260102, vol=4000), row("ES 06-26", 20260105, vol=4000)]
        sin = decisions(base)
        con = decisions(base + [row("ES 06-26", 20260108, vol=4000)])       # sólo una fila POSTERIOR a S=20260107
        for s in (20260105, 20260106, 20260107):
            self.assertEqual(sin.loc[s, "status"], con.loc[s, "status"], f"S={s} cambió por una fila futura")
            self.assertEqual(str(sin.loc[s, "contract"]), str(con.loc[s, "contract"]))

    def test_invariancia_por_prefijos(self):
        rng = np.random.default_rng(7)
        rows = []
        for k, base in (("ES 03-26", 6000), ("ES 06-26", 3000)):
            for d in CAL:
                if rng.random() < 0.85:
                    rows.append(row(k, d, vol=float(base * rng.uniform(0.6, 1.4))))
        full = decisions(rows)
        for i in range(1, len(CAL)):
            pref = decisions([r for r in rows if r["trade_date"] <= CAL[i - 1]], cal=CAL[:i + 1])
            S = CAL[i]
            self.assertEqual((full.loc[S, "status"], str(full.loc[S, "contract"])), (pref.loc[S, "status"], str(pref.loc[S, "contract"])),
                             f"decisión de {S} depende de datos posteriores a su D-1")

    def test_spread_desconocido_no_es_elegible(self):
        for sp in (None, float("nan")):
            d = decisions([row("ES 03-26", x, sp=sp) for x in CAL[:3]], cal=CAL[:3])
            self.assertEqual(d.loc[20260105, "status"], "NO_ELIGIBLE")
        ok = decisions([row("ES 03-26", x, sp=2.0) for x in CAL[:3]], cal=CAL[:3])
        self.assertEqual(ok.loc[20260105, "status"], "SELECTED")
        caro = decisions([row("ES 03-26", x, sp=9.0) for x in CAL[:3]], cal=CAL[:3])
        self.assertEqual(caro.loc[20260105, "status"], "NO_ELIGIBLE")

    def test_spread_desconocido_solo_con_excepcion_explicita(self):
        pol = LiquidityPolicy("t", 100, 10, 4.0, allow_unknown_spread=True)
        d = decisions([row("ES 03-26", x, sp=None) for x in CAL[:3]], cal=CAL[:3], pol=pol)
        self.assertEqual(d.loc[20260105, "status"], "SELECTED")

    def test_missing_bloquea_como_unknown(self):
        rows = [row("ES 03-26", d, vol=5000) for d in CAL[:3]] + [row("ES 06-26", 20260102, vol=4500), row("ES 06-26", 20260105, vol=4500, cov="MISSING")]
        d = decisions(rows, cal=CAL[:4])
        self.assertEqual(d.loc[20260106, "status"], "UNDETERMINED")

    def test_parametros_de_politica_invalidos(self):
        for bad in (dict(min_prev_volume=float("nan")), dict(min_prev_ticks=-1), dict(max_prev_spread_p50_ticks=float("inf"))):
            kw = dict(version="t", min_prev_volume=1.0, min_prev_ticks=1, max_prev_spread_p50_ticks=2.0)
            kw.update(bad)
            with self.assertRaises(ValueError):
                LiquidityPolicy(**kw)


def write_parquet(path, trade_dates, ts, row_group_size=2, with_stats=True):
    t = pa.table({"ts_utc_ns": pa.array(ts, pa.int64()), "trade_date": pa.array(trade_dates, pa.int32()),
                  "price_ticks": pa.array([1] * len(ts), pa.int64())})
    pq.write_table(t, path, row_group_size=row_group_size, write_statistics=with_stats)


class Spy:
    """Cuenta lecturas de payload sobre un ParquetFile."""

    def __init__(self, monkey):
        self.reads = 0
        orig_g, orig_rg = pq.ParquetFile.read_row_group, pq.ParquetFile.read_row_groups
        spy = self

        def g(self_, *a, **k):
            spy.reads += 1
            return orig_g(self_, *a, **k)

        def gs(self_, *a, **k):
            spy.reads += 1
            return orig_rg(self_, *a, **k)

        pq.ParquetFile.read_row_group, pq.ParquetFile.read_row_groups = g, gs
        monkey.addCleanup(lambda: (setattr(pq.ParquetFile, "read_row_group", orig_g), setattr(pq.ParquetFile, "read_row_groups", orig_rg)))


class CustodiaDeLectura(unittest.TestCase):
    CUT = getattr(rr, "HOLDOUT_FIRST_TS_NS", 1_790_805_600_000_000_000)

    def _release(self, tmp, trade_dates, ts, **kw):
        root = Path(tmp)
        (root / "data").mkdir()
        p = root / "data" / "ES_ticks.parquet"
        write_parquet(p, trade_dates, ts, **kw)
        import hashlib
        man = dict(schema=rr.SCHEMA, assets={"ES": dict(file="data/ES_ticks.parquet", bytes=p.stat().st_size,
                                                          sha256=hashlib.sha256(p.read_bytes()).hexdigest(), rows=len(ts))})
        (root / "release_manifest.json").write_text(json.dumps(man), encoding="utf-8")
        return root

    def test_timestamp_reservado_con_trade_date_mal_rotulado_no_se_lee(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._release(tmp, [20260929, 20260929, 20260930, 20260930], [1, 2, self.CUT + 5, self.CUT + 9])
            spy = Spy(self)
            with self.assertRaises(rr.ReleaseStop):
                rr.read_asset(root, "ES", 20260929, 20260930, purpose="audit")
            self.assertEqual(spy.reads, 0, "se leyó payload de un archivo con timestamp reservado")

    def test_footer_sin_estadisticas_de_ts_no_se_lee(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._release(tmp, [20260929] * 4, [1, 2, 3, 4], with_stats=False)
            spy = Spy(self)
            with self.assertRaises(rr.ReleaseStop):
                rr.read_asset(root, "ES", 20260929, 20260929, purpose="audit")
            self.assertEqual(spy.reads, 0)

    def test_grupo_reservado_fuera_del_rango_pedido_tambien_detiene(self):
        with tempfile.TemporaryDirectory() as tmp:           # el archivo es inválido aunque lo pedido sea una fecha limpia
            root = self._release(tmp, [20260101, 20260101, 20260930, 20260930], [1, 2, self.CUT + 1, self.CUT + 2])
            spy = Spy(self)
            with self.assertRaises(rr.ReleaseStop):
                rr.read_asset(root, "ES", 20260101, 20260101, purpose="audit")
            self.assertEqual(spy.reads, 0)

    def test_archivo_limpio_se_lee(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._release(tmp, [20260101, 20260101, 20260102, 20260102], [1, 2, 3, 4])
            self.assertEqual(rr.read_asset(root, "ES", 20260101, 20260102, purpose="audit").num_rows, 4)

    def test_verificador_hace_preflight_antes_de_leer(self):
        import verify_release as vr
        with tempfile.TemporaryDirectory() as tmp:
            root = self._release(tmp, [20260929, 20260929, 20260930, 20260930], [1, 2, self.CUT + 5, self.CUT + 9])
            spy = Spy(self)
            info = dict(file="data/ES_ticks.parquet", rows=4)
            with self.assertRaises(rr.ReleaseStop):
                vr.verify_asset("ES", info, root, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
            self.assertEqual(spy.reads, 0, "el verificador leyó un row group reservado antes de rechazarlo")


class Admision(unittest.TestCase):
    def _root(self, tmp, **extra):
        root = CustodiaDeLectura()._release(tmp, [20260101, 20260101], [1, 2])
        m = json.loads((root / "release_manifest.json").read_text(encoding="utf-8"))
        m.update(extra)
        (root / "release_manifest.json").write_text(json.dumps(m), encoding="utf-8")
        return root

    def test_purpose_es_obligatorio(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            with self.assertRaises(rr.ReleaseStop):
                rr.load_manifest(root)
            with self.assertRaises(rr.ReleaseStop):
                rr.load_manifest(root, purpose="cualquier cosa")

    def test_research_exige_aprobacion_atada_al_hash_del_manifiesto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, research_allowed=False)
            with self.assertRaises(rr.ReleaseStop):
                rr.load_manifest(root, purpose="research")                          # sin release_approval.json
            self.assertEqual(len(rr.load_manifest(root, purpose="audit")), 1)         # auditoría sí puede examinar la candidata
            self.assertEqual(len(rr.load_manifest(root, purpose="provisional_research")), 1)
            (root / rr.APPROVAL_FILE).write_text(json.dumps(dict(manifest_sha256="0" * 64, approved_by="Nico", liquidity_policy_approved=True)), encoding="utf-8")
            with self.assertRaises(rr.ReleaseStop):
                rr.load_manifest(root, purpose="research")                          # atada a otro manifiesto
            m = json.loads((root / "release_manifest.json").read_text(encoding="utf-8"))
            m["research_allowed"] = True
            (root / "release_manifest.json").write_text(json.dumps(m), encoding="utf-8")
            (root / rr.APPROVAL_FILE).write_text(json.dumps(dict(manifest_sha256=rr.sha256_file(root / "release_manifest.json"),
                                                                 approved_by="Nico", liquidity_policy_approved=True)), encoding="utf-8")
            self.assertEqual(len(rr.load_manifest(root, purpose="research")), 1)
            with self.assertRaises(rr.ReleaseStop):
                rr.load_manifest(root, purpose="research", verify_hash=False)       # sin atajos para research

    def test_metadata_files_listados_pero_ausentes_o_alterados_detienen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, metadata_files={"metadata/fantasma.json": {"sha256": "0" * 64, "bytes": 3}})
            with self.assertRaises(rr.ReleaseStop):
                rr.load_manifest(root, purpose="audit")
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, metadata_files={"metadata/x.json": {"sha256": "0" * 64, "bytes": 2}})
            (root / "metadata").mkdir()
            (root / "metadata" / "x.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(rr.ReleaseStop):
                rr.load_manifest(root, purpose="audit")                              # tamaño ok, SHA distinto


class PoliticaProspectiva(unittest.TestCase):
    def test_la_politica_no_depende_de_sesiones_posteriores_a_la_ventana(self):
        from edgelab.data.liquid_release import plan as P
        d = pd.date_range("2026-01-05", periods=200, freq="B").strftime("%Y%m%d").astype(int)
        base = pd.DataFrame(dict(instrument="ES", contract="ES 03-26", trade_date=d, vol_reg=1000.0, n_reg=500, spread_p50=1.0))
        futuro = base.copy()
        futuro.loc[futuro.index >= P.CALIBRATION_SESSIONS, "vol_reg"] = 10_000_000.0     # cambia sólo lo posterior a la ventana
        a, b = P.propose_policy(base, "ES"), P.propose_policy(futuro, "ES")
        self.assertEqual((a.min_prev_volume, a.min_prev_ticks, a.max_prev_spread_p50_ticks),
                         (b.min_prev_volume, b.min_prev_ticks, b.max_prev_spread_p50_ticks))
        self.assertIn("in-sample", a.notes)


if __name__ == "__main__":
    unittest.main()

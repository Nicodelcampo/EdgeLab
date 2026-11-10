"""Tests de paridad NT8 SQLite, causalidad estricta por truncado y controles sintéticos para HFT-GC-P10."""
from __future__ import annotations

from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import pytest

from edgelab.bridge.indicators import hft_gc_cluster_p10 as HGC
from edgelab.research import grilla_generica as GG, hft_gc_cluster_p10 as EXP, indicadores as I, sintetico

SQLITE_NT8 = Path(r"C:\LoggerHFT\data\hft_logger_gc_cluster_p10.sqlite")


def test_causal():
    ctx = GG.contexto_m1(sintetico.bloques(dias=80, planta=False, seed=11, t0_s=EXP.PREFLIGHT_T0_S), tick=0.10)
    assert I.causal(EXP.disparos, ctx) == []
    assert I.causal_por_disparo(EXP.disparos, ctx, n=25) == []


def test_libro_barreras_hft_no_mira_el_futuro():
    ctx = GG.contexto_m1(sintetico.bloques(dias=40, planta=False, seed=7, t0_s=EXP.PREFLIGHT_T0_S), tick=0.10)
    fuente_full = EXP._fuente_sintetica_causal(ctx)
    libro_full = HGC.LibroBarrerasHFT(
        fuente_full["HFTGCP10"], fuente_full["HFTGCP10_CLUST"], ctx["t"], ctx["h"], ctx["l"], vida_m1=360
    )
    k = len(ctx["c"]) // 2
    ctx_pre = I._prefijo(ctx, k + 1)
    fuente_pre = EXP._fuente_sintetica_causal(ctx_pre)
    libro_pre = HGC.LibroBarrerasHFT(
        fuente_pre["HFTGCP10"], fuente_pre["HFTGCP10_CLUST"], ctx_pre["t"], ctx_pre["h"], ctx_pre["l"], vida_m1=360
    )
    p0 = float(ctx["c"][k]) - 3.0
    p1 = float(ctx["c"][k]) + 3.0
    for solo_gris in (False, True):
        z_a = libro_full.zonas_en_recorrido(k, p0, p1, solo_no_mitigadas=True, solo_borde_gris=solo_gris)
        z_b = libro_pre.zonas_en_recorrido(k, p0, p1, solo_no_mitigadas=True, solo_borde_gris=solo_gris)
        assert list(z_a["zone_id"]) == list(z_b["zone_id"])


def test_control_ruido():
    old_b = GG.B_RW
    GG.B_RW = 40
    try:
        ctx = GG.contexto_m1(sintetico.bloques(dias=150, planta=False, seed=11, t0_s=EXP.PREFLIGHT_T0_S), tick=0.25)
        D = EXP.disparos(ctx)
        assert len(D) > 100
        cortes = GG.cortes_e0(D, EXP.VARIABLES)
        res, _ = GG.correr(EXP, ctx, modo="DESC", friccion=1.0, extra_adverso=0.5, cortes=cortes, log=lambda s: None)
        assert res["canales"]["total"]["evaluables"] > 0
        assert res["canales"]["total"]["nominadas_fdr"] == 0
    finally:
        GG.B_RW = old_b


def test_control_plantado():
    ctx_p = GG.contexto_m1(sintetico.bloques(dias=50, planta=True, seed=3, t0_s=EXP.PREFLIGHT_T0_S), tick=0.25)
    ctx_r = GG.contexto_m1(sintetico.bloques(dias=50, planta=False, seed=3, t0_s=EXP.PREFLIGHT_T0_S), tick=0.25)
    Dp = EXP.disparos(ctx_p).reset_index(drop=True)
    Dr = EXP.disparos(ctx_r).reset_index(drop=True)
    di_p, _, pnl_p, _, _ = GG.simular_ops(EXP, Dp, ctx_p)
    di_r, _, pnl_r, _, _ = GG.simular_ops(EXP, Dr, ctx_r)
    assert float(np.nanmean(pnl_p)) > float(np.nanmean(pnl_r)) + 1.5
    mec_p = Dp["mec"].to_numpy(np.int64)[di_p]
    mec_r = Dr["mec"].to_numpy(np.int64)[di_r]
    assert float(np.nanmean(pnl_p[mec_p == 0])) > float(np.nanmean(pnl_r[mec_r == 0])) + 2.0
    assert float(np.nanmean(pnl_p[mec_p == 3])) > float(np.nanmean(pnl_r[mec_r == 3])) + 2.0


@pytest.mark.skipif(not SQLITE_NT8.exists(), reason="SQLite de NT8 local no presente en este entorno")
def test_paridad_sqlite_nt8():
    con = sqlite3.connect(str(SQLITE_NT8))
    try:
        rid = con.execute("SELECT MAX(run_id) FROM logger_runs").fetchone()[0]
        z = pd.read_sql_query(f"SELECT * FROM hft_zones WHERE run_id={rid} ORDER BY zone_id", con)
        b = pd.read_sql_query(f"SELECT * FROM primary_bars WHERE run_id={rid} ORDER BY bar_idx", con)
        c = pd.read_sql_query(f"SELECT * FROM hft_clusters_p10 WHERE run_id={rid} ORDER BY event_seq", con)
        a = pd.read_sql_query(f"SELECT * FROM hft_away_events WHERE run_id={rid} ORDER BY zone_id", con)
    finally:
        con.close()

    b_map = {"Predator": 0, "Ultra": 1, "Fast": 2, "Absorb": 3}
    zb = z["bucket"].map(b_map).to_numpy(np.int64)
    cl_cols, cl_df = HGC.evaluar_clusters_p10_causal(
        z["start_bar"].to_numpy(np.int64),
        z["end_bar"].to_numpy(np.int64),
        z["end_ts"].to_numpy(np.int64) * 10**6,
        z["lower_tick"].to_numpy(np.int64),
        z["upper_tick"].to_numpy(np.int64),
        zb,
        z["total_vol"].to_numpy(float),
        z["market_clock_sec"].to_numpy(float),
    )
    assert int((cl_cols["min4_height_ticks"] != z["min4_height_ticks"].to_numpy()).sum()) == 0
    assert int((cl_cols["p10_threshold_ticks"] != z["p10_threshold_ticks"].to_numpy()).sum()) == 0
    assert int((cl_cols["triggered_cluster"] != z["triggered_cluster"].to_numpy()).sum()) == 0
    assert len(cl_df) == len(c)
    assert int((cl_df["event_type"].to_numpy() != c["event_type"].to_numpy()).sum()) == 0
    assert float(np.max(np.abs(cl_df["poc"].to_numpy() - c["poc_price"].to_numpy()))) == 0.0

    b_hi = np.zeros(int(b["bar_idx"].max()) + 1, np.float64)
    b_lo = np.zeros_like(b_hi)
    b_ns = np.zeros(len(b_hi), np.int64)
    idx = b["bar_idx"].to_numpy(np.int64)
    b_hi[idx] = b["high"].to_numpy(np.float64)
    b_lo[idx] = b["low"].to_numpy(np.float64)
    b_ns[idx] = b["close_ts"].to_numpy(np.int64) * 10**6

    z_m = z.merge(a, on="zone_id")
    base_b = np.maximum(z_m["end_bar"].to_numpy(np.int64), z_m["drawn_bar"].to_numpy(np.int64))
    rc, ad, ab, _ = HGC.resolver_alejamiento_barras_nb(
        base_b,
        z_m["price_lower"].to_numpy(np.float64),
        z_m["price_upper"].to_numpy(np.float64),
        z_m["dir"].to_numpy(np.int64),
        z_m["bucket"].map(b_map).to_numpy(np.int64),
        z_m["end_price"].to_numpy(np.float64),
        b_ns,
        b_hi,
        b_lo,
        0.10,
    )
    inv = {v: k for k, v in HGC.AWAY_RES_CODES.items()}
    rc_s = np.array([inv[x] for x in rc])
    assert int((rc_s != z_m["resolution"].to_numpy()).sum()) == 0
    assert int((ab != z_m["resolved_bar"].to_numpy()).sum()) == 0


def test_almacen_gc_numba_compila():
    ts = 1_760_000_000 * 10**9 + np.r_[np.arange(80) * 2_000_000, 500_000_000 + np.arange(80) * 10_000_000]
    px = 4000.0 + np.r_[(np.arange(80) // 3) * 0.10, 3.0 + (np.arange(80) % 5) * 0.10]
    bl = [pd.DataFrame(dict(ts_ns=ts, px=px, vol=np.full(len(ts), 15.0), sesion=np.full(len(ts), 20260910), segmento=np.zeros(len(ts), int)))]
    out = HGC.almacen_gc(bl, tick=0.10, spec=50)
    assert len(out["HFTGCP10"]) >= 1
    out_vacio = HGC.almacen_gc([], tick=0.10, spec=50)
    assert len(out_vacio["HFTGCP10"]) == 0
    assert int((ad != z_m["away_dir"].to_numpy()).sum()) == 0

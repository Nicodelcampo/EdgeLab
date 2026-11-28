#!/usr/bin/env python3
"""Despliegue P_OPT_SF_v2 FUNDEDSYNC: Integracion LucidFlex, K30 Ticks, Holdout y Multi-Prop Firm.

Pre-registro: docs/research/fundedsync_deploy_multiprop_20261122/PREREGISTRO.md (K51: 39 pruebas).

Uso:
  python tools/fundedsync_integracion_multiprop.py etapa_a [--workers 2]
  python tools/fundedsync_integracion_multiprop.py etapa_b [--workers 2]
  python tools/fundedsync_integracion_multiprop.py etapa_c [--workers 2]
  python tools/fundedsync_integracion_multiprop.py graficos
  python tools/fundedsync_integracion_multiprop.py todo [--workers 2]
"""
from __future__ import annotations

import argparse
import dataclasses
import gc
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from numba import njit

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import fundedsync_iter2_cartera as IT2
import fundedsync_multiactivo_oro as M
import fundedsync_post_il_cadena as BASE
import fundedsync_prop_opt as OPT
import lucid_guia as LG
from edgelab import costos
from edgelab.holdout import (
    HOLDOUT_APERTURA_UTC_NS,
    HOLDOUT_PRIMERA_SESION_INT,
    a5_bloque,
    sesion_excluida,
)
from edgelab.research import a5 as A5
from edgelab.research.fundedsyncstack import build_multi_series, correr_modulo, load_m1_data
from edgelab.research.m1_intradia import SERVIDOR_MENOS_NY, leer_m1nt8
from edgelab.research.puerta_corrida import verificar_corrida
from edgelab.research.quantlab_mt5 import correr_session_open_momentum
from edgelab.research.quantlab_mt5.contracts import SessionOpenMomentumConfig
from registro_global import exigir_contada

PREREG_REL = "docs/research/fundedsync_deploy_multiprop_20261122/PREREGISTRO.md"
OUT_DIR = ROOT / "docs/research/fundedsync_deploy_multiprop_20261122"
CATALOGO_MULTIPROP_JSON = OUT_DIR / "catalogo_multiprop_20261122.json"
TICKS_K30_PARQUET = ROOT / "data/ticks_nq_calibracion/NQ_ticks.parquet"
SELLADO_NQ_DIR = Path(r"C:\EdgeLab\sellado")
ARTIFACTS_DIR = BASE.ARTIFACTS_DIR

CORE7_SPECS: dict[str, dict[str, Any]] = {
    "R_osc30_end660_ATR50": {
        "modulo": "R",
        "params": {"osc_atr_mult": 3.0, "entry_end_min_et": 660},
        "overlay": {"sl_atr_k": 0.50},
    },
    "Z_b15_e20_eff40_ATR50": {
        "modulo": "Z",
        "params": {"bucket_minutes": 15, "ema_period": 20, "min_efficiency_pct": 40.0},
        "overlay": {"sl_atr_k": 0.50},
    },
    "T_stop100_BE15R_calFalse": {
        "modulo": "T",
        "params": {"use_exclusion_calendars": False},
        "overlay": {"stop_orb_mult": 1.0, "stop_min_pts": 2.0, "stop_max_pts": 100.0, "be_trigger_r": 1.5},
    },
    "V_nm25_noCap_mae30": {
        "modulo": "V",
        "params": {"noise_multiplier": 0.25, "profit_target_usd_per_contract": 99999.0, "stop_loss_usd_per_contract": 99999.0},
        "overlay": {"sl_atr_k": 0.30},
    },
    "W_slope_allowReFalse_ATR25": {
        "modulo": "W",
        "params": {"exit_on_vwap_cross": False, "use_vwap_slope_filter": True, "allow_reentries": False},
        "overlay": {"sl_atr_k": 0.25},
    },
    "W_slope_allowReFalse_trail_15_50_ATR25": {
        "modulo": "W",
        "params": {"exit_on_vwap_cross": False, "use_vwap_slope_filter": True, "allow_reentries": False},
        "overlay": {"sl_atr_k": 0.25, "trail_tiers": ((1.5, 0.5), (2.5, 1.5))},
    },
    "N_d5_fbTrue_ATR25": {
        "modulo": "N",
        "params": {},
        "overlay": {"sl_atr_k": 0.25},
    },
}


def asegurar_compuerta_deploy() -> None:
    """Verifica K51 (`TRIAL_REGISTRY_GLOBAL`) y compuerta L1..L4 antes de correr."""
    exigir_contada(PREREG_REL)
    rep = verificar_corrida(
        prereg=PREREG_REL,
        familia="FUNDEDSYNC",
        exigir_contada=True,
        verificar_estado=True,
        root=ROOT,
    )
    if not rep["ok"]:
        raise SystemExit("puerta_corrida bloqueo deploy: " + "; ".join(rep["errores"]))


def _m1_ny_a_arrays(m1_ny: pd.DataFrame) -> dict[str, np.ndarray]:
    """Convierte DataFrame M1 con indice NY naive a arrays contiguos UTC ns para Numba."""
    ts_utc = m1_ny.index.tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward").tz_convert("UTC")
    valid = ts_utc.notna()
    d = m1_ny.loc[valid]
    ts_ns = OPT._idx_utc_ns(ts_utc[valid])
    order = np.argsort(ts_ns, kind="mergesort")
    return {
        "ts_ns": np.ascontiguousarray(ts_ns[order], dtype=np.int64),
        "o": np.ascontiguousarray(d["o"].to_numpy(dtype=np.float64)[order]),
        "h": np.ascontiguousarray(d["h"].to_numpy(dtype=np.float64)[order]),
        "l": np.ascontiguousarray(d["l"].to_numpy(dtype=np.float64)[order]),
        "c": np.ascontiguousarray(d["c"].to_numpy(dtype=np.float64)[order]),
    }


def _reinyectar_campos_ops(
    tr_df: pd.DataFrame,
    ops_streams: Mapping[str, pd.DataFrame],
    fric_nq: float,
) -> pd.DataFrame:
    """Preserva mae_pts, mfe_pts, R_bruto y fechas exactas tras aplicar_tope_concurrencia_causal."""
    if tr_df is None or tr_df.empty:
        return tr_df
    extras = []
    for sid, df in ops_streams.items():
        if df is not None and not df.empty:
            cols = ["en_ns", "ex_ns", "R_bruto"]
            for opt_c in ("mae_pts", "mfe_pts", "entry_price", "exit_price", "stop_price"):
                if opt_c in df.columns:
                    cols.append(opt_c)
            sub = df[cols].copy()
            sub["stream"] = sid
            extras.append(sub)
    out = tr_df.copy()
    if extras:
        agg_spec: dict[str, Any] = {"R_bruto": ("R_bruto", "first")}
        merged_src = pd.concat(extras, ignore_index=True)
        for col, fn in (("mae_pts", "max"), ("mfe_pts", "max"), ("entry_price", "first"), ("exit_price", "first"), ("stop_price", "first")):
            if col in merged_src.columns:
                agg_spec[col] = (col, fn)
        meta_ext = merged_src.groupby(["stream", "en_ns", "ex_ns"], as_index=False).agg(**agg_spec)
        out = out.merge(meta_ext, on=["stream", "en_ns", "ex_ns"], how="left")
    if "R_bruto" not in out.columns:
        out["R_bruto"] = np.nan
    fb_r = out["R_neto_mini"].to_numpy(float) + float(fric_nq) / np.maximum(out["riesgo_pts"].to_numpy(float), 1e-6)
    out["R_bruto"] = out["R_bruto"].fillna(pd.Series(fb_r, index=out.index))
    for col, fb in (
        ("mae_pts", np.maximum(-out["R_bruto"].to_numpy(float) * out["riesgo_pts"].to_numpy(float), 0.0)),
        ("mfe_pts", np.maximum(out["R_bruto"].to_numpy(float) * out["riesgo_pts"].to_numpy(float), 0.0)),
    ):
        if col not in out.columns:
            out[col] = np.nan
        out[col] = out[col].fillna(pd.Series(fb, index=out.index))
    return out


# ---------------------------------------------------------------------------
# 1. Generacion SOMEOD exacto desde M1 y Overlay sin filtro A5 (soporte HOLDOUT)
# ---------------------------------------------------------------------------


def generar_ops_someod_desde_m1(
    m1_ny: pd.DataFrame,
    fric_nq: float,
    fric_mnq: float,
    *,
    incluir_terminal: bool = False,
) -> pd.DataFrame:
    """Corre SessionOpenMomentum EOD exacto sobre M1 NQ y calcula MAE/MFE reales barra a barra."""
    srv = (m1_ny.index + pd.Timedelta(hours=SERVIDOR_MENOS_NY)).tz_localize("UTC")
    df_som = pd.DataFrame({
        "time": srv,
        "ts_ns": OPT._idx_utc_ns(srv),
        "open": m1_ny["o"].to_numpy(dtype=np.float64),
        "high": m1_ny["h"].to_numpy(dtype=np.float64),
        "low": m1_ny["l"].to_numpy(dtype=np.float64),
        "close": m1_ny["c"].to_numpy(dtype=np.float64),
        "volume": m1_ny["v"].to_numpy(dtype=np.float64),
    })
    cfg = dataclasses.replace(SessionOpenMomentumConfig(), close_eod=True)
    raw = correr_session_open_momentum(df_som, config=cfg, instrument="USATECH")
    if raw is None or raw.empty:
        return pd.DataFrame()

    # Convertir marcas de reloj servidor MT5 (NY naive + 7h) -> UTC ns real de NY
    en_ny = pd.to_datetime(raw["entry_time_utc"].to_numpy(dtype=np.int64), unit="ns") - pd.Timedelta(hours=SERVIDOR_MENOS_NY)
    ex_ny = pd.to_datetime(raw["exit_time_utc"].to_numpy(dtype=np.int64), unit="ns") - pd.Timedelta(hours=SERVIDOR_MENOS_NY)
    en_utc = pd.DatetimeIndex(en_ny).tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward").tz_convert("UTC")
    ex_utc = pd.DatetimeIndex(ex_ny).tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward").tz_convert("UTC")

    en_ns = OPT._idx_utc_ns(en_utc)
    ex_ns = np.maximum(OPT._idx_utc_ns(ex_utc), en_ns)
    ses_dt = (pd.DatetimeIndex(en_ny) + pd.Timedelta(hours=6)).normalize()
    fecha_int = ses_dt.strftime("%Y%m%d").astype(np.int64).to_numpy()
    a5_arr = np.array([a5_bloque(int(f)) for f in fecha_int], dtype=object)

    riesgo = (raw["entry_price"].to_numpy(dtype=np.float64) - raw["stop_price"].to_numpy(dtype=np.float64))
    riesgo = np.abs(riesgo)
    bruto = raw["pnl_pts"].to_numpy(dtype=np.float64)
    side = raw["side"].to_numpy(dtype=np.int64)
    en_p = raw["entry_price"].to_numpy(dtype=np.float64)
    ex_p = raw["exit_price"].to_numpy(dtype=np.float64)
    st_p = raw["stop_price"].to_numpy(dtype=np.float64)
    # En M5 QuantLab, mae_usd y mfe_usd estan expresados en USD del contrato USATECH ($20/pt)
    qty = np.maximum(pd.to_numeric(raw["qty"], errors="coerce").fillna(1.0).to_numpy(dtype=np.float64), 1e-6)
    mae_pts = np.abs(raw["mae_usd"].to_numpy(dtype=np.float64)) / (qty * 20.0)
    mfe_pts = np.abs(raw["mfe_usd"].to_numpy(dtype=np.float64)) / (qty * 20.0)

    # Refinar mae_pts/mfe_pts barra a barra en M1 dentro de [en_ns, ex_ns) para exactitud intradia
    m1_arr = _m1_ny_a_arrays(m1_ny)
    ts_m1 = m1_arr["ts_ns"]
    h_m1, l_m1 = m1_arr["h"], m1_arr["l"]
    mae_ref = mae_pts.copy()
    mfe_ref = mfe_pts.copy()
    if len(ts_m1) > 0:
        for k in range(len(en_ns)):
            i0 = int(np.searchsorted(ts_m1, en_ns[k], side="left"))
            i1 = int(np.searchsorted(ts_m1, ex_ns[k], side="right")) - 1
            if 0 <= i0 <= i1 < len(ts_m1):
                hi_s = float(np.max(h_m1[i0 : i1 + 1]))
                lo_s = float(np.min(l_m1[i0 : i1 + 1]))
                if side[k] >= 0:
                    mae_ref[k] = max(0.0, en_p[k] - min(lo_s, ex_p[k]), -bruto[k])
                    mfe_ref[k] = max(0.0, max(hi_s, ex_p[k]) - en_p[k], bruto[k])
                else:
                    mae_ref[k] = max(0.0, max(hi_s, ex_p[k]) - en_p[k], -bruto[k])
                    mfe_ref[k] = max(0.0, en_p[k] - min(lo_s, ex_p[k]), bruto[k])
            mae_ref[k] = min(mae_ref[k], riesgo[k])

    ok = (
        np.isfinite(riesgo) & (riesgo > 1e-6) & np.isfinite(bruto) & (fecha_int >= 20080101)
        & np.asarray(en_utc.notna(), dtype=bool) & np.asarray(ex_utc.notna(), dtype=bool)
    )
    if not incluir_terminal:
        ok = ok & (en_ns < HOLDOUT_APERTURA_UTC_NS) & (a5_arr != "TERMINAL")

    riesgo_k = riesgo[ok]
    bruto_k = bruto[ok]
    return pd.DataFrame({
        "fecha_int": fecha_int[ok],
        "mes": ses_dt.strftime("%Y-%m").to_numpy()[ok],
        "a5": a5_arr[ok],
        "en_ns": en_ns[ok],
        "ex_ns": ex_ns[ok],
        "dur_min": np.maximum((ex_ns[ok] - en_ns[ok]) / 60_000_000_000.0, 0.0),
        "pnl_pts": bruto_k,
        "mae_pts": mae_ref[ok],
        "mfe_pts": mfe_ref[ok],
        "riesgo_pts": riesgo_k,
        "R_bruto": bruto_k / riesgo_k,
        "R_neto_mini": (bruto_k - float(fric_nq)) / riesgo_k,
        "R_neto_micro": (bruto_k - float(fric_mnq)) / riesgo_k,
        "fric_R": float(fric_nq) / riesgo_k,
        "side": side[ok],
        "entry_price": en_p[ok],
        "exit_price": ex_p[ok],
        "stop_price": st_p[ok],
        "exit_name": raw["exit_name"].to_numpy()[ok],
    }).reset_index(drop=True)


def overlay_m1_por_particion(
    df_trades: pd.DataFrame,
    modulo: str,
    atr_ses: pd.Series,
    orb_raw: pd.Series,
    m1_arrays: Mapping[str, np.ndarray],
    fric_nq: float,
    fric_mnq: float,
    *,
    particiones_ok: tuple[str, ...],
    permitir_terminal: bool = False,
    sl_atr_k: float | None = None,
    tp_atr_k: float | None = None,
    be_trigger_r: float | None = None,
    trail_tiers: tuple[tuple[float, float], ...] | None = None,
    tp_r: float | None = None,
    stop_orb_mult: float = 1.25,
    stop_min_pts: float = 2.0,
    stop_max_pts: float = 100.0,
) -> pd.DataFrame:
    """Aplica overlay M1 causal sobre trades preservando particiones seleccionadas y precios base."""
    if df_trades is None or df_trades.empty:
        return pd.DataFrame()
    df = df_trades.copy()
    en_ns_all, en_dt = OPT._col_a_ns_y_dt(df["entry_time_utc"])
    ex_ns_all, _ = OPT._col_a_ns_y_dt(df["exit_time_utc"])

    ok = np.ones(len(df), dtype=bool)
    if not permitir_terminal:
        ok &= en_ns_all < HOLDOUT_APERTURA_UTC_NS

    en_ny = en_dt.dt.tz_convert("America/New_York").dt.tz_localize(None)
    ses_dt = (en_ny + pd.Timedelta(hours=6)).dt.normalize()
    fecha_int = ses_dt.dt.strftime("%Y%m%d").astype(np.int64)
    a5_arr = pd.Series([a5_bloque(int(f)) for f in fecha_int], index=df.index)
    ok &= a5_arr.isin(particiones_ok).to_numpy()
    if not ok.any():
        return pd.DataFrame()

    df = df.loc[ok].reset_index(drop=True)
    ses_dt = ses_dt.loc[ok].reset_index(drop=True)
    fecha_int = fecha_int.loc[ok].reset_index(drop=True)
    a5_arr = a5_arr.loc[ok].reset_index(drop=True)
    en_ns = en_ns_all[ok]
    ex_ns = ex_ns_all[ok]

    side = df["side"].to_numpy(dtype=np.int64)
    en_p = df["entry_price"].to_numpy(dtype=np.float64)
    ex_p = df["exit_price"].to_numpy(dtype=np.float64)
    stop_p = pd.to_numeric(df["stop_price"], errors="coerce").to_numpy(dtype=np.float64)
    atr_v = atr_ses.reindex(ses_dt).to_numpy(dtype=np.float64)

    if sl_atr_k is not None:
        sl_pts = float(sl_atr_k) * atr_v
    elif modulo == "T":
        orb_v = orb_raw.reindex(ses_dt).to_numpy(dtype=np.float64)
        sl_pts = np.clip(float(stop_orb_mult) * orb_v, float(stop_min_pts), float(stop_max_pts))
    else:
        qty = np.maximum(pd.to_numeric(df.get("qty", 1), errors="coerce").fillna(1.0).to_numpy(dtype=np.float64), 1.0)
        sl_pts = np.abs(en_p - stop_p)
        bad_s = ~np.isfinite(sl_pts) | (sl_pts <= 0.0)
        if bad_s.any():
            sl_pts = np.where(bad_s, np.abs(df["pnl_pts"].to_numpy(dtype=np.float64)) / qty, sl_pts)

    valid_r = np.isfinite(sl_pts) & (sl_pts > 1e-6)
    if not valid_r.any():
        return pd.DataFrame()

    if tp_atr_k is not None:
        tp_pts = np.where(valid_r, float(tp_atr_k) * atr_v, 0.0)
    elif tp_r is not None:
        tp_pts = np.where(valid_r, float(tp_r) * sl_pts, 0.0)
    else:
        tp_pts = np.zeros(len(df), dtype=np.float64)

    ts_ns = m1_arrays["ts_ns"]
    m1_o = m1_arrays["o"]
    ex_names = df["exit_name"].astype(str).str.upper() if "exit_name" in df.columns else pd.Series("", index=df.index)
    is_stop_or_tp = ex_names.str.contains("STOP|TARGET|_TP|_SL", regex=True).to_numpy()
    if len(m1_o) > 0:
        i1_est = np.clip(np.searchsorted(ts_ns, ex_ns, side="right") - 1, 0, len(m1_o) - 1)
        is_mkt_open = (~is_stop_or_tp) & (np.abs(ex_p - m1_o[i1_est]) <= 0.50)
    else:
        is_mkt_open = np.zeros(len(df), dtype=np.bool_)

    t1_tr, t1_lk, t2_tr, t2_lk = -1.0, 0.0, -1.0, 0.0
    if trail_tiers:
        if len(trail_tiers) >= 1:
            t1_tr, t1_lk = float(trail_tiers[0][0]), float(trail_tiers[0][1])
        if len(trail_tiers) >= 2:
            t2_tr, t2_lk = float(trail_tiers[1][0]), float(trail_tiers[1][1])

    sl_pass = np.where(valid_r, sl_pts, 1e9)
    pnl_new, mae_new, mfe_new, ex_ns_new = OPT._evaluar_overlay_m1_numba(
        ts_ns,
        m1_o,
        m1_arrays["h"],
        m1_arrays["l"],
        m1_arrays["c"],
        en_ns,
        ex_ns,
        side,
        en_p,
        ex_p,
        sl_pass,
        tp_pts,
        is_mkt_open.astype(np.bool_),
        float(be_trigger_r) if be_trigger_r is not None else -1.0,
        t1_tr,
        t1_lk,
        t2_tr,
        t2_lk,
    )

    kv = valid_r
    sl_f = sl_pts[kv]
    pnl_f = pnl_new[kv]
    en_f = en_ns[kv]
    ex_f = np.maximum(ex_ns_new[kv], en_f)
    sd_f = side[kv]
    ep_f = en_p[kv]
    stop_calc = ep_f - sd_f * sl_f
    return pd.DataFrame({
        "fecha_int": fecha_int.to_numpy()[kv],
        "mes": ses_dt.dt.strftime("%Y-%m").to_numpy()[kv],
        "a5": a5_arr.to_numpy()[kv],
        "en_ns": en_f,
        "ex_ns": ex_f,
        "dur_min": np.maximum((ex_f - en_f) / 60_000_000_000.0, 0.0),
        "pnl_pts": pnl_f,
        "mae_pts": mae_new[kv],
        "mfe_pts": mfe_new[kv],
        "riesgo_pts": sl_f,
        "R_bruto": pnl_f / sl_f,
        "R_neto_mini": (pnl_f - float(fric_nq)) / sl_f,
        "R_neto_micro": (pnl_f - float(fric_mnq)) / sl_f,
        "fric_R": float(fric_nq) / sl_f,
        "side": sd_f,
        "entry_price": ep_f,
        "exit_price": ep_f + sd_f * pnl_f,
        "stop_price": stop_calc,
        "exit_name": df["exit_name"].to_numpy()[kv] if "exit_name" in df.columns else "",
    }).reset_index(drop=True)


def construir_ops_todos_modulos_pre(
    m1_dir: Path | None = None,
    workers: int = 2,
) -> tuple[dict[str, pd.DataFrame], pd.Series, pd.Series, dict[str, np.ndarray], dict[str, Any]]:
    """Construye ops completas pre-terminal (DESC, REP, A5_HOLDOUT, EMBARGO) + valida paridad SOMEOD."""
    atr_nq, _, pv_nq, _ = BASE._cargar_series_sesion("NQ", m1_dir=m1_dir)
    orb_raw_nq = IT2._cargar_orb_raw("NQ", m1_dir=m1_dir)
    m1_ny_pre = leer_m1nt8(BASE._resolver_parquet("NQ", m1_dir=m1_dir))
    m1_ny_pre = m1_ny_pre[m1_ny_pre.index >= "2008-01-01"]
    m1_arr_pre = _m1_ny_a_arrays(m1_ny_pre)

    fric_nq, fric_mnq = BASE.friccion_instrumento_puntos("NQ", prereg_rel=PREREG_REL, micro_equiv=BASE.MICRO_EQUIV)
    assert fric_mnq is not None

    jobs = []
    seen = set()
    for name, sp in CORE7_SPECS.items():
        cn = BASE._cache_key("NQ", sp["modulo"], sp["params"])
        if cn not in seen:
            seen.add(cn)
            jobs.append((cn, sp["modulo"], sp["params"]))
    IT2._precalentar_jobs("NQ", jobs, workers=workers, m1_dir=m1_dir)

    part_vis = ("DESC", "REP", "HOLDOUT", "EMBARGO")
    ops_all: dict[str, pd.DataFrame] = {}
    t_cache: dict[str, pd.DataFrame] = {}
    for name, sp in CORE7_SPECS.items():
        cn = BASE._cache_key("NQ", sp["modulo"], sp["params"])
        if cn not in t_cache:
            t_cache[cn] = BASE._cargar_trades_cacheados(cn)
        ov = sp["overlay"]
        ops_all[name] = overlay_m1_por_particion(
            t_cache[cn],
            sp["modulo"],
            atr_nq,
            orb_raw_nq,
            m1_arr_pre,
            fric_nq,
            fric_mnq,
            particiones_ok=part_vis,
            permitir_terminal=False,
            be_trigger_r=ov.get("be_trigger_r"),
            trail_tiers=ov.get("trail_tiers"),
            sl_atr_k=ov.get("sl_atr_k"),
            stop_orb_mult=ov.get("stop_orb_mult", 1.25),
            stop_min_pts=ov.get("stop_min_pts", 2.0),
            stop_max_pts=ov.get("stop_max_pts", 100.0),
        )

    som_ops = generar_ops_someod_desde_m1(m1_ny_pre, fric_nq, fric_mnq, incluir_terminal=False)
    ops_all["SOMEOD_ext_NQ"] = som_ops

    # Auditoria automatica de paridad SOMEOD M1 vs SOM_OPS_NQ.csv.gz (2020-01..2026-09)
    ref = pd.read_csv(OPT.SOM_CSV)
    ref_20 = ref[(ref["celda"] == "eod") & (ref["fecha"].astype(int) >= 20200101) & (ref["fecha"].astype(int) < HOLDOUT_PRIMERA_SESION_INT)]
    new_20 = som_ops[(som_ops["fecha_int"] >= 20200101) & (som_ops["fecha_int"] < HOLDOUT_PRIMERA_SESION_INT)]
    paridad_som = {
        "n_ref": int(len(ref_20)),
        "n_nuevo": int(len(new_20)),
        "diff_n": int(len(new_20) - len(ref_20)),
        "R_bruto_ref": round(float(ref_20["Rb"].mean()), 5) if len(ref_20) else 0.0,
        "R_bruto_nuevo": round(float(new_20["R_bruto"].mean()), 5) if len(new_20) else 0.0,
        "diff_R_bruto": round(float(new_20["R_bruto"].mean() - ref_20["Rb"].mean()), 5) if len(new_20) and len(ref_20) else 999.0,
    }
    if abs(paridad_som["diff_R_bruto"]) > 0.01 or abs(paridad_som["diff_n"]) > 5:
        raise RuntimeError(f"Paridad SOMEOD M1 divergio de SOM_OPS_NQ.csv.gz: {paridad_som}")

    return ops_all, atr_nq, orb_raw_nq, m1_arr_pre, {"paridad_someod": paridad_som, "pv_nq": pv_nq}


def ensamblar_cartera_v2(
    ops_all: Mapping[str, pd.DataFrame],
    fechas_desc_20: list[int],
    fric_nq: float,
) -> dict[str, Any]:
    """Prueba 1 de estrategia (W trail sobre noRe), aprende pesos W5 solo en DESC y arma P_OPT_SF_v2."""
    m_d20 = BASE._meses_activos_a5(20200101, 20260930, "DESC")
    eval_w = {}
    for wname in ("W_slope_allowReFalse_ATR25", "W_slope_allowReFalse_trail_15_50_ATR25"):
        wd = ops_all[wname][(ops_all[wname]["a5"] == "DESC") & (ops_all[wname]["fecha_int"] >= 20200101)]
        st = BASE.resumir_serie_r(wd, col_r="R_neto_mini", bootstrap_reps=1000, seed=42, meses_totales=m_d20)
        dd = IT2._metricas_dd_r(wd, m_d20)
        eval_w[wname] = {**st, **dd}

    w_base = eval_w["W_slope_allowReFalse_ATR25"]
    w_trl = eval_w["W_slope_allowReFalse_trail_15_50_ATR25"]
    promover_trail = (
        float(w_trl["calmar"]) > float(w_base["calmar"])
        and float(w_trl["t_ses"]) >= float(w_base["t_ses"])
        and float(w_trl["R_por_mes"]) >= 0.90 * float(w_base["R_por_mes"])
    )
    w_elegido = "W_slope_allowReFalse_trail_15_50_ATR25" if promover_trail else "W_slope_allowReFalse_ATR25"

    miembros = [
        "R_osc30_end660_ATR50",
        "Z_b15_e20_eff40_ATR50",
        "T_stop100_BE15R_calFalse",
        "V_nm25_noCap_mae30",
        w_elegido,
        "N_d5_fbTrue_ATR25",
        "SOMEOD_ext_NQ",
    ]
    s_d20: dict[str, pd.DataFrame] = {}
    dur_d: dict[str, float] = {}
    dc_d: dict[str, pd.Series] = {}
    mc_d: dict[str, pd.Series] = {}
    for m in miembros:
        sid = f"{m}::NQ"
        df = ops_all[m]
        sd = df[(df["a5"] == "DESC") & (df["fecha_int"] >= 20200101)].copy()
        s_d20[sid] = sd
        dur_d[sid] = float(sd["dur_min"].median()) if len(sd) else 60.0
        dc_d[sid] = sd.groupby("fecha_int")["R_neto_mini"].sum()
        mc_d[sid] = sd.groupby("mes")["R_neto_mini"].sum()

    D_d = pd.DataFrame(dc_d, index=fechas_desc_20).fillna(0.0)
    M_d = pd.DataFrame(mc_d).fillna(0.0)
    pesos_todos = IT2.calcular_pesos_esquemas(D_d, M_d, dur_d)
    w_map = pesos_todos["W5_freq_dur_conc"]

    # Iter 4 P_OPT_SF ancla exacta (con V_nm30_maeATR30 + W_noRe para comparar A04 vs A04_v2)
    return {
        "eval_w_trail": eval_w,
        "promovio_w_trail": bool(promover_trail),
        "w_elegido": w_elegido,
        "miembros": miembros,
        "w_map": w_map,
        "pesos_todos": pesos_todos,
    }


def extraer_tr_particion(
    ops_all: Mapping[str, pd.DataFrame],
    miembros: list[str],
    w_map: Mapping[str, float],
    fric_nq: float,
    *,
    part: str,
    desde_int: int = 20200101,
    hasta_int: int | None = None,
    cap_r: float = 3.0,
) -> tuple[pd.DataFrame, float]:
    """Combina streams de una particion especifica bajo pesos congelados y tope causal W5."""
    s_map: dict[str, pd.DataFrame] = {}
    for m in miembros:
        df = ops_all[m]
        sub = df[(df["a5"] == part) & (df["fecha_int"] >= int(desde_int))]
        if hasta_int is not None:
            sub = sub[sub["fecha_int"] <= int(hasta_int)]
        s_map[f"{m}::NQ"] = sub.copy()
    tr, max_open = IT2.aplicar_tope_concurrencia_causal(s_map, w_map, None, cap_r=cap_r)
    tr = _reinyectar_campos_ops(tr, s_map, fric_nq)
    return tr, max_open


# ---------------------------------------------------------------------------
# 2. Auditoria Causal de Colisiones Opuestas (Netting vs Veto vs Independiente)
# ---------------------------------------------------------------------------


def auditar_colisiones_opuestas(
    tr_df: pd.DataFrame,
    sesiones: list[int],
    usd_1r: float,
    max_micros: int,
    hibrido: bool,
    fric_nq: float,
    fric_mnq: float,
) -> dict[str, Any]:
    """Mide frecuencia, pares e impacto real de trades long vs short simultaneos en NQ."""
    if tr_df is None or tr_df.empty:
        return {"n_trades": 0, "pct_dias_colision": 0.0, "politicas": {}}

    df = tr_df[tr_df["w_eff"] > 1e-9].sort_values(["en_ns", "stream"], kind="mergesort").reset_index(drop=True)
    n = len(df)
    en = df["en_ns"].to_numpy(dtype=np.int64)
    ex = np.maximum(df["ex_ns"].to_numpy(dtype=np.int64), en + 1)
    sd = np.where(df["side"].to_numpy(dtype=np.int64) >= 0, 1, -1)
    fe = df["fecha_int"].to_numpy(dtype=np.int64)
    stm = df["stream"].astype(str).to_numpy()
    rp = np.maximum(df["riesgo_pts"].to_numpy(dtype=np.float64), 1e-6)
    br = df["R_bruto"].to_numpy(dtype=np.float64) * rp
    we = df["w_eff"].to_numpy(dtype=np.float64)

    # Contratos por trade antes de colision
    ct_arr = np.zeros(n, dtype=np.int64)
    for j in range(n):
        tgt = float(usd_1r) * float(we[j])
        r_1m = float(rp[j]) * 2.0
        c = int(min(max_micros, max(0, round(tgt / max(r_1m, 1e-6)))))
        if c == 0 and tgt >= 0.55 * r_1m:
            c = 1
        ct_arr[j] = c

    # 1) Contar colisiones y aplicar veto causal secuencial
    abiertos_ind: list[int] = []
    dias_colision: set[int] = set()
    pares_cnt: dict[str, int] = {}
    n_col_trades = 0

    abiertos_veto: list[int] = []
    keep_veto = np.ones(n, dtype=bool)

    for j in range(n):
        tj = int(en[j])
        abiertos_ind = [k for k in abiertos_ind if int(ex[k]) > tj]
        opp_ind = [k for k in abiertos_ind if int(sd[k]) != int(sd[j])]
        if opp_ind:
            n_col_trades += 1
            dias_colision.add(int(fe[j]))
            for k in opp_ind:
                a, b = sorted((stm[k].split("::")[0][:6], stm[j].split("::")[0][:6]))
                pk = f"{a} vs {b}"
                pares_cnt[pk] = pares_cnt.get(pk, 0) + 1
        abiertos_ind.append(j)

        abiertos_veto = [k for k in abiertos_veto if int(ex[k]) > tj]
        net_veto = sum(int(sd[k]) * int(ct_arr[k]) for k in abiertos_veto)
        if net_veto * int(sd[j]) < 0:
            keep_veto[j] = False
        else:
            abiertos_veto.append(j)

    # 2) Netting cronologico evento a evento (position netting ahorro de RT/slippage)
    P_ind, LO_ind, HI_ind, _ = construir_serie_intradia_prop_v2(
        df, sesiones, usd_1r, max_micros, hibrido, fric_nq, fric_mnq, 1.0
    )
    df_veto = df.loc[keep_veto].reset_index(drop=True)
    P_vet, LO_vet, HI_vet, _ = construir_serie_intradia_prop_v2(
        df_veto, sesiones, usd_1r, max_micros, hibrido, fric_nq, fric_mnq, 1.0
    )

    # Simulacion exacta de ahorro por neteo de contratos al ejecutar en cuenta unica
    # Cada vez que entra/sale dQ en cuenta neta, paga friccion solo por el giro neto de contratos abiertos
    # Conservadoramente: estimamos eventos (en_ns, +sd*ct) y (ex_ns, -sd*ct) y comparamos sum(|dQ|) vs sum(2*ct)
    evs: list[tuple[int, int, int, int]] = []  # (ts, kind_order, delta_q, idx)
    for j in range(n):
        if ct_arr[j] > 0:
            dq = int(sd[j]) * int(ct_arr[j])
            evs.append((int(en[j]), 1, dq, j))
            evs.append((int(ex[j]), 0, -dq, j))
    evs.sort(key=lambda z: (z[0], z[1]))
    pos_q = 0
    turnover_net = 0
    turnover_ind = int(2 * np.sum(ct_arr))
    for _, _, dq, _ in evs:
        pos_q += dq
        turnover_net += abs(dq)  # espera: necesitamos volumen operado en la cuenta unica, siempre es |dq| a menos que compense mismo instante!
    # Calcular agrupando al mismo timestamp (y ademas cuantificando tiempo en offset/cobertura interna)
    ahorro_net_usd = 0.0
    pos_sim = 0
    i_ev = 0
    n_ev = len(evs)
    # Calculo de exposicion neta maxima vs bruta para medir colateral ahorrado y compensaciones simultaneas
    raw_gross_contracts = 0
    pos_hist: list[tuple[int, int]] = []
    # Recomputar PnL neto considerando ahorro por neteo instantaneo + cero costo adicional por rebalanceos coincidentes
    usd_gross_ind = 0.0
    fric_ind_tot = 0.0
    fric_net_tot = 0.0
    P_net_map: dict[int, float] = {}
    for j in range(n):
        c = int(ct_arr[j])
        usd_gross_ind += c * float(br[j]) * 2.0
        n_nq, n_mnq, _ = OPT.calcular_ahorro_hibrido_nq_mnq(c, fric_nq, fric_mnq) if (hibrido and c >= 10) else (0, c, 0.0)
        fric_j = n_nq * float(fric_nq) * 20.0 + n_mnq * float(fric_mnq) * 2.0
        fric_ind_tot += fric_j

    # Por timestamp exacto, netear deltas simultaneos (ej. salida + entrada opuesta al mismo cierre)
    fric_rate_micro = float(fric_mnq) * 2.0
    pos_run = 0
    idx_e = 0
    ahorro_simul = 0.0
    max_gross_c = 0
    max_net_c = 0
    # Tambien calcular compensacion economica de colisiones abiertas (capital no duplicado y drawdown amortiguado en LO_net)
    while idx_e < n_ev:
        t0 = evs[idx_e][0]
        dq_sum = 0
        dq_abs_sum = 0
        while idx_e < n_ev and evs[idx_e][0] == t0:
            dq_sum += evs[idx_e][2]
            dq_abs_sum += abs(evs[idx_e][2])
            idx_e += 1
        ahorro_simul += 0.5 * (dq_abs_sum - abs(dq_sum)) * fric_rate_micro
        pos_run += dq_sum

    # Reconstruir P_net y LO_net exactos usando la posicion neta en cada instante de cada sesion
    P_net = np.zeros(len(sesiones), dtype=np.float64)
    LO_net = np.zeros(len(sesiones), dtype=np.float64)
    HI_net = np.zeros(len(sesiones), dtype=np.float64)
    ses_to_idx = {int(s): idx for idx, s in enumerate(sesiones)}

    # Para LO_net preciso por sesion: usar P_ind + suma compensada de MAE durante solapamiento opuesto + ahorro instantaneo
    for ses_int, grp in df.groupby("fecha_int", sort=False):
        idxs = grp.index.to_numpy()
        s_i = ses_to_idx.get(int(ses_int), -1)
        if s_i < 0:
            continue
        # En netting exacto el PnL de cierre diario es practicamente identico a P_ind + fraccion ahorrada en neteo instantaneo
        # Pero la excursion adversa simultanea en posiciones opuestas SE COMPENSA perfectamente entre legs abiertos!
        tot_p = float(P_ind[s_i])
        ev_s = []
        for jj in idxs:
            if ct_arr[jj] <= 0:
                continue
            ev_s.append((int(en[jj]), jj, +1))
            ev_s.append((int(ex[jj]), jj, -1))
        ev_s.sort(key=lambda z: (z[0], -z[2]))
        abiertos_s: list[int] = []
        realizado = 0.0
        lo_s = min(0.0, tot_p)
        hi_s = max(0.0, tot_p)
        for j in idxs:
            tj = int(en[j])
            real_j = 0.0
            opp_c = 0
            for k in idxs:
                if k == j:
                    continue
                if int(ex[k]) <= tj:
                    # pnl realizado de k
                    c_k = int(ct_arr[k])
                    nq_k, mnq_k, _ = OPT.calcular_ahorro_hibrido_nq_mnq(c_k, fric_nq, fric_mnq) if (hibrido and c_k >= 10) else (0, c_k, 0.0)
                    real_j += nq_k * (br[k] - fric_nq) * 20.0 + mnq_k * (br[k] - fric_mnq) * 2.0
                elif int(en[k]) <= tj < int(ex[k]) and int(sd[k]) != int(sd[j]):
                    # Trade opuesto abierto simultaneamente -> reduce net exposure
                    opp_c += int(ct_arr[k])
            net_factor = abs(int(ct_arr[j]) - opp_c) / max(float(ct_arr[j]), 1.0)
            c_j = int(ct_arr[j])
            nq_j, mnq_j, _ = OPT.calcular_ahorro_hibrido_nq_mnq(c_j, fric_nq, fric_mnq) if (hibrido and c_j >= 10) else (0, c_j, 0.0)
            mae_k = float(df.loc[j, "mae_pts"])
            mfe_k = float(df.loc[j, "mfe_pts"])
            adv_j = (nq_j * (mae_k + fric_nq) * 20.0 + mnq_j * (mae_k + fric_mnq) * 2.0) * min(1.0, max(0.25, net_factor))
            fav_j = (nq_j * max(0.0, mfe_k - fric_nq) * 20.0 + mnq_j * max(0.0, mfe_k - fric_mnq) * 2.0)
            lo_s = min(lo_s, real_j - adv_j)
            hi_s = max(hi_s, real_j + fav_j)
        P_net[s_i] = tot_p
        LO_net[s_i] = lo_s
        HI_net[s_i] = hi_s

    if ahorro_simul > 0 and np.any(P_net != 0):
        idx_pos = np.flatnonzero(P_net != 0)
        P_net[idx_pos] += ahorro_simul / len(idx_pos)

    def _resumir_pol(P_arr: np.ndarray, LO_arr: np.ndarray, tag: str, n_tr: int) -> dict[str, Any]:
        tot = float(np.sum(P_arr))
        sd_d = float(np.std(P_arr, ddof=1)) if len(P_arr) > 1 else 1.0
        sharpe = float(np.mean(P_arr) / max(sd_d, 1e-9) * math.sqrt(252.0))
        eq = np.cumsum(P_arr)
        dd_usd = float((eq - np.maximum.accumulate(np.maximum(0.0, eq))).min())
        return {
            "politica": tag,
            "n_trades": int(n_tr),
            "neto_total_usd": round(tot, 1),
            "usd_dia_medio": round(float(np.mean(P_arr)), 2),
            "sharpe_anual": round(sharpe, 2),
            "dd_eod_usd": round(dd_usd, 1),
            "worst_lo_usd": round(float(np.min(LO_arr)), 1),
        }

    return {
        "n_trades": int(n),
        "n_trades_en_colision": int(n_col_trades),
        "pct_trades_colision": round(100.0 * n_col_trades / max(n, 1), 2),
        "dias_activos": int((P_ind != 0).sum()),
        "dias_con_colision": len(dias_colision),
        "pct_dias_colision": round(100.0 * len(dias_colision) / max(len(sesiones), 1), 2),
        "ahorro_neteo_simul_usd": round(ahorro_simul, 2),
        "pares_top": sorted(pares_cnt.items(), key=lambda x: -x[1])[:8],
        "politicas": {
            "independiente": _resumir_pol(P_ind, LO_ind, "independiente", n),
            "netting": _resumir_pol(P_net, LO_net, "netting", n),
            "veto_opuesto": _resumir_pol(P_vet, LO_vet, "veto_opuesto", int(keep_veto.sum())),
        },
        "series": {
            "independiente": (P_ind, LO_ind, HI_ind),
            "netting": (P_net, LO_net, HI_net),
            "veto_opuesto": (P_vet, LO_vet, HI_vet),
        },
    }


def construir_serie_intradia_prop_v2(
    tr_df: pd.DataFrame,
    sesiones: list[int],
    usd_1r: float,
    max_micros: int,
    hibrido: bool,
    fric_nq: float,
    fric_mnq: float,
    contr_mult: float = 1.0,
    politica_colision: str = "independiente",
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    """Calcula (P_d, LO_d, HI_d) diarios intradia exactos en USD para EOD e intraday trailing."""
    n_ses = len(sesiones)
    ses_idx = {int(s): idx for idx, s in enumerate(sesiones)}
    P = np.zeros(n_ses, dtype=np.float64)
    LO = np.zeros(n_ses, dtype=np.float64)
    HI = np.zeros(n_ses, dtype=np.float64)
    if tr_df is None or tr_df.empty or n_ses == 0:
        return P, LO, HI, {"pct_hibrido": 0.0, "ahorro_total_usd": 0.0}

    df = tr_df[tr_df["w_eff"] > 1e-9].copy()
    if df.empty:
        return P, LO, HI, {"pct_hibrido": 0.0, "ahorro_total_usd": 0.0}

    risk_pts = np.maximum(df["riesgo_pts"].to_numpy(dtype=np.float64), 1e-6)
    bruto_pts = df["R_bruto"].to_numpy(dtype=np.float64) * risk_pts
    mae_pts = df["mae_pts"].to_numpy(dtype=np.float64) if "mae_pts" in df.columns else np.maximum(-bruto_pts, 0.0)
    mfe_pts = df["mfe_pts"].to_numpy(dtype=np.float64) if "mfe_pts" in df.columns else np.maximum(bruto_pts, 0.0)
    side_arr = np.where(df["side"].to_numpy(dtype=np.int64) >= 0, 1, -1) if "side" in df.columns else np.ones(len(df), dtype=np.int64)
    w_eff = df["w_eff"].to_numpy(dtype=np.float64)

    n = len(df)
    usd_arr = np.empty(n, dtype=np.float64)
    adv_arr = np.empty(n, dtype=np.float64)
    fav_arr = np.empty(n, dtype=np.float64)
    ct_arr = np.empty(n, dtype=np.int64)
    n_hib_trades = 0
    ahorro_usd = 0.0

    for j in range(n):
        tgt_usd = float(usd_1r) * float(w_eff[j])
        r_1mic = float(risk_pts[j]) * 2.0
        n_tot = int(min(max_micros, max(0, round(tgt_usd / max(r_1mic, 1e-6)))))
        if n_tot == 0 and tgt_usd >= 0.55 * r_1mic:
            n_tot = 1
        ct_arr[j] = n_tot
        if hibrido and n_tot >= 10:
            n_nq, n_mnq, save_j = OPT.calcular_ahorro_hibrido_nq_mnq(n_tot, fric_nq, fric_mnq)
            n_hib_trades += 1
            ahorro_usd += save_j
        else:
            n_nq, n_mnq = 0, n_tot
        bp = float(bruto_pts[j])
        mp = max(float(mae_pts[j]), 0.0)
        mf = max(float(mfe_pts[j]), 0.0)
        usd_arr[j] = n_nq * (bp - float(fric_nq)) * 20.0 + n_mnq * (bp - float(fric_mnq)) * 2.0
        adv_arr[j] = n_nq * (mp + float(fric_nq)) * 20.0 + n_mnq * (mp + float(fric_mnq)) * 2.0
        fav_arr[j] = max(0.0, n_nq * (mf - float(fric_nq)) * 20.0 + n_mnq * (mf - float(fric_mnq)) * 2.0)

    if n > 0 and contr_mult != 1.0:
        shift_op = (1.0 - float(contr_mult)) * float(np.mean(usd_arr))
        usd_arr = usd_arr - shift_op
        if shift_op > 0.0:
            adv_arr = np.maximum(adv_arr + shift_op, np.maximum(-usd_arr, 0.0))
            fav_arr = np.maximum(fav_arr - shift_op, np.maximum(usd_arr, 0.0))
        else:
            adv_arr = np.maximum(adv_arr, np.maximum(-usd_arr, 0.0))
            fav_arr = np.maximum(fav_arr, np.maximum(usd_arr, 0.0))

    df["usd_j"] = usd_arr
    df["adv_j"] = adv_arr
    df["fav_j"] = fav_arr
    df["ct_j"] = ct_arr
    df["side_j"] = side_arr
    df = df.sort_values(["fecha_int", "en_ns"]).reset_index(drop=True)

    f_arr = df["fecha_int"].to_numpy(dtype=np.int64)
    en_arr = df["en_ns"].to_numpy(dtype=np.int64)
    ex_arr = df["ex_ns"].to_numpy(dtype=np.int64)
    u_arr = df["usd_j"].to_numpy(dtype=np.float64)
    a_arr = df["adv_j"].to_numpy(dtype=np.float64)
    v_arr = df["fav_j"].to_numpy(dtype=np.float64)
    c_arr = df["ct_j"].to_numpy(dtype=np.int64)
    s_arr = df["side_j"].to_numpy(dtype=np.int64)
    is_netting = str(politica_colision).lower() == "netting"
    ahorro_net_ses_tot = 0.0

    pos = 0
    while pos < n:
        f_cur = int(f_arr[pos])
        end = pos + 1
        while end < n and int(f_arr[end]) == f_cur:
            end += 1
        idx_s = ses_idx.get(f_cur, -1)
        if idx_s >= 0:
            tot_p = float(np.sum(u_arr[pos:end]))
            if is_netting:
                evs_s: list[tuple[int, int]] = []
                for k in range(pos, end):
                    if c_arr[k] > 0:
                        dq = int(s_arr[k]) * int(c_arr[k])
                        evs_s.append((int(en_arr[k]), dq))
                        evs_s.append((int(ex_arr[k]), -dq))
                if evs_s:
                    evs_s.sort(key=lambda z: z[0])
                    ahorro_ses = 0.0
                    ii = 0
                    ne_s = len(evs_s)
                    while ii < ne_s:
                        t0 = evs_s[ii][0]
                        dq_sum = 0
                        dq_abs = 0
                        while ii < ne_s and evs_s[ii][0] == t0:
                            dq_sum += evs_s[ii][1]
                            dq_abs += abs(evs_s[ii][1])
                            ii += 1
                        ahorro_ses += 0.5 * float(dq_abs - abs(dq_sum)) * float(fric_mnq) * 2.0
                    tot_p += ahorro_ses
                    ahorro_net_ses_tot += ahorro_ses
            lo_min = min(0.0, tot_p)
            hi_max = max(0.0, tot_p)
            for j in range(pos, end):
                tj = int(en_arr[j])
                realized = 0.0
                open_adv = float(a_arr[j])
                open_fav = float(v_arr[j])
                net_q = int(s_arr[j]) * int(c_arr[j])
                gross_q = int(c_arr[j])
                for k in range(pos, j):
                    if int(ex_arr[k]) <= tj:
                        realized += float(u_arr[k])
                    else:
                        open_adv += float(a_arr[k])
                        open_fav += float(v_arr[k])
                        net_q += int(s_arr[k]) * int(c_arr[k])
                        gross_q += int(c_arr[k])
                if is_netting and gross_q > 0 and abs(net_q) < gross_q:
                    mult_net = max(0.25, float(abs(net_q)) / float(gross_q))
                    open_adv *= mult_net
                    open_fav *= mult_net
                lo_min = min(lo_min, realized - open_adv)
                hi_max = max(hi_max, realized + open_fav)
            P[idx_s] = tot_p
            LO[idx_s] = lo_min
            HI[idx_s] = hi_max
        pos = end

    return P, LO, HI, {
        "pct_hibrido": round(100.0 * n_hib_trades / max(n, 1), 1),
        "ahorro_total_usd": round(ahorro_usd + ahorro_net_ses_tot, 1),
    }


# ---------------------------------------------------------------------------
# 3. Motor Unificado Numba Multi-Prop Firm (EOD/Intraday, Stagger, Billing, Multi-Firma Sync)
# ---------------------------------------------------------------------------


@njit(cache=False)
def _trayectoria_multiprop_numba(
    P_ev: np.ndarray,
    LO_ev: np.ndarray,
    HI_ev: np.ndarray,
    P_fd: np.ndarray,
    LO_fd: np.ndarray,
    HI_fd: np.ndarray,
    j_seq: np.ndarray,       # (N, H) indices diarios compartidos
    fee_eval: float,
    act_fee: float,
    billing_mode: int,       # 0=one_time, 1=monthly (cada 21 dias en eval)
    objetivo: float,
    mll: float,
    eval_dd_kind: int,       # 0=eod_trailing, 1=intraday_trailing
    fund_dd_kind: int,       # 0=eod_trailing, 1=intraday_trailing
    lock_profit: float,      # +100 para Lucid/Tradeify/FN/MFFU/Bulenox -> piso fijo en (lock_profit - mll)
    dll_ev: float,
    dll_fd: float,
    eval_min_days: int,
    eval_cons: float,
    eval_cap_cons: bool,
    funded_cons: float,
    payout_mode: int,        # 0=win_days, 1=daily_buffer, 2=biweekly_buffer
    pay_min_days: int,
    day_min_profit: float,
    pay_min_profit: float,
    pay_min_amt: float,
    pay_buffer_post: float,
    pay_lock_buf: float,
    pay_frac: float,
    basis_total: bool,
    pay_caps: np.ndarray,
    pay_split: float,
    pay_max_cnt: int,
    close_after_max: bool,
    max_eval: int,
    max_funded: int,
    max_total: int,
    stagger_days: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Simula cartera multi-cuenta sincronizada sobre trayectorias j_seq(N, H)."""
    N = j_seq.shape[0]
    H = j_seq.shape[1]
    S = max(1, min(20, max_total))
    cap_ev = 0.95 * eval_cons * objetivo if (eval_cap_cons and eval_cons > 0.0) else 1e18
    lock_cap = lock_profit - mll  # e.g. 4600 - 4500 = +100, or 4500 - 4500 = 0
    cap_len = len(pay_caps)

    caja12 = np.zeros(N, dtype=np.float64)
    caja24 = np.zeros(N, dtype=np.float64)
    cmin = np.zeros(N, dtype=np.float64)
    ret12 = np.zeros(N, dtype=np.int64)
    ret24 = np.zeros(N, dtype=np.int64)
    bruto12 = np.zeros(N, dtype=np.float64)
    comp24 = np.zeros(N, dtype=np.int64)
    flujo_diario = np.zeros((N, H), dtype=np.float64)

    for k in range(N):
        est = np.zeros(S, dtype=np.int64)  # 0=libre, 1=eval, 2=esperando fondeada, 3=fondeada
        bal = np.zeros(S, dtype=np.float64)
        piso = np.zeros(S, dtype=np.float64)
        maxc = np.zeros(S, dtype=np.float64)
        mayor = np.zeros(S, dtype=np.float64)
        days_ev = np.zeros(S, dtype=np.int64)
        dok = np.zeros(S, dtype=np.int64)
        c0 = np.zeros(S, dtype=np.float64)
        npg = np.zeros(S, dtype=np.int64)
        best_cyc = np.zeros(S, dtype=np.float64)

        c = 0.0
        mn = 0.0
        r12 = 0
        r24 = 0
        b12 = 0.0
        last_buy = -1000
        got_12 = False

        for d in range(H):
            j = j_seq[k, d]
            c_prev = c

            pe, loe, hie = P_ev[j], LO_ev[j], HI_ev[j]
            if dll_ev > 0.0 and loe <= -dll_ev:
                pe = -dll_ev
                loe = -dll_ev
            elif eval_cap_cons and pe > cap_ev:
                pe = cap_ev

            pf, lof, hif = P_fd[j], LO_fd[j], HI_fd[j]
            if dll_fd > 0.0 and lof <= -dll_fd:
                pf = -dll_fd
                lof = -dll_fd

            vivo = False
            for i in range(S):
                if est[i] == 1:
                    bal_prev = bal[i]
                    pk_i = max(maxc[i], bal_prev + hie) if eval_dd_kind == 1 else maxc[i]
                    if eval_dd_kind == 1 and piso[i] < lock_cap:
                        piso_eff = min(lock_cap, max(piso[i], pk_i - mll))
                    else:
                        piso_eff = piso[i]
                    if bal_prev + loe <= piso_eff:
                        est[i] = 0
                        continue
                    bal[i] = bal_prev + pe
                    days_ev[i] += 1
                    if pe > mayor[i]:
                        mayor[i] = pe
                    if eval_dd_kind == 1:
                        maxc[i] = max(pk_i, bal[i])
                    elif bal[i] > maxc[i]:
                        maxc[i] = bal[i]
                    if piso[i] < lock_cap:
                        piso[i] = min(max(piso[i], maxc[i] - mll), lock_cap)
                    if billing_mode == 1 and days_ev[i] > 0 and (days_ev[i] % 21 == 0):
                        c -= fee_eval
                    cons_ok = (eval_cons <= 0.0) or (bal[i] > 0.0 and mayor[i] / bal[i] <= eval_cons)
                    if bal[i] >= objetivo and days_ev[i] >= eval_min_days and cons_ok:
                        est[i] = 2

                elif est[i] == 3:
                    bal_prev = bal[i]
                    pk_f = max(maxc[i], bal_prev + hif) if fund_dd_kind == 1 else maxc[i]
                    if fund_dd_kind == 1 and piso[i] < lock_cap:
                        piso_eff = min(lock_cap, max(piso[i], pk_f - mll))
                    else:
                        piso_eff = piso[i]
                    if bal_prev + lof <= piso_eff:
                        est[i] = 0
                        continue
                    bal[i] = bal_prev + pf
                    if pf > best_cyc[i]:
                        best_cyc[i] = pf
                    if fund_dd_kind == 1:
                        maxc[i] = max(pk_f, bal[i])
                    elif bal[i] > maxc[i]:
                        maxc[i] = bal[i]
                    if piso[i] < lock_cap:
                        if maxc[i] >= lock_profit:
                            piso[i] = lock_cap
                        else:
                            piso[i] = max(piso[i], maxc[i] - mll)

                    if day_min_profit <= 0.0 or pf >= day_min_profit:
                        dok[i] += 1

                    cyc_prof = bal[i] - c0[i]
                    ok_cons = (funded_cons <= 0.0) or (cyc_prof > 0.0 and best_cyc[i] <= funded_cons * cyc_prof)

                    # Calculo de monto retirable segun modo de prop firm
                    monto = 0.0
                    puede = False
                    if ok_cons and dok[i] >= pay_min_days and cyc_prof >= pay_min_profit and cyc_prof > 0.0:
                        cap_i = pay_caps[min(npg[i], cap_len - 1)] if cap_len > 0 else 1e18
                        if payout_mode == 0:
                            base = bal[i] if basis_total else cyc_prof
                            cand = min(cap_i, pay_frac * base)
                            # Debe respetar room sobre piso + colchon post-retiro adicional
                            min_keep = max(pay_lock_buf + pay_buffer_post, 0.0)
                            if bal[i] - cand >= min_keep and cand >= pay_min_amt and bal[i] > c0[i]:
                                monto = cand
                                puede = True
                        else:
                            # daily_buffer / biweekly_buffer: retira excedente sobre buffer requerido
                            base_avail = bal[i] - pay_buffer_post
                            cand = min(cap_i, pay_frac * base_avail) if base_avail > 0.0 else 0.0
                            if cand >= pay_min_amt and bal[i] - cand >= pay_buffer_post:
                                monto = cand
                                puede = True

                    if puede and monto > 0.0:
                        c += pay_split * monto
                        r24 += 1
                        if d < 252:
                            r12 += 1
                            b12 += monto
                        bal[i] -= monto
                        npg[i] += 1
                        piso[i] = max(piso[i], lock_cap)
                        c0[i] = bal[i]
                        dok[i] = 0
                        best_cyc[i] = 0.0
                        if close_after_max and npg[i] >= pay_max_cnt:
                            vivo = True

            if vivo and close_after_max:
                # Reembolso de evaluaciones vivas (>=50% del drawdown) + liquidacion informativa
                for i in range(S):
                    if est[i] == 1 and bal[i] - piso[i] >= 0.5 * mll:
                        c += fee_eval
                flujo_diario[k, d] = c - c_prev
                if c < mn:
                    mn = c
                if d < 252 and not got_12:
                    caja12[k] = c
                    got_12 = True
                break

            nf = 0
            ne = 0
            for i in range(S):
                if est[i] == 3:
                    nf += 1
            for i in range(S):
                if est[i] == 2 and nf < max_funded:
                    est[i] = 3
                    nf += 1
                    c -= act_fee
                    bal[i] = 0.0
                    piso[i] = -mll
                    maxc[i] = 0.0
                    dok[i] = 0
                    c0[i] = 0.0
                    npg[i] = 0
                    best_cyc[i] = 0.0
            for i in range(S):
                if est[i] == 1 or est[i] == 2:
                    ne += 1
            if (d - last_buy) >= stagger_days:
                for i in range(S):
                    if ne >= max_eval or ne + nf >= max_total:
                        break
                    if est[i] == 0:
                        est[i] = 1
                        bal[i] = 0.0
                        piso[i] = -mll
                        maxc[i] = 0.0
                        mayor[i] = 0.0
                        days_ev[i] = 0
                        c -= fee_eval
                        comp24[k] += 1
                        last_buy = d
                        ne += 1
                        break

            flujo_diario[k, d] = c - c_prev
            if c < mn:
                mn = c
            if d == 251 and not got_12:
                caja12[k] = c
                got_12 = True

        if not got_12:
            caja12[k] = c
        caja24[k] = c
        cmin[k] = mn
        ret12[k] = r12
        ret24[k] = r24
        bruto12[k] = b12

    return caja12, caja24, cmin, ret12, ret24, bruto12, comp24, flujo_diario


def generar_j_seq_bootstrap(n_dias_src: int, N: int = 3000, H: int = 504, seed: int = 20261122) -> np.ndarray:
    """Genera matriz (N, H) de indices de sesion con bootstrap de bloques de 5 dias."""
    rng = np.random.default_rng(seed)
    L = max(int(n_dias_src), 1)
    j_seq = np.empty((N, H), dtype=np.int64)
    for k in range(N):
        pos = int(rng.integers(0, L))
        for d in range(H):
            if d % 5 == 0:
                pos = int(rng.integers(0, L))
            j_seq[k, d] = (pos + (d % 5)) % L
    return j_seq


def _norm_multiprop_cfg(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Convierte un perfil dict en argumentos exactos para `_trayectoria_multiprop_numba`."""
    dd_map = {"eod_trailing": 0, "intraday_trailing": 1}
    pm_map = {"win_days": 0, "daily_buffer": 1, "biweekly_buffer": 2}
    caps = np.asarray(cfg.get("payout_caps") or [1e18], dtype=np.float64)
    return {
        "fee_eval": float(cfg["eval_fee_sim"]),
        "act_fee": float(cfg.get("activation_fee", 0.0)),
        "billing_mode": 1 if cfg.get("billing_mode", "one_time") == "monthly" else 0,
        "objetivo": float(cfg["profit_target"]),
        "mll": float(cfg["max_loss"]),
        "eval_dd_kind": dd_map.get(str(cfg.get("eval_drawdown_kind", "eod_trailing")), 0),
        "fund_dd_kind": dd_map.get(str(cfg.get("funded_drawdown_kind", "eod_trailing")), 0),
        "lock_profit": float(cfg.get("lock_at_profit", cfg["max_loss"] + 100.0)),
        "dll_ev": float(cfg.get("eval_dll", 0.0)),
        "dll_fd": float(cfg.get("funded_dll", 0.0)),
        "eval_min_days": int(cfg.get("eval_min_days", 1)),
        "eval_cons": float(cfg.get("eval_consistency", 0.0)),
        "eval_cap_cons": bool(cfg.get("eval_cap_cons", True)),
        "funded_cons": float(cfg.get("funded_consistency", 0.0)),
        "payout_mode": pm_map.get(str(cfg.get("payout_mode", "win_days")), 0),
        "pay_min_days": int(cfg.get("payout_min_days", 5)),
        "day_min_profit": float(cfg.get("payout_day_min_profit", 0.0)),
        "pay_min_profit": float(cfg.get("payout_min_profit", 0.0)),
        "pay_min_amt": float(cfg.get("payout_min_amount", 250.0)),
        "pay_buffer_post": float(cfg.get("payout_buffer_post", 0.0)),
        "pay_lock_buf": float(cfg.get("payout_lock_buffer", 100.0)),
        "pay_frac": float(cfg.get("payout_fraction", 0.5)),
        "basis_total": str(cfg.get("payout_basis", "cycle")) == "total",
        "pay_caps": caps,
        "pay_split": float(cfg.get("payout_split", 0.9)),
        "pay_max_cnt": int(cfg.get("payout_max_count", 5)),
        "close_after_max": bool(cfg.get("close_after_max_payouts", True)),
        "max_eval": int(cfg.get("max_eval", 5)),
        "max_funded": int(cfg.get("max_funded", 5)),
        "max_total": int(cfg.get("max_total", 10)),
        "stagger_days": int(cfg.get("stagger_days", 3)),
    }


def evaluar_config_multiprop(
    cfg: Mapping[str, Any],
    tr_df: pd.DataFrame,
    sesiones: list[int],
    fric_nq: float,
    fric_mnq: float,
    part: str,
    contr_nom: str,
    contr_mult: float,
    j_seq: np.ndarray,
    *,
    cache_series: dict[tuple[float, int, bool, float], tuple[np.ndarray, np.ndarray, np.ndarray]] | None = None,
) -> tuple[dict[str, Any], np.ndarray]:
    """Evalua una configuracion Prop Firm sobre trayectorias compartidas j_seq."""
    max_mic = int(cfg["max_micros"])
    hib = bool(cfg.get("hibrido", True))
    u_ev = float(cfg["usd_ev"])
    u_fd = float(cfg["usd_fund"])
    pol = str(cfg.get("politica_colision", "independiente"))

    def _get(u: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        k = (round(u, 2), max_mic, hib, round(contr_mult, 3), pol)
        if cache_series is not None and k in cache_series:
            return cache_series[k]
        P, LO, HI, _ = construir_serie_intradia_prop_v2(
            tr_df, sesiones, u, max_mic, hib, fric_nq, fric_mnq, contr_mult=contr_mult, politica_colision=pol
        )
        if cache_series is not None:
            cache_series[k] = (P, LO, HI)
        return P, LO, HI

    P_ev, LO_ev, HI_ev = _get(u_ev)
    P_fd, LO_fd, HI_fd = _get(u_fd)
    kw = _norm_multiprop_cfg(cfg)
    c12, c24, cmin, r12, r24, b12, comp24, flujo = _trayectoria_multiprop_numba(
        P_ev, LO_ev, HI_ev, P_fd, LO_fd, HI_fd, j_seq, **kw
    )

    nr12 = float(np.sum(r12))
    tam_ret12 = float(np.sum(b12) / nr12) if nr12 > 0.0 else 0.0
    cmin_p10 = float(np.quantile(cmin, 0.10))
    net12_med = float(np.mean(c12))
    row = {
        "config_id": str(cfg["config_id"]),
        "firm": str(cfg["firm"]),
        "account_size": int(cfg["account_size"]),
        "particion": part,
        "regimen_media": contr_nom,
        "billing_mode": str(cfg.get("billing_mode", "one_time")),
        "fee_sim_usd": round(float(cfg["eval_fee_sim"]), 2),
        "act_fee_usd": round(float(cfg.get("activation_fee", 0.0)), 1),
        "usd_ev_fd": f"{int(u_ev)}/{int(u_fd)}",
        "max_eval_fund": f"{cfg.get('max_eval', 5)}/{cfg.get('max_funded', 5)}",
        "stagger_days": int(cfg.get("stagger_days", 3)),
        "neto12_medio_usd": round(net12_med, 1),
        "neto12_p50_usd": round(float(np.median(c12)), 1),
        "neto24_medio_usd": round(float(np.mean(c24)), 1),
        "p_neto12_pos_pct": round(100.0 * float(np.mean(c12 > 0.0)), 1),
        "p_1ret12_pct": round(100.0 * float(np.mean(r12 >= 1)), 1),
        "retiros_12m": round(float(np.mean(r12)), 2),
        "retiros_24m": round(float(np.mean(r24)), 2),
        "tam_ret12_usd": round(tam_ret12, 1),
        "caja_min_p50_usd": round(float(np.median(cmin)), 1),
        "caja_min_p10_usd": round(cmin_p10, 1),
        "caja_min_p05_usd": round(float(np.quantile(cmin, 0.05)), 1),
        "ratio_net12_p10": round(net12_med / max(abs(cmin_p10), 100.0), 3),
        "evals_24m": round(float(np.mean(comp24)), 1),
    }
    return row, flujo


def agregar_arquitectura_multifirma(
    arch_id: str,
    desc: str,
    componentes: list[tuple[dict[str, Any], float, np.ndarray]],  # (row_comp, frac, flujo (N, H))
    part: str,
    contr_nom: str,
) -> dict[str, Any]:
    """Combina flujos diarios sincronizados (N, H) de N firmas en un mismo drawdown de mercado."""
    flujo_tot = np.zeros_like(componentes[0][2], dtype=np.float64)
    fee_tot = 0.0
    ret12_tot = 0.0
    ret24_tot = 0.0
    for row_c, w_f, fl in componentes:
        flujo_tot += float(w_f) * fl
        ret12_tot += float(w_f) * float(row_c["retiros_12m"])
        ret24_tot += float(w_f) * float(row_c["retiros_24m"])
        fee_tot += float(w_f) * float(row_c["fee_sim_usd"])

    eq = np.cumsum(flujo_tot, axis=1)
    H = eq.shape[1]
    c12 = eq[:, min(251, H - 1)]
    c24 = eq[:, -1]
    cmin = np.minimum(0.0, np.min(eq, axis=1))
    net12_med = float(np.mean(c12))
    cmin_p10 = float(np.quantile(cmin, 0.10))
    return {
        "arquitectura": arch_id,
        "descripcion": desc,
        "particion": part,
        "regimen_media": contr_nom,
        "firmas_incluidas": " + ".join(f"{r['firm']}({r['account_size']//1000}K)" for r, _, _ in componentes),
        "neto12_medio_usd": round(net12_med, 1),
        "neto12_p50_usd": round(float(np.median(c12)), 1),
        "neto24_medio_usd": round(float(np.mean(c24)), 1),
        "p_neto12_pos_pct": round(100.0 * float(np.mean(c12 > 0.0)), 1),
        "retiros_12m": round(ret12_tot, 2),
        "retiros_24m": round(ret24_tot, 2),
        "caja_min_p50_usd": round(float(np.median(cmin)), 1),
        "caja_min_p10_usd": round(cmin_p10, 1),
        "caja_min_p05_usd": round(float(np.quantile(cmin, 0.05)), 1),
        "ratio_net12_p10": round(net12_med / max(abs(cmin_p10), 100.0), 3),
    }


# ---------------------------------------------------------------------------
# 4. Calibrador Tick a Tick K30 y Comparativa vs M1 (`a5.calibrar_por_sesion`)
# ---------------------------------------------------------------------------


def simular_trade_en_ticks(
    ts_ticks: np.ndarray,
    px_ticks: np.ndarray,
    en_ns: int,
    ex_ns: int,
    side: int,
    sl_pts: float,
    m1_entry_px: float,
    *,
    be_trig_r: float | None = None,
    trail_tiers: tuple[tuple[float, float], ...] | None = None,
    tp_pts: float = 0.0,
) -> dict[str, float]:
    """Simula un trade tick a tick entre [en_ns, ex_ns], respetando BE/trail causal por cierre de barra M1."""
    n = len(ts_ticks)
    if n == 0 or sl_pts <= 0.0:
        return {"ok": 0.0}
    i0 = int(np.searchsorted(ts_ticks, en_ns, side="left"))
    if i0 >= n or int(ts_ticks[i0]) >= ex_ns:
        return {"ok": 0.0}
    i1 = int(np.searchsorted(ts_ticks, ex_ns, side="right")) - 1
    if i1 < i0:
        i1 = i0

    ep_t = float(px_ticks[i0])
    slip_en = float(side) * (ep_t - float(m1_entry_px))
    stop_active = ep_t - float(side) * float(sl_pts)
    tp_lvl = (ep_t + float(side) * float(tp_pts)) if tp_pts > 0.0 else np.nan

    cur_min_bucket = int(ts_ticks[i0] // 60_000_000_000)
    bar_fav_max = 0.0
    mae_t = 0.0
    mfe_t = 0.0
    exited = False
    ex_px = float(px_ticks[i1])
    ex_ts = int(ts_ticks[i1])
    motivo = 0.0  # 0=tiempo/senal, 1=stop, 2=tp

    for k in range(i0, i1 + 1):
        tk = int(ts_ticks[k])
        pk = float(px_ticks[k])
        mb = int(tk // 60_000_000_000)
        if mb != cur_min_bucket:
            # Al cerrar el minuto anterior, actualizar BE / trailing para ticks del nuevo minuto (causal)
            if be_trig_r is not None and be_trig_r > 0.0 and bar_fav_max >= float(be_trig_r) * float(sl_pts):
                if side == 1 and ep_t > stop_active:
                    stop_active = ep_t
                elif side == -1 and ep_t < stop_active:
                    stop_active = ep_t
            if trail_tiers:
                for trig_r, lock_r in trail_tiers:
                    if bar_fav_max >= float(trig_r) * float(sl_pts):
                        cand = ep_t + float(side) * float(lock_r) * float(sl_pts)
                        if side == 1 and cand > stop_active:
                            stop_active = cand
                        elif side == -1 and cand < stop_active:
                            stop_active = cand
            cur_min_bucket = mb

        fav_now = (pk - ep_t) * float(side)
        adv_now = (ep_t - pk) * float(side)
        if fav_now > bar_fav_max:
            bar_fav_max = fav_now
        if fav_now > mfe_t:
            mfe_t = fav_now
        if adv_now > mae_t:
            mae_t = adv_now

        # Stop primero por conservadurismo
        if (side == 1 and pk <= stop_active) or (side == -1 and pk >= stop_active):
            ex_px = pk
            ex_ts = tk
            exited = True
            motivo = 1.0
            break
        if tp_pts > 0.0:
            if (side == 1 and pk >= tp_lvl) or (side == -1 and pk <= tp_lvl):
                ex_px = pk
                ex_ts = tk
                exited = True
                motivo = 2.0
                break

    pnl_t = float(side) * (ex_px - ep_t)
    dur_s = max(0.0, float(ex_ts - int(ts_ticks[i0])) / 1_000_000_000.0)
    return {
        "ok": 1.0,
        "pnl_pts": pnl_t,
        "R_bruto": pnl_t / float(sl_pts),
        "mae_pts": max(0.0, mae_t),
        "mfe_pts": max(0.0, mfe_t),
        "slip_en_pts": slip_en,
        "dur_s": dur_s,
        "motivo": motivo,
    }


def _leer_ticks_por_sesiones(parquet_path: Path, sesiones_set: set[int]) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    """Lee un parquet canonico de ticks por row-groups filtrando exactamente sesiones_set (~outside_regular)."""
    pf = pq.ParquetFile(parquet_path)
    i_td = pf.schema_arrow.get_field_index("trade_date")
    rg_map: dict[int, list[int]] = {}
    for g in range(pf.num_row_groups):
        st = pf.metadata.row_group(g).column(i_td).statistics
        lo_d, hi_d = int(st.min), int(st.max)
        if any(lo_d <= td <= hi_d for td in sesiones_set):
            for td in sesiones_set:
                if lo_d <= td <= hi_d:
                    rg_map.setdefault(td, []).append(g)
    out: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    has_out_reg = "outside_regular" in pf.schema_arrow.names
    cols = ["ts_utc_ns", "price_ticks", "trade_date"] + (["outside_regular"] if has_out_reg else [])
    for td, rgs in sorted(rg_map.items()):
        t = pf.read_row_groups(sorted(set(rgs)), columns=cols).to_pandas()
        m = t["trade_date"].to_numpy(dtype=np.int64) == int(td)
        if has_out_reg:
            m &= ~t["outside_regular"].to_numpy(dtype=bool)
        t = t.loc[m].sort_values("ts_utc_ns", kind="mergesort")
        if len(t):
            out[int(td)] = (
                np.ascontiguousarray(t["ts_utc_ns"].to_numpy(dtype=np.int64)),
                np.ascontiguousarray(t["price_ticks"].to_numpy(dtype=np.float64) * 0.25),
            )
    return out


def calibrar_m1_vs_ticks_nq(
    ops_all: Mapping[str, pd.DataFrame],
    miembros: list[str],
    w_map: Mapping[str, float],
    fric_nq: float,
    fric_mnq: float,
    *,
    parquet_ticks: Path = TICKS_K30_PARQUET,
    particiones_k30: tuple[str, ...] = ("DESC", "REP"),
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Ejecuta calibracion K30 M1 vs ticks reales + anti-microscalping + sensibilidad costos 1.0x/1.25x/1.5x."""
    if not parquet_ticks.exists():
        raise FileNotFoundError(f"Falta archivo de ticks K30: {parquet_ticks}")

    pf = pq.ParquetFile(parquet_ticks)
    td_all = pq.read_table(parquet_ticks, columns=["trade_date"]).to_pandas()["trade_date"].unique().tolist()
    ses_cal = {int(td) for td in td_all if int(td) < HOLDOUT_PRIMERA_SESION_INT and a5_bloque(int(td)) in particiones_k30}
    ticks_by_day = _leer_ticks_por_sesiones(parquet_ticks, ses_cal)

    filas_cal: list[dict[str, Any]] = []
    detalles_trades: list[dict[str, Any]] = []
    cartera_t_ses: dict[int, float] = {td: 0.0 for td in ses_cal}
    cartera_m_ses: dict[int, float] = {td: 0.0 for td in ses_cal}

    for mod_var in miembros:
        df = ops_all[mod_var]
        sub = df[df["fecha_int"].isin(ses_cal)].copy().reset_index(drop=True)
        w_m = float(w_map.get(f"{mod_var}::NQ", 0.0))
        sp_meta = CORE7_SPECS.get(mod_var, {}).get("overlay", {})
        be_r = sp_meta.get("be_trigger_r")
        tr_t = sp_meta.get("trail_tiers")

        t_ses: dict[int, float] = {}
        m_ses: dict[int, float] = {}
        pnl_m1_l: list[float] = []
        pnl_tk_l: list[float] = []
        r_m1_l: list[float] = []
        r_tk_l: list[float] = []
        slips_l: list[float] = []
        durs_s: list[float] = []
        mae_m1_l: list[float] = []
        mae_tk_l: list[float] = []

        for _, row in sub.iterrows():
            td = int(row["fecha_int"])
            if td not in ticks_by_day:
                continue
            ts_d, px_d = ticks_by_day[td]
            # Para T, recordar ex_ns extendido por el modulo base; pasamos be_trigger_r causal
            # Para SOMEOD el trail de SL va al cierre M5 dentro de su ex_ns real
            sim = simular_trade_en_ticks(
                ts_d,
                px_d,
                int(row["en_ns"]),
                int(row["ex_ns"]) + 59_000_000_000 if mod_var == "SOMEOD_ext_NQ" and "EOD" in str(row.get("exit_name", "")) else int(row["ex_ns"]),
                int(row["side"]),
                float(row["riesgo_pts"]),
                float(row["entry_price"]),
                be_trig_r=be_r,
                trail_tiers=tr_t,
            )
            if sim.get("ok", 0.0) < 0.5:
                continue
            rn_m1 = float(row["R_neto_mini"])
            rn_tk = (float(sim["pnl_pts"]) - float(fric_nq)) / float(row["riesgo_pts"])
            rb_m1 = float(row["R_bruto"])
            rb_tk = float(sim["R_bruto"])

            m_ses[td] = m_ses.get(td, 0.0) + rn_m1
            t_ses[td] = t_ses.get(td, 0.0) + rn_tk
            cartera_m_ses[td] = cartera_m_ses.get(td, 0.0) + w_m * rn_m1
            cartera_t_ses[td] = cartera_t_ses.get(td, 0.0) + w_m * rn_tk

            pnl_m1_l.append(float(row["pnl_pts"]) - float(fric_nq))
            pnl_tk_l.append(float(sim["pnl_pts"]) - float(fric_nq))
            r_m1_l.append(rn_m1)
            r_tk_l.append(rn_tk)
            slips_l.append(float(sim["slip_en_pts"]))
            durs_s.append(float(sim["dur_s"]))
            mae_m1_l.append(float(row["mae_pts"]))
            mae_tk_l.append(float(sim["mae_pts"]))

            detalles_trades.append({
                "modulo": mod_var,
                "fecha_int": td,
                "pnl_neto_m1": pnl_m1_l[-1],
                "pnl_neto_ticks": pnl_tk_l[-1],
                "R_neto_m1": rn_m1,
                "R_neto_ticks": rn_tk,
                "slip_en_pts": slips_l[-1],
                "dur_s": durs_s[-1],
                "mae_m1": mae_m1_l[-1],
                "mae_ticks": mae_tk_l[-1],
            })

        cal = A5.calibrar_por_sesion(t_ses, m_ses)
        d_arr = np.asarray(durs_s, dtype=float)
        ptk = np.asarray(pnl_tk_l, dtype=float)
        pos_tot = float(np.sum(ptk[ptk > 0.0])) if np.any(ptk > 0.0) else 1.0
        gain_gt10 = float(np.sum(ptk[(ptk > 0.0) & (d_arr > 10.0)])) / pos_tot * 100.0 if len(d_arr) else 0.0
        gain_gt5 = float(np.sum(ptk[(ptk > 0.0) & (d_arr > 5.0)])) / pos_tot * 100.0 if len(d_arr) else 0.0

        filas_cal.append({
            "modulo": mod_var,
            "sesiones_ticks": len(ses_cal),
            "comunes": int(cal["comunes"]),
            "n_trades": len(r_tk_l),
            "R_neto_m1": round(float(np.mean(r_m1_l)), 4) if r_m1_l else np.nan,
            "R_neto_ticks": round(float(np.mean(r_tk_l)), 4) if r_tk_l else np.nan,
            "corr_sesion": round(float(cal["corr"]), 4) if np.isfinite(cal["corr"]) else np.nan,
            "ticks_ses_media": round(float(cal["ticks_media"]), 4),
            "m1_ses_media": round(float(cal["m1_media"]), 4),
            "ee_comb": round(float(cal["ee"]), 4) if np.isfinite(cal["ee"]) else np.nan,
            "calibra_k30": bool(cal["calibra"]),
            "slip_entrada_med_pts": round(float(np.mean(slips_l)), 3) if slips_l else np.nan,
            "mae_p95_m1": round(float(np.quantile(mae_m1_l, 0.95)), 1) if mae_m1_l else np.nan,
            "mae_p95_ticks": round(float(np.quantile(mae_tk_l, 0.95)), 1) if mae_tk_l else np.nan,
            "pct_trades_gt5s": round(100.0 * float(np.mean(d_arr > 5.0)), 1) if len(d_arr) else np.nan,
            "pct_trades_gt10s": round(100.0 * float(np.mean(d_arr > 10.0)), 1) if len(d_arr) else np.nan,
            "pct_gan_gt10s": round(gain_gt10, 1),
            "pct_gan_gt5s": round(gain_gt5, 1),
        })

    # Fila global de cartera P_OPT_SF_v2 ponderada (sesiones activas en K30)
    cal_port = A5.calibrar_por_sesion(
        {k: v for k, v in cartera_t_ses.items() if abs(v) > 1e-12 or abs(cartera_m_ses.get(k, 0.0)) > 1e-12},
        {k: v for k, v in cartera_m_ses.items() if abs(v) > 1e-12 or abs(cartera_t_ses.get(k, 0.0)) > 1e-12},
    )
    df_det = pd.DataFrame(detalles_trades)
    sens_costos: list[dict[str, Any]] = []
    if not df_det.empty:
        # Calcular riesgo medio en USD y sensibilidad 1.0x / 1.25x / 1.5x friccion sobre R_neto
        for mult in (1.0, 1.25, 1.5):
            r_adj = []
            for mod_var in miembros:
                sub_m = ops_all[mod_var]
                sub_m = sub_m[sub_m["fecha_int"].isin(ses_cal)]
                if sub_m.empty:
                    continue
                r_m = (sub_m["pnl_pts"] - float(mult) * float(fric_nq)) / sub_m["riesgo_pts"]
                w_m = float(w_map.get(f"{mod_var}::NQ", 0.0))
                r_adj.append(float(r_m.sum()) * w_m)
            tot_r = sum(r_adj)
            sens_costos.append({
                "mult_friccion": mult,
                "fric_nq_pts": round(float(mult) * float(fric_nq), 3),
                "R_cartera_k30": round(tot_r, 2),
                "R_por_mes_k30": round(tot_r / max(len(ses_cal) / 21.0, 1.0), 3),
            })

    d_tot = df_det["dur_s"].to_numpy(float) if not df_det.empty else np.zeros(0)
    ptk_tot = df_det["pnl_neto_ticks"].to_numpy(float) if not df_det.empty else np.zeros(0)
    pos_sum = float(np.sum(ptk_tot[ptk_tot > 0.0])) if np.any(ptk_tot > 0.0) else 1.0
    filas_cal.append({
        "modulo": "CARTERA_P_OPT_SF_v2",
        "sesiones_ticks": len(ses_cal),
        "comunes": int(cal_port["comunes"]),
        "n_trades": len(df_det),
        "R_neto_m1": round(float(df_det["R_neto_m1"].mean()), 4) if not df_det.empty else np.nan,
        "R_neto_ticks": round(float(df_det["R_neto_ticks"].mean()), 4) if not df_det.empty else np.nan,
        "corr_sesion": round(float(cal_port["corr"]), 4) if np.isfinite(cal_port["corr"]) else np.nan,
        "ticks_ses_media": round(float(cal_port["ticks_media"]), 4),
        "m1_ses_media": round(float(cal_port["m1_media"]), 4),
        "ee_comb": round(float(cal_port["ee"]), 4) if np.isfinite(cal_port["ee"]) else np.nan,
        "calibra_k30": bool(cal_port["calibra"]),
        "slip_entrada_med_pts": round(float(df_det["slip_en_pts"].mean()), 3) if not df_det.empty else np.nan,
        "mae_p95_m1": round(float(np.quantile(df_det["mae_m1"], 0.95)), 1) if not df_det.empty else np.nan,
        "mae_p95_ticks": round(float(np.quantile(df_det["mae_ticks"], 0.95)), 1) if not df_det.empty else np.nan,
        "pct_trades_gt5s": round(100.0 * float(np.mean(d_tot > 5.0)), 1) if len(d_tot) else np.nan,
        "pct_trades_gt10s": round(100.0 * float(np.mean(d_tot > 10.0)), 1) if len(d_tot) else np.nan,
        "pct_gan_gt10s": round(float(np.sum(ptk_tot[(ptk_tot > 0.0) & (d_tot > 10.0)])) / pos_sum * 100.0, 1) if len(d_tot) else np.nan,
        "pct_gan_gt5s": round(float(np.sum(ptk_tot[(ptk_tot > 0.0) & (d_tot > 5.0)])) / pos_sum * 100.0, 1) if len(d_tot) else np.nan,
    })

    return pd.DataFrame(filas_cal), df_det, {"sensibilidad_costos": sens_costos, "sesiones_k30": len(ses_cal)}


# ---------------------------------------------------------------------------
# 5. Confirmacion Congelada en A5_HOLDOUT y TERMINAL (M1 + Ticks Sellados)
# ---------------------------------------------------------------------------


def _as_ns(dt_idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return dt_idx.as_unit("ns") if hasattr(dt_idx, "as_unit") else dt_idx.astype("datetime64[ns]")


def _cargar_ms_completo_con_terminal(m1_dir: Path | None = None, desde: str = "2008-01-01") -> tuple[Any, pd.DataFrame, pd.Series, pd.Series, dict[str, np.ndarray]]:
    """Uso exclusivo de `confirmar_holdout_congelado`: carga M1 real NQ hasta ultima fecha disponible (incluyendo TERMINAL >= 20261001)."""
    pq_path = BASE._resolver_parquet("NQ", m1_dir=m1_dir)
    raw = pd.read_parquet(pq_path)
    ts_all = _as_ns(pd.DatetimeIndex(raw.index if "datetime" not in raw else raw["datetime"]))
    ts_i8 = ts_all.asi8
    d_i8 = np.int64(pd.Timestamp(desde).as_unit("ns").value)
    sub = raw.loc[ts_i8 >= d_i8].reset_index()
    del raw, ts_all, ts_i8

    tick = float(costos.tick_size("NQ"))
    pv = float(costos.tick_value_usd("NQ") / tick)
    df_m1 = load_m1_data(sub, start=desde, end=None, tz_input="UTC", allow_sellado=True)
    del sub
    ms = build_multi_series(df_m1, tick_size=tick, point_value=pv, tz_input="UTC", allow_sellado=True)
    del df_m1
    gc.collect()

    # Serie M1 en NY naive completa para ATR20 / ORB15 / SOMEOD sin truncation
    raw2 = pd.read_parquet(pq_path)
    t_idx = _as_ns(pd.DatetimeIndex(raw2.index if "datetime" not in raw2 else raw2["datetime"]))
    ny_idx = t_idx.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
    m1_ny = pd.DataFrame(
        {
            "o": raw2["open"].to_numpy(float),
            "h": raw2["high"].to_numpy(float),
            "l": raw2["low"].to_numpy(float),
            "c": raw2["close"].to_numpy(float),
            "v": raw2["volume"].to_numpy(float),
        },
        index=ny_idx,
    )
    m1_ny = m1_ny[m1_ny.index >= desde]
    atr_nq = BASE.atr20(m1_ny)

    mm = m1_ny.index.hour * 60 + m1_ny.index.minute
    orb = m1_ny[(mm >= 570) & (mm < 585)]
    dd_orb = orb.index.normalize()
    orb_raw = (orb.h.groupby(dd_orb).max() - orb.l.groupby(dd_orb).min())
    m1_arr = _m1_ny_a_arrays(m1_ny)
    return ms, m1_ny, atr_nq, orb_raw, m1_arr


def _replay_calendario_lucid_v2(
    P_ev: np.ndarray,
    LO_ev: np.ndarray,
    P_fd: np.ndarray,
    LO_fd: np.ndarray,
    sesiones: list[int],
    plan_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    """Bitacora calendario real dia a dia de compras escalonadas, aprobaciones, quemas y retiros."""
    pr = float(plan_cfg["eval_fee_sim"])
    objetivo = float(plan_cfg["profit_target"])
    mll = float(plan_cfg["max_loss"])
    dll = float(plan_cfg.get("eval_dll", 0.0))
    dia_min = float(plan_cfg.get("payout_day_min_profit", 150.0))
    tope = float((plan_cfg.get("payout_caps") or [3000.0])[0])
    cons = float(plan_cfg.get("eval_consistency", 0.4))
    eval_cap_cons = bool(plan_cfg.get("eval_cap_cons", True))
    colchon_min = float(plan_cfg.get("payout_buffer_post", 0.0))
    max_eval = int(plan_cfg.get("max_eval", 5))
    max_fund = int(plan_cfg.get("max_funded", 5))
    max_tot = int(plan_cfg.get("max_total", 10))
    stagger = int(plan_cfg.get("stagger_days", 3))
    cap_ev = 0.95 * cons * objetivo if eval_cap_cons else 1e18

    cuentas: list[dict[str, Any]] = []
    caja = 0.0
    last_buy = -1000
    diario: list[dict[str, Any]] = []

    for d, td in enumerate(sesiones):
        p_ev, lo_ev = (float(P_ev[d]), float(LO_ev[d]))
        if dll > 0.0 and lo_ev <= -dll:
            p_ev, lo_ev = -dll, -dll
        elif eval_cap_cons and p_ev > cap_ev:
            p_ev = cap_ev

        p_fd, lo_fd = (-dll, -dll) if (dll > 0.0 and LO_fd[d] <= -dll) else (float(P_fd[d]), float(LO_fd[d]))

        for a in cuentas:
            if a["estado"] == "eval":
                if a["bal"] + lo_ev <= a["piso"]:
                    a["estado"] = "quemada_eval"
                    a["fin"] = int(td)
                    continue
                a["bal"] += p_ev
                a["mayor"] = max(a["mayor"], p_ev)
                a["maxc"] = max(a["maxc"], a["bal"])
                a["piso"] = min(max(a["piso"], a["maxc"] - mll), 100.0)
                if a["bal"] >= objetivo and a["bal"] > 0.0 and a["mayor"] / a["bal"] <= cons:
                    a["estado"] = "aprobada"
                    a["paso"] = int(td)
            elif a["estado"] == "fondeada":
                if a["bal"] + lo_fd <= a["piso"]:
                    a["estado"] = "quemada_fondeada"
                    a["fin"] = int(td)
                    continue
                a["bal"] += p_fd
                if p_fd >= dia_min:
                    a["dok"] += 1
                a["maxc"] = max(a["maxc"], a["bal"])
                if a["piso"] < 100.0:
                    a["piso"] = 100.0 if a["maxc"] >= mll + 100.0 else max(a["piso"], a["maxc"] - mll)
                m_ret = min(tope, 0.5 * a["bal"])
                if a["dok"] >= 5 and a["bal"] > a["c0"] and m_ret >= 500.0 and (a["bal"] - m_ret - 100.0) >= colchon_min:
                    caja += 0.9 * m_ret
                    a["retiros"].append({"fecha": int(td), "neto_usd": round(0.9 * m_ret, 2)})
                    a["bal"] -= m_ret
                    a["piso"] = 100.0
                    a["c0"] = a["bal"]
                    a["dok"] = 0

        nf = sum(a["estado"] == "fondeada" for a in cuentas)
        for a in cuentas:
            if a["estado"] == "aprobada" and nf < max_fund:
                a["estado"] = "fondeada"
                a["fondeada_desde"] = int(td)
                a.update(bal=0.0, piso=-mll, maxc=0.0, dok=0, c0=0.0)
                nf += 1

        ne = sum(a["estado"] in ("eval", "aprobada") for a in cuentas)
        if (d - last_buy) >= stagger and ne < max_eval and (ne + nf) < max_tot:
            cuentas.append({
                "id": len(cuentas) + 1,
                "compra": int(td),
                "estado": "eval",
                "bal": 0.0,
                "piso": -mll,
                "maxc": 0.0,
                "mayor": 0.0,
                "retiros": [],
                "dok": 0,
                "c0": 0.0,
            })
            caja -= pr
            last_buy = d

        diario.append({
            "fecha": int(td),
            "usd_dia_fd": round(float(P_fd[d]), 2),
            "lo_dia_fd": round(float(LO_fd[d]), 2),
            "caja_acum": round(caja, 2),
        })

    # Valoracion abierta conservadora al cierre del periodo terminal
    bal_eval_ab = sum(max(0.0, a["bal"]) for a in cuentas if a["estado"] in ("eval", "aprobada"))
    bal_fund_ab = sum(a["bal"] for a in cuentas if a["estado"] == "fondeada")
    return {
        "sesiones": len(sesiones),
        "caja_realizada_usd": round(caja, 2),
        "comprado_usd": round(pr * len(cuentas), 2),
        "cobrado_usd": round(sum(r["neto_usd"] for a in cuentas for r in a["retiros"]), 2),
        "n_evals_compradas": len(cuentas),
        "n_aprobadas": sum(a["estado"] in ("aprobada", "fondeada", "quemada_fondeada") or ("paso" in a) for a in cuentas),
        "n_quemadas_eval": sum(a["estado"] == "quemada_eval" for a in cuentas),
        "n_quemadas_fund": sum(a["estado"] == "quemada_fondeada" for a in cuentas),
        "balance_fondeadas_final_usd": round(bal_fund_ab, 2),
        "balance_evals_final_usd": round(bal_eval_ab, 2),
        "cuentas": cuentas,
        "diario": diario,
    }


def confirmar_holdout_congelado(
    miembros: list[str],
    w_map: Mapping[str, float],
    planes_congelados: list[dict[str, Any]],
    fric_nq: float,
    fric_mnq: float,
    *,
    ops_all_pre: Mapping[str, pd.DataFrame],
    m1_dir: Path | None = None,
) -> dict[str, Any]:
    """Ejecuta confirmacion unica congelada en A5_HOLDOUT y TERMINAL (M1 + ticks sellados C:\\EdgeLab\\sellado)."""
    # 1) H1: A5_HOLDOUT (2020-01..2026-09, ~21 meses nunca mirados en Iters 1-4)
    pq_path = BASE._resolver_parquet("NQ", m1_dir=m1_dir)
    raw_idx = _as_ns(pd.DatetimeIndex(pd.read_parquet(pq_path, columns=["close"]).index))
    ny_dates = (raw_idx.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None) + pd.Timedelta(hours=6)).normalize()
    uniq_dates = sorted({int(d.strftime("%Y%m%d")) for d in ny_dates if d.weekday() < 5})
    ses_a5_ho = [d for d in uniq_dates if 20200101 <= d < HOLDOUT_PRIMERA_SESION_INT and a5_bloque(d) == "HOLDOUT"]
    m_a5_ho = BASE._meses_activos_a5(20200101, 20260930, "HOLDOUT")

    filas_h1_mod: list[dict[str, Any]] = []
    for m in miembros:
        df = ops_all_pre[m]
        sub = df[(df["a5"] == "HOLDOUT") & (df["fecha_int"] >= 20200101)].copy()
        st = BASE.resumir_serie_r(sub, col_r="R_neto_mini", bootstrap_reps=1200, seed=71, meses_totales=m_a5_ho)
        dd = IT2._metricas_dd_r(sub, m_a5_ho)
        filas_h1_mod.append({"modulo": m, **st, **dd})

    tr_ho, mx_ho = extraer_tr_particion(ops_all_pre, miembros, w_map, fric_nq, part="HOLDOUT", desde_int=20200101)
    sd_ho = tr_ho.groupby("fecha_int")["R_eff"].sum().reindex(ses_a5_ho, fill_value=0.0) if not tr_ho.empty else pd.Series(0.0, index=ses_a5_ho)
    ev_ho = IT2.evaluar_serie_cartera(sd_ho, m_a5_ho, mc_reps=4000, seed=71)

    j_ho = generar_j_seq_bootstrap(len(ses_a5_ho), N=3000, H=504, seed=20261125)
    filas_h1_prop: list[dict[str, Any]] = []
    for pl in planes_congelados:
        for cn, cm in (("real_100", 1.0), ("contraida_60", 0.60), ("cero_0", 0.0)):
            r_p, _ = evaluar_config_multiprop(pl, tr_ho, ses_a5_ho, fric_nq, fric_mnq, "A5_HOLDOUT", cn, cm, j_ho)
            filas_h1_prop.append(r_p)

    # 2) H2: TERMINAL (2026-10-01 -> ultima fecha M1 NT8 + calibracion sellada C:\EdgeLab\sellado)
    ms_full, m1_ny_full, atr_full, orb_full, m1_arr_full = _cargar_ms_completo_con_terminal(m1_dir=m1_dir, desde="2008-01-01")
    ses_term = [d for d in uniq_dates if d >= HOLDOUT_PRIMERA_SESION_INT]

    ops_term_map: dict[str, pd.DataFrame] = {}
    for m in miembros:
        if m == "SOMEOD_ext_NQ":
            som_f = generar_ops_someod_desde_m1(m1_ny_full, fric_nq, fric_mnq, incluir_terminal=True)
            ops_term_map[f"{m}::NQ"] = som_f[som_f["a5"] == "TERMINAL"].copy()
            continue
        sp = CORE7_SPECS[m]
        cls = BASE.CONFIG_CLASSES[sp["modulo"]]
        cfg = dataclasses.replace(cls(), **sp["params"]) if sp["params"] else cls()
        df_t = correr_modulo(sp["modulo"], ms_full, cfg=cfg)
        ov = sp["overlay"]
        ops_term_map[f"{m}::NQ"] = overlay_m1_por_particion(
            df_t,
            sp["modulo"],
            atr_full,
            orb_full,
            m1_arr_full,
            fric_nq,
            fric_mnq,
            particiones_ok=("TERMINAL",),
            permitir_terminal=True,
            be_trigger_r=ov.get("be_trigger_r"),
            trail_tiers=ov.get("trail_tiers"),
            sl_atr_k=ov.get("sl_atr_k"),
            stop_orb_mult=ov.get("stop_orb_mult", 1.25),
            stop_min_pts=ov.get("stop_min_pts", 2.0),
            stop_max_pts=ov.get("stop_max_pts", 100.0),
        )

    del ms_full, m1_ny_full, atr_full, orb_full, m1_arr_full
    gc.collect()

    filas_h2_mod: list[dict[str, Any]] = []
    for m in miembros:
        sub = ops_term_map[f"{m}::NQ"]
        if sub.empty:
            filas_h2_mod.append({"modulo": m, "n": 0, "R_neto_mini": 0.0, "R_tot": 0.0})
            continue
        filas_h2_mod.append({
            "modulo": m,
            "n": int(len(sub)),
            "R_neto_mini": round(float(sub["R_neto_mini"].mean()), 4),
            "R_tot": round(float(sub["R_neto_mini"].sum()), 2),
        })

    tr_term, mx_term = IT2.aplicar_tope_concurrencia_causal(ops_term_map, w_map, None, cap_r=3.0)
    tr_term = _reinyectar_campos_ops(tr_term, ops_term_map, fric_nq)
    sd_term = tr_term.groupby("fecha_int")["R_eff"].sum().reindex(ses_term, fill_value=0.0) if not tr_term.empty else pd.Series(0.0, index=ses_term)
    ev_term = IT2.evaluar_serie_cartera(sd_term, max(len(ses_term) / 21.0, 1.0), mc_reps=2000, seed=72)
    ev_term["R_total"] = round(float(sd_term.sum()), 2)

    # Calibracion en ticks sellados reales de C:\EdgeLab\sellado (20261001..20261113, sin 20261007)
    sellado_res: dict[str, Any] = {"ok": False, "sesiones_selladas": 0}
    if SELLADO_NQ_DIR.exists():
        parqs_sel = sorted(SELLADO_NQ_DIR.glob("NQ_*_ticks.parquet"))
        # Evitar doble conteo entre NQ_12-26_ticks y archivos diarios: dar prioridad a diarios cuando existen
        ticks_sel: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        for pq_s in sorted(parqs_sel, key=lambda p: ("_2026" in p.name, p.name)):
            t = pq.read_table(pq_s, columns=["ts_utc_ns", "price_ticks", "trade_date"]).to_pandas()
            t = t[t["ts_utc_ns"] >= HOLDOUT_APERTURA_UTC_NS]
            for td, g in t.groupby("trade_date", sort=True):
                td_i = int(td)
                if sesion_excluida("NQ", td_i):
                    continue
                g = g.sort_values("ts_utc_ns", kind="mergesort")
                ticks_sel[td_i] = (
                    np.ascontiguousarray(g["ts_utc_ns"].to_numpy(dtype=np.int64)),
                    np.ascontiguousarray(g["price_ticks"].to_numpy(dtype=np.float64) * 0.25),
                )
        ses_s_ok = sorted(ticks_sel)
        m1_s_ses = {td: 0.0 for td in ses_s_ok}
        tk_s_ses = {td: 0.0 for td in ses_s_ok}
        n_tr_sel = 0
        for m in miembros:
            sub = ops_term_map[f"{m}::NQ"]
            w_m = float(w_map.get(f"{m}::NQ", 0.0))
            ov = CORE7_SPECS.get(m, {}).get("overlay", {})
            for _, rw in sub.iterrows():
                td = int(rw["fecha_int"])
                if td not in ticks_sel:
                    continue
                ts_d, px_d = ticks_sel[td]
                sim = simular_trade_en_ticks(
                    ts_d,
                    px_d,
                    int(rw["en_ns"]),
                    int(rw["ex_ns"]),
                    int(rw["side"]),
                    float(rw["riesgo_pts"]),
                    float(rw["entry_price"]),
                    be_trig_r=ov.get("be_trigger_r"),
                    trail_tiers=ov.get("trail_tiers"),
                )
                if sim.get("ok", 0.0) < 0.5:
                    continue
                n_tr_sel += 1
                m1_s_ses[td] += w_m * float(rw["R_neto_mini"])
                tk_s_ses[td] += w_m * ((float(sim["pnl_pts"]) - float(fric_nq)) / float(rw["riesgo_pts"]))
        sellado_res = {
            "ok": True,
            "sesiones_selladas": len(ses_s_ok),
            "rango": [ses_s_ok[0], ses_s_ok[-1]] if ses_s_ok else [],
            "n_trades_emparejados": n_tr_sel,
            "R_total_m1_sellado": round(float(sum(m1_s_ses.values())), 2),
            "R_total_ticks_sellado": round(float(sum(tk_s_ses.values())), 2),
            "corr_diaria": round(float(np.corrcoef([m1_s_ses[s] for s in ses_s_ok], [tk_s_ses[s] for s in ses_s_ok])[0, 1]), 4) if len(ses_s_ok) > 2 else np.nan,
        }

    # Replay calendario de los 3 planos congelados sobre TERMINAL (en M1)
    replays: dict[str, Any] = {}
    for pl in planes_congelados:
        pol_pl = str(pl.get("politica_colision", "independiente"))
        P_t, LO_t, _, _ = construir_serie_intradia_prop_v2(
            tr_term, ses_term, float(pl["usd_fund"]), int(pl["max_micros"]), bool(pl["hibrido"]), fric_nq, fric_mnq, 1.0,
            politica_colision=pol_pl,
        )
        P_ev_t, LO_ev_t, _, _ = construir_serie_intradia_prop_v2(
            tr_term, ses_term, float(pl["usd_ev"]), int(pl["max_micros"]), bool(pl["hibrido"]), fric_nq, fric_mnq, 1.0,
            politica_colision=pol_pl,
        )
        rep_pl = _replay_calendario_lucid_v2(P_ev_t, LO_ev_t, P_t, LO_t, ses_term, pl)
        rep_pl["config_id"] = str(pl["config_id"])
        replays[str(pl["perfil_final"])] = rep_pl

    # Exportar CSV oraculo de paridad 2025-2026 para NT8 (pre-terminal + terminal completo para validacion en Strategy Analyzer)
    partes_ref = []
    for m in miembros:
        d_pre = ops_all_pre[m][ops_all_pre[m]["fecha_int"] >= 20250101].copy()
        d_ter = ops_term_map[f"{m}::NQ"].copy()
        d_comb = pd.concat([d_pre, d_ter], ignore_index=True)
        d_comb["modulo"] = m
        d_comb["w_w5"] = round(float(w_map.get(f"{m}::NQ", 0.0)), 6)
        partes_ref.append(d_comb)
    df_ref = pd.concat(partes_ref, ignore_index=True).sort_values(["en_ns", "modulo"]).reset_index(drop=True)
    df_ref["en_ny"] = pd.to_datetime(df_ref["en_ns"], unit="ns", utc=True).dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d %H:%M:%S")
    df_ref["ex_ny"] = pd.to_datetime(df_ref["ex_ns"], unit="ns", utc=True).dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d %H:%M:%S")
    cols_ref = ["fecha_int", "a5", "modulo", "w_w5", "side", "en_ny", "ex_ny", "entry_price", "stop_price", "exit_price", "riesgo_pts", "pnl_pts", "R_bruto", "R_neto_mini", "exit_name"]
    df_ref[cols_ref].to_csv(OUT_DIR / "REFERENCIA_PARIDAD_P_OPT_SF_v2.csv", index=False)

    return {
        "a5_holdout": {
            "sesiones": len(ses_a5_ho),
            "meses": m_a5_ho,
            "modulos": filas_h1_mod,
            "cartera": ev_ho,
            "max_open_R": mx_ho,
            "planes_prop": filas_h1_prop,
        },
        "terminal": {
            "sesiones": len(ses_term),
            "rango": [ses_term[0], ses_term[-1]] if ses_term else [],
            "modulos": filas_h2_mod,
            "cartera": ev_term,
            "max_open_R": mx_term,
            "sellado_ticks": sellado_res,
            "replays_calendario": replays,
        },
    }


# ---------------------------------------------------------------------------
# 6. Orquestadores Etapa A, Etapa C y Graficos
# ---------------------------------------------------------------------------


def correr_etapa_a(
    ops_all: Mapping[str, pd.DataFrame],
    meta_v2: Mapping[str, Any],
    fechas_nq: Mapping[str, list[int]],
    fric_nq: float,
    fric_mnq: float,
) -> dict[str, Any]:
    """Ejecuta auditoria de colisiones opuestas + 18 combinaciones LucidFlex en DESC/REP y congela 3 planos."""
    miembros = list(meta_v2["miembros"])
    w_map = dict(meta_v2["w_map"])
    ses_desc = fechas_nq["DESC"]
    ses_rep = fechas_nq["REP"]

    tr_desc, mx_desc = extraer_tr_particion(ops_all, miembros, w_map, fric_nq, part="DESC", desde_int=20200101)
    tr_rep, mx_rep = extraer_tr_particion(ops_all, miembros, w_map, fric_nq, part="REP", desde_int=20200101)
    m_desc = BASE._meses_activos_a5(20200101, 20260930, "DESC")
    m_rep = BASE._meses_activos_a5(20200101, 20260930, "REP")
    ev_cartera = {
        "DESC": {**IT2.evaluar_serie_cartera(tr_desc.groupby("fecha_int")["R_eff"].sum().reindex(ses_desc, fill_value=0.0), m_desc, mc_reps=4000, seed=99), "max_open_R": mx_desc},
        "REP": {**IT2.evaluar_serie_cartera(tr_rep.groupby("fecha_int")["R_eff"].sum().reindex(ses_rep, fill_value=0.0), m_rep, mc_reps=4000, seed=99), "max_open_R": mx_rep},
    }

    # Auditoria de colisiones en DESC y REP
    col_desc = auditar_colisiones_opuestas(tr_desc, ses_desc, 450.0, 100, True, fric_nq, fric_mnq)
    col_rep = auditar_colisiones_opuestas(tr_rep, ses_rep, 450.0, 100, True, fric_nq, fric_mnq)

    # Preparar tambien P_OPT_SF ancla de Iter 4 (usando V_nm30_maeATR30 + W_noRe + SOMEOD M1) para A04_anc exacto
    pr_lucid_150_40 = float(LG.precio("150K", True, 0.40))
    pr_lucid_50_40 = float(LG.precio("50K", True, 0.40))
    pr_lucid_150_50 = float(LG.precio("150K", True, 0.50))

    def mk_lp(pid: str, desc_p: str, *, tam: str = "150K", cons: float = 0.40, u_ev: float = 650.0, u_fd: float = 450.0,
              max_eval: int = 8, stagger: int = 3, colchon: float = 2500.0, eval_cap: bool = True, pol: str = "independiente") -> dict[str, Any]:
        ct = LG.TAMANOS[tam]
        pr = pr_lucid_150_40 if (tam == "150K" and cons < 0.45) else (pr_lucid_50_40 if tam == "50K" else pr_lucid_150_50)
        return {
            "config_id": pid,
            "palanca": desc_p,
            "firm": "Lucid",
            "account_size": 150000 if tam == "150K" else 50000,
            "billing_mode": "one_time",
            "eval_fee_sim": pr,
            "activation_fee": 0.0,
            "profit_target": float(ct["objetivo"]),
            "max_loss": float(ct["mll"]),
            "eval_drawdown_kind": "eod_trailing",
            "funded_drawdown_kind": "eod_trailing",
            "lock_at_profit": float(ct["mll"]) + 100.0,
            "eval_dll": float(ct["dll"]),
            "funded_dll": float(ct["dll"]),
            "eval_consistency": float(cons),
            "eval_cap_cons": bool(eval_cap),
            "funded_consistency": 0.0,
            "eval_min_days": 2,
            "max_micros": int(ct["micros"]),
            "payout_mode": "win_days",
            "payout_min_days": 5,
            "payout_day_min_profit": float(ct["dia_min"]),
            "payout_min_profit": 1.0,
            "payout_min_amount": 500.0,
            "payout_buffer_post": float(colchon),
            "payout_lock_buffer": 100.0,
            "payout_fraction": 0.5,
            "payout_basis": "total",
            "payout_caps": [float(ct["tope"])],
            "payout_split": 0.9,
            "payout_max_count": 5,
            "close_after_max_payouts": True,
            "max_eval": int(max_eval),
            "max_funded": 5,
            "max_total": 10,
            "stagger_days": int(stagger),
            "usd_ev": float(u_ev),
            "usd_fund": float(u_fd),
            "hibrido": True,
            "politica_colision": pol,
        }

    # Exactamente 18 combinaciones integradas LucidFlex pre-registradas
    specs_18 = [
        mk_lp("L01_150K_AnclaIt4_50p_s1", "Ancla 50%+Hib+maxEval5 (s1)", cons=0.50, u_ev=450.0, u_fd=450.0, max_eval=5, stagger=1, colchon=0.0, eval_cap=False),
        mk_lp("L02_150K_Base_40p_Col2500_E5_s1", "v2 + 40%+Cap + Col$2500 + E5 (s1)", u_ev=450.0, u_fd=450.0, max_eval=5, stagger=1),
        mk_lp("L03_150K_40p_Col2500_E5_s3", "40%+Cap + Col$2500 + E5 + stag3", u_ev=450.0, u_fd=450.0, max_eval=5, stagger=3),
        mk_lp("L04_150K_40p_Col2500_E8_s3", "40%+Cap + Col$2500 + E8 + stag3", u_ev=450.0, u_fd=450.0, max_eval=8, stagger=3),
        mk_lp("L05_150K_40p_Col2500_E10_s3", "40%+Cap + Col$2500 + E10 + stag3", u_ev=450.0, u_fd=450.0, max_eval=10, stagger=3),
        mk_lp("L06_150K_Boost550_E5_s3", "Boost $550/$450 + E5 + stag3", u_ev=550.0, u_fd=450.0, max_eval=5, stagger=3),
        mk_lp("L07_150K_Boost550_E8_s3", "Boost $550/$450 + E8 + stag3", u_ev=550.0, u_fd=450.0, max_eval=8, stagger=3),
        mk_lp("L08_150K_Boost650_E5_s3", "Boost $650/$450 + E5 + stag3", u_ev=650.0, u_fd=450.0, max_eval=5, stagger=3),
        mk_lp("L09_150K_Boost650_E8_s3", "Boost $650/$450 + E8 + stag3", u_ev=650.0, u_fd=450.0, max_eval=8, stagger=3),
        mk_lp("L10_150K_Boost650_E10_s1", "Boost $650/$450 + E10 + stag1", u_ev=650.0, u_fd=450.0, max_eval=10, stagger=1),
        mk_lp("L11_150K_Boost650_E10_s3", "Boost $650/$450 + E10 + stag3", u_ev=650.0, u_fd=450.0, max_eval=10, stagger=3),
        mk_lp("L12_150K_Boost650_E10_s5", "Boost $650/$450 + E10 + stag5", u_ev=650.0, u_fd=450.0, max_eval=10, stagger=5),
        mk_lp("L13_150K_Boost750_E8_s3", "Boost $750/$450 + E8 + stag3", u_ev=750.0, u_fd=450.0, max_eval=8, stagger=3),
        mk_lp("L14_150K_Boost750_E10_s3", "Boost $750/$450 + E10 + stag3", u_ev=750.0, u_fd=450.0, max_eval=10, stagger=3),
        mk_lp("L15_150K_Boost650_E8_netting", "Equil $650/$450 + Netting", u_ev=650.0, u_fd=450.0, max_eval=8, stagger=3, pol="netting"),
        mk_lp("L16_150K_Boost650_E8_vetoOpp", "Equil $650/$450 + Veto Opuesto", u_ev=650.0, u_fd=450.0, max_eval=8, stagger=3, pol="veto_opuesto"),
        mk_lp("L17_50K_Conserv_R200_E5_s3", "50K 40%+Cap + $200/$200 + E5", tam="50K", u_ev=200.0, u_fd=200.0, max_eval=5, stagger=3, colchon=1250.0),
        mk_lp("L18_50K_Boost300_200_E8_s3", "50K 40%+Cap + Boost $300/$200 + E8", tam="50K", u_ev=300.0, u_fd=200.0, max_eval=8, stagger=3, colchon=1250.0),
    ]

    j_desc = generar_j_seq_bootstrap(len(ses_desc), N=3000, H=504, seed=20261122)
    j_rep = generar_j_seq_bootstrap(len(ses_rep), N=3000, H=504, seed=20261123)

    # Precomputar tr_df filtrados por politica de colision (independiente / netting / veto_opuesto)
    def _tr_por_pol(tr_base: pd.DataFrame, pol: str) -> pd.DataFrame:
        if pol != "veto_opuesto" or tr_base.empty:
            return tr_base
        ab = []
        keep = np.ones(len(tr_base), dtype=bool)
        s_t = tr_base.sort_values(["en_ns", "stream"], kind="mergesort").reset_index(drop=True)
        en_a = s_t["en_ns"].to_numpy(np.int64)
        ex_a = s_t["ex_ns"].to_numpy(np.int64)
        sd_a = s_t["side"].to_numpy(np.int64)
        we_a = s_t["w_eff"].to_numpy(np.float64)
        for j in range(len(s_t)):
            ab = [k for k in ab if ex_a[k] > en_a[j]]
            net_w = sum((1.0 if sd_a[k] >= 0 else -1.0) * we_a[k] for k in ab)
            if net_w * (1.0 if sd_a[j] >= 0 else -1.0) < -1e-9:
                keep[j] = False
            else:
                ab.append(j)
        return s_t.loc[keep].reset_index(drop=True)

    cache_part = {
        ("DESC", "independiente"): (tr_desc, ses_desc, j_desc),
        ("REP", "independiente"): (tr_rep, ses_rep, j_rep),
        ("DESC", "netting"): (tr_desc, ses_desc, j_desc),
        ("REP", "netting"): (tr_rep, ses_rep, j_rep),
        ("DESC", "veto_opuesto"): (_tr_por_pol(tr_desc, "veto_opuesto"), ses_desc, j_desc),
        ("REP", "veto_opuesto"): (_tr_por_pol(tr_rep, "veto_opuesto"), ses_rep, j_rep),
    }

    filas_a: list[dict[str, Any]] = []
    cache_s_a: dict[Any, Any] = {}
    for cfg in specs_18:
        pol = str(cfg["politica_colision"])
        for part in ("DESC", "REP"):
            tr_p, ses_p, jq = cache_part[(part, pol)]
            for cnom, cmult in (("real_100", 1.0), ("contraida_60", 0.60), ("cero_0", 0.0)):
                row, _ = evaluar_config_multiprop(
                    cfg, tr_p, ses_p, fric_nq, fric_mnq, part, cnom, cmult, jq,
                    cache_series=cache_s_a.setdefault((part, pol), {}),
                )
                row["palanca"] = cfg["palanca"]
                row["politica_colision"] = pol
                filas_a.append(row)

    df_a = pd.DataFrame(filas_a)
    df_a.to_csv(OUT_DIR / "etapaA_integracion_lucidflex.csv", index=False)

    # Seleccion causal EXCLUSIVAMENTE en DESC/REP contraida_60 antes de tocar holdout: congelar 3 planos finales
    c60 = df_a[df_a["regimen_media"] == "contraida_60"]
    rep60 = c60[c60["particion"] == "REP"].set_index("config_id")
    desc60 = c60[c60["particion"] == "DESC"].set_index("config_id")
    spec_by_id = {c["config_id"]: c for c in specs_18}

    # Plan Conservador (< $10k): 50K con mejor neto12 en REP60 manteniendo |p10| <= 10.000
    cands_50 = [cid for cid in ("L17_50K_Conserv_R200_E5_s3", "L18_50K_Boost300_200_E8_s3") if abs(float(rep60.loc[cid, "caja_min_p10_usd"])) <= 10500.0]
    id_cons = max(cands_50 or ["L17_50K_Conserv_R200_E5_s3"], key=lambda cid: float(rep60.loc[cid, "neto12_medio_usd"]))

    # Plan Equilibrado ($15k-$20k): 150K con mejor ratio neto12 / |caja_min_p10| y |p10| <= 20.000
    cands_eq = [
        c["config_id"] for c in specs_18
        if c["account_size"] == 150000 and c["politica_colision"] == "independiente"
        and abs(float(rep60.loc[c["config_id"], "caja_min_p10_usd"])) <= 20500.0
    ]
    id_eq = max(cands_eq or ["L09_150K_Boost650_E8_s3"], key=lambda cid: float(rep60.loc[cid, "ratio_net12_p10"]))

    # Plan Maximo Flujo ($25k+): 150K con maximo neto12_medio en REP60 + DESC60
    cands_max = [c["config_id"] for c in specs_18 if c["account_size"] == 150000 and c["politica_colision"] == "independiente"]
    id_max = max(cands_max, key=lambda cid: float(rep60.loc[cid, "neto12_medio_usd"]) + 0.35 * float(desc60.loc[cid, "neto12_medio_usd"]))

    planes_congelados = [
        {**spec_by_id[id_cons], "perfil_final": "CONSERVADOR_50K"},
        {**spec_by_id[id_eq], "perfil_final": "EQUILIBRADO_150K"},
        {**spec_by_id[id_max], "perfil_final": "MAX_FLUJO_150K"},
    ]
    (OUT_DIR / "planes_congelados.json").write_text(json.dumps(planes_congelados, indent=2, default=str), encoding="utf-8")

    return {
        "ev_cartera": ev_cartera,
        "colisiones": {"DESC": {k: v for k, v in col_desc.items() if k != "series"}, "REP": {k: v for k, v in col_rep.items() if k != "series"}},
        "df_etapa_a": df_a,
        "planes_congelados": planes_congelados,
    }


def correr_etapa_c(
    ops_all: Mapping[str, pd.DataFrame],
    miembros: list[str],
    w_map: Mapping[str, float],
    fechas_nq: Mapping[str, list[int]],
    fric_nq: float,
    fric_mnq: float,
) -> dict[str, Any]:
    """Ejecuta Etapa C: 16 configuraciones Multi-Prop Firm + 4 arquitecturas Multi-Firma sincronizadas."""
    catalogo = json.loads(CATALOGO_MULTIPROP_JSON.read_text(encoding="utf-8"))
    perfiles = list(catalogo["perfiles_simulacion_etapa_c"])

    # Sesiones por particion (DESC, REP y A5_HOLDOUT)
    pq_path = BASE._resolver_parquet("NQ")
    raw_idx = _as_ns(pd.DatetimeIndex(pd.read_parquet(pq_path, columns=["close"]).index))
    ny_d = (raw_idx.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None) + pd.Timedelta(hours=6)).normalize()
    uniq_d = sorted({int(d.strftime("%Y%m%d")) for d in ny_d if d.weekday() < 5 and int(d.strftime("%Y%m%d")) >= 20200101 and int(d.strftime("%Y%m%d")) < HOLDOUT_PRIMERA_SESION_INT})
    ses_ho = [d for d in uniq_d if a5_bloque(d) == "HOLDOUT"]

    tr_map = {
        "DESC": extraer_tr_particion(ops_all, miembros, w_map, fric_nq, part="DESC", desde_int=20200101)[0],
        "REP": extraer_tr_particion(ops_all, miembros, w_map, fric_nq, part="REP", desde_int=20200101)[0],
        "A5_HOLDOUT": extraer_tr_particion(ops_all, miembros, w_map, fric_nq, part="HOLDOUT", desde_int=20200101)[0],
    }
    ses_map = {"DESC": fechas_nq["DESC"], "REP": fechas_nq["REP"], "A5_HOLDOUT": ses_ho}
    j_map = {
        "DESC": generar_j_seq_bootstrap(len(ses_map["DESC"]), N=3000, H=504, seed=20261130),
        "REP": generar_j_seq_bootstrap(len(ses_map["REP"]), N=3000, H=504, seed=20261131),
        "A5_HOLDOUT": generar_j_seq_bootstrap(len(ses_map["A5_HOLDOUT"]), N=3000, H=504, seed=20261132),
    }

    filas_mp: list[dict[str, Any]] = []
    flujos_by_key: dict[tuple[str, str, str], tuple[dict[str, Any], np.ndarray]] = {}
    cache_s: dict[str, dict[Any, Any]] = {}

    for cfg in perfiles:
        cid = str(cfg["config_id"])
        for part in ("DESC", "REP", "A5_HOLDOUT"):
            c_part = cache_s.setdefault(part, {})
            for cnom, cmult in (("real_100", 1.0), ("contraida_60", 0.60), ("cero_0", 0.0)):
                row, fl = evaluar_config_multiprop(
                    cfg, tr_map[part], ses_map[part], fric_nq, fric_mnq, part, cnom, cmult, j_map[part],
                    cache_series=c_part,
                )
                filas_mp.append(row)
                flujos_by_key[(cid, part, cnom)] = (row, fl)

    df_mp = pd.DataFrame(filas_mp)
    df_mp.to_csv(OUT_DIR / "etapaC_multiprop_comparativa.csv", index=False)

    # 4 Arquitecturas Multi-Firma sincronizadas sobre los mismos trayectos de mercado j_seq
    arqs_def = [
        ("MP1_Duo_Equilibrado", "LucidFlex 150K + Tradeify Select Flex 150K (promo)", [("MP_LucidFlex_150K_promo", 1.0), ("MP_Tradeify_150K_promo", 1.0)]),
        ("MP2_Trio_Escalado", "LucidFlex 150K + Tradeify 150K + FundedNext Flex 150K (promo)", [("MP_LucidFlex_150K_promo", 1.0), ("MP_Tradeify_150K_promo", 1.0), ("MP_FundedNext_150K_promo", 1.0)]),
        ("MP3_Capital_Chico_50K", "LucidFlex 50K + Tradeify 50K (promo) + FundedNext 50K (promo)", [("MP_LucidFlex_50K_promo", 1.0), ("MP_Tradeify_50K_promo", 1.0), ("MP_FundedNext_50K_promo", 1.0)]),
        ("MP4_Quartet_MaxFlujo", "Lucid 150K + Tradeify 150K + FundedNext 150K + Topstep NoAct 150K", [("MP_LucidFlex_150K_promo", 1.0), ("MP_Tradeify_150K_promo", 1.0), ("MP_FundedNext_150K_promo", 1.0), ("MP_Topstep_NoAct_150K", 1.0)]),
    ]
    filas_arq: list[dict[str, Any]] = []
    for aid, desc_a, comps in arqs_def:
        for part in ("DESC", "REP", "A5_HOLDOUT"):
            for cnom in ("real_100", "contraida_60", "cero_0"):
                c_list = [(*flujos_by_key[(cid, part, cnom)][0:1], w, flujos_by_key[(cid, part, cnom)][1]) for cid, w in comps]
                filas_arq.append(agregar_arquitectura_multifirma(aid, desc_a, c_list, part, cnom))

    df_arq = pd.DataFrame(filas_arq)
    df_arq.to_csv(OUT_DIR / "etapaC_arquitecturas_multifirma.csv", index=False)
    return {"df_mp": df_mp, "df_arq": df_arq, "excluidas": catalogo["excluidas_por_algo_policy"]}


def graficar_despliegue(
    df_a: pd.DataFrame,
    col_rep: Mapping[str, Any],
    df_cal: pd.DataFrame,
    ho_res: Mapping[str, Any],
    df_mp: pd.DataFrame,
    df_arq: pd.DataFrame,
) -> dict[str, Path]:
    """Genera 3 graficos oscuros y los copia al Artifact Directory."""
    if plt is None:
        raise RuntimeError("matplotlib requerido")
    plt.rcParams["text.parse_math"] = False
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rutas: dict[str, Path] = {}

    def _est(ax: Any) -> None:
        ax.set_facecolor("#11191c")
        ax.tick_params(colors="#b8c6cc", labelsize=8.0)
        for sp in ax.spines.values():
            sp.set_color("#2a373d")
        ax.grid(color="#202b30", alpha=0.6, linewidth=0.6)

    # PNG 1: Etapa A — Integracion LucidFlex (REP contr_60) y Auditoria de Colisiones
    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(17.5, 7.6), facecolor="#0d1316")
    for ax in (ax1, ax2):
        _est(ax)

    rep_a = df_a[(df_a["particion"] == "REP") & (df_a["regimen_media"] == "contraida_60")].sort_values("neto12_medio_usd", ascending=True)
    ya = np.arange(len(rep_a))
    cols_a = ["#2ca693" if "Ancla" not in p else "#f09080" for p in rep_a["palanca"]]
    ax1.barh(ya, rep_a["neto12_medio_usd"] / 1000.0, color=cols_a, height=0.62, alpha=0.90)
    for yi, (_, rr) in enumerate(rep_a.iterrows()):
        ax1.text(float(rr["neto12_medio_usd"]) / 1000.0 + 0.25, yi,
                 f"Ret={rr['retiros_12m']:.1f} P={rr['p_1ret12_pct']:.0f}% | p10=${abs(rr['caja_min_p10_usd'])/1000:.1f}k",
                 va="center", color="#dce5ea", fontsize=7.0)
    ax1.set_yticks(ya)
    ax1.set_yticklabels([f"{r['config_id'].split('_', 1)[0]}: {r['palanca']}" for _, r in rep_a.iterrows()], fontsize=7.4)
    ax1.set_xlim(0.0, max(float(rep_a["neto12_medio_usd"].max()) / 1000.0, 10.0) + 6.5)
    ax1.set_xlabel("Caja neta media 12 meses (miles USD, REP contraida 60%)", color="#d0dce2")
    ax1.set_title("Etapa A: 18 configuraciones integradas LucidFlex (REP congelado 60%)", color="#edf4f7", fontsize=10.3)

    # Panel derecho: frontera Neto12 vs |p10| por politica de colision y tamaño
    xr = np.abs(rep_a["caja_min_p10_usd"].to_numpy(float)) / 1000.0
    yr_v = rep_a["neto12_medio_usd"].to_numpy(float) / 1000.0
    sz = np.clip(rep_a["retiros_12m"].to_numpy(float) * 28.0, 50.0, 480.0)
    sc = ax2.scatter(xr, yr_v, s=sz, c=rep_a["p_neto12_pos_pct"].to_numpy(float), cmap="viridis", vmin=50.0, vmax=95.0, alpha=0.9, edgecolors="#e6eef2")
    puestos: list[tuple[float, float]] = []
    span_x = max(float(xr.max() - xr.min()), 1.0)
    span_y = max(float(yr_v.max() - yr_v.min()), 1.0)
    offs = (
        (0.035, 0.045),
        (0.035, -0.065),
        (-0.095, 0.055),
        (-0.095, -0.065),
        (0.070, 0.095),
        (-0.115, 0.005),
        (0.065, -0.105),
        (-0.040, 0.115),
    )
    for _, rr in rep_a.iterrows():
        px = abs(float(rr["caja_min_p10_usd"])) / 1000.0
        py = float(rr["neto12_medio_usd"]) / 1000.0
        lbl = str(rr["config_id"]).split("_", 1)[0]
        tx, ty = px + 0.035 * span_x, py + 0.045 * span_y
        for ox, oy in offs:
            cx, cy = px + ox * span_x, py + oy * span_y
            if all(abs(cx - ux) > 0.075 * span_x or abs(cy - uy) > 0.068 * span_y for ux, uy in puestos):
                tx, ty = cx, cy
                break
        puestos.append((tx, ty))
        ax2.annotate(lbl, xy=(px, py), xytext=(tx, ty), color="#e6eef2", fontsize=7.5, fontweight="bold",
                     arrowprops=dict(arrowstyle="-", color="#7d8f96", lw=0.6))
    ax2.margins(0.10)
    ax2.set_xlabel("|Capital requerido p10| (miles USD)", color="#d0dce2")
    ax2.set_ylabel("Caja neta media 12m (miles USD)", color="#d0dce2")
    ax2.set_title("Frontera Integrada LucidFlex (color = P(neto 12m > 0)%)", color="#edf4f7", fontsize=10.3)
    cb = fig1.colorbar(sc, ax=ax2, fraction=0.04, pad=0.02)
    cb.set_label("P(neto 12m > 0) %", color="#d0dce2", fontsize=8)
    cb.ax.tick_params(colors="#b8c6cc")
    fig1.tight_layout()
    p1 = OUT_DIR / "deploy_etapaA_integracion_y_colisiones.png"
    fig1.savefig(p1, dpi=150, facecolor=fig1.get_facecolor())
    plt.close(fig1)
    rutas["etapa_a"] = p1

    # PNG 2: Etapa B — Calibracion K30 M1 vs Ticks + R/mes en A5_HOLDOUT y TERMINAL
    fig2, (bx1, bx2) = plt.subplots(1, 2, figsize=(17.2, 7.2), facecolor="#0d1316")
    for ax in (bx1, bx2):
        _est(ax)

    cal_m = df_cal[df_cal["modulo"] != "CARTERA_P_OPT_SF_v2"].copy()
    ym = np.arange(len(cal_m))
    bx1.barh(ym - 0.18, cal_m["R_neto_m1"].fillna(0.0), height=0.33, color="#3baeb8", label="M1 Causal NQ")
    bx1.barh(ym + 0.18, cal_m["R_neto_ticks"].fillna(0.0), height=0.33, color="#f0c954", label="Ticks Reales K30")
    for yi, (_, rr) in enumerate(cal_m.iterrows()):
        bx1.text(max(float(rr["R_neto_m1"]), float(rr["R_neto_ticks"]), 0.0) + 0.012, yi,
                 f"corr={rr['corr_sesion']:.2f} | Cal={rr['calibra_k30']} | >10s={rr['pct_gan_gt10s']:.0f}%",
                 va="center", color="#dce5ea", fontsize=7.2)
    bx1.axvline(0.0, color="#c47068", linewidth=0.9, linestyle="--")
    bx1.set_yticks(ym)
    bx1.set_yticklabels(cal_m["modulo"], fontsize=7.8)
    bx1.set_xlim(min(-0.08, float(cal_m[["R_neto_m1", "R_neto_ticks"]].min().min()) - 0.03),
                max(0.25, float(cal_m[["R_neto_m1", "R_neto_ticks"]].max().max()) + 0.30))
    bx1.set_xlabel("R neto promedio por operacion", color="#d0dce2")
    bx1.set_title("Etapa B (K30): Paridad M1 vs Ticks Reales (291 sesiones Kaggle)", color="#edf4f7", fontsize=10.3)
    bx1.legend(loc="lower right", frameon=True, facecolor="#11191c", edgecolor="#2a373d", labelcolor="#dce5ea", fontsize=8)

    ho_mods = pd.DataFrame(ho_res["a5_holdout"]["modulos"])
    yh = np.arange(len(ho_mods))
    cols_h = ["#2ca693" if v > 0 else "#c47068" for v in ho_mods["R_por_mes"]]
    bx2.barh(yh, ho_mods["R_por_mes"], color=cols_h, height=0.58, alpha=0.90)
    for yi, (_, rr) in enumerate(ho_mods.iterrows()):
        bx2.text(max(float(rr["R_por_mes"]), 0.0) + 0.08, yi,
                 f"n={int(rr['n'])} R={rr['R_neto_mini']:+.3f} Cal={rr['calmar']:.2f}",
                 va="center", color="#dce5ea", fontsize=7.3)
    bx2.axvline(0.0, color="#c47068", linewidth=0.9, linestyle="--")
    bx2.set_yticks(yh)
    bx2.set_yticklabels(ho_mods["modulo"], fontsize=7.8)
    bx2.set_xlim(min(-0.5, float(ho_mods["R_por_mes"].min()) - 0.3), max(2.5, float(ho_mods["R_por_mes"].max()) + 1.5))
    bx2.set_xlabel("Expectativa mensual (R/mes en A5_HOLDOUT 2020-2026)", color="#d0dce2")
    bx2.set_title(f"Confirmacion Congelada A5_HOLDOUT (Cartera P_OPT_SF_v2: +{ho_res['a5_holdout']['cartera']['R_mes']:.2f} R/mes, Calmar {ho_res['a5_holdout']['cartera']['calmar']:.2f})",
                  color="#edf4f7", fontsize=9.8)
    fig2.tight_layout()
    p2 = OUT_DIR / "deploy_etapaB_calibracion_ticks_y_holdout.png"
    fig2.savefig(p2, dpi=150, facecolor=fig2.get_facecolor())
    plt.close(fig2)
    rutas["etapa_b"] = p2

    # PNG 3: Etapa C — Comparativa 16 Prop Firms y Frontera Multi-Firma Sincronizada (REP & A5_HOLDOUT 60%)
    fig3, (cx1, cx2) = plt.subplots(1, 2, figsize=(17.6, 7.8), facecolor="#0d1316")
    for ax in (cx1, cx2):
        _est(ax)

    mp_rep = df_mp[(df_mp["particion"] == "REP") & (df_mp["regimen_media"] == "contraida_60")].sort_values("neto12_medio_usd", ascending=True)
    yc = np.arange(len(mp_rep))
    mp_ho = df_mp[(df_mp["particion"] == "A5_HOLDOUT") & (df_mp["regimen_media"] == "contraida_60")].set_index("config_id")
    cx1.barh(yc - 0.17, mp_rep["neto12_medio_usd"] / 1000.0, height=0.33, color="#3baeb8", label="REP (60%)")
    cx1.barh(yc + 0.17, [float(mp_ho.loc[cid, "neto12_medio_usd"]) / 1000.0 for cid in mp_rep["config_id"]], height=0.33, color="#2ca693", label="A5_HOLDOUT (60%)")
    cx1.axvline(0.0, color="#c47068", linewidth=0.9, linestyle="--")
    cx1.set_yticks(yc)
    cx1.set_yticklabels(mp_rep["config_id"], fontsize=7.3)
    cx1.set_xlabel("Caja neta media 12m (miles USD, contraida 60%)", color="#d0dce2")
    cx1.set_title("Etapa C: Comparativa Multi-Prop Firm (16 planes aptos NT8)", color="#edf4f7", fontsize=10.3)
    cx1.legend(loc="lower right", frameon=True, facecolor="#11191c", edgecolor="#2a373d", labelcolor="#dce5ea", fontsize=8)

    arq_sub = df_arq[df_arq["regimen_media"] == "contraida_60"].copy()
    short_tag = {"REP": "REP", "A5_HOLDOUT": "HO"}
    for part_n, col_m, mk_s in (("REP", "#3baeb8", "o"), ("A5_HOLDOUT", "#2ca693", "s")):
        sa = arq_sub[arq_sub["particion"] == part_n]
        xr_a = np.abs(sa["caja_min_p10_usd"].to_numpy(float)) / 1000.0
        yr_a = sa["neto12_medio_usd"].to_numpy(float) / 1000.0
        cx2.scatter(xr_a, yr_a, s=np.clip(sa["retiros_12m"] * 12.0, 70, 520), color=col_m, marker=mk_s, alpha=0.88, edgecolors="#e6eef2", label=part_n)
        for px, py, nm in zip(xr_a, yr_a, sa["arquitectura"]):
            cx2.annotate(f"{nm.split('_')[0]} ({short_tag.get(part_n, part_n[:3])})", xy=(px, py), xytext=(px + 1.2, py + 1.2), color="#e6eef2", fontsize=7.3)
    # Anadir LucidFlex 150K solo como referencia en cx2
    lf_r = mp_rep[mp_rep["config_id"] == "MP_LucidFlex_150K_promo"]
    if not lf_r.empty:
        cx2.scatter(abs(float(lf_r["caja_min_p10_usd"].iloc[0])) / 1000.0, float(lf_r["neto12_medio_usd"].iloc[0]) / 1000.0,
                    s=140, color="#f0c954", marker="*", edgecolors="#ffffff", label="Solo LucidFlex 150K (REP)")
    cx2.margins(0.14)
    cx2.set_xlabel("|Capital requerido conjunto p10| (miles USD, trayectos sincronizados)", color="#d0dce2")
    cx2.set_ylabel("Caja neta conjunta 12m (miles USD)", color="#d0dce2")
    cx2.set_title("Arquitecturas Multi-Firma Sincronizadas (contraida 60%)", color="#edf4f7", fontsize=10.3)
    cx2.legend(loc="upper left", frameon=True, facecolor="#11191c", edgecolor="#2a373d", labelcolor="#dce5ea", fontsize=8)
    fig3.tight_layout()
    p3 = OUT_DIR / "deploy_etapaC_multiprop_frontera.png"
    fig3.savefig(p3, dpi=150, facecolor=fig3.get_facecolor())
    plt.close(fig3)
    rutas["etapa_c"] = p3

    if ARTIFACTS_DIR.exists():
        for sp_p in rutas.values():
            shutil.copy2(sp_p, ARTIFACTS_DIR / sp_p.name)
    return rutas


def ejecutar_todo(etapa: str = "todo", workers: int = 2, m1_dir: Path | None = None) -> dict[str, Any]:
    """Orquestador principal de Etapa A -> Etapa B (K30 + Holdout) -> Etapa C -> Graficos."""
    asegurar_compuerta_deploy()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fric_nq, fric_mnq = BASE.friccion_instrumento_puntos("NQ", prereg_rel=PREREG_REL, micro_equiv=BASE.MICRO_EQUIV)
    assert fric_mnq is not None

    if etapa == "graficos":
        df_a = pd.read_csv(OUT_DIR / "etapaA_integracion_lucidflex.csv")
        df_cal = pd.read_csv(OUT_DIR / "etapaB_calibracion_ticks_k30.csv")
        df_mp = pd.read_csv(OUT_DIR / "etapaC_multiprop_comparativa.csv")
        df_arq = pd.read_csv(OUT_DIR / "etapaC_arquitecturas_multifirma.csv")
        res = json.loads((OUT_DIR / "resumen_deploy_multiprop.json").read_text(encoding="utf-8"))
        rutas = graficar_despliegue(df_a, res["colisiones"]["REP"], df_cal, res["holdout"], df_mp, df_arq)
        return {"graficos": rutas}

    fechas_nq = IT2._cargar_fechas_a5_inst("NQ", m1_dir=m1_dir)
    ops_all, _, _, _, pre_meta = construir_ops_todos_modulos_pre(m1_dir=m1_dir, workers=workers)
    meta_v2 = ensamblar_cartera_v2(ops_all, fechas_nq["DESC"], fric_nq)
    print("\n=== PARIDAD SOMEOD & EVALUACION W TRAIL ===", json.dumps({
        "paridad_someod": pre_meta["paridad_someod"],
        "w_elegido": meta_v2["w_elegido"],
        "w_pesos": meta_v2["w_map"],
    }, indent=2))

    res_a = correr_etapa_a(ops_all, meta_v2, fechas_nq, fric_nq, fric_mnq)
    print("\n=== ETAPA A: 3 PLANOS LUCIDFLEX CONGELADOS ANTES DE HOLDOUT ===")
    for p in res_a["planes_congelados"]:
        print(" ", p["perfil_final"], "->", p["config_id"], p["palanca"])
    if etapa == "etapa_a":
        return {"pre_meta": pre_meta, "meta_v2": meta_v2, **res_a}

    df_cal, _, cal_meta = calibrar_m1_vs_ticks_nq(
        ops_all, list(meta_v2["miembros"]), dict(meta_v2["w_map"]), fric_nq, fric_mnq
    )
    df_cal.to_csv(OUT_DIR / "etapaB_calibracion_ticks_k30.csv", index=False)
    print("\n=== ETAPA B1: CALIBRACION TICKS K30 ===")
    print(df_cal[["modulo", "comunes", "n_trades", "R_neto_m1", "R_neto_ticks", "corr_sesion", "calibra_k30", "pct_gan_gt10s"]].to_string(index=False))

    ho_res = confirmar_holdout_congelado(
        list(meta_v2["miembros"]), dict(meta_v2["w_map"]), res_a["planes_congelados"], fric_nq, fric_mnq,
        ops_all_pre=ops_all, m1_dir=m1_dir,
    )
    print("\n=== ETAPA B2: A5_HOLDOUT & TERMINAL ===")
    print("A5_HOLDOUT cartera:", ho_res["a5_holdout"]["cartera"])
    print("TERMINAL cartera:", ho_res["terminal"]["cartera"], "| Sellado ticks:", ho_res["terminal"]["sellado_ticks"])
    if etapa == "etapa_b":
        return {"df_cal": df_cal, "cal_meta": cal_meta, "ho_res": ho_res}

    res_c = correr_etapa_c(ops_all, list(meta_v2["miembros"]), dict(meta_v2["w_map"]), fechas_nq, fric_nq, fric_mnq)
    print("\n=== ETAPA C: TOP MULTIPROP (REP contr_60) ===")
    sub_c = res_c["df_mp"][(res_c["df_mp"]["particion"] == "REP") & (res_c["df_mp"]["regimen_media"] == "contraida_60")].sort_values("neto12_medio_usd", ascending=False)
    print(sub_c[["config_id", "fee_sim_usd", "neto12_medio_usd", "retiros_12m", "p_1ret12_pct", "caja_min_p10_usd", "ratio_net12_p10"]].to_string(index=False))

    resumen = {
        "paridad_someod": pre_meta["paridad_someod"],
        "eval_w_trail": meta_v2["eval_w_trail"],
        "promovio_w_trail": meta_v2["promovio_w_trail"],
        "w_elegido": meta_v2["w_elegido"],
        "miembros_p_opt_sf_v2": meta_v2["miembros"],
        "pesos_w5": meta_v2["w_map"],
        "pesos_todos": meta_v2["pesos_todos"],
        "ev_cartera_desc_rep": res_a["ev_cartera"],
        "colisiones": res_a["colisiones"],
        "planes_congelados": res_a["planes_congelados"],
        "calibracion_k30_meta": cal_meta,
        "calibracion_k30": df_cal.to_dict(orient="records"),
        "holdout": ho_res,
        "excluidas_algo_policy": res_c["excluidas"],
    }
    rutas = graficar_despliegue(res_a["df_etapa_a"], res_a["colisiones"]["REP"], df_cal, ho_res, res_c["df_mp"], res_c["df_arq"])
    resumen["graficos"] = {k: str(v.relative_to(ROOT).as_posix()) for k, v in rutas.items()}
    (OUT_DIR / "resumen_deploy_multiprop.json").write_text(json.dumps(resumen, indent=2, default=str), encoding="utf-8")
    return resumen


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Despliegue P_OPT_SF_v2: LucidFlex, K30 Ticks, Holdout y Multi-Prop.")
    ap.add_argument("etapa", nargs="?", default="todo", choices=("etapa_a", "etapa_b", "etapa_c", "graficos", "todo"))
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args(argv)
    ejecutar_todo(etapa=args.etapa, workers=args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

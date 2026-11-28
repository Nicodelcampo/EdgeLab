#!/usr/bin/env python3
"""Iteracion 4 FUNDEDSYNC: busqueda exhaustiva de factores de edge y optimizacion prop firm (LucidFlex).

Uso:
  python tools/fundedsync_prop_opt.py etapa1 [--workers 2]
  python tools/fundedsync_prop_opt.py etapa2 [--workers 2]
  python tools/fundedsync_prop_opt.py todo [--workers 2]
  python tools/fundedsync_prop_opt.py graficos
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

import numpy as np
import pandas as pd
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
import lucid_guia as LG
from edgelab import costos
from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS, a5_bloque
from edgelab.research.m1_intradia import leer_m1nt8
from edgelab.research.puerta_corrida import verificar_corrida
from registro_global import exigir_contada

PREREG_REL = "docs/research/fundedsync_prop_opt_20261122/PREREGISTRO.md"
OUT_DIR = ROOT / "docs/research/fundedsync_prop_opt_20261122"
SOM_CSV = ROOT / "docs/research/m1_largo_20261117/SOM_OPS_NQ.csv.gz"
FRK_CSV = ROOT / "docs/research/m1_largo_20261117/FRANKLIN_OPS_NQ.csv.gz"
ARTIFACTS_DIR = BASE.ARTIFACTS_DIR

CORE6_ANCLAS_E1 = {
    "V": "V_nm30_maeATR30",
    "R": "R_osc30_end660_ATR50",
    "Z": "Z_b15_e20_eff45_ATR50",
    "W": "W_base_slope_ATR25",
    "N": "N_d5_fbTrue_ATR25",
    "T": "T_stop100_calTrue",
}


def asegurar_compuerta_iter4() -> None:
    """Verifica K51 y compuerta L1..L4 para PREREGISTRO de iteracion 4."""
    exigir_contada(PREREG_REL)
    rep = verificar_corrida(
        prereg=PREREG_REL,
        familia="FUNDEDSYNC",
        exigir_contada=True,
        verificar_estado=True,
        root=ROOT,
    )
    if not rep["ok"]:
        raise SystemExit("puerta_corrida bloqueo iter4: " + "; ".join(rep["errores"]))


def _idx_utc_ns(dt_idx: pd.DatetimeIndex) -> np.ndarray:
    """Devuelve int64 en nanosegundos UTC asegurando unidad ns (compatible pandas [us]/[ns])."""
    if hasattr(dt_idx, "as_unit"):
        dt_idx = dt_idx.as_unit("ns")
    return np.ascontiguousarray(dt_idx.asi8, dtype=np.int64)


def _col_a_ns_y_dt(col: pd.Series) -> tuple[np.ndarray, pd.Series]:
    """Convierte serie timestamp (int64 ns o datetime/str) en `(ns_utc, Series[datetime64[ns, UTC]])`."""
    if pd.api.types.is_integer_dtype(col.dtype):
        ns = np.ascontiguousarray(col.to_numpy(dtype=np.int64))
        dt = pd.Series(pd.to_datetime(ns, unit="ns", utc=True), index=col.index)
        return ns, dt
    dt_idx = pd.DatetimeIndex(pd.to_datetime(col, utc=True))
    ns = _idx_utc_ns(dt_idx)
    return ns, pd.Series(pd.to_datetime(ns, unit="ns", utc=True), index=col.index)


def cargar_m1_arrays_nq(m1_dir: Path | None = None, desde: str = "2008-01-01") -> dict[str, np.ndarray]:
    """Carga arrays contiguos M1 de NQ (< HOLDOUT-A4) indexados por timestamp UTC de apertura de vela."""
    d_ny = leer_m1nt8(BASE._resolver_parquet("NQ", m1_dir=m1_dir))
    d_ny = d_ny[d_ny.index >= desde]
    ts_utc = d_ny.index.tz_localize("America/New_York").tz_convert("UTC")
    ts_ns = _idx_utc_ns(ts_utc)
    ok = ts_ns < HOLDOUT_APERTURA_UTC_NS
    out = {
        "ts_ns": np.ascontiguousarray(ts_ns[ok], dtype=np.int64),
        "o": np.ascontiguousarray(d_ny["o"].to_numpy(dtype=np.float64)[ok]),
        "h": np.ascontiguousarray(d_ny["h"].to_numpy(dtype=np.float64)[ok]),
        "l": np.ascontiguousarray(d_ny["l"].to_numpy(dtype=np.float64)[ok]),
        "c": np.ascontiguousarray(d_ny["c"].to_numpy(dtype=np.float64)[ok]),
    }
    del d_ny, ts_utc
    gc.collect()
    return out


@njit(cache=False)
def _evaluar_overlay_m1_numba(
    ts_ns: np.ndarray,
    m1_o: np.ndarray,
    m1_h: np.ndarray,
    m1_l: np.ndarray,
    m1_c: np.ndarray,
    en_ns: np.ndarray,
    ex_ns: np.ndarray,
    side_arr: np.ndarray,
    en_p_arr: np.ndarray,
    ex_p_arr: np.ndarray,
    sl_pts_arr: np.ndarray,
    tp_pts_arr: np.ndarray,
    is_mkt_open: np.ndarray,
    be_trig_r: float,
    t1_trig_r: float,
    t1_lock_r: float,
    t2_trig_r: float,
    t2_lock_r: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Evalua barra por barra M1 overlay causal (SL, TP, BE/Trail en i+1) con K40 y stop-first."""
    n_tr = len(en_ns)
    n_m1 = len(ts_ns)
    out_pnl = np.empty(n_tr, dtype=np.float64)
    out_mae = np.empty(n_tr, dtype=np.float64)
    out_mfe = np.empty(n_tr, dtype=np.float64)
    out_ex_ns = np.empty(n_tr, dtype=np.int64)

    for k in range(n_tr):
        sd = int(side_arr[k])
        ep = float(en_p_arr[k])
        xp_orig = float(ex_p_arr[k])
        sl_d = float(sl_pts_arr[k])
        tp_d = float(tp_pts_arr[k])
        t0 = int(en_ns[k])
        t1 = int(ex_ns[k])

        if n_m1 == 0 or sl_d <= 0.0:
            out_pnl[k] = (xp_orig - ep) * sd
            out_mae[k] = 0.0
            out_mfe[k] = max(0.0, out_pnl[k])
            out_ex_ns[k] = t1
            continue

        i0 = int(np.searchsorted(ts_ns, t0, side="left"))
        i1 = int(np.searchsorted(ts_ns, t1, side="right")) - 1
        if i0 >= n_m1 or i1 < i0:
            out_pnl[k] = (xp_orig - ep) * sd
            out_mae[k] = 0.0
            out_mfe[k] = max(0.0, out_pnl[k])
            out_ex_ns[k] = t1
            continue

        stop_lvl = ep - sl_d if sd == 1 else ep + sl_d
        tp_lvl = (ep + tp_d) if sd == 1 else (ep - tp_d)
        stop_active = stop_lvl
        stop_on = sl_d < 1e8

        last_loop = i1 - 1 if (is_mkt_open[k] and i1 > i0) else i1
        exited = False
        pnl = 0.0
        mae = 0.0
        mfe = 0.0
        ex_final_ns = t1

        for i in range(i0, last_loop + 1):
            oi = m1_o[i]
            hi = m1_h[i]
            li = m1_l[i]

            if stop_on and i > i0:
                if (sd == 1 and oi <= stop_active) or (sd == -1 and oi >= stop_active):
                    adv_now = (ep - oi) if sd == 1 else (oi - ep)
                    if adv_now > mae:
                        mae = adv_now
                    pnl = (oi - ep) * sd
                    ex_final_ns = ts_ns[i]
                    exited = True
                    break

            if stop_on:
                if (sd == 1 and li <= stop_active) or (sd == -1 and hi >= stop_active):
                    adv_now = (ep - stop_active) if sd == 1 else (stop_active - ep)
                    if adv_now > mae:
                        mae = adv_now
                    pnl = (stop_active - ep) * sd
                    ex_final_ns = ts_ns[i]
                    exited = True
                    break

            bar_adv = (ep - li) if sd == 1 else (hi - ep)
            if bar_adv > mae:
                mae = bar_adv

            if tp_d > 0.0:
                if (sd == 1 and hi >= tp_lvl) or (sd == -1 and li <= tp_lvl):
                    if tp_d > mfe:
                        mfe = tp_d
                    pnl = tp_d
                    ex_final_ns = ts_ns[i]
                    exited = True
                    break

            bar_fav = (hi - ep) if sd == 1 else (ep - li)
            if bar_fav > mfe:
                mfe = bar_fav

            # Regla causal estricta: BE / trailing se actualiza al cierre de i para regir desde i + 1
            if be_trig_r > 0.0 and bar_fav >= be_trig_r * sl_d:
                if sd == 1 and ep > stop_active:
                    stop_active = ep
                elif sd == -1 and ep < stop_active:
                    stop_active = ep
            if t1_trig_r > 0.0 and bar_fav >= t1_trig_r * sl_d:
                cand1 = ep + t1_lock_r * sl_d if sd == 1 else ep - t1_lock_r * sl_d
                if sd == 1 and cand1 > stop_active:
                    stop_active = cand1
                elif sd == -1 and cand1 < stop_active:
                    stop_active = cand1
            if t2_trig_r > 0.0 and bar_fav >= t2_trig_r * sl_d:
                cand2 = ep + t2_lock_r * sl_d if sd == 1 else ep - t2_lock_r * sl_d
                if sd == 1 and cand2 > stop_active:
                    stop_active = cand2
                elif sd == -1 and cand2 < stop_active:
                    stop_active = cand2

        if not exited:
            if is_mkt_open[k] and i1 > i0 and stop_on:
                oi1 = m1_o[i1]
                if (sd == 1 and oi1 <= stop_active) or (sd == -1 and oi1 >= stop_active):
                    pnl = (oi1 - ep) * sd
                    adv_now = max(0.0, -pnl)
                    if adv_now > mae:
                        mae = adv_now
                    ex_final_ns = ts_ns[i1]
                else:
                    pnl = (xp_orig - ep) * sd
            else:
                pnl = (xp_orig - ep) * sd
            if pnl > mfe:
                mfe = pnl
            if -pnl > mae:
                mae = -pnl

        out_pnl[k] = pnl
        out_mae[k] = max(0.0, mae)
        out_mfe[k] = max(0.0, mfe)
        out_ex_ns[k] = ex_final_ns

    return out_pnl, out_mae, out_mfe, out_ex_ns


def aplicar_overlay_m1_causal(
    df_trades: pd.DataFrame,
    modulo: str,
    atr_ses: pd.Series,
    orb_raw: pd.Series,
    pv_base: float,
    m1_arrays: Mapping[str, np.ndarray],
    *,
    sl_atr_k: float | None = None,
    tp_atr_k: float | None = None,
    be_trigger_r: float | None = None,
    trail_tiers: tuple[tuple[float, float], ...] | None = None,
    tp_r: float | None = None,
    stop_orb_mult: float = 1.25,
    stop_min_pts: float = 2.0,
    stop_max_pts: float = 100.0,
) -> pd.DataFrame:
    """Evalua trades cacheados en M1 NQ con riesgos y salidas causales (BE/Trail/TP/SL ATR20)."""
    if df_trades is None or df_trades.empty:
        out = IT2._empty_ops_enr()
        out["mae_pts"] = pd.Series(dtype="float64")
        out["mfe_pts"] = pd.Series(dtype="float64")
        return out

    df = df_trades.copy()
    en_ns_all, en_dt = _col_a_ns_y_dt(df["entry_time_utc"])
    ex_ns_all, ex_dt = _col_a_ns_y_dt(df["exit_time_utc"])
    # Filtrado duro anti-holdout A4 (< 2026-10-01) y A5 (solo DESC / REP)
    ok_a4 = en_ns_all < HOLDOUT_APERTURA_UTC_NS
    if not ok_a4.any():
        return aplicar_overlay_m1_causal(df.iloc[0:0], modulo, atr_ses, orb_raw, pv_base, m1_arrays)

    df = df.loc[ok_a4].reset_index(drop=True)
    en_dt = en_dt.loc[ok_a4].reset_index(drop=True)
    ex_dt = ex_dt.loc[ok_a4].reset_index(drop=True)
    en_ns = en_ns_all[ok_a4]
    ex_ns = ex_ns_all[ok_a4]

    en_ny = en_dt.dt.tz_convert("America/New_York").dt.tz_localize(None)
    ses_dt = (en_ny + pd.Timedelta(hours=6)).dt.normalize()
    fecha_int = ses_dt.dt.strftime("%Y%m%d").astype(np.int64)
    a5_arr = pd.Series([a5_bloque(int(f)) for f in fecha_int], index=df.index)
    keep = a5_arr.isin(("DESC", "REP")).to_numpy()
    if not keep.any():
        return aplicar_overlay_m1_causal(df.iloc[0:0], modulo, atr_ses, orb_raw, pv_base, m1_arrays)

    df = df.loc[keep].reset_index(drop=True)
    ses_dt = ses_dt.loc[keep].reset_index(drop=True)
    fecha_int = fecha_int.loc[keep].reset_index(drop=True)
    a5_arr = a5_arr.loc[keep].reset_index(drop=True)

    en_ns = en_ns[keep]
    ex_ns = ex_ns[keep]
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
            sl_pts = np.where(bad_s, np.abs(df["pnl_pts"].to_numpy(dtype=np.float64)) / np.maximum(qty, 1.0), sl_pts)

    valid_r = np.isfinite(sl_pts) & (sl_pts > 0.0)
    if not valid_r.any():
        return aplicar_overlay_m1_causal(df.iloc[0:0], modulo, atr_ses, orb_raw, pv_base, m1_arrays)

    # Normalizar TP y tiers
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
    pnl_new, mae_new, mfe_new, ex_ns_new = _evaluar_overlay_m1_numba(
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

    keep_v = valid_r
    sl_f = sl_pts[keep_v]
    pnl_f = pnl_new[keep_v]
    mae_f = mae_new[keep_v]
    mfe_f = mfe_new[keep_v]
    en_f = en_ns[keep_v]
    ex_f = np.maximum(ex_ns_new[keep_v], en_f)
    fric_nq, fric_mnq = BASE.friccion_instrumento_puntos("NQ", prereg_rel=PREREG_REL, micro_equiv=BASE.MICRO_EQUIV)
    assert fric_mnq is not None

    return pd.DataFrame({
        "fecha_int": fecha_int.to_numpy()[keep_v],
        "mes": ses_dt.dt.strftime("%Y-%m").to_numpy()[keep_v],
        "a5": a5_arr.to_numpy()[keep_v],
        "en_ns": en_f,
        "ex_ns": ex_f,
        "dur_min": np.maximum((ex_f - en_f) / 60_000_000_000.0, 0.0),
        "pnl_pts": pnl_f,
        "mae_pts": mae_f,
        "mfe_pts": mfe_f,
        "riesgo_pts": sl_f,
        "R_bruto": pnl_f / sl_f,
        "R_neto_mini": (pnl_f - float(fric_nq)) / sl_f,
        "R_neto_micro": (pnl_f - float(fric_mnq)) / sl_f,
        "fric_R": float(fric_nq) / sl_f,
        "side": side[keep_v],
    }).reset_index(drop=True)


def cargar_ext_som_franklin(nombre: str) -> pd.DataFrame:
    """Carga operaciones externas confirmadas (`SOMEOD` o `FRANKLIN`) para NQ en A5 DESC/REP (< A4)."""
    fric_nq, fric_mnq = BASE.friccion_instrumento_puntos("NQ", prereg_rel=PREREG_REL, micro_equiv=BASE.MICRO_EQUIV)
    assert fric_mnq is not None

    if nombre == "SOMEOD":
        raw = pd.read_csv(SOM_CSV)
        raw = raw[(raw["celda"] == "eod") & (raw["fecha"].astype(int) >= 20080101) & (raw["fecha"].astype(int) < 20261001)].copy()
        entry_hhmm = "09:35:00"
        dur_min = np.maximum(pd.to_numeric(raw["horas"], errors="coerce").fillna(6.33).to_numpy(float) * 60.0, 1.0)
        side = np.ones(len(raw), dtype=np.int64)
    elif nombre == "FRANKLIN":
        raw = pd.read_csv(FRK_CSV)
        raw = raw[(raw["clave"] == "1000|rango|ninguno") & (raw["fecha"].astype(int) >= 20080101) & (raw["fecha"].astype(int) < 20261001)].copy()
        entry_hhmm = "10:00:00"
        mot = pd.to_numeric(raw["motivo"], errors="coerce").fillna(1).to_numpy(int)
        dur_min = np.where(mot == 3, 355.0, 60.0)
        side = pd.to_numeric(raw["lado"], errors="coerce").fillna(1).to_numpy(np.int64)
    else:
        raise ValueError(f"Señal externa desconocida: {nombre}")

    raw["a5"] = [a5_bloque(int(f)) for f in raw["fecha"].astype(int)]
    raw = raw[raw["a5"].isin(("DESC", "REP")) & (raw["riesgo"] > 0)].copy().reset_index(drop=True)
    if nombre == "SOMEOD":
        dur_min = np.maximum(pd.to_numeric(raw["horas"], errors="coerce").fillna(6.33).to_numpy(float) * 60.0, 1.0)
        side = np.ones(len(raw), dtype=np.int64)
    else:
        mot = pd.to_numeric(raw["motivo"], errors="coerce").fillna(1).to_numpy(int)
        dur_min = np.where(mot == 3, 355.0, 60.0)
        side = pd.to_numeric(raw["lado"], errors="coerce").fillna(1).to_numpy(np.int64)

    fechas_str = raw["fecha"].astype(int).astype(str)
    en_ny = pd.DatetimeIndex(pd.to_datetime(fechas_str + " " + entry_hhmm, format="%Y%m%d %H:%M:%S"))
    en_ns = _idx_utc_ns(en_ny.tz_localize("America/New_York").tz_convert("UTC"))
    ok_a4 = en_ns < HOLDOUT_APERTURA_UTC_NS
    raw = raw.loc[ok_a4].reset_index(drop=True)
    en_ns = en_ns[ok_a4]
    dur_min = dur_min[ok_a4]
    side = side[ok_a4]
    ex_ns = en_ns + (dur_min * 60_000_000_000.0).astype(np.int64)

    riesgo = raw["riesgo"].to_numpy(dtype=np.float64)
    bruto = raw["bruto"].to_numpy(dtype=np.float64)
    mae_pts = np.where(bruto < 0.0, np.minimum(riesgo, np.maximum(-bruto, 0.0)), 0.50 * riesgo)
    mfe_pts = np.where(bruto > 0.0, bruto, 0.0)

    return pd.DataFrame({
        "fecha_int": raw["fecha"].astype(np.int64).to_numpy(),
        "mes": (fechas_str.loc[ok_a4].str[:4] + "-" + fechas_str.loc[ok_a4].str[4:6]).to_numpy(),
        "a5": raw["a5"].to_numpy(),
        "en_ns": en_ns,
        "ex_ns": ex_ns,
        "dur_min": dur_min,
        "pnl_pts": bruto,
        "mae_pts": mae_pts,
        "mfe_pts": mfe_pts,
        "riesgo_pts": riesgo,
        "R_bruto": bruto / riesgo,
        "R_neto_mini": (bruto - float(fric_nq)) / riesgo,
        "R_neto_micro": (bruto - float(fric_mnq)) / riesgo,
        "fric_R": float(fric_nq) / riesgo,
        "side": side,
    })


def combinar_banda_z(ops_list: list[pd.DataFrame]) -> pd.DataFrame:
    """Combina K variantes vecinas de Z en un stream diversificado equivalente (`1/K` por celda)."""
    k = max(len(ops_list), 1)
    partes = []
    for df in ops_list:
        if df is not None and not df.empty:
            c = df.copy()
            for col in ("R_bruto", "R_neto_mini", "R_neto_micro", "pnl_pts", "mae_pts", "mfe_pts"):
                c[col] = c[col] / float(k)
            partes.append(c)
    if not partes:
        return ops_list[0].iloc[0:0].copy() if ops_list else IT2._empty_ops_enr()
    tot = pd.concat(partes, ignore_index=True)
    agg = tot.groupby(["fecha_int", "mes", "a5"], as_index=False).agg(
        en_ns=("en_ns", "min"),
        ex_ns=("ex_ns", "max"),
        dur_min=("dur_min", "mean"),
        pnl_pts=("pnl_pts", "sum"),
        mae_pts=("mae_pts", "sum"),
        mfe_pts=("mfe_pts", "sum"),
        riesgo_pts=("riesgo_pts", "median"),
        R_bruto=("R_bruto", "sum"),
        R_neto_mini=("R_neto_mini", "sum"),
        R_neto_micro=("R_neto_micro", "sum"),
        fric_R=("fric_R", "mean"),
        side=("side", "first"),
    )
    return agg.sort_values(["fecha_int", "en_ns"]).reset_index(drop=True)


def specs_etapa1_iter4() -> list[dict[str, Any]]:
    """Define las 44 variantes pre-registradas en 5 grillas para Etapa 1 (NQ DESC POST_2020)."""
    s: list[dict[str, Any]] = []

    def add(grilla: str, mod: str, var: str, params: dict[str, Any], ov: dict[str, Any], perillas: dict[str, str], ext: str | None = None) -> None:
        s.append({
            "grilla": grilla,
            "modulo": mod,
            "variante": var,
            "params": params,
            "overlay": ov,
            "perillas": perillas,
            "externa": ext,
        })

    # P1_V_ESCALA (10): eliminar topes USD 1400/2000 + ATR SL/TP + noise/hora
    nocap = {"noise_multiplier": 0.30, "profit_target_usd_per_contract": 99999.0, "stop_loss_usd_per_contract": 99999.0}
    for sl_k in (0.25, 0.30, 0.35):
        add("P1_V_ESCALA", "V", f"V_nm30_noCap_mae{int(sl_k*100)}", dict(nocap), {"sl_atr_k": sl_k}, {"eje": "noCap", "sl_tp": f"mae{int(sl_k*100)}"})
    for nm, sl_k, tp_k in ((0.30, 0.30, 0.30), (0.30, 0.30, 0.45), (0.35, 0.35, 0.50), (0.40, 0.40, 0.60)):
        add("P1_V_ESCALA", "V", f"V_nm{int(nm*100)}_atrSLTP_{int(sl_k*100)}_{int(tp_k*100)}",
            {"noise_multiplier": nm, "profit_target_usd_per_contract": 99999.0, "stop_loss_usd_per_contract": 99999.0},
            {"sl_atr_k": sl_k, "tp_atr_k": tp_k},
            {"eje": f"nm{int(nm*100)}_sltp", "sl_tp": f"{int(sl_k*100)}_{int(tp_k*100)}"})
    add("P1_V_ESCALA", "V", "V_nm30_noBlock_noCap_mae30", {**nocap, "block_entry_hour_enabled": False}, {"sl_atr_k": 0.30}, {"eje": "noBlock", "sl_tp": "mae30"})
    add("P1_V_ESCALA", "V", "V_nm25_noCap_mae30", {**nocap, "noise_multiplier": 0.25}, {"sl_atr_k": 0.30}, {"eje": "nm25", "sl_tp": "mae30"})
    add("P1_V_ESCALA", "V", "V_nm35_vwap3_noCap_mae30", {**nocap, "noise_multiplier": 0.35, "vwap_exit_bars": 3}, {"sl_atr_k": 0.30}, {"eje": "nm35_v3", "sl_tp": "mae30"})

    # P2_R_FRECUENCIA (9): 3 x 3 factorial en osc_atr_mult y entry_end_min_et
    for osc in (2.0, 2.5, 3.0):
        for end_m in (660, 720, 840):
            add("P2_R_FRECUENCIA", "R", f"R_osc{int(osc*10)}_end{end_m}_ATR50",
                {"osc_atr_mult": osc, "entry_end_min_et": end_m},
                {"sl_atr_k": 0.50},
                {"osc": str(osc), "end_et": str(end_m)})

    # P3_Z_BANDA (8): 7 celdas vecinas + 1 ensemble multi-configuracion Z_BANDA_6
    for bkt, ema, eff in ((15, 20, 45.0), (15, 20, 40.0), (15, 20, 35.0), (15, 20, 30.0), (10, 15, 35.0), (10, 20, 40.0), (20, 15, 35.0)):
        add("P3_Z_BANDA", "Z", f"Z_b{bkt}_e{ema}_eff{int(eff)}_ATR50",
            {"bucket_minutes": bkt, "ema_period": ema, "min_efficiency_pct": eff},
            {"sl_atr_k": 0.50},
            {"bkt_ema": f"{bkt}_{ema}", "eff": str(int(eff))})
    add("P3_Z_BANDA", "Z", "Z_BANDA_6_ATR50", {}, {"banda_miembros": [
        "Z_b15_e20_eff45_ATR50", "Z_b15_e20_eff40_ATR50", "Z_b15_e20_eff35_ATR50",
        "Z_b10_e15_eff35_ATR50", "Z_b10_e20_eff40_ATR50", "Z_b20_e15_eff35_ATR50",
    ]}, {"bkt_ema": "banda6", "eff": "35+"})

    # P4_WN_SALIDAS (11): salidas causales M1 en W (7) + variantes estructurales en N (4)
    w_slp = {"exit_on_vwap_cross": False, "use_vwap_slope_filter": True}
    add("P4_WN_SALIDAS", "W", "W_base_slope_ATR25", dict(w_slp), {"sl_atr_k": 0.25}, {"mod": "W", "regla": "base"})
    add("P4_WN_SALIDAS", "W", "W_slope_BE_10R_ATR25", dict(w_slp), {"sl_atr_k": 0.25, "be_trigger_r": 1.0}, {"mod": "W", "regla": "BE_1.0R"})
    add("P4_WN_SALIDAS", "W", "W_slope_BE_15R_ATR25", dict(w_slp), {"sl_atr_k": 0.25, "be_trigger_r": 1.5}, {"mod": "W", "regla": "BE_1.5R"})
    add("P4_WN_SALIDAS", "W", "W_slope_BE_20R_ATR25", dict(w_slp), {"sl_atr_k": 0.25, "be_trigger_r": 2.0}, {"mod": "W", "regla": "BE_2.0R"})
    add("P4_WN_SALIDAS", "W", "W_slope_trail_15_50_ATR25", dict(w_slp), {"sl_atr_k": 0.25, "trail_tiers": ((1.5, 0.5), (2.5, 1.5))}, {"mod": "W", "regla": "trail"})
    add("P4_WN_SALIDAS", "W", "W_slope_TP_25R_ATR25", dict(w_slp), {"sl_atr_k": 0.25, "tp_r": 2.5}, {"mod": "W", "regla": "TP_2.5R"})
    add("P4_WN_SALIDAS", "W", "W_slope_allowReFalse_ATR25", {**w_slp, "allow_reentries": False}, {"sl_atr_k": 0.25}, {"mod": "W", "regla": "noRe"})

    add("P4_WN_SALIDAS", "N", "N_d5_fbTrue_ATR25", {}, {"sl_atr_k": 0.25}, {"mod": "N", "regla": "d5_fbT"})
    add("P4_WN_SALIDAS", "N", "N_d5_fbFalse_ATR25", {"use_failed_breakout_exit": False}, {"sl_atr_k": 0.25}, {"mod": "N", "regla": "d5_fbF"})
    add("P4_WN_SALIDAS", "N", "N_d3_fbTrue_ATR25", {"num_days": 3}, {"sl_atr_k": 0.25}, {"mod": "N", "regla": "d3_fbT"})
    add("P4_WN_SALIDAS", "N", "N_d10_fbTrue_ATR25", {"num_days": 10}, {"sl_atr_k": 0.25}, {"mod": "N", "regla": "d10_fbT"})

    # P5_T_LIVE_Y_EXT (6): T live sin fechas fijas + BE/TP + externas confirmadas SOMEOD y FRANKLIN
    add("P5_T_LIVE_Y_EXT", "T", "T_stop100_calTrue", {"use_exclusion_calendars": True}, {"stop_orb_mult": 1.0, "stop_min_pts": 2.0, "stop_max_pts": 100.0}, {"mod": "T", "regla": "calT"})
    add("P5_T_LIVE_Y_EXT", "T", "T_stop100_live_calFalse", {"use_exclusion_calendars": False}, {"stop_orb_mult": 1.0, "stop_min_pts": 2.0, "stop_max_pts": 100.0}, {"mod": "T", "regla": "calF"})
    add("P5_T_LIVE_Y_EXT", "T", "T_stop100_BE15R_calFalse", {"use_exclusion_calendars": False}, {"stop_orb_mult": 1.0, "stop_min_pts": 2.0, "stop_max_pts": 100.0, "be_trigger_r": 1.5}, {"mod": "T", "regla": "calF_BE15"})
    add("P5_T_LIVE_Y_EXT", "T", "T_stop100_TP25R_calFalse", {"use_exclusion_calendars": False}, {"stop_orb_mult": 1.0, "stop_min_pts": 2.0, "stop_max_pts": 100.0, "tp_r": 2.5}, {"mod": "T", "regla": "calF_TP25"})
    add("P5_T_LIVE_Y_EXT", "SOM", "SOMEOD_ext_NQ", {}, {}, {"mod": "EXT", "regla": "SOMEOD"}, ext="SOMEOD")
    add("P5_T_LIVE_Y_EXT", "FRK", "FRANKLIN_ext_NQ", {}, {}, {"mod": "EXT", "regla": "FRANKLIN"}, ext="FRANKLIN")
    return s


def _evaluar_ops_variante(
    sp: Mapping[str, Any],
    ops_all: pd.DataFrame,
    start_nq: int,
) -> dict[str, Any]:
    """Construye fila completa de metricas DESC (POST_2020, FULL_2008, POST_2021) para una variante."""
    ops_d20 = ops_all[(ops_all["a5"] == "DESC") & (ops_all["fecha_int"] >= 20200101)].copy()
    ops_d21 = ops_all[(ops_all["a5"] == "DESC") & (ops_all["fecha_int"] >= 20210101)].copy()
    ops_d08 = ops_all[(ops_all["a5"] == "DESC")].copy()

    m_20 = BASE._meses_activos_a5(20200101, 20260930, "DESC")
    m_21 = BASE._meses_activos_a5(20210101, 20260930, "DESC")
    m_08 = BASE._meses_activos_a5(start_nq, 20260930, "DESC")

    s20 = BASE.resumir_serie_r(ops_d20, col_r="R_neto_mini", bootstrap_reps=1200, seed=42, meses_totales=m_20)
    s21 = BASE.resumir_serie_r(ops_d21, col_r="R_neto_mini", bootstrap_reps=0, seed=42, meses_totales=m_21)
    s08 = BASE.resumir_serie_r(ops_d08, col_r="R_neto_mini", bootstrap_reps=800, seed=43, meses_totales=m_08)
    dd20 = IT2._metricas_dd_r(ops_d20, m_20)
    dur_med = float(ops_d20["dur_min"].median()) if len(ops_d20) else 0.0
    if len(ops_d20) >= 6 and int(ops_d20["mes"].nunique()) > 3:
        ep20 = BASE.DG.episodios(ops_d20[["R_neto_mini", "mes"]], valor="R_neto_mini", mes="mes", k=3)
        sin_3_mej = ep20.get("media_sin_mejores")
    else:
        sin_3_mej = float("nan")

    return {
        "grilla": sp["grilla"],
        "modulo": sp["modulo"],
        "variante": sp["variante"],
        "n_2008": int(s08["n"]),
        "R_neto_2008": float(s08["R_neto_mini"]),
        "t_ses_2008": float(s08["t_ses"]),
        "p_boot_2008": float(s08["p_boot"]),
        "n_2020": int(s20["n"]),
        "ops_mes_2020": round(float(s20["n"]) / max(m_20, 1), 2),
        "R_neto_2020": float(s20["R_neto_mini"]),
        "R_micro_2020": float(s20["R_neto_micro"]),
        "R_mes_2020": float(s20["R_por_mes"]),
        "t_ses_2020": float(s20["t_ses"]),
        "dd_R": float(dd20["dd_R"]),
        "calmar": float(dd20["calmar"]),
        "worst_day_R": float(dd20["worst_day_R"]),
        "dur_med_min": round(dur_med, 1),
        "med_fric_R_2020": float(s20["med_fric_R"]),
        "R_neto_2021": float(s21["R_neto_mini"]),
        "sin_3_mej_2020": float(sin_3_mej) if sin_3_mej is not None else float("nan"),
        "media_2020_pos_sin_top3": bool(sin_3_mej is not None and np.isfinite(sin_3_mej) and float(sin_3_mej) > 0.0),
    }


def _correr_etapa1(
    atr_nq: pd.Series,
    orb_raw_nq: pd.Series,
    pv_nq: float,
    start_nq: int,
    fechas_desc_20: list[int],
    m1_arrays: Mapping[str, np.ndarray],
    *,
    workers: int = 2,
    m1_dir: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, pd.DataFrame]]:
    """Ejecuta las 44 pruebas de Etapa 1 en NQ DESC + K55/K56 + B=5000 permutaciones + confirmacion REP congelada."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    specs = specs_etapa1_iter4()

    jobs_nq: list[tuple[str, str, dict[str, Any]]] = []
    seen_k: set[str] = set()
    for sp in specs:
        if sp["externa"] or sp["overlay"].get("banda_miembros"):
            continue
        cn = BASE._cache_key("NQ", sp["modulo"], sp["params"])
        if cn not in seen_k:
            seen_k.add(cn)
            jobs_nq.append((cn, sp["modulo"], sp["params"]))
    # Asegurar tambien V_nm30_maeATR30 ancla exacta Iter 3 para comparar
    v_anc_params = {"noise_multiplier": 0.30}
    cn_v_anc = BASE._cache_key("NQ", "V", v_anc_params)
    if cn_v_anc not in seen_k:
        seen_k.add(cn_v_anc)
        jobs_nq.append((cn_v_anc, "V", v_anc_params))

    IT2._precalentar_jobs("NQ", jobs_nq, workers=workers, m1_dir=m1_dir)

    trade_cache: dict[str, pd.DataFrame] = {}
    ops_map: dict[str, pd.DataFrame] = {}
    # Cargar ancla V_nm30_maeATR30 con overlay exacto M1 SL=0.30 ATR
    trade_cache[cn_v_anc] = BASE._cargar_trades_cacheados(cn_v_anc)
    ops_map["V_nm30_maeATR30"] = aplicar_overlay_m1_causal(
        trade_cache[cn_v_anc], "V", atr_nq, orb_raw_nq, pv_nq, m1_arrays, sl_atr_k=0.30
    )

    for sp in specs:
        vname = sp["variante"]
        if sp["externa"] is not None:
            ops_map[vname] = cargar_ext_som_franklin(str(sp["externa"]))
            continue
        if sp["overlay"].get("banda_miembros"):
            continue
        cn = BASE._cache_key("NQ", sp["modulo"], sp["params"])
        if cn not in trade_cache:
            trade_cache[cn] = BASE._cargar_trades_cacheados(cn)
        ov = sp["overlay"]
        ops_map[vname] = aplicar_overlay_m1_causal(
            trade_cache[cn],
            sp["modulo"],
            atr_nq,
            orb_raw_nq,
            pv_nq,
            m1_arrays,
            sl_atr_k=ov.get("sl_atr_k"),
            tp_atr_k=ov.get("tp_atr_k"),
            be_trigger_r=ov.get("be_trigger_r"),
            trail_tiers=ov.get("trail_tiers"),
            tp_r=ov.get("tp_r"),
            stop_orb_mult=ov.get("stop_orb_mult", 1.25),
            stop_min_pts=ov.get("stop_min_pts", 2.0),
            stop_max_pts=ov.get("stop_max_pts", 100.0),
        )

    for sp in specs:
        miembros = sp["overlay"].get("banda_miembros")
        if miembros:
            ops_map[sp["variante"]] = combinar_banda_z([ops_map[m] for m in miembros])

    rows_desc: list[dict[str, Any]] = []
    daily_20_map: dict[str, pd.Series] = {}
    monthly_20_map: dict[str, pd.Series] = {}
    grilla_ops_20: dict[str, list[pd.DataFrame]] = {}
    grilla_ops_08: dict[str, list[pd.DataFrame]] = {}
    grilla_perillas: dict[str, dict[str, dict[str, str]]] = {}

    for sp in specs:
        vname = sp["variante"]
        gname = sp["grilla"]
        ops_all = ops_map[vname]
        rows_desc.append(_evaluar_ops_variante(sp, ops_all, start_nq))

        ops_d20 = ops_all[(ops_all["a5"] == "DESC") & (ops_all["fecha_int"] >= 20200101)]
        ops_d08 = ops_all[ops_all["a5"] == "DESC"]
        daily_20_map[vname] = ops_d20.groupby("fecha_int")["R_neto_mini"].sum() if len(ops_d20) else pd.Series(dtype=float)
        monthly_20_map[vname] = ops_d20.groupby("mes")["R_neto_mini"].sum() if len(ops_d20) else pd.Series(dtype=float)

        grilla_ops_20.setdefault(gname, []).append(ops_d20[["mes", "R_neto_mini"]].assign(variante=vname, R=ops_d20["R_neto_mini"]))
        grilla_ops_08.setdefault(gname, []).append(ops_d08[["mes", "R_neto_mini"]].assign(variante=vname, R=ops_d08["R_neto_mini"]))
        grilla_perillas.setdefault(gname, {})[vname] = dict(sp["perillas"])

    # B=5.000 permutaciones sincronizadas sobre las 44 variantes
    m_all_20 = pd.DataFrame(monthly_20_map).fillna(0.0)
    n_eff = max(float(BASE.DG.numero_efectivo(m_all_20)) if not m_all_20.empty else 1.0, 1.0)
    df_perm = IT2.calcular_bateria_permutaciones(daily_20_map, fechas_desc_20, n_eff=n_eff, n_perm=5000, bloque_dias=5, seed=20261122)

    df_e1 = pd.DataFrame(rows_desc).merge(df_perm[["variante", "p_perm", "q_bh", "p_maxT", "DSR"]], on="variante", how="left")
    df_e1["n_eff_global"] = round(n_eff, 2)
    df_e1["pasa_e1"] = (
        (df_e1["n_2020"] >= 30)
        & (df_e1["R_neto_2020"] > 0.0)
        & (df_e1["p_perm"] < 0.05)
        & (df_e1["q_bh"] < 0.05)
        & (df_e1["med_fric_R_2020"] <= 0.12)
        & df_e1["media_2020_pos_sin_top3"]
    )
    df_e1 = df_e1.sort_values(["grilla", "t_ses_2020"], ascending=[True, False]).reset_index(drop=True)
    df_e1.to_csv(OUT_DIR / "etapa1_factores_edge.csv", index=False)

    # Diagnosticos K55 / K56 por grilla (POST_2020 y FULL_2008)
    diags: dict[str, Any] = {}
    for gname in sorted(grilla_ops_20):
        pmap = grilla_perillas[gname]
        per_fn = {pcol: (lambda v, pcol=pcol, pm=pmap: pm.get(v, {}).get(pcol, "?")) for pcol in next(iter(pmap.values()))}
        df_g20 = pd.concat(grilla_ops_20[gname], ignore_index=True) if grilla_ops_20[gname] else pd.DataFrame()
        df_g08 = pd.concat(grilla_ops_08[gname], ignore_index=True) if grilla_ops_08[gname] else pd.DataFrame()
        diags[f"{gname}__POST_2020"] = BASE._diagnostico_con_mejor(df_g20, per_fn, total_celdas=len(pmap))
        diags[f"{gname}__FULL_2008"] = BASE._diagnostico_con_mejor(df_g08, per_fn, total_celdas=len(pmap))
    (OUT_DIR / "diagnostico_grillas_iter4.json").write_text(json.dumps(diags, indent=2, default=str), encoding="utf-8")

    # Confirmacion unica congelada en REP POST_2020 para: anclas + nominadas + top 2 por grilla
    cands_rep: set[str] = set(CORE6_ANCLAS_E1.values())
    cands_rep |= set(df_e1[df_e1["pasa_e1"]]["variante"].tolist())
    for _, grp in df_e1.groupby("grilla"):
        sub_g = grp[grp["n_2020"] >= 10] if (grp["n_2020"] >= 10).any() else grp
        cands_rep |= set(sub_g.sort_values("t_ses_2020", ascending=False).head(2)["variante"].tolist())

    m_rep_20 = BASE._meses_activos_a5(20200101, 20260930, "REP")
    m_rep_08 = BASE._meses_activos_a5(start_nq, 20260930, "REP")
    rows_rep: list[dict[str, Any]] = []
    gr_map = {s["variante"]: (s["grilla"], s["modulo"]) for s in specs}
    gr_map["V_nm30_maeATR30"] = ("ANCLA_IT3", "V")
    e1_idx = df_e1.set_index("variante")

    for vname in sorted(cands_rep):
        ops_all = ops_map[vname]
        ops_r20 = ops_all[(ops_all["a5"] == "REP") & (ops_all["fecha_int"] >= 20200101)].copy()
        ops_r08 = ops_all[ops_all["a5"] == "REP"].copy()
        sr20 = BASE.resumir_serie_r(ops_r20, col_r="R_neto_mini", bootstrap_reps=1200, seed=55, meses_totales=m_rep_20)
        sr08 = BASE.resumir_serie_r(ops_r08, col_r="R_neto_mini", bootstrap_reps=0, seed=55, meses_totales=m_rep_08)
        ddr20 = IT2._metricas_dd_r(ops_r20, m_rep_20)

        ops_d20 = ops_all[(ops_all["a5"] == "DESC") & (ops_all["fecha_int"] >= 20200101)].copy()
        sd20 = BASE.resumir_serie_r(ops_d20, col_r="R_neto_mini", bootstrap_reps=0, seed=42, meses_totales=BASE._meses_activos_a5(20200101, 20260930, "DESC"))
        ddd20 = IT2._metricas_dd_r(ops_d20, BASE._meses_activos_a5(20200101, 20260930, "DESC"))

        gr, mo = gr_map.get(vname, ("ANCLA", "?"))
        q_val = float(e1_idx.loc[vname, "q_bh"]) if vname in e1_idx.index else float("nan")
        r_rep_20_val = float(sr20["R_neto_mini"])
        rows_rep.append({
            "grilla": gr,
            "modulo": mo,
            "variante": vname,
            "n_desc_20": int(sd20["n"]),
            "R_desc_20": float(sd20["R_neto_mini"]),
            "R_mes_desc_20": float(sd20["R_por_mes"]),
            "t_desc_20": float(sd20["t_ses"]),
            "calmar_desc_20": float(ddd20["calmar"]),
            "q_bh_desc": q_val,
            "n_rep_20": int(sr20["n"]),
            "R_rep_20": r_rep_20_val,
            "R_micro_rep_20": float(sr20["R_neto_micro"]),
            "R_mes_rep_20": float(sr20["R_por_mes"]),
            "t_rep_20": float(sr20["t_ses"]),
            "dd_R_rep_20": float(ddr20["dd_R"]),
            "calmar_rep_20": float(ddr20["calmar"]),
            "p_boot_rep_20": float(sr20["p_boot"]),
            "R_rep_08": float(sr08["R_neto_mini"]),
            "confirma_rep": bool(sr20["n"] >= 5 and np.isfinite(r_rep_20_val) and r_rep_20_val > 0.0),
        })

    df_rep = pd.DataFrame(rows_rep).sort_values(["modulo", "calmar_rep_20"], ascending=[True, False]).reset_index(drop=True)
    df_rep.to_csv(OUT_DIR / "etapa1_confirmacion_rep.csv", index=False)
    return df_e1, df_rep, diags, ops_map


def seleccionar_carteras_causales(
    df_e1: pd.DataFrame,
    ops_map: Mapping[str, pd.DataFrame],
) -> tuple[dict[str, dict[str, pd.DataFrame]], dict[str, str]]:
    """Promueve variantes en DESC POST_2020 estrictamente sin mirar REP para armar CORE_6, P_OPT y P_OPT_SF."""
    e1 = df_e1.set_index("variante")
    core6 = {f"{v}::NQ": ops_map[v] for v in (
        "R_osc30_end660_ATR50", "Z_b15_e20_eff45_ATR50", "T_stop100_calTrue",
        "V_nm30_maeATR30", "W_base_slope_ATR25", "N_d5_fbTrue_ATR25",
    )}

    # Evaluar tambien ancla V_nm30_maeATR30 en DESC para comparar exactamente contra P1_V_ESCALA
    m_d20 = BASE._meses_activos_a5(20200101, 20260930, "DESC")
    ops_va = ops_map["V_nm30_maeATR30"]
    va_d = ops_va[(ops_va["a5"] == "DESC") & (ops_va["fecha_int"] >= 20200101)]
    va_s = BASE.resumir_serie_r(va_d, col_r="R_neto_mini", bootstrap_reps=0, seed=42, meses_totales=m_d20)
    va_dd = IT2._metricas_dd_r(va_d, m_d20)

    elegidos: dict[str, str] = {}
    p_opt_streams: dict[str, pd.DataFrame] = {}

    for mod, ancla in CORE6_ANCLAS_E1.items():
        if mod == "V":
            anc_cal, anc_ts, anc_rm, anc_dd = float(va_dd["calmar"]), float(va_s["t_ses"]), float(va_s["R_por_mes"]), abs(float(va_dd["dd_R"]))
        else:
            anc_cal = float(e1.loc[ancla, "calmar"])
            anc_ts = float(e1.loc[ancla, "t_ses_2020"])
            anc_rm = float(e1.loc[ancla, "R_mes_2020"])
            anc_dd = abs(float(e1.loc[ancla, "dd_R"]))

        sub = df_e1[(df_e1["modulo"] == mod) & df_e1["pasa_e1"]].copy()
        mej = []
        for _, rr in sub.iterrows():
            cal_r = float(rr["calmar"])
            ts_r = float(rr["t_ses_2020"])
            rm_r = float(rr["R_mes_2020"])
            dd_r = abs(float(rr["dd_R"]))
            mejora_calmar = cal_r > anc_cal + 1e-6 and dd_r <= 1.25 * max(anc_dd, 1.0)
            mejora_freq = (ts_r >= anc_ts - 0.05) and (rm_r > anc_rm * 1.10) and (dd_r <= 1.15 * max(anc_dd, 1.0))
            if str(rr["variante"]) != ancla and (mejora_calmar or mejora_freq):
                mej.append((cal_r + 0.25 * ts_r, str(rr["variante"])))

        gan = max(mej, key=lambda x: x[0])[1] if mej else ancla
        elegidos[mod] = gan
        p_opt_streams[f"{gan}::NQ"] = ops_map[gan]

    p_opt_sf = dict(p_opt_streams)
    for ext_mod, ext_name in (("SOM", "SOMEOD_ext_NQ"), ("FRK", "FRANKLIN_ext_NQ")):
        if ext_name in e1.index and bool(e1.loc[ext_name, "pasa_e1"]):
            p_opt_sf[f"{ext_name}::NQ"] = ops_map[ext_name]
            elegidos[ext_mod] = ext_name

    carteras = {"CORE_6": core6, "P_OPT": p_opt_streams}
    if len(p_opt_sf) > len(p_opt_streams):
        carteras["P_OPT_SF"] = p_opt_sf
    return carteras, elegidos


def calcular_ahorro_hibrido_nq_mnq(n_micros_total: int, fric_nq: float, fric_mnq: float) -> tuple[int, int, float]:
    """Descompone N micros equivalentes en (n_nq, n_mnq) y devuelve ahorro USD por viaje redondo vs MNQ puro."""
    n_tot = max(int(n_micros_total), 0)
    n_nq = n_tot // 10
    n_mnq = n_tot % 10
    costo_puro = n_tot * float(fric_mnq) * 2.0
    costo_hib = n_nq * float(fric_nq) * 20.0 + n_mnq * float(fric_mnq) * 2.0
    return n_nq, n_mnq, max(0.0, costo_puro - costo_hib)


def construir_serie_intradia_prop(
    tr_df: pd.DataFrame,
    sesiones: list[int],
    usd_1r: float,
    max_micros: int,
    hibrido: bool,
    fric_nq: float,
    fric_mnq: float,
    contr_mult: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Convierte trades de cartera a (P_d, LO_d) diarios intradia exactos en USD (MNQ puro o hibrido NQ/MNQ)."""
    n_ses = len(sesiones)
    ses_idx = {int(s): idx for idx, s in enumerate(sesiones)}
    P = np.zeros(n_ses, dtype=np.float64)
    LO = np.zeros(n_ses, dtype=np.float64)
    if tr_df is None or tr_df.empty or n_ses == 0:
        return P, LO, {"pct_hibrido": 0.0, "ahorro_total_usd": 0.0}

    df = tr_df[tr_df["w_eff"] > 1e-9].copy()
    if df.empty:
        return P, LO, {"pct_hibrido": 0.0, "ahorro_total_usd": 0.0}

    risk_pts = np.maximum(df["riesgo_pts"].to_numpy(dtype=np.float64), 1e-6)
    bruto_pts = (df["R_bruto"].to_numpy(dtype=np.float64) * risk_pts)
    mae_pts = df["mae_pts"].to_numpy(dtype=np.float64) if "mae_pts" in df.columns else np.maximum(-bruto_pts, 0.0)
    w_eff = df["w_eff"].to_numpy(dtype=np.float64)

    usd_arr = np.empty(len(df), dtype=np.float64)
    adv_arr = np.empty(len(df), dtype=np.float64)
    n_hib_trades = 0
    ahorro_usd = 0.0

    for j in range(len(df)):
        tgt_usd = float(usd_1r) * float(w_eff[j])
        r_1mic = float(risk_pts[j]) * 2.0
        n_tot = int(min(max_micros, max(0, round(tgt_usd / max(r_1mic, 1e-6)))))
        if n_tot == 0 and tgt_usd >= 0.55 * r_1mic:
            n_tot = 1
        if hibrido and n_tot >= 10:
            n_nq, n_mnq, save_j = calcular_ahorro_hibrido_nq_mnq(n_tot, fric_nq, fric_mnq)
            n_hib_trades += 1
            ahorro_usd += save_j
        else:
            n_nq, n_mnq = 0, n_tot
        bp = float(bruto_pts[j])
        mp = max(float(mae_pts[j]), 0.0)
        usd_arr[j] = n_nq * (bp - float(fric_nq)) * 20.0 + n_mnq * (bp - float(fric_mnq)) * 2.0
        adv_arr[j] = n_nq * (mp + float(fric_nq)) * 20.0 + n_mnq * (mp + float(fric_mnq)) * 2.0

    # Contraccion causal por operacion operando solo dias activos (evita deriva fantasma en dias sin trades)
    if len(usd_arr) > 0 and contr_mult != 1.0:
        shift_op = (1.0 - float(contr_mult)) * float(np.mean(usd_arr))
        usd_arr = usd_arr - shift_op
        if shift_op > 0.0:
            adv_arr = np.maximum(adv_arr + shift_op, np.maximum(-usd_arr, 0.0))
        else:
            adv_arr = np.maximum(adv_arr, np.maximum(-usd_arr, 0.0))

    df["usd_j"] = usd_arr
    df["adv_j"] = adv_arr
    df = df.sort_values(["fecha_int", "en_ns"]).reset_index(drop=True)

    f_arr = df["fecha_int"].to_numpy(dtype=np.int64)
    en_arr = df["en_ns"].to_numpy(dtype=np.int64)
    ex_arr = df["ex_ns"].to_numpy(dtype=np.int64)
    u_arr = df["usd_j"].to_numpy(dtype=np.float64)
    a_arr = df["adv_j"].to_numpy(dtype=np.float64)

    n = len(df)
    pos = 0
    while pos < n:
        f_cur = int(f_arr[pos])
        end = pos + 1
        while end < n and int(f_arr[end]) == f_cur:
            end += 1
        idx_s = ses_idx.get(f_cur, -1)
        if idx_s >= 0:
            tot_p = float(np.sum(u_arr[pos:end]))
            lo_min = min(0.0, tot_p)
            for j in range(pos, end):
                tj = int(en_arr[j])
                realized = 0.0
                open_adv = float(a_arr[j])
                for k in range(pos, j):
                    if int(ex_arr[k]) <= tj:
                        realized += float(u_arr[k])
                    else:
                        open_adv += float(a_arr[k])
                lo_min = min(lo_min, realized - open_adv)
            P[idx_s] = tot_p
            LO[idx_s] = lo_min
        pos = end

    return P, LO, {
        "pct_hibrido": round(100.0 * n_hib_trades / max(len(df), 1), 1),
        "ahorro_total_usd": round(ahorro_usd, 1),
    }


@njit(cache=False)
def _trayectoria_cuenta_intradia(
    P_ev: np.ndarray,
    LO_ev: np.ndarray,
    P_f0: np.ndarray,
    LO_f0: np.ndarray,
    P_f1: np.ndarray,
    LO_f1: np.ndarray,
    P_f2: np.ndarray,
    LO_f2: np.ndarray,
    thr1: float,
    thr2: float,
    N: int,
    seed: int,
    max_dias: int,
    objetivo: float,
    mll: float,
    dll: float,
    dia_min: float,
    tope: float,
    cons: float,
    pol_max: bool,
    colchon_min: float,
    eval_cap_cons: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Trayectoria Monte Carlo de una sola cuenta LucidFlex (evaluacion -> 5 retiros -> live)."""
    np.random.seed(seed)
    L = len(P_ev)
    cap_ev = 0.95 * cons * objetivo if eval_cap_cons else 1e18

    pasa = np.zeros(N, dtype=np.int64)
    quema_eval = np.zeros(N, dtype=np.int64)
    cobrado = np.zeros(N, dtype=np.float64)
    n_ret = np.zeros(N, dtype=np.int64)
    dias_eval = np.zeros(N, dtype=np.int64)
    llega_live = np.zeros(N, dtype=np.int64)

    for k in range(N):
        est = 1  # 1=eval, 3=funded
        bal = 0.0
        piso = -mll
        maxc = 0.0
        mayor = 0.0
        dok = 0
        c0 = 0.0
        npg = 0
        pos = np.random.randint(L)

        for d in range(max_dias):
            if d % 5 == 0:
                pos = np.random.randint(L)
            j = (pos + d % 5) % L

            if est == 1:
                p = P_ev[j]
                lo = LO_ev[j]
                if dll > 0.0 and lo <= -dll:
                    p = -dll
                    lo = -dll
                elif eval_cap_cons and p > cap_ev:
                    p = cap_ev
                if bal + lo <= piso:
                    quema_eval[k] = 1
                    dias_eval[k] = d + 1
                    break
                bal += p
                if p > mayor:
                    mayor = p
                if bal > maxc:
                    maxc = bal
                piso = min(max(piso, maxc - mll), 100.0)
                if bal >= objetivo and (bal <= 0.0 or mayor / bal <= cons):
                    pasa[k] = 1
                    dias_eval[k] = d + 1
                    est = 3
                    bal = 0.0
                    piso = -mll
                    maxc = 0.0
                    dok = 0
                    c0 = 0.0
                    npg = 0
            else:
                if thr1 > 0.0 and bal < thr1:
                    p, lo = P_f0[j], LO_f0[j]
                elif thr2 > 0.0 and bal >= thr2:
                    p, lo = P_f2[j], LO_f2[j]
                else:
                    p, lo = P_f1[j], LO_f1[j]

                if dll > 0.0 and lo <= -dll:
                    p = -dll
                    lo = -dll
                if bal + lo <= piso:
                    break
                bal += p
                if p >= dia_min:
                    dok += 1
                if bal > maxc:
                    maxc = bal
                if piso < 100.0:
                    piso = 100.0 if maxc > mll + 100.0 else max(piso, maxc - mll)
                monto = min(tope, 0.5 * bal)
                cond_pol = (monto >= tope) if pol_max else True
                cond_col = (bal - monto - 100.0) >= colchon_min if colchon_min > 0.0 else True
                if dok >= 5 and bal > c0 and monto >= 500.0 and cond_pol and cond_col:
                    cobrado[k] += 0.9 * monto
                    n_ret[k] += 1
                    bal -= monto
                    npg += 1
                    piso = 100.0
                    c0 = bal
                    dok = 0
                    if npg >= 5:
                        llega_live[k] = 1
                        break

    return pasa, quema_eval, cobrado, n_ret, dias_eval, llega_live


@njit(cache=False)
def _trayectoria_cartera_intradia(
    P_ev: np.ndarray,
    LO_ev: np.ndarray,
    P_f0: np.ndarray,
    LO_f0: np.ndarray,
    P_f1: np.ndarray,
    LO_f1: np.ndarray,
    P_f2: np.ndarray,
    LO_f2: np.ndarray,
    thr1: float,
    thr2: float,
    N: int,
    seed: int,
    H: int,
    objetivo: float,
    mll: float,
    dll: float,
    dia_min: float,
    tope: float,
    cons: float,
    pr: float,
    max_eval: int,
    pol_max: bool,
    colchon_min: float,
    eval_cap_cons: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Cartera LucidFlex intradia hasta 5 fondeadas + max 10 totales a 12m (252) y 24m (504)."""
    np.random.seed(seed)
    L = len(P_ev)
    S = 10
    cap_ev = 0.95 * cons * objetivo if eval_cap_cons else 1e18

    caja12 = np.zeros(N, dtype=np.float64)
    caja24 = np.zeros(N, dtype=np.float64)
    cmin = np.zeros(N, dtype=np.float64)
    ret12 = np.zeros(N, dtype=np.int64)
    ret24 = np.zeros(N, dtype=np.int64)
    bruto12 = np.zeros(N, dtype=np.float64)
    bruto24 = np.zeros(N, dtype=np.float64)
    live24 = np.full(N, -1.0, dtype=np.float64)
    comp24 = np.zeros(N, dtype=np.int64)

    for k in range(N):
        est = np.zeros(S, dtype=np.int64)
        bal = np.zeros(S, dtype=np.float64)
        piso = np.zeros(S, dtype=np.float64)
        maxc = np.zeros(S, dtype=np.float64)
        mayor = np.zeros(S, dtype=np.float64)
        dok = np.zeros(S, dtype=np.int64)
        c0 = np.zeros(S, dtype=np.float64)
        npg = np.zeros(S, dtype=np.int64)

        pos = np.random.randint(L)
        c = 0.0
        mn = 0.0
        r12 = 0
        b12 = 0.0
        r24 = 0
        b24 = 0.0
        got_12 = False

        for d in range(H):
            if d % 5 == 0:
                pos = np.random.randint(L)
            j = (pos + d % 5) % L

            p_ev_d, lo_ev_d = P_ev[j], LO_ev[j]
            if dll > 0.0 and lo_ev_d <= -dll:
                p_ev_d = -dll
                lo_ev_d = -dll
            elif eval_cap_cons and p_ev_d > cap_ev:
                p_ev_d = cap_ev

            vivo = False
            for i in range(S):
                if est[i] == 1:
                    if bal[i] + lo_ev_d <= piso[i]:
                        est[i] = 0
                        continue
                    bal[i] += p_ev_d
                    if p_ev_d > mayor[i]:
                        mayor[i] = p_ev_d
                    if bal[i] > maxc[i]:
                        maxc[i] = bal[i]
                    piso[i] = min(max(piso[i], maxc[i] - mll), 100.0)
                    if bal[i] >= objetivo and (bal[i] <= 0.0 or mayor[i] / bal[i] <= cons):
                        est[i] = 2
                elif est[i] == 3:
                    if thr1 > 0.0 and bal[i] < thr1:
                        pf, lof = P_f0[j], LO_f0[j]
                    elif thr2 > 0.0 and bal[i] >= thr2:
                        pf, lof = P_f2[j], LO_f2[j]
                    else:
                        pf, lof = P_f1[j], LO_f1[j]
                    if dll > 0.0 and lof <= -dll:
                        pf = -dll
                        lof = -dll
                    if bal[i] + lof <= piso[i]:
                        est[i] = 0
                        continue
                    bal[i] += pf
                    if pf >= dia_min:
                        dok[i] += 1
                    if bal[i] > maxc[i]:
                        maxc[i] = bal[i]
                    if piso[i] < 100.0:
                        piso[i] = 100.0 if maxc[i] > mll + 100.0 else max(piso[i], maxc[i] - mll)
                    monto = min(tope, 0.5 * bal[i])
                    cond_pol = (monto >= tope) if pol_max else True
                    cond_col = (bal[i] - monto - 100.0) >= colchon_min if colchon_min > 0.0 else True
                    if dok[i] >= 5 and bal[i] > c0[i] and monto >= 500.0 and cond_pol and cond_col:
                        c += 0.9 * monto
                        r24 += 1
                        b24 += monto
                        if d < 252:
                            r12 += 1
                            b12 += monto
                        bal[i] -= monto
                        npg[i] += 1
                        piso[i] = 100.0
                        c0[i] = bal[i]
                        dok[i] = 0
                        if npg[i] >= 5:
                            vivo = True

            if vivo:
                for i in range(S):
                    if est[i] == 1 and bal[i] - piso[i] >= 0.5 * mll:
                        c += pr
                live24[k] = float(d)
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
                if est[i] == 2 and nf < 5:
                    est[i] = 3
                    nf += 1
                    bal[i] = 0.0
                    piso[i] = -mll
                    maxc[i] = 0.0
                    dok[i] = 0
                    c0[i] = 0.0
                    npg[i] = 0
            for i in range(S):
                if est[i] == 1 or est[i] == 2:
                    ne += 1
            for i in range(S):
                if ne >= max_eval or ne + nf >= 10:
                    break
                if est[i] == 0:
                    est[i] = 1
                    bal[i] = 0.0
                    piso[i] = -mll
                    maxc[i] = 0.0
                    mayor[i] = 0.0
                    c -= pr
                    comp24[k] += 1
                    ne += 1
                    break

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
        bruto24[k] = b24

    return caja12, caja24, cmin, ret12, ret24, bruto12, bruto24, live24, comp24


def planes_etapa2_iter4(cart_gan_a: str = "P_OPT") -> list[dict[str, Any]]:
    """Define las 24 configuraciones de ablacion controlada Prop Firm (Bloques A..D)."""
    def mk(pid: str, blq: str, pal: str, cart: str, tam: str, usd_ev: float, usd_f1: float,
           *, usd_f0: float | None = None, usd_f2: float | None = None, thr1: float = 0.0, thr2: float = 0.0,
           hibrido: bool = True, dll: bool = True, cons: float = 0.50, pol_max: bool = True,
           colchon: float = 0.0, max_eval: int = 5, eval_cap: bool = False, esq: str = "W5") -> dict[str, Any]:
        return {
            "plan_id": pid, "bloque": blq, "palanca": pal, "cartera": cart, "esquema": esq,
            "tam": tam, "usd_ev": usd_ev, "usd_f0": usd_f0 if usd_f0 is not None else usd_f1,
            "usd_f1": usd_f1, "usd_f2": usd_f2 if usd_f2 is not None else usd_f1,
            "thr1": thr1, "thr2": thr2, "hibrido": hibrido, "dll": dll, "cons": cons,
            "pol_max": pol_max, "colchon_min": colchon, "max_eval": max_eval, "eval_cap_cons": eval_cap,
        }

    # Base 150K: $450/R, DLL=True, cons=50%, tope $3000, max_eval=5
    out = [
        # Bloque A (6): efecto de cartera + ejecucion hibrida NQ/MNQ
        mk("A01_150K_CORE6_MNQ_base", "A_Cartera_Hibrido", "Ancla CORE_6 MNQ", "CORE_6", "150K", 450.0, 450.0, hibrido=False),
        mk("A02_150K_P_OPT_MNQ", "A_Cartera_Hibrido", "Edge P_OPT MNQ", "P_OPT", "150K", 450.0, 450.0, hibrido=False),
        mk("A03_150K_P_OPT_HibridoNQ", "A_Cartera_Hibrido", "Hibrido NQ/MNQ", "P_OPT", "150K", 450.0, 450.0, hibrido=True),
        mk("A04_150K_P_OPT_SF_HibridoNQ", "A_Cartera_Hibrido", "+SOMEOD+FRANKLIN", "P_OPT_SF", "150K", 450.0, 450.0, hibrido=True),
        mk("A05_50K_CORE6_MNQ_base", "A_Cartera_Hibrido", "50K CORE_6 MNQ", "CORE_6", "50K", 200.0, 200.0, hibrido=False),
        mk("A06_50K_P_OPT_SF_HibridoNQ", "A_Cartera_Hibrido", "50K Opt+Ext+Hib", "P_OPT_SF", "50K", 200.0, 200.0, hibrido=True),

        # Bloque B (6): reglas LucidFlex (Tamano 50/100/150K, DLL On/Off, Cons 40%/50%, Eval Cap)
        mk("B07_100K_Hibrido", "B_Reglas_Lucid", "Tamano 100K R300", cart_gan_a, "100K", 300.0, 300.0),
        mk("B08_150K_sinDLL", "B_Reglas_Lucid", "DLL Off (sinDLL)", cart_gan_a, "150K", 450.0, 450.0, dll=False),
        mk("B09_150K_cons40", "B_Reglas_Lucid", "Consistencia 40%", cart_gan_a, "150K", 450.0, 450.0, cons=0.40),
        mk("B10_150K_cons40_capEval", "B_Reglas_Lucid", "40% + Cap Eval", cart_gan_a, "150K", 450.0, 450.0, cons=0.40, eval_cap=True),
        mk("B11_50K_cons40_capEval", "B_Reglas_Lucid", "50K 40%+CapEval", cart_gan_a, "50K", 200.0, 200.0, cons=0.40, eval_cap=True),
        mk("B12_150K_cons50_capEval", "B_Reglas_Lucid", "50% + Cap Eval", cart_gan_a, "150K", 450.0, 450.0, cons=0.50, eval_cap=True),

        # Bloque C (6): sizing por riesgo + asimetria Eval/Funded + Buffer Scaling dinamico
        mk("C13_150K_R300_conserv", "C_Sizing_Buffer", "R fijo $300", cart_gan_a, "150K", 300.0, 300.0),
        mk("C14_150K_R600_agresivo", "C_Sizing_Buffer", "R fijo $600", cart_gan_a, "150K", 600.0, 600.0),
        mk("C15_150K_R750_evalBoost", "C_Sizing_Buffer", "Eval $750 / Fund $450", cart_gan_a, "150K", 750.0, 450.0),
        mk("C16_150K_Asim_Eval600_Fund300", "C_Sizing_Buffer", "Asim $600/$300", cart_gan_a, "150K", 600.0, 300.0),
        mk("C17_150K_BufferScale", "C_Sizing_Buffer", "BufferScale 300/450/600", cart_gan_a, "150K", 450.0, 450.0, usd_f0=300.0, usd_f2=600.0, thr1=2000.0, thr2=4500.0),
        mk("C18_150K_Eval675_BufferScale", "C_Sizing_Buffer", "Eval $675 + BufferScale", cart_gan_a, "150K", 675.0, 450.0, usd_f0=300.0, usd_f2=675.0, thr1=2000.0, thr2=4500.0),

        # Bloque D (6): politica de retiros/colchon, concurrencia de evals y esquema W5 vs W3_ERC
        mk("D19_150K_RetiroMin500", "D_Retiro_Pool", "Retiro Min $500", cart_gan_a, "150K", 450.0, 450.0, pol_max=False, colchon=0.0),
        mk("D20_150K_RetiroColchon1500", "D_Retiro_Pool", "Colchon Min $1500", cart_gan_a, "150K", 450.0, 450.0, pol_max=False, colchon=1500.0),
        mk("D21_150K_RetiroColchon2500", "D_Retiro_Pool", "Colchon Min $2500", cart_gan_a, "150K", 450.0, 450.0, pol_max=False, colchon=2500.0),
        mk("D22_150K_maxEval10", "D_Retiro_Pool", "Pool 10 Evals", cart_gan_a, "150K", 450.0, 450.0, max_eval=10),
        mk("D23_150K_maxEval3", "D_Retiro_Pool", "Pool 3 Evals", cart_gan_a, "150K", 450.0, 450.0, max_eval=3),
        mk("D24_150K_Pesos_W3_ERC", "D_Retiro_Pool", "Esquema W3_ERC", cart_gan_a, "150K", 450.0, 450.0, esq="W3"),
    ]
    return out


def _evaluar_plan_prop(
    cfg_p: Mapping[str, Any],
    tr_map: Mapping[tuple[str, str, str], pd.DataFrame],
    sesiones_map: Mapping[str, list[int]],
    fric_nq: float,
    fric_mnq: float,
    part: str,
    contr_nom: str,
    contr_mult: float,
    *,
    N: int = 3000,
    seed: int = 2026,
) -> dict[str, Any]:
    """Ejecuta MC intradia completo (1 cuenta + cartera 12m/24m) para un plan bajo un regimén dado."""
    tam = str(cfg_p["tam"])
    ct = LG.TAMANOS[tam]
    cons = float(cfg_p["cons"])
    dll_val = float(ct["dll"]) if cfg_p["dll"] else 0.0
    if abs(cons - 0.40) < 1e-6:
        with costos.estimados_permitidos(PREREG_REL):
            pr = float(LG.precio(tam, bool(cfg_p["dll"]), cons))
    else:
        pr = float(LG.precio(tam, bool(cfg_p["dll"]), cons))

    key_tr = (str(cfg_p["cartera"]), str(cfg_p["esquema"]), part)
    tr_df = tr_map.get(key_tr, tr_map[("P_OPT", str(cfg_p["esquema"]), part)])
    ses = sesiones_map[part]
    cache_s: dict[float, tuple[np.ndarray, np.ndarray, dict[str, Any]]] = {}

    def get_pl(u: float) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
        key_u = round(float(u), 2)
        if key_u not in cache_s:
            cache_s[key_u] = construir_serie_intradia_prop(
                tr_df, ses, float(u), int(ct["micros"]), bool(cfg_p["hibrido"]),
                fric_nq, fric_mnq, contr_mult=contr_mult,
            )
        return cache_s[key_u]

    P_ev, LO_ev, info_ev = get_pl(cfg_p["usd_ev"])
    P_f0, LO_f0, _ = get_pl(cfg_p["usd_f0"])
    P_f1, LO_f1, info_f1 = get_pl(cfg_p["usd_f1"])
    P_f2, LO_f2, _ = get_pl(cfg_p["usd_f2"])

    pasa, quema, cob_acc, nret_acc, d_ev, live_acc = _trayectoria_cuenta_intradia(
        P_ev, LO_ev, P_f0, LO_f0, P_f1, LO_f1, P_f2, LO_f2,
        float(cfg_p["thr1"]), float(cfg_p["thr2"]),
        N, seed, 504,
        float(ct["objetivo"]), float(ct["mll"]), dll_val, float(ct["dia_min"]),
        float(ct["tope"]), cons, bool(cfg_p["pol_max"]), float(cfg_p["colchon_min"]),
        bool(cfg_p["eval_cap_cons"]),
    )
    c12, c24, cmin, r12, r24, b12, b24, live24, comp24 = _trayectoria_cartera_intradia(
        P_ev, LO_ev, P_f0, LO_f0, P_f1, LO_f1, P_f2, LO_f2,
        float(cfg_p["thr1"]), float(cfg_p["thr2"]),
        N, seed + 17, 504,
        float(ct["objetivo"]), float(ct["mll"]), dll_val, float(ct["dia_min"]),
        float(ct["tope"]), cons, pr, int(cfg_p["max_eval"]),
        bool(cfg_p["pol_max"]), float(cfg_p["colchon_min"]), bool(cfg_p["eval_cap_cons"]),
    )

    n_ret_tot = float(np.sum(r24))
    tam_med_ret = float(np.sum(b24) / n_ret_tot) if n_ret_tot > 0.0 else 0.0
    passed_mask = pasa == 1
    d_pas = d_ev[passed_mask]

    return {
        "plan_id": cfg_p["plan_id"],
        "bloque": cfg_p["bloque"],
        "palanca": cfg_p["palanca"],
        "cartera": cfg_p["cartera"],
        "esquema": cfg_p["esquema"],
        "tam": tam,
        "particion_a5": part,
        "regimen_media": contr_nom,
        "precio_eval": round(pr, 2),
        "usd_dia_f1": round(float(np.mean(P_f1)), 2),
        "worst_lo_f1": round(float(np.min(LO_f1)), 1),
        "pct_hibrido_ops": info_f1["pct_hibrido"],
        "ahorro_hib_hist_usd": info_f1["ahorro_total_usd"],
        "ev_examen_usd": round(float(np.mean(cob_acc) - pr), 1),
        "pasa_eval_pct": round(100.0 * float(np.mean(pasa)), 1),
        "quema_eval_pct": round(100.0 * float(np.mean(quema)), 1),
        "dias_pasar_p50": round(float(np.median(d_pas)), 1) if len(d_pas) else None,
        "retiros_por_cuenta": round(float(np.mean(nret_acc)), 2),
        "prob_3plus_cuenta_pct": round(100.0 * float(np.mean(nret_acc >= 3)), 1),
        "p_primer_retiro_12m_pct": round(100.0 * float(np.mean(r12 >= 1)), 1),
        "retiros_12m": round(float(np.mean(r12)), 2),
        "retiros_24m": round(float(np.mean(r24)), 2),
        "tamano_medio_retiro_usd": round(tam_med_ret, 1),
        "neto12_medio_usd": round(float(np.mean(c12)), 1),
        "neto12_p50_usd": round(float(np.median(c12)), 1),
        "neto24_medio_usd": round(float(np.mean(c24)), 1),
        "p_neto12_pos_pct": round(100.0 * float(np.mean(c12 > 0.0)), 1),
        "p_live_24m_pct": round(100.0 * float(np.mean(live24 >= 0.0)), 1),
        "caja_min_p50_usd": round(float(np.median(cmin)), 1),
        "caja_min_p10_usd": round(float(np.quantile(cmin, 0.10)), 1),
        "evals_compradas_24m": round(float(np.mean(comp24)), 1),
    }


def _reinyectar_mae_y_bruto(
    tr_df: pd.DataFrame,
    ops_streams: Mapping[str, pd.DataFrame],
    fric_nq: float,
) -> pd.DataFrame:
    """Preserva mae_pts intradia real y R_bruto perdidos al pasar por aplicar_tope_concurrencia_causal."""
    if tr_df is None or tr_df.empty:
        return tr_df
    extras = []
    for sid, df in ops_streams.items():
        if df is not None and not df.empty and "mae_pts" in df.columns and "R_bruto" in df.columns:
            sub = df[["en_ns", "ex_ns", "mae_pts", "R_bruto"]].copy()
            sub["stream"] = sid
            extras.append(sub)
    out = tr_df.copy()
    if extras:
        meta_ext = (
            pd.concat(extras, ignore_index=True)
            .groupby(["stream", "en_ns", "ex_ns"], as_index=False)
            .agg(mae_pts=("mae_pts", "max"), R_bruto=("R_bruto", "first"))
        )
        out = out.merge(meta_ext, on=["stream", "en_ns", "ex_ns"], how="left")
    if "R_bruto" not in out.columns:
        out["R_bruto"] = np.nan
    fb_r = out["R_neto_mini"].to_numpy(float) + float(fric_nq) / np.maximum(out["riesgo_pts"].to_numpy(float), 1e-6)
    out["R_bruto"] = out["R_bruto"].fillna(pd.Series(fb_r, index=out.index))
    if "mae_pts" not in out.columns:
        out["mae_pts"] = np.nan
    fb_mae = np.maximum(-out["R_bruto"].to_numpy(float) * out["riesgo_pts"].to_numpy(float), 0.0)
    out["mae_pts"] = out["mae_pts"].fillna(pd.Series(fb_mae, index=out.index))
    return out


def _correr_etapa2(
    df_e1: pd.DataFrame,
    ops_map: Mapping[str, pd.DataFrame],
    fechas_nq: Mapping[str, list[int]],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Ejecuta las 24 pruebas de Etapa 2 (Prop Firm intradia DESC -> REP) y calcula deltas por palanca."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fric_nq, fric_mnq = BASE.friccion_instrumento_puntos("NQ", prereg_rel=PREREG_REL, micro_equiv=BASE.MICRO_EQUIV)
    assert fric_mnq is not None

    carteras, elegidos = seleccionar_carteras_causales(df_e1, ops_map)
    m_desc = BASE._meses_activos_a5(20200101, 20260930, "DESC")
    m_rep = BASE._meses_activos_a5(20200101, 20260930, "REP")
    ses_desc = fechas_nq["DESC"]
    ses_rep = fechas_nq["REP"]

    pesos_meta: dict[str, Any] = {}
    tr_map: dict[tuple[str, str, str], pd.DataFrame] = {}
    resumen_carteras: list[dict[str, Any]] = []

    for cnom, smap in carteras.items():
        s_d: dict[str, pd.DataFrame] = {}
        s_r: dict[str, pd.DataFrame] = {}
        dur_d: dict[str, float] = {}
        dc_d: dict[str, pd.Series] = {}
        mc_d: dict[str, pd.Series] = {}
        for sid, df in smap.items():
            sd = df[(df["a5"] == "DESC") & (df["fecha_int"] >= 20200101)].copy()
            sr = df[(df["a5"] == "REP") & (df["fecha_int"] >= 20200101)].copy()
            s_d[sid], s_r[sid] = sd, sr
            dur_d[sid] = float(sd["dur_min"].median()) if len(sd) else 60.0
            dc_d[sid] = sd.groupby("fecha_int")["R_neto_mini"].sum()
            mc_d[sid] = sd.groupby("mes")["R_neto_mini"].sum()

        D_d = pd.DataFrame(dc_d, index=ses_desc).fillna(0.0)
        M_d = pd.DataFrame(mc_d).fillna(0.0)
        p_all = IT2.calcular_pesos_esquemas(D_d, M_d, dur_d)
        pesos_meta[cnom] = p_all

        for esq_short, esq_key, cap in (("W5", "W5_freq_dur_conc", 3.0), ("W3", "W3_ERC_cov_cap", None)):
            w_map = p_all[esq_key]
            tr_d, mx_d = IT2.aplicar_tope_concurrencia_causal(s_d, w_map, None, cap_r=cap)
            tr_r, mx_r = IT2.aplicar_tope_concurrencia_causal(s_r, w_map, None, cap_r=cap)
            tr_d = _reinyectar_mae_y_bruto(tr_d, s_d, fric_nq)
            tr_r = _reinyectar_mae_y_bruto(tr_r, s_r, fric_nq)
            tr_map[(cnom, esq_short, "DESC")] = tr_d
            tr_map[(cnom, esq_short, "REP")] = tr_r

            for pnom, tr_p, ses_p, mtot, mx in (("DESC", tr_d, ses_desc, m_desc, mx_d), ("REP", tr_r, ses_rep, m_rep, mx_r)):
                sdia = tr_p.groupby("fecha_int")["R_eff"].sum().reindex(ses_p, fill_value=0.0)
                ev = IT2.evaluar_serie_cartera(sdia, mtot, mc_reps=4000, seed=99)
                resumen_carteras.append({"cartera": cnom, "esquema": esq_short, "particion": pnom, "max_open_R": mx, **ev})

    # Seleccionar mejor cartera del Bloque A exclusivamente en DESC bajo contraccion 60%
    planes_a = [
        p for p in planes_etapa2_iter4("P_OPT")
        if p["bloque"] == "A_Cartera_Hibrido" and p["tam"] == "150K" and p["cartera"] in carteras
    ]
    evals_a_desc = [
        _evaluar_plan_prop(p, tr_map, fechas_nq, fric_nq, fric_mnq, "DESC", "contraida_60", 0.60, N=2500, seed=100 + idx)
        for idx, p in enumerate(planes_a)
    ]
    # Solo elegimos P_OPT o P_OPT_SF si gana estrictamente en neto12_medio sobre CORE_6 en DESC contraida_60
    gan_a = max(evals_a_desc, key=lambda r: (float(r["neto12_medio_usd"]), float(r["retiros_12m"])))
    cart_gan_a = str(gan_a["cartera"])

    # Evaluar las 24 pruebas definitivas bajo DESC y REP congelado, en real_100, contraida_60 y cero_0
    planes_24 = planes_etapa2_iter4(cart_gan_a)
    filas_24: list[dict[str, Any]] = []
    for p_idx, cfg_p in enumerate(planes_24):
        for part in ("DESC", "REP"):
            for cnom_r, cmult in (("real_100", 1.0), ("contraida_60", 0.60), ("cero_0", 0.0)):
                res = _evaluar_plan_prop(
                    cfg_p, tr_map, fechas_nq, fric_nq, fric_mnq, part, cnom_r, cmult,
                    N=3000, seed=300 + p_idx * 7,
                )
                filas_24.append(res)

    df_e2_all = pd.DataFrame(filas_24)
    df_e2_all.to_csv(OUT_DIR / "etapa2_ablacion_factores_prop.csv", index=False)

    # Tabla resumen pivot DESC vs REP para contraida_60 y real_100
    c60 = df_e2_all[df_e2_all["regimen_media"] == "contraida_60"]
    r100 = df_e2_all[df_e2_all["regimen_media"] == "real_100"]
    piv_d = c60[c60["particion_a5"] == "DESC"].set_index("plan_id")
    piv_r = c60[c60["particion_a5"] == "REP"].set_index("plan_id")
    r_d = r100[r100["particion_a5"] == "DESC"].set_index("plan_id")
    r_r = r100[r100["particion_a5"] == "REP"].set_index("plan_id")

    top_rows = []
    for pid in [p["plan_id"] for p in planes_24]:
        top_rows.append({
            "plan_id": pid,
            "bloque": piv_d.loc[pid, "bloque"],
            "palanca": piv_d.loc[pid, "palanca"],
            "cartera": piv_d.loc[pid, "cartera"],
            "tam": piv_d.loc[pid, "tam"],
            "desc_c60_neto12": piv_d.loc[pid, "neto12_medio_usd"],
            "desc_c60_neto24": piv_d.loc[pid, "neto24_medio_usd"],
            "desc_c60_p1ret12": piv_d.loc[pid, "p_primer_retiro_12m_pct"],
            "desc_c60_ret12": piv_d.loc[pid, "retiros_12m"],
            "desc_c60_tam_ret": piv_d.loc[pid, "tamano_medio_retiro_usd"],
            "desc_c60_cmin_p10": piv_d.loc[pid, "caja_min_p10_usd"],
            "rep_c60_neto12": piv_r.loc[pid, "neto12_medio_usd"],
            "rep_c60_neto24": piv_r.loc[pid, "neto24_medio_usd"],
            "rep_c60_p1ret12": piv_r.loc[pid, "p_primer_retiro_12m_pct"],
            "rep_c60_ret12": piv_r.loc[pid, "retiros_12m"],
            "rep_c60_tam_ret": piv_r.loc[pid, "tamano_medio_retiro_usd"],
            "rep_c60_p_pos12": piv_r.loc[pid, "p_neto12_pos_pct"],
            "rep_c60_cmin_p10": piv_r.loc[pid, "caja_min_p10_usd"],
            "desc_r100_neto12": r_d.loc[pid, "neto12_medio_usd"],
            "rep_r100_neto12": r_r.loc[pid, "neto12_medio_usd"],
            "rep_r100_ret12": r_r.loc[pid, "retiros_12m"],
        })

    df_top = pd.DataFrame(top_rows).sort_values("rep_c60_neto12", ascending=False).reset_index(drop=True)
    df_top.to_csv(OUT_DIR / "etapa2_planes_top_desc_vs_rep.csv", index=False)

    meta = {
        "elegidos_etapa1": elegidos,
        "cartera_ganadora_bloque_a_desc": cart_gan_a,
        "resumen_carteras_r": resumen_carteras,
        "pesos_w5_w3": pesos_meta,
    }
    return df_e2_all, df_top, meta


def graficar_iter4(
    df_e1: pd.DataFrame,
    df_rep: pd.DataFrame,
    df_e2_all: pd.DataFrame,
    df_top: pd.DataFrame,
) -> dict[str, Path]:
    """Genera 3 PNG oscuros con text.parse_math=False en OUT_DIR y los copia a ARTIFACTS_DIR."""
    if plt is None:
        raise RuntimeError("matplotlib requerido")
    plt.rcParams["text.parse_math"] = False
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rutas: dict[str, Path] = {}

    def _estilo(ax: Any) -> None:
        ax.set_facecolor("#11191c")
        ax.tick_params(colors="#b8c6cc", labelsize=8.2)
        for sp in ax.spines.values():
            sp.set_color("#2a373d")
        ax.grid(color="#202b30", alpha=0.6, linewidth=0.6)

    # PNG 1: Etapa 1 Top variantes (DESC t_ses vs Calmar) y comparativa DESC vs REP
    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(17.2, 7.8), facecolor="#0d1316")
    for ax in (ax1, ax2):
        _estilo(ax)

    sub1 = df_e1[df_e1["n_2020"] >= 30].sort_values("t_ses_2020", ascending=True).tail(20)
    y1 = np.arange(len(sub1))
    cols1 = ["#2ca693" if ok else "#587cc9" if r > 0 else "#c47068"
             for ok, r in zip(sub1["pasa_e1"], sub1["R_neto_2020"])]
    ax1.barh(y1, sub1["t_ses_2020"], color=cols1, height=0.64, alpha=0.92)
    for yi, (_, rr) in enumerate(sub1.iterrows()):
        ax1.text(max(float(rr["t_ses_2020"]), 0.0) + 0.07, yi,
                 f"R={rr['R_neto_2020']:+.3f} q={rr['q_bh']:.3f} Cal={rr['calmar']:.2f}",
                 va="center", color="#dce5ea", fontsize=7.0)
    ax1.axvline(1.96, color="#f0c954", linewidth=0.9, linestyle=":", label="t = 1.96")
    ax1.set_yticks(y1)
    ax1.set_yticklabels(sub1["variante"], fontsize=7.6)
    ax1.set_xlim(0.0, max(float(sub1["t_ses_2020"].max()), 3.0) + 2.3)
    ax1.set_xlabel("t-stat por sesion (NQ DESC POST_2020)", color="#d0dce2")
    ax1.set_title("Etapa 1: Top 20 factores de edge en NQ DESC (B=5000, q<0.05 verde)", color="#edf4f7", fontsize=10.5)
    ax1.legend(loc="lower right", frameon=True, facecolor="#11191c", edgecolor="#2a373d", labelcolor="#dce5ea", fontsize=8)

    sub_r = df_rep.sort_values("calmar_desc_20", ascending=True).tail(18)
    yr = np.arange(len(sub_r))
    ax2.barh(yr - 0.17, sub_r["R_mes_desc_20"], height=0.32, color="#3baeb8", alpha=0.88, label="DESC (46m)")
    ax2.barh(yr + 0.17, sub_r["R_mes_rep_20"], height=0.32, color="#f0c954", alpha=0.88, label="REP congelado (14m)")
    ax2.axvline(0.0, color="#9ab0ba", linewidth=0.85, linestyle="--")
    ax2.set_yticks(yr)
    ax2.set_yticklabels(sub_r["variante"], fontsize=7.5)
    ax2.set_xlabel("Expectativa mensual (R/mes mini)", color="#d0dce2")
    ax2.set_title("Confirmacion congelada DESC vs REP (top + anclas por grilla)", color="#edf4f7", fontsize=10.5)
    ax2.legend(loc="lower right", frameon=True, facecolor="#11191c", edgecolor="#2a373d", labelcolor="#dce5ea", fontsize=8)

    fig1.tight_layout()
    p1 = OUT_DIR / "prop_opt_etapa1_factores_edge.png"
    fig1.savefig(p1, dpi=150, facecolor=fig1.get_facecolor())
    plt.close(fig1)
    rutas["etapa1"] = p1

    # PNG 2: Ablacion de palancas Prop Firm (Neto 12m + retiros_12m en contraida_60, DESC vs REP)
    fig2, (bx1, bx2) = plt.subplots(1, 2, figsize=(17.6, 8.2), facecolor="#0d1316")
    for ax in (bx1, bx2):
        _estilo(ax)

    ord_p = df_top.sort_values("rep_c60_neto12", ascending=True).reset_index(drop=True)
    yp = np.arange(len(ord_p))
    bx1.barh(yp - 0.18, ord_p["desc_c60_neto12"] / 1000.0, height=0.34, color="#3baeb8", alpha=0.85, label="DESC contr_60")
    bx1.barh(yp + 0.18, ord_p["rep_c60_neto12"] / 1000.0, height=0.34, color="#2ca693", alpha=0.92, label="REP contr_60")
    bx1.axvline(0.0, color="#c47068", linewidth=0.9, linestyle="--")
    bx1.set_yticks(yp)
    bx1.set_yticklabels([f"{r['plan_id']} ({r['palanca']})" for _, r in ord_p.iterrows()], fontsize=7.2)
    bx1.set_xlabel("Caja neta media 12 meses (miles USD)", color="#d0dce2")
    bx1.set_title("Ablacion Prop Firm (24 pruebas): Neto medio 12m (media contraida 60%)", color="#edf4f7", fontsize=10.5)
    bx1.legend(loc="lower right", frameon=True, facecolor="#11191c", edgecolor="#2a373d", labelcolor="#dce5ea", fontsize=8)

    bx2.barh(yp - 0.18, ord_p["rep_c60_ret12"], height=0.34, color="#f0c954", alpha=0.90, label="Retiros medios 12m (REP 60%)")
    bx2.barh(yp + 0.18, ord_p["rep_c60_tam_ret"] / 500.0, height=0.34, color="#8b7ed8", alpha=0.85, label="Tamano retiro / $500 (REP 60%)")
    for yi, (_, rr) in enumerate(ord_p.iterrows()):
        bx2.text(max(float(rr["rep_c60_ret12"]), float(rr["rep_c60_tam_ret"]) / 500.0) + 0.15, yi,
                 f"P(ret)={rr['rep_c60_p1ret12']:.0f}% | ${rr['rep_c60_tam_ret']:.0f}",
                 va="center", color="#dce5ea", fontsize=6.9)
    bx2.set_yticks(yp)
    bx2.set_yticklabels(["" for _ in yp])
    bx2.set_xlim(0.0, max(float(ord_p["rep_c60_ret12"].max()), float(ord_p["rep_c60_tam_ret"].max()) / 500.0, 5.0) + 4.8)
    bx2.set_xlabel("Cantidad de retiros 12m / Escala de monto por retiro", color="#d0dce2")
    bx2.set_title("Frecuencia y tamano medio por retiro en REP congelado (60%)", color="#edf4f7", fontsize=10.5)
    bx2.legend(loc="lower right", frameon=True, facecolor="#11191c", edgecolor="#2a373d", labelcolor="#dce5ea", fontsize=8)

    fig2.tight_layout()
    p2 = OUT_DIR / "prop_opt_etapa2_ablacion_palancas.png"
    fig2.savefig(p2, dpi=150, facecolor=fig2.get_facecolor())
    plt.close(fig2)
    rutas["ablacion"] = p2

    # PNG 3: Frontera riesgo/retiros (|caja_min_p10| vs neto12_medio en DESC y REP, contraida_60)
    fig3, (cx1, cx2) = plt.subplots(1, 2, figsize=(16.5, 6.8), facecolor="#0d1316")
    for ax in (cx1, cx2):
        _estilo(ax)

    c60 = df_e2_all[df_e2_all["regimen_media"] == "contraida_60"].copy()
    for ax_c, part_n in ((cx1, "DESC"), (cx2, "REP")):
        sub_p = c60[c60["particion_a5"] == part_n].copy()
        xr = np.abs(sub_p["caja_min_p10_usd"].to_numpy(float)) / 1000.0
        yr_v = sub_p["neto12_medio_usd"].to_numpy(float) / 1000.0
        sz = np.clip(sub_p["retiros_12m"].to_numpy(float) * 26.0, 45.0, 480.0)
        sc = ax_c.scatter(xr, yr_v, s=sz, c=sub_p["p_primer_retiro_12m_pct"].to_numpy(float),
                          cmap="viridis", vmin=40.0, vmax=100.0, alpha=0.88, edgecolors="#e6eef2", linewidth=0.7)
        lbs_df = pd.concat([
            sub_p.sort_values("neto12_medio_usd", ascending=False).head(8).assign(_star=False),
            sub_p[sub_p["plan_id"].isin(("A01_150K_CORE6_MNQ_base", "A05_50K_CORE6_MNQ_base"))].assign(_star=True),
        ], ignore_index=True).drop_duplicates(subset=["plan_id"])
        span_x = max(float(xr.max() - xr.min()), 1.0)
        span_y = max(float(yr_v.max() - yr_v.min()), 1.0)
        puestos: list[tuple[float, float]] = []
        offs = ((0.03, 0.04), (0.03, -0.06), (-0.09, 0.05), (-0.09, -0.06), (0.06, 0.09), (0.06, -0.10))
        for _, rr in lbs_df.iterrows():
            px = abs(float(rr["caja_min_p10_usd"])) / 1000.0
            py = float(rr["neto12_medio_usd"]) / 1000.0
            lbl = str(rr["plan_id"]).split("_", 1)[0] + ("*" if bool(rr["_star"]) else "")
            col_l = "#f09080" if bool(rr["_star"]) else "#e6eef2"
            tx, ty = px + 0.03 * span_x, py + 0.04 * span_y
            for ox, oy in offs:
                cx, cy = px + ox * span_x, py + oy * span_y
                if all(abs(cx - ux) > 0.08 * span_x or abs(cy - uy) > 0.06 * span_y for ux, uy in puestos):
                    tx, ty = cx, cy
                    break
            puestos.append((tx, ty))
            ax_c.annotate(
                lbl, xy=(px, py), xytext=(tx, ty), color=col_l, fontsize=7.3, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color="#7d8f96", lw=0.7, alpha=0.8),
            )
        ax_c.axhline(0.0, color="#c47068", linewidth=0.85, linestyle="--")
        ax_c.set_xlabel("|Capital requerido p10| (|caja minima p10|, miles USD)", color="#d0dce2")
        ax_c.set_ylabel("Caja neta media 12m (miles USD)", color="#d0dce2")
        ax_c.set_title(f"Frontera LucidFlex {part_n} (contraida 60%, tamano = retiros_12m)", color="#edf4f7", fontsize=10.2)
        cbar = fig3.colorbar(sc, ax=ax_c, fraction=0.04, pad=0.02)
        cbar.set_label("P(>= 1 retiro en 12m) %", color="#d0dce2", fontsize=8)
        cbar.ax.tick_params(colors="#b8c6cc", labelsize=7.5)

    fig3.tight_layout()
    p3 = OUT_DIR / "prop_opt_etapa2_frontera_retiros.png"
    fig3.savefig(p3, dpi=150, facecolor=fig3.get_facecolor())
    plt.close(fig3)
    rutas["frontera"] = p3

    if ARTIFACTS_DIR.exists():
        for sp_p in rutas.values():
            shutil.copy2(sp_p, ARTIFACTS_DIR / sp_p.name)
    return rutas


def ejecutar_iter4(etapa: str = "todo", m1_dir: Path | None = None, workers: int = 2) -> dict[str, Any]:
    """Orquestador principal de Iteracion 4 (compuerta K51 -> Etapa 1 -> Etapa 2 -> Graficos)."""
    asegurar_compuerta_iter4()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if etapa == "graficos":
        df_e1 = pd.read_csv(OUT_DIR / "etapa1_factores_edge.csv")
        df_rep = pd.read_csv(OUT_DIR / "etapa1_confirmacion_rep.csv")
        df_e2_all = pd.read_csv(OUT_DIR / "etapa2_ablacion_factores_prop.csv")
        df_top = pd.read_csv(OUT_DIR / "etapa2_planes_top_desc_vs_rep.csv")
        graficar_iter4(df_e1, df_rep, df_e2_all, df_top)
        return {"df_e1": df_e1, "df_rep": df_rep, "df_e2_all": df_e2_all, "df_top": df_top}

    atr_nq, _, pv_nq, start_nq = BASE._cargar_series_sesion("NQ", m1_dir=m1_dir)
    orb_raw_nq = IT2._cargar_orb_raw("NQ", m1_dir=m1_dir)
    fechas_nq = IT2._cargar_fechas_a5_inst("NQ", m1_dir=m1_dir)
    m1_arrays = cargar_m1_arrays_nq(m1_dir=m1_dir)

    df_e1, df_rep, diags, ops_map = _correr_etapa1(
        atr_nq, orb_raw_nq, pv_nq, start_nq, fechas_nq["DESC"], m1_arrays, workers=workers, m1_dir=m1_dir
    )
    print("\n=== ETAPA 1 TOP 20 POR t_ses_2020 (NQ DESC POST_2020) ===")
    c1 = ["grilla", "variante", "n_2020", "ops_mes_2020", "R_neto_2020", "R_mes_2020", "dd_R", "calmar", "p_perm", "q_bh", "pasa_e1"]
    print(df_e1.sort_values("t_ses_2020", ascending=False)[c1].head(20).to_string(index=False))
    print("\n=== ETAPA 1 CONFIRMACION REP CONGELADA ===")
    print(df_rep[["modulo", "variante", "R_mes_desc_20", "calmar_desc_20", "n_rep_20", "R_rep_20", "R_mes_rep_20", "calmar_rep_20", "confirma_rep"]].to_string(index=False))

    if etapa == "etapa1":
        return {"df_e1": df_e1, "df_rep": df_rep, "diags": diags}

    df_e2_all, df_top, meta = _correr_etapa2(df_e1, ops_map, fechas_nq)
    print("\n=== ETAPA 2 ABLACION PROP FIRM (ORDENADO POR REP contr_60) ===")
    print(df_top[["plan_id", "palanca", "desc_c60_neto12", "desc_c60_ret12", "desc_c60_tam_ret", "rep_c60_neto12", "rep_c60_p1ret12", "rep_c60_ret12", "rep_c60_tam_ret", "rep_c60_cmin_p10"]].to_string(index=False))

    rutas = graficar_iter4(df_e1, df_rep, df_e2_all, df_top)
    resumen = {
        "n_etapa1": int(len(df_e1)),
        "n_etapa2_planes": int(len(df_top)),
        "diagnosticos": diags,
        "elegidos_etapa1": meta["elegidos_etapa1"],
        "cartera_ganadora_bloque_a_desc": meta["cartera_ganadora_bloque_a_desc"],
        "resumen_carteras_r": meta["resumen_carteras_r"],
        "pesos_w5_w3": meta["pesos_w5_w3"],
        "graficos": {k: str(v.relative_to(ROOT).as_posix()) for k, v in rutas.items()},
    }
    (OUT_DIR / "resumen_prop_opt.json").write_text(json.dumps(resumen, indent=2, default=str), encoding="utf-8")
    return {"df_e1": df_e1, "df_rep": df_rep, "df_e2_all": df_e2_all, "df_top": df_top, "resumen": resumen}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Iteracion 4 FUNDEDSYNC: Factores de edge y optimizacion prop firm LucidFlex.")
    ap.add_argument("etapa", nargs="?", default="todo", choices=("etapa1", "etapa2", "todo", "graficos"))
    ap.add_argument("--workers", type=int, default=2, help="Workers paralelos (default 2)")
    args = ap.parse_args(argv)
    ejecutar_iter4(etapa=args.etapa, workers=args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

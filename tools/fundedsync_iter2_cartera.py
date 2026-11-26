#!/usr/bin/env python3
"""Iteracion 2 FUNDEDSYNC: V1 robustez, V2 rescate, bateria de permutaciones y cartera ponderada.

Uso:
  python tools/fundedsync_iter2_cartera.py etapa1 [--workers 2]
  python tools/fundedsync_iter2_cartera.py etapa2 [--workers 2]
  python tools/fundedsync_iter2_cartera.py etapa3_4 [--workers 2]
  python tools/fundedsync_iter2_cartera.py todo [--workers 2]
"""
from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import gc
import json
import math
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

import numpy as np
import pandas as pd

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

import fundedsync_post_il_cadena as BASE
import lucid_guia as LG
from edgelab import costos
from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS, a5_bloque
from edgelab.research import diagnostico_grilla as DG
from edgelab.research.fundedsyncstack import CONFIG_CLASSES
from edgelab.research.m1_intradia import leer_m1nt8
from edgelab.research.puerta_corrida import verificar_corrida
from m1_largo import _sesion
from registro_global import exigir_contada

PREREG_REL = "docs/research/fundedsync_iter2_cartera_20261122/PREREGISTRO.md"
OUT_DIR = ROOT / "docs/research/fundedsync_iter2_cartera_20261122"
CACHE_DIR = BASE.CACHE_DIR
ARTIFACTS_DIR = BASE.ARTIFACTS_DIR


def asegurar_compuerta_iter2() -> None:
    """Verifica K51 y compuerta L1..L4 para PREREGISTRO de iteracion 2."""
    exigir_contada(PREREG_REL)
    rep = verificar_corrida(
        prereg=PREREG_REL,
        familia="FUNDEDSYNC",
        exigir_contada=True,
        verificar_estado=True,
        root=ROOT,
    )
    if not rep["ok"]:
        raise SystemExit("puerta_corrida bloqueo iter2: " + "; ".join(rep["errores"]))


def friccion_iter2(inst: str) -> tuple[float, float | None]:
    """Devuelve `(friccion_mini_pts, friccion_micro_pts)` bajo `PREREG_REL` (K33)."""
    sym = inst.upper()
    with costos.estimados_permitidos(PREREG_REL):
        fric_mini = float(costos.friccion_rt_puntos(sym, "base"))
        mic = BASE.MICRO_EQUIV.get(sym)
        fric_micro = float(costos.friccion_rt_puntos(mic, "base")) if mic else None
    return fric_mini, fric_micro


def _cargar_orb_raw(inst: str, m1_dir: Path | None = None, desde: str = "2008-01-01") -> pd.Series:
    """Carga rango ORB15 (09:30-09:45 ET) sin recorte para evaluar `stop_orb_multiplier` en `T`."""
    d_ny = leer_m1nt8(BASE._resolver_parquet(inst, m1_dir=m1_dir))
    d_ny = d_ny[d_ny.index >= desde]
    mm = d_ny.index.hour * 60 + d_ny.index.minute
    orb = d_ny[(mm >= 570) & (mm < 585)]
    dd = orb.index.normalize()
    rng = orb.h.groupby(dd).max() - orb.l.groupby(dd).min()
    del d_ny, orb, dd, mm
    gc.collect()
    return rng


def _cargar_fechas_a5_inst(inst: str, m1_dir: Path | None = None, desde: str = "2020-01-01") -> dict[str, list[int]]:
    """Devuelve sesiones reales del parquet clasificadas en `DESC` y `REP` (>= desde, < A4)."""
    d_ny = leer_m1nt8(BASE._resolver_parquet(inst, m1_dir=m1_dir))
    fechas_un = pd.DatetimeIndex(d_ny[d_ny.index >= desde].index.normalize().unique())
    del d_ny
    gc.collect()
    out: dict[str, list[int]] = {"DESC": [], "REP": []}
    for dt in fechas_un:
        f = int(dt.strftime("%Y%m%d"))
        b = a5_bloque(f)
        if b in out:
            out[b].append(f)
    return out


def _empty_ops_enr() -> pd.DataFrame:
    return pd.DataFrame({
        "fecha_int": pd.Series(dtype="int64"),
        "mes": pd.Series(dtype="object"),
        "a5": pd.Series(dtype="object"),
        "en_ns": pd.Series(dtype="int64"),
        "ex_ns": pd.Series(dtype="int64"),
        "dur_min": pd.Series(dtype="float64"),
        "pnl_pts": pd.Series(dtype="float64"),
        "mae_pts": pd.Series(dtype="float64"),
        "mfe_pts": pd.Series(dtype="float64"),
        "riesgo_pts": pd.Series(dtype="float64"),
        "R_bruto": pd.Series(dtype="float64"),
        "R_neto_mini": pd.Series(dtype="float64"),
        "R_neto_micro": pd.Series(dtype="float64"),
        "fric_R": pd.Series(dtype="float64"),
        "side": pd.Series(dtype="int64"),
    })


def convertir_ops_enriquecidas(
    df_trades: pd.DataFrame,
    modulo: str,
    inst: str,
    atr_ses: pd.Series,
    orb_raw: pd.Series,
    pv_base: float,
    *,
    stop_atr_k: float | None = None,
    cap_mae_atr_k: float | None = None,
    stop_orb_mult: float = 1.25,
) -> pd.DataFrame:
    """Convierte trades a unidad `R` anadiendo timestamps exactos, duracion y MFE/MAE."""
    if df_trades is None or len(df_trades) == 0:
        return _empty_ops_enr()

    en_utc = pd.to_datetime(df_trades["entry_time_utc"], utc=True)
    ex_utc = pd.to_datetime(df_trades["exit_time_utc"], utc=True)
    tt_ny = en_utc.dt.tz_convert("America/New_York").dt.tz_localize(None)
    ses = _sesion(pd.DatetimeIndex(tt_ny))
    atr_vec = atr_ses.reindex(ses).to_numpy(dtype=float)

    pp = pd.to_numeric(df_trades["pnl_pts"], errors="coerce").to_numpy(dtype=float)
    pu = pd.to_numeric(df_trades["pnl_usd"], errors="coerce").to_numpy(dtype=float)
    qt = pd.to_numeric(df_trades["qty"], errors="coerce").abs().replace(0, np.nan).to_numpy(dtype=float)
    mae_u = pd.to_numeric(df_trades["mae_usd"], errors="coerce").abs().to_numpy(dtype=float)
    mfe_u = pd.to_numeric(df_trades["mfe_usd"], errors="coerce").abs().to_numpy(dtype=float)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio_pv = np.abs(pu) / (np.abs(pp) * qt)
    finite_pv = ratio_pv[np.isfinite(ratio_pv) & (ratio_pv > 0)]
    pv_unit = float(np.median(finite_pv)) if len(finite_pv) else (
        float(pv_base / 10.0) if modulo == "Q" else float(pv_base)
    )
    mae_pts = mae_u / np.maximum(qt * pv_unit, 1e-9)
    mfe_pts = mfe_u / np.maximum(qt * pv_unit, 1e-9)

    en_px = pd.to_numeric(df_trades["entry_price"], errors="coerce").to_numpy(dtype=float)
    st_px = pd.to_numeric(df_trades["stop_price"], errors="coerce").to_numpy(dtype=float)
    nat_stop = np.abs(en_px - st_px)

    if modulo == "T":
        orb_vec = (orb_raw.reindex(pd.DatetimeIndex(tt_ny).normalize()) * float(stop_orb_mult)).clip(2.0, 100.0).to_numpy(dtype=float)
        nat_stop = np.where(np.isfinite(orb_vec) & (orb_vec > 0), orb_vec, nat_stop)

    if stop_atr_k is not None:
        riesgo = float(stop_atr_k) * atr_vec
        pnl_eff = np.where(mae_pts >= riesgo, -riesgo, pp)
    elif cap_mae_atr_k is not None:
        cap_pts = float(cap_mae_atr_k) * atr_vec
        riesgo = np.where(np.isfinite(nat_stop) & (nat_stop > 0), np.minimum(nat_stop, cap_pts), cap_pts)
        pnl_eff = np.where(mae_pts >= cap_pts, -cap_pts, pp)
    else:
        riesgo = np.where(np.isfinite(nat_stop) & (nat_stop > 0), nat_stop, 0.5 * atr_vec)
        pnl_eff = pp

    ok = np.isfinite(riesgo) & (riesgo > 1e-6) & np.isfinite(pnl_eff)
    fecha_int = pd.DatetimeIndex(ses).strftime("%Y%m%d").astype(int)
    a5_labels = np.array([a5_bloque(int(f)) for f in fecha_int], dtype=object)
    ok = ok & (a5_labels != "TERMINAL")
    if not ok.any():
        return _empty_ops_enr()

    fric_mini, fric_micro = friccion_iter2(inst)
    riesgo_k = riesgo[ok]
    pnl_k = pnl_eff[ok]
    r_bruto = pnl_k / riesgo_k
    r_mini = (pnl_k - fric_mini) / riesgo_k
    r_micro = ((pnl_k - fric_micro) / riesgo_k) if fric_micro is not None else np.full_like(r_mini, np.nan)
    dur_min = ((ex_utc - en_utc).dt.total_seconds() / 60.0).to_numpy(dtype=float)[ok]

    return pd.DataFrame({
        "fecha_int": fecha_int[ok],
        "mes": pd.DatetimeIndex(ses)[ok].strftime("%Y-%m"),
        "a5": a5_labels[ok],
        "en_ns": en_utc.astype("int64").to_numpy()[ok],
        "ex_ns": ex_utc.astype("int64").to_numpy()[ok],
        "dur_min": dur_min,
        "pnl_pts": pnl_k,
        "mae_pts": mae_pts[ok],
        "mfe_pts": mfe_pts[ok],
        "riesgo_pts": riesgo_k,
        "R_bruto": r_bruto,
        "R_neto_mini": r_mini,
        "R_neto_micro": r_micro,
        "fric_R": fric_mini / riesgo_k,
        "side": df_trades["side"].to_numpy(dtype=int)[ok],
    })


def _grillas_iter2() -> list[dict[str, Any]]:
    """Presupuesto exacto PREREGISTRO: 23 variantes V1 + 22 variantes V2 = 45 variantes."""
    specs: list[dict[str, Any]] = []

    def _add(grilla: str, mod: str, var: str, params: dict[str, Any], *, stop_atr_k: float | None = None,
             cap_mae_atr_k: float | None = None, stop_orb_mult: float = 1.25, perillas: dict[str, str], bloque: str) -> None:
        specs.append({
            "bloque": bloque, "grilla": grilla, "modulo": mod, "variante": var,
            "params": params, "stop_atr_k": stop_atr_k, "cap_mae_atr_k": cap_mae_atr_k,
            "stop_orb_mult": stop_orb_mult, "perillas": perillas,
        })

    # --- V1 (23 variantes) ---
    for mod in ("R", "Z"):
        for k_atr in (0.20, 0.25, 0.35, 0.50):
            _add("V1_RZ", mod, f"{mod}_maeATR{int(round(k_atr*100))}", {}, stop_atr_k=k_atr,
                 perillas={"mod": mod, "stop_atr": str(k_atr)}, bloque="V1")

    w_filtros = {
        "slope": {"exit_on_vwap_cross": False, "allow_reentries": False, "use_vwap_slope_filter": True},
        "conf2": {"exit_on_vwap_cross": False, "allow_reentries": False, "use_confirmation_filter": True, "confirmation_bars": 2},
        "dist4": {"exit_on_vwap_cross": False, "allow_reentries": False, "use_vwap_distance_filter": True, "minimum_vwap_distance_ticks": 4.0},
    }
    for fn, fparams in w_filtros.items():
        for k_atr in (0.25, 0.35, 0.50):
            _add("V1_W", "W", f"W_eod_{fn}_ATR{int(round(k_atr*100))}", fparams, stop_atr_k=k_atr,
                 perillas={"filtro": fn, "stop_atr": str(k_atr)}, bloque="V1")

    v_nm30 = {"noise_multiplier": 0.30, "vwap_exit_bars": 2, "profit_target_usd_per_contract": 1400.0}
    for k_ov in (0.30, 0.40, 0.50):
        _add("V1_VT", "V", f"V_nm30_maeATR{int(round(k_ov*100))}", v_nm30, cap_mae_atr_k=k_ov,
             perillas={"mod": "V", "nivel": f"atr_{k_ov}"}, bloque="V1")
    _add("V1_VT", "V", "V_nm30_sl1200", {**v_nm30, "stop_loss_usd_per_contract": 1200.0},
         perillas={"mod": "V", "nivel": "sl_1200"}, bloque="V1")
    _add("V1_VT", "T", "T_stop100", {"stop_orb_multiplier": 1.0}, stop_orb_mult=1.0,
         perillas={"mod": "T", "nivel": "orb_1.0"}, bloque="V1")
    _add("V1_VT", "T", "T_stop150", {"stop_orb_multiplier": 1.5}, stop_orb_mult=1.5,
         perillas={"mod": "T", "nivel": "orb_1.5"}, bloque="V1")

    # --- V2 (22 variantes) ---
    for hs in (3.0, 5.0):
        _add("V2_ABSORB", "A1", f"A1_short_hs{int(hs*10)}",
             {"allow_longs": False, "allow_shorts": True, "hard_stop_atr_mult": hs},
             perillas={"mod": "A1", "nivel": f"short_hs{hs}"}, bloque="V2")
    _add("V2_ABSORB", "A20", "A20_fab", {}, perillas={"mod": "A20", "nivel": "fab"}, bloque="V2")
    _add("V2_ABSORB", "A20", "A20_stAlign", {"require_supertrend_entry_alignment": True},
         perillas={"mod": "A20", "nivel": "stAlign"}, bloque="V2")
    _add("V2_ABSORB", "A20", "A20_hs25", {"hard_stop_atr_mult": 2.5},
         perillas={"mod": "A20", "nivel": "hs25"}, bloque="V2")
    _add("V2_ABSORB", "A20", "A20_stAlign_hs25", {"require_supertrend_entry_alignment": True, "hard_stop_atr_mult": 2.5},
         perillas={"mod": "A20", "nivel": "stAlign_hs25"}, bloque="V2")

    f_grid = (
        (2.0, False, 0.0, "F_tp2_d1_a0"),
        (99.0, False, 0.0, "F_tp99_d1_a0"),
        (2.0, True, 0.0, "F_tp2_d0_a0"),
        (99.0, True, 0.0, "F_tp99_d0_a0"),
        (99.0, False, 5.0, "F_tp99_d1_a5"),
        (99.0, False, 8.0, "F_tp99_d1_a8"),
    )
    for tpr, d_off, ra, tag in f_grid:
        _add("V2_ORB_PB", "F", tag, {"tp_rr": tpr, "disable_delta_filter": d_off, "max_initial_risk_atr": ra},
             perillas={"mod": "F", "nivel": tag}, bloque="V2")
    for mrr, sw in ((1.0, 5), (1.5, 10), (2.0, 15)):
        _add("V2_ORB_PB", "P", f"P_rr{int(mrr*10)}_sw{sw}", {"minimum_reward_risk": mrr, "target_swing_length": sw},
             perillas={"mod": "P", "nivel": f"rr{mrr}_sw{sw}"}, bloque="V2")

    _add("V2_GAP_SWEEP_N", "C", "C_both_150", {"enable_short_entries": True},
         perillas={"mod": "C", "nivel": "both_150"}, bloque="V2")
    _add("V2_GAP_SWEEP_N", "C", "C_long_60", {"entry_start_offset_minutes": 60},
         perillas={"mod": "C", "nivel": "long_60"}, bloque="V2")
    _add("V2_GAP_SWEEP_N", "C", "C_both_60", {"enable_short_entries": True, "entry_start_offset_minutes": 60},
         perillas={"mod": "C", "nivel": "both_60"}, bloque="V2")
    _add("V2_GAP_SWEEP_N", "S", "S_stAlign", {"require_supertrend_entry_alignment": True}, stop_atr_k=0.50,
         perillas={"mod": "S", "nivel": "stAlign"}, bloque="V2")
    _add("V2_GAP_SWEEP_N", "S", "S_stAlign_Sonly", {"require_supertrend_entry_alignment": True, "allow_longs": False}, stop_atr_k=0.50,
         perillas={"mod": "S", "nivel": "stAlign_S"}, bloque="V2")
    for ka in (0.25, 0.35):
        _add("V2_GAP_SWEEP_N", "N", f"N_fab_maeATR{int(round(ka*100))}", {}, stop_atr_k=ka,
             perillas={"mod": "N", "nivel": f"atr_{ka}"}, bloque="V2")

    return specs


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(float(x) / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Inversa normal estandar (aproximacion racional Peter J. Acklam, sin SciPy)."""
    p = min(max(float(p), 1e-12), 1.0 - 1e-12)
    a = (-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
         1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00)
    b = (-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
         6.680131188771972e01, -1.328068155288572e01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
         -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00, 3.754408661907416e00)
    plow, phigh = 0.02425, 1.0 - 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)
    if p > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q / (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1.0)


def _benjamini_hochberg(pvals: np.ndarray) -> np.ndarray:
    """Ajuste Benjamini-Hochberg (q-valor monotono) en orden original."""
    m = len(pvals)
    if m == 0:
        return np.array([], dtype=float)
    order = np.argsort(pvals, kind="mergesort")
    ranked = pvals[order]
    q_raw = ranked * m / np.arange(1, m + 1, dtype=float)
    q_mon = np.minimum(1.0, np.minimum.accumulate(q_raw[::-1])[::-1])
    out = np.empty(m, dtype=float)
    out[order] = q_mon
    return out


def calcular_bateria_permutaciones(
    series_por_var: Mapping[str, pd.Series],
    fechas_calendario: list[int],
    n_eff: float,
    *,
    n_perm: int = 5000,
    bloque_dias: int = 5,
    seed: int = 20261122,
) -> pd.DataFrame:
    """Permutaciones sincronizadas por bloque de 5 dias (p_perm, q_BH, White maxT y DSR)."""
    vars_list = list(series_por_var.keys())
    idx = pd.Index(sorted(fechas_calendario), dtype=int)
    n_cal = len(idx)
    n_var = len(vars_list)
    mat = np.zeros((n_cal, n_var), dtype=float)
    active = np.zeros((n_cal, n_var), dtype=bool)

    for j, v in enumerate(vars_list):
        s = series_por_var[v]
        if len(s):
            s_al = s.reindex(idx)
            is_act = s_al.notna().to_numpy()
            active[:, j] = is_act
            mat[:, j] = s_al.fillna(0.0).to_numpy(dtype=float)

    n_act = np.maximum(active.sum(axis=0), 1)
    sum_sq = (mat ** 2).sum(axis=0)
    t_obs = np.zeros(n_var, dtype=float)
    dsr_arr = np.zeros(n_var, dtype=float)
    gamma = 0.5772156649015329
    neff_safe = max(float(n_eff), 2.0)
    z1 = _norm_ppf(1.0 - 1.0 / neff_safe)
    z2 = _norm_ppf(1.0 - 1.0 / (neff_safe * math.e))
    sr0 = ((1.0 - gamma) * z1 + gamma * z2) / math.sqrt(max(n_cal, 2))

    for j in range(n_var):
        na = int(n_act[j])
        if na >= 3:
            v_act = mat[active[:, j], j]
            sd = float(np.std(v_act, ddof=1))
            t_obs[j] = float(np.mean(v_act) / sd * math.sqrt(na)) if sd > 1e-12 else 0.0
        col = mat[:, j]
        sd_cal = float(np.std(col, ddof=1)) if n_cal >= 3 else 0.0
        if sd_cal > 1e-12 and n_cal >= 10:
            z = (col - np.mean(col)) / sd_cal
            sr = float(np.mean(col) / sd_cal)
            skew = float(np.mean(z ** 3))
            kurt = float(np.mean(z ** 4))
            denom = max(1.0 - skew * sr + max((kurt - 1.0) / 4.0, 0.0) * (sr ** 2), 1e-6)
            dsr_arr[j] = _norm_cdf((sr - sr0) * math.sqrt(n_cal - 1) / math.sqrt(denom))

    # Permutacion exacta sobre bloques de sesiones conservando covarianza y autocorrelacion
    n_blk = (n_cal + bloque_dias - 1) // bloque_dias
    pad = n_blk * bloque_dias - n_cal
    mat_pad = np.vstack([mat, np.zeros((pad, n_var))]) if pad > 0 else mat
    b_sum = mat_pad.reshape(n_blk, bloque_dias, n_var).sum(axis=1)

    rng = np.random.default_rng(seed)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(int(n_perm), n_blk))
    sums_perm = signs @ b_sum  # (n_perm, n_var)
    means_perm = sums_perm / n_act[None, :]
    vars_perm = np.maximum((sum_sq[None, :] - n_act[None, :] * (means_perm ** 2)) / np.maximum(n_act[None, :] - 1.0, 1.0), 1e-18)
    t_perm = np.where(n_act[None, :] >= 3, means_perm / np.sqrt(vars_perm / n_act[None, :]), 0.0)

    p_perm = (1.0 + np.sum(t_perm >= t_obs[None, :], axis=0)) / (int(n_perm) + 1.0)
    max_t_perm = np.max(t_perm, axis=1)
    p_maxt = np.array([(1.0 + np.sum(max_t_perm >= float(to))) / (int(n_perm) + 1.0) for to in t_obs])
    q_bh = _benjamini_hochberg(p_perm)

    return pd.DataFrame({
        "variante": vars_list,
        "t_ses_perm": np.round(t_obs, 3),
        "p_perm": np.round(p_perm, 4),
        "q_bh": np.round(q_bh, 4),
        "p_maxT": np.round(p_maxt, 4),
        "DSR": np.round(dsr_arr, 4),
    })


def _precalentar_jobs(
    inst: str,
    jobs: list[tuple[str, str, dict[str, Any]]],
    *,
    workers: int = 2,
    m1_dir: Path | None = None,
) -> None:
    pend = sorted(
        [j for j in jobs if not (CACHE_DIR / f"{j[0]}.pkl").exists()],
        key=lambda j: (-BASE._PESO_MOD_ORDEN.get(j[1], 20), j[0]),
    )
    if not pend:
        print(f"[CACHE] Todos los jobs de {inst} ya estan en disco.", flush=True)
        return
    n_w = min(max(int(workers), 1), len(pend))
    print(f"[{inst}] Simulando {len(pend)} jobs faltantes con workers={n_w}...", flush=True)
    m1_str = str(m1_dir) if m1_dir is not None else None
    t0 = time.perf_counter()
    if n_w == 1:
        ms = BASE._cargar_ms_futuro(inst, m1_dir=m1_dir)
        for i, (cname, mod, params) in enumerate(pend, 1):
            _, n_tr, dt = BASE._ejecutar_job_con_ms(cname, mod, params, ms)
            print(f"  [{inst} {i}/{len(pend)}] {cname}: n={n_tr} ({dt:.1f}s)", flush=True)
        del ms
        gc.collect()
    else:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=n_w,
            initializer=BASE._init_worker_inst,
            initargs=(inst, m1_str),
        ) as ex:
            for i, (cname, n_tr, dt) in enumerate(ex.map(BASE._run_job_en_worker, pend), 1):
                print(f"  [{inst} {i}/{len(pend)}] {cname}: n={n_tr} ({dt:.1f}s)", flush=True)
    print(f"[{inst}] Simulaciones listas en {time.perf_counter() - t0:.1f}s.", flush=True)


def _metricas_dd_r(ops: pd.DataFrame, meses_tot: int) -> dict[str, Any]:
    if len(ops) == 0:
        return {"dd_R": np.nan, "calmar": np.nan, "dur_med_min": np.nan, "worst_day_R": np.nan}
    eq = ops.sort_values("en_ns")["R_neto_mini"].cumsum().to_numpy(dtype=float)
    dd = float((eq - np.maximum.accumulate(eq)).min())
    por_dia = ops.groupby("fecha_int")["R_neto_mini"].sum()
    r_anual = float(ops["R_neto_mini"].sum() / max(meses_tot, 1) * 12.0)
    calmar = round(r_anual / max(abs(dd), 0.1), 2) if abs(dd) > 0 else np.nan
    return {
        "dd_R": round(dd, 2),
        "calmar": calmar,
        "dur_med_min": round(float(ops["dur_min"].median()), 1),
        "worst_day_R": round(float(por_dia.min()), 2),
    }


def _correr_etapa1(
    atr_nq: pd.Series,
    orb_raw_nq: pd.Series,
    pv_nq: float,
    start_nq: int,
    fechas_desc_20: list[int],
    *,
    workers: int = 2,
    m1_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, pd.DataFrame]]:
    """Corre V1+V2 en NQ A5 DESC, ejecuta K55/K56 y bateria de 5.000 permutaciones."""
    specs = _grillas_iter2()
    uniq_jobs: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for sp in specs:
        mod = str(sp["modulo"])
        params = dict(sp["params"])
        cname = BASE._cache_key("NQ", mod, params)
        uniq_jobs[cname] = (cname, mod, params)
    _precalentar_jobs("NQ", list(uniq_jobs.values()), workers=workers, m1_dir=m1_dir)

    trade_cache = {cn: BASE._cargar_trades_cacheados(cn) for cn in uniq_jobs}
    m_desc_full = BASE._meses_activos_a5(start_nq, 20260930, "DESC")
    m_desc_20 = BASE._meses_activos_a5(20200101, 20260930, "DESC")
    m_desc_21 = BASE._meses_activos_a5(20210101, 20260930, "DESC")

    rows: list[dict[str, Any]] = []
    por_g_full: dict[str, list[pd.DataFrame]] = {}
    por_g_20: dict[str, list[pd.DataFrame]] = {}
    por_g_per: dict[str, dict[str, dict[str, str]]] = {}
    ops_desc_map: dict[str, pd.DataFrame] = {}
    daily_20_map: dict[str, pd.Series] = {}
    monthly_20_all: list[pd.DataFrame] = []

    for sp in specs:
        mod = str(sp["modulo"])
        params = dict(sp["params"])
        cname = BASE._cache_key("NQ", mod, params)
        ops_full = convertir_ops_enriquecidas(
            trade_cache[cname], mod, "NQ", atr_nq, orb_raw_nq, pv_nq,
            stop_atr_k=sp["stop_atr_k"], cap_mae_atr_k=sp["cap_mae_atr_k"], stop_orb_mult=sp["stop_orb_mult"],
        )
        ops_desc = ops_full[ops_full["a5"] == "DESC"].copy()
        ops_desc_map[sp["variante"]] = ops_desc
        ops_20 = ops_desc[ops_desc["fecha_int"] >= 20200101]
        ops_21 = ops_desc[ops_desc["fecha_int"] >= 20210101]

        st = BASE.resumir_serie_r(ops_desc, meses_totales=m_desc_full)
        st20 = BASE.resumir_serie_r(ops_20, meses_totales=m_desc_20)
        st21 = BASE.resumir_serie_r(ops_21, meses_totales=m_desc_21)
        dd20 = _metricas_dd_r(ops_20, m_desc_20)

        rows.append({
            "bloque": sp["bloque"],
            "grilla": sp["grilla"],
            "modulo": mod,
            "variante": sp["variante"],
            "params_json": json.dumps(params, sort_keys=True),
            "stop_atr_k": sp["stop_atr_k"],
            "cap_mae_atr_k": sp["cap_mae_atr_k"],
            "stop_orb_mult": sp["stop_orb_mult"],
            **st,
            "episodios": BASE._episodios_seguro(ops_desc),
            "n_2020": st20["n"],
            "ops_mes_2020": st20["ops_mes"],
            "R_bruto_2020": st20["R_bruto"],
            "R_neto_2020": st20["R_neto_mini"],
            "R_micro_2020": st20["R_neto_micro"],
            "R_mes_2020": st20["R_por_mes"],
            "t_ses_2020": st20["t_ses"],
            "p_boot_2020": st20["p_boot"],
            "med_fric_R_2020": st20["med_fric_R"],
            "peor_mes_2020": st20["peor_mes_R"],
            "episodios_2020": BASE._episodios_seguro(ops_20),
            **dd20,
            "n_2021": st21["n"],
            "R_neto_2021": st21["R_neto_mini"],
            "R_mes_2021": st21["R_por_mes"],
            "t_ses_2021": st21["t_ses"],
        })

        daily_20_map[sp["variante"]] = ops_20.groupby("fecha_int")["R_neto_mini"].sum() if len(ops_20) else pd.Series(dtype=float)
        g = str(sp["grilla"])
        por_g_full.setdefault(g, [])
        por_g_20.setdefault(g, [])
        if not ops_desc.empty:
            por_g_full[g].append(ops_desc[["R_neto_mini", "mes"]].rename(columns={"R_neto_mini": "R"}).assign(variante=sp["variante"]))
        if not ops_20.empty:
            chunk = ops_20[["R_neto_mini", "mes"]].rename(columns={"R_neto_mini": "R"}).assign(variante=sp["variante"])
            por_g_20[g].append(chunk)
            monthly_20_all.append(chunk)
        por_g_per.setdefault(g, {})[sp["variante"]] = sp["perillas"]

    diags: dict[str, Any] = {}
    degen20: set[str] = set()
    for g, dfs in por_g_full.items():
        df_g = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        df_g20 = pd.concat(por_g_20[g], ignore_index=True) if por_g_20[g] else pd.DataFrame()
        pmap = por_g_per[g]
        pnames = list(next(iter(pmap.values())).keys())
        per_fn = {pn: (lambda v, pn=pn, pmap=pmap: pmap[v][pn]) for pn in pnames}
        d_full = BASE._diagnostico_con_mejor(df_g, per_fn, total_celdas=len(pmap))
        d_20 = BASE._diagnostico_con_mejor(df_g20, per_fn, total_celdas=len(pmap))
        d_full["post_2020"] = d_20
        diags[g] = d_full
        degen20 |= set(d_20.get("degeneradas", []))

    # Numero efectivo global de la familia (45 variantes POST_2020 DESC) para DSR
    df_all20 = pd.concat(monthly_20_all, ignore_index=True) if monthly_20_all else pd.DataFrame(columns=["mes", "variante", "R"])
    m_all = df_all20.groupby(["mes", "variante"])["R"].sum().unstack().fillna(0.0) if len(df_all20) else pd.DataFrame()
    neff_global = round(DG.numero_efectivo(m_all), 2) if len(m_all) else 10.0

    df_perm = calcular_bateria_permutaciones(daily_20_map, fechas_desc_20, n_eff=neff_global, n_perm=5000)
    df_e1 = pd.DataFrame(rows).merge(df_perm, on="variante", how="left")
    df_e1["neff_global"] = neff_global
    df_e1["degenerada_2020"] = df_e1["variante"].isin(degen20) | (df_e1["n_2020"] < 30)
    df_e1["pasa_e1"] = (
        (~df_e1["degenerada_2020"])
        & (df_e1["R_neto_2020"] > 0.0)
        & (df_e1["p_perm"] < 0.05)
        & (df_e1["med_fric_R_2020"] <= 0.12)
    )
    df_e1.to_csv(OUT_DIR / "etapa1_variantes_y_permutaciones.csv", index=False)
    (OUT_DIR / "diagnostico_grillas_iter2.json").write_text(json.dumps(diags, indent=2, default=str), encoding="utf-8")
    return df_e1, diags, ops_desc_map


def _seleccionar_candidatos_etapa2(df_e1: pd.DataFrame) -> list[str]:
    """Elige hasta 9 candidatos de etapa 2 estrictamente desde `NQ DESC POST_2020`."""
    elegidos: list[str] = []

    def _add_if(v: str) -> None:
        if v not in elegidos and len(elegidos) < 9:
            elegidos.append(v)

    sub_ok = df_e1[df_e1["pasa_e1"]].copy()
    # 1) Nucleo T, R, Z, V, W (prioriza Calmar + t_ses en DESC)
    for mod, fallback in (("T", "T_stop100"), ("R", "R_maeATR25"), ("Z", "Z_maeATR25"), ("V", "V_nm30_maeATR40")):
        cand = sub_ok[sub_ok["modulo"] == mod].sort_values(["calmar", "t_ses_2020"], ascending=False)
        if not cand.empty:
            _add_if(str(cand.iloc[0]["variante"]))
        elif fallback in set(df_e1["variante"]):
            _add_if(fallback)
    # Asegurar tambien T_fab si no entro T_stop y R_maeATR25/35 si aporta
    w_cand = sub_ok[sub_ok["modulo"] == "W"].sort_values(["calmar", "t_ses_2020"], ascending=False)
    if not w_cand.empty:
        _add_if(str(w_cand.iloc[0]["variante"]))

    # 2) Diversificadores N y A20
    for mod in ("N", "A20"):
        cand = sub_ok[sub_ok["modulo"] == mod].sort_values(["calmar", "t_ses_2020"], ascending=False)
        if cand.empty:
            cand = df_e1[(df_e1["modulo"] == mod) & (~df_e1["degenerada_2020"]) & (df_e1["R_neto_2020"] > 0)].sort_values(
                ["t_ses_2020", "calmar"], ascending=False
            )
        if not cand.empty:
            _add_if(str(cand.iloc[0]["variante"]))

    # 3) Hasta 2 rescatadas de V2 (A1, F, P, C, S) que hayan pasado pasa_e1
    resc = sub_ok[sub_ok["modulo"].isin(("A1", "F", "P", "C", "S"))].sort_values(["t_ses_2020", "calmar"], ascending=False)
    for _, r in resc.iterrows():
        _add_if(str(r["variante"]))

    # 4) Si quedan cupos, sumar alternativas robustas de R o V o W en DESC (p.ej. R_maeATR35 o W segundo mejor)
    extras = sub_ok[~sub_ok["variante"].isin(elegidos)].sort_values(["calmar", "t_ses_2020"], ascending=False)
    for _, r in extras.iterrows():
        if len(elegidos) < 9:
            _add_if(str(r["variante"]))
    return elegidos[:9]


def _correr_etapa2(
    candidatos: list[str],
    specs_by_var: Mapping[str, Mapping[str, Any]],
    *,
    workers: int = 2,
    m1_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict[tuple[str, str], pd.DataFrame]]:
    """Evalua candidatos en NQ, ES, YM, RTY (medidos) y EMD (K33) en DESC y REP congelado."""
    activos = ("NQ", "ES", "YM", "RTY", "EMD")
    m1_str = str(m1_dir) if m1_dir is not None else None
    tasks: list[tuple[str, list[tuple[str, str, dict[str, Any]]], str | None]] = []
    for inst in activos:
        jobs_i: list[tuple[str, str, dict[str, Any]]] = []
        seen: set[str] = set()
        for vname in candidatos:
            sp = specs_by_var[vname]
            mod = str(sp["modulo"])
            params = dict(sp["params"])
            cname = BASE._cache_key(inst, mod, params)
            if cname not in seen and not (CACHE_DIR / f"{cname}.pkl").exists():
                seen.add(cname)
                jobs_i.append((cname, mod, params))
        if jobs_i:
            tasks.append((inst, jobs_i, m1_str))

    if tasks:
        n_w = min(max(int(workers), 1), len(tasks))
        print(f"[ETAPA 2] Corriendo transferencia para {len(tasks)} activos con workers={n_w}...", flush=True)
        if n_w == 1:
            for ta in tasks:
                for cname, n_tr, dt in BASE._run_instrumento_b4_worker(ta):
                    print(f"  [E2 RUN] {cname}: n={n_tr} ({dt:.1f}s)", flush=True)
        else:
            with concurrent.futures.ProcessPoolExecutor(max_workers=n_w) as ex:
                for logs in ex.map(BASE._run_instrumento_b4_worker, tasks):
                    for cname, n_tr, dt in logs:
                        print(f"  [E2 RUN] {cname}: n={n_tr} ({dt:.1f}s)", flush=True)
    else:
        print("[CACHE] Etapa 2 completa en disco.", flush=True)

    rows: list[dict[str, Any]] = []
    ops_safe_cache: dict[tuple[str, str], pd.DataFrame] = {}
    for inst in activos:
        atr_i, orb15_i, pv_i, start_i = BASE._cargar_series_sesion(inst, m1_dir=m1_dir)
        orb_raw_i = _cargar_orb_raw(inst, m1_dir=m1_dir) if any(specs_by_var[v]["modulo"] == "T" for v in candidatos) else orb15_i / 1.25
        for vname in candidatos:
            sp = specs_by_var[vname]
            mod = str(sp["modulo"])
            cname = BASE._cache_key(inst, mod, dict(sp["params"]))
            df_t = BASE._cargar_trades_cacheados(cname)
            ops = convertir_ops_enriquecidas(
                df_t, mod, inst, atr_i, orb_raw_i, pv_i,
                stop_atr_k=sp["stop_atr_k"], cap_mae_atr_k=sp["cap_mae_atr_k"], stop_orb_mult=sp["stop_orb_mult"],
            )
            ops_safe = ops[ops["a5"].isin(("DESC", "REP"))].copy()
            ops_safe_cache[(vname, inst)] = ops_safe

            for part in ("DESC", "REP"):
                sub_full = ops_safe[ops_safe["a5"] == part]
                sub_20 = sub_full[sub_full["fecha_int"] >= 20200101]
                sub_21 = sub_full[sub_full["fecha_int"] >= 20210101]
                st21 = BASE.resumir_serie_r(sub_21, meses_totales=BASE._meses_activos_a5(max(start_i, 20210101), 20260930, part))
                for per_nom, sub_p, d0 in (("FULL_2008", sub_full, start_i), ("POST_2020", sub_20, max(start_i, 20200101))):
                    m_tot = BASE._meses_activos_a5(d0, 20260930, part)
                    st = BASE.resumir_serie_r(sub_p, meses_totales=m_tot)
                    dd_m = _metricas_dd_r(sub_p, m_tot)
                    rows.append({
                        "variante": vname,
                        "modulo": mod,
                        "instrumento": inst,
                        "particion_a5": part,
                        "periodo": per_nom,
                        "spread_estimado": inst == "EMD",
                        **st,
                        **dd_m,
                        "n_2021": st21["n"],
                        "R_neto_2021": st21["R_neto_mini"],
                        "R_mes_2021": st21["R_por_mes"],
                    })

    df_e2 = pd.DataFrame(rows)
    df_e2.to_csv(OUT_DIR / "etapa2_transfer_y_rep.csv", index=False)
    return df_e2, ops_safe_cache


# ---------------------------------------------------------------------------
# Etapa 3 y 4: Ponderacion, Concurrencia, Sizing, Monte Carlo y LucidFlex
# ---------------------------------------------------------------------------


def calcular_pesos_esquemas(
    d_desc: pd.DataFrame,
    m_desc: pd.DataFrame,
    dur_med_min: Mapping[str, float],
) -> dict[str, dict[str, float]]:
    """Calcula W0..W5 exclusivamente en DESC, normalizados a la volatilidad diaria de W0."""
    cols = list(d_desc.columns)
    k = len(cols)
    x = d_desc.to_numpy(dtype=float)
    base_vol = float(np.std(x @ np.ones(k), ddof=1)) if k else 1.0
    sig_d = np.maximum(d_desc.std(ddof=1).to_numpy(dtype=float), 1e-6)
    sig_m = np.maximum(m_desc.std(ddof=1).to_numpy(dtype=float), 1e-6)

    # Covarianza diaria con shrinkage ligero tipo Ledoit-Wolf hacia diagonal
    cov_raw = np.cov(x, rowvar=False, ddof=1) if k > 1 else np.array([[sig_d[0] ** 2]])
    cov_shr = 0.80 * cov_raw + 0.20 * np.diag(np.diag(cov_raw))

    # W3: ERC con tope w_i <= 1.8 * mediana(w)
    w_erc = 1.0 / sig_d
    w_erc /= w_erc.sum()
    for _ in range(250):
        mc = cov_shr @ w_erc
        rc = w_erc * mc
        w_erc *= (rc.mean() / np.maximum(rc, 1e-12)) ** 0.30
        cap = 1.80 * float(np.median(w_erc))
        w_erc = np.minimum(w_erc, cap)
        w_erc /= w_erc.sum()

    # W4: Hierarchical Risk Parity (HRP) en NumPy puro
    if k >= 2:
        corr = np.corrcoef(x, rowvar=False)
        corr = np.nan_to_num(corr, nan=0.0)
        dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0.0, 1.0))
        np.fill_diagonal(dist, 0.0)
        clusters: list[list[int]] = [[i] for i in range(k)]
        d_mat = dist.copy()
        np.fill_diagonal(d_mat, np.inf)
        active_c = list(range(k))
        # Clustering jerarquico enlace simple hasta ordenar hojas
        next_id = k
        merges: list[tuple[int, int, float]] = []
        c_members: dict[int, list[int]] = {i: [i] for i in range(k)}
        d_work: dict[tuple[int, int], float] = {
            (i, j): float(dist[i, j]) for i in range(k) for j in range(i + 1, k)
        }
        cur_ids = list(range(k))
        while len(cur_ids) > 1:
            best_pair = min(
                ((cur_ids[a], cur_ids[b]) for a in range(len(cur_ids)) for b in range(a + 1, len(cur_ids))),
                key=lambda pr: d_work[(min(pr), max(pr))],
            )
            a_id, b_id = best_pair
            new_id = next_id
            next_id += 1
            c_members[new_id] = c_members[a_id] + c_members[b_id]
            rem = [cid for cid in cur_ids if cid not in (a_id, b_id)]
            for r_id in rem:
                da = d_work[(min(a_id, r_id), max(a_id, r_id))]
                db = d_work[(min(b_id, r_id), max(b_id, r_id))]
                d_work[(min(new_id, r_id), max(new_id, r_id))] = min(da, db)
            cur_ids = rem + [new_id]
            merges.append((a_id, b_id, 0.0))
        order = c_members[cur_ids[0]]

        def _cluster_var(idxs: list[int]) -> float:
            sub_c = cov_shr[np.ix_(idxs, idxs)]
            iv = 1.0 / np.maximum(np.diag(sub_c), 1e-12)
            w_loc = iv / iv.sum()
            return float(w_loc @ sub_c @ w_loc)

        w_hrp = np.ones(k, dtype=float)
        cola = [order]
        while cola:
            blk = cola.pop(0)
            if len(blk) <= 1:
                continue
            mid = len(blk) // 2
            izq, der = blk[:mid], blk[mid:]
            v_i = _cluster_var(izq)
            v_d = _cluster_var(der)
            alfa = 1.0 - v_i / max(v_i + v_d, 1e-12)
            w_hrp[izq] *= alfa
            w_hrp[der] *= (1.0 - alfa)
            cola.extend([izq, der])
    else:
        w_hrp = np.ones(k, dtype=float)

    dur_h = np.array([max(float(dur_med_min.get(c, 60.0)), 1.0) / 60.0 for c in cols])
    w_w5 = w_erc / (1.0 + 0.25 * (dur_h / 6.5))

    crudos = {
        "W0_equal_1R": np.ones(k, dtype=float),
        "W1_inv_vol_dia": 1.0 / sig_d,
        "W2_inv_vol_mes_freq": 1.0 / sig_m,
        "W3_ERC_cov_cap": w_erc,
        "W4_HRP": w_hrp,
        "W5_freq_dur_conc": w_w5,
    }
    norm: dict[str, dict[str, float]] = {}
    for nom, w in crudos.items():
        s_raw = x @ w
        sd_raw = float(np.std(s_raw, ddof=1)) if k else 1.0
        w_sc = w * (base_vol / max(sd_raw, 1e-12))
        norm[nom] = {c: float(w_sc[i]) for i, c in enumerate(cols)}
    return norm


def aplicar_tope_concurrencia_causal(
    ops_streams: Mapping[str, pd.DataFrame],
    pesos: Mapping[str, float],
    sizing_factor: Mapping[str, pd.Series] | None = None,
    cap_r: float | None = 3.0,
) -> tuple[pd.DataFrame, float]:
    """Combina trades cronologicamente con peso por stream y tope ex-ante por direccion."""
    chunks: list[pd.DataFrame] = []
    for sid, df in ops_streams.items():
        if df is None or len(df) == 0 or pesos.get(sid, 0.0) <= 0.0:
            continue
        cols_keep = ["fecha_int", "mes", "en_ns", "ex_ns", "side", "R_neto_mini", "riesgo_pts"]
        sub = df[cols_keep].copy()
        sub["R_neto_micro"] = df["R_neto_micro"].to_numpy(dtype=float) if "R_neto_micro" in df.columns else df["R_neto_mini"].to_numpy(dtype=float)
        sub["stream"] = sid
        sf = sizing_factor[sid].reindex(df.index).to_numpy(dtype=float) if sizing_factor and sid in sizing_factor else np.ones(len(sub))
        sub["w_target"] = float(pesos[sid]) * sf
        chunks.append(sub)
    if not chunks:
        return pd.DataFrame(columns=["fecha_int", "mes", "en_ns", "ex_ns", "side", "stream", "w_target", "w_eff", "R_eff"]), 0.0

    todo = pd.concat(chunks, ignore_index=True).sort_values(["en_ns", "stream"], kind="mergesort").reset_index(drop=True)
    abiertos: list[tuple[int, int, float]] = []
    w_eff = np.empty(len(todo), dtype=float)
    max_open = 0.0

    en_arr = todo["en_ns"].to_numpy(dtype=np.int64)
    ex_arr = todo["ex_ns"].to_numpy(dtype=np.int64)
    sd_arr = todo["side"].to_numpy(dtype=int)
    wt_arr = todo["w_target"].to_numpy(dtype=float)

    for i in range(len(todo)):
        t_cur = int(en_arr[i])
        sd_cur = 1 if sd_arr[i] >= 0 else -1
        abiertos = [(ex_p, s_p, w_p) for (ex_p, s_p, w_p) in abiertos if ex_p > t_cur]
        same_open = sum(w_p for (_, s_p, w_p) in abiertos if s_p == sd_cur)
        w_i = float(wt_arr[i])
        if cap_r is not None:
            w_final = min(w_i, max(0.0, float(cap_r) - same_open))
        else:
            w_final = w_i
        w_eff[i] = w_final
        if w_final > 1e-9:
            abiertos.append((int(ex_arr[i]), sd_cur, w_final))
            tot_net = abs(sum(s_p * w_p for (_, s_p, w_p) in abiertos))
            if tot_net > max_open:
                max_open = tot_net

    todo["w_eff"] = w_eff
    todo["R_eff"] = todo["R_neto_mini"].to_numpy(dtype=float) * w_eff
    return todo, round(float(max_open), 2)


def evaluar_serie_cartera(
    serie_diaria: pd.Series,
    meses_tot: int,
    *,
    mc_reps: int = 5000,
    seed: int = 99,
) -> dict[str, Any]:
    """Evalua desempeno y estres Monte Carlo por bloques de 5 dias sobre serie diaria en R."""
    arr = serie_diaria.to_numpy(dtype=float)
    n_d = len(arr)
    if n_d < 5:
        return {"R_mes": np.nan, "t_ses": np.nan, "sharpe_anual": np.nan, "dd_R": np.nan}

    eq = np.cumsum(arr)
    peak = np.maximum.accumulate(eq)
    dd_vec = eq - peak
    dd_real = float(dd_vec.min())
    ulcer = float(np.sqrt(np.mean(dd_vec ** 2)))
    sd = float(np.std(arr, ddof=1))
    mean_d = float(np.mean(arr))
    t_ses = float(mean_d / sd * math.sqrt(n_d)) if sd > 1e-12 else 0.0
    sharpe = float(mean_d / sd * math.sqrt(252.0)) if sd > 1e-12 else 0.0
    r_mes = float(np.sum(arr) / max(meses_tot, 1))
    calmar = round((r_mes * 12.0) / max(abs(dd_real), 0.1), 2)

    dt_idx = pd.to_datetime(serie_diaria.index.astype(str), format="%Y%m%d")
    mon = pd.Series(arr, index=dt_idx.to_period("M").astype(str)).groupby(level=0).sum()
    pct_mes_pos = round(float((mon > 0.0).mean() * 100.0), 1) if len(mon) else 0.0

    # Maximo meses underwater
    mon_eq = mon.cumsum().to_numpy(dtype=float)
    mon_pk = np.maximum.accumulate(mon_eq)
    uw, max_uw = 0, 0
    for e_v, p_v in zip(mon_eq, mon_pk):
        if e_v < p_v - 1e-9:
            uw += 1
            max_uw = max(max_uw, uw)
        else:
            uw = 0

    # Monte Carlo block bootstrap (bloque 5 dias, largo n_d)
    rng = np.random.default_rng(seed)
    blk = 5
    nb = max(1, (n_d + blk - 1) // blk)
    starts = rng.integers(0, max(n_d - blk + 1, 1), size=(int(mc_reps), nb))
    offs = np.arange(blk)[None, None, :]
    idx_mc = (starts[:, :, None] + offs).reshape(int(mc_reps), -1)[:, :n_d]
    tray = arr[idx_mc]
    eq_mc = np.cumsum(tray, axis=1)
    dd_mc = np.min(eq_mc - np.maximum.accumulate(np.maximum(0.0, eq_mc), axis=1), axis=1)

    return {
        "sesiones": n_d,
        "R_mes": round(r_mes, 3),
        "t_ses": round(t_ses, 2),
        "sharpe_anual": round(sharpe, 2),
        "dd_R": round(dd_real, 2),
        "calmar": calmar,
        "ulcer_R": round(ulcer, 2),
        "worst_day_R": round(float(arr.min()), 2),
        "worst_mes_R": round(float(mon.min()), 2) if len(mon) else np.nan,
        "pct_meses_pos": pct_mes_pos,
        "max_meses_uw": int(max_uw),
        "mc_dd_p50": round(float(np.quantile(dd_mc, 0.50)), 2),
        "mc_dd_p90": round(float(np.quantile(dd_mc, 0.10)), 2),
        "mc_dd_p95": round(float(np.quantile(dd_mc, 0.05)), 2),
        "mc_dd_p99": round(float(np.quantile(dd_mc, 0.01)), 2),
    }


def _factor_sizing(
    ops: pd.DataFrame,
    modo: str,
    ref_riesgo_pts: float,
    mean_factor_ref: float | None = None,
) -> tuple[pd.Series, float]:
    """Sizing sin leakage: `R_const`, `raiz_riesgo` o `fijo_micro` escalados a media 1.0 en DESC."""
    rp = np.maximum(ops["riesgo_pts"].to_numpy(dtype=float), 1e-6)
    ref = max(float(ref_riesgo_pts), 1e-6)
    if modo == "R_const":
        raw = np.ones(len(rp), dtype=float)
    elif modo == "raiz_riesgo":
        raw = np.sqrt(rp / ref)
    elif modo == "fijo_micro":
        raw = rp / ref
    else:
        raise ValueError(f"Modo sizing desconocido: {modo}")
    fac_ref = float(np.mean(raw)) if mean_factor_ref is None and len(raw) else (mean_factor_ref or 1.0)
    return pd.Series(raw / max(fac_ref, 1e-6), index=ops.index), fac_ref


def _usd_pt_micro(inst: str) -> float:
    mic = BASE.MICRO_EQUIV.get(inst.upper())
    if mic is None:
        return float(costos.tick_value_usd(inst.upper()) / costos.tick_size(inst.upper()))
    return float(costos.tick_value_usd(mic) / costos.tick_size(mic))


def _serie_usd_micros_enteros(
    ops_cartera: pd.DataFrame,
    fechas_ses: list[int],
    usd_por_r: float,
    max_micros: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Convierte trades de cartera a USD diario en micros enteros reales (`MNQ/MES/MYM`) con tope por prop firm."""
    d_usd = {f: 0.0 for f in fechas_ses}
    micros_por_stream: dict[str, list[int]] = {}
    if len(ops_cartera) == 0:
        return np.zeros(len(fechas_ses), dtype=float), {}

    for row in ops_cartera.itertuples(index=False):
        if row.w_eff <= 1e-9:
            continue
        inst = str(row.stream).split("::")[1]
        if inst not in BASE.MICRO_EQUIV:
            continue  # RTY/EMD fuera de micros sin medicion K33 de M2K
        upt = _usd_pt_micro(inst)
        r_1mic = float(row.riesgo_pts) * upt
        tgt_usd = float(usd_por_r) * float(row.w_eff)
        n_mic = int(min(max_micros, max(0, round(tgt_usd / max(r_1mic, 1e-6)))))
        if n_mic == 0 and tgt_usd >= 0.55 * r_1mic:
            n_mic = 1
        micros_por_stream.setdefault(str(row.stream), []).append(n_mic)
        r_mic = float(row.R_neto_micro) if np.isfinite(row.R_neto_micro) else float(row.R_neto_mini)
        usd_tr = (r_mic * float(row.riesgo_pts)) * upt * n_mic
        fi = int(row.fecha_int)
        if fi in d_usd:
            d_usd[fi] += usd_tr

    arr = np.array([d_usd[f] for f in fechas_ses], dtype=float)
    res_mic = {k: round(float(np.median(v)), 1) for k, v in micros_por_stream.items() if v}
    return arr, res_mic


def _correr_etapa3_y_4(
    df_e1: pd.DataFrame,
    df_e2: pd.DataFrame,
    ops_e2: Mapping[tuple[str, str], pd.DataFrame],
    fechas_nq: Mapping[str, list[int]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Disena carteras (NQ vs Multi-Indice), compara W0..W5 y sizing DESC->REP, y evalua LucidFlex."""
    # 1) Seleccion causal de streams en DESC POST_2020
    e1_map = df_e1.set_index("variante")
    pasan_nq = []
    for vname in sorted({k[0] for k in ops_e2}):
        if vname in e1_map.index and bool(e1_map.loc[vname, "pasa_e1"]):
            pasan_nq.append((vname, "NQ"))

    # Evitar duplicados por mismo modulo en NQ: queda el de mejor Calmar en DESC
    mejores_nq_por_mod: dict[str, str] = {}
    for v, _ in sorted(pasan_nq, key=lambda x: float(e1_map.loc[x[0], "calmar"]), reverse=True):
        m = str(e1_map.loc[v, "modulo"])
        if m not in mejores_nq_por_mod:
            mejores_nq_por_mod[m] = v
    streams_nq = {f"{v}::NQ": ops_e2[(v, "NQ")] for v in mejores_nq_por_mod.values()}

    # Multi-indice: anadir streams externos MEDIDOS (ES, YM, RTY — nunca EMD) con EDGE claro en DESC POST_2020
    streams_multi = dict(streams_nq)
    e2_desc = df_e2[(df_e2["periodo"] == "POST_2020") & (df_e2["particion_a5"] == "DESC") & (~df_e2["spread_estimado"])]
    for _, r in e2_desc[e2_desc["instrumento"].isin(("ES", "YM", "RTY"))].iterrows():
        if int(r["n"]) >= 30 and float(r["R_neto_mini"]) > 0.0 and float(r["p_boot"]) < 0.10 and float(r["med_fric_R"]) <= 0.10:
            sid = f"{r['variante']}::{r['instrumento']}"
            streams_multi[sid] = ops_e2[(str(r["variante"]), str(r["instrumento"]))]

    carteras_def = {"NQ_CORE": streams_nq}
    if len(streams_multi) > len(streams_nq):
        carteras_def["MULTI_INDICE"] = streams_multi

    ses_desc = fechas_nq["DESC"]
    ses_rep = fechas_nq["REP"]
    m_desc = BASE._meses_activos_a5(20200101, 20260930, "DESC")
    m_rep = BASE._meses_activos_a5(20200101, 20260930, "REP")

    rows_e4: list[dict[str, Any]] = []
    curvas_graf: dict[str, dict[str, pd.Series]] = {}
    pesos_res: dict[str, Any] = {}
    asignacion_detalle: dict[str, Any] = {}

    for cnom, smap in carteras_def.items():
        s_desc: dict[str, pd.DataFrame] = {}
        s_rep: dict[str, pd.DataFrame] = {}
        dur_med: dict[str, float] = {}
        ref_risk: dict[str, float] = {}
        d_desc_cols: dict[str, pd.Series] = {}
        m_desc_cols: dict[str, pd.Series] = {}

        for sid, df in smap.items():
            sub_d = df[(df["a5"] == "DESC") & (df["fecha_int"] >= 20200101)].copy()
            sub_r = df[(df["a5"] == "REP") & (df["fecha_int"] >= 20200101)].copy()
            s_desc[sid] = sub_d
            s_rep[sid] = sub_r
            dur_med[sid] = float(sub_d["dur_min"].median()) if len(sub_d) else 60.0
            ref_risk[sid] = float(sub_d["riesgo_pts"].median()) if len(sub_d) else 50.0
            d_desc_cols[sid] = sub_d.groupby("fecha_int")["R_neto_mini"].sum()
            m_desc_cols[sid] = sub_d.groupby("mes")["R_neto_mini"].sum()

        D_desc = pd.DataFrame(d_desc_cols, index=ses_desc).fillna(0.0)
        M_desc = pd.DataFrame(m_desc_cols).fillna(0.0)
        pesos_dict = calcular_pesos_esquemas(D_desc, M_desc, dur_med)
        pesos_res[cnom] = pesos_dict

        # Evaluar 6 esquemas (con R_const) + comparativa sizing en W3 y W5
        curvas_graf[cnom] = {}
        for esq, w_map in pesos_dict.items():
            cap = 3.0 if esq == "W5_freq_dur_conc" else None
            # Escala cap proporcional al peso medio si pesos estan normalizados
            for modo_sz in (("R_const", "raiz_riesgo", "fijo_micro") if esq in ("W0_equal_1R", "W3_ERC_cov_cap", "W5_freq_dur_conc") else ("R_const",)):
                fac_d, fac_r = {}, {}
                for sid in smap:
                    fd, fmean = _factor_sizing(s_desc[sid], modo_sz, ref_risk[sid])
                    fr, _ = _factor_sizing(s_rep[sid], modo_sz, ref_risk[sid], mean_factor_ref=fmean)
                    fac_d[sid], fac_r[sid] = fd, fr

                tr_d, mx_d = aplicar_tope_concurrencia_causal(s_desc, w_map, fac_d, cap_r=cap)
                tr_r, mx_r = aplicar_tope_concurrencia_causal(s_rep, w_map, fac_r, cap_r=cap)
                sd_ser = tr_d.groupby("fecha_int")["R_eff"].sum().reindex(ses_desc, fill_value=0.0)
                sr_ser = tr_r.groupby("fecha_int")["R_eff"].sum().reindex(ses_rep, fill_value=0.0)
                if modo_sz == "R_const" and esq in ("W0_equal_1R", "W3_ERC_cov_cap", "W4_HRP", "W5_freq_dur_conc"):
                    curvas_graf[cnom][f"{esq}__DESC"] = sd_ser
                    curvas_graf[cnom][f"{esq}__REP"] = sr_ser

                for part_n, ser_p, tr_p, mtot, mx_o in (("DESC", sd_ser, tr_d, m_desc, mx_d), ("REP", sr_ser, tr_r, m_rep, mx_r)):
                    ev = evaluar_serie_cartera(ser_p, mtot, mc_reps=5000, seed=99)
                    wt_sum = float(tr_p["w_target"].sum()) if len(tr_p) and "w_target" in tr_p.columns else 0.0
                    we_sum = float(tr_p["w_eff"].sum()) if len(tr_p) and "w_eff" in tr_p.columns else 0.0
                    pct_rec = round(max(0.0, 1.0 - we_sum / wt_sum) * 100.0, 1) if wt_sum > 0 else 0.0
                    rows_e4.append({
                        "cartera": cnom,
                        "esquema": esq,
                        "sizing": modo_sz,
                        "particion_a5": part_n,
                        "n_streams": len(smap),
                        "max_open_R": mx_o,
                        "pct_recorte_conc": pct_rec,
                        **ev,
                    })

        # Tabla operativa detallada por stream (para W3 y W5 en NQ/ES/YM operables con micros)
        det_rows = []
        w_pref = pesos_dict.get("W5_freq_dur_conc", pesos_dict["W3_ERC_cov_cap"])
        for sid in smap:
            sub_d = s_desc[sid]
            inst = sid.split("::")[1]
            upt = _usd_pt_micro(inst)
            det_rows.append({
                "stream": sid,
                "instrumento": inst,
                "peso_W5": round(w_pref[sid], 3),
                "peso_W3": round(pesos_dict["W3_ERC_cov_cap"][sid], 3),
                "ops_mes_DESC": round(len(sub_d) / m_desc, 1),
                "dur_med_min": round(dur_med[sid], 0),
                "riesgo_med_pts": round(ref_risk[sid], 1),
                "usd_riesgo_1mic": round(ref_risk[sid] * upt, 1),
                "R_neto_DESC": round(float(sub_d["R_neto_mini"].mean()), 4),
                "aporte_R_mes_W5": round(float(sub_d["R_neto_mini"].sum() * w_pref[sid] / m_desc), 2),
                "micros_50K_base125": round(125.0 * w_pref[sid] / max(ref_risk[sid] * upt, 1e-6), 1),
                "micros_150K_base250": round(250.0 * w_pref[sid] / max(ref_risk[sid] * upt, 1e-6), 1),
            })
        asignacion_detalle[cnom] = det_rows

    # Simulacion LucidFlex sobre W5 (con fallback a W3) en NQ_CORE y MULTI_INDICE (micros reales!)
    lucid_out: dict[str, Any] = {}
    for cnom, smap in carteras_def.items():
        # Construir trades de W5 en DESC y REP para micros enteros
        s_desc = {sid: df[(df["a5"] == "DESC") & (df["fecha_int"] >= 20200101)].copy() for sid, df in smap.items() if sid.split("::")[1] in BASE.MICRO_EQUIV}
        s_rep = {sid: df[(df["a5"] == "REP") & (df["fecha_int"] >= 20200101)].copy() for sid, df in smap.items() if sid.split("::")[1] in BASE.MICRO_EQUIV}
        if not s_desc:
            continue
        w_map = {k: v for k, v in pesos_res[cnom]["W5_freq_dur_conc"].items() if k in s_desc}
        tr_d, _ = aplicar_tope_concurrencia_causal(s_desc, w_map, None, cap_r=3.0)
        tr_r, _ = aplicar_tope_concurrencia_causal(s_rep, w_map, None, cap_r=3.0)

        for tam, cfg_t in LG.TAMANOS.items():
            esc = cfg_t["mll"] / 1000.0
            for base_r in (100.0, 150.0):
                usd_r = base_r * esc
                y_desc, mic_d = _serie_usd_micros_enteros(tr_d, ses_desc, usd_r, cfg_t["micros"])
                y_rep, _ = _serie_usd_micros_enteros(tr_r, ses_rep, usd_r, cfg_t["micros"])
                pr = LG.precio(tam, True, 0.50)
                for p_nom, y_raw in (("DESC", y_desc), ("REP", y_rep)):
                    for mult_nom, mult in (("real_100", 1.0), ("contraida_60", 0.60)):
                        y_sc = y_raw - np.mean(y_raw) + mult * np.mean(y_raw)
                        acc = LG.por_cuenta(y_sc, cfg_t, 0.50, N=4000)
                        car = LG.cartera(y_sc, cfg_t, 0.50, pr, max_eval=5, por_dia=1, N=1500, H=504)
                        key = f"{cnom}|{tam}|R{int(usd_r)}|{p_nom}|{mult_nom}"
                        lucid_out[key] = {
                            "precio_eval": pr,
                            "usd_dia_media": round(float(np.mean(y_sc)), 2),
                            "usd_dia_sd": round(float(np.std(y_sc, ddof=1)), 2),
                            "worst_day_usd": round(float(np.min(y_sc)), 1),
                            "micros_med_stream": mic_d,
                            "ev_examen_usd": round(float(acc["cobrado_medio"] - pr), 1),
                            "pasa_pct": round(float(acc["pasa"] * 100.0), 1),
                            "quema_eval_pct": round(float(acc["quema_eval"] * 100.0), 1),
                            "llega_live_pct": round(float(acc["llega_a_live"] * 100.0), 1),
                            "dias_pasar_p50": acc["dias_pasar_p10_50_90"][1] if acc["dias_pasar_p10_50_90"] else None,
                            "cartera_neto_medio_usd": round(float(car["neto_medio"]), 1),
                            "cartera_p_pos_pct": round(float(car["p_neto_positivo"] * 100.0), 1),
                            "cartera_usd_mes": round(float(car["usd_por_mes_hasta_fin"]), 1),
                            "cartera_caja_min_p10": car["caja_minima_p50_p10"][1],
                        }

    df_e4 = pd.DataFrame(rows_e4)
    df_e4.to_csv(OUT_DIR / "etapa4_cartera_pesos_y_sizing.csv", index=False)
    pack_lucid = {"asignacion": asignacion_detalle, "pesos": pesos_res, "lucid": lucid_out}
    (OUT_DIR / "etapa4_lucid_y_mc.json").write_text(json.dumps(pack_lucid, indent=2, default=str), encoding="utf-8")
    return df_e4, {"pack": pack_lucid, "curvas": curvas_graf}


def graficar_iter2(
    df_e1: pd.DataFrame,
    df_e2: pd.DataFrame,
    df_e4: pd.DataFrame,
    extra_e4: Mapping[str, Any],
) -> dict[str, Path]:
    """Genera 3 graficos visuales claros y los copia en `ARTIFACTS_DIR`."""
    if plt is None:
        raise RuntimeError("matplotlib requerido")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rutas: dict[str, Path] = {}

    # 1) Variantes V1/V2 y permutaciones
    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(16.5, 7.6), facecolor="#0d1316")
    for ax in (ax1, ax2):
        ax.set_facecolor("#11191c")
        ax.tick_params(colors="#b4c2c8", labelsize=8.5)
        for sp in ax.spines.values():
            sp.set_color("#29363c")

    sub1 = df_e1[df_e1["n_2020"] >= 30].sort_values("t_ses_2020", ascending=True).tail(20)
    y1 = np.arange(len(sub1))
    cols1 = ["#2ca693" if ok and q < 0.10 else "#587cc9" if r > 0 else "#c47068"
             for ok, q, r in zip(sub1["pasa_e1"], sub1["q_bh"], sub1["R_neto_2020"])]
    ax1.barh(y1, sub1["t_ses_2020"], color=cols1, height=0.64, alpha=0.92)
    for yi, (_, rr) in enumerate(sub1.iterrows()):
        tag = "*" if rr["q_bh"] < 0.05 else ""
        ax1.text(max(float(rr["t_ses_2020"]), 0.0) + 0.08, yi,
                 f"R={rr['R_neto_2020']:+.3f} q={rr['q_bh']:.3f}{tag}",
                 va="center", color="#d2dce1", fontsize=7.2)
    ax1.axvline(1.96, color="#f0c954", linewidth=0.85, linestyle=":", label="t=1.96")
    ax1.axvline(0.0, color="#9ab0ba", linewidth=0.85, linestyle="--")
    ax1.set_xlim(min(float(sub1["t_ses_2020"].min()), -0.5) - 0.3, float(sub1["t_ses_2020"].max()) + 2.1)
    ax1.set_yticks(y1)
    ax1.set_yticklabels(sub1["variante"])
    ax1.set_xlabel("t-stat por sesion (NQ DESC POST_2020)", color="#c8d4da")
    ax1.set_title("Etapa 1 (V1+V2): Top 20 variantes y control BH-FDR (B=5000)", color="#e6eef2", fontsize=10.5)

    v_plot = df_e1[(df_e1["n_2020"] >= 30) & df_e1["calmar"].notna() & (df_e1["R_neto_2020"] > -0.15)].copy()
    sc_col = ["#2ca693" if ok else "#587cc9" if r > 0 else "#c47068" for ok, r in zip(v_plot["pasa_e1"], v_plot["R_neto_2020"])]
    ax2.scatter(np.abs(v_plot["dd_R"]), v_plot["R_mes_2020"], c=sc_col, s=55, alpha=0.88, edgecolors="#0d1316")
    top_lbl = v_plot.sort_values("calmar", ascending=False).head(10)
    for _, rr in top_lbl.iterrows():
        ax2.text(abs(float(rr["dd_R"])) + 0.4, float(rr["R_mes_2020"]) + 0.04, str(rr["variante"]), color="#dce4e8", fontsize=7.0)
    ax2.axhline(0.0, color="#9ab0ba", linewidth=0.8, linestyle="--")
    ax2.set_xlabel("|Drawdown maximo| en NQ DESC POST_2020 (R)", color="#c8d4da")
    ax2.set_ylabel("Expectativa mensual (R/mes)", color="#c8d4da")
    ax2.set_title("Frontera Riesgo/Retorno (|DD| vs R/mes, verde=valida p_perm<0.05)", color="#e6eef2", fontsize=10.5)
    fig1.tight_layout()
    p1 = OUT_DIR / "iter2_variantes_y_permutaciones.png"
    fig1.savefig(p1, dpi=150, facecolor=fig1.get_facecolor())
    plt.close(fig1)
    rutas["etapa1"] = p1

    # 2) Heatmap multi-indice Etapa 2 (POST_2020)
    fig2, bx = plt.subplots(figsize=(13.5, 6.8), facecolor="#0d1316")
    bx.set_facecolor("#11191c")
    bx.tick_params(colors="#b4c2c8", labelsize=8.5)
    for sp in bx.spines.values():
        sp.set_color("#29363c")
    piv2 = df_e2[df_e2["periodo"] == "POST_2020"].copy()
    piv2["col"] = piv2["instrumento"] + "_" + piv2["particion_a5"]
    hm = piv2.pivot(index="variante", columns="col", values="R_neto_mini")
    hn = piv2.pivot(index="variante", columns="col", values="n")
    orden_c = [c for c in ("NQ_DESC", "NQ_REP", "ES_DESC", "ES_REP", "YM_DESC", "YM_REP", "RTY_DESC", "RTY_REP", "EMD_DESC", "EMD_REP") if c in hm.columns]
    hm, hn = hm[orden_c], hn[orden_c]
    im = bx.imshow(hm.fillna(0.0).to_numpy(dtype=float), cmap="RdYlGn", vmin=-0.18, vmax=0.40, aspect="auto")
    bx.set_xticks(np.arange(hm.shape[1]))
    bx.set_xticklabels([c.replace("EMD_", "EMD*_") for c in hm.columns], rotation=28, ha="right", fontsize=8.5)
    bx.set_yticks(np.arange(hm.shape[0]))
    bx.set_yticklabels(hm.index, fontsize=8.5)
    for r_i in range(hm.shape[0]):
        for c_i in range(hm.shape[1]):
            v, nv = hm.iloc[r_i, c_i], hn.iloc[r_i, c_i]
            txt = f"{v:+.2f}\nn={int(nv)}" if np.isfinite(v) and np.isfinite(nv) else "—"
            col_t = "#f4f7f8" if (np.isfinite(v) and (v < -0.07 or v > 0.24)) else "#0c1214"
            bx.text(c_i, r_i, txt, ha="center", va="center", color=col_t, fontsize=7.2, fontweight="bold")
    bx.set_title("Etapa 2 POST_2020: Transferencia multi-indice (DESC) y Confirmacion Congelada (REP)\n(*EMD = spread estimado K33, reportado aparte)", color="#e6eef2", fontsize=10.5)
    fig2.colorbar(im, ax=bx, fraction=0.035, pad=0.02)
    fig2.tight_layout()
    p2 = OUT_DIR / "iter2_transferencia_multiindice_A5.png"
    fig2.savefig(p2, dpi=150, facecolor=fig2.get_facecolor())
    plt.close(fig2)
    rutas["etapa2"] = p2

    # 3) Cartera: equity DESC / REP + comparativa Calmar y pesos
    fig3, (cx1, cx2, cx3) = plt.subplots(1, 3, figsize=(18.0, 6.2), facecolor="#0d1316")
    for ax in (cx1, cx2, cx3):
        ax.set_facecolor("#11191c")
        ax.tick_params(colors="#b4c2c8", labelsize=8)
        for sp in ax.spines.values():
            sp.set_color("#29363c")

    curv = extra_e4.get("curvas", {})
    cnom_pref = "MULTI_INDICE" if "MULTI_INDICE" in curv else "NQ_CORE"
    col_esq = {"W0_equal_1R": "#8ca0ab", "W3_ERC_cov_cap": "#3baeb8", "W4_HRP": "#f0c954", "W5_freq_dur_conc": "#2ca693"}
    for ax_c, part in ((cx1, "DESC"), (cx2, "REP")):
        for esq, chex in col_esq.items():
            ser = curv.get(cnom_pref, {}).get(f"{esq}__{part}")
            if ser is not None and len(ser):
                ax_c.plot(np.arange(len(ser)), np.cumsum(ser.to_numpy(dtype=float)), label=esq, color=chex, linewidth=1.6)
        ax_c.set_title(f"{cnom_pref} ({part} A5 congelado, R)", color="#e6eef2", fontsize=10)
        ax_c.set_xlabel("Sesiones", color="#c8d4da")
        ax_c.set_ylabel("R acumulado (misma vol DESC)", color="#c8d4da")
        ax_c.legend(loc="upper left", fontsize=7.5, frameon=True, facecolor="#11191c", edgecolor="#29363c", labelcolor="#dbe4e8")

    # Panel derecho: pesos W5 vs W3 de la cartera ganadora
    asig = extra_e4["pack"]["asignacion"].get(cnom_pref, [])
    if asig:
        df_as = pd.DataFrame(asig).sort_values("peso_W5", ascending=True)
        ya = np.arange(len(df_as))
        cx3.barh(ya - 0.16, df_as["peso_W3"], height=0.30, color="#3baeb8", label="W3 ERC_cap")
        cx3.barh(ya + 0.16, df_as["peso_W5"], height=0.30, color="#2ca693", label="W5 Freq+Dur+Conc")
        cx3.set_yticks(ya)
        cx3.set_yticklabels(df_as["stream"], fontsize=7.5)
        cx3.set_xlabel("Multiplicador de peso por R (escala eq_vol)", color="#c8d4da")
        cx3.set_title("Pesos por stream ajustados en DESC", color="#e6eef2", fontsize=10)
        cx3.legend(loc="lower right", fontsize=7.5, frameon=True, facecolor="#11191c", edgecolor="#29363c", labelcolor="#dbe4e8")

    fig3.tight_layout()
    p3 = OUT_DIR / "iter2_cartera_pesos_dd_y_mc.png"
    fig3.savefig(p3, dpi=150, facecolor=fig3.get_facecolor())
    plt.close(fig3)
    rutas["etapa4"] = p3

    if ARTIFACTS_DIR.exists():
        import shutil
        for sp_p in rutas.values():
            shutil.copy2(sp_p, ARTIFACTS_DIR / sp_p.name)
    return rutas


def ejecutar_iter2(etapa: str = "todo", m1_dir: Path | None = None, workers: int = 2) -> dict[str, Any]:
    asegurar_compuerta_iter2()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    atr_nq, _, pv_nq, start_nq = BASE._cargar_series_sesion("NQ", m1_dir=m1_dir)
    orb_raw_nq = _cargar_orb_raw("NQ", m1_dir=m1_dir)
    fechas_nq = _cargar_fechas_a5_inst("NQ", m1_dir=m1_dir)
    specs_by_var = {s["variante"]: s for s in _grillas_iter2()}

    df_e1: pd.DataFrame | None = None
    diags: dict[str, Any] = {}
    if etapa in ("etapa1", "todo"):
        df_e1, diags, _ = _correr_etapa1(
            atr_nq, orb_raw_nq, pv_nq, start_nq, fechas_nq["DESC"], workers=workers, m1_dir=m1_dir
        )
        print("\n=== ETAPA 1 TOP POR t_ses_2020 (NQ DESC POST_2020) ===")
        cols1 = ["bloque", "variante", "n_2020", "R_neto_2020", "R_mes_2020", "dd_R", "calmar", "p_perm", "q_bh", "p_maxT", "DSR", "pasa_e1"]
        print(df_e1.sort_values("t_ses_2020", ascending=False)[cols1].head(24).to_string(index=False))

    df_e2: pd.DataFrame | None = None
    ops_e2: dict[tuple[str, str], pd.DataFrame] = {}
    cands: list[str] = []
    if etapa in ("etapa2", "etapa3_4", "todo"):
        if df_e1 is None:
            df_e1 = pd.read_csv(OUT_DIR / "etapa1_variantes_y_permutaciones.csv")
            diags = json.loads((OUT_DIR / "diagnostico_grillas_iter2.json").read_text(encoding="utf-8"))
        cands = _seleccionar_candidatos_etapa2(df_e1)
        print("\n=== CANDIDATOS ETAPA 2 (DESC -> MULTI-INDICE + REP) ===", cands, flush=True)
        df_e2, ops_e2 = _correr_etapa2(cands, specs_by_var, workers=workers, m1_dir=m1_dir)
        print("\n=== ETAPA 2 POST_2020 RESUMEN ===")
        print(df_e2[df_e2["periodo"] == "POST_2020"][["variante", "instrumento", "particion_a5", "n", "R_neto_mini", "R_por_mes", "dd_R", "calmar", "p_boot"]].to_string(index=False))

    df_e4: pd.DataFrame | None = None
    extra_e4: dict[str, Any] = {}
    if etapa in ("etapa3_4", "todo"):
        assert df_e1 is not None and df_e2 is not None
        df_e4, extra_e4 = _correr_etapa3_y_4(df_e1, df_e2, ops_e2, fechas_nq)
        print("\n=== ETAPA 4 CARTERA (DESC vs REP CONGELADO) ===")
        print(df_e4[["cartera", "esquema", "sizing", "particion_a5", "R_mes", "t_ses", "dd_R", "mc_dd_p95", "calmar", "worst_day_R", "max_open_R"]].to_string(index=False))
        resumen = {
            "candidatos_etapa2": cands,
            "diagnosticos": diags,
            "asignacion": extra_e4["pack"]["asignacion"],
            "pesos": extra_e4["pack"]["pesos"],
            "lucid_resumen": extra_e4["pack"]["lucid"],
        }
        (OUT_DIR / "resumen_iter2.json").write_text(json.dumps(resumen, indent=2, default=str), encoding="utf-8")
        graficar_iter2(df_e1, df_e2, df_e4, extra_e4)

    return {"df_e1": df_e1, "df_e2": df_e2, "df_e4": df_e4}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Iteracion 2 FUNDEDSYNC: V1/V2, permutaciones y cartera.")
    ap.add_argument("etapa", nargs="?", default="todo", choices=("etapa1", "etapa2", "etapa3_4", "todo"))
    ap.add_argument("--workers", type=int, default=2, help="Workers paralelos (default 2)")
    args = ap.parse_args(argv)
    ejecutar_iter2(etapa=args.etapa, workers=args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Iteracion 3 FUNDEDSYNC: matriz 15x6 multi-activo y adaptacion estructural para Oro (GC) e indices.

Uso:
  python tools/fundedsync_multiactivo_oro.py etapa_a [--workers 2]
  python tools/fundedsync_multiactivo_oro.py etapa_b [--workers 2]
  python tools/fundedsync_multiactivo_oro.py etapa_c [--workers 2]
  python tools/fundedsync_multiactivo_oro.py todo [--workers 2]
"""
from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import gc
import json
import math
import shutil
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

import fundedsync_iter2_cartera as IT2
import fundedsync_post_il_cadena as BASE
import lucid_guia as LG
from edgelab import costos
from edgelab.holdout import a5_bloque
from edgelab.research import diagnostico_grilla as DG
from edgelab.research.m1_intradia import leer_m1nt8
from edgelab.research.puerta_corrida import verificar_corrida
from m1_largo import _sesion
from registro_global import exigir_contada

PREREG_REL = "docs/research/fundedsync_multiactivo_oro_20261122/PREREGISTRO.md"
OUT_DIR = ROOT / "docs/research/fundedsync_multiactivo_oro_20261122"
CACHE_DIR = BASE.CACHE_DIR
ARTIFACTS_DIR = BASE.ARTIFACTS_DIR

ACTIVOS_TODOS: tuple[str, ...] = ("NQ", "ES", "YM", "RTY", "GC", "EMD")
ACTIVOS_MEDIDOS: tuple[str, ...] = ("NQ", "ES", "YM", "RTY", "GC")
ACTIVOS_EXT: tuple[str, ...] = ("ES", "YM", "RTY", "EMD")
MODULOS_ORDEN: tuple[str, ...] = ("A1", "A20", "F", "S", "P", "C", "V", "O", "W", "N", "T", "R", "Z", "E", "Q")
MICRO_MAP: dict[str, str] = {**BASE.MICRO_EQUIV, "GC": "MGC"}

# Mediana ATR20 (rango diario NY 2020+) medida sobre los parquets locales para reescalar B2
ATR_REF_2020: dict[str, float] = {
    "NQ": 258.05,
    "ES": 58.08,
    "YM": 420.95,
    "RTY": 37.18,
    "GC": 27.01,
    "EMD": 40.52,
}


def asegurar_compuerta_iter3() -> None:
    """Verifica K51 y compuerta L1..L4 para PREREGISTRO de iteracion 3."""
    exigir_contada(PREREG_REL)
    rep = verificar_corrida(
        prereg=PREREG_REL,
        familia="FUNDEDSYNC",
        exigir_contada=True,
        verificar_estado=True,
        root=ROOT,
    )
    if not rep["ok"]:
        raise SystemExit("puerta_corrida bloqueo iter3: " + "; ".join(rep["errores"]))


def friccion_multiactivo(inst: str) -> tuple[float, float | None]:
    """Devuelve `(fric_mini_pts, fric_micro_pts)` reutilizando `BASE.friccion_instrumento_puntos` con `MGC` y K33."""
    return BASE.friccion_instrumento_puntos(inst, prereg_rel=PREREG_REL, micro_equiv=MICRO_MAP)


def _usd_pt_micro_ma(inst: str) -> float:
    sym = inst.upper()
    tgt = MICRO_MAP.get(sym, sym)
    return float(costos.tick_value_usd(tgt) / costos.tick_size(tgt))


def cargar_orb_ventanas(
    inst: str,
    ventanas: list[tuple[int, int]],
    *,
    m1_dir: Path | None = None,
    desde: str = "2008-01-01",
) -> dict[tuple[int, int], pd.Series]:
    """Calcula rango ORB crudo para varias ventanas ET en una sola lectura del parquet."""
    d_ny = leer_m1nt8(BASE._resolver_parquet(inst, m1_dir=m1_dir))
    d_ny = d_ny[d_ny.index >= desde]
    mm = d_ny.index.hour * 60 + d_ny.index.minute
    out: dict[tuple[int, int], pd.Series] = {}
    for w_ini, w_fin in sorted(set(ventanas)):
        sub = d_ny[(mm >= int(w_ini)) & (mm < int(w_fin))]
        dd = sub.index.normalize()
        out[(int(w_ini), int(w_fin))] = sub.h.groupby(dd).max() - sub.l.groupby(dd).min()
    del d_ny, mm
    gc.collect()
    return out


def _resolver_riesgo_y_pnl(
    pp: np.ndarray,
    mae_pts: np.ndarray,
    nat_stop: np.ndarray,
    atr_vec: np.ndarray,
    *,
    stop_atr_k: float | None,
    cap_mae_atr_k: float | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Aplica regla de stop ATR o tope MAE causal sobre riesgo natural."""
    if stop_atr_k is not None:
        riesgo = float(stop_atr_k) * atr_vec
        pnl_eff = np.where(mae_pts >= riesgo, -riesgo, pp)
        return riesgo, pnl_eff
    if cap_mae_atr_k is not None:
        cap_pts = float(cap_mae_atr_k) * atr_vec
        riesgo = np.where(np.isfinite(nat_stop) & (nat_stop > 0.0), np.minimum(nat_stop, cap_pts), cap_pts)
        pnl_eff = np.where(mae_pts >= cap_pts, -cap_pts, pp)
        return riesgo, pnl_eff
    riesgo = np.where(np.isfinite(nat_stop) & (nat_stop > 0.0), nat_stop, 0.5 * atr_vec)
    return riesgo, pp


def convertir_ops_activo(
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
    stop_min_pts: float = 2.0,
    stop_max_pts: float = 100.0,
) -> pd.DataFrame:
    """Normaliza trades a R usando friccion real por activo (`MGC` para `GC`) y ventana ORB dinamica."""
    if df_trades is None or len(df_trades) == 0:
        return IT2._empty_ops_enr()

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
    fin = ratio_pv[np.isfinite(ratio_pv) & (ratio_pv > 0.0)]
    pv_unit = float(np.median(fin)) if len(fin) else (float(pv_base / 10.0) if modulo == "Q" else float(pv_base))
    denom = np.maximum(qt * pv_unit, 1e-9)
    mae_pts = mae_u / denom
    mfe_pts = mfe_u / denom

    en_px = pd.to_numeric(df_trades["entry_price"], errors="coerce").to_numpy(dtype=float)
    st_px = pd.to_numeric(df_trades["stop_price"], errors="coerce").to_numpy(dtype=float)
    nat_stop = np.abs(en_px - st_px)

    if modulo == "T" and len(orb_raw):
        orb_scaled = (orb_raw.reindex(pd.DatetimeIndex(tt_ny).normalize()) * float(stop_orb_mult)).clip(
            float(stop_min_pts), float(stop_max_pts)
        ).to_numpy(dtype=float)
        nat_stop = np.where(np.isfinite(orb_scaled) & (orb_scaled > 0.0), orb_scaled, nat_stop)

    riesgo, pnl_eff = _resolver_riesgo_y_pnl(
        pp, mae_pts, nat_stop, atr_vec,
        stop_atr_k=stop_atr_k, cap_mae_atr_k=cap_mae_atr_k,
    )

    fecha_int = pd.DatetimeIndex(ses).strftime("%Y%m%d").astype(int)
    a5_labels = np.array([a5_bloque(int(f)) for f in fecha_int], dtype=object)
    ok = np.isfinite(riesgo) & (riesgo > 1e-6) & np.isfinite(pnl_eff) & (a5_labels != "TERMINAL")
    if not ok.any():
        return IT2._empty_ops_enr()

    fric_mini, fric_micro = friccion_multiactivo(inst)
    riesgo_k = riesgo[ok]
    pnl_k = pnl_eff[ok]
    return pd.DataFrame({
        "fecha_int": fecha_int[ok],
        "mes": pd.DatetimeIndex(ses)[ok].strftime("%Y-%m"),
        "a5": a5_labels[ok],
        "en_ns": en_utc.astype("int64").to_numpy()[ok],
        "ex_ns": ex_utc.astype("int64").to_numpy()[ok],
        "dur_min": ((ex_utc - en_utc).dt.total_seconds() / 60.0).to_numpy(dtype=float)[ok],
        "pnl_pts": pnl_k,
        "mae_pts": mae_pts[ok],
        "mfe_pts": mfe_pts[ok],
        "riesgo_pts": riesgo_k,
        "R_bruto": pnl_k / riesgo_k,
        "R_neto_mini": (pnl_k - fric_mini) / riesgo_k,
        "R_neto_micro": ((pnl_k - fric_micro) / riesgo_k) if fric_micro is not None else np.full_like(riesgo_k, np.nan),
        "fric_R": fric_mini / riesgo_k,
        "side": df_trades["side"].to_numpy(dtype=int)[ok],
    })


def _specs_etapa_a_gc_nucleo() -> list[dict[str, Any]]:
    """Las 7 variantes validadas de Iter 1/2 evaluadas directo sobre Oro GC (sin adaptar)."""
    return [
        {"modulo": "R", "variante": "R_maeATR50_nq", "params": {}, "stop_atr_k": 0.50, "cap_mae_atr_k": None, "orb_win": (570, 585), "stop_orb_mult": 1.25, "stop_min_pts": 2.0, "stop_max_pts": 100.0},
        {"modulo": "R", "variante": "R_maeATR25_nq", "params": {}, "stop_atr_k": 0.25, "cap_mae_atr_k": None, "orb_win": (570, 585), "stop_orb_mult": 1.25, "stop_min_pts": 2.0, "stop_max_pts": 100.0},
        {"modulo": "Z", "variante": "Z_maeATR50_nq", "params": {}, "stop_atr_k": 0.50, "cap_mae_atr_k": None, "orb_win": (570, 585), "stop_orb_mult": 1.25, "stop_min_pts": 2.0, "stop_max_pts": 100.0},
        {"modulo": "T", "variante": "T_stop100_nq", "params": {"stop_orb_multiplier": 1.0}, "stop_atr_k": None, "cap_mae_atr_k": None, "orb_win": (570, 585), "stop_orb_mult": 1.0, "stop_min_pts": 2.0, "stop_max_pts": 100.0},
        {"modulo": "V", "variante": "V_nm30_maeATR30_nq", "params": {"noise_multiplier": 0.30, "vwap_exit_bars": 2, "profit_target_usd_per_contract": 1400.0}, "stop_atr_k": None, "cap_mae_atr_k": 0.30, "orb_win": (570, 585), "stop_orb_mult": 1.25, "stop_min_pts": 2.0, "stop_max_pts": 100.0},
        {"modulo": "W", "variante": "W_eod_slope_ATR25_nq", "params": {"exit_on_vwap_cross": False, "allow_reentries": False, "use_vwap_slope_filter": True}, "stop_atr_k": 0.25, "cap_mae_atr_k": None, "orb_win": (570, 585), "stop_orb_mult": 1.25, "stop_min_pts": 2.0, "stop_max_pts": 100.0},
        {"modulo": "N", "variante": "N_fab_maeATR25_nq", "params": {}, "stop_atr_k": 0.25, "cap_mae_atr_k": None, "orb_win": (570, 585), "stop_orb_mult": 1.25, "stop_min_pts": 2.0, "stop_max_pts": 100.0},
    ]


def specs_etapa_b1_oro() -> list[dict[str, Any]]:
    """Presupuesto exacto PREREGISTRO Etapa B1: 60 variantes adaptadas para Oro (GC) en 5 grillas."""
    specs: list[dict[str, Any]] = []

    def _add(
        grilla: str, mod: str, var: str, params: dict[str, Any], perillas: dict[str, str],
        *, stop_atr_k: float | None = None, cap_mae_atr_k: float | None = None,
        orb_win: tuple[int, int] = (570, 585), stop_orb_mult: float = 1.25,
        stop_min_pts: float = 2.0, stop_max_pts: float = 100.0,
    ) -> None:
        specs.append({
            "grilla": grilla, "modulo": mod, "variante": var, "params": params, "perillas": perillas,
            "stop_atr_k": stop_atr_k, "cap_mae_atr_k": cap_mae_atr_k, "orb_win": orb_win,
            "stop_orb_mult": stop_orb_mult, "stop_min_pts": stop_min_pts, "stop_max_pts": stop_max_pts,
        })

    # 1) GC_ORB_TREND (14)
    for cl_lbl, qh, cond, cash in (("1330", 540, 780, 810), ("1600", 540, 930, 960)):
        for m in (1.0, 1.25, 1.5):
            _add(
                "GC_ORB_TREND", "T", f"T_gc_comex{cl_lbl}_m{int(round(m*100))}",
                {
                    "orb_start_minute_et": 510, "orb_end_minute_et": 525, "quarter_hour_start_minute_et": qh,
                    "conditional_exit_minute_et": cond, "cash_close_minute_et": cash,
                    "stop_min_points": 0.5, "stop_max_points": 15.0, "stop_orb_multiplier": m,
                    "use_exclusion_calendars": False,
                },
                {"mod": "T", "ventana": f"comex_{cl_lbl}", "escala": f"m{m}"},
                orb_win=(510, 525), stop_orb_mult=m, stop_min_pts=0.5, stop_max_pts=15.0,
            )
    for m in (1.0, 1.25):
        _add(
            "GC_ORB_TREND", "T", f"T_gc_nyse_m{int(round(m*100))}",
            {"stop_min_points": 0.5, "stop_max_points": 15.0, "stop_orb_multiplier": m, "use_exclusion_calendars": False},
            {"mod": "T", "ventana": "nyse_0930", "escala": f"m{m}"},
            orb_win=(570, 585), stop_orb_mult=m, stop_min_pts=0.5, stop_max_pts=15.0,
        )
        _add(
            "GC_ORB_TREND", "T", f"T_gc_lon0300_m{int(round(m*100))}",
            {
                "orb_start_minute_et": 180, "orb_end_minute_et": 195, "quarter_hour_start_minute_et": 210,
                "conditional_exit_minute_et": 780, "cash_close_minute_et": 810,
                "stop_min_points": 0.5, "stop_max_points": 10.0, "stop_orb_multiplier": m,
                "use_exclusion_calendars": False,
            },
            {"mod": "T", "ventana": "lon_0300", "escala": f"m{m}"},
            orb_win=(180, 195), stop_orb_mult=m, stop_min_pts=0.5, stop_max_pts=10.0,
        )
    for sm in (20, 30):
        for rr in (1.5, 2.5):
            _add(
                "GC_ORB_TREND", "F", f"F_gc_07{sm}_rr{int(rr*10)}",
                {"start_h": 7, "start_m": sm, "end_h": 12, "end_m": 30, "max_initial_risk_points": 14.0, "disable_delta_filter": True, "tp_rr": rr},
                {"mod": "F", "ventana": f"07{sm}_CT", "escala": f"rr{rr}"},
            )

    # 2) GC_ATR_ZETA (14)
    r_win = {
        "comex": {"entry_start_min_et": 500, "entry_end_min_et": 600, "rth_vwap_start_min_et": 500, "rth_vwap_end_min_et": 810, "cash_close_min_et": 810},
        "full": {"entry_start_min_et": 510, "entry_end_min_et": 660, "rth_vwap_start_min_et": 510, "rth_vwap_end_min_et": 960, "cash_close_min_et": 960},
    }
    for wlbl, wcfg in r_win.items():
        for om in (2.0, 3.0):
            for ka in (0.25, 0.50):
                _add(
                    "GC_ATR_ZETA", "R", f"R_gc_{wlbl}_osc{int(om*10)}_ATR{int(ka*100)}",
                    {**wcfg, "osc_atr_mult": om, "roll_gap_ticks": 200.0, "blocked_sessions": ()},
                    {"mod": "R", "ventana": f"r_{wlbl}", "atr": str(ka)},
                    stop_atr_k=ka,
                )
    for eff in (35.0, 45.0):
        for ka in (0.25, 0.50):
            _add(
                "GC_ATR_ZETA", "Z", f"Z_gc_comex_eff{int(eff)}_ATR{int(ka*100)}",
                {"session_start_min_ct": 450, "session_end_min_ct": 750, "min_efficiency_pct": eff, "non_full_nyse": ()},
                {"mod": "Z", "ventana": f"z_comex_e{int(eff)}", "atr": str(ka)},
                stop_atr_k=ka,
            )
    for ka in (0.25, 0.50):
        _add(
            "GC_ATR_ZETA", "Z", f"Z_gc_full_eff40_ATR{int(ka*100)}",
            {"session_start_min_ct": 450, "session_end_min_ct": 840, "min_efficiency_pct": 40.0, "non_full_nyse": ()},
            {"mod": "Z", "ventana": "z_full_e40", "atr": str(ka)},
            stop_atr_k=ka,
        )

    # 3) GC_VWAP_NDAY (12)
    for slp in (False, True):
        slbl = "sl" if slp else "nosl"
        for ka in (0.25, 0.50):
            _add(
                "GC_VWAP_NDAY", "W", f"W_gc_comex_{slbl}_ATR{int(ka*100)}",
                {"vwap_start_time_central": 72000, "vwap_end_time_central": 123000, "initial_entry_boundary_central": 72100, "last_entry_time_central": 113000, "exit_on_vwap_cross": False, "allow_reentries": False, "use_vwap_slope_filter": slp},
                {"mod": f"W_{slbl}", "escala": f"comex_atr{ka}"},
                stop_atr_k=ka,
            )
        _add(
            "GC_VWAP_NDAY", "W", f"W_gc_full_{slbl}_ATR35",
            {"vwap_start_time_central": 73000, "vwap_end_time_central": 140000, "initial_entry_boundary_central": 73100, "last_entry_time_central": 130000, "exit_on_vwap_cross": False, "allow_reentries": False, "use_vwap_slope_filter": slp},
            {"mod": f"W_{slbl}", "escala": "full_atr0.35"},
            stop_atr_k=0.35,
        )
    for nd in (3, 5, 10):
        for ka in (0.25, 0.50):
            _add(
                "GC_VWAP_NDAY", "N", f"N_gc_d{nd}_ATR{int(ka*100)}",
                {"num_days": nd, "acceptance_buffer_points": 0.4},
                {"mod": "N", "escala": f"d{nd}_atr{ka}"},
                stop_atr_k=ka,
            )

    # 4) GC_SCALE_VCE (12)
    for nm in (0.30, 0.40, 0.50):
        for cap_k, clbl in ((None, "raw"), (0.35, "mae35")):
            _add(
                "GC_SCALE_VCE", "V", f"V_gc_nm{int(nm*100)}_{clbl}",
                {"noise_multiplier": nm, "block_entry_hour_enabled": False, "profit_target_usd_per_contract": 200.0, "stop_loss_usd_per_contract": 300.0, "vwap_exit_bars": 2},
                {"mod": "V", "nivel": f"nm{nm}_{clbl}"},
                cap_mae_atr_k=cap_k,
            )
    for sl_p, tp_p in ((3.5, 5.5), (5.0, 7.5), (5.0, 10.0), (7.0, 10.5)):
        _add(
            "GC_SCALE_VCE", "E", f"E_gc_sl{int(round(sl_p*10))}_tp{int(round(tp_p*10))}",
            {"stop_points": sl_p, "target_points": tp_p, "historical_minute14_delay": False},
            {"mod": "E", "nivel": f"{sl_p}/{tp_p}"},
        )
    for sh_on, dlbl in ((False, "long60"), (True, "both60")):
        _add(
            "GC_SCALE_VCE", "C", f"C_gc_{dlbl}",
            {"minimum_gap_points": 0.3, "stop_loss_amount": 160.0, "profit_target_amount": 260.0, "entry_start_offset_minutes": 60, "enable_short_entries": sh_on},
            {"mod": "C", "nivel": dlbl},
        )

    # 5) GC_DIR_QASO (8)
    for sh, sm, eh, em in ((8, 0, 8, 35), (8, 20, 8, 55)):
        _add(
            "GC_DIR_QASO", "Q", f"Q_gc_{sh:02d}{sm:02d}_{eh:02d}{em:02d}",
            {"range_start_hour": sh, "range_start_minute": sm, "range_end_hour": eh, "range_end_minute": em, "break_margin_ticks": 3, "risk_reward": 1.5, "force_close_hour": 13, "force_close_minute": 30},
            {"mod": "Q", "regla": f"r_{sh}{sm:02d}"},
        )
    for al_l, al_s, dlbl in ((True, False, "long"), (False, True, "short"), (True, True, "both")):
        _add(
            "GC_DIR_QASO", "A20", f"A20_gc_{dlbl}",
            {"allow_longs": al_l, "allow_shorts": al_s, "require_supertrend_entry_alignment": True, "hard_stop_atr_mult": 2.5, "session_start_hour": 7, "session_start_minute": 20, "session_end_hour": 13, "session_end_minute": 30},
            {"mod": "A20", "regla": dlbl},
        )
    _add(
        "GC_DIR_QASO", "S", "S_gc_comex_stAlign",
        {"ny_open_hour": 8, "ny_open_minute": 20, "require_supertrend_entry_alignment": True},
        {"mod": "S", "regla": "comex_stAlign"},
        stop_atr_k=0.50,
    )
    for tr_on in (True, False):
        _add(
            "GC_DIR_QASO", "O", f"O_gc_trend{'On' if tr_on else 'Off'}",
            {"exit_time_central": 72000, "use_trend_filter": tr_on},
            {"mod": "O", "regla": f"trend_{tr_on}"},
            stop_atr_k=0.50,
        )

    assert len(specs) == 60, f"Se esperaban 60 specs B1, hay {len(specs)}"
    return specs


def specs_etapa_b2_indices() -> list[dict[str, Any]]:
    """Presupuesto exacto PREREGISTRO Etapa B2: 12 variantes escaladas x 4 indices = 48 pruebas."""
    specs: list[dict[str, Any]] = []
    for inst in ACTIVOS_EXT:
        atr = ATR_REF_2020[inst]
        tick = float(costos.tick_size(inst))
        v_tp = round(round(0.271 * atr, 1) * 20.0, 1)
        v_sl = round(round(0.388 * atr, 1) * 20.0, 1)
        t_min = round(max(0.01 * atr, 2.0 * tick), 1)
        t_max = round(0.50 * atr, 1)
        c_sl = round(round(0.291 * atr, 1) * 20.0, 1)
        c_tp = round(round(0.484 * atr, 1) * 20.0, 1)
        c_gap = max(round(0.008 * atr, 1), tick)
        n_buf = max(round(0.015 * atr, 1), tick)

        plantillas = [
            ("V", "V_scaled_nm30", {"noise_multiplier": 0.30, "vwap_exit_bars": 2, "profit_target_usd_per_contract": v_tp, "stop_loss_usd_per_contract": v_sl}, None, 0.35, 1.25, 2.0, 100.0),
            ("V", "V_scaled_nm40", {"noise_multiplier": 0.40, "vwap_exit_bars": 2, "profit_target_usd_per_contract": v_tp, "stop_loss_usd_per_contract": v_sl}, None, 0.35, 1.25, 2.0, 100.0),
            ("E", "E_scaled_tight", {"stop_points": round(0.12 * atr, 1), "target_points": round(0.18 * atr, 1), "historical_minute14_delay": False}, None, None, 1.25, 2.0, 100.0),
            ("E", "E_scaled_wide", {"stop_points": round(0.18 * atr, 1), "target_points": round(0.30 * atr, 1), "historical_minute14_delay": False}, None, None, 1.25, 2.0, 100.0),
            ("T", "T_scaled_100", {"stop_min_points": t_min, "stop_max_points": t_max, "stop_orb_multiplier": 1.0}, None, None, 1.0, t_min, t_max),
            ("T", "T_scaled_125", {"stop_min_points": t_min, "stop_max_points": t_max, "stop_orb_multiplier": 1.25}, None, None, 1.25, t_min, t_max),
            ("N", "N_scaled_ATR25", {"acceptance_buffer_points": n_buf}, 0.25, None, 1.25, 2.0, 100.0),
            ("R", "R_osc20_ATR50", {"osc_atr_mult": 2.0}, 0.50, None, 1.25, 2.0, 100.0),
            ("R", "R_osc25_ATR35", {"osc_atr_mult": 2.5}, 0.35, None, 1.25, 2.0, 100.0),
            ("Z", "Z_eff35_ATR50", {"min_efficiency_pct": 35.0}, 0.50, None, 1.25, 2.0, 100.0),
            ("W", "W_eod_ATR35", {"exit_on_vwap_cross": False, "allow_reentries": False}, 0.35, None, 1.25, 2.0, 100.0),
            ("C", "C_scaled_long60", {"minimum_gap_points": c_gap, "stop_loss_amount": c_sl, "profit_target_amount": c_tp, "entry_start_offset_minutes": 60}, None, None, 1.25, 2.0, 100.0),
        ]
        for mod, vname, params, ka, capk, mult, smin, smax in plantillas:
            specs.append({
                "grilla": f"IND_{inst}", "instrumento": inst, "modulo": mod, "variante": f"{inst}__{vname}",
                "variante_base": vname, "params": params, "perillas": {"mod": mod, "variante": vname},
                "stop_atr_k": ka, "cap_mae_atr_k": capk, "orb_win": (570, 585),
                "stop_orb_mult": mult, "stop_min_pts": smin, "stop_max_pts": smax,
            })
    assert len(specs) == 48, f"Se esperaban 48 specs B2, hay {len(specs)}"
    return specs


def _clasificar_etapa_a(df_a: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Clasifica cada modulo de fabrica en MULTI_ACTIVO / ORO_NATIVO / ESPECIFICO_NQ / SIN_VENTAJA_BASE."""
    p20 = df_a[(df_a["periodo"] == "POST_2020") & (df_a["variante"] == "fabrica")].copy()
    clasif: dict[str, dict[str, Any]] = {}
    for mod in MODULOS_ORDEN:
        sub = p20[p20["modulo"] == mod]
        buenos_med: list[str] = []
        for inst in ACTIVOS_MEDIDOS:
            d_row = sub[(sub["instrumento"] == inst) & (sub["particion_a5"] == "DESC")]
            r_row = sub[(sub["instrumento"] == inst) & (sub["particion_a5"] == "REP")]
            if not d_row.empty and not r_row.empty:
                ok_d = int(d_row.iloc[0]["n"]) >= 20 and float(d_row.iloc[0]["R_neto_mini"]) > 0.0 and float(d_row.iloc[0]["med_fric_R"]) <= 0.12
                ok_r = int(r_row.iloc[0]["n"]) >= 8 and float(r_row.iloc[0]["R_neto_mini"]) > 0.0
                if ok_d and ok_r:
                    buenos_med.append(inst)
        if len(buenos_med) >= 2:
            cat = "MULTI_ACTIVO"
        elif buenos_med == ["GC"]:
            cat = "ORO_NATIVO"
        elif buenos_med == ["NQ"]:
            cat = "ESPECIFICO_NQ"
        elif "GC" in buenos_med:
            cat = "MULTI_ACTIVO"
        else:
            cat = "SIN_VENTAJA_BASE"
        clasif[mod] = {"categoria": cat, "activos_confirmados": buenos_med}
    return clasif


def _correr_etapa_a(workers: int = 2, m1_dir: Path | None = None) -> pd.DataFrame:
    """Ejecuta matriz base 15x6 de fabrica + 7 nucleo Iter 1/2 en GC (DESC/REP, FULL_2008/POST_2020)."""
    m1_str = str(m1_dir) if m1_dir is not None else None
    gc_ext = _specs_etapa_a_gc_nucleo()
    tasks: list[tuple[str, list[tuple[str, str, dict[str, Any]]], str | None]] = []
    for inst in ACTIVOS_TODOS:
        jobs_i: list[tuple[str, str, dict[str, Any]]] = []
        seen: set[str] = set()
        for mod in MODULOS_ORDEN:
            cname = BASE._cache_key(inst, mod, None)
            if cname not in seen and not (CACHE_DIR / f"{cname}.pkl").exists():
                seen.add(cname)
                jobs_i.append((cname, mod, {}))
        if inst == "GC":
            for sp in gc_ext:
                cname = BASE._cache_key("GC", sp["modulo"], sp["params"])
                if cname not in seen and not (CACHE_DIR / f"{cname}.pkl").exists():
                    seen.add(cname)
                    jobs_i.append((cname, sp["modulo"], sp["params"]))
        if jobs_i:
            # A1 primero para balancear workers sin bloqueos largos al final
            jobs_i.sort(key=lambda j: (-BASE._PESO_MOD_ORDEN.get(j[1], 20), j[0]))
            tasks.append((inst, jobs_i, m1_str))

    if tasks:
        n_w = min(max(int(workers), 1), len(tasks))
        print(f"[ETAPA A] Corriendo matriz base para {len(tasks)} activos con workers={n_w}...", flush=True)
        if n_w == 1:
            for ta in tasks:
                for cname, n_tr, dt in BASE._run_instrumento_b4_worker(ta):
                    print(f"  [ETAPA A RUN] {cname}: n={n_tr} ({dt:.1f}s)", flush=True)
        else:
            with concurrent.futures.ProcessPoolExecutor(max_workers=n_w) as ex:
                for logs in ex.map(BASE._run_instrumento_b4_worker, tasks):
                    for cname, n_tr, dt in logs:
                        print(f"  [ETAPA A RUN] {cname}: n={n_tr} ({dt:.1f}s)", flush=True)
    else:
        print("[CACHE] Etapa A completa en disco.", flush=True)

    rows: list[dict[str, Any]] = []
    for inst in ACTIVOS_TODOS:
        atr_i, _, pv_i, start_i = BASE._cargar_series_sesion(inst, m1_dir=m1_dir)
        orb_raw_i = cargar_orb_ventanas(inst, [(570, 585)], m1_dir=m1_dir)[(570, 585)]
        items = [
            {"modulo": m, "variante": "fabrica", "params": {}, "stop_atr_k": BASE.STOP_ATR_DEFAULT[m], "cap_mae_atr_k": None, "stop_orb_mult": 1.25, "stop_min_pts": 2.0, "stop_max_pts": 100.0}
            for m in MODULOS_ORDEN
        ]
        if inst == "GC":
            items.extend(gc_ext)
        for sp in items:
            mod = str(sp["modulo"])
            cname = BASE._cache_key(inst, mod, sp["params"] if sp["params"] else None)
            df_t = BASE._cargar_trades_cacheados(cname)
            ops = convertir_ops_activo(
                df_t, mod, inst, atr_i, orb_raw_i, pv_i,
                stop_atr_k=sp["stop_atr_k"], cap_mae_atr_k=sp["cap_mae_atr_k"],
                stop_orb_mult=sp["stop_orb_mult"], stop_min_pts=sp["stop_min_pts"], stop_max_pts=sp["stop_max_pts"],
            )
            ops_safe = ops[ops["a5"].isin(("DESC", "REP"))]
            for part in ("DESC", "REP"):
                sub_f = ops_safe[ops_safe["a5"] == part]
                sub_20 = sub_f[sub_f["fecha_int"] >= 20200101]
                sub_21 = sub_f[sub_f["fecha_int"] >= 20210101]
                st21 = BASE.resumir_serie_r(sub_21, meses_totales=BASE._meses_activos_a5(max(start_i, 20210101), 20260930, part))
                for per_nom, sub_p, d0 in (("FULL_2008", sub_f, start_i), ("POST_2020", sub_20, max(start_i, 20200101))):
                    mtot = BASE._meses_activos_a5(d0, 20260930, part)
                    st = BASE.resumir_serie_r(sub_p, meses_totales=mtot)
                    dd_m = IT2._metricas_dd_r(sub_p, mtot)
                    rows.append({
                        "instrumento": inst, "spread_estimado": inst == "EMD", "modulo": mod,
                        "variante": sp["variante"], "particion_a5": part, "periodo": per_nom,
                        **st, **dd_m, "n_2021": st21["n"], "R_neto_2021": st21["R_neto_mini"], "R_mes_2021": st21["R_por_mes"],
                    })

    df_a = pd.DataFrame(rows)
    df_a.to_csv(OUT_DIR / "etapa_a_matriz_base_15x6.csv", index=False)
    return df_a


def _evaluar_variantes_inst(
    inst: str,
    specs: list[dict[str, Any]],
    fechas_desc_20: list[int],
    atr_i: pd.Series,
    orb_map: Mapping[tuple[int, int], pd.Series],
    pv_i: float,
    start_i: int,
    *,
    scope_perm: str,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, pd.DataFrame]]:
    """Evalua variantes en DESC (FULL_2008 y POST_2020), calcula K55/K56 y permutaciones."""
    m_desc_full = BASE._meses_activos_a5(start_i, 20260930, "DESC")
    m_desc_20 = BASE._meses_activos_a5(max(start_i, 20200101), 20260930, "DESC")
    m_desc_21 = BASE._meses_activos_a5(max(start_i, 20210101), 20260930, "DESC")

    rows: list[dict[str, Any]] = []
    por_g_full: dict[str, list[pd.DataFrame]] = {}
    por_g_20: dict[str, list[pd.DataFrame]] = {}
    por_g_per: dict[str, dict[str, dict[str, str]]] = {}
    ops_safe_map: dict[str, pd.DataFrame] = {}
    daily_20_map: dict[str, pd.Series] = {}
    monthly_20_all: list[pd.DataFrame] = []

    for sp in specs:
        mod = str(sp["modulo"])
        cname = BASE._cache_key(inst, mod, sp["params"] if sp["params"] else None)
        df_t = BASE._cargar_trades_cacheados(cname)
        orb_raw = orb_map.get(sp["orb_win"], pd.Series(dtype=float))
        ops_full = convertir_ops_activo(
            df_t, mod, inst, atr_i, orb_raw, pv_i,
            stop_atr_k=sp["stop_atr_k"], cap_mae_atr_k=sp["cap_mae_atr_k"],
            stop_orb_mult=sp["stop_orb_mult"], stop_min_pts=sp["stop_min_pts"], stop_max_pts=sp["stop_max_pts"],
        )
        ops_safe = ops_full[ops_full["a5"].isin(("DESC", "REP"))].copy()
        ops_safe_map[sp["variante"]] = ops_safe
        ops_desc = ops_safe[ops_safe["a5"] == "DESC"]
        ops_20 = ops_desc[ops_desc["fecha_int"] >= 20200101]
        ops_21 = ops_desc[ops_desc["fecha_int"] >= 20210101]

        st = BASE.resumir_serie_r(ops_desc, meses_totales=m_desc_full)
        st20 = BASE.resumir_serie_r(ops_20, meses_totales=m_desc_20)
        st21 = BASE.resumir_serie_r(ops_21, meses_totales=m_desc_21)
        dd20 = IT2._metricas_dd_r(ops_20, m_desc_20)

        rows.append({
            "scope": scope_perm,
            "grilla": sp["grilla"],
            "instrumento": inst,
            "spread_estimado": inst == "EMD",
            "modulo": mod,
            "variante": sp["variante"],
            "params_json": json.dumps(sp["params"], sort_keys=True),
            "stop_atr_k": sp["stop_atr_k"],
            "cap_mae_atr_k": sp["cap_mae_atr_k"],
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
        })

        daily_20_map[sp["variante"]] = ops_20.groupby("fecha_int")["R_neto_mini"].sum() if len(ops_20) else pd.Series(dtype=float)
        g = str(sp["grilla"])
        por_g_full.setdefault(g, [])
        por_g_20.setdefault(g, [])
        if not ops_desc.empty:
            por_g_full[g].append(ops_desc[["R_neto_mini", "mes"]].rename(columns={"R_neto_mini": "R"}).assign(variante=sp["variante"]))
        if not ops_20.empty:
            chk = ops_20[["R_neto_mini", "mes"]].rename(columns={"R_neto_mini": "R"}).assign(variante=sp["variante"])
            por_g_20[g].append(chk)
            monthly_20_all.append(chk)
        por_g_per.setdefault(g, {})[sp["variante"]] = sp["perillas"]

    diags: dict[str, Any] = {}
    degen20: set[str] = set()
    for g in por_g_per:
        df_g = pd.concat(por_g_full[g], ignore_index=True) if por_g_full[g] else pd.DataFrame()
        df_g20 = pd.concat(por_g_20[g], ignore_index=True) if por_g_20[g] else pd.DataFrame()
        pmap = por_g_per[g]
        pnames = list(next(iter(pmap.values())).keys())
        per_fn = {pn: (lambda v, pn=pn, pmap=pmap: pmap[v][pn]) for pn in pnames}
        d_full = BASE._diagnostico_con_mejor(df_g, per_fn, total_celdas=len(pmap)) if not df_g.empty else {"celdas_cero_ops": len(pmap), "degeneradas": list(pmap), "linea": "Diagnóstico de grilla: 0 operaciones."}
        d_20 = BASE._diagnostico_con_mejor(df_g20, per_fn, total_celdas=len(pmap)) if not df_g20.empty else {"celdas_cero_ops": len(pmap), "degeneradas": list(pmap), "linea": "Diagnóstico de grilla: 0 operaciones."}
        d_full["post_2020"] = d_20
        diags[g] = d_full
        degen20 |= set(d_20.get("degeneradas", []))

    df_all20 = pd.concat(monthly_20_all, ignore_index=True) if monthly_20_all else pd.DataFrame(columns=["mes", "variante", "R"])
    m_all = df_all20.groupby(["mes", "variante"])["R"].sum().unstack().fillna(0.0) if len(df_all20) else pd.DataFrame()
    neff = round(DG.numero_efectivo(m_all), 2) if m_all.shape[1] >= 2 else max(float(m_all.shape[1]), 2.0)

    df_perm = IT2.calcular_bateria_permutaciones(daily_20_map, fechas_desc_20, n_eff=neff, n_perm=5000)
    df_out = pd.DataFrame(rows).merge(df_perm, on="variante", how="left")
    df_out["neff_scope"] = neff
    df_out["degenerada_2020"] = df_out["variante"].isin(degen20) | (df_out["n_2020"] < 30)
    df_out["pasa_desc"] = (
        (~df_out["degenerada_2020"])
        & (df_out["R_neto_2020"] > 0.0)
        & (df_out["p_perm"] < 0.05)
        & (df_out["med_fric_R_2020"] <= 0.12)
    )
    return df_out, diags, ops_safe_map


def _correr_etapa_b(
    workers: int = 2, m1_dir: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, pd.DataFrame]]:
    """Ejecuta Etapa B1 (Oro GC) y Etapa B2 (ES/YM/RTY/EMD) + confirmacion congelada REP."""
    specs_gc = specs_etapa_b1_oro()
    specs_b2 = specs_etapa_b2_indices()

    # 1) Precalentar GC (2 workers sobre GC si faltan varios)
    jobs_gc_map: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for sp in specs_gc:
        cname = BASE._cache_key("GC", sp["modulo"], sp["params"])
        jobs_gc_map[cname] = (cname, sp["modulo"], sp["params"])
    IT2._precalentar_jobs("GC", list(jobs_gc_map.values()), workers=workers, m1_dir=m1_dir)

    # 2) Precalentar B2 por instrumento en paralelo
    m1_str = str(m1_dir) if m1_dir is not None else None
    tasks_b2: list[tuple[str, list[tuple[str, str, dict[str, Any]]], str | None]] = []
    for inst in ACTIVOS_EXT:
        j_map: dict[str, tuple[str, str, dict[str, Any]]] = {}
        for sp in specs_b2:
            if sp["instrumento"] == inst:
                cname = BASE._cache_key(inst, sp["modulo"], sp["params"])
                if not (CACHE_DIR / f"{cname}.pkl").exists():
                    j_map[cname] = (cname, sp["modulo"], sp["params"])
        if j_map:
            tasks_b2.append((inst, sorted(j_map.values(), key=lambda j: (-BASE._PESO_MOD_ORDEN.get(j[1], 20), j[0])), m1_str))
    if tasks_b2:
        n_w = min(max(int(workers), 1), len(tasks_b2))
        print(f"[ETAPA B2] Corriendo adaptacion por escala para {len(tasks_b2)} indices con workers={n_w}...", flush=True)
        if n_w == 1:
            for ta in tasks_b2:
                for cname, n_tr, dt in BASE._run_instrumento_b4_worker(ta):
                    print(f"  [B2 RUN] {cname}: n={n_tr} ({dt:.1f}s)", flush=True)
        else:
            with concurrent.futures.ProcessPoolExecutor(max_workers=n_w) as ex:
                for logs in ex.map(BASE._run_instrumento_b4_worker, tasks_b2):
                    for cname, n_tr, dt in logs:
                        print(f"  [B2 RUN] {cname}: n={n_tr} ({dt:.1f}s)", flush=True)
    else:
        print("[CACHE] Etapa B2 completa en disco.", flush=True)

    # 3) Evaluar B1 (GC DESC + permutaciones globales 60 variantes GC)
    atr_gc, _, pv_gc, start_gc = BASE._cargar_series_sesion("GC", m1_dir=m1_dir)
    orb_gc = cargar_orb_ventanas("GC", [(510, 525), (570, 585), (180, 195)], m1_dir=m1_dir)
    fechas_gc = IT2._cargar_fechas_a5_inst("GC", m1_dir=m1_dir)
    df_b1, diags_b1, ops_gc = _evaluar_variantes_inst(
        "GC", specs_gc, fechas_gc["DESC"], atr_gc, orb_gc, pv_gc, start_gc, scope_perm="B1_GC",
    )
    df_b1.to_csv(OUT_DIR / "etapa_b1_oro_gc_adaptacion.csv", index=False)

    # 4) Evaluar B2 por activo (DESC + permutaciones)
    b2_dfs: list[pd.DataFrame] = []
    diags_all = dict(diags_b1)
    ops_all = dict(ops_gc)
    start_map = {"GC": start_gc}
    for inst in ACTIVOS_EXT:
        atr_i, _, pv_i, start_i = BASE._cargar_series_sesion(inst, m1_dir=m1_dir)
        orb_i_map = cargar_orb_ventanas(inst, [(570, 585)], m1_dir=m1_dir)
        start_map[inst] = start_i
        fechas_i = IT2._cargar_fechas_a5_inst(inst, m1_dir=m1_dir)
        sub_sp = [s for s in specs_b2 if s["instrumento"] == inst]
        df_i, dg_i, op_i = _evaluar_variantes_inst(
            inst, sub_sp, fechas_i["DESC"], atr_i, orb_i_map, pv_i, start_i, scope_perm=f"B2_{inst}",
        )
        b2_dfs.append(df_i)
        diags_all.update(dg_i)
        ops_all.update(op_i)

    df_b2 = pd.concat(b2_dfs, ignore_index=True)
    df_b2.to_csv(OUT_DIR / "etapa_b2_indices_adaptacion.csv", index=False)
    (OUT_DIR / "diagnostico_grillas_multiactivo.json").write_text(json.dumps(diags_all, indent=2, default=str), encoding="utf-8")

    # 5) Lectura UNICA congelada en REP para candidatas pasa_desc (+ top 2 por familia GC para trazabilidad)
    cand_rows: dict[str, tuple[bool, str]] = {}
    for _, r in pd.concat([df_b1, df_b2], ignore_index=True).iterrows():
        if bool(r["pasa_desc"]):
            cand_rows[str(r["variante"])] = (True, "pasa_desc")
    for g, sub_g in df_b1.groupby("grilla"):
        top2 = sub_g[~sub_g["degenerada_2020"]].sort_values(["t_ses_2020", "calmar"], ascending=False).head(2)
        for _, r in top2.iterrows():
            v = str(r["variante"])
            if v not in cand_rows:
                cand_rows[v] = (False, f"top2_traza_{g}")

    meta_map = {str(r["variante"]): r for _, r in pd.concat([df_b1, df_b2], ignore_index=True).iterrows()}
    rep_rows: list[dict[str, Any]] = []
    for vname, (pasa_d, motivo) in cand_rows.items():
        rm = meta_map[vname]
        inst = str(rm["instrumento"])
        ops_safe = ops_all[vname]
        st_i = start_map[inst]
        for part in ("DESC", "REP"):
            sub_f = ops_safe[ops_safe["a5"] == part]
            sub_20 = sub_f[sub_f["fecha_int"] >= 20200101]
            sub_21 = sub_f[sub_f["fecha_int"] >= 20210101]
            st21 = BASE.resumir_serie_r(sub_21, meses_totales=BASE._meses_activos_a5(max(st_i, 20210101), 20260930, part))
            for per_nom, sub_p, d0 in (("FULL_2008", sub_f, st_i), ("POST_2020", sub_20, max(st_i, 20200101))):
                mtot = BASE._meses_activos_a5(d0, 20260930, part)
                st = BASE.resumir_serie_r(sub_p, meses_totales=mtot)
                dd_m = IT2._metricas_dd_r(sub_p, mtot)
                rep_rows.append({
                    "variante": vname, "grilla": str(rm["grilla"]), "instrumento": inst, "modulo": str(rm["modulo"]),
                    "spread_estimado": inst == "EMD", "pasa_desc": pasa_d, "motivo_rep": motivo,
                    "q_bh_desc": float(rm["q_bh"]), "p_perm_desc": float(rm["p_perm"]), "p_maxT_desc": float(rm["p_maxT"]),
                    "particion_a5": part, "periodo": per_nom, **st, **dd_m,
                    "n_2021": st21["n"], "R_neto_2021": st21["R_neto_mini"], "R_mes_2021": st21["R_por_mes"],
                })
    df_rep = pd.DataFrame(rep_rows)
    df_rep.to_csv(OUT_DIR / "etapa_b_confirmacion_rep.csv", index=False)
    return df_b1, df_b2, df_rep, diags_all, ops_all


def _serie_usd_micros_ma(
    ops_cartera: pd.DataFrame,
    fechas_ses: list[int],
    usd_por_r: float,
    max_micros: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Convierte trades cross-asset a USD diario en micros enteros (`MNQ/MES/MYM/MGC`)."""
    d_usd = {f: 0.0 for f in fechas_ses}
    mic_log: dict[str, list[int]] = {}
    if len(ops_cartera) == 0:
        return np.zeros(len(fechas_ses), dtype=float), {}

    for row in ops_cartera.itertuples(index=False):
        if row.w_eff <= 1e-9:
            continue
        inst = str(row.stream).split("::")[1]
        if inst not in MICRO_MAP:
            continue
        upt = _usd_pt_micro_ma(inst)
        r_1mic = float(row.riesgo_pts) * upt
        tgt_usd = float(usd_por_r) * float(row.w_eff)
        n_mic = int(min(max_micros, max(0, round(tgt_usd / max(r_1mic, 1e-6)))))
        if n_mic == 0 and tgt_usd >= 0.55 * r_1mic:
            n_mic = 1
        mic_log.setdefault(str(row.stream), []).append(n_mic)
        r_mic = float(row.R_neto_micro) if np.isfinite(row.R_neto_micro) else float(row.R_neto_mini)
        fi = int(row.fecha_int)
        if fi in d_usd:
            d_usd[fi] += (r_mic * float(row.riesgo_pts)) * upt * n_mic

    return np.array([d_usd[f] for f in fechas_ses], dtype=float), {k: round(float(np.median(v)), 1) for k, v in mic_log.items() if v}


def _cartera_cross_asset_y_lucid(
    df_b1: pd.DataFrame,
    df_b2: pd.DataFrame,
    ops_ext: Mapping[str, pd.DataFrame],
    m1_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Etapa C: correlacion diaria DESC y evaluacion NQ_CORE_6 vs Indices y Oro GC (DESC->REP + LucidFlex)."""
    # 1) Nucleo NQ_CORE_6 validado en Iter 2 (sin A20 que cayo en REP)
    specs_nq6 = [
        ("R_maeATR50::NQ", "R", {}, 0.50, None, 1.25),
        ("Z_maeATR50::NQ", "Z", {}, 0.50, None, 1.25),
        ("T_stop100::NQ", "T", {"stop_orb_multiplier": 1.0}, None, None, 1.0),
        ("V_nm30_maeATR30::NQ", "V", {"noise_multiplier": 0.30, "vwap_exit_bars": 2, "profit_target_usd_per_contract": 1400.0}, None, 0.30, 1.25),
        ("W_eod_slope_ATR25::NQ", "W", {"exit_on_vwap_cross": False, "allow_reentries": False, "use_vwap_slope_filter": True}, 0.25, None, 1.25),
        ("N_fab_maeATR25::NQ", "N", {}, 0.25, None, 1.25),
    ]
    atr_nq, _, pv_nq, _ = BASE._cargar_series_sesion("NQ", m1_dir=m1_dir)
    orb_raw_nq = cargar_orb_ventanas("NQ", [(570, 585)], m1_dir=m1_dir)[(570, 585)]
    fechas_nq = IT2._cargar_fechas_a5_inst("NQ", m1_dir=m1_dir)
    ses_desc, ses_rep = fechas_nq["DESC"], fechas_nq["REP"]
    m_desc = BASE._meses_activos_a5(20200101, 20260930, "DESC")
    m_rep = BASE._meses_activos_a5(20200101, 20260930, "REP")

    nq_streams: dict[str, pd.DataFrame] = {}
    for sid, mod, params, ka, capk, mult in specs_nq6:
        df_t = BASE._cargar_trades_cacheados(BASE._cache_key("NQ", mod, params if params else None))
        nq_streams[sid] = convertir_ops_activo(df_t, mod, "NQ", atr_nq, orb_raw_nq, pv_nq, stop_atr_k=ka, cap_mae_atr_k=capk, stop_orb_mult=mult)

    d_nq6_desc = pd.DataFrame({k: v[(v["a5"] == "DESC") & (v["fecha_int"] >= 20200101)].groupby("fecha_int")["R_neto_mini"].sum() for k, v in nq_streams.items()}, index=ses_desc).fillna(0.0)
    nq6_tot_desc = d_nq6_desc.sum(axis=1)

    # 2) Seleccion estricta en DESC POST_2020 (sin EMD* ni lectura de REP): q_bh<0.10, t_ses>=1.8, fric<=0.12, corr<=0.50
    def _pick_streams(df_src: pd.DataFrame, insts: tuple[str, ...]) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
        sub = df_src[(df_src["instrumento"].isin(insts)) & (~df_src["degenerada_2020"]) & (df_src["med_fric_R_2020"] <= 0.12)].copy()
        sub = sub[(sub["q_bh"] < 0.10) & (sub["t_ses_2020"] >= 1.80) & (sub["R_neto_2020"] > 0.0)]
        picked: dict[str, pd.DataFrame] = {}
        diag_corr: dict[str, Any] = {}
        seen_mi: set[tuple[str, str]] = set()
        for _, r in sub.sort_values(["calmar", "t_ses_2020"], ascending=False).iterrows():
            key_mi = (str(r["modulo"]), str(r["instrumento"]))
            if key_mi in seen_mi:
                continue
            vname = str(r["variante"])
            op = ops_ext[vname]
            sd = op[(op["a5"] == "DESC") & (op["fecha_int"] >= 20200101)].groupby("fecha_int")["R_neto_mini"].sum().reindex(ses_desc, fill_value=0.0)
            corr = float(np.corrcoef(sd.to_numpy(), nq6_tot_desc.to_numpy())[0, 1]) if np.std(sd) > 0 and np.std(nq6_tot_desc) > 0 else 0.0
            diag_corr[vname] = {"corr_vs_nq6_desc": round(corr, 3), "t_ses_desc": float(r["t_ses_2020"]), "q_bh_desc": float(r["q_bh"]), "calmar_desc": float(r["calmar"])}
            if abs(corr) <= 0.50:
                seen_mi.add(key_mi)
                picked[f"{vname}::{r['instrumento']}"] = op
        return picked, diag_corr

    idx_pick, corr_idx = _pick_streams(df_b2, ("ES", "YM", "RTY"))
    oro_pick, corr_oro = _pick_streams(df_b1, ("GC",))

    # Top-1 GC sensibilidad aunque no pase filtro estricto (solo trazado aparte si oro_pick vacio)
    oro_sens: dict[str, pd.DataFrame] = {}
    gc_top_row = df_b1[(~df_b1["degenerada_2020"]) & (df_b1["R_neto_2020"] > 0.0)].sort_values(["t_ses_2020", "calmar"], ascending=False)
    if not oro_pick and not gc_top_row.empty:
        r0 = gc_top_row.iloc[0]
        vn = str(r0["variante"])
        op = ops_ext[vn]
        sd = op[(op["a5"] == "DESC") & (op["fecha_int"] >= 20200101)].groupby("fecha_int")["R_neto_mini"].sum().reindex(ses_desc, fill_value=0.0)
        corr0 = float(np.corrcoef(sd.to_numpy(), nq6_tot_desc.to_numpy())[0, 1]) if np.std(sd) > 0 and np.std(nq6_tot_desc) > 0 else 0.0
        corr_oro[vn] = {"corr_vs_nq6_desc": round(corr0, 3), "t_ses_desc": float(r0["t_ses_2020"]), "q_bh_desc": float(r0["q_bh"]), "sensibilidad_fuera_filtro": True}
        oro_sens[f"{vn}::GC"] = op

    carteras: dict[str, tuple[dict[str, pd.DataFrame], bool]] = {"NQ_CORE_6": (nq_streams, False)}
    if idx_pick:
        carteras["NQ_PLUS_INDICES"] = ({**nq_streams, **idx_pick}, False)
    if oro_pick:
        carteras["NQ_PLUS_ORO"] = ({**nq_streams, **oro_pick}, False)
    elif oro_sens:
        carteras["SENSIBILIDAD_NQ_ORO"] = ({**nq_streams, **oro_sens}, True)
    if idx_pick and oro_pick:
        carteras["CROSS_ASSET_TOTAL"] = ({**nq_streams, **idx_pick, **oro_pick}, False)

    # Correlacion completa entre streams incluidos
    all_streams = {}
    for s_m, _ in carteras.values():
        all_streams.update(s_m)
    d_mat_desc = pd.DataFrame({
        sid: df[(df["a5"] == "DESC") & (df["fecha_int"] >= 20200101)].groupby("fecha_int")["R_neto_mini"].sum()
        for sid, df in all_streams.items()
    }, index=ses_desc).fillna(0.0)
    corr_matrix = d_mat_desc.corr().round(3).to_dict() if len(d_mat_desc.columns) >= 2 else {}

    rows_c: list[dict[str, Any]] = []
    curvas: dict[str, dict[str, pd.Series]] = {}
    pesos_out: dict[str, Any] = {}
    lucid_out: dict[str, Any] = {}

    for cnom, (smap, is_sens) in carteras.items():
        s_d = {sid: df[(df["a5"] == "DESC") & (df["fecha_int"] >= 20200101)].copy() for sid, df in smap.items()}
        s_r = {sid: df[(df["a5"] == "REP") & (df["fecha_int"] >= 20200101)].copy() for sid, df in smap.items()}
        dur_med = {sid: (float(sub["dur_min"].median()) if len(sub) else 60.0) for sid, sub in s_d.items()}
        ref_risk = {sid: (float(sub["riesgo_pts"].median()) if len(sub) else 50.0) for sid, sub in s_d.items()}
        D_d = pd.DataFrame({sid: sub.groupby("fecha_int")["R_neto_mini"].sum() for sid, sub in s_d.items()}, index=ses_desc).fillna(0.0)
        M_d = pd.DataFrame({sid: sub.groupby("mes")["R_neto_mini"].sum() for sid, sub in s_d.items()}).fillna(0.0)
        p_dict = IT2.calcular_pesos_esquemas(D_d, M_d, dur_med)
        pesos_out[cnom] = {k: {sk: round(sv, 4) for sk, sv in p_dict[k].items()} for k in ("W0_equal_1R", "W3_ERC_cov_cap", "W5_freq_dur_conc")}
        curvas[cnom] = {}

        for esq in ("W0_equal_1R", "W3_ERC_cov_cap", "W5_freq_dur_conc"):
            cap = 3.0 if esq == "W5_freq_dur_conc" else None
            w_map = p_dict[esq]
            for modo_sz in (("R_const", "fijo_micro") if esq != "W0_equal_1R" else ("R_const",)):
                fac_d, fac_r = {}, {}
                for sid in smap:
                    fd, fm = IT2._factor_sizing(s_d[sid], modo_sz, ref_risk[sid])
                    fr, _ = IT2._factor_sizing(s_r[sid], modo_sz, ref_risk[sid], mean_factor_ref=fm)
                    fac_d[sid], fac_r[sid] = fd, fr
                tr_d, mx_d = IT2.aplicar_tope_concurrencia_causal(s_d, w_map, fac_d, cap_r=cap)
                tr_r, mx_r = IT2.aplicar_tope_concurrencia_causal(s_r, w_map, fac_r, cap_r=cap)
                sd_ser = tr_d.groupby("fecha_int")["R_eff"].sum().reindex(ses_desc, fill_value=0.0)
                sr_ser = tr_r.groupby("fecha_int")["R_eff"].sum().reindex(ses_rep, fill_value=0.0)
                if modo_sz == "R_const":
                    curvas[cnom][f"{esq}__DESC"] = sd_ser
                    curvas[cnom][f"{esq}__REP"] = sr_ser
                for pn, sp_ser, mtot, mxo in (("DESC", sd_ser, m_desc, mx_d), ("REP", sr_ser, m_rep, mx_r)):
                    ev = IT2.evaluar_serie_cartera(sp_ser, mtot, mc_reps=5000, seed=99)
                    rows_c.append({
                        "cartera": cnom, "sensibilidad_fuera_filtro": is_sens, "esquema": esq, "sizing": modo_sz,
                        "particion_a5": pn, "n_streams": len(smap), "max_open_R": mxo, **ev,
                    })

        # LucidFlex sobre W5 (o W3) con micros medidos (MNQ/MES/MYM/MGC)
        s_d_mic = {sid: df for sid, df in s_d.items() if sid.split("::")[1] in MICRO_MAP}
        s_r_mic = {sid: df for sid, df in s_r.items() if sid.split("::")[1] in MICRO_MAP}
        w_pref = {sid: p_dict["W5_freq_dur_conc"][sid] for sid in s_d_mic}
        tr_dm, _ = IT2.aplicar_tope_concurrencia_causal(s_d_mic, w_pref, None, cap_r=3.0)
        tr_rm, _ = IT2.aplicar_tope_concurrencia_causal(s_r_mic, w_pref, None, cap_r=3.0)
        for tam, base_r in (("25K", 150.0), ("50K", 200.0), ("150K", 450.0)):
            cfg_t = LG.TAMANOS[tam]
            pr = LG.precio(tam, True, 0.50)
            yd, mic_d = _serie_usd_micros_ma(tr_dm, ses_desc, base_r, cfg_t["micros"])
            yr, _ = _serie_usd_micros_ma(tr_rm, ses_rep, base_r, cfg_t["micros"])
            for pnom, yraw in (("DESC", yd), ("REP", yr)):
                for mnom, mult in (("real_100", 1.0), ("contraida_60", 0.60)):
                    ysc = yraw - np.mean(yraw) + mult * np.mean(yraw)
                    acc = LG.por_cuenta(ysc, cfg_t, 0.50, N=4000)
                    car = LG.cartera(ysc, cfg_t, 0.50, pr, max_eval=5, por_dia=1, N=1500, H=504)
                    lucid_out[f"{cnom}|{tam}|R{int(base_r)}|{pnom}|{mnom}"] = {
                        "usd_dia_media": round(float(np.mean(ysc)), 2),
                        "worst_day_usd": round(float(np.min(ysc)), 1),
                        "micros_med_stream": mic_d,
                        "ev_examen_usd": round(float(acc["cobrado_medio"] - pr), 1),
                        "pasa_pct": round(float(acc["pasa"] * 100.0), 1),
                        "cartera_neto_medio_usd": round(float(car["neto_medio"]), 1),
                        "cartera_usd_mes": round(float(car["usd_por_mes_hasta_fin"]), 1),
                        "cartera_p_pos_pct": round(float(car["p_neto_positivo"] * 100.0), 1),
                        "cartera_caja_min_p10": car["caja_minima_p50_p10"][1],
                    }

    df_c = pd.DataFrame(rows_c)
    df_c.to_csv(OUT_DIR / "etapa_c_cartera_cross_asset.csv", index=False)
    pack = {
        "streams_indices_admitidos": sorted(idx_pick),
        "streams_oro_admitidos": sorted(oro_pick),
        "streams_oro_sensibilidad": sorted(oro_sens),
        "diag_seleccion_indices": corr_idx,
        "diag_seleccion_oro": corr_oro,
        "matriz_correlacion_desc": corr_matrix,
        "pesos": pesos_out,
        "lucid": lucid_out,
    }
    (OUT_DIR / "etapa_c_correlacion_y_lucid.json").write_text(json.dumps(pack, indent=2, default=str), encoding="utf-8")
    return df_c, {"pack": pack, "curvas": curvas}


def graficar_iter3(
    df_a: pd.DataFrame,
    df_b1: pd.DataFrame,
    df_b2: pd.DataFrame,
    df_rep: pd.DataFrame,
    extra_c: Mapping[str, Any],
) -> dict[str, Path]:
    """Genera los 3 graficos oscuros legibles en OUT_DIR y los copia en ARTIFACTS_DIR."""
    if plt is None:
        raise RuntimeError("matplotlib requerido")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rutas: dict[str, Path] = {}

    # 1) Matriz base 15 x 6 (DESC y REP POST_2020)
    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(16.8, 8.2), facecolor="#0d1316")
    sub_a = df_a[(df_a["periodo"] == "POST_2020") & (df_a["variante"] == "fabrica")].copy()
    act_lbls = [a if a != "EMD" else "EMD*" for a in ACTIVOS_TODOS]
    for ax_h, part in ((ax1, "DESC"), (ax2, "REP")):
        ax_h.set_facecolor("#11191c")
        s_p = sub_a[sub_a["particion_a5"] == part]
        piv_r = s_p.pivot(index="modulo", columns="instrumento", values="R_neto_mini").reindex(index=list(MODULOS_ORDEN), columns=list(ACTIVOS_TODOS))
        piv_n = s_p.pivot(index="modulo", columns="instrumento", values="n").reindex(index=list(MODULOS_ORDEN), columns=list(ACTIVOS_TODOS))
        im = ax_h.imshow(piv_r.fillna(0.0).to_numpy(dtype=float), cmap="RdYlGn", vmin=-0.20, vmax=0.35, aspect="auto")
        ax_h.set_xticks(np.arange(len(ACTIVOS_TODOS)))
        ax_h.set_xticklabels(act_lbls, color="#d0dce2", fontsize=9)
        ax_h.set_yticks(np.arange(len(MODULOS_ORDEN)))
        ax_h.set_yticklabels(MODULOS_ORDEN, color="#d0dce2", fontsize=9)
        for ri in range(len(MODULOS_ORDEN)):
            for ci in range(len(ACTIVOS_TODOS)):
                v, nv = piv_r.iloc[ri, ci], piv_n.iloc[ri, ci]
                txt = f"{v:+.2f}\nn={int(nv)}" if np.isfinite(v) and np.isfinite(nv) and int(nv) > 0 else "0"
                ct = "#f4f7f8" if (not np.isfinite(v) or v < -0.07 or v > 0.22) else "#0c1214"
                ax_h.text(ci, ri, txt, ha="center", va="center", color=ct, fontsize=7.0, fontweight="bold")
        ax_h.set_title(f"POST_2020 {part}: R_neto fábrica (il_fabrica)", color="#e6eef2", fontsize=10.5)
        for sp in ax_h.spines.values():
            sp.set_color("#29363c")
    fig1.suptitle("Etapa A — Matriz 15 Modulos x 6 Futuros en R (*EMD spread estimado K33)", color="#e6eef2", fontsize=12)
    fig1.subplots_adjust(left=0.045, right=0.905, top=0.90, bottom=0.06, wspace=0.14)
    cax = fig1.add_axes([0.922, 0.12, 0.015, 0.74])
    cb = fig1.colorbar(im, cax=cax)
    cb.ax.tick_params(colors="#d0dce2", labelsize=8.5)
    p1 = OUT_DIR / "multiactivo_matriz_base_15x6.png"
    fig1.savefig(p1, dpi=150, facecolor=fig1.get_facecolor())
    plt.close(fig1)
    rutas["matriz"] = p1

    # 2) Oro (GC) adaptacion y permutaciones DESC vs REP
    fig2, (bx1, bx2) = plt.subplots(1, 2, figsize=(16.5, 7.6), facecolor="#0d1316")
    for ax in (bx1, bx2):
        ax.set_facecolor("#11191c")
        ax.tick_params(colors="#b4c2c8", labelsize=8.5)
        for sp in ax.spines.values():
            sp.set_color("#29363c")
    top_gc = df_b1[~df_b1["degenerada_2020"]].sort_values("t_ses_2020", ascending=True).tail(18)
    yg = np.arange(len(top_gc))
    c_gc = ["#2ca693" if ok and q < 0.10 else "#587cc9" if r > 0 else "#c47068" for ok, q, r in zip(top_gc["pasa_desc"], top_gc["q_bh"], top_gc["R_neto_2020"])]
    bx1.barh(yg, top_gc["t_ses_2020"], color=c_gc, height=0.64)
    for yi, (_, rr) in enumerate(top_gc.iterrows()):
        star = "*" if rr["q_bh"] < 0.10 else ""
        bx1.text(max(float(rr["t_ses_2020"]), 0.0) + 0.06, yi, f"R={rr['R_neto_2020']:+.3f} q={rr['q_bh']:.3f}{star}", va="center", color="#d2dce1", fontsize=7.0)
    bx1.axvline(1.96, color="#f0c954", linewidth=0.85, linestyle=":")
    bx1.axvline(0.0, color="#9ab0ba", linewidth=0.85, linestyle="--")
    bx1.set_xlim(min(float(top_gc["t_ses_2020"].min()), -0.5) - 0.3, float(top_gc["t_ses_2020"].max()) + 2.0)
    bx1.set_yticks(yg)
    bx1.set_yticklabels(top_gc["variante"], fontsize=8)
    bx1.set_xlabel("t-stat por sesion (GC DESC POST_2020)", color="#c8d4da")
    bx1.set_title("Etapa B1 Oro (GC): Top 18 variantes adaptadas y BH-FDR", color="#e6eef2", fontsize=10.5)

    gc_rep = df_rep[(df_rep["instrumento"] == "GC") & (df_rep["periodo"] == "POST_2020")]
    if not gc_rep.empty:
        pv_gc = gc_rep.pivot(index="variante", columns="particion_a5", values="R_neto_mini").dropna()
        if not pv_gc.empty:
            cols_sc = ["#2ca693" if (d > 0 and r > 0) else "#f0c954" if d > 0 else "#c47068" for d, r in zip(pv_gc["DESC"], pv_gc["REP"])]
            bx2.scatter(pv_gc["DESC"], pv_gc["REP"], c=cols_sc, s=65, edgecolors="#0d1316")
            for vn, rr in pv_gc.iterrows():
                bx2.text(float(rr["DESC"]) + 0.005, float(rr["REP"]) + 0.005, str(vn), color="#d2dce1", fontsize=7.0)
            bx2.axhline(0.0, color="#9ab0ba", linewidth=0.8, linestyle="--")
            bx2.axvline(0.0, color="#9ab0ba", linewidth=0.8, linestyle="--")
            x_lo, x_hi = bx2.get_xlim()
            bx2.set_xlim(x_lo, x_hi + 0.025)
    bx2.set_xlabel("R_neto DESC (POST_2020)", color="#c8d4da")
    bx2.set_ylabel("R_neto REP congelado (POST_2020)", color="#c8d4da")
    bx2.set_title("Oro (GC): Consistencia DESC vs REP congelado", color="#e6eef2", fontsize=10.5)
    fig2.tight_layout()
    p2 = OUT_DIR / "oro_gc_adaptacion_y_permutaciones.png"
    fig2.savefig(p2, dpi=150, facecolor=fig2.get_facecolor())
    plt.close(fig2)
    rutas["oro"] = p2

    # 3) Antes vs Despues por activo + Cartera Cross-Asset DESC/REP
    fig3, (cx1, cx2, cx3) = plt.subplots(1, 3, figsize=(18.0, 6.2), facecolor="#0d1316")
    for ax in (cx1, cx2, cx3):
        ax.set_facecolor("#11191c")
        ax.tick_params(colors="#b4c2c8", labelsize=8)
        for sp in ax.spines.values():
            sp.set_color("#29363c")

    # Panel 1: Mejor R_neto DESC fabrica vs adaptado en ES, YM, RTY, GC, EMD*
    inst_comp = ("ES", "YM", "RTY", "GC", "EMD")
    sub_b = df_a[(df_a["periodo"] == "POST_2020") & (df_a["particion_a5"] == "DESC") & (df_a["variante"] == "fabrica") & (df_a["n"] >= 30)]
    best_fab = [float(sub_b[sub_b["instrumento"] == i]["R_neto_mini"].max()) if not sub_b[sub_b["instrumento"] == i].empty else 0.0 for i in inst_comp]
    sub_ad = pd.concat([df_b1, df_b2], ignore_index=True)
    best_adp = [float(sub_ad[(sub_ad["instrumento"] == i) & (~sub_ad["degenerada_2020"])]["R_neto_2020"].max()) if not sub_ad[(sub_ad["instrumento"] == i) & (~sub_ad["degenerada_2020"])].empty else 0.0 for i in inst_comp]
    xi = np.arange(len(inst_comp))
    cx1.bar(xi - 0.18, best_fab, width=0.34, color="#587cc9", label="Mejor Fabrica (DESC)")
    cx1.bar(xi + 0.18, best_adp, width=0.34, color="#2ca693", label="Mejor Adaptado (DESC)")
    cx1.axhline(0.0, color="#9ab0ba", linewidth=0.8, linestyle="--")
    cx1.set_xticks(xi)
    cx1.set_xticklabels([i if i != "EMD" else "EMD*" for i in inst_comp])
    cx1.set_ylabel("Mejor R_neto por op. (POST_2020 DESC)", color="#c8d4da")
    cx1.set_title("Antes vs Despues de adaptacion por activo", color="#e6eef2", fontsize=10)
    cx1.legend(loc="upper right", fontsize=7.5, frameon=True, facecolor="#11191c", edgecolor="#29363c", labelcolor="#dbe4e8")

    curv = extra_c.get("curvas", {})
    pal_c = {"NQ_CORE_6": "#3baeb8", "NQ_PLUS_INDICES": "#f0c954", "NQ_PLUS_ORO": "#2ca693", "SENSIBILIDAD_NQ_ORO": "#d9825b", "CROSS_ASSET_TOTAL": "#8ce08c"}
    for ax_p, part in ((cx2, "DESC"), (cx3, "REP")):
        for cn, cmap in curv.items():
            ser = cmap.get(f"W5_freq_dur_conc__{part}")
            if ser is not None and len(ser):
                ax_p.plot(np.arange(len(ser)), np.cumsum(ser.to_numpy(dtype=float)), label=cn, color=pal_c.get(cn, "#cccccc"), linewidth=1.6)
        ax_p.set_title(f"Carteras W5 Cross-Asset ({part} A5)", color="#e6eef2", fontsize=10)
        ax_p.set_xlabel("Sesiones", color="#c8d4da")
        ax_p.set_ylabel("R acumulado", color="#c8d4da")
        ax_p.legend(loc="upper left", fontsize=7.2, frameon=True, facecolor="#11191c", edgecolor="#29363c", labelcolor="#dbe4e8")

    fig3.tight_layout()
    p3 = OUT_DIR / "multiactivo_adaptado_y_cartera.png"
    fig3.savefig(p3, dpi=150, facecolor=fig3.get_facecolor())
    plt.close(fig3)
    rutas["cartera"] = p3

    if ARTIFACTS_DIR.exists():
        for rp in rutas.values():
            shutil.copy2(rp, ARTIFACTS_DIR / rp.name)
    return rutas


def ejecutar_iter3(etapa: str = "todo", m1_dir: Path | None = None, workers: int = 2) -> dict[str, Any]:
    asegurar_compuerta_iter3()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df_a: pd.DataFrame | None = None
    clasif: dict[str, Any] = {}
    if etapa in ("etapa_a", "todo"):
        df_a = _correr_etapa_a(workers=workers, m1_dir=m1_dir)
        clasif = _clasificar_etapa_a(df_a)
        print("\n=== ETAPA A: CLASIFICACION PORTABILIDAD BASE (15 x 6 POST_2020) ===")
        for mod, info in clasif.items():
            print(f"  {mod:3s}: {info['categoria']:18s} activos={info['activos_confirmados']}")

    df_b1: pd.DataFrame | None = None
    df_b2: pd.DataFrame | None = None
    df_rep: pd.DataFrame | None = None
    diags_all: dict[str, Any] = {}
    ops_all: dict[str, pd.DataFrame] = {}
    if etapa in ("etapa_b", "etapa_c", "todo"):
        df_b1, df_b2, df_rep, diags_all, ops_all = _correr_etapa_b(workers=workers, m1_dir=m1_dir)
        print("\n=== ETAPA B1 ORO (GC) TOP 15 DESC POST_2020 ===")
        cols_b = ["grilla", "modulo", "variante", "n_2020", "R_neto_2020", "R_micro_2020", "R_mes_2020", "t_ses_2020", "dd_R", "p_perm", "q_bh", "p_maxT", "pasa_desc"]
        print(df_b1.sort_values("t_ses_2020", ascending=False)[cols_b].head(15).to_string(index=False))
        print("\n=== ETAPA B2 INDICES TOP 15 DESC POST_2020 ===")
        print(df_b2.sort_values("t_ses_2020", ascending=False)[cols_b].head(15).to_string(index=False))

    df_c: pd.DataFrame | None = None
    extra_c: dict[str, Any] = {}
    if etapa in ("etapa_c", "todo"):
        if df_a is None:
            df_a = pd.read_csv(OUT_DIR / "etapa_a_matriz_base_15x6.csv")
            clasif = _clasificar_etapa_a(df_a)
        assert df_b1 is not None and df_b2 is not None and df_rep is not None
        df_c, extra_c = _cartera_cross_asset_y_lucid(df_b1, df_b2, ops_all, m1_dir=m1_dir)
        print("\n=== ETAPA C CARTERA CROSS-ASSET (DESC vs REP CONGELADO) ===")
        print(df_c[["cartera", "sensibilidad_fuera_filtro", "esquema", "sizing", "particion_a5", "n_streams", "R_mes", "t_ses", "dd_R", "mc_dd_p95", "calmar"]].to_string(index=False))
        resumen = {"clasificacion_base": clasif, "diagnosticos": diags_all, "cartera": extra_c["pack"]}
        (OUT_DIR / "resumen_multiactivo_oro.json").write_text(json.dumps(resumen, indent=2, default=str), encoding="utf-8")
        graficar_iter3(df_a, df_b1, df_b2, df_rep, extra_c)

    return {"df_a": df_a, "df_b1": df_b1, "df_b2": df_b2, "df_rep": df_rep, "df_c": df_c}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Iteracion 3 FUNDEDSYNC: multi-activo y adaptacion Oro GC.")
    ap.add_argument("etapa", nargs="?", default="todo", choices=("etapa_a", "etapa_b", "etapa_c", "todo"))
    ap.add_argument("--workers", type=int, default=2, help="Workers paralelos (default 2)")
    args = ap.parse_args(argv)
    ejecutar_iter3(etapa=args.etapa, workers=args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

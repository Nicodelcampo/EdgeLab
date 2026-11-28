#!/usr/bin/env python3
"""Barrido ordenado de paridad (Etapas 0 -> 1 -> 2) y graficado OOS de `fundedsyncstack`.

Objetivo: medir y minimizar la divergencia morfologica contra los tramos claros v2 del vendedor
en in-sample (2022-2024) y validar fuera de muestra (2025-2026), manteniendo intocable `il_fabrica`.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import pickle
import shutil
import time
from pathlib import Path
from typing import Any, Mapping

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None  # type: ignore[assignment]
import numpy as np
import pandas as pd

from edgelab.research.fundedsyncstack import CONFIG_CLASSES, build_multi_series, correr_modulo, load_m1_data
from edgelab.research.fundedsyncstack.motor_cartera import PortfolioConfig, SizingProfile, simular_cartera
from edgelab.research.fundedsyncstack.paridad_vendedor import (
    DEFAULT_CSV_GEMINI,
    DEFAULT_CSV_V2,
    PARIDAD_DIR,
    VENDOR_PARITY_OVERRIDES,
    cargar_curva_vendedor,
    evaluar_paridad_variantes,
    obtener_config_modulo,
    resolver_identidad_teal,
    serie_diaria_desde_trades,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_M1_PARQUET = Path(r"C:\Users\nicoc\OneDrive\Documentos\NinjaTrader 8\exports\edgelab_nt8_m1_parquet\NQ_M1_nonadj_utc.parquet")
DEFAULT_NEWS_CSV = Path(r"C:\Users\nicoc\Downloads\FUNDEDSYNCSTACK-1.0.0.5\templates\FundedSync\restricted-news-days.csv")
DEFAULT_NONADJ_PKL = Path(r"C:\Users\nicoc\.gemini\antigravity\brain\417d395c-1bd7-4157-b782-277352881af1\scratch\trades_nt8_2020_2026.pkl")
DEFAULT_BACKADJ_PKL = Path(r"C:\Users\nicoc\.gemini\antigravity\brain\417d395c-1bd7-4157-b782-277352881af1\scratch\trades_nt8_adj_2020_2026.pkl")
DEFAULT_BEST_CACHE = Path(r"C:\Users\nicoc\.gemini\antigravity\brain\417d395c-1bd7-4157-b782-277352881af1\scratch\sweep_best_series_20261121.pkl")
ARTIFACTS_DIR = Path(r"C:\Users\nicoc\.gemini\antigravity\brain\417d395c-1bd7-4157-b782-277352881af1")

MODS_14: tuple[str, ...] = ("A1", "E", "S", "T", "V", "W", "Z", "A20", "C", "F", "O", "P", "Q", "R")

ESTILO_VENDEDOR: dict[str, tuple[str, str, str]] = {
    "A1":  ("A · A1",  "#a8cc5c", "-"),
    "E":   ("A · E",   "#549e5d", "-"),
    "S":   ("A · S",   "#2ca693", "-"),
    "T":   ("A · T",   "#3baeb8", "-"),
    "V":   ("A · V",   "#d9be5b", "-"),
    "W":   ("A · W",   "#cc8b54", "-"),
    "Z":   ("A · Z",   "#7c8c5e", "-"),
    "A20": ("B · A20", "#587cc9", "--"),
    "C":   ("B · C",   "#8b70c7", "--"),
    "F":   ("B · F",   "#b56ca0", "--"),
    "O":   ("B · O",   "#b57cd4", "--"),
    "P":   ("B · P",   "#4aaec4", "--"),
    "Q":   ("B · Q",   "#c47068", "--"),
    "R":   ("B · R",   "#688fb8", "--"),
}


def cargar_caches_baseline(
    nonadj_pkl: Path = DEFAULT_NONADJ_PKL,
    backadj_pkl: Path = DEFAULT_BACKADJ_PKL,
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    """Carga los pickles de trades baseline `nonadj` y `backadj` pre-calculados (<2026-10-01)."""
    with nonadj_pkl.open("rb") as f:
        nonadj = pickle.load(f)
    with backadj_pkl.open("rb") as f:
        backadj = pickle.load(f)
    return nonadj, backadj


def construir_variantes_desde_trades(
    df_trades: pd.DataFrame,
    prefijo: str,
    modos: tuple[str, ...] = ("bruto_1cto", "nt8_1cto", "edge_1cto", "usd_dll"),
) -> dict[str, pd.DataFrame]:
    """Genera el diccionario `nombre -> serie diaria` para multiples modos de friccion/escala."""
    return {
        f"{prefijo}_{modo}": serie_diaria_desde_trades(df_trades, modo=modo, desde="2021-09-15", hasta="2026-09-30")
        for modo in modos
    }


def _cartera_lucid_news_por_modulo(
    trades_dict: Mapping[str, pd.DataFrame],
    news_csv: Path = DEFAULT_NEWS_CSV,
) -> dict[str, pd.DataFrame]:
    """Aplica sizing Lucid50K + calendario de noticias restringidas sobre trades cacheados."""
    sub = {k: v for k, v in trades_dict.items() if k in MODS_14 and isinstance(v, pd.DataFrame)}
    cfg = PortfolioConfig(
        SizingProfile=SizingProfile.Lucid50K,
        FundedSyncStackBlockRestrictedNewsDays=news_csv.exists(),
        FundedSyncStackRestrictedNewsCsvPath=str(news_csv),
        FlattenBeforeDailyFuturesClose=False,
    )
    res = simular_cartera(ms=None, runners_dict=sub, config=cfg)
    tdf = res["trades_df"]
    out: dict[str, pd.DataFrame] = {}
    for mod in sub:
        out[mod] = tdf[tdf["module"] == mod].copy()
    return out


def ejecutar_etapa0_baseline(
    nonadj: Mapping[str, pd.DataFrame],
    backadj: Mapping[str, pd.DataFrame],
    out_dir: Path = PARIDAD_DIR,
) -> dict[str, Any]:
    """Etapa 0: baseline 14 estrategias (nonadj vs backadj x friccion x Lucid50K+news) y TEAL 2x2."""
    out_dir.mkdir(parents=True, exist_ok=True)
    lucid_nonadj = _cartera_lucid_news_por_modulo(nonadj)
    lucid_backadj = _cartera_lucid_news_por_modulo(backadj)

    teal_res = resolver_identidad_teal(
        serie_diaria_desde_trades(nonadj["S"], modo="bruto_1cto", desde="2021-09-15"),
        serie_diaria_desde_trades(nonadj["T"], modo="bruto_1cto", desde="2021-09-15"),
        csv_vendedor=DEFAULT_CSV_V2,
    )
    teal_map = teal_res["asignacion"]

    all_rows: list[dict[str, Any]] = []
    best_per_mod: list[dict[str, Any]] = []
    for mod in MODS_14:
        vars_m: dict[str, pd.DataFrame] = {}
        for sname, src, lsrc in (("nonadj", nonadj, lucid_nonadj), ("backadj", backadj, lucid_backadj)):
            if mod not in src:
                continue
            vars_m.update(
                construir_variantes_desde_trades(
                    src[mod],
                    sname,
                    ("bruto_1cto", "nt8_1cto", "edge_1cto", "usd_dll", "usd_dll_nt8", "usd_dll_edge"),
                )
            )
            if mod in lsrc and not lsrc[mod].empty:
                vars_m[f"{sname}_lucid50k_news"] = serie_diaria_desde_trades(
                    lsrc[mod], modo="usd_dll", desde="2021-09-15", hasta="2026-09-30"
                )
        ev = evaluar_paridad_variantes(mod, vars_m, csv_vendedor=DEFAULT_CSV_V2, teal_map=teal_map)
        if not ev.empty:
            ev.insert(0, "modulo", mod)
            all_rows.extend(ev.to_dict(orient="records"))
            best_row = ev.iloc[0].to_dict()
            # Cruzamiento informativo contra CSV Gemini (descartando picos)
            try:
                ev_gem = evaluar_paridad_variantes(mod, {best_row["config"]: vars_m[best_row["config"]]}, csv_vendedor=DEFAULT_CSV_GEMINI)
                if not ev_gem.empty:
                    best_row["gemini_r_total"] = ev_gem.iloc[0]["r_total"]
                    best_row["gemini_score_pre"] = ev_gem.iloc[0]["score_pre"]
            except ValueError:
                best_row["gemini_r_total"] = np.nan
                best_row["gemini_score_pre"] = np.nan
            best_per_mod.append(best_row)

    df_all = pd.DataFrame(all_rows)
    df_all.to_csv(out_dir / "sweep_etapa0_baseline.csv", index=False)
    df_best = pd.DataFrame(best_per_mod)
    return {"teal": teal_res, "best_baseline": df_best, "all_baseline": df_all}


def _cargar_ms_dev(parquet_path: Path = DEFAULT_M1_PARQUET) -> Any:
    raw = pd.read_parquet(parquet_path).loc["2021-01-01":"2026-09-30 21:59:59"].reset_index()
    df_m1 = load_m1_data(raw, start="2021-01-01", end="2026-10-01", tz_input="UTC", allow_sellado=False)
    return build_multi_series(df_m1, tz_input="UTC", allow_sellado=False)


def _evaluar_candidatos_modulo(
    ms: Any,
    modulo: str,
    candidatos: list[tuple[str, dict[str, Any]]],
    teal_map: Mapping[str, str],
    etapa: str,
    modos: tuple[str, ...] = ("bruto_1cto", "edge_1cto", "usd_dll"),
) -> tuple[list[dict[str, Any]], dict[str, tuple[pd.DataFrame, dict[str, Any]]]]:
    cls = CONFIG_CLASSES[modulo]
    base_cfg = cls()
    rows: list[dict[str, Any]] = []
    cache_series: dict[str, tuple[pd.DataFrame, dict[str, Any]]] = {}

    for nombre, params in candidatos:
        cfg = dataclasses.replace(base_cfg, **params) if params else base_cfg
        t0 = time.perf_counter()
        df_t = correr_modulo(modulo, ms, cfg=cfg)
        dt_s = time.perf_counter() - t0
        vars_m = construir_variantes_desde_trades(df_t, nombre, modos)
        ev = evaluar_paridad_variantes(modulo, vars_m, csv_vendedor=DEFAULT_CSV_V2, teal_map=teal_map)
        for rec in ev.to_dict(orient="records"):
            cfg_key = rec["config"]
            modo = cfg_key[len(nombre) + 1 :]
            rec["etapa"] = etapa
            rec["modulo"] = modulo
            rec["variante"] = nombre
            rec["modo_serie"] = modo
            rec["n_trades"] = int(len(df_t))
            rec["tiempo_s"] = round(dt_s, 2)
            rec["parametros_json"] = json.dumps(params, sort_keys=True)
            rows.append(rec)
            cache_series[cfg_key] = (vars_m[cfg_key], {"modulo": modulo, "variante": nombre, "modo_serie": modo, "parametros": params, "metrics": rec})
    return rows, cache_series


def construir_grilla_etapa1() -> dict[str, list[tuple[str, dict[str, Any]]]]:
    """Define variantes estructurales de ejecucion/sesion/friccion/delay (Etapa 1)."""
    return {
        "F": [
            ("F_il_default", {}),
            ("F_tz_et", {"timezone": "et"}),
            ("F_no_delta", {"disable_delta_filter": True}),
            ("F_no_delta_et", {"disable_delta_filter": True, "timezone": "et"}),
            ("F_cum_delta", {"use_cum_delta": True}),
            ("F_delta0", {"delta_threshold": 0}),
            ("F_delta500", {"delta_threshold": 500}),
        ],
        "S": [
            ("S_il_default", {}),
            ("S_tz_et", {"timezone": "et"}),
            ("S_tz_et_notime", {"timezone": "et", "use_time_filter": False}),
            ("S_notime", {"use_time_filter": False}),
            ("S_no_eod", {"use_eod_close": False}),
            ("S_no_flatten", {"flatten_before_daily_futures_close": False}),
        ],
        "C": [
            ("C_il_default", {}),
            ("C_no_flatten", {"enforce_daily_futures_close": False}),
            ("C_long_short", {"enable_short_entries": True}),
            ("C_start90", {"entry_start_offset_minutes": 90}),
            ("C_start120", {"entry_start_offset_minutes": 120}),
            ("C_start180", {"entry_start_offset_minutes": 180}),
            ("C_exit420", {"exit_offset_minutes": 420}),
        ],
        "W": [
            ("W_il_default", {}),
            ("W_no_vwap_exit", {"exit_on_vwap_cross": False}),
            ("W_no_reentry", {"allow_reentries": False}),
            ("W_no_last_entry", {"use_last_entry_time_filter": False}),
            ("W_last1300", {"last_entry_time_central": 130000}),
            ("W_last1500", {"last_entry_time_central": 150000}),
            ("W_start930", {"vwap_start_time_central": 93000}),
        ],
        "E": [
            ("E_il_default", {}),
            ("E_nodelay", {"historical_minute14_delay": False, "delay_minutes": 0}),
            ("E_delay5", {"delay_minutes": 5}),
            ("E_no_flatten", {"flatten_before_daily_futures_close": False}),
            ("E_nodelay_noflat", {"historical_minute14_delay": False, "delay_minutes": 0, "flatten_before_daily_futures_close": False}),
        ],
        "O": [
            ("O_il_default", {}),
            ("O_no_postmaint", {"use_post_maintenance_entry": False}),
            ("O_no_flatten", {"enforce_daily_futures_close": False}),
            ("O_allow_fri", {"allow_friday_entries": True}),
            ("O_no_slope", {"use_rising_ma_slope_filter": False}),
            ("O_no_range", {"use_rth_range_filter": False}),
        ],
        "R": [
            ("R_il_default", {}),
            ("R_no_rollgap", {"roll_gap_ticks": 0.0}),
            ("R_no_blocked", {"blocked_sessions": ()}),
        ],
    }


def _combinar_etapa2_para_modulo(mod: str, base_p: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    def m(extra: dict[str, Any]) -> dict[str, Any]:
        return {**base_p, **extra}

    if mod == "F":
        return [
            ("F_s2_tprr075", m({"tp_rr": 0.75})),
            ("F_s2_tprr125", m({"tp_rr": 1.25})),
            ("F_s2_tprr150", m({"tp_rr": 1.5})),
            ("F_s2_tprr200", m({"tp_rr": 2.0})),
            ("F_s2_risk75", m({"max_initial_risk_points": 75.0})),
            ("F_s2_risk100", m({"max_initial_risk_points": 100.0})),
            ("F_s2_risk175", m({"max_initial_risk_points": 175.0})),
            ("F_s2_dur15", m({"dur_min": 15})),
            ("F_s2_dur45", m({"dur_min": 45})),
            ("F_s2_dur60", m({"dur_min": 60})),
            ("F_s2_cd1", m({"loss_cooldown_bars": 1})),
            ("F_s2_cd3", m({"loss_cooldown_bars": 3})),
            ("F_s2_tprr15_r100", m({"tp_rr": 1.5, "max_initial_risk_points": 100.0})),
            ("F_s2_end1500", m({"end_h": 15, "end_m": 0})),
        ]
    if mod == "S":
        return [
            ("S_s2_st25", m({"st_mult": 2.5})),
            ("S_s2_st30", m({"st_mult": 3.0})),
            ("S_s2_st36", m({"st_mult": 3.6})),
            ("S_s2_st40", m({"st_mult": 4.0})),
            ("S_s2_noadx", m({"use_adx_filter": False})),
            ("S_s2_adx25", m({"adx_threshold": 25.0})),
            ("S_s2_nobias", m({"use_vwap_ema_bias": False})),
            ("S_s2_noregime", m({"use_regime_filter": False})),
            ("S_s2_hardstop", m({"use_hard_stop": True})),
            ("S_s2_st_align", m({"require_supertrend_entry_alignment": True})),
            ("S_s2_slope0", m({"min_ema_slope_atr": 0.0})),
            ("S_s2_cd3", m({"loss_cooldown_bars": 3})),
        ]
    if mod == "W":
        return [
            ("W_s2_nocd", m({"use_cooldown_filter": False})),
            ("W_s2_cd10", m({"cooldown_bars": 10})),
            ("W_s2_cd15", m({"cooldown_bars": 15})),
            ("W_s2_cd30", m({"cooldown_bars": 30})),
            ("W_s2_conf2", m({"use_confirmation_filter": True, "confirmation_bars": 2})),
            ("W_s2_conf3", m({"use_confirmation_filter": True, "confirmation_bars": 3})),
            ("W_s2_dist4", m({"use_vwap_distance_filter": True, "minimum_vwap_distance_ticks": 4.0})),
            ("W_s2_dist8", m({"use_vwap_distance_filter": True, "minimum_vwap_distance_ticks": 8.0})),
            ("W_s2_dist12", m({"use_vwap_distance_filter": True, "minimum_vwap_distance_ticks": 12.0})),
            ("W_s2_slope05", m({"use_vwap_slope_filter": True, "minimum_vwap_slope_ticks": 0.5})),
            ("W_s2_rth", m({"use_prior_rth_range_filter": True})),
        ]
    if mod == "E":
        return [
            ("E_s2_sl20_tp30", m({"stop_points": 20.0, "target_points": 30.0})),
            ("E_s2_sl25_tp40", m({"stop_points": 25.0, "target_points": 40.0})),
            ("E_s2_sl30_tp60", m({"stop_points": 30.0, "target_points": 60.0})),
            ("E_s2_sl40_tp60", m({"stop_points": 40.0, "target_points": 60.0})),
            ("E_s2_cvdz0", m({"cvd_z_thresh": 0.0})),
            ("E_s2_cvdz25", m({"cvd_z_thresh": 0.25})),
            ("E_s2_cvdz50", m({"cvd_z_thresh": 0.50})),
            ("E_s2_cvdc1", m({"cvd_min_count": 1})),
            ("E_s2_cvdc5", m({"cvd_min_count": 5})),
            ("E_s2_absv05", m({"absorption_vol_z_thresh": 0.5})),
            ("E_s2_absc6", m({"absorption_min_count": 6})),
            ("E_s2_absc14", m({"absorption_min_count": 14})),
        ]
    if mod == "C":
        return [
            ("C_s2_1000_2000", m({"stop_loss_amount": 1000.0, "profit_target_amount": 2000.0})),
            ("C_s2_1500_3000", m({"stop_loss_amount": 1500.0, "profit_target_amount": 3000.0})),
            ("C_s2_2000_3000", m({"stop_loss_amount": 2000.0, "profit_target_amount": 3000.0})),
            ("C_s2_gap1", m({"minimum_gap_points": 1.0})),
            ("C_s2_gap5", m({"minimum_gap_points": 5.0})),
            ("C_s2_gap10", m({"minimum_gap_points": 10.0})),
            ("C_s2_max1", m({"max_entries_per_day": 1})),
            ("C_s2_max3", m({"max_entries_per_day": 3})),
            ("C_s2_lb6", m({"prior_bars_lookback": 6})),
            ("C_s2_lb20", m({"prior_bars_lookback": 20})),
        ]
    if mod == "Z":
        return [
            ("Z_il_default", {}),
            ("Z_s2_eff35", {"min_efficiency_pct": 35.0}),
            ("Z_s2_eff55", {"min_efficiency_pct": 55.0}),
            ("Z_s2_ema10", {"ema_period": 10}),
            ("Z_s2_ema30", {"ema_period": 30}),
            ("Z_s2_bkt10", {"bucket_minutes": 10}),
            ("Z_s2_bkt30", {"bucket_minutes": 30}),
        ]
    return []


def _seleccionar_promocion_oos(
    mod: str,
    base_row: dict[str, Any],
    df_mod_cand: pd.DataFrame,
) -> dict[str, Any]:
    """Criterio fail-closed: exige mejora >= +0.03 en `score_pre` y validacion OOS `r_nivel_25_26 >= 0.80`."""
    base_score = float(base_row.get("score_pre", np.nan))
    base_post = float(base_row.get("r_nivel_25_26", np.nan))
    if df_mod_cand.empty:
        return {"promovido": False, "razon": "sin_candidatos"}

    orden = df_mod_cand.sort_values(["score_pre", "r_nivel_25_26", "r_total"], ascending=False)
    for _, r in orden.iterrows():
        params = json.loads(r["parametros_json"])
        if not params:
            continue
        sc = float(r["score_pre"]) if not pd.isna(r["score_pre"]) else -9.0
        post = float(r["r_nivel_25_26"]) if not pd.isna(r["r_nivel_25_26"]) else -9.0
        mejora = sc - (base_score if not np.isnan(base_score) else 0.0)
        caida_post = (base_post - post) if not np.isnan(base_post) else 0.0
        if mejora >= 0.03 and post >= 0.80 and caida_post <= 0.05:
            return {
                "promovido": True,
                "config": r["config"],
                "variante": r["variante"],
                "modo_serie": r["modo_serie"],
                "parametros": params,
                "score_pre": float(sc),
                "r_nivel_22_24": float(r["r_nivel_22_24"]),
                "r_delta_22_24": float(r["r_delta_22_24"]),
                "r_nivel_25_26": float(post),
                "r_delta_25_26": float(r["r_delta_25_26"]) if not pd.isna(r["r_delta_25_26"]) else None,
                "r_total": float(r["r_total"]),
                "rmse_zscore": float(r["rmse_zscore"]),
                "mejora_score_pre": round(float(mejora), 4),
            }
    best = orden.iloc[0]
    return {
        "promovido": False,
        "mejor_candidato": best["config"],
        "mejor_params": json.loads(best["parametros_json"]),
        "score_pre": float(best["score_pre"]) if not pd.isna(best["score_pre"]) else None,
        "r_nivel_25_26": float(best["r_nivel_25_26"]) if not pd.isna(best["r_nivel_25_26"]) else None,
        "razon": "no_cumple_puerta_oos_o_mejora_minima",
    }


def _escalar_desde_origen(y_edge: np.ndarray, t_edge: np.ndarray, df_vend: pd.DataFrame) -> np.ndarray:
    """Escala proporcional positiva (`y / $/grilla`) anclada en 0 al inicio de la ventana."""
    y0 = y_edge - float(y_edge[0])
    t_v = df_vend["fecha"].to_numpy(dtype="datetime64[D]").astype(float)
    t_e = t_edge.astype("datetime64[D]").astype(float)
    y_i = np.interp(t_v, t_e, y0)
    y_v = df_vend["y_vendedor"].to_numpy(dtype=float)
    denom = float(np.dot(y_i, y_i))
    if denom < 1e-9:
        return np.zeros_like(y0)
    scale = float(np.dot(y_i, y_v)) / denom
    if scale <= 0.0:
        return y0 / max(float(np.std(y_i)), 1e-9) * max(float(np.std(y_v)), 1e-9)
    return y0 * scale


def _alinear_afin(y_edge: np.ndarray, t_edge: np.ndarray, df_vend: pd.DataFrame) -> np.ndarray:
    """Ajusta escala y desplazamiento (`a*y + b`) por minimos cuadrados solo para overlay visual."""
    t_v = df_vend["fecha"].to_numpy(dtype="datetime64[D]").astype(float)
    t_e = t_edge.astype("datetime64[D]").astype(float)
    y_interp = np.interp(t_v, t_e, y_edge)
    y_v = df_vend["y_vendedor"].to_numpy(dtype=float)
    if np.std(y_interp) < 1e-9:
        return np.zeros_like(y_edge)
    a, b = np.polyfit(y_interp, y_v, 1)
    if a < 0:
        # Mantener signo real de la estrategia para no ocultar anticorrida visualmente
        std_r = np.std(y_v) / max(np.std(y_interp), 1e-9)
        return (y_edge - y_edge[0]) * std_r
    return a * y_edge + b


def graficar_entregables_paridad(
    resumen: Mapping[str, Any],
    nonadj: Mapping[str, pd.DataFrame],
    backadj: Mapping[str, pd.DataFrame],
    series_calibradas: Mapping[str, pd.DataFrame] | None = None,
    out_dir: Path = PARIDAD_DIR,
    copiar_artifacts: bool = True,
) -> dict[str, Path]:
    """Genera las 3 figuras solicitadas: Foto 1 (v2), Foto 2 (EdgeLab calibrada) y panel 14x."""
    if plt is None:
        raise RuntimeError("matplotlib es requerido para graficar_entregables_paridad")
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_v2 = DEFAULT_CSV_V2
    teal_map = resumen.get("teal", {}).get("asignacion", {"S": "TEAL_LOWER", "T": "TEAL_UPPER"})

    # 1) Foto 1 — Original del vendedor re-vectorizada limpia v2 (cero saltos)
    raw_v2 = pd.read_csv(csv_v2)
    fig1, ax1 = plt.subplots(figsize=(14, 7.5), facecolor="#0d1316")
    ax1.set_facecolor("#11191c")
    for y_g in (0.0, 1.0, 2.0, 3.0, 4.0):
        ax1.axhline(y_g, color="#2a3840" if y_g == 0.0 else "#1c262c", linewidth=0.9)
    for mod in MODS_14:
        label, col, ls = ESTILO_VENDEDOR[mod]
        track = f"A · {teal_map[mod]}" if mod in teal_map else label
        sub = raw_v2[raw_v2["estrategia"] == track].sort_values("x_px")
        for _, seg in sub.groupby("segmento_id"):
            ax1.plot(pd.to_datetime(seg["fecha"]), seg["y_grid_unidades"], color=col, linestyle=ls, linewidth=1.6, alpha=0.95)
        ax1.plot([], [], color=col, linestyle=ls, linewidth=2.0, label=f"{label} ({len(sub)})")
    ax1.set_xlim(pd.Timestamp("2021-09-15"), pd.Timestamp("2026-04-30"))
    ax1.set_ylim(-0.55, 3.95)
    ax1.set_title("FOTO 1 — Vendedor original vectorizada limpia v2 (2021-10 -> 2026-04, sin superposicion)", color="#e2eaee", fontsize=12)
    ax1.set_ylabel("Unidades de grilla", color="#9cb0b8")
    ax1.tick_params(colors="#9cb0b8")
    for sp in ax1.spines.values():
        sp.set_color("#243036")
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=5, fontsize=9, frameon=False, labelcolor="#d9e2e6")
    fig1.tight_layout()
    p1 = out_dir / "foto_1_vendedor_vectorizada_v2.png"
    fig1.savefig(p1, dpi=160, bbox_inches="tight", facecolor=fig1.get_facecolor())
    plt.close(fig1)

    # Resolver series finales calibradas (por defecto o override promovido)
    series_fin: dict[str, pd.DataFrame] = {}
    metas_fin: dict[str, dict[str, Any]] = {r["modulo"]: r for r in resumen.get("tabla_final", [])}
    for mod in MODS_14:
        if series_calibradas and mod in series_calibradas:
            series_fin[mod] = series_calibradas[mod]
        else:
            meta = metas_fin.get(mod, {})
            cfg_name = str(meta.get("config_final", "nonadj_bruto_1cto"))
            src_dict = backadj if cfg_name.startswith("backadj") and mod in backadj else nonadj
            modo = "bruto_1cto"
            for cand_m in ("usd_dll_edge", "usd_dll_nt8", "usd_dll", "edge_1cto", "nt8_1cto", "bruto_1cto"):
                if cfg_name.endswith(cand_m):
                    modo = cand_m
                    break
            series_fin[mod] = serie_diaria_desde_trades(src_dict[mod], modo=modo, desde="2021-09-15", hasta="2026-09-30")

    # 2) Foto 2 — Curvas EdgeLab calibradas (ancladas en y=0 inicial, escala proporcional USD->grilla)
    fig2, ax2 = plt.subplots(figsize=(14, 7.5), facecolor="#0d1316")
    ax2.set_facecolor("#11191c")
    for y_g in (0.0, 1.0, 2.0, 3.0, 4.0):
        ax2.axhline(y_g, color="#2a3840" if y_g == 0.0 else "#1c262c", linewidth=0.9)
    for mod in MODS_14:
        label, col, ls = ESTILO_VENDEDOR[mod]
        s = series_fin[mod].sort_values("fecha").copy()
        s = s[s["fecha"] <= pd.Timestamp("2026-04-30")].copy()
        s["eq"] = s["pnl_diario"].cumsum()
        df_v = cargar_curva_vendedor(csv_v2, mod, teal_map=teal_map)
        y_al = _escalar_desde_origen(s["eq"].to_numpy(dtype=float), s["fecha"].to_numpy(), df_v)
        r_tot = metas_fin.get(mod, {}).get("r_total_final", np.nan)
        ax2.plot(s["fecha"], y_al, color=col, linestyle=ls, linewidth=1.6, alpha=0.93, label=f"{label} (r={r_tot:.2f})")
    ax2.set_xlim(pd.Timestamp("2021-09-15"), pd.Timestamp("2026-04-30"))
    ax2.set_ylim(-0.55, 3.95)
    ax2.set_title("FOTO 2 — EdgeLab paridad calibrada OOS (2021-10 -> 2026-04, escala proporcional USD->grilla)", color="#e2eaee", fontsize=12)
    ax2.set_ylabel("Unidades de grilla (proporcional desde origen)", color="#9cb0b8")
    ax2.tick_params(colors="#9cb0b8")
    for sp in ax2.spines.values():
        sp.set_color("#243036")
    ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=5, fontsize=9, frameon=False, labelcolor="#d9e2e6")
    fig2.tight_layout()
    p2 = out_dir / "foto_2_edgelab_paridad_calibrada.png"
    fig2.savefig(p2, dpi=160, bbox_inches="tight", facecolor=fig2.get_facecolor())
    plt.close(fig2)

    # 3) Panel 14 subplots: Vendedor v2 vs il_fabrica vs vendedor_calibrado
    fig3, axes = plt.subplots(4, 4, figsize=(18, 13), facecolor="#0d1316")
    axes_flat = axes.flatten()
    for i, mod in enumerate(MODS_14):
        ax = axes_flat[i]
        ax.set_facecolor("#11191c")
        label, col, _ = ESTILO_VENDEDOR[mod]
        df_v = cargar_curva_vendedor(csv_v2, mod, teal_map=teal_map)
        track = f"A · {teal_map[mod]}" if mod in teal_map else label
        sub_seg = raw_v2[raw_v2["estrategia"] == track].sort_values("x_px")

        s_fab = serie_diaria_desde_trades(nonadj[mod], modo="bruto_1cto", desde="2021-09-15", hasta="2026-09-30")
        s_fab = s_fab[s_fab["fecha"] <= pd.Timestamp("2026-04-30")].copy()
        s_fab["eq"] = s_fab["pnl_diario"].cumsum()
        y_fab_al = _alinear_afin(s_fab["eq"].to_numpy(dtype=float), s_fab["fecha"].to_numpy(), df_v)

        s_cal = series_fin[mod].sort_values("fecha")
        s_cal = s_cal[s_cal["fecha"] <= pd.Timestamp("2026-04-30")].copy()
        s_cal["eq"] = s_cal["pnl_diario"].cumsum()
        y_cal_al = _alinear_afin(s_cal["eq"].to_numpy(dtype=float), s_cal["fecha"].to_numpy(), df_v)

        for _, seg in sub_seg.groupby("segmento_id"):
            ax.plot(pd.to_datetime(seg["fecha"]), seg["y_grid_unidades"], color="#ffffff", linewidth=1.8, alpha=0.9)
        ax.plot(s_fab["fecha"], y_fab_al, color="#8ea0aa", linestyle=":", linewidth=1.1, alpha=0.75, label="il_fabrica")
        ax.plot(s_cal["fecha"], y_cal_al, color=col, linewidth=1.5, alpha=0.95, label="calibrado")
        ax.axvline(pd.Timestamp("2025-01-01"), color="#38474f", linestyle="--", linewidth=0.8)

        meta = metas_fin.get(mod, {})
        ax.set_title(
            f"{label} | pre={meta.get('r_nivel_22_24', np.nan):.2f} post={meta.get('r_nivel_25_26', np.nan):.2f} d={meta.get('r_delta_22_24', np.nan):.2f} tot={meta.get('r_total_final', np.nan):.2f}",
            color="#e2eaee",
            fontsize=8.5,
        )
        ax.tick_params(colors="#8b9ca4", labelsize=7)
        for sp in ax.spines.values():
            sp.set_color("#243036")
    for j in range(len(MODS_14), len(axes_flat)):
        axes_flat[j].set_visible(False)
    fig3.suptitle("Comparativa 14 Modulos: Vendedor v2 (blanco) vs IL Fabrica (punteado gris) vs Perfil Calibrado (color) | Split OOS 2025-01", color="#e8eff2", fontsize=12)
    fig3.tight_layout(rect=[0, 0, 1, 0.96])
    p3 = out_dir / "comparativa_panel_14_modulos_paridad_20261121.png"
    fig3.savefig(p3, dpi=150, facecolor=fig3.get_facecolor())
    plt.close(fig3)

    if copiar_artifacts and ARTIFACTS_DIR.exists():
        for src_p in (p1, p2, p3):
            shutil.copy2(src_p, ARTIFACTS_DIR / src_p.name)

    return {"foto_1": p1, "foto_2": p2, "panel_14": p3}


def ejecutar_barrido_completo(
    *,
    etapas: tuple[int, ...] = (0, 1, 2),
    out_dir: Path = PARIDAD_DIR,
) -> dict[str, Any]:
    """Ejecuta Etapa 0 -> Etapa 1 -> Etapa 2 y exporta CSVs + resumen JSON."""
    out_dir.mkdir(parents=True, exist_ok=True)
    nonadj, backadj = cargar_caches_baseline()
    res0 = ejecutar_etapa0_baseline(nonadj, backadj, out_dir=out_dir)
    teal_map = res0["teal"]["asignacion"]
    base_por_mod = {r["modulo"]: r for r in res0["best_baseline"].to_dict(orient="records")}

    if 1 not in etapas and 2 not in etapas:
        return {"res0": res0}

    ms = _cargar_ms_dev()
    etapa1_rows: list[dict[str, Any]] = []
    cache_total: dict[str, tuple[pd.DataFrame, dict[str, Any]]] = {}

    if 1 in etapas:
        gr1 = construir_grilla_etapa1()
        for mod, cands in gr1.items():
            rows_m, cache_m = _evaluar_candidatos_modulo(ms, mod, cands, teal_map, "etapa1")
            etapa1_rows.extend(rows_m)
            cache_total.update(cache_m)
            print(f"[ETAPA 1] {mod}: evaluadas {len(cands)} variantes ({len(rows_m)} filas)")
        df_e1 = pd.DataFrame(etapa1_rows)
        df_e1.to_csv(out_dir / "sweep_etapa1_ejecucion.csv", index=False)
    else:
        e1_csv = out_dir / "sweep_etapa1_ejecucion.csv"
        df_e1 = pd.read_csv(e1_csv) if e1_csv.exists() else pd.DataFrame()

    etapa2_rows: list[dict[str, Any]] = []
    if 2 in etapas:
        for mod in ("F", "S", "W", "E", "C", "Z"):
            base_params: dict[str, Any] = {}
            if not df_e1.empty:
                sub1 = df_e1[df_e1["modulo"] == mod].sort_values(["score_pre", "r_nivel_25_26"], ascending=False)
                if not sub1.empty:
                    cand_p = json.loads(sub1.iloc[0]["parametros_json"])
                    cand_post = float(sub1.iloc[0]["r_nivel_25_26"]) if not pd.isna(sub1.iloc[0]["r_nivel_25_26"]) else -9.0
                    if cand_p and cand_post >= 0.70:
                        base_params = cand_p
            cands2 = _combinar_etapa2_para_modulo(mod, base_params)
            rows_m, cache_m = _evaluar_candidatos_modulo(ms, mod, cands2, teal_map, "etapa2")
            etapa2_rows.extend(rows_m)
            cache_total.update(cache_m)
            print(f"[ETAPA 2] {mod}: evaluadas {len(cands2)} variantes ({len(rows_m)} filas)")
        df_e2 = pd.DataFrame(etapa2_rows)
        df_e2.to_csv(out_dir / "sweep_etapa2_parametros.csv", index=False)
    else:
        e2_csv = out_dir / "sweep_etapa2_parametros.csv"
        df_e2 = pd.read_csv(e2_csv) if e2_csv.exists() else pd.DataFrame()

    df_cand = pd.concat([df_e1, df_e2], ignore_index=True) if (not df_e1.empty or not df_e2.empty) else pd.DataFrame()

    promociones: dict[str, Any] = {}
    tabla_final: list[dict[str, Any]] = []
    best_series_cache: dict[str, pd.DataFrame] = {}

    for mod in MODS_14:
        b = base_por_mod[mod]
        sub_c = df_cand[df_cand["modulo"] == mod] if not df_cand.empty else pd.DataFrame()
        promo = _seleccionar_promocion_oos(mod, b, sub_c)
        promociones[mod] = promo
        if promo.get("promovido"):
            cfg_win = promo["config"]
            if cfg_win in cache_total:
                best_series_cache[mod] = cache_total[cfg_win][0]
            fila = {
                "modulo": mod,
                "config_base": b["config"],
                "score_pre_base": b["score_pre"],
                "r_total_base": b["r_total"],
                "config_final": cfg_win,
                "parametros_final": promo["parametros"],
                "score_pre_final": promo["score_pre"],
                "r_nivel_22_24": promo["r_nivel_22_24"],
                "r_delta_22_24": promo["r_delta_22_24"],
                "r_nivel_25_26": promo["r_nivel_25_26"],
                "r_delta_25_26": promo["r_delta_25_26"],
                "r_total_final": promo["r_total"],
                "rmse_zscore": promo["rmse_zscore"],
                "promovido": True,
            }
        else:
            fila = {
                "modulo": mod,
                "config_base": b["config"],
                "score_pre_base": b["score_pre"],
                "r_total_base": b["r_total"],
                "config_final": b["config"],
                "parametros_final": {},
                "score_pre_final": b["score_pre"],
                "r_nivel_22_24": b["r_nivel_22_24"],
                "r_delta_22_24": b["r_delta_22_24"],
                "r_nivel_25_26": b["r_nivel_25_26"],
                "r_delta_25_26": b["r_delta_25_26"],
                "r_total_final": b["r_total"],
                "rmse_zscore": b["rmse_zscore"],
                "promovido": False,
            }
        tabla_final.append(fila)

    resumen = {
        "teal": res0["teal"],
        "promociones": promociones,
        "tabla_final": tabla_final,
    }
    (out_dir / "resumen_paridad_final.json").write_text(json.dumps(resumen, indent=2, default=str), encoding="utf-8")
    DEFAULT_BEST_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_BEST_CACHE.open("wb") as f:
        pickle.dump(best_series_cache, f)

    rutas = graficar_entregables_paridad(resumen, nonadj, backadj, series_calibradas=best_series_cache, out_dir=out_dir)
    print(f"[OK] Graficos -> {rutas}")
    return {"resumen": resumen, "rutas": rutas}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Barrido de paridad OOS y graficado de FundedsyncStack contra vendedor.")
    ap.add_argument("--solo-etapa0", action="store_true", help="Ejecuta solo Etapa 0 sobre caches locales")
    ap.add_argument("--graficar", action="store_true", help="Regenera solo graficos desde resumen_paridad_final.json")
    args = ap.parse_args(argv)

    if args.graficar:
        res_p = PARIDAD_DIR / "resumen_paridad_final.json"
        resumen = json.loads(res_p.read_text(encoding="utf-8"))
        nonadj, backadj = cargar_caches_baseline()
        series_cal: dict[str, pd.DataFrame] = {}
        if DEFAULT_BEST_CACHE.exists():
            with DEFAULT_BEST_CACHE.open("rb") as f:
                series_cal = pickle.load(f)
        graficar_entregables_paridad(resumen, nonadj, backadj, series_calibradas=series_cal)
        return 0

    etapas = (0,) if args.solo_etapa0 else (0, 1, 2)
    ejecutar_barrido_completo(etapas=etapas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

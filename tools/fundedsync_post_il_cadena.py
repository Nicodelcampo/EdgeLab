#!/usr/bin/env python3
"""Campana post-IL de `FUNDEDSYNCSTACK` sobre M1 real de futuros (NQ, ES, YM, RTY, EMD) en unidad R.

Uso:
  python tools/fundedsync_post_il_cadena.py bloque_a [--workers 2]
  python tools/fundedsync_post_il_cadena.py bloque_b13 [--workers 2]
  python tools/fundedsync_post_il_cadena.py bloque_b4 [--workers 2]
  python tools/fundedsync_post_il_cadena.py todo [--workers 2]
"""
from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import gc
import hashlib
import json
import os
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

from edgelab import costos
from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS, a5_bloque, a5_meses
from edgelab.research import diagnostico_grilla as DG
from edgelab.research.fundedsyncstack import CONFIG_CLASSES, MODULOS, build_multi_series, correr_modulo, load_m1_data
from edgelab.research.m1_intradia import leer_m1nt8
from edgelab.research.puerta_corrida import verificar_corrida
from m1_largo import _sesion, atr20
from registro_global import exigir_contada

PREREG_REL = "docs/research/fundedsync_post_il_20261122/PREREGISTRO.md"
OUT_DIR = ROOT / "docs/research/fundedsync_post_il_20261122"
CACHE_DIR = ROOT / "data/fundedsync_post_il_20261122"
ARTIFACTS_DIR = Path(r"C:\Users\nicoc\.gemini\antigravity\brain\417d395c-1bd7-4157-b782-277352881af1")
DEFAULT_M1_DIR = Path(r"C:\Users\nicoc\OneDrive\Documentos\NinjaTrader 8\exports\edgelab_nt8_m1_parquet")

MICRO_EQUIV: dict[str, str] = {"NQ": "MNQ", "ES": "MES", "YM": "MYM"}
STOP_ATR_DEFAULT: dict[str, float | None] = {
    "A1": None, "A20": None, "F": None, "P": None, "C": None, "V": None, "E": None, "Q": None, "T": None,
    "S": 0.50, "W": 0.50, "N": 0.50, "R": 0.25, "Z": 0.25, "O": 0.50,
}
_PESO_MOD_ORDEN: dict[str, int] = {
    "A1": 400, "P": 85, "S": 65, "T": 56, "O": 53, "N": 38, "Z": 31,
    "E": 25, "A20": 24, "C": 24, "R": 24, "W": 17, "Q": 14, "F": 12, "V": 6,
}
_WORKER_MS: Any = None


def asegurar_compuerta() -> None:
    """Verifica K51 (`registro_global.exigir_contada`) y capas L1..L4 antes de leer datos."""
    exigir_contada(PREREG_REL)
    rep = verificar_corrida(
        prereg=PREREG_REL,
        familia="FUNDEDSYNC",
        exigir_contada=True,
        verificar_estado=True,
        root=ROOT,
    )
    if not rep["ok"]:
        raise SystemExit("puerta_corrida bloqueo ejecucion: " + "; ".join(rep["errores"]))


def friccion_instrumento_puntos(inst: str) -> tuple[float, float | None]:
    """Devuelve `(friccion_mini_pts, friccion_micro_pts_o_None)` usando `edgelab/costos.py` + K33."""
    sym = inst.upper()
    with costos.estimados_permitidos(PREREG_REL):
        fric_mini = float(costos.friccion_rt_puntos(sym, "base"))
        mic = MICRO_EQUIV.get(sym)
        fric_micro = float(costos.friccion_rt_puntos(mic, "base")) if mic else None
    return fric_mini, fric_micro


def _cache_key(inst: str, modulo: str, params: Mapping[str, Any] | None = None) -> str:
    """Genera clave de cache determinista entre procesos (sin salt aleatoria)."""
    sym = inst.upper()
    if not params:
        return f"{sym}_fabrica_{modulo}"
    p_json = json.dumps(dict(params), sort_keys=True)
    h = hashlib.sha256(p_json.encode("utf-8")).hexdigest()[:10]
    return f"{sym}_{modulo}_{h}"


def _resolver_parquet(inst: str, m1_dir: Path | None = None) -> Path:
    base = DEFAULT_M1_DIR if m1_dir is None else Path(m1_dir)
    pq_path = base / f"{inst.upper()}_M1_nonadj_utc.parquet"
    if not pq_path.exists():
        raise FileNotFoundError(f"No existe M1 parquet para {inst}: {pq_path}")
    return pq_path


def _cargar_series_sesion(
    inst: str,
    m1_dir: Path | None = None,
    desde: str = "2008-01-01",
) -> tuple[pd.Series, pd.Series, float, int]:
    """Calcula `atr20(D_ny)`, rango ORB15 causal, `point_value` y fecha inicial sin retener `MultiSeries`."""
    pq_path = _resolver_parquet(inst, m1_dir=m1_dir)
    d_ny = leer_m1nt8(pq_path)
    d_ny = d_ny[d_ny.index >= desde]
    primer_fecha_int = int(pd.Timestamp(d_ny.index.min()).strftime("%Y%m%d")) if len(d_ny) else 20080101
    atr_ses = atr20(d_ny)
    mm = d_ny.index.hour * 60 + d_ny.index.minute
    orb = d_ny[(mm >= 570) & (mm < 585)]
    dd_orb = orb.index.normalize()
    orb15_t = ((orb.h.groupby(dd_orb).max() - orb.l.groupby(dd_orb).min()) * 1.25).clip(2.0, 100.0)
    del d_ny, mm, orb, dd_orb
    gc.collect()
    tick = float(costos.tick_size(inst.upper()))
    pv = float(costos.tick_value_usd(inst.upper()) / tick)
    return atr_ses, orb15_t, pv, primer_fecha_int


def _cargar_ms_futuro(
    inst: str,
    m1_dir: Path | None = None,
    desde: str = "2008-01-01",
) -> Any:
    """Construye `MultiSeries` M1/M5/D1 truncado fisicamente `< HOLDOUT_APERTURA_UTC_NS`."""
    pq_path = _resolver_parquet(inst, m1_dir=m1_dir)
    raw = pd.read_parquet(pq_path)
    idx_utc = pd.DatetimeIndex(raw.index if "datetime" not in raw else raw["datetime"]).astype("datetime64[ns]")
    ts_i8 = idx_utc.asi8
    d_i8 = np.int64(pd.Timestamp(desde).as_unit("ns").value)
    mask = (ts_i8 >= d_i8) & (ts_i8 < int(HOLDOUT_APERTURA_UTC_NS))
    sub = raw.loc[mask].reset_index()
    del raw, idx_utc, ts_i8, mask
    tick = float(costos.tick_size(inst.upper()))
    pv = float(costos.tick_value_usd(inst.upper()) / tick)
    df_m1 = load_m1_data(sub, start=desde, end="2026-10-01", tz_input="UTC", allow_sellado=False)
    del sub
    ms = build_multi_series(df_m1, tick_size=tick, point_value=pv, tz_input="UTC", allow_sellado=False)
    del df_m1
    gc.collect()
    return ms


def cargar_contexto_futuro(
    inst: str,
    m1_dir: Path | None = None,
    desde: str = "2008-01-01",
) -> tuple[Any, pd.DataFrame, pd.Series, pd.Series]:
    """Wrapper compatible: carga `MultiSeries`, `atr20(D_ny)` y rango ORB15 causal pre-holdout."""
    atr_ses, orb15_t, _, _ = _cargar_series_sesion(inst, m1_dir=m1_dir, desde=desde)
    ms = _cargar_ms_futuro(inst, m1_dir=m1_dir, desde=desde)
    return ms, pd.DataFrame(), atr_ses, orb15_t


def _escribir_pkl_atomico(cache_name: str, df_t: pd.DataFrame) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = CACHE_DIR / f"{cache_name}.pkl"
    p_tmp = CACHE_DIR / f"{cache_name}.{os.getpid()}.tmp.pkl"
    df_t.to_pickle(p_tmp)
    os.replace(p_tmp, p)


def _ejecutar_job_con_ms(cache_name: str, modulo: str, params: Mapping[str, Any], ms: Any) -> tuple[str, int, float]:
    p = CACHE_DIR / f"{cache_name}.pkl"
    if p.exists():
        return cache_name, -1, 0.0
    cls = CONFIG_CLASSES[modulo]
    cfg = dataclasses.replace(cls(), **dict(params)) if params else cls()
    t0 = time.perf_counter()
    df_t = correr_modulo(modulo, ms, cfg=cfg)
    dt = time.perf_counter() - t0
    _escribir_pkl_atomico(cache_name, df_t)
    return cache_name, int(len(df_t)), dt


def _init_worker_inst(inst: str, m1_dir_str: str | None) -> None:
    """Inicializador de worker Windows/spawn: carga un unico `MultiSeries` por proceso."""
    global _WORKER_MS
    m1_dir = Path(m1_dir_str) if m1_dir_str else None
    _WORKER_MS = _cargar_ms_futuro(inst, m1_dir=m1_dir)


def _run_job_en_worker(job: tuple[str, str, dict[str, Any]]) -> tuple[str, int, float]:
    cache_name, modulo, params = job
    return _ejecutar_job_con_ms(cache_name, modulo, params, _WORKER_MS)


def _run_instrumento_b4_worker(
    args: tuple[str, list[tuple[str, str, dict[str, Any]]], str | None],
) -> list[tuple[str, int, float]]:
    """Corre en un worker todos los jobs pendientes de un instrumento externo de Bloque B4."""
    inst, jobs, m1_dir_str = args
    pend = [j for j in jobs if not (CACHE_DIR / f"{j[0]}.pkl").exists()]
    if not pend:
        return []
    m1_dir = Path(m1_dir_str) if m1_dir_str else None
    ms = _cargar_ms_futuro(inst, m1_dir=m1_dir)
    out = [_ejecutar_job_con_ms(cname, mod, params, ms) for cname, mod, params in pend]
    del ms
    gc.collect()
    return out


def _cargar_trades_cacheados(cache_name: str) -> pd.DataFrame:
    p = CACHE_DIR / f"{cache_name}.pkl"
    if not p.exists():
        raise FileNotFoundError(f"Cache faltante inesperado: {p}")
    return pd.read_pickle(p)


def _empty_ops_df() -> pd.DataFrame:
    return pd.DataFrame({
        "fecha_int": pd.Series(dtype="int64"),
        "mes": pd.Series(dtype="object"),
        "a5": pd.Series(dtype="object"),
        "pnl_pts": pd.Series(dtype="float64"),
        "mae_pts": pd.Series(dtype="float64"),
        "riesgo_pts": pd.Series(dtype="float64"),
        "R_bruto": pd.Series(dtype="float64"),
        "R_neto_mini": pd.Series(dtype="float64"),
        "R_neto_micro": pd.Series(dtype="float64"),
        "fric_R": pd.Series(dtype="float64"),
        "side": pd.Series(dtype="int64"),
    })


def convertir_trades_a_ops_r(
    df_trades: pd.DataFrame,
    modulo: str,
    inst: str,
    atr_ses: pd.Series,
    orb15_t: pd.Series,
    ms: Any,
    *,
    stop_atr_k: float | None = None,
    cap_mae_atr_k: float | None = None,
) -> pd.DataFrame:
    """Convierte trades brutos a tabla en unidad `R` con particion temporal A4 y A5."""
    if df_trades is None or len(df_trades) == 0:
        return _empty_ops_df()

    en_utc = pd.to_datetime(df_trades["entry_time_utc"], utc=True)
    tt_ny = en_utc.dt.tz_convert("America/New_York").dt.tz_localize(None)
    ses = _sesion(pd.DatetimeIndex(tt_ny))
    atr_vec = atr_ses.reindex(ses).to_numpy(dtype=float)

    pp = pd.to_numeric(df_trades["pnl_pts"], errors="coerce").to_numpy(dtype=float)
    pu = pd.to_numeric(df_trades["pnl_usd"], errors="coerce").to_numpy(dtype=float)
    qt = pd.to_numeric(df_trades["qty"], errors="coerce").abs().replace(0, np.nan).to_numpy(dtype=float)
    mae_u = pd.to_numeric(df_trades["mae_usd"], errors="coerce").abs().to_numpy(dtype=float)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio_pv = np.abs(pu) / (np.abs(pp) * qt)
    finite_pv = ratio_pv[np.isfinite(ratio_pv) & (ratio_pv > 0)]
    pv_unit = float(np.median(finite_pv)) if len(finite_pv) else (
        float(ms.point_value / 10.0) if modulo == "Q" else float(ms.point_value)
    )
    mae_pts = mae_u / np.maximum(qt * pv_unit, 1e-9)

    en_px = pd.to_numeric(df_trades["entry_price"], errors="coerce").to_numpy(dtype=float)
    st_px = pd.to_numeric(df_trades["stop_price"], errors="coerce").to_numpy(dtype=float)
    nat_stop = np.abs(en_px - st_px)

    if modulo == "T":
        orb_vec = orb15_t.reindex(pd.DatetimeIndex(tt_ny).normalize()).to_numpy(dtype=float)
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
    if not ok.any():
        return _empty_ops_df()

    fric_mini, fric_micro = friccion_instrumento_puntos(inst)
    fecha_int = pd.DatetimeIndex(ses).strftime("%Y%m%d").astype(int)
    a5_labels = np.array([a5_bloque(int(f)) for f in fecha_int], dtype=object)
    # Blindaje duro HOLDOUT-A4
    ok = ok & (a5_labels != "TERMINAL")

    riesgo_k = riesgo[ok]
    pnl_k = pnl_eff[ok]
    r_bruto = pnl_k / riesgo_k
    r_mini = (pnl_k - fric_mini) / riesgo_k
    r_micro = ((pnl_k - fric_micro) / riesgo_k) if fric_micro is not None else np.full_like(r_mini, np.nan)
    fric_r = fric_mini / riesgo_k

    return pd.DataFrame({
        "fecha_int": fecha_int[ok],
        "mes": pd.DatetimeIndex(ses)[ok].strftime("%Y-%m"),
        "a5": a5_labels[ok],
        "pnl_pts": pnl_k,
        "mae_pts": mae_pts[ok],
        "riesgo_pts": riesgo_k,
        "R_bruto": r_bruto,
        "R_neto_mini": r_mini,
        "R_neto_micro": r_micro,
        "fric_R": fric_r,
        "side": df_trades["side"].to_numpy(dtype=int)[ok],
    })


def _meses_activos_a5(start_int: int, end_int: int, part: str | None = None) -> int:
    """Cuenta meses calendario reales (o pertenecientes a `part` en A5) entre `start_int` y `end_int`."""
    y0, m0 = start_int // 10000, (start_int // 100) % 100
    y1, m1 = end_int // 10000, (end_int // 100) % 100
    ym_cur = y0 * 12 + (m0 - 1)
    ym_fin = y1 * 12 + (m1 - 1)
    if ym_fin < ym_cur:
        return 1
    cache_anios: dict[int, dict[int, str]] = {}
    cnt = 0
    for ym in range(ym_cur, ym_fin + 1):
        y, m = divmod(ym, 12)
        m += 1
        if part is None:
            cnt += 1
        else:
            amap = cache_anios.setdefault(y, a5_meses(y))
            if amap.get(m) == part:
                cnt += 1
    return max(cnt, 1)


def _episodios_seguro(ops: pd.DataFrame, col: str = "R_neto_mini", k: int = 3) -> str:
    if len(ops) < max(6, k + 1) or int(ops["mes"].nunique()) <= k:
        return "Episodios: muestra o meses insuficientes"
    return str(DG.episodios(ops[[col, "mes"]], valor=col, mes="mes", k=k)["linea"])


def resumir_serie_r(
    ops: pd.DataFrame,
    *,
    col_r: str = "R_neto_mini",
    bootstrap_reps: int = 1200,
    seed: int = 42,
    meses_totales: int | None = None,
) -> dict[str, Any]:
    """Calcula estadisticas en R con bootstrap por bloque de sesion (unilateral > 0)."""
    n = int(len(ops))
    if n == 0:
        return {
            "n": 0, "ops_mes": 0.0, "R_bruto": np.nan, "R_neto_mini": np.nan, "R_neto_micro": np.nan,
            "R_por_mes": np.nan, "t_ses": np.nan, "p_boot": 1.0, "med_fric_R": np.nan, "peor_mes_R": np.nan,
        }
    r = ops[col_r].to_numpy(dtype=float)
    r_br = ops["R_bruto"].to_numpy(dtype=float)
    r_mic = ops["R_neto_micro"].to_numpy(dtype=float)
    por_ses = ops.groupby("fecha_int")[col_r].sum().to_numpy(dtype=float)
    por_mes = ops.groupby("mes")[col_r].sum()
    n_meses = float(meses_totales) if meses_totales is not None else float(max(int(por_mes.shape[0]), 1))
    if meses_totales is None and n >= 2:
        f_dt = pd.to_datetime(ops["fecha_int"].astype(str), format="%Y%m%d")
        n_meses = max((f_dt.max() - f_dt.min()).days / 30.44, 1.0)
    ops_mes = float(n / max(n_meses, 1.0))

    if len(por_ses) >= 3 and float(np.std(por_ses, ddof=1)) > 1e-12:
        t_ses = float(np.mean(por_ses) / np.std(por_ses, ddof=1) * np.sqrt(len(por_ses)))
        rng = np.random.default_rng(seed)
        ns = len(por_ses)
        idx = rng.integers(0, ns, size=(int(bootstrap_reps), ns))
        boot_means = por_ses[idx].mean(axis=1)
        p_boot = float((1 + np.sum(boot_means <= 0.0)) / (len(boot_means) + 1))
    else:
        t_ses = np.nan
        p_boot = 1.0

    r_mean = float(np.nanmean(r))
    return {
        "n": n,
        "ops_mes": round(ops_mes, 2),
        "R_bruto": round(float(np.nanmean(r_br)), 4),
        "R_neto_mini": round(r_mean, 4),
        "R_neto_micro": round(float(np.nanmean(r_mic)), 4) if np.isfinite(r_mic).any() else np.nan,
        "R_por_mes": round(r_mean * ops_mes, 3),
        "t_ses": round(t_ses, 2) if np.isfinite(t_ses) else np.nan,
        "p_boot": round(p_boot, 4),
        "med_fric_R": round(float(np.nanmedian(ops["fric_R"])), 4),
        "peor_mes_R": round(float(por_mes.min()), 2) if len(por_mes) else np.nan,
    }


def _correr_bloque_a(
    atr_nq: pd.Series,
    orb_nq: pd.Series,
    pv_nq: float,
    m1_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Bloque A: los 15 modulos de fabrica en NQ real (2008 -> 2026-09-30) en unidad R."""
    regimes = [
        ("TOTAL", 20080101, 20260930, 225),
        ("PRE_2020", 20080101, 20191231, 144),
        ("POST_2020", 20200101, 20260831, 80),
        ("POST_2021", 20210101, 20260831, 68),
        ("VEND_A", 20200101, 20241231, 60),
        ("VEND_B_HASTA_1SEP", 20250101, 20260831, 20),
        ("POST_1SEP", 20260901, 20260930, 1),
    ]
    faltantes = [mod for mod in MODULOS if not (CACHE_DIR / f"NQ_fabrica_{mod}.pkl").exists()]
    if faltantes:
        ms_nq = _cargar_ms_futuro("NQ", m1_dir=m1_dir)
        for mod in faltantes:
            cname, n_tr, dt = _ejecutar_job_con_ms(f"NQ_fabrica_{mod}", mod, {}, ms_nq)
            print(f"  [RUN] {cname}: n={n_tr} ({dt:.1f}s)", flush=True)
        del ms_nq
        gc.collect()

    ms_ref = SimpleNamespace(point_value=pv_nq)
    rows: list[dict[str, Any]] = []
    ops_por_mod: dict[str, pd.DataFrame] = {}

    for mod in MODULOS:
        df_t = _cargar_trades_cacheados(f"NQ_fabrica_{mod}")
        ops = convertir_trades_a_ops_r(df_t, mod, "NQ", atr_nq, orb_nq, ms_ref, stop_atr_k=STOP_ATR_DEFAULT[mod])
        ops_por_mod[mod] = ops
        ep_total = _episodios_seguro(ops)
        ep_2020 = _episodios_seguro(ops[(ops["fecha_int"] >= 20200101) & (ops["fecha_int"] <= 20260831)])
        for rname, d0, d1, m_div in regimes:
            sub = ops[(ops["fecha_int"] >= d0) & (ops["fecha_int"] <= d1)]
            st = resumir_serie_r(sub, meses_totales=m_div)
            ep_txt = ep_total if rname == "TOTAL" else (ep_2020 if rname == "POST_2020" else "")
            rows.append({
                "modulo": mod,
                "regimen": rname,
                "elegible_intradia": mod != "O",
                **st,
                "episodios": ep_txt,
            })
    df_a = pd.DataFrame(rows)
    df_a.to_csv(OUT_DIR / "bloque_a_fabrica_nq.csv", index=False)
    return df_a, ops_por_mod


def _grillas_bloque_b() -> list[dict[str, Any]]:
    """Define las grillas B1, B2 y B3 exactamente conforme a PREREGISTRO.md (A5 DESC)."""
    specs: list[dict[str, Any]] = []
    # B1: V (12 nativos + 2 overlays MAE ATR20)
    for nm in (0.30, 0.40, 0.55):
        for vb in (2, 999):
            for tp in (1400.0, 99999.0):
                tag = f"V_nm{int(nm*100)}_vb{vb}_tp{int(tp)}"
                specs.append({
                    "grilla": "B1_V", "modulo": "V", "variante": tag,
                    "params": {"noise_multiplier": nm, "vwap_exit_bars": vb, "profit_target_usd_per_contract": tp},
                    "stop_atr_k": None, "cap_mae_atr_k": None,
                    "perillas": {"noise": str(nm), "vwap_exit": str(vb), "tp_usd": str(int(tp))},
                })
    for k_ov in (0.40, 0.60):
        specs.append({
            "grilla": "B1_V", "modulo": "V", "variante": f"V_fab_maeATR{int(k_ov*100)}",
            "params": {}, "stop_atr_k": None, "cap_mae_atr_k": k_ov,
            "perillas": {"noise": "0.4", "vwap_exit": "2", "tp_usd": "1400_mae"},
        })

    # B2: EOD + stop duro amplio en R (S, W, A20, N)
    for hm in (2.0, 3.0, 4.5):
        specs.append({
            "grilla": "B2_EOD", "modulo": "S", "variante": f"S_eod_hsATR{int(hm*10)}",
            "params": {"exit_on_st_flip": False, "use_hard_stop": True, "hard_stop_atr_mult": hm},
            "stop_atr_k": None, "cap_mae_atr_k": None,
            "perillas": {"mod": "S", "stop": f"hs_{hm}"},
        })
    for ka in (0.25, 0.50, 0.75):
        specs.append({
            "grilla": "B2_EOD", "modulo": "W", "variante": f"W_eod_maeATR{int(ka*100)}",
            "params": {"exit_on_vwap_cross": False, "allow_reentries": False},
            "stop_atr_k": ka, "cap_mae_atr_k": None,
            "perillas": {"mod": "W", "stop": f"mae_{ka}"},
        })
    for hm in (1.5, 2.5, 3.5):
        specs.append({
            "grilla": "B2_EOD", "modulo": "A20", "variante": f"A20_eod_hsATR{int(hm*10)}",
            "params": {"exit_on_st_flip": False, "use_hard_stop": True, "hard_stop_atr_mult": hm},
            "stop_atr_k": None, "cap_mae_atr_k": None,
            "perillas": {"mod": "A20", "stop": f"hs_{hm}"},
        })
    for frac in (0.5, 1.0):
        specs.append({
            "grilla": "B2_EOD", "modulo": "N", "variante": f"N_eod_loss{int(frac*10)}",
            "params": {"use_failed_breakout_exit": False, "maximum_loss_prior_range_fraction": frac},
            "stop_atr_k": 0.50, "cap_mae_atr_k": None,
            "perillas": {"mod": "N", "stop": f"loss_{frac}"},
        })
    specs.append({
        "grilla": "B2_EOD", "modulo": "N", "variante": "N_eod_eff",
        "params": {"use_failed_breakout_exit": False, "use_daily_efficiency_filter": True},
        "stop_atr_k": 0.50, "cap_mae_atr_k": None,
        "perillas": {"mod": "N", "stop": "eff"},
    })

    # B3: Escalado RR y ATR20 (Q, F, C, E)
    for rr in (0.30, 0.75, 1.50, 2.50):
        for bm in (6, 12):
            specs.append({
                "grilla": "B3_Q", "modulo": "Q", "variante": f"Q_rr{int(rr*100)}_bm{bm}",
                "params": {"risk_reward": rr, "break_margin_ticks": bm},
                "stop_atr_k": None, "cap_mae_atr_k": None,
                "perillas": {"rr": str(rr), "margin": str(bm)},
            })
    for tpr in (1.0, 1.5, 2.5):
        for mra in (0.0, 0.50):
            specs.append({
                "grilla": "B3_F", "modulo": "F", "variante": f"F_rr{int(tpr*10)}_atr{int(mra*10)}",
                "params": {"tp_rr": tpr, "max_initial_risk_atr": mra},
                "stop_atr_k": None, "cap_mae_atr_k": None,
                "perillas": {"tp_rr": str(tpr), "risk_atr": str(mra)},
            })
    for sl_u, tp_u, gap in ((1500.0, 2500.0, 2.0), (1500.0, 4000.0, 2.0), (2500.0, 5000.0, 2.0), (1500.0, 2500.0, 8.0)):
        specs.append({
            "grilla": "B3_C", "modulo": "C", "variante": f"C_sl{int(sl_u)}_tp{int(tp_u)}_g{int(gap)}",
            "params": {"stop_loss_amount": sl_u, "profit_target_amount": tp_u, "minimum_gap_points": gap},
            "stop_atr_k": None, "cap_mae_atr_k": None,
            "perillas": {"sl_tp": f"{int(sl_u)}_{int(tp_u)}", "gap": str(int(gap))},
        })
    for sp, tp in ((30.0, 45.0), (40.0, 80.0), (60.0, 120.0)):
        specs.append({
            "grilla": "B3_E", "modulo": "E", "variante": f"E_sl{int(sp)}_tp{int(tp)}",
            "params": {"stop_points": sp, "target_points": tp},
            "stop_atr_k": None, "cap_mae_atr_k": None,
            "perillas": {"sl": str(int(sp)), "tp": str(int(tp))},
        })
    return specs


def _precalentar_b13_nq(
    specs: list[dict[str, Any]],
    *,
    workers: int = 2,
    m1_dir: Path | None = None,
) -> None:
    """Simula en paralelo seguro en RAM todas las combinaciones unicas B1-B3 de NQ aun no cacheadas."""
    jobs_map: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for sp in specs:
        mod = str(sp["modulo"])
        params = dict(sp["params"])
        cname = _cache_key("NQ", mod, params)
        if cname not in jobs_map and not (CACHE_DIR / f"{cname}.pkl").exists():
            jobs_map[cname] = (cname, mod, params)
    jobs = sorted(jobs_map.values(), key=lambda j: (-_PESO_MOD_ORDEN.get(j[1], 20), j[0]))
    if not jobs:
        print("[CACHE] Bloque B1-B3 NQ completo en disco.", flush=True)
        return

    n_w = min(max(int(workers), 1), len(jobs))
    print(f"[B1-B3] Corriendo {len(jobs)} jobs NQ con workers={n_w}...", flush=True)
    m1_str = str(m1_dir) if m1_dir is not None else None
    t0_all = time.perf_counter()
    if n_w == 1:
        ms = _cargar_ms_futuro("NQ", m1_dir=m1_dir)
        for i, (cname, mod, params) in enumerate(jobs, 1):
            _, n_tr, dt = _ejecutar_job_con_ms(cname, mod, params, ms)
            print(f"  [RUN {i}/{len(jobs)}] {cname}: n={n_tr} ({dt:.1f}s)", flush=True)
        del ms
        gc.collect()
    else:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=n_w,
            initializer=_init_worker_inst,
            initargs=("NQ", m1_str),
        ) as ex:
            for i, (cname, n_tr, dt) in enumerate(ex.map(_run_job_en_worker, jobs), 1):
                print(f"  [RUN {i}/{len(jobs)}] {cname}: n={n_tr} ({dt:.1f}s)", flush=True)
    print(f"[B1-B3] Simulaciones terminadas en {time.perf_counter() - t0_all:.1f}s.", flush=True)


def _diagnostico_con_mejor(df_g: pd.DataFrame, per_fn: dict[str, Any], total_celdas: int | None = None) -> dict[str, Any]:
    df_clean = df_g.assign(R=pd.to_numeric(df_g["R"], errors="coerce")).dropna(subset=["R", "mes", "variante"]) if not df_g.empty else df_g
    if df_clean.empty:
        return {
            "variantes": 0, "degeneradas": [], "numero_efectivo": 0.0,
            "celdas_cero_ops": total_celdas or 0,
            "linea": "Diagnóstico de grilla: 0 variantes.",
            "episodios_mejor": "Episodios: n=0", "mejor_variante": "",
        }
    d_res = DG.diagnostico(df_clean, variante="variante", valor="R", mes="mes", perillas=per_fn)
    if total_celdas is not None:
        d_res["celdas_cero_ops"] = max(int(total_celdas) - int(d_res["variantes"]), 0)
    grupos = [g for _, g in df_clean.groupby("variante") if len(g) > 0]
    if grupos:
        elig = [g for g in grupos if len(g) >= 30] or grupos
        best_df = max(elig, key=lambda d: float(d["R"].mean()))
        best_var = str(best_df["variante"].iloc[0])
        d_res["episodios_mejor"] = _episodios_seguro(best_df, col="R")
        d_res["mejor_variante"] = best_var
    return d_res


def _ejecutar_grillas_desc(
    atr_nq: pd.Series,
    orb_nq: pd.Series,
    pv_nq: float,
    start_nq: int,
    *,
    workers: int = 2,
    m1_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, pd.DataFrame]]:
    """Corre B1-B3 estrictamente sobre sesiones A5 == DESC en NQ + diagnostico K55/K56 dual (FULL y POST_2020)."""
    specs = _grillas_bloque_b()
    _precalentar_b13_nq(specs, workers=workers, m1_dir=m1_dir)

    ms_ref = SimpleNamespace(point_value=pv_nq)
    trade_cache: dict[str, pd.DataFrame] = {}
    rows: list[dict[str, Any]] = []
    por_grilla_ops_full: dict[str, list[pd.DataFrame]] = {}
    por_grilla_ops_2020: dict[str, list[pd.DataFrame]] = {}
    por_grilla_perillas: dict[str, dict[str, dict[str, str]]] = {}
    ops_desc_map: dict[str, pd.DataFrame] = {}
    specs_by_var: dict[str, dict[str, Any]] = {s["variante"]: s for s in specs}

    m_desc_full = _meses_activos_a5(start_nq, 20260930, "DESC")
    m_desc_20 = _meses_activos_a5(20200101, 20260930, "DESC")
    m_desc_21 = _meses_activos_a5(20210101, 20260930, "DESC")

    for sp in specs:
        mod = str(sp["modulo"])
        params = dict(sp["params"])
        cname = _cache_key("NQ", mod, params)
        if cname not in trade_cache:
            trade_cache[cname] = _cargar_trades_cacheados(cname)

        ops_full = convertir_trades_a_ops_r(
            trade_cache[cname], mod, "NQ", atr_nq, orb_nq, ms_ref,
            stop_atr_k=sp["stop_atr_k"], cap_mae_atr_k=sp["cap_mae_atr_k"],
        )
        # Firewall estricto HOLDOUT-A5: descubrimiento solo toca DESC
        ops_desc = ops_full[ops_full["a5"] == "DESC"].copy()
        ops_desc_map[sp["variante"]] = ops_desc

        st = resumir_serie_r(ops_desc, meses_totales=m_desc_full)
        ops_20 = ops_desc[ops_desc["fecha_int"] >= 20200101]
        ops_21 = ops_desc[ops_desc["fecha_int"] >= 20210101]
        st20 = resumir_serie_r(ops_20, meses_totales=m_desc_20)
        st21 = resumir_serie_r(ops_21, meses_totales=m_desc_21)

        rows.append({
            "grilla": sp["grilla"],
            "modulo": mod,
            "variante": sp["variante"],
            "params_json": json.dumps(params, sort_keys=True),
            "stop_atr_k": sp["stop_atr_k"],
            "cap_mae_atr_k": sp["cap_mae_atr_k"],
            **st,
            "episodios": _episodios_seguro(ops_desc),
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
            "episodios_2020": _episodios_seguro(ops_20),
            "n_2021": st21["n"],
            "R_neto_2021": st21["R_neto_mini"],
            "R_mes_2021": st21["R_por_mes"],
            "t_ses_2021": st21["t_ses"],
            "p_boot_2021": st21["p_boot"],
        })

        g = str(sp["grilla"])
        por_grilla_ops_full.setdefault(g, [])
        por_grilla_ops_2020.setdefault(g, [])
        if not ops_desc.empty:
            por_grilla_ops_full[g].append(
                ops_desc[["R_neto_mini", "mes"]].rename(columns={"R_neto_mini": "R"}).assign(variante=sp["variante"])
            )
        if not ops_20.empty:
            por_grilla_ops_2020[g].append(
                ops_20[["R_neto_mini", "mes"]].rename(columns={"R_neto_mini": "R"}).assign(variante=sp["variante"])
            )
        por_grilla_perillas.setdefault(g, {})[sp["variante"]] = sp["perillas"]

    diags: dict[str, dict[str, Any]] = {}
    degen_full: set[str] = set()
    degen_2020: set[str] = set()
    for g, dfs in por_grilla_ops_full.items():
        df_g = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        dfs20 = por_grilla_ops_2020[g]
        df_g20 = pd.concat(dfs20, ignore_index=True) if dfs20 else pd.DataFrame()
        pmap = por_grilla_perillas[g]
        pnames = list(next(iter(pmap.values())).keys())
        per_fn = {pn: (lambda v, pn=pn, pmap=pmap: pmap[v][pn]) for pn in pnames}

        d_full = _diagnostico_con_mejor(df_g, per_fn, total_celdas=len(pmap))
        d_20 = _diagnostico_con_mejor(df_g20, per_fn, total_celdas=len(pmap))
        d_full["post_2020"] = d_20
        diags[g] = d_full
        degen_full |= set(d_full.get("degeneradas", []))
        degen_2020 |= set(d_20.get("degeneradas", []))

    df_b = pd.DataFrame(rows)
    df_b["degenerada"] = df_b["variante"].isin(degen_full) | (df_b["n"] < 30)
    df_b["pasa_desc"] = (
        (~df_b["degenerada"])
        & (df_b["n"] >= 30)
        & (df_b["R_neto_mini"] > 0.0)
        & (df_b["p_boot"] < 0.05)
        & (df_b["med_fric_R"] <= 0.12)
    )
    df_b["degenerada_2020"] = df_b["variante"].isin(degen_2020) | (df_b["n_2020"] < 30)
    df_b["pasa_desc_2020"] = (
        (~df_b["degenerada_2020"])
        & (df_b["n_2020"] >= 30)
        & (df_b["R_neto_2020"] > 0.0)
        & (df_b["p_boot_2020"] < 0.05)
        & (df_b["med_fric_R_2020"] <= 0.12)
    )
    df_b.to_csv(OUT_DIR / "bloque_b_variantes_nq_desc.csv", index=False)
    (OUT_DIR / "diagnostico_grillas.json").write_text(json.dumps(diags, indent=2, default=str), encoding="utf-8")
    return df_b, diags, specs_by_var, ops_desc_map


def _seleccionar_finalistas_b4(df_b: pd.DataFrame) -> list[str]:
    """Elige hasta 6 finalistas de modulos distintos en DESC (prioriza FULL_2008, luego POST_2020)."""
    elegidos: list[str] = []
    mods_vistos: set[str] = set()

    if "pasa_desc" in df_b.columns:
        pasan = df_b[df_b["pasa_desc"]].sort_values(["R_por_mes", "t_ses"], ascending=False)
        for _, r in pasan.iterrows():
            m = str(r["modulo"])
            if m not in mods_vistos and len(elegidos) < 6:
                elegidos.append(str(r["variante"]))
                mods_vistos.add(m)

    if "pasa_desc_2020" in df_b.columns and "R_mes_2020" in df_b.columns:
        pasan20 = df_b[df_b["pasa_desc_2020"]].sort_values(["R_mes_2020", "t_ses_2020"], ascending=False)
        for _, r in pasan20.iterrows():
            m = str(r["modulo"])
            if m not in mods_vistos and len(elegidos) < 6:
                elegidos.append(str(r["variante"]))
                mods_vistos.add(m)

    if "V" not in mods_vistos and len(elegidos) < 6:
        col_r = "R_neto_2020" if "R_neto_2020" in df_b.columns else "R_neto_mini"
        col_t = "t_ses_2020" if "t_ses_2020" in df_b.columns else "t_ses"
        v_top = df_b[df_b["modulo"] == "V"].sort_values([col_r, col_t], ascending=False)
        if not v_top.empty:
            elegidos.append(str(v_top.iloc[0]["variante"]))
            mods_vistos.add("V")

    if len(elegidos) < 6 and "R_neto_2020" in df_b.columns:
        mask_deg = df_b["degenerada_2020"] if "degenerada_2020" in df_b.columns else False
        sub_pos = df_b[(df_b["R_neto_2020"] > 0.0) & (~mask_deg)].sort_values(
            ["R_mes_2020", "t_ses_2020"], ascending=False
        )
        for _, r in sub_pos.iterrows():
            m = str(r["modulo"])
            if m not in mods_vistos and len(elegidos) < 6:
                elegidos.append(str(r["variante"]))
                mods_vistos.add(m)
    elif len(elegidos) < 6:
        for m_chk in ("S", "W", "Q"):
            if m_chk not in mods_vistos and len(elegidos) < 6:
                sub = df_b[df_b["modulo"] == m_chk].sort_values(["R_neto_mini", "t_ses"], ascending=False)
                if not sub.empty and float(sub.iloc[0]["R_neto_mini"]) > -0.05:
                    elegidos.append(str(sub.iloc[0]["variante"]))
                    mods_vistos.add(m_chk)
    return elegidos[:6]


def _correlacion_y_aporte_tzr(
    ops_safe: pd.DataFrame,
    tzr_ops: Mapping[str, pd.DataFrame],
) -> dict[str, Any]:
    """Calcula correlacion diaria vs T/Z/R/T+Z+R y aporte R/mes + t_ses en POST_2020 DESC y REP."""
    def _calc_corr(min_fecha: int) -> dict[str, Any]:
        sc_sub = ops_safe[ops_safe["fecha_int"] >= min_fecha]
        s_cand = sc_sub.groupby("fecha_int")["R_neto_mini"].sum()
        corrs: dict[str, float | None] = {}
        tzr_daily: dict[str, pd.Series] = {}
        for bmod in ("T", "Z", "R"):
            op_b = tzr_ops[bmod]
            sb_sub = op_b[op_b["a5"].isin(("DESC", "REP")) & (op_b["fecha_int"] >= min_fecha)]
            s_b = sb_sub.groupby("fecha_int")["R_neto_mini"].sum()
            tzr_daily[bmod] = s_b
            ix = s_cand.index.union(s_b.index)
            x = s_cand.reindex(ix, fill_value=0.0).to_numpy(dtype=float)
            y = s_b.reindex(ix, fill_value=0.0).to_numpy(dtype=float)
            corrs[bmod] = round(float(np.corrcoef(x, y)[0, 1]), 3) if np.std(x) > 0 and np.std(y) > 0 else None
        s_tzr = tzr_daily["T"].add(tzr_daily["Z"], fill_value=0.0).add(tzr_daily["R"], fill_value=0.0)
        ix = s_cand.index.union(s_tzr.index)
        xc = s_cand.reindex(ix, fill_value=0.0).to_numpy(dtype=float)
        yc = s_tzr.reindex(ix, fill_value=0.0).to_numpy(dtype=float)
        corr_c = round(float(np.corrcoef(xc, yc)[0, 1]), 3) if np.std(xc) > 0 and np.std(yc) > 0 else None
        return {"correlacion_vs": corrs, "corr_con_TZR": corr_c}

    aporte: dict[str, Any] = {}
    for part in ("DESC", "REP"):
        m_p20 = _meses_activos_a5(20200101, 20260930, part)
        s_tzr_p = pd.Series(dtype=float)
        r_sum_tzr = 0.0
        for bmod in ("T", "Z", "R"):
            op_b = tzr_ops[bmod]
            sub_b = op_b[(op_b["a5"] == part) & (op_b["fecha_int"] >= 20200101)]
            r_sum_tzr += float(sub_b["R_neto_mini"].sum())
            s_tzr_p = s_tzr_p.add(sub_b.groupby("fecha_int")["R_neto_mini"].sum(), fill_value=0.0)
        sub_c = ops_safe[(ops_safe["a5"] == part) & (ops_safe["fecha_int"] >= 20200101)]
        r_sum_c = float(sub_c["R_neto_mini"].sum())
        s_c_p = sub_c.groupby("fecha_int")["R_neto_mini"].sum()
        s_comb = s_tzr_p.add(s_c_p, fill_value=0.0)
        v_tzr = s_tzr_p.to_numpy(dtype=float)
        v_comb = s_comb.to_numpy(dtype=float)
        t_tzr = float(np.mean(v_tzr) / np.std(v_tzr, ddof=1) * np.sqrt(len(v_tzr))) if len(v_tzr) >= 3 and np.std(v_tzr, ddof=1) > 1e-12 else np.nan
        t_comb = float(np.mean(v_comb) / np.std(v_comb, ddof=1) * np.sqrt(len(v_comb))) if len(v_comb) >= 3 and np.std(v_comb, ddof=1) > 1e-12 else np.nan
        aporte[part] = {
            "tzr_R_mes": round(r_sum_tzr / m_p20, 3),
            "cand_R_mes": round(r_sum_c / m_p20, 3),
            "combo_R_mes": round((r_sum_tzr + r_sum_c) / m_p20, 3),
            "tzr_t_ses": round(t_tzr, 2) if np.isfinite(t_tzr) else None,
            "combo_t_ses": round(t_comb, 2) if np.isfinite(t_comb) else None,
        }

    return {
        "FULL_2008": _calc_corr(20080101),
        "POST_2020": _calc_corr(20200101),
        "aporte_post_2020": aporte,
    }


def _correr_bloque_b4_transfer_rep(
    finalistas: list[str],
    specs_by_var: Mapping[str, Mapping[str, Any]],
    atr_nq: pd.Series,
    orb_nq: pd.Series,
    pv_nq: float,
    start_nq: int,
    ops_a_nq: Mapping[str, pd.DataFrame],
    *,
    workers: int = 2,
    m1_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Evalua finalistas en NQ REP + ES/YM/RTY/EMD (DESC y REP) en FULL_2008 y POST_2020."""
    activos = ("NQ", "ES", "YM", "RTY", "EMD")
    m1_str = str(m1_dir) if m1_dir is not None else None

    # Pre-calentar en paralelo solo los instrumentos externos con jobs aun no cacheados
    tasks_b4: list[tuple[str, list[tuple[str, str, dict[str, Any]]], str | None]] = []
    for inst in activos:
        jobs_i: list[tuple[str, str, dict[str, Any]]] = []
        seen_c: set[str] = set()
        for vname in finalistas:
            sp = specs_by_var[vname]
            mod = str(sp["modulo"])
            params = dict(sp["params"])
            cname = _cache_key(inst, mod, params)
            if cname not in seen_c and not (CACHE_DIR / f"{cname}.pkl").exists():
                seen_c.add(cname)
                jobs_i.append((cname, mod, params))
        if jobs_i:
            tasks_b4.append((inst, jobs_i, m1_str))

    if tasks_b4:
        n_w = min(max(int(workers), 1), len(tasks_b4))
        print(f"[B4] Corriendo transferencia para {len(tasks_b4)} activos con workers={n_w}...", flush=True)
        if n_w == 1:
            for t_arg in tasks_b4:
                for cname, n_tr, dt in _run_instrumento_b4_worker(t_arg):
                    print(f"  [B4 RUN] {cname}: n={n_tr} ({dt:.1f}s)", flush=True)
        else:
            with concurrent.futures.ProcessPoolExecutor(max_workers=n_w) as ex:
                for logs in ex.map(_run_instrumento_b4_worker, tasks_b4):
                    for cname, n_tr, dt in logs:
                        print(f"  [B4 RUN] {cname}: n={n_tr} ({dt:.1f}s)", flush=True)
    else:
        print("[CACHE] Bloque B4 completo en disco.", flush=True)

    rows: list[dict[str, Any]] = []
    corrs_y_aporte: dict[str, Any] = {}
    for inst in activos:
        if inst == "NQ":
            atr_i, orb_i, pv_i, start_i = atr_nq, orb_nq, pv_nq, start_nq
        else:
            atr_i, orb_i, pv_i, start_i = _cargar_series_sesion(inst, m1_dir=m1_dir)
        ms_ref = SimpleNamespace(point_value=pv_i)

        for vname in finalistas:
            sp = specs_by_var[vname]
            mod = str(sp["modulo"])
            params = dict(sp["params"])
            cname = _cache_key(inst, mod, params)
            df_t = _cargar_trades_cacheados(cname)
            ops = convertir_trades_a_ops_r(
                df_t, mod, inst, atr_i, orb_i, ms_ref,
                stop_atr_k=sp["stop_atr_k"], cap_mae_atr_k=sp["cap_mae_atr_k"],
            )
            # Firewall estricto: B4 jamas lee HOLDOUT, EMBARGO o TERMINAL
            ops_safe = ops[ops["a5"].isin(("DESC", "REP"))].copy()
            for part in ("DESC", "REP"):
                sub_full = ops_safe[ops_safe["a5"] == part]
                sub_20 = sub_full[sub_full["fecha_int"] >= 20200101]
                sub_21 = sub_full[sub_full["fecha_int"] >= 20210101]

                st_21 = resumir_serie_r(sub_21, meses_totales=_meses_activos_a5(max(start_i, 20210101), 20260930, part))
                for per_nom, sub_p, s_d0 in (
                    ("FULL_2008", sub_full, start_i),
                    ("POST_2020", sub_20, max(start_i, 20200101)),
                ):
                    st = resumir_serie_r(sub_p, meses_totales=_meses_activos_a5(s_d0, 20260930, part))
                    rows.append({
                        "variante": vname,
                        "modulo": mod,
                        "instrumento": inst,
                        "particion_a5": part,
                        "periodo": per_nom,
                        "spread_estimado": inst == "EMD",
                        **st,
                        "n_2021": st_21["n"],
                        "R_neto_2021": st_21["R_neto_mini"],
                        "R_mes_2021": st_21["R_por_mes"],
                    })

            if inst == "NQ":
                corrs_y_aporte[vname] = _correlacion_y_aporte_tzr(ops_safe, ops_a_nq)

    df_b4 = pd.DataFrame(rows)
    df_b4.to_csv(OUT_DIR / "bloque_b_transfer_y_rep.csv", index=False)
    return df_b4, corrs_y_aporte


def graficar_campana(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    df_b4: pd.DataFrame | None = None,
) -> dict[str, Path]:
    """Genera 2 graficos resumen legibles (Bloque A en R por epoca + Bloque B variantes/transferencia POST_2020)."""
    if plt is None:
        raise RuntimeError("matplotlib requerido para graficar_campana")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rutas: dict[str, Path] = {}

    # 1) Bloque A: R neto medio por regimen (izq) y R/mes POST_2020 (der)
    piv = df_a.pivot(index="modulo", columns="regimen", values="R_neto_mini")
    sort_col = "POST_2020" if "POST_2020" in piv.columns else "VEND_B_HASTA_1SEP"
    order_m = piv[sort_col].fillna(-9).sort_values(ascending=True).index.tolist()
    piv = piv.loc[order_m]

    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7.8), facecolor="#0d1316")
    for ax in (ax1, ax2):
        ax.set_facecolor("#11191c")
        ax.tick_params(colors="#b4c2c8", labelsize=9)
        for sp in ax.spines.values():
            sp.set_color("#29363c")

    y_pos = np.arange(len(order_m))
    h = 0.20
    cols_reg = [
        ("PRE_2020", "#647a87", -1.5 * h),
        ("VEND_A", "#3baeb8", -0.5 * h),
        ("VEND_B_HASTA_1SEP", "#2ca693", +0.5 * h),
        ("POST_1SEP", "#e0a458", +1.5 * h),
    ]
    x_lim_a = 0.90
    for rname, color, off in cols_reg:
        if rname not in piv.columns:
            continue
        vals = piv[rname].fillna(0.0).to_numpy(dtype=float)
        clipped = np.clip(vals, -x_lim_a + 0.02, x_lim_a - 0.02)
        ax1.barh(y_pos + off, clipped, height=h, color=color, label=rname, alpha=0.92)
        for yi, v in enumerate(vals):
            if np.isfinite(v) and abs(v) > x_lim_a - 0.03:
                ax1.text(
                    -x_lim_a + 0.04 if v < 0 else x_lim_a - 0.04,
                    yi + off,
                    f"{v:+.2f}",
                    va="center",
                    ha="left" if v < 0 else "right",
                    color="#f0c954",
                    fontsize=7.2,
                    fontweight="bold",
                )
    ax1.set_xlim(-x_lim_a, x_lim_a)
    ax1.axvline(0.0, color="#9ab0ba", linewidth=0.9, linestyle="--")
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels([f"{m} (Ov)" if m == "O" else m for m in order_m])
    ax1.set_xlabel("R neto medio por operacion (mini NQ)", color="#c8d4da")
    ax1.set_title("Bloque A: Calidad post-IL en R (ordenado por POST_2020)", color="#e6eef2", fontsize=11)
    ax1.legend(loc="lower right", fontsize=8, frameon=True, facecolor="#11191c", edgecolor="#29363c", labelcolor="#dbe4e8")

    reg_der = "POST_2020" if "POST_2020" in df_a["regimen"].values else "TOTAL"
    sub_der = df_a[df_a["regimen"] == reg_der].set_index("modulo").loc[order_m]
    rm_vals = sub_der["R_por_mes"].fillna(0.0).to_numpy(dtype=float)
    pb_vals = sub_der["p_boot"].fillna(1.0).to_numpy(dtype=float)
    c_bars = [
        "#2ca693" if (v > 0 and p < 0.05) else "#587cc9" if v > 0 else "#c47068"
        for v, p in zip(rm_vals, pb_vals)
    ]
    ax2.barh(y_pos, rm_vals, color=c_bars, height=0.58, alpha=0.9)
    span_x = max(float(np.nanmax(rm_vals) - min(float(np.nanmin(rm_vals)), -1.0)), 2.5)
    pad_txt = 0.025 * span_x
    for idx_m, m_name in enumerate(order_m):
        fr_val = sub_der.loc[m_name, "med_fric_R"]
        rm_val = float(sub_der.loc[m_name, "R_por_mes"]) if np.isfinite(sub_der.loc[m_name, "R_por_mes"]) else 0.0
        pb_val = float(sub_der.loc[m_name, "p_boot"]) if np.isfinite(sub_der.loc[m_name, "p_boot"]) else 1.0
        fr_txt = f"{fr_val:.2f}R" if np.isfinite(fr_val) else "—"
        ax2.text(
            max(rm_val, 0.0) + pad_txt,
            idx_m,
            f"{rm_val:+.2f} R/m | fric={fr_txt} | p={pb_val:.3f}",
            va="center", color="#c6d2d8", fontsize=7.8,
        )
    ax2.set_xlim(min(float(np.nanmin(rm_vals)) - 0.12 * span_x, -0.8), max(float(np.nanmax(rm_vals)), 0.5) + 0.58 * span_x)
    ax2.axvline(0.0, color="#9ab0ba", linewidth=0.9, linestyle="--")
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([f"{m} (Ov)" if m == "O" else m for m in order_m])
    ax2.set_xlabel(f"R neto / mes (mini NQ, {reg_der})", color="#c8d4da")
    ax2.set_title(f"Expectativa mensual {reg_der} (2020 -> 2026-08)", color="#e6eef2", fontsize=11)
    fig1.tight_layout()
    p1 = OUT_DIR / "bloque_a_calidad_14_modulos_R.png"
    fig1.savefig(p1, dpi=150, facecolor=fig1.get_facecolor())
    plt.close(fig1)
    rutas["bloque_a"] = p1

    # 2) Bloque B: top variantes NQ DESC POST_2020 y heatmap transferencia B4 POST_2020
    fig2, (bx1, bx2) = plt.subplots(1, 2, figsize=(17.0, 7.2), facecolor="#0d1316")
    for ax in (bx1, bx2):
        ax.set_facecolor("#11191c")
        ax.tick_params(colors="#b4c2c8", labelsize=8.5)
        for sp in ax.spines.values():
            sp.set_color("#29363c")

    use_20 = "R_neto_2020" in df_b.columns and "pasa_desc_2020" in df_b.columns
    r_col = "R_neto_2020" if use_20 else "R_neto_mini"
    n_col = "n_2020" if use_20 else "n"
    ok_col = "pasa_desc_2020" if use_20 else "pasa_desc"
    top_b = df_b[df_b[n_col] >= 30].sort_values(r_col, ascending=True).tail(16)
    yb = np.arange(len(top_b))
    cb = ["#2ca693" if ok else "#587cc9" if r > 0 else "#c47068" for ok, r in zip(top_b[ok_col], top_b[r_col])]
    bx1.barh(yb, top_b[r_col], color=cb, height=0.62, alpha=0.92, label="POST_2020 DESC")
    if use_20 and not top_b.empty:
        r_full = top_b["R_neto_mini"].fillna(0.0).to_numpy(dtype=float)
        x_lo = min(float(top_b[r_col].min()), float(r_full.min()), -0.05) - 0.04
        bx1.scatter(np.maximum(r_full, x_lo + 0.01), yb, marker="D", s=26, color="#f0c954", zorder=4, label="FULL_2008 DESC")
        bx1.set_xlim(x_lo, max(float(top_b[r_col].max()), float(r_full.max()), 0.1) + 0.06)
        bx1.legend(loc="lower right", fontsize=8, frameon=True, facecolor="#11191c", edgecolor="#29363c", labelcolor="#dbe4e8")
    bx1.axvline(0.0, color="#9ab0ba", linewidth=0.9, linestyle="--")
    bx1.set_yticks(yb)
    bx1.set_yticklabels(top_b["variante"])
    bx1.set_xlabel("R neto medio por op (NQ A5 DESC)", color="#c8d4da")
    bx1.set_title("Bloque B: Top variantes en NQ DESC (POST_2020 vs FULL_2008)", color="#e6eef2", fontsize=11)

    if df_b4 is not None and not df_b4.empty:
        piv4 = df_b4[df_b4["particion_a5"].isin(("DESC", "REP"))].copy()
        if "periodo" in piv4.columns and (piv4["periodo"] == "POST_2020").any():
            piv4 = piv4[piv4["periodo"] == "POST_2020"].copy()
        piv4["col"] = piv4["instrumento"] + "_" + piv4["particion_a5"]
        hm = piv4.pivot(index="variante", columns="col", values="R_neto_mini")
        hn = piv4.pivot(index="variante", columns="col", values="n")
        orden_cols = [c for c in ("NQ_DESC", "NQ_REP", "ES_DESC", "ES_REP", "YM_DESC", "YM_REP", "RTY_DESC", "RTY_REP", "EMD_DESC", "EMD_REP") if c in hm.columns]
        if orden_cols:
            hm = hm[orden_cols]
            hn = hn[orden_cols]
        im = bx2.imshow(hm.fillna(0.0).to_numpy(dtype=float), cmap="RdYlGn", vmin=-0.20, vmax=0.35, aspect="auto")
        bx2.set_xticks(np.arange(hm.shape[1]))
        xlabels = [c.replace("EMD_", "EMD*_") for c in hm.columns]
        bx2.set_xticklabels(xlabels, rotation=32, ha="right", fontsize=8)
        bx2.set_yticks(np.arange(hm.shape[0]))
        bx2.set_yticklabels(hm.index, fontsize=8)
        for r_i in range(hm.shape[0]):
            for c_i in range(hm.shape[1]):
                val = hm.iloc[r_i, c_i]
                nv = hn.iloc[r_i, c_i]
                if np.isfinite(val):
                    n_txt = f"n={int(nv)}" if np.isfinite(nv) else ""
                    txt = f"{val:+.2f}\n{n_txt}"
                    txt_col = "#f4f7f8" if (val < -0.09 or val > 0.22) else "#0c1214"
                else:
                    txt, txt_col = "—", "#0c1214"
                bx2.text(c_i, r_i, txt, ha="center", va="center", color=txt_col, fontsize=7.0, fontweight="bold")
        bx2.set_title("B4 POST_2020: Transferencia (DESC) y Confirmacion Congelada (REP)\n(*EMD = spread estimado K33)", color="#e6eef2", fontsize=10.5)
        fig2.colorbar(im, ax=bx2, fraction=0.038, pad=0.03)
    else:
        bx2.set_visible(False)

    fig2.tight_layout()
    p2 = OUT_DIR / "bloque_b_variantes_y_transferencia_A5.png"
    fig2.savefig(p2, dpi=150, facecolor=fig2.get_facecolor())
    plt.close(fig2)
    rutas["bloque_b"] = p2

    if ARTIFACTS_DIR.exists():
        import shutil
        for sp_p in rutas.values():
            shutil.copy2(sp_p, ARTIFACTS_DIR / sp_p.name)
    return rutas


def ejecutar_campana(etapa: str = "todo", m1_dir: Path | None = None, workers: int = 2) -> dict[str, Any]:
    """Orquesta la campana completa respetando compuerta K51, A4 (<2026-10-01) y A5."""
    asegurar_compuerta()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    atr_nq, orb_nq, pv_nq, start_nq = _cargar_series_sesion("NQ", m1_dir=m1_dir)

    df_a: pd.DataFrame | None = None
    ops_a_nq: dict[str, pd.DataFrame] = {}
    if etapa in ("bloque_a", "todo", "bloque_b4"):
        df_a, ops_a_nq = _correr_bloque_a(atr_nq, orb_nq, pv_nq, m1_dir=m1_dir)
        print("\n=== BLOQUE A (PRE_2020 vs POST_2020 vs VEND_B vs POST_1SEP) ===")
        sub_p = df_a[df_a["regimen"].isin(("TOTAL", "PRE_2020", "POST_2020", "POST_2021", "VEND_B_HASTA_1SEP", "POST_1SEP"))]
        print(sub_p.pivot(index="modulo", columns="regimen", values="R_neto_mini").round(4).to_string())

    df_b: pd.DataFrame | None = None
    diags: dict[str, Any] = {}
    specs_by_var = {s["variante"]: s for s in _grillas_bloque_b()}
    if etapa in ("bloque_b13", "todo"):
        df_b, diags, specs_by_var, _ = _ejecutar_grillas_desc(
            atr_nq, orb_nq, pv_nq, start_nq, workers=workers, m1_dir=m1_dir
        )
        print("\n=== BLOQUE B1-B3 TOP POST_2020 (NQ DESC A5) ===")
        cols_p = ["grilla", "variante", "n_2020", "R_neto_2020", "R_mes_2020", "p_boot_2020", "pasa_desc_2020", "n", "R_neto_mini", "pasa_desc"]
        print(df_b.sort_values("R_neto_2020", ascending=False)[cols_p].head(25).to_string(index=False))

    df_b4: pd.DataFrame | None = None
    corrs_b4: dict[str, Any] = {}
    if etapa in ("bloque_b4", "todo"):
        if df_b is None:
            df_b = pd.read_csv(OUT_DIR / "bloque_b_variantes_nq_desc.csv")
            diags = json.loads((OUT_DIR / "diagnostico_grillas.json").read_text(encoding="utf-8"))
        finalistas = _seleccionar_finalistas_b4(df_b)
        print("\n=== FINALISTAS PARA B4 (TRANSFERENCIA + REP) ===", finalistas, flush=True)
        df_b4, corrs_b4 = _correr_bloque_b4_transfer_rep(
            finalistas, specs_by_var, atr_nq, orb_nq, pv_nq, start_nq, ops_a_nq,
            workers=workers, m1_dir=m1_dir,
        )
        print("\n=== BLOQUE B4 POST_2020 ===")
        b4_p20 = df_b4[df_b4["periodo"] == "POST_2020"][["variante", "instrumento", "particion_a5", "n", "R_neto_mini", "R_por_mes", "p_boot", "med_fric_R"]]
        print(b4_p20.to_string(index=False))
        resumen = {
            "finalistas": finalistas,
            "correlaciones_tzr": corrs_b4,
            "diagnosticos": diags,
        }
        (OUT_DIR / "resumen_campana_post_il.json").write_text(json.dumps(resumen, indent=2, default=str), encoding="utf-8")
        if df_a is not None:
            graficar_campana(df_a, df_b, df_b4)

    return {"df_a": df_a, "df_b": df_b, "df_b4": df_b4}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Campana post-IL FUNDEDSYNCSTACK en unidad R y variantes A5.")
    ap.add_argument("etapa", nargs="?", default="todo", choices=("bloque_a", "bloque_b13", "bloque_b4", "todo"))
    ap.add_argument("--workers", type=int, default=2, help="Procesos en paralelo (default 2 para 7.8 GB RAM)")
    args = ap.parse_args(argv)
    ejecutar_campana(etapa=args.etapa, workers=args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

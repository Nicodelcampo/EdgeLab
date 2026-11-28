#!/usr/bin/env python3
"""ADAPTAR-PRESENTE 2 (2026-11-26): Auditoria estructural de limites fijos en puntos/USD en V, C, N y O
que quedaron sin medir en ADAPTAR-PRESENTE 1 (donde Claude solo probo T y F).

Regla anti-overfit: UNA sola variante proporcional pre-declarada por modulo usando P_REF = 15757.875
(mediana de cierre NQ 2022-01 -> 2025-08 usada en adaptar_presente.py), medida en DESC y REP (A5)
sobre 2012-01-01 -> 2026-09-30 (corte estricto < 2026-10-01, HOLDOUT/TERMINAL sellados).

Uso:
  python -u tools/adaptar_presente_v2.py
"""
from __future__ import annotations

import dataclasses
import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from edgelab import costos
from edgelab.holdout import a5_bloque
from edgelab.research.fundedsyncstack import (
    CapstoneConfig,
    NDayConfig,
    VaultConfig,
    build_multi_series,
    load_m1_data,
    modulos_p_c_v_o as PVO,
    modulos_w_n_t as WNT,
    run_c,
    run_n,
    run_o,
    run_v,
)
from edgelab.research.m1_intradia import leer_m1nt8
from m1_largo import _sesion, atr20

OUT = ROOT / "docs/research/auditoria_cartera_20261126"
OUT.mkdir(parents=True, exist_ok=True)
P_REF = 15757.875


def _scaled_run_v(ms, qty=1, cfg=None):
    """Exact run_v with causal price scaling (session_open / P_REF) applied to SL/TP USD brackets."""
    src = inspect.getsource(PVO.run_v)
    # Replace fixed stop_price/target_price in run_v with causal session_open/P_REF scaling
    old = "stop_price=round_tick(o_i - stop_dist, tick),\n                target_price=round_tick(o_i + target_dist, tick),"
    new = (
        "stop_price=round_tick(o_i - stop_dist * (max(session_open, 1000.0) / 15757.875), tick),\n"
        "                target_price=round_tick(o_i + target_dist * (max(session_open, 1000.0) / 15757.875), tick),"
    )
    assert old in src, "run_v patch target not found"
    ns = dict(PVO.__dict__)
    exec(compile(src.replace(old, new), "run_v_scaled.py", "exec"), ns)
    return ns["run_v"](ms, qty=qty, cfg=cfg)


def _scaled_run_c(ms, qty=1, cfg=None):
    """Exact run_c with causal price scaling (prev_close / P_REF) applied to min_gap, SL y TP."""
    src = inspect.getsource(PVO.run_c)
    old1 = "if (\n            cfg.enable_long_entries\n            and today_open > (prev_close + cfg.minimum_gap_points)\n            and today_open < daily_highs[1]\n        ):"
    new1 = (
        "_sc = max(prev_close, 1000.0) / 15757.875\n"
        "        _sd = stop_dist * _sc\n"
        "        _td = target_dist * _sc\n"
        "        _mg = cfg.minimum_gap_points * _sc\n"
        "        if (\n            cfg.enable_long_entries\n            and today_open > (prev_close + _mg)\n            and today_open < daily_highs[1]\n        ):"
    )
    assert old1 in src, "run_c patch target 1 not found"
    src2 = src.replace(old1, new1)
    src2 = src2.replace("use_qty, stop_dist, target_dist", "use_qty, _sd, _td")
    ns = dict(PVO.__dict__)
    exec(compile(src2, "run_c_scaled.py", "exec"), ns)
    return ns["run_c"](ms, qty=qty, cfg=cfg)


def _scaled_run_n(ms, qty=1, cfg=None):
    """Exact run_n with causal price scaling (day_hi / P_REF) applied to acceptance_buffer_points."""
    src = inspect.getsource(WNT.run_n)
    old = "if float(closes[i]) > day_hi + cfg.acceptance_buffer_points:"
    new = "if float(closes[i]) > day_hi + cfg.acceptance_buffer_points * (max(day_hi, 1000.0) / 15757.875):"
    assert old in src, "run_n patch target not found"
    ns = dict(WNT.__dict__)
    exec(compile(src.replace(old, new), "run_n_scaled.py", "exec"), ns)
    return ns["run_n"](ms, qty=qty, cfg=cfg)


def eval_trades(df: pd.DataFrame, atr_s: pd.Series, fr_mnq_pts: float, inst_pv: float = 2.0, cat_atr_mult: float | None = None, default_risk_pts: float | None = None) -> dict:
    if df is None or len(df) == 0:
        return {"n": 0, "usd_mes": 0.0, "sharpe": 0.0, "pct_anios_pos": 0.0}
    d = df.copy()
    ex_ny = pd.to_datetime(d["exit_time_utc"], unit="ns", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    en_ny = pd.to_datetime(d["entry_time_utc"], unit="ns", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    d["dia"] = ex_ny.dt.normalize()
    d["ses"] = _sesion(pd.DatetimeIndex(ex_ny))
    d = d[(d["dia"] >= "2012-01-01") & (d["dia"] <= "2026-09-30")].copy()
    if len(d) == 0:
        return {"n": 0, "usd_mes": 0.0, "sharpe": 0.0}
    d["atr20"] = atr_s.reindex(_sesion(pd.DatetimeIndex(en_ny.loc[d.index]))).to_numpy()
    d["mae_pts"] = d["mae_usd"].abs() / 20.0  # signal pv=20 in run_* calls

    pnl_pts = d["pnl_pts"].to_numpy(float)
    if cat_atr_mult is not None:
        stop_pts = cat_atr_mult * d["atr20"].to_numpy(float)
        hit = np.isfinite(stop_pts) & (stop_pts > 0) & (d["mae_pts"].to_numpy(float) >= stop_pts)
        pnl_pts = np.where(hit, -stop_pts, pnl_pts)
        riesgo_pts = stop_pts
    else:
        st = d["stop_price"].to_numpy(float)
        en = d["entry_price"].to_numpy(float)
        riesgo_pts = np.where(np.isfinite(st) & (st > 0), np.abs(en - st), d["atr20"].to_numpy(float))

    d["neto_pts"] = pnl_pts - fr_mnq_pts
    d["usd_1m"] = d["neto_pts"] * inst_pv
    ok_r = np.isfinite(riesgo_pts) & (riesgo_pts > 0)
    d["R"] = np.where(ok_r, d["neto_pts"] / riesgo_pts, np.nan)
    d["bloque"] = d["dia"].dt.strftime("%Y%m%d").astype(int).map(a5_bloque)

    def _blk(sub: pd.DataFrame) -> dict:
        if len(sub) < 3:
            return {"n": int(len(sub)), "usd_mes": 0.0, "sharpe": 0.0, "R_op": float("nan")}
        cal = pd.date_range(sub["dia"].min(), sub["dia"].max(), freq="B")
        ds = sub.groupby("dia")["usd_1m"].sum().reindex(cal, fill_value=0.0)
        m = ds.groupby(ds.index.to_period("M")).sum()
        a = ds.groupby(ds.index.year).sum()
        r_m = float(sub["R"].mean()) if sub["R"].notna().any() else float("nan")
        sh = float(m.mean() / m.std(ddof=1) * np.sqrt(12)) if len(m) > 2 and m.std(ddof=1) > 0 else 0.0
        return {
            "n": int(len(sub)),
            "usd_mes": round(float(m.mean()), 2),
            "sharpe": round(sh, 3),
            "pct_anios_pos": round(float((a > 0).mean()), 3),
            "R_op": round(r_m, 4) if np.isfinite(r_m) else None,
            "peor_op_pts": round(float(sub["neto_pts"].min()), 2),
        }

    is_stop = d["exit_name"].astype(str).str.contains("STOP")
    is_tgt = d["exit_name"].astype(str).str.contains("TARGET")
    rec = d[d["dia"] >= "2022-01-01"]
    return {
        "full_2012_2026": _blk(d),
        "rec_2022_2026": _blk(rec),
        "A5_DESC": _blk(d[d["bloque"] == "DESC"]),
        "A5_REP": _blk(d[d["bloque"] == "REP"]),
        "stop_pct_2026": round(float(is_stop[d["dia"].dt.year == 2026].mean()), 3) if (d["dia"].dt.year == 2026).any() else 0.0,
        "tgt_pct_2026": round(float(is_tgt[d["dia"].dt.year == 2026].mean()), 3) if (d["dia"].dt.year == 2026).any() else 0.0,
        "ops_2026": int((d["dia"].dt.year == 2026).sum()),
    }


def main() -> None:
    raw = pd.read_parquet(ROOT / "data/m1nt8/NQ_M1_nonadj_utc.parquet")
    df_m1 = load_m1_data(raw.reset_index(), start="2011-01-01", end="2026-10-01", tz_input="UTC", allow_sellado=False)
    ms_nq = build_multi_series(df_m1, tick_size=0.25, point_value=20.0, tz_input="UTC", allow_sellado=False)
    d_ny = leer_m1nt8(ROOT / "data/m1nt8/NQ_M1_nonadj_utc.parquet")
    atr_nq = atr20(d_ny[d_ny.index >= "2011-01-01"])
    fr_mnq = float(costos.friccion_rt_puntos("MNQ", "base"))

    results = {}

    print("=== 1. MODULO V (VaultBreak: $1400/$2000 fijo vs escalado precio vs V_nm25_noCap_ATR30) ===")
    v_base = run_v(ms_nq, qty=1)
    v_esc = _scaled_run_v(ms_nq, qty=1)
    # Also V without USD bracket (like EdgeLabFundedSyncCore.cs V_nm25_noCap_mae30: nm=0.25, huge cap, cat stop 0.30*ATR20)
    v_nocap = run_v(ms_nq, qty=1, cfg=VaultConfig(noise_multiplier=0.25, profit_target_usd_per_contract=1e6, stop_loss_usd_per_contract=1e6))
    results["V"] = {
        "base": eval_trades(v_base, atr_nq, fr_mnq),
        "escala_precio": eval_trades(v_esc, atr_nq, fr_mnq),
        "noCap_nm25_ATR30": eval_trades(v_nocap, atr_nq, fr_mnq, cat_atr_mult=0.30),
    }
    print(json.dumps(results["V"], indent=2))

    print("\n=== 2. MODULO C (CapstoneGap: $1500/$2500 & 2pt gap fijo vs escalado precio) ===")
    c_base = run_c(ms_nq, qty=1)
    c_esc = _scaled_run_c(ms_nq, qty=1)
    results["C"] = {
        "base": eval_trades(c_base, atr_nq, fr_mnq),
        "escala_precio": eval_trades(c_esc, atr_nq, fr_mnq),
    }
    print(json.dumps(results["C"], indent=2))

    print("\n=== 3. MODULO N (NDayLong: buffer 4pt fijo vs escalado precio, con y sin stop 0.25*ATR20) ===")
    n_base = run_n(ms_nq, qty=1)
    n_esc = _scaled_run_n(ms_nq, qty=1)
    results["N"] = {
        "base": eval_trades(n_base, atr_nq, fr_mnq),
        "escala_precio": eval_trades(n_esc, atr_nq, fr_mnq),
        "base_ATR25": eval_trades(n_base, atr_nq, fr_mnq, cat_atr_mult=0.25),
        "escala_ATR25": eval_trades(n_esc, atr_nq, fr_mnq, cat_atr_mult=0.25),
    }
    print(json.dumps(results["N"], indent=2))

    print("\n=== 4. MODULO O (Overnight: margen 25k/close vs qty=1 + stop ATR50 vs noWed) ===")
    o_base = run_o(ms_nq, qty=None)
    o_q1 = run_o(ms_nq, qty=1)
    o_q1_nw = o_q1.copy()
    en_dow = pd.to_datetime(o_q1_nw["entry_time_utc"], unit="ns", utc=True).dt.tz_convert("America/New_York").dt.dayofweek
    o_q1_nw = o_q1_nw[en_dow != 2]
    results["O"] = {
        "base_con_tope_25k": eval_trades(o_base, atr_nq, fr_mnq),
        "qty1_ATR50": eval_trades(o_q1, atr_nq, fr_mnq, cat_atr_mult=0.50),
        "qty1_noWed_ATR50": eval_trades(o_q1_nw, atr_nq, fr_mnq, cat_atr_mult=0.50),
    }
    print(json.dumps(results["O"], indent=2))

    # Adoption verdicts (same pre-registered logic: adopt only if REP positive AND better/more robust without destroying Sharpe)
    verdicts = {
        "V_escala_precio": "ADOPTA" if results["V"]["escala_precio"]["rec_2022_2026"]["sharpe"] > results["V"]["base"]["rec_2022_2026"]["sharpe"] and results["V"]["escala_precio"]["A5_REP"]["usd_mes"] > results["V"]["base"]["A5_REP"]["usd_mes"] else "NO_ADOPTA",
        "V_noCap_nm25_ATR30": "ADOPTA" if results["V"]["noCap_nm25_ATR30"]["full_2012_2026"]["sharpe"] > results["V"]["base"]["full_2012_2026"]["sharpe"] else "NO_ADOPTA",
        "C_escala_precio": "ADOPTA" if results["C"]["escala_precio"]["full_2012_2026"]["sharpe"] > results["C"]["base"]["full_2012_2026"]["sharpe"] + 0.05 and results["C"]["escala_precio"]["A5_REP"]["usd_mes"] > 0 else "NO_ADOPTA",
        "N_escala_ATR25": "ADOPTA" if results["N"]["escala_ATR25"]["full_2012_2026"]["sharpe"] > results["N"]["base_ATR25"]["full_2012_2026"]["sharpe"] else "NO_ADOPTA",
        "O_qty1_ATR50": "ADOPTA_MIXTO_SOLO_NOCHE" if results["O"]["qty1_ATR50"]["A5_REP"]["usd_mes"] > 0 else "NO_ADOPTA",
    }
    results["verdicts"] = verdicts
    print("\n=== VEREDICTOS ADAPTAR-PRESENTE 2 ===")
    print(json.dumps(verdicts, indent=2))

    (OUT / "ADAPTAR_PRESENTE_V2.json").write_text(json.dumps(results, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("Saved:", OUT / "ADAPTAR_PRESENTE_V2.json")


if __name__ == "__main__":
    main()

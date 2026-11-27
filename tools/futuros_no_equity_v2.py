#!/usr/bin/env python3
"""FUTUROS-NO-EQUITY v2 (2026-11-27): 22 futuros continuos reales de 5 clases balanceadas (Energia, Metales,
Agricolas/Softs, Tasas/Bonos, Divisas) en 4 mecanismos ortogonales (2005 -> 2026-09-30, < 2026-10-01).

Evaluacion ESTRICTA por bloques A5 DESC y REP, dejando HOLDOUT A5, EMBARGO y TERMINAL sellados (NaN).
Uso:
  python -u tools/futuros_no_equity_v2.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from math import erf, sqrt
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edgelab.holdout import a5_bloque  # noqa: E402

DATA = ROOT / "data" / "futuros_no_equity_v2"
DATA.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "docs" / "research" / "auditoria_claude_20261127"
OUT.mkdir(parents=True, exist_ok=True)

CORTE = pd.Timestamp("2026-10-01")
FUTURES_MAP = {
    "CL=F": ("energia", "WTI_Crude"),
    "HO=F": ("energia", "Heating_Oil"),
    "RB=F": ("energia", "RBOB_Gas"),
    "NG=F": ("energia", "Nat_Gas"),
    "GC=F": ("metales", "Gold"),
    "SI=F": ("metales", "Silver"),
    "HG=F": ("metales", "Copper"),
    "PL=F": ("metales", "Platinum"),
    "ZC=F": ("agricolas", "Corn"),
    "ZS=F": ("agricolas", "Soybeans"),
    "ZW=F": ("agricolas", "Wheat"),
    "SB=F": ("agricolas", "Sugar"),
    "KC=F": ("agricolas", "Coffee"),
    "CC=F": ("agricolas", "Cocoa"),
    "ZB=F": ("tasas", "US_30Y_Bond"),
    "ZN=F": ("tasas", "US_10Y_Note"),
    "ZF=F": ("tasas", "US_5Y_Note"),
    "6E=F": ("divisas", "EUR_FX"),
    "6J=F": ("divisas", "JPY_FX"),
    "6B=F": ("divisas", "GBP_FX"),
    "6A=F": ("divisas", "AUD_FX"),
    "6C=F": ("divisas", "CAD_FX"),
}
UA = {"User-Agent": "Mozilla/5.0"}


def fetch_yahoo_ohlc(ticker: str) -> tuple[pd.DataFrame | None, dict]:
    safe_name = ticker.replace("=", "_")
    pq = DATA / f"{safe_name}.parquet"
    if pq.exists():
        df = pd.read_parquet(pq)
        if len(df) and df.index.max() < CORTE:
            return df, {"desde": str(df.index[0].date()), "hasta": str(df.index[-1].date()), "n": len(df), "cached": True}

    p1 = int(pd.Timestamp("2004-01-01").timestamp())
    p2 = int(CORTE.timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={p1}&period2={p2}&interval=1d"
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
        j = json.loads(raw)["chart"]["result"][0]
        ts = pd.to_datetime(j["timestamp"], unit="s", utc=True).tz_convert("America/New_York").tz_localize(None).normalize()
        q = j["indicators"]["quote"][0]
        df = pd.DataFrame({"open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"]}, index=ts).dropna()
        df = df[~df.index.duplicated(keep="last")].sort_index()
        df = df[(df.index < CORTE) & (df["close"] > 0) & (df["open"] > 0)]
        df.to_parquet(pq)
        meta = {"desde": str(df.index[0].date()), "hasta": str(df.index[-1].date()), "n": len(df), "sha256": hashlib.sha256(raw).hexdigest()}
        return df, meta
    except Exception as e:
        return None, {"error": str(e)}


def stats_serie(x: pd.Series) -> dict:
    x = x.dropna()
    m = x.groupby(x.index.to_period("M")).sum()
    n = len(m)
    if n < 3:
        return {"usd_mes": 0.0, "t_mes": 0.0, "p_una_cola": 0.5, "sharpe": 0.0, "pct_meses_pos": 0.0, "pct_anios_pos": 0.0, "caida_max": 0.0, "meses": n}
    mu = float(m.mean())
    sd = float(m.std(ddof=1))
    t = mu / (sd / np.sqrt(n)) if sd > 0 else 0.0
    sh = mu / sd * np.sqrt(12) if sd > 0 else 0.0
    a = x.groupby(x.index.year).sum()
    eq = x.cumsum()
    return {
        "usd_mes": round(mu, 1),
        "t_mes": round(t, 2),
        "p_una_cola": round(0.5 * (1.0 - erf(t / sqrt(2.0))), 4),
        "sharpe": round(sh, 2),
        "pct_meses_pos": round(float((m > 0).mean()), 2),
        "pct_anios_pos": round(float((a > 0).mean()), 2),
        "caida_max": round(float((eq - eq.cummax()).min()), 0),
        "meses": int(n),
    }


def _pnl(C: pd.DataFrame, pos_w: pd.DataFrame, cost_rt: float, cap: float = 10_000.0) -> tuple[pd.Series, float]:
    w = pos_w.shift(1).fillna(0.0)
    dw = (w - w.shift(1).fillna(0.0)).abs()
    r = C.pct_change(fill_method=None).fillna(0.0)
    # Clip extreme single-day roll glitches (>35%) conservatively so bad Yahoo prints don't manufacture fake Sharpe
    r = r.clip(-0.35, 0.35)
    pnl_bar = (w * r - dw * (cost_rt * 0.5)).sum(axis=1) * cap
    turn_m = float(dw.to_numpy().sum() * 0.5) / max(1.0, len(C) / 21.0)
    return pnl_bar, round(turn_m, 2)


def _donchian_atr(C: np.ndarray, H: np.ndarray, L: np.ndarray, atr: np.ndarray, n_en: int = 55, n_ex: int = 20, st_mult: float = 2.0) -> np.ndarray:
    p = np.zeros(len(C))
    st, stop = 0.0, 0.0
    for i in range(n_en + 2, len(C)):
        a = atr[i - 1]
        if not np.isfinite(C[i]) or not np.isfinite(a) or a <= 0:
            st = 0.0
            continue
        hi_en = np.nanmax(H[i - n_en : i])
        lo_en = np.nanmin(L[i - n_en : i])
        hi_ex = np.nanmax(H[i - n_ex : i])
        lo_ex = np.nanmin(L[i - n_ex : i])
        if st > 0.0:
            if L[i] <= stop or C[i] < lo_ex:
                st = 0.0
        elif st < 0.0:
            if H[i] >= stop or C[i] > hi_ex:
                st = 0.0
        if st == 0.0:
            if C[i] > hi_en:
                st, stop = 1.0, C[i] - st_mult * a
            elif C[i] < lo_en:
                st, stop = -1.0, C[i] + st_mult * a
        p[i] = st
    return p


def _volcomp_atr(C: np.ndarray, H: np.ndarray, L: np.ndarray, a10: np.ndarray, a60: np.ndarray, a20: np.ndarray) -> np.ndarray:
    p = np.zeros(len(C))
    st, stop = 0.0, 0.0
    for i in range(65, len(C)):
        if not np.isfinite(C[i]) or not np.isfinite(a20[i - 1]) or a20[i - 1] <= 0 or not np.isfinite(a60[i - 1]) or a60[i - 1] <= 0:
            st = 0.0
            continue
        if st > 0.0:
            stop = max(stop, C[i] - 2.0 * a20[i - 1])
            if L[i] <= stop:
                st = 0.0
        elif st < 0.0:
            stop = min(stop, C[i] + 2.0 * a20[i - 1])
            if H[i] >= stop:
                st = 0.0
        if st == 0.0 and (a10[i - 1] / a60[i - 1]) < 0.80:
            hi20 = np.nanmax(H[i - 20 : i])
            lo20 = np.nanmin(L[i - 20 : i])
            if C[i] > hi20:
                st, stop = 1.0, C[i] - 2.0 * a20[i - 1]
            elif C[i] < lo20:
                st, stop = -1.0, C[i] + 2.0 * a20[i - 1]
        p[i] = st
    return p


def main() -> None:
    print("=== FUTUROS-NO-EQUITY v2: Descarga 22 futuros continuos (< 2026-10-01) ===", flush=True)
    data: Dict[str, pd.DataFrame] = {}
    proc = {}
    for tk, (cls, desc) in FUTURES_MAP.items():
        df, meta = fetch_yahoo_ohlc(tk)
        if df is not None and len(df) >= 1500:
            data[tk] = df
            proc[tk] = {**meta, "clase": cls, "desc": desc}
        else:
            proc[tk] = {**meta, "clase": cls, "desc": desc, "dropped": True}
    (DATA / "PROCEDENCIA.json").write_text(json.dumps(proc, indent=1), encoding="utf-8")
    print(f"Cargados {len(data)}/{len(FUTURES_MAP)} futuros continuos", flush=True)

    C = pd.DataFrame({s: df["close"] for s, df in data.items()}).sort_index()
    H = pd.DataFrame({s: df["high"] for s, df in data.items()}).reindex(C.index)
    L = pd.DataFrame({s: df["low"] for s, df in data.items()}).reindex(C.index)
    C = C[C.index < CORTE]
    H, L = H.reindex(C.index), L.reindex(C.index)

    # Sanity parity check vs local GC and WTI M1
    parity = {}
    try:
        from edgelab.research.m1_intradia import leer_m1, leer_m1nt8
        gc_m1 = leer_m1nt8(ROOT / "data/m1nt8/GC_M1_nonadj_utc.parquet")
        gc_d = gc_m1["c"].groupby(gc_m1.index.normalize()).last().pct_change().dropna()
        gcf_d = C["GC=F"].pct_change().dropna()
        com = gc_d.index.intersection(gcf_d.index)
        parity["corr_GC_M1NT8_vs_GCF"] = round(float(gc_d.loc[com].corr(gcf_d.loc[com])), 4)
        wti_m1 = leer_m1(ROOT / "data/m1dk/LIGHTCMDUSD-M1-.csv")
        wti_d = wti_m1["c"].groupby(wti_m1.index.normalize()).last().pct_change().dropna()
        clf_d = C["CL=F"].pct_change().dropna()
        com2 = wti_d.index.intersection(clf_d.index)
        parity["corr_WTI_M1DK_vs_CLF"] = round(float(wti_d.loc[com2].corr(clf_d.loc[com2])), 4)
        print("Paridad diaria vs M1 local:", parity, flush=True)
    except Exception as e:
        parity["err"] = str(e)

    # Balanced class risk budget: 20% per class divided by active symbols in that class on date t!
    r1 = C.pct_change(fill_method=None).clip(-0.35, 0.35)
    vol63 = (r1.rolling(63, min_periods=25).std() * np.sqrt(252)).clip(lower=0.04)
    # Target 12% annualized vol across 5 classes -> 2.4% class vol budget -> inv-vol scaled per active member in class
    tr = np.maximum(H - L, np.maximum((H - C.shift(1)).abs(), (L - C.shift(1)).abs()))
    atr10 = tr.rolling(10, min_periods=5).mean()
    atr20 = tr.rolling(20, min_periods=10).mean()
    atr60 = tr.rolling(60, min_periods=25).mean()

    class_budget = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    for cls_name in sorted({v[0] for v in FUTURES_MAP.values()}):
        cols_c = [s for s in C.columns if FUTURES_MAP[s][0] == cls_name]
        n_act = C[cols_c].notna().sum(axis=1).replace(0, np.nan)
        for s in cols_c:
            # Target annual vol 0.12 -> total class share 0.20 * (0.12 / vol63) / n_act
            class_budget[s] = (0.20 * (0.12 / vol63[s]) / n_act).clip(upper=0.25).fillna(0.0)

    # M1: FUT_TSMOM_MultiH (21d + 63d + 126d + 252d sign blend, threshold rebalance |dw| > 0.20*|w|)
    s_ts = (
        np.sign(C.pct_change(21, fill_method=None).fillna(0.0))
        + np.sign(C.pct_change(63, fill_method=None).fillna(0.0))
        + np.sign(C.pct_change(126, fill_method=None).fillna(0.0))
        + np.sign(C.pct_change(252, fill_method=None).fillna(0.0))
    ) / 4.0
    w_ts_raw = s_ts * class_budget
    w_ts = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    for s in C.columns:
        arr = w_ts_raw[s].to_numpy()
        out_a = np.zeros(len(arr))
        cur = 0.0
        for i in range(len(arr)):
            tgt = arr[i]
            if not np.isfinite(tgt) or tgt == 0.0:
                cur = 0.0
            elif abs(tgt - cur) > 0.20 * max(abs(cur), 0.01):
                cur = tgt
            out_a[i] = cur
        w_ts[s] = out_a

    # M2: FUT_Donchian_55_20 (with 2*ATR20 stop)
    pos_don = pd.DataFrame({s: _donchian_atr(C[s].to_numpy(), H[s].to_numpy(), L[s].to_numpy(), atr20[s].to_numpy()) for s in C.columns}, index=C.index)
    w_don = pos_don * class_budget

    # M3: FUT_XSMOM_Neutral (63d vol-adj momentum, long top-4 / short bot-4 active-leg risk-balanced, rebalance 10d)
    sc63 = C.pct_change(63, fill_method=None) / vol63
    rk63 = sc63.rank(axis=1, ascending=False, method="first")
    n63 = sc63.notna().sum(axis=1).to_numpy()[:, None]
    pos_xs = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    pos_xs[(rk63 <= 4) & (n63 >= 10)] = 1.0
    pos_xs[(rk63 >= n63 - 3) & (n63 >= 10)] = -1.0
    pos_xs = pos_xs.iloc[::10].reindex(C.index).ffill().fillna(0.0)
    lw = (pos_xs.clip(lower=0.0) * (0.12 / vol63)).clip(upper=0.25)
    sw = ((-pos_xs).clip(lower=0.0) * (0.12 / vol63)).clip(upper=0.25)
    both = (lw.sum(axis=1) > 0) & (sw.sum(axis=1) > 0)
    w_xs = lw.div(lw.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0) * 0.5 - sw.div(sw.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0) * 0.5
    w_xs[~both] = 0.0

    # M4: FUT_VolComp_Break (ATR10/ATR60 < 0.80 -> 20d breakout + 2*ATR20 trail)
    pos_vc = pd.DataFrame({s: _volcomp_atr(C[s].to_numpy(), H[s].to_numpy(), L[s].to_numpy(), atr10[s].to_numpy(), atr60[s].to_numpy(), atr20[s].to_numpy()) for s in C.columns}, index=C.index)
    w_vc = pos_vc * class_budget

    w_map = {
        "FUT_TSMOM_MultiH": w_ts,
        "FUT_Donchian_55_20": w_don,
        "FUT_XSMOM_Neutral": w_xs,
        "FUT_VolComp_Break": w_vc,
    }

    idx_eval = C.index[(C.index >= "2006-01-01") & (C.index < CORTE)]
    blq = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in idx_eval], index=idx_eval)
    assert not blq.isin(["TERMINAL"]).any(), "TERMINAL breach!"
    mask_dr = blq.isin(["DESC", "REP"])

    res = {
        "status": "INVALIDADO_POR_ROLL_NO_AJUSTADO_YAHOO",
        "data_quality_note": "Yahoo =F son empalmes crudos sin back-adjustment (ej. NG=F 208 dias >8%, CL=F 78 dias >8%; paridad M1 solo 0.76). No sirve ni para aprobar ni para refutar futuros no-equity.",
        "roll_glitch_audit": {
            tk: {
                "gt_8pct_days": int((df["close"].pct_change().dropna().abs() > 0.08).sum()),
                "gt_15pct_days": int((df["close"].pct_change().dropna().abs() > 0.15).sum()),
                "max_abs_ret": round(float(df["close"].pct_change().dropna().abs().max()), 3),
            }
            for tk, df in sorted(data.items())
        },
        "n_futures_loaded": len(data),
        "parity_vs_local_m1": parity,
        "rules": {},
    }
    base_df = pd.DataFrame(index=idx_eval)

    print("\n=== FUTUROS-NO-EQUITY v2 (10 bps RT base, 20 bps adverso, SOLO DESC & REP; HOLDOUT SELLADO) ===")
    for name, W in w_map.items():
        res["rules"][name] = {}
        for bps in (10, 20):
            s_raw, turn_m = _pnl(C, W, bps / 10_000.0)
            s = s_raw.reindex(idx_eval).fillna(0.0)
            if bps == 10:
                base_df[name] = s
                res["rules"][name]["turnover_x_mes"] = turn_m
            res["rules"][name][f"bps_{bps}"] = {
                "DESC": stats_serie(s[blq == "DESC"]),
                "REP": stats_serie(s[blq == "REP"]),
                "DESC_REP": stats_serie(s[mask_dr]),
                "DESC_REP_19_26": stats_serie(s[mask_dr & (idx_eval >= "2019-07-01")]),
            }
        b10 = res["rules"][name]["bps_10"]
        print(
            f"  {name:20s} | turn={res['rules'][name]['turnover_x_mes']:4.1f}x | "
            f"DESC Sh={b10['DESC']['sharpe']:4.2f} t={b10['DESC']['t_mes']:4.2f} | "
            f"REP Sh={b10['REP']['sharpe']:4.2f} t={b10['REP']['t_mes']:4.2f} | "
            f"DR Sh={b10['DESC_REP']['sharpe']:4.2f} t={b10['DESC_REP']['t_mes']:4.2f} | "
            f"19-26 Sh={b10['DESC_REP_19_26']['sharpe']:4.2f}"
        )

    # Contribution by asset class for FUT_TSMOM_MultiH in DESC+REP
    cls_contrib = {}
    w_lag = w_ts.shift(1).fillna(0.0)
    dw_lag = (w_lag - w_lag.shift(1).fillna(0.0)).abs()
    pnl_asset = ((w_lag * r1 - dw_lag * 0.0005) * 10_000.0).reindex(idx_eval).fillna(0.0)
    for cls_name in sorted({v[0] for v in FUTURES_MAP.values()}):
        cols_c = [s for s in C.columns if FUTURES_MAP[s][0] == cls_name]
        s_cls = pnl_asset[cols_c].sum(axis=1)
        cls_contrib[cls_name] = stats_serie(s_cls[mask_dr])
    res["TSMOM_by_class_DESC_REP"] = cls_contrib

    # Build 1/sd basket fit STRICTLY on DESC over positive DESC rules
    alive_desc = [c for c in w_map if res["rules"][c]["bps_10"]["DESC"]["usd_mes"] > 0]
    if not alive_desc:
        alive_desc = list(w_map.keys())
    m_desc = base_df.loc[blq == "DESC", alive_desc].groupby(base_df.loc[blq == "DESC"].index.to_period("M")).sum()
    sd_d = m_desc.std(ddof=1).replace(0.0, np.nan).fillna(1.0)
    w_b = (1.0 / sd_d) / (1.0 / sd_d).sum()
    bask = (base_df[alive_desc] * w_b).sum(axis=1)
    base_df["FUT_Canasta_InvVol"] = bask

    save_dr = base_df.copy()
    save_dr.loc[~mask_dr] = np.nan
    save_dr.to_csv(OUT / "SERIES_FUTUROS_NO_EQUITY_V2_DR.csv.gz")

    res["basket_alive_DESC"] = alive_desc
    res["basket_weights_DESC"] = {k: round(float(v), 4) for k, v in w_b.items()}
    res["FUT_Canasta_InvVol"] = {
        "DESC": stats_serie(bask[blq == "DESC"]),
        "REP": stats_serie(bask[blq == "REP"]),
        "DESC_REP": stats_serie(bask[mask_dr]),
        "DESC_REP_19_26": stats_serie(bask[mask_dr & (idx_eval >= "2019-07-01")]),
    }
    print("\n=== CANASTA FUTUROS NO-EQUITY v2 (pesos 1/sd DESC) ===")
    print("  Vivas DESC:", alive_desc, "pesos:", res["basket_weights_DESC"])
    print("  Canasta:", res["FUT_Canasta_InvVol"])
    print("  TSMOM por clase (DESC+REP):", {k: v["sharpe"] for k, v in cls_contrib.items()})

    (OUT / "FUTUROS_NO_EQUITY_V2.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("Saved:", OUT / "FUTUROS_NO_EQUITY_V2.json")


if __name__ == "__main__":
    main()

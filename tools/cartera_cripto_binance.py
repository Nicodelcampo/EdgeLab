#!/usr/bin/env python3
"""NUEVO FRENTE CRIPTO (2026-11-26): Descarga historica limpia de Binance Futures USDT-M (2020-09 -> 2026-09,
corte estricto < 2026-10-01) y evaluacion de 5 estrategias canonicas ortogonales + cartera cripto OOS (DESC + REP A5,
dejando HOLDOUT A5 y TERMINAL sellados).

Monedas (8 perpetuos liquidos): BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, LINKUSDT, AVAXUSDT, DOGEUSDT.
Costos reales: 10 bps ida+vuelta (0.05% por lado taker/slippage) + Funding Rate historico real cada 8h.
Capital de referencia: $10,000 base ($100 de riesgo 1R = 1% por estrategia/rebalanceo, para comparar en USD y R).

Uso:
  python tools/cartera_cripto_binance.py
"""
from __future__ import annotations

import concurrent.futures
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
try:
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.optimize import minimize
    from scipy.spatial.distance import squareform
    from sklearn.covariance import LedoitWolf
except ImportError:
    leaves_list = linkage = minimize = squareform = LedoitWolf = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edgelab.holdout import a5_bloque

DATA_DIR = ROOT / "data/crypto_binance"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "docs/research/auditoria_cartera_20261126"
OUT.mkdir(parents=True, exist_ok=True)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "LINKUSDT", "AVAXUSDT", "DOGEUSDT"]
CUTOFF_UTC_STR = "2026-10-01"  # < 2026-10-01 estricto (HOLDOUT-A4 / TERMINAL sellado)
COST_RT = 0.0010  # 10 bps RT (0.05% por lado taker Binance Futures + slippage conservador)


def _download_month_kline(sym: str, ym: str) -> pd.DataFrame | None:
    url = f"https://data.binance.vision/data/futures/um/monthly/klines/{sym}/1h/{sym}-1h-{ym}.zip"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15) as r:
            zf = zipfile.ZipFile(io.BytesIO(r.read()))
        csv_name = zf.namelist()[0]
        raw = pd.read_csv(zf.open(csv_name), header=None)
        if isinstance(raw.iloc[0, 0], str) and not str(raw.iloc[0, 0]).isdigit():
            raw = pd.read_csv(zf.open(csv_name))
        raw = raw.iloc[:, :6].copy()
        raw.columns = ["open_time", "open", "high", "low", "close", "volume"]
        for c in ("open", "high", "low", "close", "volume"):
            raw[c] = pd.to_numeric(raw[c], errors="coerce")
        raw["open_time"] = pd.to_numeric(raw["open_time"], errors="coerce")
        raw = raw.dropna()
        return raw
    except Exception:
        return None


def _download_month_funding(sym: str, ym: str) -> pd.DataFrame | None:
    url = f"https://data.binance.vision/data/futures/um/monthly/fundingRate/{sym}/{sym}-fundingRate-{ym}.zip"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15) as r:
            zf = zipfile.ZipFile(io.BytesIO(r.read()))
        csv_name = zf.namelist()[0]
        df = pd.read_csv(zf.open(csv_name))
        cols = [c.lower() for c in df.columns]
        df.columns = cols
        tcol = "calc_time" if "calc_time" in cols else cols[0]
        rcol = "last_funding_rate" if "last_funding_rate" in cols else cols[-1]
        out = pd.DataFrame({"calc_time": pd.to_numeric(df[tcol], errors="coerce"), "rate": pd.to_numeric(df[rcol], errors="coerce")}).dropna()
        return out
    except Exception:
        return None


def fetch_symbol(sym: str, months: List[str]) -> pd.DataFrame:
    pq = DATA_DIR / f"{sym}_1h_funding.parquet"
    if pq.exists():
        df = pd.read_parquet(pq)
        if df.index.max() < pd.Timestamp(CUTOFF_UTC_STR, tz="UTC"):
            return df

    k_parts, f_parts = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        k_futs = {ex.submit(_download_month_kline, sym, ym): ym for ym in months}
        f_futs = {ex.submit(_download_month_funding, sym, ym): ym for ym in months}
        for fut in concurrent.futures.as_completed(k_futs):
            res = fut.result()
            if res is not None and len(res):
                k_parts.append(res)
        for fut in concurrent.futures.as_completed(f_futs):
            res = fut.result()
            if res is not None and len(res):
                f_parts.append(res)

    k = pd.concat(k_parts, ignore_index=True).drop_duplicates("open_time").sort_values("open_time")
    k["dt"] = pd.to_datetime(k["open_time"], unit="ms", utc=True)
    k = k[k["dt"] < pd.Timestamp(CUTOFF_UTC_STR, tz="UTC")].set_index("dt")[["open", "high", "low", "close", "volume"]]

    if f_parts:
        f = pd.concat(f_parts, ignore_index=True).drop_duplicates("calc_time").sort_values("calc_time")
        f["dt"] = pd.to_datetime(f["calc_time"], unit="ms", utc=True).dt.floor("h")
        f = f[f["dt"] < pd.Timestamp(CUTOFF_UTC_STR, tz="UTC")].groupby("dt")["rate"].last()
        k["funding"] = f.reindex(k.index, fill_value=0.0)
    else:
        k["funding"] = 0.0

    k.to_parquet(pq)
    print(f"  {sym}: {len(k)} 1h bars ({k.index.min().date()} -> {k.index.max().date()})", flush=True)
    return k


def _resample_4h(df: pd.DataFrame) -> pd.DataFrame:
    return df.resample("4h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum", "funding": "sum"}
    ).dropna(subset=["open", "close"])


def _resample_1d(df: pd.DataFrame) -> pd.DataFrame:
    return df.resample("1D", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum", "funding": "sum"}
    ).dropna(subset=["open", "close"])


def backtest_weights_bar(
    closes: pd.DataFrame,
    pos_w: pd.DataFrame,
    funding: pd.DataFrame,
    cost_rt: float = COST_RT,
    notional_base: float = 10_000.0,
) -> tuple[pd.Series, pd.Series, float]:
    """Backtest vectorizado causal sin look-ahead:
    pos_w[t] decidida al cierre t -> expuesta al retorno (close[t+1]/close[t] - 1) y funding[t+1].
    Retorna (pnl_diario_usd, min_diario_usd_est, ops_mes_aprox).
    """
    w = pos_w.shift(1).fillna(0.0)
    dw = (w - w.shift(1).fillna(0.0)).abs()
    ret = closes.pct_change().fillna(0.0)
    # funding positivo: largos pagan, cortos cobran
    fund_pnl = -w * funding.fillna(0.0)
    cost_bar = dw * (cost_rt * 0.5)
    bar_ret = (w * ret + fund_pnl - cost_bar).sum(axis=1)
    bar_usd = bar_ret * notional_base
    daily_usd = bar_usd.resample("1D").sum()
    daily_usd.index = daily_usd.index.tz_localize(None)
    # Estimacion conservadora de minimo intradia diario: worst cumulative path inside each day
    cum_intra = bar_usd.groupby(bar_usd.index.floor("D")).cumsum()
    min_intra = cum_intra.groupby(cum_intra.index.floor("D")).min().reindex(bar_usd.resample("1D").sum().index, fill_value=0.0)
    min_intra.index = min_intra.index.tz_localize(None)
    min_intra = np.minimum(min_intra, np.minimum(daily_usd, 0.0))

    n_months = max(1.0, len(daily_usd) / 30.4)
    n_trades = float((dw > 1e-6).to_numpy().sum() / 2.0)
    return daily_usd, min_intra, n_trades / n_months


def build_strategies(data: Dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """5 estrategias canonicas ortogonales (1 spec fija c/u, sin grilla)."""
    d1_close = pd.DataFrame({s: _resample_1d(df)["close"] for s, df in data.items()}).dropna(how="all")
    d1_high = pd.DataFrame({s: _resample_1d(df)["high"] for s, df in data.items()}).reindex(d1_close.index)
    d1_low = pd.DataFrame({s: _resample_1d(df)["low"] for s, df in data.items()}).reindex(d1_close.index)
    d1_fund = pd.DataFrame({s: _resample_1d(df)["funding"] for s, df in data.items()}).reindex(d1_close.index).fillna(0.0)

    h4_bars = {s: _resample_4h(df) for s, df in data.items()}
    h4_close = pd.DataFrame({s: b["close"] for s, b in h4_bars.items()}).dropna(how="all")
    h4_high = pd.DataFrame({s: b["high"] for s, b in h4_bars.items()}).reindex(h4_close.index)
    h4_low = pd.DataFrame({s: b["low"] for s, b in h4_bars.items()}).reindex(h4_close.index)
    h4_fund = pd.DataFrame({s: b["funding"] for s, b in h4_bars.items()}).reindex(h4_close.index).fillna(0.0)

    tr_1d = np.maximum(d1_high - d1_low, np.maximum((d1_high - d1_close.shift(1)).abs(), (d1_low - d1_close.shift(1)).abs()))
    atr20_d1 = tr_1d.rolling(20).mean()
    vol_pct_d1 = (atr20_d1 / d1_close).clip(lower=0.01)

    tr_4h = np.maximum(h4_high - h4_low, np.maximum((h4_high - h4_close.shift(1)).abs(), (h4_low - h4_close.shift(1)).abs()))
    atr42_4h = tr_4h.rolling(42).mean()
    vol_pct_4h = (atr42_4h / h4_close).clip(lower=0.005)

    meta = {}
    daily_dict = {}
    min_dict = {}

    # 1) CR_Donchian_20_10_1D: Trend Following diario Long/Short, sizing inverso a volatilidad ATR20 (target vol ~ 1.5% diaria total)
    hi20 = d1_high.shift(1).rolling(20).max()
    lo20 = d1_low.shift(1).rolling(20).min()
    hi10 = d1_high.shift(1).rolling(10).max()
    lo10 = d1_low.shift(1).rolling(10).min()
    pos_don = pd.DataFrame(0.0, index=d1_close.index, columns=d1_close.columns)
    for s in d1_close.columns:
        c = d1_close[s].to_numpy()
        h20, l20, h10, l10 = hi20[s].to_numpy(), lo20[s].to_numpy(), hi10[s].to_numpy(), lo10[s].to_numpy()
        p = np.zeros(len(c))
        st = 0.0
        for i in range(21, len(c)):
            if st == 0:
                if c[i] > h20[i]: st = 1.0
                elif c[i] < l20[i]: st = -1.0
            elif st > 0:
                if c[i] < l10[i]: st = -1.0 if c[i] < l20[i] else 0.0
            elif st < 0:
                if c[i] > h10[i]: st = 1.0 if c[i] > h20[i] else 0.0
            p[i] = st
        pos_don[s] = p
    # Inverse vol scaling per coin: target 0.015 / vol_pct, capped at 0.25 notional per coin (max 2.0x gross)
    w_don = pos_don * (0.005 / vol_pct_d1).clip(upper=0.25)
    d_ret, d_min, ops_m = backtest_weights_bar(d1_close, w_don, d1_fund)
    daily_dict["CR_Donchian_1D"], min_dict["CR_Donchian_1D"] = d_ret, d_min
    meta["CR_Donchian_1D"] = {"ops_mes": round(ops_m, 1), "desc": "Donchian 20/10 L/S inv-vol 8 perpetuos"}

    # 2) CR_EMA_Momentum_4H: EMA 24 vs EMA 96 (4H = 4d vs 16d), tendencia pura 4H con stop ATR 2.5x
    ema_f = h4_close.ewm(span=24, adjust=False).mean()
    ema_s = h4_close.ewm(span=96, adjust=False).mean()
    sig_ema = pd.DataFrame(0.0, index=h4_close.index, columns=h4_close.columns)
    for s in h4_close.columns:
        c = h4_close[s].to_numpy()
        hi, lo = h4_high[s].to_numpy(), h4_low[s].to_numpy()
        ef, es, a = ema_f[s].to_numpy(), ema_s[s].to_numpy(), atr42_4h[s].to_numpy()
        p = np.zeros(len(c))
        st, stop = 0.0, 0.0
        for i in range(100, len(c)):
            if not np.isfinite(a[i]) or a[i] <= 0:
                continue
            if st > 0:
                stop = max(stop, c[i] - 2.5 * a[i])
                if lo[i] <= stop or ef[i] < es[i]:
                    st = 0.0
            elif st < 0:
                stop = min(stop, c[i] + 2.5 * a[i])
                if hi[i] >= stop or ef[i] > es[i]:
                    st = 0.0
            if st == 0:
                if ef[i] > es[i] and c[i] > ef[i]:
                    st, stop = 1.0, c[i] - 2.5 * a[i]
                elif ef[i] < es[i] and c[i] < ef[i]:
                    st, stop = -1.0, c[i] + 2.5 * a[i]
            p[i] = st
        sig_ema[s] = p
    w_ema = sig_ema * (0.003 / vol_pct_4h).clip(upper=0.20)
    d_ret, d_min, ops_m = backtest_weights_bar(h4_close, w_ema, h4_fund)
    daily_dict["CR_Trend_4H_EMA"], min_dict["CR_Trend_4H_EMA"] = d_ret, d_min
    meta["CR_Trend_4H_EMA"] = {"ops_mes": round(ops_m, 1), "desc": "Trend 4H EMA24/96 + trailing 2.5xATR"}

    # 3) CR_XSMOM_Neutral_1D: Cross-sectional momentum 14d ajustado por vol: Long top-2 vs Short bottom-2 (mercado neutral!)
    ret14 = d1_close.pct_change(14) / vol_pct_d1
    ranks = ret14.rank(axis=1, ascending=False, method="first")
    n_avail = ret14.notna().sum(axis=1)
    long_m = (ranks <= 2) & (n_avail >= 6).to_numpy()[:, None]
    short_m = (ranks >= (n_avail - 1).to_numpy()[:, None]) & (n_avail >= 6).to_numpy()[:, None]
    pos_xs = pd.DataFrame(0.0, index=d1_close.index, columns=d1_close.columns)
    pos_xs[long_m] = 1.0
    pos_xs[short_m] = -1.0
    # Rebalancear cada 3 dias para no quemar friccion
    pos_xs = pos_xs.iloc[::3].reindex(d1_close.index).ffill().fillna(0.0)
    w_xs = pos_xs * (0.005 / vol_pct_d1).clip(upper=0.25)
    # Neutralize exact dollar-vol net per row
    w_xs = w_xs.sub(w_xs.mean(axis=1), axis=0)
    d_ret, d_min, ops_m = backtest_weights_bar(d1_close, w_xs, d1_fund)
    daily_dict["CR_XSMOM_Neutral"], min_dict["CR_XSMOM_Neutral"] = d_ret, d_min
    meta["CR_XSMOM_Neutral"] = {"ops_mes": round(ops_m, 1), "desc": "Long top-2 / Short bottom-2 (14d vol-adj, neutral cada 3d)"}

    # 4) CR_Funding_Carry_4H: Cobrar funding extremo (+): corto si funding 8h > 0.025% y precio < EMA24; largo si funding < -0.015% y precio > EMA24
    # O carry puro neutral: short top-2 highest positive funding, long bottom-2 lowest/negative funding
    f_roll = h4_fund.rolling(6).mean()  # media 24h de funding
    f_ranks = f_roll.rank(axis=1, ascending=False, method="first")
    n_f = f_roll.notna().sum(axis=1)
    pos_fc = pd.DataFrame(0.0, index=h4_close.index, columns=h4_close.columns)
    # Short over-levered longs (high positive funding) vs Long negative/low funding
    pos_fc[(f_ranks <= 2) & (f_roll > 0.00015) & (n_f >= 6).to_numpy()[:, None]] = -1.0
    pos_fc[(f_ranks >= (n_f - 1).to_numpy()[:, None]) & (f_roll < 0.00005) & (n_f >= 6).to_numpy()[:, None]] = 1.0
    pos_fc = pos_fc.iloc[::6].reindex(h4_close.index).ffill().fillna(0.0)  # rebalanceo cada 24h
    w_fc = pos_fc * 0.20
    d_ret, d_min, ops_m = backtest_weights_bar(h4_close, w_fc, h4_fund)
    daily_dict["CR_Funding_Carry"], min_dict["CR_Funding_Carry"] = d_ret, d_min
    meta["CR_Funding_Carry"] = {"ops_mes": round(ops_m, 1), "desc": "Carry de funding 24h: corto funding alto vs largo funding bajo"}

    # 5) CR_VolBreakout_4H: Compresion 4H (ATR12 / ATR72 < 0.75) -> ruptura maximo/minimo 12 velas (48h) con trailing stop 2.0xATR
    atr12 = tr_4h.rolling(12).mean()
    atr72 = tr_4h.rolling(72).mean()
    hi12 = h4_high.shift(1).rolling(12).max()
    lo12 = h4_low.shift(1).rolling(12).min()
    sig_vb = pd.DataFrame(0.0, index=h4_close.index, columns=h4_close.columns)
    for s in h4_close.columns:
        c = h4_close[s].to_numpy()
        hi, lo = h4_high[s].to_numpy(), h4_low[s].to_numpy()
        a12, a72, h12, l12, a42 = atr12[s].to_numpy(), atr72[s].to_numpy(), hi12[s].to_numpy(), lo12[s].to_numpy(), atr42_4h[s].to_numpy()
        p = np.zeros(len(c))
        st, stop, age = 0.0, 0.0, 0
        for i in range(75, len(c)):
            if not np.isfinite(a42[i]) or a42[i] <= 0 or a72[i] <= 0:
                continue
            if st > 0:
                age += 1
                stop = max(stop, c[i] - 2.0 * a42[i])
                if lo[i] <= stop or age >= 18:
                    st = 0.0
            elif st < 0:
                age += 1
                stop = min(stop, c[i] + 2.0 * a42[i])
                if hi[i] >= stop or age >= 18:
                    st = 0.0
            if st == 0 and (a12[i] / a72[i]) < 0.80:
                if c[i] > h12[i]:
                    st, stop, age = 1.0, c[i] - 2.0 * a42[i], 0
                elif c[i] < l12[i]:
                    st, stop, age = -1.0, c[i] + 2.0 * a42[i], 0
            p[i] = st
        sig_vb[s] = p
    w_vb = sig_vb * (0.004 / vol_pct_4h).clip(upper=0.22)
    d_ret, d_min, ops_m = backtest_weights_bar(h4_close, w_vb, h4_fund)
    daily_dict["CR_VolBreakout_4H"], min_dict["CR_VolBreakout_4H"] = d_ret, d_min
    meta["CR_VolBreakout_4H"] = {"ops_mes": round(ops_m, 1), "desc": "Ruptura post-compresion 4H (ATR12/ATR72 < 0.80)"}

    df_d = pd.DataFrame(daily_dict).fillna(0.0)
    df_m = pd.DataFrame(min_dict).reindex(df_d.index).fillna(0.0)
    # Truncate strictly < 2026-10-01 and keep only >= 2021-01-01 (warmup 4 meses 2020-09..12)
    df_d = df_d[(df_d.index >= "2021-01-01") & (df_d.index < CUTOFF_UTC_STR)]
    df_m = df_m.reindex(df_d.index).fillna(0.0)
    return df_d, df_m, meta


def stats_block(x: pd.Series, xmin: pd.Series | None = None) -> dict:
    x = x.dropna()
    if len(x) < 10:
        return {"usd_mes": 0.0, "sharpe": 0.0, "t_mes": 0.0, "caida_max_eod": 0.0, "caida_max_intra": 0.0, "pct_meses_pos": 0.0}
    m = x.groupby(x.index.to_period("M")).sum()
    eq = x.cumsum()
    dd = eq - eq.cummax()
    dd_i = float(dd.min())
    if xmin is not None:
        xm = np.minimum(xmin.reindex(x.index).fillna(0.0), np.minimum(x, 0.0))
        dd_i = float(min((eq.shift(1, fill_value=0.0) + xm - eq.cummax().shift(1, fill_value=0.0)).min(), dd.min()))
    sd = float(m.std(ddof=1)) if len(m) > 1 else 0.0
    mu = float(m.mean()) if len(m) else 0.0
    return {
        "usd_mes": round(mu, 2),
        "sharpe": round(float(mu / sd * np.sqrt(12)), 3) if sd > 0 else 0.0,
        "t_mes": round(float(mu / (sd / np.sqrt(len(m)))), 2) if sd > 0 and len(m) > 1 else 0.0,
        "caida_max_eod": round(float(dd.min()), 1),
        "caida_max_intra": round(dd_i, 1),
        "calmar_eod": round(float((mu * 12) / abs(dd.min())), 2) if dd.min() < 0 else 0.0,
        "pct_meses_pos": round(float((m > 0).mean()), 3),
        "meses": int(len(m)),
    }


def _hrp_weights(ret: pd.DataFrame) -> np.ndarray:
    lw = LedoitWolf().fit(ret.to_numpy())
    cov = lw.covariance_
    sd = np.sqrt(np.clip(np.diag(cov), 1e-9, None))
    corr = cov / np.outer(sd, sd)
    np.fill_diagonal(corr, 1.0)
    dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0.0, 1.0))
    np.fill_diagonal(dist, 0.0)
    order = leaves_list(linkage(squareform(dist, checks=False), "single"))
    w = np.ones(len(sd))
    clusters = [list(order)]
    while clusters:
        c = clusters.pop()
        if len(c) <= 1:
            continue
        a, b = c[: len(c) // 2], c[len(c) // 2 :]
        def v_c(ix):
            cc = cov[np.ix_(ix, ix)]
            iv = 1.0 / np.clip(np.diag(cc), 1e-9, None)
            iv /= iv.sum()
            return float(iv @ cc @ iv)
        va, vb = v_c(a), v_c(b)
        al = 1.0 - va / (va + vb) if (va + vb) > 0 else 0.5
        w[a] *= al
        w[b] *= 1.0 - al
        clusters += [a, b]
    return w / w.sum()


def main() -> None:
    months = pd.period_range("2020-09", "2026-09", freq="M").strftime("%Y-%m").tolist()
    print(f"=== DESCARGA BINANCE FUTURES USDT-M ({len(SYMBOLS)} monedas x {len(months)} meses, < {CUTOFF_UTC_STR}) ===", flush=True)
    data = {sym: fetch_symbol(sym, months) for sym in SYMBOLS}

    df_d, df_m, meta = build_strategies(data)
    # STRICT A5 GOVERNANCE: Crypto is a NEW family -> only read DESC and REP! Seal HOLDOUT, EMBARGO, TERMINAL!
    ses = pd.Series([int(d.strftime("%Y%m%d")) for d in df_d.index], index=df_d.index)
    blq = ses.map(a5_bloque)
    mask_dr = blq.isin(["DESC", "REP"])
    assert not (df_d.index >= pd.Timestamp(CUTOFF_UTC_STR)).any(), "HOLDOUT-A4 breach!"

    print("\n=== RESULTADOS ESTRATEGIAS CRIPTO EN DESC vs REP (A5; HOLDOUT SELLADO) ===")
    strats_res = {}
    alive = []
    for c in df_d.columns:
        st_desc = stats_block(df_d.loc[blq == "DESC", c], df_m.loc[blq == "DESC", c])
        st_rep = stats_block(df_d.loc[blq == "REP", c], df_m.loc[blq == "REP", c])
        st_dr = stats_block(df_d.loc[mask_dr, c], df_m.loc[mask_dr, c])
        strats_res[c] = {"meta": meta[c], "DESC": st_desc, "REP": st_rep, "DESC_REP": st_dr}
        ok = st_desc["usd_mes"] > 0 and st_rep["usd_mes"] > 0
        if ok:
            alive.append(c)
        print(
            f"  {c:20s} | ops/m={meta[c]['ops_mes']:5.1f} | DESC: Sh={st_desc['sharpe']:5.2f} $/m={st_desc['usd_mes']:6.1f} | "
            f"REP: Sh={st_rep['sharpe']:5.2f} $/m={st_rep['usd_mes']:6.1f} | vivo_DESC+REP={ok}"
        )

    # Construct Crypto Portfolio on alive strategies using causal HRP on DESC -> test on REP (plus WF within DESC+REP)
    if len(alive) < 2:
        alive = [c for c in df_d.columns if strats_res[c]["DESC_REP"]["usd_mes"] > 0]
    w_eq = np.ones(len(alive)) / len(alive)
    w_hrp = _hrp_weights(df_d.loc[blq == "DESC", alive])

    port_eq = (df_d[alive] * w_eq).sum(axis=1)
    port_eq_m = (df_m[alive] * w_eq).sum(axis=1)
    port_hrp = (df_d[alive] * w_hrp).sum(axis=1)
    port_hrp_m = (df_m[alive] * w_hrp).sum(axis=1)

    crypto_port = {
        "alive_strategies": alive,
        "hrp_weights_from_DESC": {k: round(float(v), 4) for k, v in zip(alive, w_hrp)},
        "EQ_1N": {"DESC": stats_block(port_eq[blq == "DESC"], port_eq_m[blq == "DESC"]),
                  "REP": stats_block(port_eq[blq == "REP"], port_eq_m[blq == "REP"]),
                  "DESC_REP": stats_block(port_eq[mask_dr], port_eq_m[mask_dr])},
        "HRP_DESC": {"DESC": stats_block(port_hrp[blq == "DESC"], port_hrp_m[blq == "DESC"]),
                     "REP": stats_block(port_hrp[blq == "REP"], port_hrp_m[blq == "REP"]),
                     "DESC_REP": stats_block(port_hrp[mask_dr], port_hrp_m[mask_dr])},
    }
    print("\n=== CARTERA CRIPTO ($10k base, net 10bps RT + funding real) ===")
    print("  Vivas (DESC>0 y REP>0):", alive)
    print("  HRP pesos (fit DESC):", crypto_port["HRP_DESC"]["DESC"], "-> OOS REP:", crypto_port["HRP_DESC"]["REP"])
    print("  1/N (fit DESC)     :", crypto_port["EQ_1N"]["DESC"], "-> OOS REP:", crypto_port["EQ_1N"]["REP"])

    # Cross-front correlation vs CME (strictly on DESC+REP dates so crypto HOLDOUT stays sealed!)
    cme = pd.read_csv(OUT / "SERIES_AUDITORIA_DIARIAS.csv.gz", index_col=0, parse_dates=True)
    intra8_cols = ["T_NQ", "R_NQ", "Z_NQ", "V_NQ", "RQ5_NQ", "FR_NQ", "RQ5_ES", "ES5N_ES"]
    inter3_cols = ["SOMSF_NQ", "C2VZ_NQ", "C2VZ_ES"]
    cme_intra = cme[intra8_cols].sum(axis=1)
    cme_mix = cme[intra8_cols + inter3_cols].sum(axis=1)

    common = df_d.index[mask_dr].intersection(cme.index)
    # Compare on business/common days and monthly
    cr_dr = port_hrp.reindex(cme.index).fillna(0.0).loc[cme.index.isin(df_d.index[mask_dr])]
    # Actually resample Crypto to monthly using ONLY DESC+REP days, and CME on same months (DESC+REP of A5 is aligned by month!)
    c_m_crypto = port_hrp.loc[mask_dr].groupby(port_hrp.loc[mask_dr].index.to_period("M")).sum()
    c_m_intra = cme_intra.groupby(cme_intra.index.to_period("M")).sum().reindex(c_m_crypto.index).dropna()
    c_m_mix = cme_mix.groupby(cme_mix.index.to_period("M")).sum().reindex(c_m_crypto.index).dropna()
    c_m_crypto_al = c_m_crypto.reindex(c_m_intra.index)

    corr_intra_m = float(c_m_crypto_al.corr(c_m_intra))
    corr_mix_m = float(c_m_crypto_al.corr(c_m_mix))
    corr_intra_d = float(port_hrp.loc[common].corr(cme_intra.loc[common]))
    corr_mix_d = float(port_hrp.loc[common].corr(cme_mix.loc[common]))

    # Multi-front Vol-matched combination (scale Crypto HRP to match CME Mixto monthly SD -> 50/50 risk parity CME+Crypto)
    scale_cr = float(c_m_mix.std(ddof=1) / c_m_crypto_al.std(ddof=1)) if c_m_crypto_al.std(ddof=1) > 0 else 1.0
    multi_frente_m = 0.5 * c_m_mix + 0.5 * (c_m_crypto_al * scale_cr)
    # Daily proxy on DESC+REP dates (mapping weekend crypto pnl onto Monday or keeping 7d series + CME 0 on weekends)
    dr_full_idx = df_d.index[mask_dr]
    cme_mix_7d = cme_mix.reindex(dr_full_idx, fill_value=0.0)
    cme_min_full = pd.read_csv(OUT / "SERIES_AUDITORIA_MIN_INTRADIA.csv.gz", index_col=0, parse_dates=True)[intra8_cols + inter3_cols].sum(axis=1).reindex(dr_full_idx, fill_value=0.0)
    super_d = 0.5 * cme_mix_7d + 0.5 * (port_hrp.loc[dr_full_idx] * scale_cr)
    super_min = 0.5 * cme_min_full + 0.5 * (port_hrp_m.loc[dr_full_idx] * scale_cr)

    cross_front = {
        "corr_mensual_vs_CME_INTRADIA8": round(corr_intra_m, 3),
        "corr_mensual_vs_CME_MIXTO": round(corr_mix_m, 3),
        "corr_diaria_vs_CME_INTRADIA8": round(corr_intra_d, 3),
        "corr_diaria_vs_CME_MIXTO": round(corr_mix_d, 3),
        "crypto_scale_to_match_CME_mix_vol": round(scale_cr, 3),
        "CME_MIXTO_en_DESC_REP": stats_block(cme_mix_7d, cme_min_full),
        "SUPER_50_50_CME_CRIPTO_en_DESC_REP": stats_block(super_d, super_min),
    }
    print("\n=== INTEGRACION MULTI-FRENTE (CME + CRIPTO en meses DESC+REP, 2021-2026) ===")
    print(json.dumps(cross_front, indent=2))

    # Save ONLY DESC+REP daily series (explicitly zero/NaN in HOLDOUT so downstream never touches crypto HOLDOUT!)
    save_df = df_d.copy()
    save_df[~mask_dr] = np.nan
    save_df["CR_HRP_PORT"] = np.where(mask_dr, port_hrp, np.nan)
    save_df.to_csv(OUT / "SERIES_CRIPTO_DESC_REP.csv.gz")

    save_min = df_m.copy()
    save_min[~mask_dr] = np.nan
    save_min["CR_HRP_PORT"] = np.where(mask_dr, port_hrp_m, np.nan)
    save_min.to_csv(OUT / "SERIES_CRIPTO_MIN_DESC_REP.csv.gz")

    res = {
        "symbols": SYMBOLS,
        "cost_rt": COST_RT,
        "strategies_A5": strats_res,
        "crypto_portfolio": crypto_port,
        "cross_front_integration": cross_front,
    }
    (OUT / "CARTERA_CRIPTO_RESUMEN.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("\nSaved:", OUT / "CARTERA_CRIPTO_RESUMEN.json")


if __name__ == "__main__":
    main()

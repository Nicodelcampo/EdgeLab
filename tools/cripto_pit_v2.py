#!/usr/bin/env python3
"""CRIPTO-PIT v2 (2026-11-27): Universo PIT limpio + correccion del bug de neutralizacion + 5 mecanismos de baja rotacion.

Evalua ESTRICTAMENTE sobre A5 DESC (39m) y REP (12m), manteniendo HOLDOUT A5 (18m) y TERMINAL (>=2026-10-01) SELLADOS (NaN).
Uso:
  python -u tools/cripto_pit_v2.py
"""
from __future__ import annotations

import concurrent.futures
import io
import json
import re
import sys
import time
import urllib.request
import zipfile
from math import erf, sqrt
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edgelab.holdout import a5_bloque  # noqa: E402

DATA = ROOT / "data" / "crypto_binance_pit_1d"
DATA.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "docs" / "research" / "auditoria_claude_20261127"
OUT.mkdir(parents=True, exist_ok=True)

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
VIS = "https://data.binance.vision"
CORTE = "2026-10-01"
PER_MIN = "2020-01"          # primer mes de descarga (cripto_v3_2019.py lo adelanta a 2019-09)
CORTE_TS = pd.Timestamp(CORTE, tz="UTC")
MESES_ALL = set(pd.period_range("2020-01", "2026-09", freq="M").strftime("%Y-%m").tolist())
UA = {"User-Agent": "edgelab-research"}
TRADFI_EXCLUDE = {
    "CLUSDT", "BZUSDT", "MUUSDT", "INTCUSDT", "SOXLUSDT", "EWYUSDT", "KORUUSDT",
    "XAUUSDT", "XAGUSDT", "PAXGUSDT", "SPCXUSDT", "DRAMUSDT",
    "USDCUSDT", "BUSDUSDT", "FDUSDUSDT", "TUSDUSDT", "USDPUSDT",
    "EURUSDT", "GBPUSDT", "JPYUSDT", "NVDAUSDT", "TSLAUSDT", "AAPLUSDT",
    "AMZNUSDT", "GOOGLUSDT", "METAUSDT", "MSFTUSDT", "COINUSDT", "MSTRUSDT",
    "HOODUSDT", "PLTRUSDT", "SPXUSDT", "QQQUSDT", "SLVUSDT", "GLDUSDT", "USOUSDT",
}


def _get(url: str, timeout: int = 25) -> bytes | None:
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            time.sleep(0.2)
    return None


def _listar(prefix: str) -> list[str]:
    from urllib.parse import quote
    out, marker = [], ""
    while True:
        x = _get(f"{S3}?delimiter=/&prefix={quote(prefix)}&marker={quote(marker)}")
        if x is None:
            return out
        t = x.decode("utf-8", errors="ignore")
        out += re.findall(r"<Prefix>([^<]+)</Prefix>", t)[1:] + re.findall(r"<Key>([^<]+)</Key>", t)
        if "<IsTruncated>true</IsTruncated>" not in t:
            return out
        m = re.search(r"<NextMarker>([^<]+)</NextMarker>", t)
        if not m:
            return out
        marker = m.group(1)


def _sym_months_from_pit(u: pd.DataFrame) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    per_min = pd.Period(PER_MIN, "M")
    per_max = pd.Period("2026-09", "M")
    for sym, grp in u.groupby("simbolo"):
        if not str(sym).isascii() or sym in TRADFI_EXCLUDE:
            continue
        p0 = max(per_min, pd.Period(grp["mes"].min(), "M") - 4)
        p1 = min(per_max, pd.Period(grp["mes"].max(), "M") + 1)
        out[sym] = pd.period_range(p0, p1, freq="M").strftime("%Y-%m").tolist()
    return out


def _dl_one_kline(args: tuple[str, str]) -> tuple[str, pd.DataFrame | None]:
    sym, ym = args
    from urllib.parse import quote
    b = _get(quote(f"{VIS}/data/futures/um/monthly/klines/{sym}/1d/{sym}-1d-{ym}.zip", safe=":/"), timeout=12)
    if b is None:
        return sym, None
    try:
        z = zipfile.ZipFile(io.BytesIO(b))
        raw = pd.read_csv(z.open(z.namelist()[0]), header=None)
        if not str(raw.iloc[0, 0]).isdigit():
            raw = raw.iloc[1:]
        raw = raw.iloc[:, :8].astype(float)
        raw.columns = ["t", "open", "high", "low", "close", "volume", "t_cierre", "quote_volume"]
        return sym, raw
    except Exception:
        return sym, None


def _dl_one_fund(args: tuple[str, str]) -> tuple[str, pd.DataFrame | None]:
    sym, ym = args
    from urllib.parse import quote
    b = _get(quote(f"{VIS}/data/futures/um/monthly/fundingRate/{sym}/{sym}-fundingRate-{ym}.zip", safe=":/"), timeout=12)
    if b is None:
        return sym, None
    try:
        z = zipfile.ZipFile(io.BytesIO(b))
        df = pd.read_csv(z.open(z.namelist()[0]))
        df.columns = [c.lower() for c in df.columns]
        tc = "calc_time" if "calc_time" in df.columns else df.columns[0]
        rc = "last_funding_rate" if "last_funding_rate" in df.columns else df.columns[-1]
        return sym, pd.DataFrame({"t": pd.to_numeric(df[tc], errors="coerce"), "rate": pd.to_numeric(df[rc], errors="coerce")}).dropna()
    except Exception:
        return sym, None


def fetch_all_pit_fast(u: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    sym_months = _sym_months_from_pit(u)
    bars: Dict[str, pd.DataFrame] = {}
    todo_k, todo_f = [], []
    for sym, ms in sym_months.items():
        pq = DATA / f"{sym}_1d_funding.parquet"
        if pq.exists():
            df = pd.read_parquet(pq)
            if len(df) >= 40 and df.index.max() < CORTE_TS:
                bars[sym] = df
            continue
        for ym in ms:
            todo_k.append((sym, ym))
            todo_f.append((sym, ym))

    if todo_k:
        print(f"  Descargando {len(todo_k)} archivos mensuales 1D+funding en paralelo (32 hilos)...", flush=True)
        k_acc: Dict[str, list] = {}
        f_acc: Dict[str, list] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
            for sym, part in ex.map(_dl_one_kline, todo_k):
                if part is not None:
                    k_acc.setdefault(sym, []).append(part)
            for sym, part in ex.map(_dl_one_fund, todo_f):
                if part is not None:
                    f_acc.setdefault(sym, []).append(part)

        for sym in sym_months:
            if sym in bars:
                continue
            pq = DATA / f"{sym}_1d_funding.parquet"
            k_parts = k_acc.get(sym, [])
            if not k_parts:
                pd.DataFrame().to_parquet(pq)
                continue
            k = pd.concat(k_parts, ignore_index=True).drop_duplicates("t").sort_values("t")
            k["dt"] = pd.to_datetime(k["t"].astype("int64"), unit="ms", utc=True).dt.normalize()
            k = k[k["dt"] < CORTE_TS].drop_duplicates("dt").set_index("dt")[["open", "high", "low", "close", "volume", "quote_volume"]]
            f_parts = f_acc.get(sym, [])
            if f_parts:
                f = pd.concat(f_parts, ignore_index=True).drop_duplicates("t").sort_values("t")
                f["dt"] = pd.to_datetime(f["t"].astype("int64"), unit="ms", utc=True).dt.normalize()
                f = f[f["dt"] < CORTE_TS].groupby("dt")["rate"].sum()
                k["funding"] = f.reindex(k.index, fill_value=0.0)
            else:
                k["funding"] = 0.0
            assert not (k.index >= CORTE_TS).any(), f"Holdout breach in {sym}!"
            k.to_parquet(pq)
            if len(k) >= 40:
                bars[sym] = k
    return bars


def stats_serie(x: pd.Series) -> dict:
    x = x.dropna()
    m = x.groupby(x.index.to_period("M")).sum()
    n = len(m)
    if n < 3:
        return {"usd_mes": 0.0, "t_mes": 0.0, "p_una_cola": 0.5, "sharpe": 0.0, "pct_meses_pos": 0.0, "caida_max": 0.0, "meses": n}
    mu = float(m.mean())
    sd = float(m.std(ddof=1))
    t = mu / (sd / np.sqrt(n)) if sd > 0 else 0.0
    sh = mu / sd * np.sqrt(12) if sd > 0 else 0.0
    eq = x.cumsum()
    return {
        "usd_mes": round(mu, 1),
        "t_mes": round(t, 2),
        "p_una_cola": round(0.5 * (1.0 - erf(t / sqrt(2.0))), 4),
        "sharpe": round(sh, 2),
        "pct_meses_pos": round(float((m > 0).mean()), 2),
        "caida_max": round(float((eq - eq.cummax()).min()), 0),
        "meses": int(n),
    }


def _safe_close_returns(C: pd.DataFrame, max_gap: int = 5) -> pd.DataFrame:
    """Preserva retorno real ante huecos internos de archivo (ej. 2022-02-26..28), sin inventar precios post-delisting."""
    C_int = C.copy()
    for s in C_int.columns:
        lv = C_int[s].last_valid_index()
        if lv is not None:
            m = C_int.index <= lv
            C_int.loc[m, s] = C_int.loc[m, s].ffill(limit=max_gap)
    return C_int.pct_change(fill_method=None)


def _stagger_weights(w_daily: pd.DataFrame, E: pd.DataFrame, k: int) -> pd.DataFrame:
    """Promedia k tranches escalonadas congelando pesos cada k dias (elimina sesgo de fase y churn diario inv_vol)."""
    return sum(
        w_daily.iloc[o::k].reindex(w_daily.index).ffill().fillna(0.0).where(E, 0.0)
        for o in range(k)
    ) / float(k)


def _pnl(
    C: pd.DataFrame,
    pos_w: pd.DataFrame,
    F: pd.DataFrame,
    cost_rt: float,
    cap: float = 10_000.0,
    r_override: pd.DataFrame | None = None,
) -> tuple[pd.Series, pd.Series, float, int]:
    w = pos_w.shift(1).fillna(0.0)
    dw = (w - w.shift(1).fillna(0.0)).abs()
    r = r_override if r_override is not None else _safe_close_returns(C)
    delist_mask = (w != 0.0) & r.isna()
    delist_hits = int(delist_mask.sum().sum())
    r_clean = r.fillna(0.0)
    pnl_bar = (w * r_clean - w * F.fillna(0.0) - dw * (cost_rt * 0.5)).sum(axis=1) * cap
    shock_pnl = (delist_mask * (-0.30 * w.abs())).sum(axis=1) * cap
    pnl_stress = pnl_bar + shock_pnl
    turnover_m = float(dw.to_numpy().sum() * 0.5) / max(1.0, len(C) / 30.4)
    return pnl_bar, pnl_stress, round(turnover_m, 2), delist_hits


def _donchian_1d(C: np.ndarray, H: np.ndarray, L: np.ndarray, n_en: int, n_ex: int) -> np.ndarray:
    p = np.zeros(len(C))
    st = 0.0
    for i in range(n_en + 1, len(C)):
        if not np.isfinite(C[i]) or not np.isfinite(C[i - 1]):
            st = 0.0
            continue
        hi_en = np.nanmax(H[i - n_en : i])
        lo_en = np.nanmin(L[i - n_en : i])
        hi_ex = np.nanmax(H[i - n_ex : i])
        lo_ex = np.nanmin(L[i - n_ex : i])
        if st == 0.0:
            if C[i] > hi_en:
                st = 1.0
            elif C[i] < lo_en:
                st = -1.0
        elif st > 0.0:
            if C[i] < lo_ex:
                st = -1.0 if C[i] < lo_en else 0.0
        elif st < 0.0:
            if C[i] > hi_ex:
                st = 1.0 if C[i] > hi_en else 0.0
        p[i] = st
    return p


def _normalize_active_neutral(raw_pos: pd.DataFrame, vol_inv: pd.DataFrame, max_w: float = 0.15) -> pd.DataFrame:
    """Neutralizacion EXCLUSIVA sobre patas activas (corrige el bug de .sub(mean_all) en Claude!)."""
    lw = (raw_pos.clip(lower=0.0) * vol_inv).clip(upper=max_w)
    sw = ((-raw_pos).clip(lower=0.0) * vol_inv).clip(upper=max_w)
    lsum = lw.sum(axis=1)
    ssum = sw.sum(axis=1)
    # Match long and short total risk exposure cleanly when both legs have active positions
    both = (lsum > 0) & (ssum > 0)
    target = 0.50  # 50% long + 50% short = 100% gross, 0% net dollar exposure!
    lw_n = lw.div(lsum.replace(0, np.nan), axis=0).fillna(0.0) * target
    sw_n = sw.div(ssum.replace(0, np.nan), axis=0).fillna(0.0) * target
    out = lw_n - sw_n
    out[~both] = 0.0
    return out


def build_eligibility(idx: pd.DatetimeIndex, cols: pd.Index, u: pd.DataFrame, top_k: int = 25, hysteresis_exit: int | None = None) -> pd.DataFrame:
    E = pd.DataFrame(False, index=idx, columns=cols)
    if hysteresis_exit is None:
        um = {(r.mes, r.simbolo): r.rango for r in u.itertuples() if r.rango <= top_k}
        per = pd.PeriodIndex(idx, freq="M").astype(str)
        # Strict causal: membership for month m uses UNIVERSO_PIT month m (which Claude built strictly from prior 30 days volume!)
        for c in cols:
            ok = [((m, c) in um) for m in per]
            E[c] = ok
        return E

    # Hysteresis membership: enter if rank <= top_k, stay eligible until rank > hysteresis_exit (or delisted)
    rk_map = {(r.mes, r.simbolo): r.rango for r in u.itertuples()}
    months = sorted(u.mes.unique())
    active = set()
    active_by_month = {}
    for m in months:
        new_active = set()
        for c in cols:
            rk = rk_map.get((m, c), 9999)
            if c in active:
                if rk <= hysteresis_exit:
                    new_active.add(c)
            elif rk <= top_k:
                new_active.add(c)
        active = new_active
        active_by_month[m] = active
    per = pd.PeriodIndex(idx, freq="M").astype(str)
    for c in cols:
        E[c] = [c in active_by_month.get(m, set()) for m in per]
    return E


def main() -> None:
    t0 = time.time()
    u = pd.read_csv(ROOT / "docs/research/cripto_pit_20261127/UNIVERSO_PIT.csv")
    ascii_syms = sorted([s for s in u["simbolo"].unique() if str(s).isascii() and s not in TRADFI_EXCLUDE])
    print(f"=== CRIPTO-PIT v2 (auditada): Cargando 1D+Funding (< 2026-10-01) para {len(ascii_syms)} monedas crypto PIT ===", flush=True)

    bars = {s: df for s, df in fetch_all_pit_fast(u).items() if s not in TRADFI_EXCLUDE}

    print(f"Cargadas {len(bars)}/{len(ascii_syms)} monedas crypto con >=40 barras en {time.time() - t0:.1f}s", flush=True)

    C = pd.DataFrame({s: df["close"] for s, df in bars.items()}).sort_index()
    H = pd.DataFrame({s: df["high"] for s, df in bars.items()}).reindex(C.index)
    L = pd.DataFrame({s: df["low"] for s, df in bars.items()}).reindex(C.index)
    F = pd.DataFrame({s: df["funding"] for s, df in bars.items()}).reindex(C.index).fillna(0.0)
    C.index = C.index.tz_localize(None)
    H.index = C.index
    L.index = C.index
    F.index = C.index

    # Only keep rows strictly < 2026-10-01
    C = C[C.index < "2026-10-01"]
    H, L, F = H.reindex(C.index), L.reindex(C.index), F.reindex(C.index)

    r_safe = _safe_close_returns(C, max_gap=5)
    tr = np.maximum(H - L, np.maximum((H - C.shift(1)).abs(), (L - C.shift(1)).abs()))
    atr20 = tr.rolling(20, min_periods=10).mean()
    vol1 = (atr20 / C).clip(lower=0.01)
    inv_vol = (0.01 / vol1).clip(upper=0.25)

    # Causal filters: 60d live history + 60d annualized vol >= 25% (blocks stablecoins/gold/FX!)
    live_base = C.notna().rolling(60, min_periods=60).sum() >= 60
    vol60_ok = (r_safe.rolling(60, min_periods=30).std() * np.sqrt(365.0)) >= 0.25
    live60 = live_base & vol60_ok

    # ---- PART 1: ABLACION DE BUG DE CLAUDE EN UNIVERSO PIT TOP-25 ----
    E25 = build_eligibility(C.index, C.columns, u, top_k=25, hysteresis_exit=None) & live60
    esc25 = (8.0 / E25.sum(axis=1).clip(lower=1)).to_numpy()[:, None]

    # 1a) Claude's exact XSMOM (buggy .sub(mean))
    sc14 = (C.pct_change(14, fill_method=None) / vol1).where(E25)
    rk14 = sc14.rank(axis=1, ascending=False, method="first")
    n14 = sc14.notna().sum(axis=1).to_numpy()[:, None]
    pos_cl = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    pos_cl[(rk14 <= 2) & (n14 >= 6)] = 1.0
    pos_cl[(rk14 >= n14 - 1) & (n14 >= 6)] = -1.0
    pos_cl = pos_cl.iloc[::3].reindex(C.index).ffill().fillna(0.0)
    w_cl_raw = (pos_cl * (0.005 / vol1).clip(upper=0.25)).where(E25, 0.0)
    w_cl_bug = w_cl_raw.sub(w_cl_raw.where(E25).mean(axis=1), axis=0).where(E25, 0.0)

    # 1b) Active-Leg Fixed XSMOM on exact same signal (3d rebalance, zero spill to flat coins!)
    w_xs_fixed = _normalize_active_neutral(pos_cl.where(E25, 0.0), (0.01 / vol1).clip(upper=0.25), max_w=0.25)

    # 1c) Claude Donchian 20/10 PIT
    pos_don_cl = pd.DataFrame({s: _donchian_1d(C[s].to_numpy(), H[s].to_numpy(), L[s].to_numpy(), 20, 10) for s in C.columns}, index=C.index)
    w_don_cl = (pos_don_cl * (0.005 / vol1).clip(upper=0.25)).where(E25, 0.0) * esc25

    # ---- PART 2: 5 MECANISMOS LIMPIOS ESCALONADOS (Histeresis REAL enter<=20, exit>25 en rango 1..25, MIN_DIAS=60) ----
    E_hyst = build_eligibility(C.index, C.columns, u, top_k=20, hysteresis_exit=25) & live60
    esc_h = (8.0 / E_hyst.sum(axis=1).clip(lower=1)).to_numpy()[:, None]

    # M1: CR2_TSMOM_Blend_1D (7d + 21d + 60d continuous trend, threshold rebalance |dw|>0.25*|w| to suppress churn)
    ret_7 = C.pct_change(7, fill_method=None)
    ret_21 = C.pct_change(21, fill_method=None)
    ret_60 = C.pct_change(60, fill_method=None)
    sig_ts = (np.sign(ret_7.fillna(0.0)) + np.sign(ret_21.fillna(0.0)) + np.sign(ret_60.fillna(0.0))) / 3.0
    w_ts_raw = (sig_ts * (0.005 / vol1).clip(upper=0.20)).where(E_hyst, 0.0) * esc_h
    w_ts = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    for s in C.columns:
        arr = w_ts_raw[s].to_numpy()
        out_a = np.zeros(len(arr))
        cur = 0.0
        for i in range(len(arr)):
            tgt = arr[i]
            if tgt == 0.0:
                cur = 0.0
            elif abs(tgt - cur) > 0.25 * max(abs(cur), 0.01):
                cur = tgt
            out_a[i] = cur
        w_ts[s] = out_a

    # M2: CR2_Donchian_30_15
    pos_don30 = pd.DataFrame({s: _donchian_1d(C[s].to_numpy(), H[s].to_numpy(), L[s].to_numpy(), 30, 15) for s in C.columns}, index=C.index)
    w_don30 = (pos_don30 * (0.005 / vol1).clip(upper=0.20)).where(E_hyst, 0.0) * esc_h

    # M3: CR2_XSMOM_Stag5d (21d vol-adj momentum, top-4 long / bot-4 short, frozen 5d staggered across all 5 phases!)
    sc21 = (ret_21 / vol1).where(E_hyst)
    rk21 = sc21.rank(axis=1, ascending=False, method="first")
    n21 = sc21.notna().sum(axis=1).to_numpy()[:, None]
    pos_xs5_d = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    pos_xs5_d[(rk21 <= 4) & (n21 >= 10)] = 1.0
    pos_xs5_d[(rk21 >= n21 - 3) & (n21 >= 10)] = -1.0
    w_xs5_daily = _normalize_active_neutral(pos_xs5_d, inv_vol, max_w=0.20)
    w_xs5_stag = _stagger_weights(w_xs5_daily, E_hyst, 5)

    # M4: CR2_ResidMom_Stag5d (14d residual return vs 30d rolling BTC beta, top-4/bot-4, frozen 5d staggered)
    r1d = r_safe
    btc = r1d["BTCUSDT"].fillna(0.0) if "BTCUSDT" in r1d else r1d.mean(axis=1)
    btc_var = btc.rolling(30, min_periods=15).var().replace(0.0, np.nan)
    resid_1d = r1d.copy()
    for s in C.columns:
        cov_b = r1d[s].rolling(30, min_periods=15).cov(btc)
        beta = (cov_b / btc_var).clip(-2.0, 4.0).shift(1).fillna(1.0)
        resid_1d[s] = r1d[s] - beta * btc
    res14 = (resid_1d.rolling(14, min_periods=10).sum() / vol1).where(E_hyst)
    rkr = res14.rank(axis=1, ascending=False, method="first")
    nr = res14.notna().sum(axis=1).to_numpy()[:, None]
    pos_res_d = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    pos_res_d[(rkr <= 4) & (nr >= 10)] = 1.0
    pos_res_d[(rkr >= nr - 3) & (nr >= 10)] = -1.0
    w_res_daily = _normalize_active_neutral(pos_res_d, inv_vol, max_w=0.20)
    w_res_stag = _stagger_weights(w_res_daily, E_hyst, 5)

    # M5: CR2_Funding_Carry_Stag3d (3d avg funding rank, frozen 3d staggered)
    f3 = F.rolling(3, min_periods=2).mean().where(E_hyst)
    rkf = f3.rank(axis=1, ascending=False, method="first")
    nf = f3.notna().sum(axis=1).to_numpy()[:, None]
    squeeze = C > H.shift(1).rolling(10).max()
    pos_fc_d = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    pos_fc_d[(rkf <= 3) & (f3 > 0.0002) & (~squeeze) & (nf >= 10)] = -1.0
    pos_fc_d[(rkf >= nf - 2) & (f3 < 0.0001) & (nf >= 10)] = 1.0
    w_fc_daily = _normalize_active_neutral(pos_fc_d, inv_vol, max_w=0.20)
    w_fc_stag = _stagger_weights(w_fc_daily, E_hyst, 3)

    weights_map = {
        "ABL_Claude_XSMOM_Bug": w_cl_bug,
        "ABL_XSMOM_ActiveLeg_Clean": w_xs_fixed,
        "ABL_Donchian_20_10": w_don_cl,
        "CR2_TSMOM_Blend_1D": w_ts,
        "CR2_Donchian_30_15": w_don30,
        "CR2_XSMOM_Stag5d": w_xs5_stag,
        "CR2_ResidMom_Stag5d": w_res_stag,
        "CR2_Funding_Carry_Stag3d": w_fc_stag,
    }

    idx_eval = C.index[(C.index >= "2021-01-01") & (C.index < CORTE)]
    blq = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in idx_eval], index=idx_eval)
    assert not blq.isin(["TERMINAL"]).any(), "TERMINAL breach!"
    mask_dr = blq.isin(["DESC", "REP"])
    btc_eval = btc.reindex(idx_eval).fillna(0.0)

    def _extras(s: pd.Series) -> dict:
        sd_r = s[mask_dr]
        bt_r = btc_eval[mask_dr]
        corr_b = round(float(sd_r.corr(bt_r)), 3) if sd_r.std(ddof=1) > 0 and bt_r.std(ddof=1) > 0 else 0.0
        # Return per $10k capital vs BTC return
        beta_b = round(float((sd_r / 10_000.0).cov(bt_r) / max(bt_r.var(), 1e-12)), 3)
        tot = float(sd_r.sum())
        top5 = float(sd_r.nlargest(5).sum())
        top5_share = round(top5 / tot, 3) if tot > 1e-6 else None
        yearly = {str(k): round(float(v), 1) for k, v in sd_r.groupby(sd_r.index.year).sum().items()}
        return {"corr_BTC": corr_b, "beta_BTC": beta_b, "top5_days_share": top5_share, "yearly_usd": yearly}

    results = {
        "n_ascii_pit_coins_loaded": len(bars),
        "tradfi_excluded_count": len(TRADFI_EXCLUDE),
        "costs_tested_bps": [10, 20, 30, 40],
        "rules": {},
    }
    base_series = pd.DataFrame(index=idx_eval)

    print("\n=== RESULTADOS CRIPTO-PIT v2 AUDITADA (ex-TradFi, Stag, 20 bps + funding, SOLO DESC & REP) ===")
    for name, W in weights_map.items():
        results["rules"][name] = {}
        for bps in (10, 20, 30, 40):
            s_raw, s_stress_raw, turn_m, delist_hits = _pnl(C, W, F, bps / 10_000.0, r_override=r_safe)
            s = s_raw.reindex(idx_eval).fillna(0.0)
            s_stress = s_stress_raw.reindex(idx_eval).fillna(0.0)
            entry = {
                "DESC": stats_serie(s[blq == "DESC"]),
                "REP": stats_serie(s[blq == "REP"]),
                "DESC_REP": stats_serie(s[mask_dr]),
            }
            if bps == 20:
                base_series[name] = s
                results["rules"][name]["turnover_x_mes"] = turn_m
                results["rules"][name]["delist_hits"] = delist_hits
                entry["DESC_REP_22_26"] = stats_serie(s[mask_dr & (idx_eval >= "2022-01-01")])
                entry["DESC_REP_shock30"] = stats_serie(s_stress[mask_dr])
                entry.update(_extras(s))
            results["rules"][name][f"bps_{bps}"] = entry
        b20 = results["rules"][name]["bps_20"]
        print(
            f"  {name:26s} | turn={results['rules'][name]['turnover_x_mes']:4.1f}x | "
            f"DESC t={b20['DESC']['t_mes']:5.2f} | REP t={b20['REP']['t_mes']:5.2f} | "
            f"DR Sh={b20['DESC_REP']['sharpe']:4.2f} t={b20['DESC_REP']['t_mes']:4.2f} | "
            f"22-26 Sh={b20['DESC_REP_22_26']['sharpe']:4.2f} | top5={b20['top5_days_share']} | dh={results['rules'][name]['delist_hits']}"
        )

    # Diagnostic xsmom_audit: 5 individual phases + Long/Short/BTC decomp + Top10_liq
    phase_audit = {}
    for off in range(5):
        w_ph = w_xs5_daily.iloc[off::5].reindex(C.index).ffill().fillna(0.0).where(E_hyst, 0.0)
        s_ph_raw, _, _, dh_ph = _pnl(C, w_ph, F, 20 / 10_000.0, r_override=r_safe)
        s_ph = s_ph_raw.reindex(idx_eval).fillna(0.0)
        phase_audit[f"Phase_{off}"] = {
            "DESC_REP": stats_serie(s_ph[mask_dr]),
            "REP": stats_serie(s_ph[blq == "REP"]),
            "DESC_REP_22_26": stats_serie(s_ph[mask_dr & (idx_eval >= "2022-01-01")]),
            "delist_hits": dh_ph,
        }

    def _decomp(E_uni: pd.DataFrame, sc_df: pd.DataFrame, nleg: int) -> dict:
        rk = sc_df.rank(axis=1, ascending=False, method="first")
        nn = sc_df.notna().sum(axis=1).to_numpy()[:, None]
        pl = pd.DataFrame(0.0, index=C.index, columns=C.columns)
        pl[(rk <= nleg) & (nn >= 2 * nleg + 2)] = 1.0
        ps = pd.DataFrame(0.0, index=C.index, columns=C.columns)
        ps[(rk >= nn - nleg + 1) & (nn >= 2 * nleg + 2)] = 1.0
        lw = (pl * inv_vol).clip(upper=0.20)
        lw = lw.div(lw.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0) * 0.5
        sw = (ps * inv_vol).clip(upper=0.20)
        sw = sw.div(sw.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0) * 0.5
        both = (lw.sum(axis=1) > 0) & (sw.sum(axis=1) > 0)
        w_ls = lw - sw
        w_ls[~both] = 0.0
        w_lo = lw.copy()
        w_lo[~both] = 0.0
        w_so = -sw.copy()
        w_so[~both] = 0.0
        w_lbtc = w_lo.copy()
        if "BTCUSDT" in w_lbtc.columns:
            w_lbtc["BTCUSDT"] = w_lbtc["BTCUSDT"] - 0.5 * both.astype(float)
        out_d = {}
        for lbl, Wraw in [("Long-Short_Alts", w_ls), ("Long-Only_Alts", w_lo), ("Short-Only_Alts", w_so), ("LongAlts-ShortBTC", w_lbtc)]:
            ws = _stagger_weights(Wraw, E_uni, 5)
            sr, s_st, tm, dh = _pnl(C, ws, F, 20 / 10_000.0, r_override=r_safe)
            se = sr.reindex(idx_eval).fillna(0.0)
            st = stats_serie(se[mask_dr])
            st["REP_sh"] = stats_serie(se[blq == "REP"])["sharpe"]
            st["22_26_sh"] = stats_serie(se[mask_dr & (idx_eval >= "2022-01-01")])["sharpe"]
            st["delist_hits"] = dh
            st["shock30_sh"] = stats_serie(s_st.reindex(idx_eval).fillna(0.0)[mask_dr])["sharpe"]
            st.update(_extras(se))
            out_d[lbl] = st
        return out_d

    E10 = build_eligibility(C.index, C.columns, u, top_k=10, hysteresis_exit=15) & live60
    results["xsmom_audit"] = {
        "phases_frozen_5d_Top20": phase_audit,
        "decomp_Top20_hyst_4L4S": _decomp(E_hyst, sc21, 4),
        "decomp_Top10_liq_3L3S": _decomp(E10, (ret_21 / vol1).where(E10), 3),
    }

    # Causal baskets (1/sd fit STRICTLY on DESC)
    v2_cols = ["CR2_TSMOM_Blend_1D", "CR2_XSMOM_Stag5d", "CR2_ResidMom_Stag5d", "CR2_Funding_Carry_Stag3d"]
    alive_desc = [c for c in v2_cols if results["rules"][c]["bps_20"]["DESC"]["usd_mes"] > 0]
    m_desc = base_series.loc[blq == "DESC", alive_desc].groupby(base_series.loc[blq == "DESC"].index.to_period("M")).sum()
    sd_d = m_desc.std(ddof=1).replace(0.0, np.nan).fillna(1.0)
    w_bask = (1.0 / sd_d) / (1.0 / sd_d).sum()
    bask = (base_series[alive_desc] * w_bask).sum(axis=1)
    bask_1n = base_series[alive_desc].mean(axis=1)

    core_cols = ["CR2_XSMOM_Stag5d", "CR2_ResidMom_Stag5d"]
    m_core_d = base_series.loc[blq == "DESC", core_cols].groupby(base_series.loc[blq == "DESC"].index.to_period("M")).sum()
    sd_core = m_core_d.std(ddof=1).replace(0.0, np.nan).fillna(1.0)
    w_core = (1.0 / sd_core) / (1.0 / sd_core).sum()
    bask_core = (base_series[core_cols] * w_core).sum(axis=1)

    base_series["CR2_Canasta_InvVol"] = bask
    base_series["CR2_Core_XSMOM_ResidMom"] = bask_core
    base_series["CR2_Canasta_1N"] = bask_1n

    # Save strictly sealed (NaN outside DESC+REP!)
    save_dr = base_series.copy()
    save_dr.loc[~mask_dr] = np.nan
    save_dr.to_csv(OUT / "SERIES_CRIPTO_PIT_V2_DR.csv.gz")

    def _full_bask(s: pd.Series) -> dict:
        out = {
            "DESC": stats_serie(s[blq == "DESC"]),
            "REP": stats_serie(s[blq == "REP"]),
            "DESC_REP": stats_serie(s[mask_dr]),
            "DESC_REP_22_26": stats_serie(s[mask_dr & (idx_eval >= "2022-01-01")]),
        }
        out.update(_extras(s))
        return out

    results["basket_alive_DESC"] = alive_desc
    results["basket_inv_vol_weights_DESC"] = {k: round(float(v), 4) for k, v in w_bask.items()}
    results["core_inv_vol_weights_DESC"] = {k: round(float(v), 4) for k, v in w_core.items()}
    results["CR2_Canasta_InvVol_bps20"] = _full_bask(bask)
    results["CR2_Core_XSMOM_ResidMom_bps20"] = _full_bask(bask_core)
    results["CR2_Canasta_1N_bps20"] = _full_bask(bask_1n)

    print("\n=== CANASTAS CRIPTO-PIT v2 AUDITADA (1/sd DESC, 20 bps + funding real) ===")
    print("  Vivas DESC :", alive_desc, "pesos:", results["basket_inv_vol_weights_DESC"])
    print("  Canasta InvVol :", results["CR2_Canasta_InvVol_bps20"]["DESC_REP"], "| top5=", results["CR2_Canasta_InvVol_bps20"]["top5_days_share"])
    print("  Core XSMOM+Resid:", results["CR2_Core_XSMOM_ResidMom_bps20"]["DESC_REP"], "| pesos=", results["core_inv_vol_weights_DESC"], "| top5=", results["CR2_Core_XSMOM_ResidMom_bps20"]["top5_days_share"])

    (OUT / "CRIPTO_PIT_V2.json").write_text(json.dumps(results, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("Saved:", OUT / "CRIPTO_PIT_V2.json")


if __name__ == "__main__":
    main()

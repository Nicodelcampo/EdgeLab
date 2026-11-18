"""Indicadores estrictamente causales (0..i) y helpers compartidos para las estrategias traducidas del catálogo externo."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd


def extraer_arrays(barras: pd.DataFrame) -> tuple[np.ndarray, ...]:
    """Extrae arreglos NumPy contiguos (ts, o, h, l, c, v, ses) desde un DataFrame de barras M1."""
    ts = barras["ts"].to_numpy(np.int64)
    o = barras["o"].to_numpy(np.float64)
    h = barras["h"].to_numpy(np.float64)
    l = barras["l"].to_numpy(np.float64)
    c = barras["c"].to_numpy(np.float64)
    v = barras["v"].to_numpy(np.float64) if "v" in barras.columns else np.ones(len(c), dtype=np.float64)
    ses = barras["ses"].to_numpy(np.int64)
    return ts, o, h, l, c, v, ses


def sma(x: np.ndarray, period: int) -> np.ndarray:
    """Media móvil simple causal; en las primeras barras usa la ventana disponible."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    p = max(1, int(period))
    cs = np.cumsum(x)
    for i in range(n):
        if i < p:
            out[i] = cs[i] / (i + 1)
        else:
            out[i] = (cs[i] - cs[i - p]) / p
    return out


def ema(x: np.ndarray, period: int) -> np.ndarray:
    """Media móvil exponencial causal estándar (alpha = 2 / (period + 1))."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    alpha = 2.0 / (max(1, int(period)) + 1.0)
    out[0] = x[0]
    for i in range(1, n):
        out[i] = alpha * x[i] + (1.0 - alpha) * out[i - 1]
    return out


def rma(x: np.ndarray, period: int) -> np.ndarray:
    """Media móvil de Wilder causal (alpha = 1 / period)."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    alpha = 1.0 / max(1, int(period))
    out[0] = x[0]
    for i in range(1, n):
        out[i] = alpha * x[i] + (1.0 - alpha) * out[i - 1]
    return out


def wma(x: np.ndarray, period: int) -> np.ndarray:
    """Media móvil ponderada lineal causal."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    p = max(1, int(period))
    pesos_full = np.arange(1, p + 1, dtype=np.float64)
    denom_full = pesos_full.sum()
    for i in range(n):
        k = min(i + 1, p)
        w = pesos_full[-k:] if k < p else pesos_full
        den = w.sum() if k < p else denom_full
        out[i] = float(np.dot(x[i - k + 1 : i + 1], w) / den)
    return out


def hma(x: np.ndarray, period: int) -> np.ndarray:
    """Hull Moving Average causal."""
    p = max(2, int(period))
    half = max(1, p // 2)
    sq = max(1, int(round(math.sqrt(p))))
    return wma(2.0 * wma(x, half) - wma(x, p), sq)


def tema(x: np.ndarray, period: int) -> np.ndarray:
    """Triple Exponential Moving Average causal."""
    e1 = ema(x, period)
    e2 = ema(e1, period)
    e3 = ema(e2, period)
    return 3.0 * e1 - 3.0 * e2 + e3


def true_range(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    """True Range causal."""
    n = len(c)
    tr = np.empty(n, dtype=np.float64)
    if n == 0:
        return tr
    tr[0] = max(float(h[0] - l[0]), 1e-9)
    for i in range(1, n):
        hl = h[i] - l[i]
        hc = abs(h[i] - c[i - 1])
        lc = abs(l[i] - c[i - 1])
        tr[i] = max(hl, hc, lc, 1e-9)
    return tr


def atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, period: int = 14, usar_rma: bool = True) -> np.ndarray:
    """Average True Range causal (RMA de Wilder o SMA)."""
    tr = true_range(h, l, c)
    return rma(tr, period) if usar_rma else sma(tr, period)


def rsi(c: np.ndarray, period: int = 14) -> np.ndarray:
    """RSI de Wilder estrictamente causal en rango [0, 100]."""
    c = np.asarray(c, dtype=np.float64)
    n = len(c)
    out = np.full(n, 50.0, dtype=np.float64)
    if n < 2:
        return out
    diff = np.zeros(n, dtype=np.float64)
    diff[1:] = np.diff(c)
    gains = np.where(diff > 0.0, diff, 0.0)
    losses = np.where(diff < 0.0, -diff, 0.0)
    avg_g = rma(gains, period)
    avg_l = rma(losses, period)
    for i in range(1, n):
        if avg_l[i] <= 1e-12:
            out[i] = 100.0 if avg_g[i] > 1e-12 else 50.0
        else:
            rs = avg_g[i] / avg_l[i]
            out[i] = 100.0 - (100.0 / (1.0 + rs))
    return out


def mfi(h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray, period: int = 14) -> np.ndarray:
    """Money Flow Index causal; maneja volumen positivo uniforme sin dividir por cero."""
    n = len(c)
    out = np.full(n, 50.0, dtype=np.float64)
    if n < 2:
        return out
    tp = (h + l + c) / 3.0
    vol = np.where(v > 0.0, v, 1.0)
    rmf = tp * vol
    pos = np.zeros(n, dtype=np.float64)
    neg = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        if tp[i] > tp[i - 1]:
            pos[i] = rmf[i]
        elif tp[i] < tp[i - 1]:
            neg[i] = rmf[i]
    p = max(1, int(period))
    cs_pos = np.cumsum(pos)
    cs_neg = np.cumsum(neg)
    for i in range(1, n):
        j0 = i - p
        sp = cs_pos[i] - (cs_pos[j0] if j0 >= 0 else 0.0)
        sn = cs_neg[i] - (cs_neg[j0] if j0 >= 0 else 0.0)
        if sn <= 1e-12:
            out[i] = 100.0 if sp > 1e-12 else 50.0
        else:
            out[i] = 100.0 - (100.0 / (1.0 + sp / sn))
    return out


def cci(h: np.ndarray, l: np.ndarray, c: np.ndarray, period: int = 20) -> np.ndarray:
    """Commodity Channel Index causal."""
    n = len(c)
    out = np.zeros(n, dtype=np.float64)
    if n == 0:
        return out
    tp = (h + l + c) / 3.0
    ma = sma(tp, period)
    p = max(1, int(period))
    for i in range(1, n):
        start = max(0, i - p + 1)
        win = tp[start : i + 1]
        md = float(np.mean(np.abs(win - ma[i])))
        if md > 1e-12:
            out[i] = (tp[i] - ma[i]) / (0.015 * md)
    return out


def stoch_f(h: np.ndarray, l: np.ndarray, c: np.ndarray, k_period: int = 14, d_period: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Fast Stochastic (%K, %D) causal."""
    n = len(c)
    fk = np.full(n, 50.0, dtype=np.float64)
    p = max(1, int(k_period))
    for i in range(n):
        start = max(0, i - p + 1)
        hi = float(np.max(h[start : i + 1]))
        lo = float(np.min(l[start : i + 1]))
        if hi - lo > 1e-12:
            fk[i] = 100.0 * (c[i] - lo) / (hi - lo)
    fd = sma(fk, d_period)
    return fk, fd


def adx_di(h: np.ndarray, l: np.ndarray, c: np.ndarray, adx_period: int = 14, di_period: int | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """ADX, +DI y -DI de Wilder estrictamente causales."""
    n = len(c)
    dp_len = adx_period if di_period is None else di_period
    plus_dm = np.zeros(n, dtype=np.float64)
    minus_dm = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        up = h[i] - h[i - 1]
        dn = l[i - 1] - l[i]
        if up > dn and up > 0.0:
            plus_dm[i] = up
        if dn > up and dn > 0.0:
            minus_dm[i] = dn
    tr_di = rma(true_range(h, l, c), dp_len)
    pdi = 100.0 * rma(plus_dm, dp_len) / np.maximum(tr_di, 1e-12)
    mdi = 100.0 * rma(minus_dm, dp_len) / np.maximum(tr_di, 1e-12)
    dx = 100.0 * np.abs(pdi - mdi) / np.maximum(pdi + mdi, 1e-12)
    adx = rma(dx, adx_period)
    return adx, pdi, mdi


def bollinger(x: np.ndarray, period: int = 20, mult: float = 2.0) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Bandas de Bollinger causales: retorna (mid, upper, lower, stdev)."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    mid = sma(x, period)
    std = np.zeros(n, dtype=np.float64)
    p = max(2, int(period))
    for i in range(n):
        start = max(0, i - p + 1)
        win = x[start : i + 1]
        if len(win) > 1:
            std[i] = float(np.std(win, ddof=0))
    upper = mid + mult * std
    lower = mid - mult * std
    return mid, upper, lower, std


def donchian_prev(h: np.ndarray, l: np.ndarray, period: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Canal Donchian causal basado en las `period` barras previas [i-period .. i-1]."""
    n = len(h)
    hi_prev = np.full(n, np.nan, dtype=np.float64)
    lo_prev = np.full(n, np.nan, dtype=np.float64)
    p = max(1, int(period))
    for i in range(1, n):
        start = max(0, i - p)
        hi_prev[i] = float(np.max(h[start:i]))
        lo_prev[i] = float(np.min(l[start:i]))
    return hi_prev, lo_prev


def supertrend(h: np.ndarray, l: np.ndarray, c: np.ndarray, period: int = 10, mult: float = 3.0) -> tuple[np.ndarray, np.ndarray]:
    """Supertrend causal: retorna (st_line, trend_dir en {+1, -1})."""
    n = len(c)
    st = np.empty(n, dtype=np.float64)
    tdir = np.ones(n, dtype=np.int64)
    if n == 0:
        return st, tdir
    atr_v = atr(h, l, c, period, usar_rma=True)
    hl2 = 0.5 * (h + l)
    up_basic = hl2 + mult * atr_v
    dn_basic = hl2 - mult * atr_v
    up_fin = np.copy(up_basic)
    dn_fin = np.copy(dn_basic)
    st[0] = dn_fin[0]
    for i in range(1, n):
        dn_fin[i] = max(dn_basic[i], dn_fin[i - 1]) if c[i - 1] > dn_fin[i - 1] else dn_basic[i]
        up_fin[i] = min(up_basic[i], up_fin[i - 1]) if c[i - 1] < up_fin[i - 1] else up_basic[i]
        if tdir[i - 1] == 1:
            if c[i] < dn_fin[i - 1]:
                tdir[i] = -1
                st[i] = up_fin[i]
            else:
                tdir[i] = 1
                st[i] = dn_fin[i]
        else:
            if c[i] > up_fin[i - 1]:
                tdir[i] = 1
                st[i] = dn_fin[i]
            else:
                tdir[i] = -1
                st[i] = up_fin[i]
    return st, tdir


def ehlers_gaussian_filter(x: np.ndarray, period: int = 14, poles: int = 4) -> np.ndarray:
    """Filtro recursivo Gaussiano multipolo de Ehlers (causal, equivalente a Gaussian Channel DW)."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    if n == 0:
        return np.copy(x)
    p = max(2, int(period))
    pol = max(1, min(9, int(poles)))
    beta = (1.0 - math.cos(2.0 * math.pi / p)) / (math.pow(1.414213562, 2.0 / pol) - 1.0)
    alpha = -beta + math.sqrt(beta * beta + 2.0 * beta)
    one_minus = 1.0 - alpha

    cur = np.copy(x)
    for _ in range(pol):
        nxt = np.empty(n, dtype=np.float64)
        nxt[0] = cur[0]
        for i in range(1, n):
            nxt[i] = alpha * cur[i] + one_minus * nxt[i - 1]
        cur = nxt
    return cur


def wavetrend(h: np.ndarray, l: np.ndarray, c: np.ndarray, n1: int = 10, n2: int = 21) -> tuple[np.ndarray, np.ndarray]:
    """WaveTrend [LazyBear] estrictamente causal."""
    ap = (h + l + c) / 3.0
    esa = ema(ap, n1)
    d = ema(np.abs(ap - esa), n1)
    ci = (ap - esa) / np.maximum(0.015 * d, 1e-12)
    wt1 = ema(ci, n2)
    wt2 = sma(wt1, 4)
    return wt1, wt2


def fisher_transform(h: np.ndarray, l: np.ndarray, period: int = 10) -> tuple[np.ndarray, np.ndarray]:
    """Fisher Transform causal; retorna (fisher, fisher_prev)."""
    n = len(h)
    fish = np.zeros(n, dtype=np.float64)
    fish_prev = np.zeros(n, dtype=np.float64)
    hl2 = 0.5 * (h + l)
    p = max(2, int(period))
    val = 0.0
    for i in range(1, n):
        start = max(0, i - p + 1)
        hi = float(np.max(hl2[start : i + 1]))
        lo = float(np.min(hl2[start : i + 1]))
        rng = max(hi - lo, 1e-9)
        raw = 0.33 * 2.0 * ((hl2[i] - lo) / rng - 0.5) + 0.67 * val
        val = max(-0.999, min(0.999, raw))
        fish_prev[i] = fish[i - 1]
        fish[i] = 0.5 * math.log((1.0 + val) / (1.0 - val)) + 0.5 * fish[i - 1]
    return fish, fish_prev


def aroon_osc(h: np.ndarray, l: np.ndarray, period: int = 25) -> np.ndarray:
    """Aroon Oscillator causal en [-100, 100]."""
    n = len(h)
    osc = np.zeros(n, dtype=np.float64)
    p = max(2, int(period))
    for i in range(p, n):
        win_h = h[i - p : i + 1]
        win_l = l[i - p : i + 1]
        bars_since_hi = p - int(np.argmax(win_h))
        bars_since_lo = p - int(np.argmin(win_l))
        aroon_up = 100.0 * (p - bars_since_hi) / p
        aroon_dn = 100.0 * (p - bars_since_lo) / p
        osc[i] = aroon_up - aroon_dn
    return osc


def parabolic_sar(h: np.ndarray, l: np.ndarray, c: np.ndarray, af_step: float = 0.02, af_max: float = 0.20) -> tuple[np.ndarray, np.ndarray]:
    """Parabolic SAR causal; retorna (sar, trend_dir en {+1, -1})."""
    n = len(c)
    sar = np.empty(n, dtype=np.float64)
    tdir = np.ones(n, dtype=np.int64)
    if n == 0:
        return sar, tdir
    sar[0] = l[0]
    ep = h[0]
    af = af_step
    for i in range(1, n):
        prev_dir = tdir[i - 1]
        cand = sar[i - 1] + af * (ep - sar[i - 1])
        if prev_dir == 1:
            cand = min(cand, l[i - 1], l[max(0, i - 2)])
            if l[i] < cand:
                tdir[i] = -1
                sar[i] = ep
                ep = l[i]
                af = af_step
            else:
                tdir[i] = 1
                sar[i] = cand
                if h[i] > ep:
                    ep = h[i]
                    af = min(af_max, af + af_step)
        else:
            cand = max(cand, h[i - 1], h[max(0, i - 2)])
            if h[i] > cand:
                tdir[i] = 1
                sar[i] = ep
                ep = h[i]
                af = af_step
            else:
                tdir[i] = -1
                sar[i] = cand
                if l[i] < ep:
                    ep = l[i]
                    af = min(af_max, af + af_step)
    return sar, tdir


def kalman_1d(x: np.ndarray, q: float = 1e-4, r: float = 1e-2, z_win: int = 30) -> tuple[np.ndarray, np.ndarray]:
    """Filtro de Kalman escalar 1D causal y Z-score rodante del residuo."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    est = np.empty(n, dtype=np.float64)
    z = np.zeros(n, dtype=np.float64)
    if n == 0:
        return est, z
    x_hat = float(x[0])
    p_cov = 1.0
    resid = np.zeros(n, dtype=np.float64)
    for i in range(n):
        p_pred = p_cov + q
        k_gain = p_pred / (p_pred + r)
        innov = x[i] - x_hat
        x_hat = x_hat + k_gain * innov
        p_cov = (1.0 - k_gain) * p_pred
        est[i] = x_hat
        resid[i] = innov
        if i >= 5:
            start = max(0, i - z_win + 1)
            sd = float(np.std(resid[start : i + 1]))
            if sd > 1e-12:
                z[i] = innov / sd
    return est, z


def vwap_sesion(h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray, ses: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """VWAP y desviación estándar ponderada por volumen, acumulados causalmente por sesión."""
    n = len(c)
    vwap = np.empty(n, dtype=np.float64)
    sd = np.zeros(n, dtype=np.float64)
    if n == 0:
        return vwap, sd
    tp = (h + l + c) / 3.0
    vol = np.where(v > 0.0, v, 1.0)
    sum_v = 0.0
    sum_pv = 0.0
    sum_p2v = 0.0
    for i in range(n):
        if i == 0 or ses[i] != ses[i - 1]:
            sum_v = 0.0
            sum_pv = 0.0
            sum_p2v = 0.0
        sum_v += vol[i]
        sum_pv += tp[i] * vol[i]
        sum_p2v += (tp[i] * tp[i]) * vol[i]
        mu = sum_pv / max(sum_v, 1e-12)
        var = max(0.0, (sum_p2v / max(sum_v, 1e-12)) - mu * mu)
        vwap[i] = mu
        sd[i] = math.sqrt(var)
    return vwap, sd


def linreg_slope(x: np.ndarray, period: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Regresión lineal rodante causal (valor final de la recta y pendiente por barra)."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    val = np.copy(x)
    slope = np.zeros(n, dtype=np.float64)
    p = max(2, int(period))
    t_idx = np.arange(p, dtype=np.float64)
    t_mean = t_idx.mean()
    t_var = float(np.sum((t_idx - t_mean) ** 2))
    for i in range(p - 1, n):
        y = x[i - p + 1 : i + 1]
        y_mean = float(np.mean(y))
        m = float(np.sum((t_idx - t_mean) * (y - y_mean)) / t_var)
        b = y_mean - m * t_mean
        slope[i] = m
        val[i] = m * (p - 1) + b
    return val, slope


def emitir_espaciadas(
    ts: np.ndarray,
    ses: np.ndarray,
    indices: list[int] | np.ndarray,
    dirs: list[int] | np.ndarray,
    atr_arr: np.ndarray,
    mult_tp: float = 2.0,
    mult_sl: float = 1.0,
    cooldown_bars: int = 15,
    time_stop_min: int = 180,
) -> list[dict]:
    """Convierte índices y direcciones candidatos en señales para `analizador.py` con enfriamiento causal."""
    out: list[dict] = []
    ultimo_i = -10**9
    ultimo_ses = None
    for idx_raw, d_raw in zip(indices, dirs):
        i = int(idx_raw)
        d = int(d_raw)
        if d not in (1, -1):
            continue
        cur_ses = int(ses[i])
        if ultimo_ses == cur_ses and (i - ultimo_i) < cooldown_bars:
            continue
        a = float(atr_arr[i])
        if not np.isfinite(a) or a <= 0.0:
            a = 1.0
        tgt = max(float(mult_tp) * a, 0.5)
        stp = max(float(mult_sl) * a, 0.5)
        out.append(
            dict(
                available_at=int(ts[i]),
                dir=d,
                target_pts=tgt,
                stop_pts=stp,
                time_stop_min=int(time_stop_min),
            )
        )
        ultimo_i = i
        ultimo_ses = cur_ses
    return out

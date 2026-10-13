"""Zonas de tendencia estable respecto de una EMA: (1) ubicar en barras reales las zonas que el usuario marcó en capturas (coincidencia de plantillas digitalizadas) y
(2) detectores causales parametrizables + métricas de recall/frecuencia para calibrarlos contra esas zonas. Sin P&L: es detección de régimen, no evidencia de edge."""
from __future__ import annotations

import numpy as np


def ema(x: np.ndarray, n: int) -> np.ndarray:
    a = 2.0 / (n + 1); out = np.empty(len(x)); out[0] = x[0]
    for i in range(1, len(x)): out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def _fill(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, float); ok = ~np.isnan(a)
    return np.interp(np.arange(len(a)), np.flatnonzero(ok), a[ok]) if ok.any() else a


def _roll_stats(x: np.ndarray, L: int):
    c1 = np.r_[0.0, np.cumsum(x)]; c2 = np.r_[0.0, np.cumsum(x * x)]
    m = (c1[L:] - c1[:-L]) / L; v = np.maximum((c2[L:] - c2[:-L]) / L - m * m, 1e-18)
    return m, np.sqrt(v)


def _boxc(x, k):
    c = np.r_[0.0, np.cumsum(x)]; h = k // 2; idx = np.arange(len(x)); lo = np.clip(idx - h, 0, len(x)); hi = np.clip(idx - h + k, 0, len(x))
    return (c[hi] - c[lo]) / np.maximum(hi - lo, 1)


def _slide_corr(series: np.ndarray, tz: np.ndarray) -> np.ndarray:
    """Pearson entre `tz` (media 0, desvío 1, largo L) y cada ventana de `series` (largo L)."""
    L = len(tz); n = len(series); N = 1 << int(np.ceil(np.log2(n + L)))
    cc = np.fft.irfft(np.fft.rfft(series, N) * np.conj(np.fft.rfft(tz, N)), N)[: n - L + 1]
    m, s = _roll_stats(series, L)
    return cc / (L * s)


def template_arrays(t: dict):
    hi, lo, em = _fill(t["hi"]), _fill(t["lo"]), _fill(t["ema"])
    price = -(hi + lo) / 2.0; e = -em
    return price, e, price - e


def match(t: dict, mid: np.ndarray, e_bars: np.ndarray, scales=None, topk=3):
    """Busca la plantilla en la serie de barras (mid = (H+L)/2 en ticks, e_bars = EMA). Devuelve las mejores coincidencias (inicio de barra, barras por píxel, puntaje)
    con su margen sobre la mejor coincidencia no solapada. Puntaje = media de la correlación de precio, de precio−EMA y de la forma de la EMA."""
    price, e, d = template_arrays(t); W = len(price); D = mid - e_bars
    scales = np.geomspace(0.35, 6.0, 30) if scales is None else scales; res = []
    for s in scales:
        L = int(round(W * s))
        if L < 60 or L >= len(mid): continue
        x = (np.arange(L) + 0.5) / s - 0.5; sc = {}; k = max(3, int(round(6 * s)))                 # detalle fino: precio menos su media móvil de ~6 px (no sobrevive a una escala equivocada)
        for name, tmpl, ser in (("p", price, mid), ("d", d, D), ("e", e, e_bars)):
            tt = np.interp(x, np.arange(W), tmpl); tt = (tt - tt.mean()) / (tt.std() + 1e-12); sc[name] = _slide_corr(ser, tt)
        tt = np.interp(x, np.arange(W), price); tt = tt - _boxc(tt, k); tt = (tt - tt.mean()) / (tt.std() + 1e-12); sc["h"] = _slide_corr(mid - _boxc(mid, k), tt)
        S = 0.5 * sc["h"] + 0.2 * sc["p"] + 0.15 * sc["d"] + 0.15 * sc["e"]
        for i in np.argsort(-S)[: topk * 40]: res.append((float(S[i]), int(i), float(s), int(L), float(sc["p"][i]), float(sc["d"][i]), float(sc["e"][i]), float(sc["h"][i])))
    res.sort(reverse=True); out = []
    for r in res:
        if all(abs(r[1] - o["start"]) > 0.5 * min(r[3], o["L"]) for o in out):
            out.append(dict(score=r[0], start=r[1], bars_per_px=r[2], L=r[3], corr_price=r[4], corr_detr=r[5], corr_ema=r[6], corr_fine=r[7]))
        if len(out) >= topk + 1: break
    for o in out: o["margin_vs_next"] = None
    for k in range(len(out) - 1): out[k]["margin_vs_next"] = out[k]["score"] - out[k + 1]["score"]
    return out[:topk]


def target_range(t: dict, m: dict):
    """Rango de barras [a, b] de la línea azul del usuario dentro de la coincidencia m."""
    b = t["blue"]; s = m["bars_per_px"]
    return int(m["start"] + b["x0"] * s), int(m["start"] + b["x1"] * s)


# ---------------- detector causal parametrizable ----------------
EXPANDING = False        # True: en las primeras barras la ventana se achica (para evaluar sobre recortes que no traen historia previa)


def _rmean(x, L):
    c = np.r_[0.0, np.cumsum(x)]
    if EXPANDING:
        idx = np.arange(len(x)); lo = np.maximum(idx + 1 - L, 0); return (c[idx + 1] - c[lo]) / (idx + 1 - lo)
    out = np.full(len(x), np.nan); out[L - 1:] = (c[L:] - c[:-L]) / L
    return out


def precompute(close, high, low, ema_n=200, atr_n=100, e=None):
    e = ema(close.astype(float), ema_n) if e is None else np.asarray(e, float); tr = np.maximum(high - low, 1e-9); atr = _rmean(tr, atr_n)
    return dict(c=close.astype(float), e=e, atr=atr, g=close - e)


def state(P, M=150, K=100, f=0.9, er=0.5, dmin=0.0, cv=0.0, hold=0, drift_atr=0.0):
    """+1/−1/0 causal. Condiciones en ventana de M barras: EMA direccional en K barras (eficiencia ≥ er y desplazamiento ≥ drift_atr·ATR·√K),
    fracción de barras del lado de la tendencia ≥ f, distancia media ≥ dmin·ATR, y (si cv>0) desvío de la distancia / media ≤ cv. `hold` mantiene el estado tantas barras tras dejar de cumplirse."""
    c, e, atr, g = P["c"], P["e"], P["atr"], P["g"]; n = len(c); de = np.abs(np.diff(e, prepend=e[0]))
    disp = np.full(n, np.nan); disp[K:] = e[K:] - e[:-K]
    if EXPANDING: disp[:K] = e[:K] - e[0]
    sumde = _rmean(de, K) * K
    dire = np.sign(np.nan_to_num(disp)); eff = np.abs(np.nan_to_num(disp)) / np.maximum(sumde, 1e-12)
    up = _rmean((g > 0).astype(float), M); dn = _rmean((g < 0).astype(float), M); mu = _rmean(g, M)
    ok = (eff >= er) & (np.abs(np.nan_to_num(disp)) >= drift_atr * atr * np.sqrt(K)) & (np.abs(np.nan_to_num(mu)) >= dmin * atr)
    if cv > 0:
        sd = np.sqrt(np.maximum(_rmean(g * g, M) - mu * mu, 0)); ok &= (sd / np.maximum(np.abs(mu), 1e-9) <= cv)
    cu = ok & (dire > 0) & (np.nan_to_num(up) >= f) & (np.nan_to_num(mu) > 0); cd = ok & (dire < 0) & (np.nan_to_num(dn) >= f) & (np.nan_to_num(mu) < 0)
    if hold > 0:
        def hold_on(b):
            cs = np.r_[0, np.cumsum(b.astype(int))]; idx = np.arange(n); lo = np.maximum(idx + 1 - hold, 0); return (cs[idx + 1] - cs[lo]) > 0
        cu, cd = hold_on(cu), hold_on(cd)
    return np.where(cu, 1, np.where(cd, -1, 0)).astype(np.int8)


def score(st, targets):
    """targets: lista de (a, b, dir). recall causal = fracción de barras del objetivo con estado == dir; detección = fracción del objetivo transcurrida hasta el primer estado correcto."""
    rec, det = [], []
    for a, b, d in targets:
        a, b = max(a, 0), min(b, len(st) - 1); seg = st[a:b + 1] == d; rec.append(float(seg.mean()))
        det.append(float(np.argmax(seg) / max(len(seg), 1)) if seg.any() else 1.0)
    return dict(recall=rec, recall_mean=float(np.mean(rec)), detect_frac=det, flagged=float((st != 0).mean()), n_segments=int(((st != 0) & (np.r_[0, st[:-1]] == 0)).sum()))

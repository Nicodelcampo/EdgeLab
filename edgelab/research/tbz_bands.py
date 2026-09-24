"""Familia TBZ, etapa E1 (target-free): construcción de franjas de baja permanencia.

Protocolo congelado: `docs/research/FAMILIA_TBZ_FRANJAS_BAJA_PERMANENCIA_20260924.md`.

- `expansion_bands`: variante TBZ-EXP, franjas que deja una expansión rápida A->B (evento causal).
- `dwell_bands`: variante TBZ-DWELL, huecos de permanencia dentro del rango recién negociado (estado cada 5 min).
- `overlap_ratio_vs_null`: solapamiento entre conjuntos de franjas contra franjas desplazadas al azar.

Nada de este módulo mira el precio posterior a la disponibilidad de la franja.
"""
from __future__ import annotations

import numpy as np

SESSION_GAP_S = 1800          # hueco de tiempo que corta una expansión en curso (pausa diaria, fin de semana)


def _ticks(x, tick):
    return np.round(np.asarray(x, dtype=float) / tick).astype(np.int64)


def causal_sigma(close_ticks: np.ndarray, W: int, hist: int = 3000) -> np.ndarray:
    """σ_W(j) = mediana de |c_t - c_{t-W}| sobre las `hist` velas ANTERIORES a j (NaN mientras no hay historia)."""
    n = len(close_ticks)
    d = np.full(n, np.nan)
    d[W:] = np.abs(close_ticks[W:] - close_ticks[:-W])
    out = np.full(n, np.nan)
    # mediana móvil causal, recalculada cada 50 velas (estable y barata)
    step = 50
    for j in range(W + hist, n, step):
        m = np.nanmedian(d[j - hist:j])
        out[j:j + step] = m
    return out


def expansion_bands(t_s, o, h, l, c, tick: float, W: int = 20, k: float = 2.5, e: float = 0.6, r: float = 0.3,
                    min_net_ticks: int = 4, hist: int = 3000) -> list[dict]:
    """TBZ-EXP. Una expansión arranca en la vela j si, en la ventana [j-W, j], el cierre de j se alejó del extremo
    opuesto de la ventana al menos max(k·σ_W, min_net) ticks con eficiencia (neto / recorrido de cierres) >= e.
    Mientras sigue, el extremo se actualiza; termina en la primera vela cuyo retroceso desde el extremo es
    >= max(2 ticks, r·recorrido). A = extremo opuesto de la ventana (inicio), B = extremo alcanzado. La franja
    queda DISPONIBLE al cierre de la vela que confirma el fin (t_avail). Un hueco de tiempo > 30 min descarta la
    expansión en curso (censura). Entradas: arrays de velas en orden temporal."""
    t_s = np.asarray(t_s, dtype=np.int64)
    H, L, C = _ticks(h, tick), _ticks(l, tick), _ticks(c, tick)
    n = len(C)
    if n <= W + 1:
        return []
    sig = causal_sigma(C, W, hist)
    from numpy.lib.stride_tricks import sliding_window_view
    lw = sliding_window_view(L, W + 1)            # fila j-W: velas j-W..j
    hw = sliding_window_view(H, W + 1)
    amin = lw.argmin(axis=1)
    amax = hw.argmax(axis=1)
    path = np.concatenate([[0], np.cumsum(np.abs(np.diff(C)))])
    out, state = [], None
    for j in range(W, n):
        if j > 0 and t_s[j] - t_s[j - 1] > SESSION_GAP_S:
            state = None                           # censura: no cruzar sesiones
        if state is None:
            s = sig[j]
            if not np.isfinite(s):
                continue
            thr = max(k * s, min_net_ticks)
            row = j - W
            ia, ib = row + amin[row], row + amax[row]
            best = None
            if ia < j:
                net = C[j] - L[ia]
                p = path[j] - path[ia]
                if net >= thr and p > 0 and (C[j] - C[ia]) / p >= e:
                    best = (net, 1, ia, L[ia], H[j])
            if ib < j:
                net = H[ib] - C[j]
                p = path[j] - path[ib]
                if net >= thr and p > 0 and (C[ib] - C[j]) / p >= e and (best is None or net > best[0]):
                    best = (net, -1, ib, H[ib], L[j])
            if best is not None:
                _, d, i0, a, ext = best
                if all(t_s[q] - t_s[q - 1] <= SESSION_GAP_S for q in range(i0 + 1, j + 1)):
                    state = dict(dir=d, i0=i0, a=a, ext=ext, iext=j, sigma=float(s))
            continue
        d = state["dir"]
        if d == 1 and H[j] > state["ext"]:
            state["ext"], state["iext"] = H[j], j
        elif d == -1 and L[j] < state["ext"]:
            state["ext"], state["iext"] = L[j], j
        total = abs(state["ext"] - state["a"])
        retr = (state["ext"] - L[j]) if d == 1 else (H[j] - state["ext"])
        if retr >= max(2, r * total):
            out.append(dict(dir=int(d), a_tick=int(state["a"]), b_tick=int(state["ext"]),
                            lo_tick=int(min(state["a"], state["ext"])), hi_tick=int(max(state["a"], state["ext"])),
                            width_ticks=int(total), sigma_ticks=state["sigma"],
                            t_start=int(t_s[state["i0"]]), t_ext=int(t_s[state["iext"]]), t_avail=int(t_s[j]),
                            i_start=int(state["i0"]), i_ext=int(state["iext"]), i_avail=int(j)))
            state = None
    return out


def dwell_bands(t_s, h, l, v, tick: float, snap_s: int = 300, L_s: int = 3600, q: float = 0.25, w_min: int = 4,
                min_bars: int = 50) -> list[dict]:
    """TBZ-DWELL. En cada múltiplo de `snap_s`, volumen por precio de las velas con t en [T-L, T) (el volumen de cada
    vela repartido parejo entre su mínimo y su máximo). Hueco = tramo contiguo de ticks con volumen < q·mediana de
    los ticks con volumen > 0, estrictamente interior al rango [min, max] de la ventana, de ancho >= w_min.
    Devuelve una fila por muestra con sus huecos (lista vacía si no hay)."""
    t_s = np.asarray(t_s, dtype=np.int64)
    H, L = _ticks(h, tick), _ticks(l, tick)
    V = np.asarray(v, dtype=float)
    n = len(t_s)
    if n == 0:
        return []
    out = []
    T = (int(t_s[0]) // snap_s + 1) * snap_s
    t_end = int(t_s[-1])
    while T <= t_end + snap_s:
        i0, i1 = np.searchsorted(t_s, T - L_s, "left"), np.searchsorted(t_s, T, "left")
        if i1 - i0 >= min_bars:
            lo, hi = L[i0:i1], H[i0:i1]
            pmin, pmax = int(lo.min()), int(hi.max())
            width = pmax - pmin + 1
            vpt = V[i0:i1] / (hi - lo + 1)
            diff = np.zeros(width + 1)
            np.add.at(diff, lo - pmin, vpt)
            np.add.at(diff, hi - pmin + 1, -vpt)
            vol = np.cumsum(diff)[:width]
            pos = vol[vol > 0]
            bands = []
            if len(pos) and width > 2:
                low = vol < q * np.median(pos)
                k = 1                                   # interior: no tocar el primer ni el último tick del rango
                while k < width - 1:
                    if low[k]:
                        s = k
                        while k < width - 1 and low[k]:
                            k += 1
                        # interior: ni pegado al borde inferior (low[s-1] alto) ni al superior (termina antes del último)
                        if k < width - 1 and not low[s - 1] and (k - s) >= w_min:
                            bands.append((pmin + s, pmin + k - 1))
                    else:
                        k += 1
            out.append(dict(t=int(T), range=(pmin, pmax), bands=bands))
        T += snap_s
    return out


def tick_set(bands) -> set:
    s = set()
    for lo, hi in bands:
        s.update(range(int(lo), int(hi) + 1))
    return s


def overlap_ratio_vs_null(a_bands, b_set: set, rng_lo: int, rng_hi: int, rng, reps: int = 20):
    """Fracción de ticks de las franjas `a_bands` cubiertos por `b_set`, real y bajo el nulo (las mismas franjas,
    mismo ancho, desplazadas al azar dentro de [rng_lo, rng_hi]). Devuelve (real, media_nulo, n_ticks)."""
    a = tick_set(a_bands)
    if not a:
        return None
    real = len(a & b_set) / len(a)
    null = []
    for _ in range(reps):
        sh = []
        for lo, hi in a_bands:
            w = hi - lo
            if rng_hi - rng_lo - w <= 0:
                sh.append((lo, hi)); continue
            x = int(rng.integers(rng_lo, rng_hi - w + 1))
            sh.append((x, x + w))
        s = tick_set(sh)
        null.append(len(s & b_set) / len(s) if s else 0.0)
    return real, float(np.mean(null)), len(a)

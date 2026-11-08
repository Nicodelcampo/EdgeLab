"""Estrategias de reels que juntó Nico (2026-11-08), medidas con las reglas tal como se ven, en R y con costos canónicos.
Pre-registro: `docs/research/estrategias_scrapeadas_20261108/PREREGISTRO.md`. Kemet (gaps) va aparte: `gap_continuacion.py`.

Tres familias, cada una devuelve operaciones (fecha, celda, lado, riesgo, bruto) desde un contexto M1 (`grilla_generica.contexto_m1`):
- ORO_RANGO (Italian Founder «Channel breakout GOLD»): rango de las 6 horas 03:00–09:00 Bucharest; desde las 09:00 stop de compra en el
  máximo y de venta en el mínimo (OCO); stop al otro lado del rango o a medio rango; salida 21:00 Bucharest o 4 h después.
  Más «martes débil» (SPX500): el martes a las 15:59 ET, si el martes cerró bajo su apertura y bajo la media de 40 cierres, compra;
  stop 1 ATR diario; salida al cierre del miércoles o del viernes.
- EMA_VWAP (AlphaZone): velas de 3 min en RTH, VWAP anclado a las 09:30 ET (volumen = volumen de tick del feed). Mecha que cruza el
  VWAP y cierre del otro lado (rechazo) → entrada en contra del cruce a la apertura de la vela siguiente; salida cuando una vela de
  3 min cierra del otro lado de la EMA9; stop en la mecha, a 1 o 2 ATR(14) de 3 min.
- ORB_EMA20 (FlexingJoe): rango 09:30–10:00 ET; primera vela de 10 min que cierra fuera → dirección; después, en velas de 2 min, primer
  toque de la EMA20 → entrada al nivel de la EMA20 (límite) en esa vela; stop al otro extremo del rango o a mitad del rango; objetivo
  1R, 2R o cierre del día. Una por día, entradas hasta las 15:00.

Simulación por velas (`_sim_velas`): el stop se revisa antes que el objetivo dentro de la vela (conservador); salidas por cierre al
precio de cierre de la vela. Es una aproximación declarada: no usa el orden de ticks dentro de la vela.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ORO_CELDAS = [(s, x) for s in ("rango", "medio") for x in ("21h", "4h")]
MARTES_CELDAS = [("miercoles",), ("viernes",)]
EV_CELDAS = [(s, f) for s in ("mecha", "atr1", "atr2") for f in ("rth", "2h")]
ORB_CELDAS = [(s, t) for s in ("opuesto", "medio") for t in (1.0, 2.0, 0.0)]          # objetivo 0 = cierre del día


def _hora(ctx, tz):
    lt = pd.to_datetime(ctx["t"] - 60, unit="s", utc=True).tz_convert(tz)
    return (lt.hour * 60 + lt.minute).to_numpy(), np.asarray(lt.strftime("%Y%m%d"), dtype=np.int64), lt.dayofweek.to_numpy()


def _agregar(o, h, l, c, v, grupos):
    """Velas agregadas por etiqueta de grupo consecutiva: (o, h, l, c, v, índice M1 de la última)."""
    corte = np.flatnonzero(np.r_[True, grupos[1:] != grupos[:-1]])
    fin = np.r_[corte[1:], len(grupos)] - 1
    return (o[corte], np.maximum.reduceat(h, corte), np.minimum.reduceat(l, corte), c[fin], np.add.reduceat(v, corte), fin)


def _ema(x, n):
    a = 2 / (n + 1); e = np.empty(len(x)); e[0] = x[0]
    for i in range(1, len(x)): e[i] = a * x[i] + (1 - a) * e[i - 1]
    return e


def _sim_velas(o, h, l, c, i0, entrada, d, sl, tp, salida_ok, ult):
    """Desde la vela i0 (inclusive) con entrada al precio `entrada`. Devuelve (bruto, motivo 1 stop / 2 objetivo / 3 regla o tiempo)."""
    st = entrada - d * sl; ob = entrada + d * tp if tp > 0 else None
    for i in range(i0, ult + 1):
        if (l[i] <= st) if d == 1 else (h[i] >= st): return d * (st - entrada), 1
        if ob is not None and ((h[i] >= ob) if d == 1 else (l[i] <= ob)): return d * (ob - entrada), 2
        if i == ult or (salida_ok is not None and salida_ok(i)): return d * (c[i] - entrada), 3
    return d * (c[ult] - entrada), 3


def oro_rango(ctx) -> pd.DataFrame:
    o, h, l, c = ctx["o"], ctx["h"], ctx["l"], ctx["c"]; m, f, _ = _hora(ctx, "Europe/Bucharest"); filas = []
    for dia in np.unique(f):
        ix = np.flatnonzero(f == dia); mm = m[ix]
        r = ix[(mm >= 180) & (mm < 540)]; post = ix[mm >= 540]
        if len(r) < 300 or not len(post): continue
        hi, lo = h[r].max(), l[r].min(); w = hi - lo
        if w <= 0: continue
        k = next((j for j in post if h[j] >= hi or l[j] <= lo), None)
        if k is None or (h[k] >= hi and l[k] <= lo): continue                       # ambos en la misma vela: ambiguo, se descarta
        d = 1 if h[k] >= hi else -1; ent = max(o[k], hi) if d == 1 else min(o[k], lo)
        for celda in ORO_CELDAS:
            s, x = celda; sl = w if s == "rango" else w / 2
            lim = post[m[post] < 1260] if x == "21h" else post[(m[post] < m[k] + 240) & (m[post] < 1260)]
            if not len(lim) or lim[-1] < k: continue
            b, mot = _sim_velas(o, h, l, c, k, ent, d, sl, 0.0, None, int(lim[-1]))
            filas.append(dict(fecha=int(dia), celda=celda, lado=d, riesgo=float(sl), bruto=float(b), motivo=mot))
    return pd.DataFrame(filas)


def _diarias_rth(ctx):
    m, f, dw = _hora(ctx, "America/New_York"); rth = (m >= 570) & (m < 960); filas = []
    for dia in np.unique(f[rth]):
        ix = np.flatnonzero(rth & (f == dia))
        filas.append(dict(fecha=int(dia), dow=int(dw[ix[0]]), o=float(ctx["o"][ix[0]]), c=float(ctx["c"][ix[-1]]),
                          rango=float(ctx["h"][ix].max() - ctx["l"][ix].min()), lo=float(ctx["l"][ix].min()), n=len(ix)))
    D = pd.DataFrame(filas)
    if len(D): D["sma40"] = D.c.rolling(40).mean(); D["atr"] = D.rango.rolling(14).mean().shift(1)
    return D


def martes_debil(ctx) -> pd.DataFrame:
    D = _diarias_rth(ctx); filas = []
    for i in range(len(D) - 1):
        r = D.iloc[i]
        if r.dow != 1 or r.n < 380 or not (r.c < r.o and r.c < r.sma40 and r.atr > 0): continue
        for celda in MARTES_CELDAS:
            fin = i + 1 if celda[0] == "miercoles" else next((j for j in range(i + 1, min(i + 5, len(D))) if D.dow.iloc[j] == 4), None)
            if fin is None or fin >= len(D): continue
            st = r.c - r.atr; seg = D.iloc[i + 1: fin + 1]
            hit = seg.index[seg.lo <= st]
            b = (st - r.c) if len(hit) else (D.c.iloc[fin] - r.c)
            filas.append(dict(fecha=int(r.fecha), celda=celda, lado=1, riesgo=float(r.atr), bruto=float(b), motivo=1 if len(hit) else 3))
    return pd.DataFrame(filas)


def ema_vwap(ctx) -> pd.DataFrame:
    m, f, _ = _hora(ctx, "America/New_York"); rth = np.flatnonzero((m >= 570) & (m < 960)); filas = []
    if not len(rth): return pd.DataFrame()
    g = f[rth] * 1000 + (m[rth] - 570) // 3
    O, H, L, C, V, _ = _agregar(ctx["o"][rth], ctx["h"][rth], ctx["l"][rth], ctx["c"][rth], np.maximum(ctx["v"][rth], 1.0), g)
    dia = (g[np.r_[np.flatnonzero(np.r_[True, g[1:] != g[:-1]])]] // 1000)
    slot = g[np.r_[np.flatnonzero(np.r_[True, g[1:] != g[:-1]])]] % 1000
    tr = np.maximum(H - L, np.abs(H - np.r_[C[0], C[:-1]])); atr = pd.Series(tr).rolling(14).mean().shift(1).to_numpy()
    for d0 in np.unique(dia):
        ix = np.flatnonzero(dia == d0)
        if len(ix) < 100: continue
        tp = (H[ix] + L[ix] + C[ix]) / 3; vw = np.cumsum(tp * V[ix]) / np.cumsum(V[ix]); em = _ema(C[ix], 9)
        ocupado = -1
        for j in range(1, len(ix) - 1):
            if j <= ocupado: continue
            i = ix[j]; prev = vw[j - 1]
            if H[i] > prev and C[i] < prev and O[i] < prev: d = -1
            elif L[i] < prev and C[i] > prev and O[i] > prev: d = 1
            else: continue
            ent = O[ix[j + 1]]; ult = ix[-1]; fin_j = len(ix) - 1
            for celda in EV_CELDAS:
                s, fl = celda
                if fl == "2h" and slot[i] >= 40: continue
                sl = (d * (ent - L[i]) if d == 1 else d * (ent - H[i])) if s == "mecha" else (1 if s == "atr1" else 2) * atr[i]
                if not (np.isfinite(sl) and sl > 0): continue
                sal = lambda q, d=d: (C[q] < em[q - ix[0]] if d == 1 else C[q] > em[q - ix[0]])
                b, mot = _sim_velas(O, H, L, C, ix[j + 1], ent, d, sl, 0.0, sal, ult)
                filas.append(dict(fecha=int(d0), celda=celda, lado=d, riesgo=float(sl), bruto=float(b), motivo=mot))
            # una posición a la vez (por la celda base mecha/rth): la siguiente señal espera la salida por EMA
            k = next((q for q in range(j + 1, fin_j + 1) if (C[ix[q]] < em[q] if d == 1 else C[ix[q]] > em[q])), fin_j)
            ocupado = k
    return pd.DataFrame(filas)


def orb_ema20(ctx) -> pd.DataFrame:
    o, h, l, c = ctx["o"], ctx["h"], ctx["l"], ctx["c"]; m, f, _ = _hora(ctx, "America/New_York"); filas = []
    for dia in np.unique(f):
        ix = np.flatnonzero(f == dia); mm = m[ix]
        orr = ix[(mm >= 570) & (mm < 600)]; post = ix[(mm >= 600) & (mm < 960)]
        if len(orr) < 25 or len(post) < 300: continue
        hi, lo = h[orr].max(), l[orr].min(); w = hi - lo
        if w <= 0: continue
        g10 = (m[post] - 600) // 10; d = 0; k10 = None
        for q in np.unique(g10):
            u = post[g10 == q][-1]
            if c[u] > hi: d, k10 = 1, u; break
            if c[u] < lo: d, k10 = -1, u; break
        if not d: continue
        rest = ix[(ix > k10) & (mm < 960)]
        if len(rest) < 2: continue
        g2 = (m[rest] - 570) // 2
        O2, H2, L2, C2, _, fin2 = _agregar(o[rest], h[rest], l[rest], c[rest], np.ones(len(rest)), g2)
        pre = ix[(ix <= k10) & (mm >= 570)]
        _, _, _, Cp, _, _ = _agregar(o[pre], h[pre], l[pre], c[pre], np.ones(len(pre)), (m[pre] - 570) // 2)
        em = _ema(np.r_[Cp, C2], 20)[len(Cp) - 1:-1]                                   # EMA20 conocida al abrir cada vela de 2 min
        hora2 = m[rest][fin2]
        j = next((q for q in range(len(C2)) if hora2[q] < 900 and ((L2[q] <= em[q]) if d == 1 else (H2[q] >= em[q]))), None)
        if j is None: continue
        ent = min(O2[j], em[j]) if d == 1 else max(O2[j], em[j])
        for celda in ORB_CELDAS:
            s, rr = celda
            sl = d * (ent - (lo if d == 1 else hi)) if s == "opuesto" else d * (ent - (lo + w / 2))
            if not sl > 0: continue
            b, mot = _sim_velas(O2, H2, L2, C2, j, ent, d, sl, rr * sl, None, len(C2) - 1)
            filas.append(dict(fecha=int(dia), celda=celda, lado=d, riesgo=float(sl), bruto=float(b), motivo=mot))
    return pd.DataFrame(filas)


FAMILIAS = {"ORO_RANGO": (oro_rango, ORO_CELDAS), "MARTES_DEBIL": (martes_debil, MARTES_CELDAS),
            "EMA_VWAP": (ema_vwap, EV_CELDAS), "ORB_EMA20": (orb_ema20, ORB_CELDAS)}

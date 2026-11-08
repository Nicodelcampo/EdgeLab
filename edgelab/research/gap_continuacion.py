"""GAP-CONTINUACION (2026-11-08): la mitad no medida de la regla de Kemet Capital (reel «Gap SP500»): un gap de apertura grande que
sigue abierto una hora después no se rellena; se opera A FAVOR del gap hasta el cierre. La mitad «gap chico se rellena» ya la midió
GAP_RTH (`docs/research/gap_rth_20261025/`, réplica SIN_POTENCIA con estimación ≈ 0). Pre-registro:
`docs/research/gap_continuacion_20261108/PREREGISTRO.md`.

Reutiliza `gap_rth.dias` (gap = cierre 09:29 − cierre RTH previo, ATR de 14 días) y `bracket.sim`. Regla por día y celda
(g, stop, hold, T): si |gap| > g·ATR y ninguna vela desde las 09:30 hasta la anterior a T tocó el cierre previo, orden a mercado a
favor del gap en el primer tick de la vela T; stop en el cierre previo («cierre») o a 0,5 ATR («atr05»); salida por tiempo (hold
minutos) o en la última vela RTH. Sin objetivo. R = (bruto − fricción) / distancia del stop.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

G = (0.15, 0.3, 0.45, 0.6, 0.9)
STOPS = ("cierre", "atr05")
HOLDS = (120, 999)
T_DEC = (10 * 60, 10 * 60 + 30)
CELDAS = [(g, s, h, t) for g in G for s in STOPS for h in HOLDS for t in T_DEC]      # 40 por fuente y canal


def operaciones(ctx) -> pd.DataFrame:
    from edgelab.research.bracket import sim
    from edgelab.research.gap_rth import dias
    D = dias(ctx); ts = ctx["tstart"]; tpx = ctx["tpx"]
    if not len(D) or len(tpx) == 0: return pd.DataFrame()
    et = pd.to_datetime(ctx["t"] - 60, unit="s", utc=True).tz_convert("America/New_York")
    mdd = (et.hour * 60 + et.minute).to_numpy()
    tick_bar = np.repeat(np.arange(len(ts) - 1), np.diff(ts)); bar_last = np.maximum(ts[1:] - 1, 0)
    filas = []
    for r in D.itertuples(index=False):
        if r.b929 < 0 or r.b930 < 0 or not (np.isfinite(r.cierre_prev) and np.isfinite(r.atr) and r.atr > 0): continue
        gap = r.c929 - r.cierre_prev; d = int(np.sign(gap))
        if d == 0: continue
        fin = int(ts[r.b_ult + 1] - 1); up, dn = (-1e18, -1e18) if d == 1 else (1e18, 1e18)
        for T in T_DEC:
            rng = np.arange(r.b930, r.b_ult + 1); bT = rng[mdd[rng] == T]
            if not len(bT): continue
            bT = int(bT[0]); prev = np.arange(r.b930, bT)
            tocado = (ctx["l"][prev].min() <= r.cierre_prev) if d == 1 else (ctx["h"][prev].max() >= r.cierre_prev)
            if tocado: continue
            i0 = int(ts[bT]); entrada = float(tpx[i0])
            for celda in (c for c in CELDAS if c[3] == T):
                g, st, h, _ = celda
                if abs(gap) <= g * r.atr: continue
                dist = d * (entrada - r.cierre_prev) if st == "cierre" else 0.5 * r.atr
                if not dist > 0: continue
                en, lado, pnl, mot = sim(tpx, tick_bar, bar_last, fin, i0, bT, up, dn, dist, 1e12, 0.0, 1, h)
                if en: filas.append(dict(fecha=r.fecha, celda=celda, lado=int(lado), gap=float(gap), atr=float(r.atr),
                                         riesgo=float(dist), bruto=float(pnl), motivo=int(mot)))
    return pd.DataFrame(filas)

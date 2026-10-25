"""GAP-RTH (2026-10-25): relanzamiento de C-TICKS F4 «cierre de gap» (`docs/research/CAMPANA_TICKS_MULTI_RESULTADOS_20260923.md`) con
muestra de años (Dukascopy) y la inferencia actual. F4 murió «sin potencia» (25–56 trades en 4 meses) con MCPT p 0,001 en ES y NQ.
Pre-registro: `docs/research/gap_rth_20261025/PREREGISTRO_GAP_RTH.md`.

Regla, por día de trading (hora de Nueva York): gap = cierre de la vela 09:29 − cierre RTH previo (cierre de la vela 15:59 del día
hábil anterior), conocido a las 09:30:00. Si |gap| > g × ATR_d (media de los rangos RTH 09:30–15:59 de los 14 días previos), orden a
mercado en contra del gap en el primer tick desde las 09:30:00. Objetivo a `frac` × |gap| desde la entrada (límite), stop opcional a
`k` × |gap| (mercado, al precio del tick), salida por tiempo o a las 16:00. Simulador: `edgelab/research/bracket.py::sim` (se fuerza el
lado poniendo los dos niveles del bracket del mismo lado). Diferencias con F4, declaradas: velas M1 en vez de 5 min, decisión con el
precio de las 09:29 (F4 usaba la apertura, que es el mismo precio que se llena) y objetivo por distancia en vez de nivel.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RTH0, RTH1 = 9 * 60 + 30, 16 * 60                # minutos ET
G = (0.15, 0.3, 0.45, 0.6, 0.9)                  # umbral del gap en ATR diarios (F4 usaba 0,3 y 0,6)
FRAC = (1.0, 0.5)                                # objetivo: cierre previo (gap entero) o medio gap
HOLDS = (30, 60, 120, 999)                       # minutos; 999 = hasta las 16:00 (F4: 60 min y fin del día)
STOPS = (0.0, 1.0)                               # 0 = sin stop; 1 = un gap más allá de la entrada
CELDAS = [(g, f, h, k) for g in G for f in FRAC for h in HOLDS for k in STOPS]   # 80 por fuente y ventana
ATR_N = 14


def dias(ctx) -> pd.DataFrame:
    """Una fila por día ET con vela 09:29 y vela 09:30: índices de vela, cierre 09:29, cierre RTH, rango RTH y ATR previo."""
    et = pd.to_datetime(ctx["t"] - 60, unit="s", utc=True).tz_convert("America/New_York")
    mdd = (et.hour * 60 + et.minute).to_numpy(); fecha = np.asarray(et.strftime("%Y%m%d"), dtype=np.int64)
    filas = []
    for f in np.unique(fecha):
        ix = np.flatnonzero(fecha == f); m = mdd[ix]
        if pd.Timestamp(str(f)).dayofweek >= 5: continue
        a = ix[m == RTH0 - 1]; b = ix[m == RTH0]; r = ix[(m >= RTH0) & (m < RTH1)]
        if not len(r): continue
        filas.append(dict(fecha=int(f), b929=int(a[0]) if len(a) else -1, b930=int(b[0]) if len(b) else -1, b_ult=int(r[-1]),
                          c929=float(ctx["c"][a[0]]) if len(a) else np.nan, cierre=float(ctx["c"][r[-1]]) if m[(m >= RTH0) & (m < RTH1)].max() >= RTH1 - 5 else np.nan,
                          rango=float(ctx["h"][r].max() - ctx["l"][r].min()), n_rth=int(len(r))))
    D = pd.DataFrame(filas)
    if not len(D): return D
    D["cierre_prev"] = D.cierre.shift(1)
    D["atr"] = D.rango.rolling(ATR_N, min_periods=ATR_N).mean().shift(1)
    return D


def operaciones(ctx) -> pd.DataFrame:
    """Una fila por (día, celda) que dispara: fecha, celda, lado, gap, atr, bruto (precio), motivo (1 stop, 2 objetivo, 3 tiempo)."""
    from edgelab.research.bracket import sim
    D = dias(ctx); ts = ctx["tstart"]; tpx = ctx["tpx"]
    if not len(D) or len(tpx) == 0: return pd.DataFrame()
    tick_bar = np.repeat(np.arange(len(ts) - 1), np.diff(ts)); bar_last = np.maximum(ts[1:] - 1, 0)
    filas = []
    for r in D.itertuples(index=False):
        if r.b929 < 0 or r.b930 < 0 or not (np.isfinite(r.cierre_prev) and np.isfinite(r.atr) and r.atr > 0): continue
        gap = r.c929 - r.cierre_prev; d = -int(np.sign(gap))
        if d == 0: continue
        i0 = int(ts[r.b930]); fin = int(ts[r.b_ult + 1] - 1)
        up, dn = (-1e18, -1e18) if d == 1 else (1e18, 1e18)
        for celda in CELDAS:
            g, frac, h, k = celda
            if abs(gap) <= g * r.atr: continue
            sl = k * abs(gap) if k else 1e12
            en, lado, pnl, mot = sim(tpx, tick_bar, bar_last, fin, i0, r.b930, up, dn, sl, frac * abs(gap), 0.0, 1, h)
            if en: filas.append(dict(fecha=r.fecha, celda=celda, lado=int(lado), gap=float(gap), atr=float(r.atr), bruto=float(pnl), motivo=int(mot)))
    return pd.DataFrame(filas)

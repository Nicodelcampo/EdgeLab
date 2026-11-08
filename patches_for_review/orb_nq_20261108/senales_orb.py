"""Prototipo target-free ORB RTH: solo señales, no simulación ni P&L.

Borrador de revisión, NO integrar ni lanzar sin aprobación del manifiesto y guardas.
`ctx`: columnas t (segundos UTC al cierre de M1), o/h/l/c, ses (trade date
YYYYMMDD), seg (identificador contractual); orden estrictamente cronológico.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

DURACIONES = (5, 15, 30)
COLUMNAS = ["k", "ses", "duracion", "lado", "hi", "lo", "dia", "hora", "atr14"]


def disparos(ctx):
    t = np.asarray(ctx["t"], dtype=np.int64)
    h, l, c = (np.asarray(ctx[z], dtype=float) for z in ("h", "l", "c"))
    ses, seg = (np.asarray(ctx[z], dtype=np.int64) for z in ("ses", "seg"))
    n = len(t)
    if not all(len(a) == n for a in (h, l, c, ses, seg)):
        raise ValueError("columnas de distinta longitud")
    if n == 0:
        return pd.DataFrame(columns=COLUMNAS)
    if np.any(np.diff(t) <= 0) or np.any(np.diff(ses) < 0):
        raise ValueError("tiempos o sesiones fuera de orden")
    dt = pd.to_datetime(t, unit="s", utc=True).tz_convert("America/New_York")
    minuto = np.asarray(dt.hour * 60 + dt.minute)
    # ATR14 simple de TR M1: no atraviesa sesión, roll ni huecos de minutos.
    atr = np.full(n, np.nan)
    tr = np.full(n, np.nan)
    for i in range(1, n):
        if ses[i] == ses[i-1] and seg[i] == seg[i-1] and t[i]-t[i-1] == 60:
            if np.all(np.isfinite([h[i], l[i], c[i-1]])) and h[i] >= l[i]:
                tr[i] = max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1]))
    atr = pd.Series(tr).rolling(14, min_periods=14).mean().to_numpy()
    filas = []
    for s in np.unique(ses):
        idx = np.flatnonzero(ses == s)
        # RTH y trade date han de coincidir para evitar una asociación falsa.
        rth = idx[(minuto[idx] > 570) & (minuto[idx] <= 955)]
        if not len(rth):
            continue
        dates = np.asarray(dt[rth].strftime("%Y%m%d"), dtype=np.int64)
        if np.any(dates != s):
            raise ValueError("fecha RTH no coincide con trade date")
        for dur in DURACIONES:
            rg = rth[(minuto[rth] > 570) & (minuto[rth] <= 570 + dur)]
            # Exigir cada minuto y un único segmento: nada de reconstruir huecos.
            if len(rg) != dur or not np.array_equal(minuto[rg], np.arange(571, 571+dur)):
                continue
            if np.any(seg[rg] != seg[rg[0]]) or not np.all(np.isfinite(h[rg]) & np.isfinite(l[rg])):
                continue
            hi, lo = float(h[rg].max()), float(l[rg].min())
            if hi <= lo:
                continue
            post = rth[(minuto[rth] > 570 + dur) & (minuto[rth] < 955)]
            prev = int(rg[-1])
            for k in post:
                # Una barra ausente puede ocultar la primera ruptura.
                if seg[k] != seg[rg[0]] or t[k] - t[prev] != 60 or not np.isfinite(c[k]):
                    break
                prev = int(k)
                lado = 1 if c[k] > hi else (-1 if c[k] < lo else 0)
                if not lado:
                    continue
                m = int(minuto[k]); hora = 0 if m < 630 else 1 if m < 720 else 2 if m < 840 else 3
                filas.append((int(k), int(s), dur, lado, hi, lo, int(dt[k].day_of_week), hora, float(atr[k])))
                break
    return pd.DataFrame(filas, columns=COLUMNAS)

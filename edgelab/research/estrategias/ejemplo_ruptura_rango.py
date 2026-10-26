"""EJEMPLO para el analizador (no es una hipótesis): ruptura del rango de las primeras N velas M1 de la sesión, una operación por
sesión, objetivo y stop en múltiplos del rango. Sirve de plantilla: cada señal se decide al cierre de la vela que rompe."""
import numpy as np

NOMBRE = "EJEMPLO-RUPTURA-RANGO"
FAMILIA = "EJEMPLO_ANALIZADOR"
INSTRUMENTO = "DK:USATECHIDXUSD"
PARAMETROS = dict(n_velas=[15, 30], mult_objetivo=[1.0, 2.0])


def senales(barras, n_velas=30, mult_objetivo=1.0):
    out = []
    for _, g in barras.groupby("ses", sort=True):
        if len(g) <= n_velas: continue
        hi, lo = g.h.iloc[:n_velas].max(), g.l.iloc[:n_velas].min(); r = hi - lo
        if not np.isfinite(r) or r <= 0: continue
        resto = g.iloc[n_velas:]
        arriba, abajo = np.flatnonzero(resto.c.to_numpy() > hi), np.flatnonzero(resto.c.to_numpy() < lo)
        i = min([x[0] for x in (arriba, abajo) if len(x)], default=None)
        if i is None: continue
        d = 1 if len(arriba) and arriba[0] == i else -1
        out.append(dict(available_at=int(resto.ts.iloc[i]), dir=d, target_pts=mult_objetivo * r, stop_pts=r, time_stop_min=240))
    return out

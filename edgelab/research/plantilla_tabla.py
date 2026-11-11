"""PLANTILLA de una familia como tabla de eventos (edgelab/research/tablas.py). Copiarla para una familia nueva y cambiar sólo
`eventos`, las definiciones, los filtros y las ejecuciones. Es también el ejemplo que usan los tests del contrato.

Evento de ejemplo (sin hipótesis de mercado: sirve para probar la cadena): en la vela k el cierre se alejó ≥ M·ATR(14) del extremo
opuesto A de las 30 velas anteriores; la operación va en contra (hacia A). Definiciones: M = 3 y M = 5. Rasgo: rapidez.
Justificación económica y cómo podría refutarse: en una familia real van en el pre-registro (plantilla de tools/prereg.py).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

NOMBRE = "PLANTILLA"
DEFINICIONES = ["def_m3", "def_m5"]
CONTROL = {"def_m5": "def_m3"}
FILTROS = {"rapido": ("vel", ">=", 1.0)}
EJECUCIONES = [("MERCADO", 0.5, 1.0, 0, 0), ("MERCADO", 0.5, 1.0, 0, 0.25), ("VUELTA", 0.1, 0.05, 0.1, 0, 0.6), ("LIMITE", 0.1, 0.5, 1.0)]
VENTANA = 30


def eventos(ctx) -> pd.DataFrame:
    h, l, c, ses = (np.asarray(ctx[x]) for x in ("h", "l", "c", "ses"))
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = pd.Series(tr).rolling(14).mean().shift(1).to_numpy()                 # sólo velas anteriores
    lo = pd.Series(l).rolling(VENTANA).min().to_numpy(); hi = pd.Series(h).rolling(VENTANA).max().to_numpy()
    filas = []; ultimo = -10**9
    for k in range(VENTANA + 15, len(c)):
        if not np.isfinite(atr[k]) or atr[k] <= 0 or k - ultimo < VENTANA: continue
        for d, A in ((1, lo[k]), (-1, hi[k])):
            m = (c[k] - A) * d / atr[k]
            if m < 3: continue
            w = np.arange(k - VENTANA + 1, k + 1); iA = int(w[np.argmin(l[w])] if d == 1 else w[np.argmax(h[w])])
            if ses[iA] != ses[k]: continue
            filas.append(dict(k=k, lado=-d, ref=float(A), ext=float(c[k]), rg=abs(c[k] - A), vel=m / max(k - iA, 1),
                              def_m3=True, def_m5=bool(m >= 5)))
            ultimo = k; break
    return pd.DataFrame(filas, columns=["k", "lado", "ref", "ext", "rg", "vel"] + DEFINICIONES)

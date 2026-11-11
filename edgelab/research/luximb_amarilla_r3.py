"""LUXIMB-AMARILLA-R3 (2026-11-11, pedido de Nico): la regla viva de R2 (ctrl|W2|e2|DESPUES, VWAP lejos) con STOPS MÁS CORTOS,
porque con el stop en el extremo de la excursión cada ganadora paga ≈ 0,1 R. Stops: el de R2 (`stop_ext`, referencia), el borde
externo de la caja + 0,1·H_am (`stop_b10`) o + 0,5·H_am (`stop_b50`), y la mitad entre borde externo y extremo (`stop_mid`).
Objetivos 50 % y 75 %. Sólo desarrollo (DESC/REP); el holdout de la familia ya se usó. Pre-registro: PREREGISTRO_R3.md."""
from __future__ import annotations

import numpy as np

from edgelab.research import luximb_amarilla as A, luximb_amarilla_r2 as R2

NOMBRE = "LUXIMB-AMARILLA-R3"
CARPETA = "docs/research/luximb_amarilla_20261111/r3"
BASES = {"ctrl": R2.BASES["ctrl"]}
DEFINICIONES = [f"ctrl|W2|{f}|e2|DESPUES" for f in A.FILTROS_VOL]
CONTROL = {"ctrl|W2|amarilla|e2|DESPUES": "ctrl|W2|sin_filtro|e2|DESPUES"}
EJECUCIONES = [("PRECIOS", o, s) for o in ("obj_50", "obj_75") for s in ("stop_ext", "stop_b10", "stop_b50", "stop_mid")]
PERIODOS = A.PERIODOS


def eventos(ctx):
    E = A.construir(ctx, BASES, (2,), (2.0,), R2.PCT, R2.AMP_R, largos=True)
    if not len(E):
        for s in ("stop_b10", "stop_b50", "stop_mid"): E[s] = []
        return E
    E = E[E.punto == "DESPUES"].reset_index(drop=True)
    d = -E.lado.to_numpy(); B = 2 * E.obj_50.to_numpy() - E.ref.to_numpy(); H = E.rg.to_numpy(); ham = 0.5 * H
    borde = B + d * 0.25 * H
    E["stop_b10"] = borde + d * 0.1 * ham; E["stop_b50"] = borde + d * 0.5 * ham
    E["stop_mid"] = 0.5 * (borde + E.stop_ext.to_numpy())
    return E

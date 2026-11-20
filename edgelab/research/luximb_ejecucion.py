"""LUXIMB-EJECUCION (2026-11-18, punto 2 de Nico): los mismos eventos de LUXIMB-A5 (fade hacia A de un impulso fuerte de LUX-IMB, cuya
reversión BRUTA se confirmó en REP) con ejecuciones rediseñadas para que la fricción pese menos en R, más el rescate de Nico.

Eventos: `luximb_hvn.eventos` con el detector D3_20 y la amplitud de A5 (percentil causal 60, sin piso), exactamente como
`tools/luximb_a5.py`. Contrato de `tablas`: lado = −d (fade), ref = A (origen del impulso), ext = B, rg = |B − A|.
Definiciones: `z0` (control: toda marca) y `z1` (≥ 1 zona OG/VI en el 25 % inicial).
Ejecuciones (motor único `ejecucion.py`; D = distancia a A desde la entrada):
  - MERCADO con stop amplio 0,5 / 1 / 1,5 / 2·D y objetivo A (tp 1);
  - objetivo más allá de A (tp 1,5) con stop 1 y 2·D;
  - break even a 0,5·D y parcial del 50 % a 0,5·D, con stop 1 y 2·D;
  - RESCATE (Nico): stop 1 / 1,5 / 2·D, objetivo A; al adentrarse d = 0,5 o 0,75 del riesgo, salida límite a x = 0 o 0,25 del riesgo.
Justificación económica y cómo podría refutarse: `docs/research/luximb_ejecucion_20261118/PREREGISTRO.md`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

NOMBRE = "LUXIMB-EJECUCION"
DEFINICIONES = ["z0", "z1"]
DEPENDENCIAS_KERNEL = ("edgelab.research.luximb_hvn", "edgelab.research.luximb_grilla")
EJECUCIONES = ([("MERCADO", sl, 1.0, 0, 0) for sl in (0.5, 1.0, 1.5, 2.0)] +
               [("MERCADO", sl, 1.5, 0, 0) for sl in (1.0, 2.0)] +
               [("MERCADO", sl, 1.0, 0, 0.5) for sl in (1.0, 2.0)] +
               [("MERCADO", sl, 1.0, 0.5, 0) for sl in (1.0, 2.0)] +
               [("RESCATE", sl, 1.0, d, x) for sl in (1.0, 1.5, 2.0) for d in (0.5, 0.75) for x in (0.0, 0.25)])
_DET = {"D3_20": (3.0, 20)}
_AMP = ((60.0, 0.0),)


def eventos(ctx) -> pd.DataFrame:
    from edgelab.research import luximb_hvn as H
    viejo = H.DETECTORES; H.DETECTORES = dict(_DET)
    try: E = H.eventos(ctx, amp=_AMP)
    finally: H.DETECTORES = viejo
    cols = ["k", "lado", "ref", "ext", "rg"] + DEFINICIONES
    if not len(E): return pd.DataFrame(columns=cols)
    out = pd.DataFrame(dict(k=E.k.to_numpy(np.int64), lado=-E.d.to_numpy(np.int64), ref=E.pa.to_numpy(float), ext=E.ext.to_numpy(float),
                            rg=E.rg.to_numpy(float), z0=E["D3_20_a0_z0"].astype(bool).to_numpy(), z1=E["D3_20_a0_z1"].astype(bool).to_numpy()))
    out = out[(out.z0 | out.z1) & (out.rg > 0)].reset_index(drop=True)
    return out[cols]

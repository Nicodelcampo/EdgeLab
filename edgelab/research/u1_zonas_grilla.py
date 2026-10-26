"""U1-ZONAS-GRILLA (2026-10-26, Nico: «relajá el filtro para considerar zonas individuales»): como `u1_racimos_grilla`, pero cada zona
INDIVIDUAL de aVolZonePOI2 es un área (sin exigir racimo), con la definición de zona (36, `almacen_zonas_main.GRILLA_ZONA`) como perilla.
Nació porque en YM los racimos no dieron ninguna celda evaluable. 2·3·3·36·6 = 3.888 celdas por canal. Almacén `ZONAS_AVZG_<INST>`.
Pre-registro: `docs/research/u1_zonas_20261025/PREREGISTRO_U1_ZONAS_BT2_AVZR.md` §7.
"""
from __future__ import annotations

import os

import pandas as pd

from edgelab.research import areas_expansion as AX
from edgelab.research import u1_indaga as U
from edgelab.research import u1_oro as UO
from edgelab.research import u1_zonas as Z
from edgelab.research.grilla_generica import Variable
from edgelab.research.u1_indaga import niveles  # noqa: F401
from edgelab.research.u1_racimos_grilla import EJECUCIONES, EJES_ORDINALES  # noqa: F401

NOMBRE = "U1-ZONAS-GRILLA"
INDICADORES = ["aVolZonePOI2"]
FUENTE = "AVZG"
N_ZONA = 36
VARIABLES = list(U.VARIABLES[:3]) + [Variable("def_zona", "zt", "grupo", categoria=N_ZONA)]
VACIO = ["m", "k", "xi", "ciclo", "lado", "lo", "hi", "H", "E", "A", "D", "ni", "A_H", "zt"]
BASE = {"N": 0, "x": 1, "A/H": 1, "def_zona": 17, "ejecución": 0}            # zona 95/2/10/3


def _cargar(inst):
    import glob
    f = glob.glob(f"{os.environ.get('ENTRADA', '/kaggle/input')}/**/ZONAS_{FUENTE}_{inst}.parquet", recursive=True)
    if not f: raise FileNotFoundError(f"sin almacén {FUENTE}/{inst}: nunca se cae a otra fuente")
    return pd.read_parquet(f[0], columns=["t_ns", "lo", "hi", "zona"])


def disparos(ctx, r_ref: float | None = None) -> pd.DataFrame:
    if "zonas" in ctx: Zs = ctx["zonas"][FUENTE]
    elif os.environ.get("SENSOR"): Zs = _cargar(os.environ["SENSOR"])
    else: Zs = None
    mes, f = UO.escala_por_mes(ctx, r_ref or UO.R_USATECH)
    cx = dict(ctx, seg=mes, escala_seg=f)
    grupos = [(0, None)] if Zs is None else list(Zs.groupby("zona", sort=True))
    out = []
    for zt, Zi in grupos:
        previo = U.AX; U.AX = Z._AXConZonas(Zi) if Zi is not None else AX
        try: D = U.disparos(cx)
        finally: U.AX = previo
        if len(D): out.append(D.assign(zt=int(zt)))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=VACIO)

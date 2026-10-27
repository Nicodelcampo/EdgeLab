"""U1-RACIMOS-GRILLA (2026-10-26, nivel 1 del diseño aprobado por Nico: «optimizalo bien y usá las variantes que valen la pena»).

Los racimos de aVolZonePOI2 como zonas de la gramática de U1, con la DEFINICIÓN de zona y de racimo como perillas: zona (36 definiciones
del indicador) × racimo (12 definiciones) del almacén `ZONAS_AVZRG_<INST>` (`tools/kaggle_grilla/almacen_zonas_main.py`, GRILLA_ZONA y
GRILLA_RACIMO). Para que el tamiz tenga potencia, U1 se reduce a su vecindario: N (2) × x (3) × A/H (3) × 6 ejecuciones, escala 1
(el racimo ya trae su tamaño en ticks). 2·3·3·36·12·6 = 46.656 celdas por canal. El nivel 2 (gramática completa) corre sólo sobre las
definiciones que salgan como pistas, en su réplica.
Pre-registro: `docs/research/u1_zonas_20261025/PREREGISTRO_U1_ZONAS_BT2_AVZR.md`.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from edgelab.research import areas_expansion as AX
from edgelab.research import u1_indaga as U
from edgelab.research import u1_oro as UO
from edgelab.research import u1_zonas as Z
from edgelab.research.grilla_generica import Variable
from edgelab.research.u1_indaga import niveles  # noqa: F401

NOMBRE = "U1-RACIMOS-GRILLA"
INDICADORES = ["aVolZonePOI2"]
FUENTE = "AVZRG"
N_ZONA, N_RACIMO = 36, 12
VARIABLES = list(U.VARIABLES[:3]) + [Variable("def_zona", "zt", "grupo", categoria=N_ZONA),
                                     Variable("def_racimo", "rt", "grupo", categoria=N_RACIMO)]
EJES_ORDINALES = (1, 2)
EJECUCIONES = [(e, o, "S3", 0) for e in ("E1A", "RET10", "VOL_VUELTA") for o in ("T1", "T2")]
VACIO = ["m", "k", "xi", "ciclo", "lado", "lo", "hi", "H", "E", "A", "D", "ni", "A_H", "zt", "rt"]
BASE = {"N": 0, "x": 1, "A/H": 1, "def_zona": 17, "def_racimo": 4, "ejecución": 0}   # zona 95/2/10/3 (pc·12+mm·4+wb·2+mc), racimo 6/500/30 (m·4+w·2+a)


def _cargar(inst):
    import glob
    f = glob.glob(f"{os.environ.get('ENTRADA', '/kaggle/input')}/**/ZONAS_{FUENTE}_{inst}.parquet", recursive=True)
    if not f: raise FileNotFoundError(f"sin almacén {FUENTE}/{inst}: nunca se cae a otra fuente")
    return pd.read_parquet(f[0], columns=["t_ns", "lo", "hi", "zona", "racimo"])


def disparos(ctx, r_ref: float | None = None) -> pd.DataFrame:
    """Un llamado de la gramática de U1 (escala 1, como `u1_oro`) por definición (zona, racimo) con esas zonas del almacén. Sin almacén
    ni zonas en el contexto (preflight, tests sintéticos) usa las de LUX-IMB del contexto como definición (0, 0)."""
    if "zonas" in ctx: Zs = ctx["zonas"][FUENTE]
    elif os.environ.get("SENSOR"): Zs = _cargar(os.environ["SENSOR"])
    else: Zs = None
    mes, f = UO.escala_por_mes(ctx, r_ref or UO.R_USATECH)
    cx = dict(ctx, seg=mes, escala_seg=f)
    grupos = [((0, 0), None)] if Zs is None else list(Zs.groupby(["zona", "racimo"], sort=True))
    out = []
    for (zt, rt), Zi in grupos:
        previo = U.AX; U.AX = Z._AXConZonas(Zi) if Zi is not None else AX
        try: D = U.disparos(cx)
        finally: U.AX = previo
        if len(D): out.append(D.assign(zt=int(zt), rt=int(rt)))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=VACIO)

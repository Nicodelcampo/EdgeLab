"""U1-ZONAS (2026-10-25): la gramática completa de U1 (racimo → estiramiento A/H → vuelta x → ejecución hacia el área, anatomía de
U1-INDAGA y escala causal mensual de U1-ORO-GRILLA) con las zonas de OTRO indicador en lugar de las de LUX-IMB. Spec:
`docs/research/u1_zonas_20261025/SPEC_U1_ZONAS.md`.

Las zonas vienen del almacén (`tools/kaggle_grilla/almacen_zonas_main.py`: `ZONAS_<IND>_<INST>.parquet` con t_ns de creación, lo, hi).
Una zona está disponible al cierre de la primera vela M1 que cierra en o después de su creación, y vive 500 min como en U1
(`areas_expansion.VIDA_MIN`). No se modifica `u1_indaga` (lo usa el embudo de U1-ORO-GRILLA): su `disparos` busca `AX.zonas` en el
módulo, así que mientras corre se le presta un `AX` que devuelve las zonas del almacén y delega todo lo demás en `areas_expansion`.
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

from edgelab.research import areas_expansion as AX
from edgelab.research import u1_indaga as U
from edgelab.research import u1_oro as UO
from edgelab.research.grilla_generica import Variable
from edgelab.research.u1_indaga import niveles  # noqa: F401

NOMBRE = "U1-ZONAS"
INDICADORES = ["aVolZonePOI2"]
FUENTES_ZONAS = ("AVZP2",)                       # perilla «indicador»: se agregan más fuentes al almacén sin cambiar la gramática
ESCALAS = UO.ESCALAS
VARIABLES = list(UO.VARIABLES) + [Variable("indicador", "ind", "grupo", categoria=len(FUENTES_ZONAS))]
EJES_ORDINALES = UO.EJES_ORDINALES
EJECUCIONES = UO.EJECUCIONES
VACIO = UO.VACIO + ["ind"]
BASE = dict(UO.BASE, indicador=0)


def zonas_almacen(Zs: pd.DataFrame, t_close) -> dict:
    """Zonas del almacén en índices de las velas M1 `t_close` (s de cierre), con la forma de `areas_expansion.zonas`."""
    t_close = np.asarray(t_close, np.int64)
    if not len(Zs) or not len(t_close):
        e = np.zeros(0); return dict(zi=e.astype(np.int64), zlo=e, zhi=e, zfin=e.astype(np.int64), og=e.astype(bool))
    tz = Zs.t_ns.to_numpy(np.int64) // 10**9
    zi = np.searchsorted(t_close, tz, side="left")                                  # primera vela que cierra en o después de la creación
    ok = (zi < len(t_close)) & (tz > t_close[0] - 60)
    zi = zi[ok].astype(np.int64); lo, hi = Zs.lo.to_numpy(float)[ok], Zs.hi.to_numpy(float)[ok]
    o = np.argsort(zi, kind="stable"); zi, lo, hi = zi[o], lo[o], hi[o]
    zfin = np.searchsorted(t_close, t_close[zi] + AX.VIDA_MIN * 60, side="right")
    return dict(zi=zi, zlo=np.minimum(lo, hi), zhi=np.maximum(lo, hi), zfin=zfin, og=np.zeros(len(zi), bool))


class _AXConZonas:
    """`areas_expansion` con `zonas` reemplazada por el almacén (todo lo demás se delega)."""
    def __init__(self, Zs): self._Zs = Zs
    def zonas(self, t_close, o, h, l, c): return zonas_almacen(self._Zs, t_close)
    def __getattr__(self, k): return getattr(AX, k)


def cargar(indicador: str, instrumento: str, entrada: str | None = None) -> pd.DataFrame:
    entrada = entrada or os.environ.get("ENTRADA", "/kaggle/input")
    f = glob.glob(f"{entrada}/**/ZONAS_{indicador}_{instrumento}.parquet", recursive=True)
    if not f: raise FileNotFoundError(f"sin almacén de zonas {indicador}/{instrumento} en {entrada}")
    return pd.read_parquet(f[0], columns=["t_ns", "lo", "hi"])


def disparos(ctx, r_ref: float | None = None) -> pd.DataFrame:
    inst = ctx.get("instrumento") or os.environ["SENSOR"]
    out = []
    for i, ind in enumerate(FUENTES_ZONAS):
        Zs = ctx["zonas"][ind] if "zonas" in ctx else cargar(ind, inst)
        previo = U.AX; U.AX = _AXConZonas(Zs)
        try: D = UO.disparos(ctx, r_ref)
        finally: U.AX = previo
        if len(D): out.append(D.assign(ind=i))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=VACIO)

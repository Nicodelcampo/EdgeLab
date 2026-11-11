"""LUXIMB-HFT (2026-11-11, pedido de Nico): la regla de impulsos del visor de LUX-IMB en NQ, pero con ZONAS HFT individuales en
lugar de OG/VI: impulso (detector ESPEJO-IND del visor, marca en tiempo real) que atraviesa ≥ n zonas HFT en su 25 % inicial, con n
como parámetro. Pre-registro: docs/research/luximb_hft_20261111/PREREGISTRO.md. Cadena estándar (edgelab/research/tablas.py).

Construcción (causal):
  - Zonas HFT individuales aceptadas `Z_CERT` (`niveles_sesion.zonas_del_dia`, el detector de los clusters HFT) sobre los ticks de
    cada día (`POR_BLOQUE`); cada zona está disponible en su `t_ns` y entra a la vela M1 cuyo cierre es ≥ `t_ns`.
  - Marcas: `luximb_grilla.marcas_segmento` (el objeto congelado del visor) con estas zonas en lugar de las OG/VI: zona atravesada
    entera por el tramo A → extremo después de nacer, con vida de 500 velas; condición «≥ n zonas en el 25 % inicial y ≥ 50 % del
    total ahí». n ∈ ZON (0 = control sin condición de zonas).
  - Operación: fade hacia A (como el visor), a mercado o en la vuelta (motor único).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import luximb_grilla as LG

NOMBRE = "LUXIMB-HFT"
CARPETA = "docs/research/luximb_hft_20261111"
DETECTORES = {"D3_20": (3.0, 20), "D2_20": (2.0, 20)}
AMP = ((60.0, 60.0), (80.0, 60.0))
ZON = ((0.0, 0), (0.25, 1), (0.25, 2), (0.25, 3), (0.25, 5), (0.25, 8), (0.25, 12))     # n zonas HFT en el 25 % inicial (0 = control)
DEFINICIONES = [f"{d}_a{a}_z{z}" for d in DETECTORES for a in range(len(AMP)) for z in range(len(ZON))]
CONTROL = {f"{d}_a{a}_z{z}": f"{d}_a{a}_z0" for d in DETECTORES for a in range(len(AMP)) for z in range(1, len(ZON))}
EJECUCIONES = [("MERCADO", sl, tp, 0, be) for sl in (0.2, 0.35, 0.5) for tp in (0.5, 1.0) for be in (0, 0.25)] + \
              [("VUELTA", e, r, 0.1, o, round(e + 0.5, 4)) for e in (0.1, 0.25) for r in (0.1, 0.2) for o in (0, 1)]
DEPENDENCIAS_KERNEL = ("edgelab.research.niveles_sesion",)                 # import perezoso en POR_BLOQUE (zonas HFT)
PERIODOS = [("DESC", 20250805, 20260331), ("REP", 20260401, 20260930)]


def POR_BLOQUE(B: pd.DataFrame, tick: float) -> pd.DataFrame:
    from edgelab.research import niveles_sesion as NV
    return NV.zonas_del_dia(B.ts_ns.to_numpy(), B.px.to_numpy(), B.vol.to_numpy(), B.sesion.to_numpy(), tick)


def _zonas_en_velas(ctx, a0, b0) -> dict:
    """Zonas HFT del contexto como las de `areas_expansion.zonas` (zi relativo al segmento, zlo, zhi); sólo las disponibles al
    cierre de una vela del segmento (las posteriores a la última vela se descartan: causalidad por prefijo)."""
    Z = ctx.get("por_bloque")
    vacio = dict(zi=np.zeros(0, np.int64), zlo=np.zeros(0), zhi=np.zeros(0), zfin=np.zeros(0, np.int64), og=np.zeros(0, bool))
    if Z is None or not len(Z): return vacio
    tc = np.asarray(ctx["t"], float)[a0:b0] * 1e9
    zi = np.searchsorted(tc, Z.t_ns.to_numpy(np.int64), side="left")       # primera vela cuyo cierre es >= disponibilidad
    m = (zi < len(tc)) & (Z.t_ns.to_numpy(np.int64) > tc[0] - 60e9)
    o = np.argsort(zi[m], kind="mergesort")
    return dict(zi=zi[m][o].astype(np.int64), zlo=Z.lo.to_numpy(float)[m][o], zhi=Z.hi.to_numpy(float)[m][o],
                zfin=np.full(int(m.sum()), len(tc), np.int64), og=np.zeros(int(m.sum()), bool))


def eventos(ctx) -> pd.DataFrame:
    o, h, l, c, t, seg = (np.asarray(ctx[x]) for x in ("o", "h", "l", "c", "t", "seg"))
    tick = float(ctx["tick"]); partes = []
    for sg in pd.unique(seg):
        idx = np.flatnonzero(seg == sg); a0, b0 = idx[0], idx[-1] + 1
        Z = _zonas_en_velas(ctx, a0, b0)
        for det, (ak, mb) in DETECTORES.items():
            M = LG.marcas_segmento(t[a0:b0], o[a0:b0], h[a0:b0], l[a0:b0], c[a0:b0], tick, Z=Z, atr_k=ak, max_bars=mb, amp=AMP, zon=ZON)
            if not len(M): continue
            for col in ("k", "i0", "iext"): M[col] = M[col].astype(np.int64) + a0
            M["defn"] = [f"{det}_a{int(a)}_z{int(z)}" for a, z in zip(M.amp, M.zon)]; partes.append(M)
    cols = ["k", "lado", "ref", "ext", "rg", "d", "i0", "nz", "nini25", "vel"]
    if not partes: return pd.DataFrame(columns=cols + DEFINICIONES)
    D = pd.concat(partes, ignore_index=True)
    piv = pd.crosstab([D.k, D.d, D.i0], D.defn).reindex(columns=DEFINICIONES, fill_value=0).astype(bool)
    U = D.drop_duplicates(["k", "d", "i0"]).set_index(["k", "d", "i0"])[["pa", "ext", "rg", "velas", "nz", "nini25"]]
    E = U.join(piv).reset_index().sort_values(["k", "i0"], kind="mergesort").reset_index(drop=True)
    E["vel"] = E.rg / np.maximum(E.velas, 1); E["lado"] = -E.d.astype(np.int64); E["ref"] = E.pa.astype(float)   # fade hacia A
    return E.drop(columns=["pa", "velas"])

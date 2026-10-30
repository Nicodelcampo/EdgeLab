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
    if "t_fin_ns" in Zs:                     # 2026-10-26: rectángulo extendido (BigTrap2): vive hasta que el indicador lo cierra
        tf = Zs.t_fin_ns.to_numpy(np.int64)[ok][o] // 10**9
        zfin = np.where(tf > 0, np.searchsorted(t_close, tf, side="left"), len(t_close))      # muerta ya en la vela que la cierra
        zfin = np.maximum(zfin, zi + 1)
    return dict(zi=zi, zlo=np.minimum(lo, hi), zhi=np.maximum(lo, hi), zfin=zfin, og=np.zeros(len(zi), bool))


class _AXConZonas:
    """`areas_expansion` con `zonas` reemplazada por el almacén (todo lo demás se delega)."""
    def __init__(self, Zs): self._Zs = Zs
    def zonas(self, t_close, o, h, l, c): return zonas_almacen(self._Zs, t_close)
    def __getattr__(self, k): return getattr(AX, k)


def _zonas_selladas(indicador: str, instrumento: str, entrada: str) -> pd.DataFrame:
    """En el holdout (`SELLADO=1`), el dataset sellado trae ticks crudos (`<INST>_*ticks.parquet`), no el almacén precalculado:
    se corren las mismas funciones de `tools/kaggle_grilla/almacen_zonas_main.py` sobre todas las sesiones selladas hasta `HASTA`."""
    from edgelab.bridge import bars as B
    from edgelab.bridge.indicators import avolclusterpoi as AVCL, avolzonepoi2 as AVZP2, bigtrap2 as BT2
    from edgelab.bridge.ticks import TickSeries
    from edgelab.research import fuentes_ticks as F
    r = glob.glob(f"{entrada}/**/{instrumento}_*ticks.parquet", recursive=True)
    if not r: raise FileNotFoundError(f"sin ticks sellados de {instrumento} en {entrada}")
    acta = os.environ.get("ACTA_HOLDOUT_RUTA") or os.path.abspath("ACTA_HOLDOUT.json"); hasta = int(os.environ.get("HASTA", 20991231)); tick = F.TICK_FUTURO[instrumento]
    bl = list(F.bloques_nq_sellado(F.HOLDOUT_PRIMERA_SESION_INT, hasta, r[0], acta, tick))
    if not bl: return pd.DataFrame(columns=["t_ns", "lo", "hi"])
    ts = np.concatenate([b.ts_ns.to_numpy() for b in bl]); px = np.concatenate([b.px.to_numpy() for b in bl])
    vol = np.concatenate([b.vol.to_numpy() for b in bl])
    if indicador == "AVZP2":
        p = dict(ob_away_heights=6.0, ob_max_inside_pct=4.0, racimo_min=0, racimo_bars=500, racimo_altura_ticks=30)
        tk = TickSeries(ts_ns=ts, price_ticks=np.round(px / tick).astype(np.int64), volume=vol.astype(np.int64), bid_ticks=None, ask_ticks=None,
                        sequence=np.arange(len(ts), dtype=np.int64), tick_size=tick)
        bars = B.build_tick_bars(tk, 25); fps = B.build_total_footprint_csr_nt8(tk, bars)
        res = AVZP2.run(bars, fps, B.session_ids(np.asarray(bars.end_ns, np.int64)), p)
        return pd.DataFrame([dict(t_ns=z["end_ns"], lo=z["low_tick"] * tick, hi=z["high_tick"] * tick) for z in res["zones"]])
    if indicador == "AVCL":
        tk = TickSeries(ts_ns=ts, price_ticks=np.round(px / tick).astype(np.int64), volume=vol.astype(np.int64), bid_ticks=None, ask_ticks=None,
                        sequence=np.arange(len(ts), dtype=np.int64), tick_size=tick)
        bars = B.build_tick_bars(tk, 50); fps = B.build_footprints(tk, bars, nt8_subseries=True)
        return pd.DataFrame([dict(t_ns=int(z["created_ms"]) * 10**6, lo=float(z["bottom"]), hi=float(z["top"])) for z in AVCL.run(tk, bars, fps)["zones"]])
    if indicador == "BT2":
        neg = np.full(len(ts), -1, np.int64)
        tk = TickSeries(ts_ns=ts, price_ticks=np.round(px / tick).astype(np.int64), volume=vol.astype(np.int64), bid_ticks=neg, ask_ticks=neg,
                        sequence=np.arange(len(ts), dtype=np.int64), tick_size=tick)
        bars = B.build_time_bars(tk, 1); fps = B.build_footprints(tk, bars)
        return pd.DataFrame([dict(t_ns=int(z["created_ms"]) * 10**6, lo=float(z["bottom"]), hi=float(z["top"]),
                                  t_fin_ns=int(z["ended_ms"]) * 10**6 if z.get("ended_ms") else -1) for z in BT2.run(tk, bars, fps)["zones"]])
    raise FileNotFoundError(f"indicador {indicador} no soportado en _zonas_selladas")


def cargar(indicador: str, instrumento: str, entrada: str | None = None) -> pd.DataFrame:
    entrada = entrada or os.environ.get("ENTRADA", "/kaggle/input")
    f = glob.glob(f"{entrada}/**/ZONAS_{indicador}_{instrumento}.parquet", recursive=True)
    if not f:
        if os.environ.get("SELLADO") == "1": return _zonas_selladas(indicador, instrumento, entrada)
        raise FileNotFoundError(f"sin almacén de zonas {indicador}/{instrumento} en {entrada}")
    Z = pd.read_parquet(f[0]); return Z[[c for c in ("t_ns", "lo", "hi", "t_fin_ns") if c in Z]]


def disparos(ctx, r_ref: float | None = None) -> pd.DataFrame:
    """Zonas: `ctx["zonas"][indicador]` si viene en el contexto; si no, el almacén del instrumento `SENSOR` (lo pone el kernel del
    embudo; sin almacén falla, nunca cae a otra fuente). Sin `SENSOR` ni zonas en el contexto (preflight y tests con datos
    sintéticos) las zonas son las de LUX-IMB del propio contexto: así el preflight prueba la gramática, que es lo que se reutiliza."""
    out = []
    for i, ind in enumerate(FUENTES_ZONAS):
        if "zonas" in ctx: Zs = ctx["zonas"][ind]
        elif os.environ.get("SENSOR"): Zs = cargar(ind, os.environ["SENSOR"])
        else: Zs = None
        previo = U.AX; U.AX = _AXConZonas(Zs) if Zs is not None else AX
        try: D = UO.disparos(ctx, r_ref)
        finally: U.AX = previo
        if len(D): out.append(D.assign(ind=i))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=VACIO)

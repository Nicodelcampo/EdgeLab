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


def _zonas_avzg_selladas(inst: str, entrada: str) -> pd.DataFrame:
    import glob
    import json
    import numpy as np
    from edgelab.bridge import bars as B
    from edgelab.bridge.indicators.avolzonepoi2 import run
    from edgelab.bridge.ticks import TickSeries
    from edgelab.research import fuentes_ticks as F
    from edgelab.research.u1_racimos_grilla import GRILLA_ZONA
    r = glob.glob(f"{entrada}/**/{inst}_*ticks.parquet", recursive=True)
    if not r: raise FileNotFoundError(f"sin ticks sellados de {inst} en {entrada}")
    acta = os.environ.get("ACTA_HOLDOUT_RUTA") or os.path.abspath("ACTA_HOLDOUT.json"); hasta = int(os.environ.get("HASTA", 20991231)); tick = F.TICK_FUTURO[inst]
    bl = list(F.bloques_nq_sellado(F.HOLDOUT_PRIMERA_SESION_INT, hasta, r[0], acta, tick))
    if not bl: return pd.DataFrame(columns=["t_ns", "lo", "hi", "zona"])
    ts = np.concatenate([b.ts_ns.to_numpy() for b in bl]); px = np.concatenate([b.px.to_numpy() for b in bl])
    vol = np.concatenate([b.vol.to_numpy() for b in bl])
    tk = TickSeries(ts_ns=ts, price_ticks=np.round(px / tick).astype(np.int64), volume=vol.astype(np.int64), bid_ticks=None, ask_ticks=None,
                    sequence=np.arange(len(ts), dtype=np.int64), tick_size=tick)
    bars = B.build_tick_bars(tk, 25); fps = B.build_total_footprint_csr_nt8(tk, bars)
    end = np.asarray(bars.end_ns, np.int64); ses = B.session_ids(end); filas = []
    p_base = dict(ob_away_heights=6.0, ob_max_inside_pct=4.0, racimo_min=0, racimo_bars=500, racimo_altura_ticks=30)
    celdas = (json.loads(os.environ.get("PARAMS") or "{}")).get("celdas") or []
    zts = sorted({int(c[3]) for c in celdas if len(c) > 3}) or list(range(len(GRILLA_ZONA)))
    for iz in zts:
        filas += [(int(z["end_ns"]), z["low_tick"] * tick, z["high_tick"] * tick, iz) for z in run(bars, fps, ses, dict(p_base, **GRILLA_ZONA[iz], racimo_min=0))["zones"]]
    return pd.DataFrame(filas, columns=["t_ns", "lo", "hi", "zona"])


def _cargar(inst):
    import glob
    ent = os.environ.get("ENTRADA", "/kaggle/input")
    f = glob.glob(f"{ent}/**/ZONAS_{FUENTE}_{inst}.parquet", recursive=True)
    if not f:
        if os.environ.get("SELLADO") == "1": return _zonas_avzg_selladas(inst, ent)
        raise FileNotFoundError(f"sin almacén {FUENTE}/{inst}: nunca se cae a otra fuente")
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

"""LUXIMB-AMARILLA-DS (2026-11-14, pedido de Nico: DeltaSweep como disparador de entrada dentro del contexto de otra estrategia).
Contexto: la regla viva de LUXIMB-AMARILLA (impulso de 40 velas sin condición de zonas, caja amarilla W2, excursión e2, regreso DESPUES del
borde interno; R2). En lugar de entrar al cierre de esa vela («base», el control), se espera el PRIMER disparo de DeltaSweep a favor de la
operación (lado = en contra del impulso) dentro de los `V` minutos siguientes; entrada a mercado en la vela siguiente al disparo, mismos
objetivos (50 % / 75 % del impulso) y stop (extremo de la excursión). Si al disparo el precio ya pasó el stop o el objetivo, no hay operación.
Sólo NQ (DeltaSweep necesita bid/ask). Pre-registro: docs/research/deltasweep_20261114/PREREGISTRO.md."""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import deltasweep_seq as DS, luximb_amarilla as A, luximb_amarilla_r2 as R2

LIBRO = True
NOMBRE = "LUXIMB-AMARILLA-DS"
CARPETA = "docs/research/deltasweep_20261114/amarilla"
DEPENDENCIAS_KERNEL = ("edgelab.research.deltasweep_nq",)
POR_BLOQUE = DS.POR_BLOQUE
TRIG = {"V4W_S1": (64, 1, 0), "V4S_S1": (8, 1, 0), "V2A_S1": (2, 1, 0), "V4W_S2": (64, 2, 600)}
VENT = (30, 120)
FILTROS_VOL = ("amarilla", "sin_filtro")
DEFINICIONES = [f"{f}|base" for f in FILTROS_VOL] + [f"{f}|{t}|v{v}" for f in FILTROS_VOL for t in TRIG for v in VENT]
CONTROL = {f"{f}|{t}|v{v}": f"{f}|base" for f in FILTROS_VOL for t in TRIG for v in VENT}
EJECUCIONES = [("PRECIOS", o, "stop_ext") for o in ("obj_50", "obj_75")]
PERIODOS = A.PERIODOS


def eventos(ctx) -> pd.DataFrame:
    E = A.construir(ctx, {"ctrl": R2.BASES["ctrl"]}, (2,), (2.0,), R2.PCT, R2.AMP_R, largos=True)
    cols = ["k", "lado", "ref", "ext", "rg", "obj_50", "obj_75", "stop_ext"] + DEFINICIONES
    if not len(E): return pd.DataFrame(columns=cols)
    E = E[E.punto == "DESPUES"].reset_index(drop=True); c = np.asarray(ctx["c"], float); tc = np.asarray(ctx["t"], float) * 1e9
    Z = ctx.get("por_bloque"); Z = Z.sort_values("t_ns", kind="mergesort").reset_index(drop=True) if Z is not None and len(Z) else None
    filas = []
    for r in E.itertuples():
        base = dict(k=int(r.k), lado=int(r.lado), ref=r.ref, ext=float(c[int(r.k)]), rg=r.rg, obj_50=r.obj_50, obj_75=r.obj_75,
                    stop_ext=r.stop_ext, **{d: False for d in DEFINICIONES})
        f = "amarilla" if r.amarilla else "sin_filtro"
        fb = dict(base); fb["amarilla|base"] = bool(r.amarilla); fb["sin_filtro|base"] = True; filas.append(fb)
        if Z is None: continue
        t0 = tc[int(r.k)]
        for t, (bit, n, gap) in TRIG.items():
            m = DS.secuencias(Z, bit, n, gap) & (Z.dir.to_numpy() == int(r.lado)) & (Z.t_ns.to_numpy() > t0)
            for v in VENT:
                i = np.flatnonzero(m & (Z.t_ns.to_numpy() <= t0 + v * 60e9))
                if not len(i): continue
                k = int(DS.a_velas(ctx, Z.t_ns.to_numpy()[i[:1]])[0])
                if k < 0 or k <= int(r.k): continue
                lado = int(r.lado); px = float(c[k])
                if lado * (px - r.stop_ext) <= 0 or lado * (r.obj_50 - px) <= 0: continue   # ya pasó el stop o el objetivo
                fl = dict(base, k=k, ext=px); fl[f"sin_filtro|{t}|v{v}"] = True; fl[f"amarilla|{t}|v{v}"] = bool(r.amarilla)
                filas.append(fl)
    if not filas: return pd.DataFrame(columns=cols)
    out = pd.DataFrame(filas)
    return out.groupby(["k", "lado", "stop_ext"], as_index=False).agg({**{x: "first" for x in ("ref", "ext", "rg", "obj_50", "obj_75")},
                                                                      **{d: "max" for d in DEFINICIONES}}).sort_values("k", kind="mergesort").reset_index(drop=True)

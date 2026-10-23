"""U1-CRUZADO (2026-10-23): la señal U1 se calcula sobre USATECH (zonas LUX-IMB del CFD) y se opera en NQ.

Idea de Nico: «como se mueven parecido, podría aplicar la estrategia en el USATECH y operar en el NQ». Manifiesto:
docs/research/areas_expansion_20261022/u1/MANIFIESTO_U1_CRUZADO.md.

Traslado de niveles: en la vela de decisión k (cierre del minuto t), base = cierre NQ(t) − cierre USATECH(t). Objetivo y stop
se trasladan sumando la base y se redondean al tick de NQ (el stop, hacia afuera: nunca más favorable). Se entra en el primer
tick de la vela NQ siguiente y todo se resuelve con NQ (orden de ticks si una vela toca stop y objetivo, hueco al precio real,
fricción canónica de NQ). Una señal sin vela NQ en ese minuto (fuera de la sesión CME) no se opera y se cuenta.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import areas_expansion as AX
from edgelab.research import u1_indaga as U

CELDA_U1 = dict(ni=0, xi=1, ah_min=8.0)                     # N >= 3, x = 0,25, A/H >= 8 (U1 tal cual)
EJECUCIONES = (("E1A", "T1", "S3"), ("E1A", "T3", "S3"))     # «objetivo: el borde cercano o el lejano»


def senales(ctx_us) -> pd.DataFrame:
    D = U.disparos(ctx_us)
    if not len(D): return D
    return D[(D.ni == CELDA_U1["ni"]) & (D.xi == CELDA_U1["xi"]) & (D.A_H >= CELDA_U1["ah_min"])].reset_index(drop=True)


def operar(ctx_us, ctx_nq, S=None) -> pd.DataFrame:
    """Una fila por (señal, ejecución): base, niveles en NQ, P&L bruto en puntos de NQ (NaN = sin llenado) y motivo si no se opera."""
    S = senales(ctx_us) if S is None else S
    t_nq = ctx_nq["t"]; tick = ctx_nq["tick"]; filas = []
    for r in S.to_dict("records"):
        k = int(r["k"]); t = ctx_us["t"][k]; j = int(np.searchsorted(t_nq, t))
        base = None if j >= len(t_nq) or t_nq[j] != t else float(ctx_nq["c"][j] - ctx_us["c"][k])
        d = int(r["lado"]); s = -d; borde, lejos = (r["hi"], r["lo"]) if d == 1 else (r["lo"], r["hi"])
        for en, ob, sl in EJECUCIONES:
            fila = dict(k_us=k, t=t, ses=int(ctx_us["ses"][k]), lado=d, ejecucion=f"{en}/{ob}/{sl}", base=base)
            if base is None: filas.append(dict(fila, motivo="sin vela NQ en ese minuto")); continue
            tp = np.round(((borde if ob == "T1" else lejos) + base) / tick) * tick
            st = r["E"] + base - s * tick
            st = np.floor(st / tick) * tick if s == 1 else np.ceil(st / tick) * tick          # stop hacia afuera
            e = float(ctx_nq["c"][j])
            if (e - tp) * -s < tick or (e - st) * s < tick: filas.append(dict(fila, motivo="niveles no válidos en NQ")); continue
            filas.append(dict(fila, j_nq=j, entrada_plan=e, tp=tp, stop=st, motivo=""))
    F = pd.DataFrame(filas)
    if not len(F): return F
    ok = F.motivo.eq("").to_numpy(); F["bruto"] = np.nan; F["amb"] = 0
    if ok.any():
        g = F[ok]
        pnl, amb = AX.simular(g.j_nq.to_numpy(np.int64), np.where(g.lado.to_numpy() == 1, -1, 1).astype(np.int64), np.full(ok.sum(), 2, np.int64),
                              g.entrada_plan.to_numpy(float), g.stop.to_numpy(float), g.tp.to_numpy(float), np.zeros(ok.sum(), np.int64),
                              ctx_nq["o"], ctx_nq["h"], ctx_nq["l"], ctx_nq["c"], ctx_nq["ses"], tick, ctx_nq["tpx"], ctx_nq["tstart"])
        F.loc[ok, "bruto"] = pnl; F.loc[ok, "amb"] = amb
    return F

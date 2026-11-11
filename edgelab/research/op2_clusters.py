"""OP-2 (2026-11-11): continuación en el primer regreso a un cluster HFT grande. Pre-registro:
`docs/research/hft_clusters_u1_20261110/PREREGISTRO_OP2.md`.

Evento: D0 de `hft_rebotes.eventos` (primer regreso tras alejarse X/2) sobre los clusters del E0-b, real (placebo 0) y de control
(pseudo-cluster desplazado ±1.200/±2.400 s sin superposición, placebo 1), con la misma regla de ubicación que `hft_ruptura`.
Operación: entrada a MERCADO en el tick del toque, a favor de la llegada (sigue de largo: −lado); stop X; objetivos X/2, X (primaria)
y 2X; salida por tiempo a 900 s (`fill_pasivo.operar_mercado`). R neto = bruto − fricción / X.
"""
from __future__ import annotations

import numpy as np

from edgelab.research import fill_pasivo as FP
from edgelab.research import hft_rebotes as RB
from edgelab.research.hft_clusters_info import VIDA_CLUSTER_S, barrera

NS = 1_000_000_000
GEOMETRIAS = {"g05": 0.5, "g1": 1.0, "g2": 2.0}
T_MAX_S = 900


def _op(ts, px, vol, t0, lo, hi, X, tick, friccion):
    i0 = int(np.searchsorted(ts, t0, side="right")); i1 = int(np.searchsorted(ts, t0 + VIDA_CLUSTER_S * NS, side="right"))
    if i1 - i0 < 3: return None
    ev = RB.eventos((ts[i0:i1] - t0) / NS, px[i0:i1], vol[i0:i1], lo, hi, X, tick).get("D0_BASE")
    if ev is None: return None
    j, ref, lado, _ = ev; j += i0
    out = dict(lado=lado, op_costo_r=float(friccion / X))
    for g, f in GEOMETRIAS.items(): out[f"op_{g}"] = FP.operar_mercado(ts, px, j, -lado, X, f * X, T_MAX_S)["r_bruto"]
    return out


def op2_del_dia(inst, fecha, ts, px, vol, C, tick, friccion) -> list:
    X = barrera(friccion, tick); filas = []; C = C.reset_index(drop=True); reales = C.t_ns.to_numpy(np.int64)
    r_lo, r_hi = C.lo.to_numpy(float), C.hi.to_numpy(float)
    for c in C.itertuples(index=False):
        o = _op(ts, px, vol, int(c.t_ns), float(c.lo), float(c.hi), X, tick, friccion)
        if o: filas.append(dict(inst=inst, fecha=int(fecha), placebo=0, **o))
        w = float(c.hi - c.lo)
        for des in RB.DESFASES_S:
            t2 = int(c.t_ns) + des * NS
            if t2 <= ts[0] or t2 >= ts[-1] or np.abs(reales - t2).min() < RB.MARGEN_S * NS: continue
            kk = int(np.searchsorted(ts, t2, side="right")) - 1; centro = float(px[kk]); plo, phi = centro - w / 2, centro + w / 2
            vivo = (reales < t2 + VIDA_CLUSTER_S * NS) & (reales + VIDA_CLUSTER_S * NS > t2)
            if (vivo & (r_lo <= phi + X / 4) & (plo - X / 4 <= r_hi)).any(): continue
            o = _op(ts, px, vol, int(ts[kk]), plo, phi, X, tick, friccion)
            if o: filas.append(dict(inst=inst, fecha=int(fecha), placebo=1, **o))
    return filas

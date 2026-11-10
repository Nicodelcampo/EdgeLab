# Principal del kernel U1-COMBO E0 (edgelab/research/u1_combo_e0.py): censo target-free de áreas por par de fuentes en NQ.
# Ventana fija en código (20250805..20260331): no se toma del entorno. Sin HFT, sin desenlaces. Salida: U1_COMBO_E0.json y RESULTADO.json.
import json
import os
import time
from itertools import combinations

import numpy as np


def main():
    from edgelab.research import fuentes_ticks as F, u1_combo_e0 as C, u1_zonas as UZ
    ent = os.environ.get("ENTRADA", "/kaggle/input"); t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    nq = C.ctx_m1(F.bloques_nq(C.DESDE, C.HASTA, ent)); log(f"NQ {len(nq['t'])} velas, {len(set(nq['seg'].tolist()))} segmentos")
    cfd = C.ctx_m1(F.bloques_usatech(C.DESDE, C.HASTA, ent)); log(f"CFD {len(cfd['t'])} velas")
    t0_ns, t1_ns = (int(nq["t"][0]) - 60) * 10**9, int(nq["t"][-1]) * 10**9
    lux_cfd, desc = C.trasladar(C.lux_almacen(cfd), cfd, nq)
    zonas = dict(LUX_CFD=lux_cfd, LUX_NQ=C.lux_almacen(nq))
    for f in ("AVZP2", "AVCL", "BT2"):
        Z = UZ.cargar(f, "NQ", ent); Z = Z[(Z.t_ns > t0_ns) & (Z.t_ns <= t1_ns)].reset_index(drop=True)
        mid = float(((Z.lo + Z.hi) / 2).median())
        if not nq["l"].min() * 0.8 <= mid <= nq["h"].max() * 1.2: raise ValueError(f"{f}: zonas fuera de la escala de NQ")
        zonas[f] = Z
    n = {k: len(v) for k, v in zonas.items()}; log(f"zonas {n}; CFD descartadas sin base {desc}")
    segs = C.preparar(nq, zonas); res = []
    for a, b in combinations(C.FUENTES, 2):
        r = C.censar_par(nq, segs, a, b); res.append(r)
        log(f"{a}+{b}: {r['combinaciones']} comb, {r['evaluables']} evaluables, {r['evaluables_unicas']} unicas, {r['degeneradas']} degeneradas, {r['duplicadas']} duplicadas")
    salida = dict(experimento="U1-COMBO-E0", desde=C.DESDE, hasta=C.HASTA, target_free=True, codigo=CODIGO_SHA, modulos=MODULOS_SHA, zonas=n,
                  cfd_descartadas_sin_base=desc, velas_nq=len(nq["t"]), sesiones_nq=int(len(np.unique(nq["ses"]))), pares=res)
    json.dump(salida, open("U1_COMBO_E0.json", "w"), indent=1, default=float)
    corto = dict(salida, pares=[{k: v for k, v in r.items() if k != "detalle"} for r in res])
    json.dump(corto, open("RESULTADO.json", "w"), indent=1, default=float)
    log("listo")


if __name__ == "__main__":
    main()

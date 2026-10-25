# Principal del kernel ORO-0530-RUPTURA (docs/research/oro_0530_20261024/PREREGISTRO_RUPTURA_0530.md): bracket OCO sobre el rango
# 05:00–05:29 UTC, colocado a las 05:30, en XAU (proxy con costos de GC) y en GC. Reutiliza oro_0530 (ruptura, trimestres),
# bracket.sim (VTD-BRACKET), fuentes_ticks, grilla_generica.contexto_m1 y funnel/escalera. Entorno: FRICCION / FRICCION_ADV (puntos de GC).
# Salida: ORO_0530_RUPTURA.json y ORO_0530_RUPTURA_operaciones.csv.
import json
import os
import time

import numpy as np
import pandas as pd

FUENTES = {"XAU": ("DK:XAUUSD", 20230101, 20260930), "GC": ("GC", 20250701, 20260930)}
RECIENTE = 20260401


def main():
    from edgelab.funnel import escalera as ES
    from edgelab.research import fuentes_ticks as F, grilla_generica as GG, oro_0530 as X
    ent = os.environ.get("ENTRADA", "/kaggle/input"); fr, fra = float(os.environ["FRICCION"]), float(os.environ["FRICCION_ADV"])
    t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    res = dict(experimento="ORO-0530-RUPTURA", codigo=CODIGO_SHA, modulos=MODULOS_SHA, friccion_pts=fr, friccion_adversa_pts=fra, celdas=[])
    todas, pruebas = [], []
    for inst, (fuente, d0, d1) in FUENTES.items():
        lector, tick = F.resolver(fuente); filas = []
        for lo, hi in X.trimestres(d0, d1):
            try: ctx = GG.contexto_m1(lector(lo, hi, ent), tick)
            except (ValueError, IndexError): log(f"{inst} {lo}-{hi}: sin datos"); continue
            R = X.ruptura(ctx); del ctx
            if len(R): filas.append(R)
            log(f"{inst} {lo}-{hi}: {len(R)} filas")
        R = pd.concat(filas, ignore_index=True).assign(inst=inst); R["neto"] = R.bruto - fr; R["neto_adv"] = R.bruto - fra; todas.append(R)
        for ventana, sub in (("total", R), ("reciente", R[R.fecha >= RECIENTE])):
            for (stop, h), g in sub.groupby(["stop", "hold"]):
                x = g.neto.to_numpy(float); ok = np.isfinite(x); x, ses = x[ok], g.fecha.to_numpy()[ok]
                c = dict(inst=inst, ventana=ventana, stop=stop, hold=int(h), sesiones=int(g.fecha.nunique()), llenadas=int(ok.sum()),
                         frac_llenado=float(ok.mean()) if len(ok) else None)
                if ok.sum() >= 30:
                    rs = ES.resumen_sesiones(x, ses, n_boot=20000)
                    xa = g.neto_adv.to_numpy(float)[ok]
                    c.update(media=rs["media"], ic90=rs["ic"], p=rs["p_unilateral"], mde=float(ES.mde(rs["se"])), acierto=float((x > 0).mean()),
                             media_adversa=float(xa.mean()), peor=float(x.min()), mejor=float(x.max()),
                             por_anio={str(a): float(v) for a, v in pd.Series(x).groupby(ses // 10000).mean().items()})
                else: c.update(p=1.0, nota="< 30 operaciones: no evaluable")
                res["celdas"].append(c); pruebas.append(c["p"])
    tz = ES.tamiz_fdr(pruebas, q=0.10)
    for i, c in enumerate(res["celdas"]): c["q"] = tz["q_valores"][i]; c["nominada"] = i in tz["nominadas"]
    res["tamiz"] = dict(m=tz["m"], pi0=tz["pi0"], metodo=tz["metodo"], nominadas=len(tz["nominadas"]))
    json.dump(res, open("ORO_0530_RUPTURA.json", "w"), indent=1, default=float)
    pd.concat(todas, ignore_index=True).to_csv("ORO_0530_RUPTURA_operaciones.csv", index=False)
    log(json.dumps({f"{c['inst']}/{c['ventana']}/{c['stop']}/{c['hold']}": (c["llenadas"], round(c.get("media", float("nan")), 3), round(c["p"], 4)) for c in res["celdas"]}))


if __name__ == "__main__":
    main()

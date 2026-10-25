# Principal del kernel ORO-0530-UTC (docs/research/oro_0530_20261024/PREREGISTRO_ORO_0530_UTC.md): perfil de actividad por minuto
# UTC (target-free) y las 16 celdas por instrumento y ventana. Reutiliza fuentes_ticks (lectores), grilla_generica.contexto_m1
# (velas M1 y ticks por vela) y funnel/escalera (bootstrap por sesión, tamiz FDR, MDE). Entorno: FRICCION / FRICCION_ADV (puntos
# de GC, de edgelab.costos, los pone el lanzador). Salida: ORO_0530_UTC.json y ORO_0530_UTC_sesiones_<INST>.csv.
import json
import os
import time

import numpy as np
import pandas as pd

FUENTES = {"XAU": ("DK:XAUUSD", 20230101, 20260930), "GC": ("GC", 20250701, 20260930)}
RECIENTE = 20260401                                                           # ventana «reciente» declarada antes de mirar


def trimestres(d0, d1):
    for a in range(d0 // 10000, d1 // 10000 + 1):
        for q0, q1 in ((101, 331), (401, 630), (701, 930), (1001, 1231)):
            lo, hi = max(a * 10000 + q0, d0), min(a * 10000 + q1, d1)
            if lo <= hi: yield lo, hi


def main():
    from edgelab.funnel import escalera as ES
    from edgelab.research import fuentes_ticks as F, grilla_generica as GG, oro_0530 as X
    ent = os.environ.get("ENTRADA", "/kaggle/input"); fr, fra = float(os.environ["FRICCION"]), float(os.environ["FRICCION_ADV"])
    t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    res = dict(experimento="ORO-0530-UTC", codigo=CODIGO_SHA, modulos=MODULOS_SHA, friccion_pts=fr, friccion_adversa_pts=fra, instrumentos={})
    pruebas = []
    for inst, (fuente, d0, d1) in FUENTES.items():
        lector, tick = F.resolver(fuente); livianas, tablas = [], []
        for lo, hi in trimestres(d0, d1):
            try: ctx = GG.contexto_m1(lector(lo, hi, ent), tick)
            except (ValueError, IndexError): log(f"{inst} {lo}-{hi}: sin datos"); continue
            M = X.minutos_utc(ctx); del ctx
            livianas.append(M[["dia", "mdd", "ticks", "v"]]); tablas.append(X.tabla(M)); log(f"{inst} {lo}-{hi}: {len(M)} velas")
        M = pd.concat(livianas, ignore_index=True); D = pd.concat(tablas, ignore_index=True).drop_duplicates("fecha").sort_values("fecha")
        P = X.perfil(M); top = P.ticks_rel.sort_values(ascending=False).head(20)
        dst = pd.to_datetime(M.dia.unique() * 86400, unit="s").tz_localize("UTC").tz_convert("America/New_York").map(lambda x: bool(x.dst()))
        de = dict(zip(M.dia.unique(), dst)); Mv, Mi = M[M.dia.map(de)], M[~M.dia.map(de)]
        r = dict(fuente=fuente, sesiones=int(len(D)), primera=int(D.fecha.min()), ultima=int(D.fecha.max()),
                 perfil=dict(top20_minutos_utc={f"{m // 60:02d}:{m % 60:02d}": round(float(v), 3) for m, v in top.items()},
                             alrededor_0530={f"{m // 60:02d}:{m % 60:02d}": dict(ticks=round(float(P.ticks_rel[m]), 3), vol=round(float(P.vol_rel[m]), 3))
                                             for m in range(X.ANCLA - 10, X.ANCLA + 16)},
                             verano_eeuu_0530=round(float(X.perfil(Mv).ticks_rel[X.ANCLA]), 3) if len(Mv) else None,
                             invierno_eeuu_0530=round(float(X.perfil(Mi).ticks_rel[X.ANCLA]), 3) if len(Mi) else None,
                             por_anio_0530={str(a): round(float(X.perfil(M[pd.to_datetime(M.dia * 86400, unit="s").dt.year == a]).ticks_rel[X.ANCLA]), 3)
                                            for a in sorted(pd.to_datetime(M.dia.unique() * 86400, unit="s").year.unique())}),
                 burst=dict(ticks_mediana=float(D.burst_ticks.median()), ticks_p25_p75=[float(D.burst_ticks.quantile(q)) for q in (.25, .75)],
                            frac_sesiones_ticks_x2=float((D.burst_ticks > 2).mean()), vol_mediana=float(D.burst_vol.median())),
                 ventanas={})
        for nombre, sub in (("total", D), ("reciente", D[D.fecha >= RECIENTE])):
            cel = X.evaluar(sub, fr, fra); r["ventanas"][nombre] = dict(sesiones=int(len(sub)), celdas=cel)
            pruebas += [dict(inst=inst, ventana=nombre, **c) for c in cel]
        D.to_csv(f"ORO_0530_UTC_sesiones_{inst}.csv", index=False); res["instrumentos"][inst] = r
        log(json.dumps(dict(inst=inst, sesiones=r["sesiones"], burst=r["burst"]["ticks_mediana"], top=list(r["perfil"]["top20_minutos_utc"])[:5])))
    tz = ES.tamiz_fdr([p["p"] for p in pruebas], q=0.10)
    res["tamiz"] = dict(m=tz["m"], pi0=tz["pi0"], metodo=tz["metodo"], nominadas=[dict(pruebas[i], q=tz["q_valores"][i]) for i in tz["nominadas"]])
    res["pruebas"] = [dict(p, q=tz["q_valores"][i]) for i, p in enumerate(pruebas)]
    json.dump(res, open("ORO_0530_UTC.json", "w"), indent=1, default=float)
    log(f"tamiz: {len(res['tamiz']['nominadas'])} nominadas de {tz['m']}")


if __name__ == "__main__":
    main()

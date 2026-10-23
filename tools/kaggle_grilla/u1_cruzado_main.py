# Principal del kernel U1-CRUZADO: señal U1 en USATECH, operación en NQ (manifiesto u1/MANIFIESTO_U1_CRUZADO.md).
# Entorno: DESDE/HASTA = YYYYMMDD (antes del holdout). Salidas: U1_CRUZADO_<DESDE>_<HASTA>.json (+ _operaciones.csv).
import json
import os
import time

import numpy as np
import pandas as pd


def resumen(x, ses, mes):
    from edgelab.funnel.escalera import resumen_sesiones
    ok = np.isfinite(x)
    if ok.sum() < 5: return dict(n=int(ok.sum()))
    rs = resumen_sesiones(x[ok], ses[ok], n_boot=4000)
    por_mes = pd.Series(x[ok]).groupby(mes[ok]).agg(["count", "mean"]).round(3)
    return dict(n=int(ok.sum()), media=float(x[ok].mean()), mediana=float(np.median(x[ok])), peor=float(x[ok].min()), mejor=float(x[ok].max()),
                sesiones=rs["n_sesiones"], ic90=rs["ic"], p_sesiones=rs["p_unilateral"], acierto=float((x[ok] > 0).mean()),
                por_mes={str(k): dict(n=int(v["count"]), media=float(v["mean"])) for k, v in por_mes.iterrows()})


def main():
    from edgelab.research import areas_expansion as AX, fuentes_ticks as F, grilla_generica as GG, u1_cruzado as X, u1_indaga as U
    desde, hasta = int(os.environ["DESDE"]), int(os.environ["HASTA"]); ent = os.environ.get("ENTRADA", "/kaggle/input")
    t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    us = GG.contexto_m1(F.bloques_usatech(desde, hasta, ent), F.FUENTES["USATECH"][1]); log(f"USATECH {len(us['c'])} velas")
    S = X.senales(us); log(f"señales U1: {len(S)}")
    # P&L de las mismas señales operadas en el propio USATECH (referencia del traslado)
    propio = []
    for (en, ob, sl) in X.EJECUCIONES:
        nv = [U.niveles(r, (en, ob, sl, 0), us) for r in S.to_dict("records")]; idx = [i for i, v in enumerate(nv) if v is not None]
        if not idx: continue
        st0, lim, s, e, st, tp, be = (np.array(v) for v in zip(*[nv[i] for i in idx]))
        pnl, _ = AX.simular(st0.astype(np.int64), s.astype(np.int64), lim.astype(np.int64), e, st, tp, be.astype(np.int64),
                            us["o"], us["h"], us["l"], us["c"], us["ses"], us["tick"], us["tpx"], us["tstart"])
        propio.append(pd.DataFrame(dict(k_us=S.k.to_numpy()[idx], ejecucion=f"{en}/{ob}/{sl}", bruto_usatech=pnl)))
    del us["tpx"]                                                             # memoria: los ticks del CFD ya no hacen falta
    nq = GG.contexto_m1(F.bloques_nq(desde, hasta, ent), F.FUENTES["NQ"][1]); log(f"NQ {len(nq['c'])} velas")
    ops = X.operar(us, nq, S)
    if propio: ops = ops.merge(pd.concat(propio), on=["k_us", "ejecucion"], how="left")
    fr = F.FUENTES["NQ"][2]; ops["neto"] = ops.bruto - fr
    ops["mes"] = pd.to_datetime(ops.t, unit="s", utc=True).dt.strftime("%Y%m")
    res = dict(experimento="U1-CRUZADO", desde=desde, hasta=hasta, friccion_pts=fr, codigo=CODIGO_SHA, modulos=MODULOS_SHA, senales=int(len(S)),
               motivos=ops.motivo.replace("", "operada").value_counts().to_dict(),
               base=dict(mediana=float(ops.base.median()), p05=float(ops.base.quantile(.05)), p95=float(ops.base.quantile(.95))) if ops.base.notna().any() else None,
               por_ejecucion={})
    for ej, g in ops.groupby("ejecucion"):
        res["por_ejecucion"][ej] = dict(nq_neto=resumen(g.neto.to_numpy(float), g.ses.to_numpy(), g.mes.to_numpy()),
                                        usatech_neto_mismas_senales=resumen((g.bruto_usatech - fr).to_numpy(float), g.ses.to_numpy(), g.mes.to_numpy()) if "bruto_usatech" in g else None,
                                        ambiguas_resueltas_con_ticks=int((g.amb == 1).sum()))
    nombre = f"U1_CRUZADO_{desde}_{hasta}"
    json.dump(res, open(f"{nombre}.json", "w"), indent=1, default=float)
    ops.to_csv(f"{nombre}_operaciones.csv", index=False)
    log(json.dumps({k: {kk: (vv.get("n"), round(vv.get("media", float("nan")), 2)) for kk, vv in v.items() if isinstance(vv, dict)} for k, v in res["por_ejecucion"].items()}))


main()

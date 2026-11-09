# Principal de los kernels ESTRATEGIAS-SCRAPEADAS (docs/research/estrategias_scrapeadas_20261108/PREREGISTRO.md), una familia por kernel: relanzamiento de C-TICKS F4 «cierre de gap».
# MODO=desc: 80 celdas × {USATECH→NQ, USA500→ES, USA30→YM} (Dukascopy 2023-01 → 2026-03, costos del futuro) × {total, reciente},
# tamiz FDR; más el canal de desarrollo en los futuros (jul-2025 → mar-2026), descriptivo. MODO=rep: las celdas de REP_CELDAS (JSON)
# en los futuros abr → sep 2026, sin tamiz (la decisión es el lote de LORD++, fuera del kernel). Reutiliza gap_rth (+ bracket.sim),
# oro_0530.trimestres, fuentes_ticks, grilla_generica.contexto_m1 y funnel/escalera. Fricción embebida de edgelab/costos.py.
# Salida: GAP_RTH_<MODO>.json y GAP_RTH_<MODO>_operaciones.csv.
import json
import os
import time

import numpy as np
import pandas as pd

FAMILIA = "ORO_RANGO"                                                      # lo reemplaza tools/estrategias_scrapeadas.py al construir
PARES_POR_FAMILIA = {"ORO_RANGO": {"GC": "DK:XAUUSD"}, "MARTES_DEBIL": {"ES": "DK:USA500IDXUSD"},
                     "EMA_VWAP": {"NQ": "DK:USATECHIDXUSD", "ES": "DK:USA500IDXUSD", "YM": "DK:USA30IDXUSD"},
                     "ORB_EMA20": {"NQ": "DK:USATECHIDXUSD", "ES": "DK:USA500IDXUSD"}}
PARES = PARES_POR_FAMILIA[FAMILIA]
DESC_DK, DESC_CME, REP = (20230101, 20260331), (20250701, 20260331), (20260401, 20260930)
RECIENTE = 20250701                                                         # ventana «reciente» declarada antes de mirar
CALENTAR = 70
REP_CELDAS = []                                                             # se congela tras el DESC
FRICCION = {"NQ": 1.5455, "ES": 0.8877, "YM": 5.052, "GC": 0.605}
FRICCION_ADV = {"NQ": 2.0455, "ES": 1.3877, "YM": 7.052, "GC": 0.805}                                                               # días de lectura previa por trimestre (ATR de 14 y cierre previo)


def leer(fuente, d0, d1, ent, log):
    from edgelab.research import fuentes_ticks as F, estrategias_scrapeadas as X, grilla_generica as GG, oro_0530 as O
    lector, tick = F.resolver(fuente); filas = []
    for lo, hi in O.trimestres(d0, d1):
        lo_c = int((pd.Timestamp(str(lo)) - pd.Timedelta(days=CALENTAR)).strftime("%Y%m%d"))
        try: ctx = GG.contexto_m1(lector(lo_c, hi, ent), tick)
        except (ValueError, IndexError): log(f"{fuente} {lo}-{hi}: sin datos"); continue
        R = X.FAMILIAS[FAMILIA][0](ctx); del ctx
        if len(R): R = R[(R.fecha >= lo) & (R.fecha <= hi)]; filas.append(R)
        log(f"{fuente} {lo}-{hi}: {len(R)} filas")
    return pd.concat(filas, ignore_index=True) if filas else pd.DataFrame()


def celda_resumen(*a, **k):
    from edgelab.research.gap_continuacion import celda_resumen as f
    return f(*a, **k)


def main():
    from edgelab.funnel import escalera as ES
    from edgelab.research import estrategias_scrapeadas as X
    ent = os.environ.get("ENTRADA", "/kaggle/input"); modo = os.environ.get("MODO", "desc")
    t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    fr, fra = FRICCION, FRICCION_ADV                                            # edgelab/costos.py, puntos por viaje (2026-11-08)
    res = dict(estadistico="R", experimento="ESTRATEGIAS-SCRAPEADAS", familia=FAMILIA, modo=modo, codigo=CODIGO_SHA, modulos=MODULOS_SHA, friccion_pts=fr, friccion_adversa_pts=fra, celdas=[])
    todas = []
    if modo == "desc":
        pruebas = []
        for inst, dk in PARES.items():
            for fuente, (d0, d1), canales in ((dk, DESC_DK, ("total", "reciente")), (inst, DESC_CME, ("cme_desarrollo",))):
                R = leer(fuente, d0, d1, ent, log)
                if not len(R): continue
                todas.append(R.assign(inst=inst, fuente=fuente))
                for canal in canales:
                    sub = R[R.fecha >= RECIENTE] if canal == "reciente" else R
                    for celda in X.FAMILIAS[FAMILIA][1]:
                        c = dict(inst=inst, fuente=fuente, canal=canal, celda=list(celda), **celda_resumen(sub[sub.celda == celda], fr[inst], fra[inst], 20000))
                        res["celdas"].append(c)
                        if canal != "cme_desarrollo": pruebas.append(len(res["celdas"]) - 1)
        ev = [i for i in pruebas if res["celdas"][i]["ops"] >= 30]
        tz = ES.tamiz_fdr([res["celdas"][i]["p"] for i in ev], q=0.10) if ev else dict(q_valores=[], nominadas=[], pi0=None, metodo=None)
        for j, i in enumerate(ev): res["celdas"][i]["q"] = tz["q_valores"][j]; res["celdas"][i]["nominada"] = j in tz["nominadas"]
        res["tamiz"] = dict(m_registradas=len(pruebas), m_evaluables=len(ev), pi0=tz["pi0"], metodo=tz["metodo"], nominadas=len(tz["nominadas"]))
    else:
        rep = json.loads(os.environ.get("REP_CELDAS") or json.dumps(REP_CELDAS))                       # [{"inst": "ES", "celda": [g, frac, hold, k]}, ...]
        for inst in sorted({r["inst"] for r in rep}):
            R = leer(inst, *REP, ent, log)
            if not len(R): continue
            todas.append(R.assign(inst=inst, fuente=inst))
            for r in (r for r in rep if r["inst"] == inst):
                celda = tuple(r["celda"])
                res["celdas"].append(dict(inst=inst, fuente=inst, canal="replica", celda=list(celda), **celda_resumen(R[R.celda == celda], fr[inst], fra[inst], 20000)))
    json.dump(res, open(f"ESCR_{FAMILIA}_{modo}.json", "w"), indent=1, default=float)
    if todas: pd.concat(todas, ignore_index=True).to_csv(f"ESCR_{FAMILIA}_{modo}_operaciones.csv", index=False)
    log(json.dumps(res.get("tamiz", {})))


if __name__ == "__main__":
    main()

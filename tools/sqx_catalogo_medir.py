#!/usr/bin/env python3
"""Mide las candidatas del catálogo de SQX (docs/research/sqx_catalogo_20261117/PREREGISTRO_MEDICION.md) con `edgelab.research.sqx_catalogo`.

  python tools/sqx_catalogo_medir.py <carpeta M1> [estrategia ...]   # -> docs/research/sqx_catalogo_20261117/RESULTADO.json
Datos: M1 Dukascopy con zona declarada (m1_intradia.leer_m1) y barras D1 de SQX (HG, ZB, 6B); COT legacy de la CFTC (data/cot). Costos: edgelab.costos
(6J, ZB, CL, HG con spread ESTIMADO). Reusa reels_20261116.tramo y fundedsync_tanda2._bh.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from reels_20261116 import tramo, REC  # noqa: E402
OUT = ROOT / "docs/research/sqx_catalogo_20261117"
M1 = {"ES": "SP_M1_dukas", "NQ": "NQ_M1_dukas", "YM": "DJ_M1_dukas", "RTY": "USSC2000IDXUSD", "GC": "XAUUSD_M1_dukas", "6E": "EURUSD_M1_dukas",
      "6J": "USDJPY_M1_dukas", "CL": "LIGHTCMDUSD"}
D1CSV = {"HG": "COPPERCMDUSD_D1", "ZB": "USTBONDTRUSD_D1", "6B": "GBPUSD_M1_dukas_D1"}
COT = {"GC": "088691", "CL": "067651", "HG": "085692", "ZB": "020601", "6E": "099741", "6J": "097741", "6B": "096742"}
PIP = {"6E": 0.0001, "6J": 0.01, "CL": 0.01, "GC": 0.1, "6B": 0.0001}
A, B_ = ("2012-01-01", "2019-12-31"), ("2020-01-01", "2026-09-29")


def cargar(inst, tf, carpeta, cache):
    from edgelab.research import m1_intradia as M, sqx_catalogo as S
    if inst in D1CSV:
        Bd = S.barras_d1_csv(ROOT / f"data/sqx_barras/{D1CSV[inst]}.csv"); return Bd[Bd.fecha < 20260930], None
    if inst not in cache:
        D = M.leer_m1(Path(carpeta) / f"{M1[inst]}.csv"); cache[inst] = D[(D.index >= "2010-06-01") & (D.index < "2026-09-30")]
    D = cache[inst]; Bt = S.barras_desde_m1(D, tf); return Bt[Bt.fecha < 20260930], D


def cot_df(inst):
    from edgelab.research import sqx_catalogo as S
    d = pd.DataFrame(json.load(open(ROOT / f"data/cot/legacy_{COT[inst]}.json"))); d["fecha"] = d.report_date_as_yyyy_mm_dd.str[:10]
    return S.cot_indices(d)


def main(carpeta, *solo):
    from edgelab.research import sqx_catalogo as S
    from edgelab.research.embudo_runners import friccion
    from fundedsync_tanda2 import _bh
    cache = {}; res = dict(preregistro="docs/research/sqx_catalogo_20261117/PREREGISTRO_MEDICION.md", pruebas={}); claves = []
    es_d1 = None
    for nom, (fn, tf, insts) in S.ESTRATEGIAS.items():
        if solo and nom not in solo: continue
        for inst in insts:
            Bx, D = cargar(inst, tf, carpeta, cache); fr = friccion(inst)[0]
            ctx = dict(pip=PIP.get(inst, 0.0), fric=fr if inst != "6J" else fr * float(np.nanmedian(Bx.c)) ** 2)
            if nom.startswith("COT"): ctx["cot"] = S.cot_por_barra(Bx, cot_df(inst), invertir=(inst == "6J"))
            if nom == "VP_POC_USDJPY": ctx["poc_dia_previo"] = S.poc_dia_previo(D, Bx)
            if nom == "PRICE_DIP" and inst in ("ES", "NQ", "YM", "RTY"):
                if es_d1 is None: es_d1, _ = cargar("ES", "D1", carpeta, cache)
                f = pd.Series((es_d1.c > es_d1.c.rolling(200).mean().shift(1)).values, index=es_d1.fecha.values)
                ctx["filtro_mercado"] = f.reindex(Bx.fecha.values).fillna(False).to_numpy(bool)
            sig = fn(Bx, ctx); m1 = S.indices_m1(Bx, D, tf) if D is not None else None   # enmienda 1: orden dentro de la barra por M1
            for var in ("original", "viernes"):
                T = S.simular(Bx, sig, viernes=(var == "viernes"), m1=m1)
                if not len(T): res["pruebas"][f"{nom}|{inst}|{var}"] = dict(n=0); continue
                frx = fr if inst != "6J" else fr * T.entrada.to_numpy() ** 2             # 6J operado como USDJPY: costo en yenes
                g = T.assign(riesgo=(T.entrada - T.stop0).abs(), bruto=T.lado * (T.salida_px - T.entrada))
                g = g[g.riesgo > 0].copy(); frx = frx if np.isscalar(frx) else frx[g.index]
                g["neto"] = g.bruto - frx; g["R"] = g.neto / g.riesgo; g["Rb"] = g.bruto / g.riesgo; g["fricR"] = frx / g.riesgo
                g["dia"] = pd.to_datetime(g.fecha.astype(str))
                k = f"{nom}|{inst}|{var}"; claves.append(k); yr = g.groupby(g.dia.dt.year).R.sum()
                res["pruebas"][k] = dict(tf=tf, A=tramo(g, *A), B=tramo(g, *B_), reciente=tramo(g, *REC), n=int(len(g)), anios_pos=int((yr > 0).sum()), anios=int(len(yr)),
                                         motivos=g.motivo.value_counts().to_dict(), barras_med=float(g.barras.median()))
                g.to_csv(OUT / "ops" / f"{nom}_{inst}_{var}.csv.gz", index=False)
                r = res["pruebas"][k]
                print(k, {t: (r[t]["n"], r[t].get("R") and round(r[t]["R"], 3), r[t].get("p") and round(r[t]["p"], 3)) for t in ("A", "B", "reciente")},
                      "fric", r["B"].get("fric_med") and round(r["B"]["fric_med"], 3), "años+", r["anios_pos"], "/", r["anios"], flush=True)
    ps = [res["pruebas"][k]["B"].get("p", 1.0) for k in claves]; bh = _bh(ps)
    for k, b in zip(claves, bh):
        r = res["pruebas"][k]; okA = r["A"].get("no_evaluable") or (r["A"].get("R") or -1) > 0
        r.update(nominada_bh=bool(b), pasa=bool(b and okA and (r["B"].get("R") or -1) > 0 and r["B"].get("fric_med", 9) <= 0.08),
                 regimen_reciente=bool((r["B"].get("R") or -1) > 0 and not r["A"].get("no_evaluable") and (r["A"].get("R") or 1) <= 0))
    res["n_pruebas"] = len(claves)
    (OUT / ("RESULTADO.json" if not solo else "RESULTADO_PARCIAL.json")).write_text(json.dumps(res, indent=1, default=float))
    print("pasan", [k for k in claves if res["pruebas"][k]["pasa"]]); print("nominadas", [k for k in claves if res["pruebas"][k]["nominada_bh"]])


if __name__ == "__main__":
    from edgelab.costos import estimados_permitidos
    (OUT / "ops").mkdir(parents=True, exist_ok=True)
    with estimados_permitidos("docs/research/sqx_catalogo_20261117/PREREGISTRO_MEDICION.md (spreads estimados 6J, ZB, CL, HG)"): main(*sys.argv[1:])

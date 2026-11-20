#!/usr/bin/env python3
"""FRICCION-RQ: curva bruto–stop y palancas de fricción de RQ2, RQ5 y RQ6 en DESC (pre-registro docs/research/friccion_rq_20261119/PREREGISTRO.md).

Reusa las señales ya calculadas (`docs/research/roboquant_20261118/EVENTOS.csv.gz`), el motor único (`ejecucion.desenlaces`, objetivo y stop
en precios), la fricción canónica (`embudo_runners.friccion`, `costos.desglose`) y el cargador verificado
`externas_estructurales_a5.cargar_ctx_m1nt8_rapido` (mismo contexto que `a5_campana._ctx` salvo el perfil de volumen). Sólo filas DESC.

  python tools/friccion_rq.py correr     # 18 celdas → OPS.csv.gz (sólo DESC) y RESULTADO.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/friccion_rq_20261119"
EVENTOS = ROOT / "docs/research/roboquant_20261118/EVENTOS.csv.gz"
REGLAS = ("RQ2", "RQ5", "RQ6")
ESCALAS = (1.0, 1.5, 2.0, 3.0)
CIERRE = (1.0, 2.0)
LEJOS = 50.0


def celdas():
    return [(f"esc{m:g}", m, False) for m in ESCALAS] + [(f"cierre{m:g}", m, True) for m in CIERRE]


def _columnas(E):
    c = E.stop + E.lado * E.rg                                         # cierre de la vela de señal (stop = c − lado·rg)
    lejos = (E.obj - c).abs() > LEJOS * E.rg
    specs = []
    for nom, m, cierre in celdas():
        E[f"stop_{nom}"] = c - E.lado * m * E.rg
        far = c + E.lado * 1000.0 * m * E.rg
        E[f"obj_{nom}"] = far if cierre else np.where(lejos, far, c + m * (E.obj - c))
        specs.append(("PRECIOS", f"obj_{nom}", f"stop_{nom}", "fin"))
    return E, specs


def correr():
    from registro_global import exigir_contada
    exigir_contada("docs/research/friccion_rq_20261119/PREREGISTRO.md")
    from datos import ruta
    from externas_estructurales_a5 import cargar_ctx_m1nt8_rapido
    from edgelab.research import ejecucion as X
    from edgelab.research.embudo_runners import friccion
    from edgelab import costos as C
    E0 = pd.read_csv(EVENTOS)
    E0 = E0[(E0.bloque == "DESC") & E0[list(REGLAS)].any(axis=1)].reset_index(drop=True)   # REP y holdout: ni se calculan
    partes = []
    for inst in ("ES", "NQ", "YM"):
        E = E0[E0.inst == inst].copy()
        ctx = cargar_ctx_m1nt8_rapido(inst, 20060106, 20250731, Path(ruta("M1NT8")))
        E, specs = _columnas(E)
        O = X.desenlaces(E.reset_index(drop=True), ctx, specs)
        fr = float(friccion(inst)[0]); d = C.desglose(inst); tk = d["tick_size"]
        ahorro = (d["spread_ticks"] / 2 + 1.0) * tk                    # salir en el objetivo con orden límite: sin medio spread ni slippage de salida
        c0 = O.stop + O.lado * O.rg; tpR = ((O.obj - c0).abs() / O.rg).where((O.obj - c0).abs() <= LEJOS * O.rg)   # objetivo en R (NaN = lejano)
        for (nom, m, cierre), sp in zip(celdas(), specs):
            r, k = O[f"r_{X.nombre(sp)}"], O[f"k_{X.nombre(sp)}"]
            for regla in REGLAS:
                s = O[regla].astype(bool) & r.notna()
                g = pd.DataFrame(dict(inst=inst, ses=O.ses[s], k=O.k[s], lado=O.lado[s], regla=regla, celda=nom, R=r[s], riesgo=k[s]))
                g["fricR"] = fr / g.riesgo
                g["toca_obj"] = (not cierre) & (g.R >= 0.95 * tpR[s]).fillna(False).to_numpy()
                g["fricR_lim"] = np.where(g.toca_obj, (fr - ahorro) / g.riesgo, g.fricR)
                partes.append(g)
        print(inst, len(O), flush=True)
    P = pd.concat(partes, ignore_index=True); P.to_csv(DIR / "OPS.csv.gz", index=False)
    resumir(P)


def _media_se(g, col):
    s = g.groupby(["inst", "ses"])[col].sum(); n = len(g)
    return float(g[col].mean()), float(s.std(ddof=1) * np.sqrt(len(s)) / n) if len(s) > 1 else None


def resumir(P=None):
    P = pd.read_csv(DIR / "OPS.csv.gz") if P is None else P
    P["neto"] = P.R - P.fricR; P["neto_lim"] = P.R - P.fricR_lim
    res = {}
    for (regla, celda), g in P.groupby(["regla", "celda"]):
        b, seb = _media_se(g, "R"); n_, sen = _media_se(g, "neto")
        p1 = g.sort_values("k").groupby(["inst", "ses"]).head(1)        # una por día y por instrumento (la primera)
        res[f"{regla}|{celda}"] = dict(n=int(len(g)), bruto=b, se_bruto=seb, fricR=float(g.fricR.mean()), neto=n_, se_neto=sen,
                                       neto_ic90_inf=n_ - 1.645 * sen, neto_salida_limite=float(g.neto_lim.mean()),
                                       una_por_dia=dict(n=int(len(p1)), bruto=float(p1.R.mean()), neto=float((p1.R - p1.fricR).mean())))
    dec = {}
    for regla in REGLAS:
        base = res[f"{regla}|esc1"]; mejores = [(c, res[f"{regla}|{c}"]) for c, m, _ in celdas() if m > 1]
        c_b, v_b = max(mejores, key=lambda x: x[1]["neto"])
        esc = v_b["neto"] > 0 and v_b["neto_ic90_inf"] > -0.01 and v_b["bruto"] >= 0.5 * base["bruto"]
        timing = v_b["neto"] <= base["neto"] + (base["se_neto"] or 0)
        dec[regla] = dict(mejor_celda=c_b, veredicto="ESCALABLE" if esc else ("TIMING" if timing else "MEJORA_SIN_NETO"))
    # RQ5 y RQ6 juntas: una sola posición cuando coinciden de lado el mismo día (descriptivo, escala 1)
    q = P[(P.celda == "esc1") & P.regla.isin(["RQ5", "RQ6"])]
    j = q.groupby(["inst", "ses", "lado"]).agg(R=("R", "mean"), fricR=("fricR", "mean"), n=("R", "size")).reset_index()
    juntas = dict(posiciones=int(len(j)), coinciden=int((j.n > 1).sum()), bruto=float(j.R.mean()), neto=float((j.R - j.fricR).mean()),
                  separadas_neto=float((q.R - q.fricR).mean()))
    out = dict(preregistro="docs/research/friccion_rq_20261119/PREREGISTRO.md", celdas=res, decision=dec, rq5_rq6_juntas=juntas)
    (DIR / "RESULTADO.json").write_text(json.dumps(out, indent=1, default=float))
    for k, v in res.items():
        print(k, {x: round(v[x], 3) for x in ("bruto", "fricR", "neto", "neto_ic90_inf", "neto_salida_limite")}, "n", v["n"])
    print(json.dumps(dec)); print(json.dumps(juntas))


if __name__ == "__main__":
    {"correr": correr, "resumir": resumir}[sys.argv[1]]()

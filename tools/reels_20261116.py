#!/usr/bin/env python3
"""Reels del 2026-11-16 (pre-registro docs/research/reels_20261116/PREREGISTRO.md): VIERNES_LUNES, DOS_VELAS, FRANKLIN y E0 de visitas.

  python tools/reels_20261116.py correr <carpeta M1>   # M1 Dukascopy local (NQ_M1_dukas.csv, SP_M1_dukas.csv, DJ_M1_dukas.csv) -> RESULTADO.json
Reusa estrategias_scrapeadas (reglas), m1_intradia.leer_m1 (lector), embudo_runners.friccion (costos) y fundedsync_mecanismos._boot.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "docs/research/reels_20261116"
FUENTES = {"NQ": "NQ_M1_dukas", "ES": "SP_M1_dukas", "YM": "DJ_M1_dukas"}
A, B, REC = ("2012-01-20", "2019-12-31"), ("2020-01-01", "2026-09-29"), ("2025-08-05", "2026-09-29")
NB = 20000
from fundedsync_tanda2 import _bh  # noqa: E402


def ctx_de_csv(path):
    from edgelab.research import m1_intradia as M
    from edgelab.research.estrategias_scrapeadas import ctx_de_m1
    D = M.leer_m1(path); return ctx_de_m1(D[(D.index >= "2012-01-20") & (D.index < "2026-09-30")])


def _boot_media(R, ses, seed=7):
    """Media por operación con bootstrap por sesión: p unilateral (media ≤ 0), IC90, MDE (80 %, α 0,05 unilateral)."""
    u, inv = np.unique(ses, return_inverse=True); s = np.bincount(inv, R); n = np.bincount(inv)
    i = np.random.default_rng(seed).integers(0, len(u), (NB, len(u))); m = s[i].sum(1) / n[i].sum(1); sd = m.std(ddof=1)
    return dict(p=float((1 + (m <= 0).sum()) / (NB + 1)), ic90=[float(np.quantile(m, .05)), float(np.quantile(m, .95))], mde=float(2.486 * sd))


def tramo(df, x0, x1):
    g = df[(df.dia >= x0) & (df.dia <= x1)]
    if len(g) < 30: return dict(n=int(len(g)), R=float(g.R.mean()) if len(g) else None, no_evaluable=True)
    return dict(n=int(len(g)), R=float(g.R.mean()), R_bruto=float(g.Rb.mean()), fric_med=float(g.fricR.median()), acierto=float((g.R > 0).mean()),
                pts_neto=float(g.neto.mean()), **_boot_media(g.R.values, g.fecha.values))


def e0(V):
    """Tasa de visita del mínimo de referencia el día siguiente: por par de días, máximo menor vs no, apertura dentro vs todas."""
    out = {}
    for (dr, k), g in V.groupby(["dow_ref", "salto"]):
        nom = f"ref{dr}_vs_{'previo' if k == 1 else 'dos_antes'}"
        out[nom] = {f"{'menor' if mn else 'no_menor'}_{'dentro' if dn else 'todas'}": dict(n=int(len(x)), visita=float(x.visita.mean()))
                    for mn in (True, False) for dn in (True, False) for x in [g[(g.menor == mn) & (g.dentro | (not dn))]] if len(x)}
    return out


def filtro_t(ctx):
    """FRANKLIN_FILTRO_T: operaciones T con el sesgo VWAP+Londres en su minuto de entrada."""
    from edgelab.research import estrategias_scrapeadas as X
    vw, lh, ll = X._sesgo_franklin(ctx); c = ctx["c"]; tm = ctx["t"] - 60
    o = pd.read_csv(ROOT / "docs/research/fundedsyncstack_20261115/cadena/FUNDEDSYNC_OPS.csv.gz", parse_dates=["dia"]); o = o[o.modulo == "T"].copy()
    k = np.searchsorted(tm, o.t.values, side="right") - 1; k = np.clip(k, 0, len(c) - 1)
    p = c[k]; sesgo = np.where((p > lh[k]) & (p > vw[k]), 1, np.where((p < ll[k]) & (p < vw[k]), -1, 0))
    o["favor"] = sesgo == np.sign(o.side.values); res = {}
    import fundedsync_mecanismos as FM
    for nom, (x0, x1) in (("A", ("2012-01-20", "2019-12-31")), ("B", B)):
        g = o[(o.dia >= x0) & (o.dia <= x1)]; a, r = g[g.favor], g[~g.favor]
        res[nom] = dict(n_favor=int(len(a)), media_favor=float(a.neto.mean()), n_resto=int(len(r)), media_resto=float(r.neto.mean()),
                        **FM._boot(a.neto.values, a.dia.values, r.neto.values, r.dia.values, 7))
    res["pasa"] = bool(res["A"]["dif"] > 0 and res["B"]["dif"] > 0 and res["B"]["p_dif"] < 0.10); return res


def correr(carpeta):
    from edgelab.research import estrategias_scrapeadas as X
    from edgelab.research.embudo_runners import friccion
    res = dict(preregistro="docs/research/reels_20261116/PREREGISTRO.md", pruebas={}, e0={}); filas_p = []
    for inst, arch in FUENTES.items():
        ctx = ctx_de_csv(Path(carpeta) / f"{arch}.csv"); fr = friccion(inst)[0]
        res["e0"][inst] = e0(X.visitas_hougaard(ctx))
        if inst == "NQ": res["franklin_filtro_t"] = filtro_t(ctx); print("filtro T", res["franklin_filtro_t"], flush=True)
        for fam in ("VIERNES_LUNES", "DOS_VELAS", "FRANKLIN"):
            fn, celdas = X.FAMILIAS[fam]; R = fn(ctx)
            for celda in celdas:
                g = R[R.celda.map(tuple) == tuple(celda)].copy()
                g["dia"] = pd.to_datetime(g.fecha.astype(str)); g["neto"] = g.bruto - fr; g["R"] = g.neto / g.riesgo; g["Rb"] = g.bruto / g.riesgo; g["fricR"] = fr / g.riesgo
                clave = f"{fam}|{celda[0]}|{inst}"; r = dict(A=tramo(g, *A), B=tramo(g, *B), reciente=tramo(g, *REC), n_total=int(len(g)))
                res["pruebas"][clave] = r; filas_p.append(clave)
                print(clave, {k: (v.get("n"), v.get("R") and round(v["R"], 3), v.get("p") and round(v["p"], 3), v.get("fric_med") and round(v["fric_med"], 3)) for k, v in r.items() if isinstance(v, dict)}, flush=True)
    ps = [res["pruebas"][k]["B"].get("p", 1.0) for k in filas_p]; bh = _bh(ps)
    for k, b in zip(filas_p, bh):
        r = res["pruebas"][k]; ok = lambda t: t.get("R") is not None and t["R"] > 0 and not t.get("no_evaluable")
        r["nominada_bh"] = bool(b); r["pasa"] = bool(b and ok(r["A"]) and ok(r["B"]) and r["B"].get("fric_med", 9) <= 0.08)
        r["regimen_reciente"] = bool(ok(r["B"]) and not ok(r["A"]))
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1, default=float))
    print({k: (v["pasa"], v["nominada_bh"], v["regimen_reciente"]) for k, v in res["pruebas"].items()})


def _en_r(R, fr):
    g = R.copy(); g["dia"] = pd.to_datetime(g.fecha.astype(str)); g["neto"] = g.bruto - fr; g["R"] = g.neto / g.riesgo
    g["Rb"] = g.bruto / g.riesgo; g["fricR"] = fr / g.riesgo; g["clave"] = g.celda.map(lambda x: "|".join(x)); return g


def franklin_mejoras(carpeta):
    """PREREGISTRO_FRANKLIN_MEJORAS.md: 32 variantes, exploración 2020–2022 (NQ, ES), 3 finalistas, confirmación 2023 → 2026-09."""
    from edgelab.research import estrategias_scrapeadas as X
    from edgelab.research.embudo_runners import friccion
    E, C = ("2020-01-01", "2022-12-31"), ("2023-01-01", "2026-09-29"); ops = {}
    for inst, arch in dict(FUENTES, RTY="USSC2000IDXUSD").items():
        ops[inst] = _en_r(X.franklin_variantes(ctx_de_csv(Path(carpeta) / f"{arch}.csv")), friccion(inst)[0]); print(inst, len(ops[inst]), flush=True)
    base = "1000|rango|ninguno"; expl = {}
    for cl in sorted(ops["NQ"].clave.unique()):
        r = {i: tramo(ops[i][ops[i].clave == cl], *E) for i in ("NQ", "ES")}
        ok = all(not r[i].get("no_evaluable") and r[i]["n"] >= 60 and r[i]["R"] > 0 and r[i]["fric_med"] <= 0.08 for i in r)
        expl[cl] = dict(NQ=r["NQ"], ES=r["ES"], puntaje=float(np.mean([r[i]["R"] or 0 for i in r])), elegible=bool(ok))
    fin = [k for k, v in sorted(expl.items(), key=lambda kv: -kv[1]["puntaje"]) if v["elegible"]][:3]
    def pool(cl, x0, x1):
        g = pd.concat([ops[i][ops[i].clave == cl] for i in ("NQ", "ES")])          # mismo día en NQ y ES = mismo bloque del bootstrap
        return tramo(g, x0, x1)
    conf = {cl: pool(cl, *C) for cl in fin + [base]}
    bh = _bh([conf[cl].get("p", 1.0) for cl in fin]) if fin else []
    for cl, b in zip(fin, bh): conf[cl]["nominada_bh"] = bool(b); conf[cl]["confirma"] = bool(b and conf[cl]["R"] > conf[base]["R"])
    gan = next((cl for cl in fin if conf[cl].get("confirma")), None)
    desc = {cl: {i: dict(A=tramo(ops[i][ops[i].clave == cl], *A), B=tramo(ops[i][ops[i].clave == cl], *B)) for i in ops} for cl in fin + [base]}
    out = dict(preregistro="docs/research/reels_20261116/PREREGISTRO_FRANKLIN_MEJORAS.md", exploracion=expl, finalistas=fin, confirmacion=conf,
               ganadora=gan, al_holdout=gan or base, descriptivo=desc)
    (OUT / "FRANKLIN_MEJORAS.json").write_text(json.dumps(out, indent=1, default=float))
    for cl in fin + [base]: print(cl, "E", round(expl[cl]["puntaje"], 3), "C", conf[cl]["n"], round(conf[cl]["R"], 3), round(conf[cl].get("p", 1), 3), conf[cl].get("confirma"),
                                  {i: (round(desc[cl][i]["B"]["R"], 3), round(desc[cl][i]["A"]["R"], 3)) for i in ops}, flush=True)
    print("ganadora", gan, "al holdout", gan or base)


if __name__ == "__main__":
    {"correr": lambda: correr(sys.argv[2]), "franklin_mejoras": lambda: franklin_mejoras(sys.argv[2])}[sys.argv[1]]()

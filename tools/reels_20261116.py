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


def ctx_de_csv(path):
    from edgelab.research import m1_intradia as M
    D = M.leer_m1(path); D = D[(D.index >= "2012-01-20") & (D.index < "2026-09-30")]
    t = D.index.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT"); ok = ~t.isna(); D = D[ok]; t = t[ok].tz_convert("UTC")
    return dict(t=np.asarray(t.astype("int64") // 10**9, dtype=np.int64) + 60, o=D.o.to_numpy(float), h=D.h.to_numpy(float),
                l=D.l.to_numpy(float), c=D.c.to_numpy(float), v=D.v.to_numpy(float))


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


def _bh(ps, q=0.10):
    ps = np.asarray(ps); o = np.argsort(ps); k = 0
    for j, idx in enumerate(o, 1):
        if ps[idx] <= q * j / len(ps): k = j
    nom = np.zeros(len(ps), bool); nom[o[:k]] = True; return nom.tolist()


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


if __name__ == "__main__":
    {"correr": lambda: correr(sys.argv[2])}[sys.argv[1]]()

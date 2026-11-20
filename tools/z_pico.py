#!/usr/bin/env python3
"""Z-PICO: ¿el pico de fábrica de Z (ZetaTrend, FundedSync) es sobreajuste? ¿Russell tiene el mismo pico?
Pre-registro de la parte de Russell: docs/research/z_pico_20261119/PREREGISTRO.md. La parte de NQ/ES es descriptiva sobre operaciones ya
medidas (neto_pistas_20261119/RZ_OPS.csv.gz). Reusa neto_pistas (_ms, _ops, _cfg, GRILLAS, FABRICA, _nombre), g2.pbo_cscv y holdout.a5_bloque.

  python tools/z_pico.py nq         # rangos, exceso sobre la grilla, «mejor de 27» por bootstrap, PBO por época → NQ_ES.json
  python tools/z_pico.py rty_grilla # grilla de 27 en RTY (reanudable, data/z_pico) → RTY_OPS.csv.gz (sólo meses DESC)
  python tools/z_pico.py rty        # misma batería en RTY → RTY.json
"""
import itertools, json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/z_pico_20261119"; PRE = "docs/research/z_pico_20261119/PREREGISTRO.md"; PARCIAL = ROOT / "data/z_pico"
FAB = "Z_15_20_45"; EPOCAS = [(2008, 2012), (2013, 2017), (2018, 2021), (2022, 2026)]


def _r(G, inst):
    from edgelab import costos
    from edgelab.research.embudo_runners import friccion
    with costos.estimados_permitidos(PRE): fr = float(friccion(inst)[0])
    s = 0.25 * G.atr20; G = G[np.isfinite(s) & (s > 0)].copy(); s = 0.25 * G.atr20
    G["R"] = (np.where(G.mae_pts >= s, -s, G.pnl_pts) - fr) / s
    G["mes"] = pd.to_datetime(G.ses).dt.to_period("M").astype(str); G["anio"] = pd.to_datetime(G.ses).dt.year; return G


def bateria(G, B=2000, seed=7):
    """G: operaciones de las 27 variantes (columnas variante, R, mes, anio). Devuelve el diagnóstico de pico."""
    from edgelab.research import g2
    nombres = sorted(G.variante.unique()); out = {}
    media = G.groupby("variante").R.mean().reindex(nombres)
    out["fabrica"] = float(media[FAB]); out["mediana_grilla"] = float(media.median()); out["exceso"] = float(media[FAB] - media.median())
    out["rango_fabrica"] = int((media > media[FAB]).sum()) + 1; out["positivas"] = int((media > 0).sum()); out["n_var"] = len(nombres)
    p = {n: n.split("_")[1:] for n in nombres}; f = p[FAB]
    vec = [n for n in nombres if sum(a != b for a, b in zip(p[n], f)) == 1]
    out["vecinos"] = {n: round(float(media[n]), 4) for n in vec}; out["vecinos_mediana"] = float(media[vec].median())
    # año por año: rango de la fábrica y exceso sobre la mediana
    A = G.groupby(["anio", "variante"]).R.mean().unstack()
    exc = A[FAB] - A.median(axis=1); out["anios_fabrica_sobre_mediana"] = f"{int((exc > 0).sum())}/{int(exc.notna().sum())}"
    out["rango_por_anio"] = {int(a): int((A.loc[a] > A.loc[a, FAB]).sum()) + 1 for a in A.index if np.isfinite(A.loc[a, FAB])}
    out["por_epoca"] = {}
    for a, b in EPOCAS:
        g = G[(G.anio >= a) & (G.anio <= b)]
        if not len(g): continue
        m = g.groupby("variante").R.mean().reindex(nombres)
        out["por_epoca"][f"{a}-{b}"] = dict(fabrica=round(float(m[FAB]), 4), mediana=round(float(m.median()), 4), rango=int((m > m[FAB]).sum()) + 1, positivas=int((m > 0).sum()))
    # «mejor de 27 por azar»: meses remuestreados, cada variante recentrada a la media de la grilla (H0: ninguna es mejor que la típica)
    S = G.groupby(["mes", "variante"]).R.agg(["sum", "count"]); su = S["sum"].unstack().reindex(columns=nombres).fillna(0); co = S["count"].unstack().reindex(columns=nombres).fillna(0)
    mu = media.to_numpy(); centro = float(np.median(mu)); su0 = su.to_numpy() - co.to_numpy() * (mu - centro)    # cada variante con media = mediana
    rng = np.random.default_rng(seed); M = len(su0); mx = []
    for _ in range(B):
        ix = rng.integers(0, M, M); m = su0[ix].sum(0) / np.maximum(co.to_numpy()[ix].sum(0), 1); mx.append(m.max() - np.median(m))
    mx = np.array(mx); out["p_mejor_de_27"] = float((mx >= out["exceso"]).mean()); out["exceso_azar_p50_p95"] = [float(np.percentile(mx, 50)), float(np.percentile(mx, 95))]
    # exceso de la fábrica por bootstrap de meses (¿es > 0?)
    fi = nombres.index(FAB); ex = []
    for _ in range(B):
        ix = rng.integers(0, M, M); m = su.to_numpy()[ix].sum(0) / np.maximum(co.to_numpy()[ix].sum(0), 1); ex.append(m[fi] - np.median(m))
    out["exceso_ic90"] = [float(np.percentile(ex, 5)), float(np.percentile(ex, 95))]
    out["pbo"] = float(g2.pbo_cscv(su.to_numpy().tolist(), s=16)[0]) if len(su) >= 32 else None
    return out


def nq():
    G = pd.read_csv(ROOT / "docs/research/neto_pistas_20261119/RZ_OPS.csv.gz"); G = G[(G.modulo == "Z") & (G.ses <= "2026-09-29")]
    res = {}
    for inst in ("NQ", "ES"):
        g = _r(G[G.inst == inst], inst); res[inst] = bateria(g)
        res[inst]["desde_2018"] = bateria(g[g.anio >= 2018])
    (DIR / "NQ_ES.json").write_text(json.dumps(res, indent=1, default=float)); print(json.dumps(res, indent=1, default=float)[:6000])


def rty_grilla():
    from registro_global import exigir_contada
    from edgelab.holdout import a5_bloque
    import neto_pistas as NP
    exigir_contada(PRE); PARCIAL.mkdir(parents=True, exist_ok=True); F, D, ms = NP._ms("RTY"); partes = []
    for v in itertools.product(*NP.GRILLAS["Z"].values()):
        nom = NP._nombre("Z", v); f = PARCIAL / f"RTY_{nom}.csv"
        if not f.exists():
            o = NP._ops(F, "Z", ms, D, NP._cfg("Z", v)); o["variante"] = nom; o.to_csv(f, index=False); print(nom, len(o), flush=True)
        partes.append(pd.read_csv(f))
    T = pd.concat(partes, ignore_index=True); T["fecha"] = pd.to_datetime(T.ses).dt.strftime("%Y%m%d").astype(int)
    T = T[np.array([a5_bloque(int(x)) == "DESC" for x in T.fecha]) & (T.fecha <= 20250731).to_numpy()]; T.to_csv(DIR / "RTY_OPS.csv.gz", index=False); print("RTY DESC", len(T))


def rty():
    G = _r(pd.read_csv(DIR / "RTY_OPS.csv.gz"), "RTY"); res = dict(todo=bateria(G), desde_2018=bateria(G[G.anio >= 2018]))
    (DIR / "RTY.json").write_text(json.dumps(res, indent=1, default=float)); print(json.dumps(res, indent=1, default=float)[:5000])


if __name__ == "__main__":
    {"nq": nq, "rty_grilla": rty_grilla, "rty": rty}[sys.argv[1]]()

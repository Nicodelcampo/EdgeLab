#!/usr/bin/env python3
"""RQ5-REGIMEN: lectura pre-registrada (docs/research/rq5_regimen_20261119/PREREGISTRO.md) sobre OPS_DESC_REP.csv.gz de `a5_campana correr`.
Escrita y commiteada ANTES de que existan los desenlaces.

Aclaración (antes de leer): el pre-registro dice «8 vecinos», pero el módulo tiene 5 perillas (L, m, corte, s, tp), así que la fábrica tiene
10 vecinos a un paso (tp: 1,5 y 3; la salida al cierre no es vecino, es P3). El umbral se aplica como proporción: 6/8 = 75 % → ≥ 8 de 10.
P1 se calcula con las celdas que calibran contra ticks (`CALIBRACION.json`), como en el resto de las campañas A5; se publica también con
todas. Decisión: sólo meses DESC del régimen 2018-01-01 → 2025-07-31. REP se informa (contaminada para la fábrica: ver pre-registro).
  python tools/rq5_regimen.py     # -> RESULTADO.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/rq5_regimen_20261119"; PRE = "docs/research/rq5_regimen_20261119/PREREGISTRO.md"
VOTAN = ("NQ", "ES", "YM", "RTY")
R0, R1 = "2018-01-01", "2025-07-31"


def _p_boot(x: pd.DataFrame, col="R", B=2000, seed=7):
    s = x.groupby("ses")[col].agg(["sum", "count"]); rng = np.random.default_rng(seed); n = len(s)
    if n < 5: return float("nan")
    idx = rng.integers(0, n, (B, n)); m = s["sum"].to_numpy()[idx].sum(1) / s["count"].to_numpy()[idx].sum(1)
    return float(np.mean(m <= 0))


def main():
    import edgelab.research.rq5_regimen as M
    from edgelab.research import ejecucion as X
    from edgelab import costos as C
    from edgelab.research.embudo_runners import friccion
    from edgelab.research.diagnostico_grilla import diagnostico, episodios
    from neto_pistas import _supf
    O = pd.read_csv(DIR / "OPS_DESC_REP.csv.gz"); O["fecha"] = pd.to_datetime(O.ses.astype(str)); O["mes"] = O.fecha.dt.to_period("M").astype(str)
    with C.estimados_permitidos(PRE):
        fr = {i: float(friccion(i)[0]) for i in O.inst.unique()}
    cal = json.loads((DIR / "CALIBRACION.json").read_text())["celdas"]
    ejs = {X.nombre(e): e for e in M.EJECUCIONES}
    filas = []
    for d in M.DEFINICIONES:
        g = O[O[d].astype(bool)]
        for en in ejs:
            x = g[g[f"r_{en}"].notna() & (g[f"k_{en}"] > 0)]
            filas.append(pd.DataFrame(dict(celda=f"{d}|{en}", d=d, e=en, inst=x.inst, ses=x.ses, mes=x.mes, fecha=x.fecha, bloque=x.bloque,
                                           Rb=x[f"r_{en}"], R=x[f"r_{en}"] - x.inst.map(fr) / x[f"k_{en}"], fR=x.inst.map(fr) / x[f"k_{en}"])))
    T = pd.concat(filas, ignore_index=True)
    reg = T[(T.bloque == "DESC") & (T.fecha >= R0) & (T.fecha <= R1)]
    fab = f"{M.DEF_FABRICA}|{[n for n in ejs if f'_{M.EJ_FABRICA}_' in n][0]}"
    res = dict(fabrica=fab, friccion=fr)
    # ---- P1: meseta (NQ+ES+YM+RTY)
    v = reg[reg.inst.isin(VOTAN)]
    cel = v.groupby("celda").agg(n=("R", "size"), R=("R", "mean"), Rb=("Rb", "mean"), fR=("fR", "median"))
    cel["calibra"] = [bool(cal.get(c, {}).get("calibra")) for c in cel.index]
    ev = cel[cel.n >= 30]; evc = ev[ev.calibra]
    pf = _p_boot(v[v.celda == fab])
    # vecinos a un paso
    L0, m0, c0, s0, t0 = 60, 1.0, 689, 0.45, 2.0
    def nom(L, m, c, s, t): return f"{M._ndef(L, m, c)}|P_obj_{M._nej(s, t)}_stop_{M._nej(s, t)}_fin"
    vec = [nom(L, m0, c0, s0, t0) for L in (40, 90)] + [nom(L0, m, c0, s0, t0) for m in (0.8, 1.2)] + [nom(L0, m0, c, s0, t0) for c in (659, 719)] + \
          [nom(L0, m0, c0, s, t0) for s in (0.30, 0.60)] + [nom(L0, m0, c0, s0, t) for t in (1.5, 3.0)]
    vv = {c: (float(cel.R[c]) if c in cel.index else None) for c in vec}
    n_vec_pos = sum(1 for x in vv.values() if x is not None and x > 0)
    res["P1"] = dict(fabrica=dict(n=int(cel.n[fab]), R=float(cel.R[fab]), Rb=float(cel.Rb[fab]), fR=float(cel.fR[fab]), p=pf),
                     celdas_evaluables=int(len(ev)), positivas=float((ev.R > 0).mean()), celdas_calibradas_evaluables=int(len(evc)),
                     positivas_calibradas=float((evc.R > 0).mean()), mediana_R=float(ev.R.median()), vecinos=vv, vecinos_positivos=n_vec_pos,
                     pasa=bool(cel.R[fab] > 0 and pf < 0.05 and (evc.R > 0).mean() >= 0.70 and n_vec_pos >= 8))
    per = {"L": lambda c: c.split("|")[0].split("_")[0], "m": lambda c: c.split("|")[0].split("_")[1], "corte": lambda c: c.split("|")[0].split("_")[2],
           "s": lambda c: c.split("|")[1].split("_")[2], "tp": lambda c: c.split("|")[1].split("_")[3]}
    dg = diagnostico(v.rename(columns={"celda": "variante"}), "variante", "R", "mes", per)
    res["P1"]["diagnostico"] = {k: dg[k] for k in ("linea", "numero_efectivo", "perillas", "perillas_inertes", "spearman_ops_R")}
    res["P1"]["episodios_fabrica"] = episodios(v[v.celda == fab], "R", "mes")["linea"]
    # ---- P2: multiactivo
    p2 = {}
    for i in list(VOTAN) + ["EMD"]:
        x = reg[(reg.celda == fab) & (reg.inst == i)]
        p2[i] = dict(n=int(len(x)), R=float(x.R.mean()) if len(x) else None, Rb=float(x.Rb.mean()) if len(x) else None,
                     fR=float(x.fR.median()) if len(x) else None, p=_p_boot(x) if len(x) else None, vota=i in VOTAN)
    res["P2"] = dict(instrumentos=p2, positivos=sum(1 for i in VOTAN if (p2[i]["R"] or 0) > 0), pasa=sum(1 for i in VOTAN if (p2[i]["R"] or 0) > 0) >= 3)
    # ---- P3: salida al cierre contra tp 2 (pareado por evento, fábrica)
    cie = f"{M.DEF_FABRICA}|P_obj_{M._nej(0.45, 0.0)}_stop_{M._nej(0.45, 0.0)}_fin"
    a = reg[(reg.celda == fab) & reg.inst.isin(VOTAN)].set_index(["inst", "ses"]).R; b = reg[(reg.celda == cie) & reg.inst.isin(VOTAN)].set_index(["inst", "ses"]).R
    ix = a.index.intersection(b.index); dd = (b.reindex(ix) - a.reindex(ix)).reset_index().rename(columns={"R": "D"}); dd["ses"] = dd.ses
    res["P3"] = dict(n=int(len(dd)), contraste=float(dd.D.mean()), p=_p_boot(dd, "D"), R_cierre=float(b.reindex(ix).mean()), R_tp2=float(a.reindex(ix).mean()))
    res["P3"]["adopta"] = bool(res["P3"]["contraste"] > 0 and res["P3"]["p"] < 0.05)
    # ---- informativos: épocas, corte sup-F, mensual, REP (contaminada para la fábrica)
    f4 = T[(T.celda == fab) & T.inst.isin(VOTAN)]
    ep = {}
    for nm, (a0, a1) in {"2006-2017": ("2006-01-01", "2017-12-31"), "2018-2025.07": (R0, R1)}.items():
        for bl in ("DESC", "REP"):
            x = f4[(f4.bloque == bl) & (f4.fecha >= a0) & (f4.fecha <= a1)]; ep[f"{nm}|{bl}"] = dict(n=int(len(x)), R=float(x.R.mean()) if len(x) else None)
    res["epocas"] = ep
    md = f4[f4.bloque == "DESC"].groupby("mes").R.sum(); mm = md.index.to_numpy()
    k, pk = _supf(md.to_numpy(), meses=mm); res["supF"] = dict(quiebre=str(mm[k]) if k is not None else None, p=float(pk))
    m = v[v.celda == fab].groupby("mes").R.sum()
    res["mensual"] = dict(ops_mes=float(len(v[v.celda == fab]) / m.size), R_mes=float(m.mean()), t=float(m.mean() / m.std() * np.sqrt(m.size)), pos=float((m > 0).mean()))
    res["veredicto"] = "REGIMEN_ROBUSTO" if res["P1"]["pasa"] and res["P2"]["pasa"] else ("INTERMEDIO" if res["P1"]["pasa"] or res["P2"]["pasa"] else "SIN_REGIMEN")
    res["regla_congelada"] = cie if res["P3"]["adopta"] else fab
    (DIR / "RESULTADO.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps({k: res[k] for k in ("veredicto", "regla_congelada", "mensual", "supF")}, default=float))
    print("P1", {k: res["P1"][k] for k in ("fabrica", "positivas_calibradas", "vecinos_positivos", "pasa")})
    print("P2", res["P2"]); print("P3", res["P3"]); print(res["P1"]["diagnostico"]["linea"]); print(res["P1"]["episodios_fabrica"])




def holdout():
    """Apertura única del holdout A5 (ADENDA_APERTURA_HOLDOUT.md; registrada en HOLDOUT_VENTANAS antes de calcular): regla congelada = fábrica,
    meses HOLDOUT 2018-01-01 → 2026-09-30, cinco índices. -> HOLDOUT.json"""
    import edgelab.research.rq5_regimen as M
    from edgelab.research import a5 as A5, ejecucion as X, rasgos_comunes as RC
    from edgelab.research import holdout_ventanas as HV
    from edgelab import costos as C
    from edgelab.research.embudo_runners import friccion
    from edgelab.research.diagnostico_grilla import episodios
    from a5_campana import _ctx
    from math import log
    from statistics import NormalDist
    if not HV.aperturas_vigentes("RQ5_REGIMEN"): raise SystemExit("sin apertura registrada: no se calcula el holdout")
    ej = [e for e in M.EJECUCIONES if X.nombre(e).endswith(f"_{M.EJ_FABRICA}_fin") and f"obj_{M.EJ_FABRICA}" in X.nombre(e)]
    en = X.nombre(ej[0]); partes = []
    with C.estimados_permitidos(PRE):
        fr = {i: float(friccion(i)[0]) for i in ("NQ", "ES", "YM", "RTY", "EMD")}
    for inst in fr:
        ctx = _ctx(inst, None, 20170901, 20260930); E = M.eventos(ctx); k = E.k.to_numpy(np.int64)
        E["ses"] = np.asarray(ctx["ses"])[k]; E["t"] = np.asarray(ctx["t"], float)[k]; E["bloque"] = A5.bloques(E.ses.to_numpy())
        E = E[E[M.DEF_FABRICA].astype(bool) & (E.bloque == "HOLDOUT") & (E.ses >= 20180101) & (E.ses <= 20260930)].reset_index(drop=True)
        O = X.desenlaces(RC.agregar(E, ctx), ctx, ej); O["inst"] = inst; partes.append(O)
    O = pd.concat(partes, ignore_index=True); O = O[O[f"r_{en}"].notna() & (O[f"k_{en}"] > 0)]
    O["R"] = O[f"r_{en}"] - O.inst.map(fr) / O[f"k_{en}"]; O["mes"] = pd.to_datetime(O.ses.astype(str)).dt.to_period("M").astype(str)
    O[["ses", "t", "inst", "lado", "R", f"r_{en}", f"k_{en}"]].to_csv(DIR / "HOLDOUT_OPS.csv.gz", index=False)
    p = _p_boot(O); pdev = 0.0445
    chi = -2 * (log(max(p, 1e-6)) + log(pdev))                       # Fisher, 4 g.l.: P(χ²₄ > x) = e^(−x/2)(1 + x/2)
    pf = float(np.exp(-chi / 2) * (1 + chi / 2))
    sd = float(O.R.std()); mde = 2.486 * sd / np.sqrt(len(O))
    res = dict(n=int(len(O)), R=float(O.R.mean()), sd=sd, p=p, p_desarrollo=pdev, p_fisher=pf, mde80=float(mde),
               por_inst={i: dict(n=int((O.inst == i).sum()), R=float(O[O.inst == i].R.mean()), p=_p_boot(O[O.inst == i])) for i in fr},
               cuatro_votantes=dict(n=int(O.inst.isin(VOTAN).sum()), R=float(O[O.inst.isin(VOTAN)].R.mean()), p=_p_boot(O[O.inst.isin(VOTAN)])),
               tramo_2025_09_2026_09=dict(n=int((O.ses >= 20250901).sum()), R=float(O[O.ses >= 20250901].R.mean()) if (O.ses >= 20250901).any() else None),
               episodios=episodios(O, "R", "mes")["linea"])
    m = O.groupby("mes").R.sum(); res["mensual"] = dict(meses=int(m.size), R_mes=float(m.mean()), pos=float((m > 0).mean()))
    res["lectura"] = ("CONFIRMA" if p < 0.05 else "APOYA" if pf < 0.05 else "NO_CONCLUYENTE" if res["R"] > 0 else "EN_CONTRA")
    (DIR / "HOLDOUT.json").write_text(json.dumps(res, indent=1, default=float) + "\n"); print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    holdout() if sys.argv[1:] == ["holdout"] else main()

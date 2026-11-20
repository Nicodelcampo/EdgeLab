#!/usr/bin/env python3
"""CONFLUENCIA (pre-registro docs/research/confluencia_20261119/PREREGISTRO.md): señales intradía con bruto real (SOM, Franklin, FM1, FM2,
RQ5, RQ6) operadas sólo cuando otra regla ya confirmó la dirección del día. Sin motor nuevo: lee operaciones ya calculadas.

  python tools/confluencia.py desc    # → OPS.csv.gz, DESC.json (commitear antes de rep)
  python tools/confluencia.py rep     # P1/P2 nominadas con potencia en días ≥ 0,8 (K49), una vez con LORD++ → REP.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/confluencia_20261119"; PRE = "docs/research/confluencia_20261119/PREREGISTRO.md"; FAM = "CONFLUENCIA_A5"
INST = ("NQ", "ES"); FIN = 20250731
HORA = {"SOM": 575, "FRANKLIN": 600, "FM1": 600, "RQ5": 600, "RQ6": 630}          # minuto NY (FM2: su hora exacta)
CONFIRMA = {"SOM", "FRANKLIN", "FM1", "FM2"}                                       # RQ5/RQ6 no confirman (sin hora exacta)


def operaciones():
    from edgelab.research.embudo_runners import friccion
    from edgelab.holdout import a5_bloque
    p = []
    T = pd.read_csv(ROOT / "docs/research/mejora_sf_20261119/TABLA.csv.gz"); T = T[T.inst.isin(INST)]
    p.append(pd.DataFrame(dict(estrategia=T.estrategia, inst=T.inst, fecha=T.fecha.astype(int), lado=T.lado.astype(int), hora=T.estrategia.map(HORA), R=T.R)))
    Q = pd.read_csv(ROOT / "docs/research/friccion_rq_20261119/OPS.csv.gz"); Q = Q[(Q.celda == "esc1") & Q.regla.isin(["RQ5", "RQ6"]) & Q.inst.isin(INST)]
    p.append(pd.DataFrame(dict(estrategia=Q.regla, inst=Q.inst, fecha=Q.ses.astype(int), lado=Q.lado.astype(int), hora=Q.regla.map(HORA), R=Q.R - Q.fricR)))
    F = pd.read_csv(ROOT / "docs/research/flujos_macro_20261119/OPS_DESC_REP.csv.gz"); F = F[F.inst.isin(INST) & F.r_P_obj_stop_fin.notna()]
    mins = pd.to_datetime(F.t, unit="s", utc=True).dt.tz_convert("America/New_York"); F = F.assign(minuto=(mins.dt.hour * 60 + mins.dt.minute).to_numpy())
    fr = {i: float(friccion(i)[0]) for i in INST}
    for d in ("FM1", "FM2"):
        g = F[F[d].astype(bool)]
        p.append(pd.DataFrame(dict(estrategia=d, inst=g.inst, fecha=g.ses.astype(int), lado=g.lado.astype(int),
                                   hora=(600 if d == "FM1" else g.minuto), R=g.r_P_obj_stop_fin - g.inst.map(fr) / g.rg)))
    O = pd.concat(p, ignore_index=True); O = O[(O.fecha <= FIN) & np.isfinite(O.R)]
    O["bloque"] = [a5_bloque(int(x)) for x in O.fecha]; O = O[O.bloque.isin(["DESC", "REP"])].reset_index(drop=True)
    conf = np.zeros(len(O), int)
    for (i, f), g in O.groupby(["inst", "fecha"]):
        for a in g.itertuples():
            n = 0
            for b in g.itertuples():
                if b.Index == a.Index or b.estrategia == a.estrategia or b.estrategia not in CONFIRMA or b.lado != a.lado: continue
                lim = 600 if (b.estrategia == "FM2" and a.estrategia in ("RQ5", "RQ6")) else a.hora
                if b.hora <= lim: n += 1
            conf[a.Index] = n
    O["confirmaciones"] = conf; return O


def _pruebas(O):
    from carril2 import _media
    from edgelab.research import a5 as A5
    c, s = O[O.confirmaciones >= 1], O[O.confirmaciones == 0]
    d, se, p1 = A5.diferencia(c.fecha.to_numpy(), c.R.to_numpy(), s.fecha.to_numpy(), s.R.to_numpy())
    m, se2, p2 = _media(c.fecha.to_numpy(), c.R.to_numpy())
    return dict(P1=dict(dif=d, se=se, p=p1, R_conf=float(c.R.mean()), R_sin=float(s.R.mean()), n_conf=int(len(c)), n_sin=int(len(s))),
                P2=dict(R=m, se=se2, p=p2, n=int(len(c))))


def desc():
    from registro_global import exigir_contada
    from edgelab.research.a5 import bh
    from edgelab.research.diagnostico_grilla import episodios
    exigir_contada(PRE)
    O = operaciones(); O.to_csv(DIR / "OPS.csv.gz", index=False); D = O[O.bloque == "DESC"].copy()
    res = _pruebas(D); rech = bh([res["P1"]["p"], res["P2"]["p"]], 0.10)
    res["P1"]["bh"], res["P2"]["bh"] = bool(rech[0] and res["P1"]["dif"] > 0), bool(rech[1] and res["P2"]["R"] > 0)
    res["por_estrategia"] = {e: dict(n=int(len(g)), R=float(g.R.mean()), frac_conf=float((g.confirmaciones >= 1).mean()),
                                     R_conf=float(g[g.confirmaciones >= 1].R.mean()) if (g.confirmaciones >= 1).any() else None,
                                     R_sin=float(g[g.confirmaciones == 0].R.mean()), R_2mas=float(g[g.confirmaciones >= 2].R.mean()) if (g.confirmaciones >= 2).any() else None)
                             for e, g in D.groupby("estrategia")}
    res["por_n_conf"] = {int(k): dict(n=int(len(g)), R=float(g.R.mean())) for k, g in D.groupby(D.confirmaciones.clip(upper=3))}
    D["mes"] = (D.fecha // 100).astype(str); res["episodios_confirmadas"] = episodios(D[D.confirmaciones >= 1])["linea"]
    res["nominadas"] = [k for k in ("P1", "P2") if res[k]["bh"]]
    (DIR / "DESC.json").write_text(json.dumps(dict(preregistro=PRE, **res), indent=1, default=float)); print(json.dumps(res, indent=1, default=float)[:4000])


def rep():
    from a5_campana import _commiteado
    from edgelab.research import a5 as A5
    from edgelab.funnel.libro_lord import LibroLord
    if not _commiteado(DIR / "DESC.json"): raise SystemExit("DESC.json sin commitear")
    J = json.loads((DIR / "DESC.json").read_text()); O = pd.read_csv(DIR / "OPS.csv.gz"); out = {}
    D = O[(O.bloque == "DESC") & (O.confirmaciones >= 1)]; n_rep = int(O[(O.bloque == "REP") & (O.confirmaciones >= 1)].fecha.nunique())
    plan = A5.plan_lectura(FAM, D.fecha.to_numpy(), D.R.to_numpy(float), n_rep); out["plan_P2"] = plan
    if not J["nominadas"] or (plan.get("potencia") or 0) < A5.POTENCIA_LECTURA_MIN:
        out["estado"] = "SIN_NOMINADAS" if not J["nominadas"] else "SIN_POTENCIA_PREVIA"
    else:
        r = _pruebas(O[O.bloque == "REP"]); dec = LibroLord().probar(FAM, "REP_CONFLUENCIA", [(k, r[k]["p"]) for k in J["nominadas"]])
        out.update(rep=r, lord=dec, confirmadas=dec.get("confirmadas"))
    (DIR / "REP.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps(out, default=float)[:2000])


if __name__ == "__main__":
    {"desc": desc, "rep": rep}[sys.argv[1]]()

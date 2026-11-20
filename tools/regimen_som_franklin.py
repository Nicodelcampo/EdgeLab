#!/usr/bin/env python3
"""REGIMEN-SOM-FRANKLIN: meseta, PBO y quiebre (procedimientos de T-REGIMEN) para SOM y Franklin
(pre-registro docs/research/regimen_som_franklin_20261119/PREREGISTRO.md).

Reusa los motores de `tools/m1_largo.py` (`quantlab_mt5_medir.ops_som`, `estrategias_scrapeadas.franklin_variantes`, `reels_20261116._en_r`),
la fricción canónica, `g2.pbo_cscv`, `g2.parameter_sensitivity` y `neto_pistas._supf`.

  python tools/regimen_som_franklin.py grilla     # SOM 81 × (NQ, ES, YM) y Franklin 32 × (NQ, ES) → data/regimen_sf (reanudable) + OPS.csv.gz
  python tools/regimen_som_franklin.py prefijo    # causalidad por prefijo de las fábricas (corte 2015-06-30)
  python tools/regimen_som_franklin.py decidir    # (a) señal bruta y (b) régimen neto → RESULTADO.json
"""
import itertools, json, sys
from dataclasses import replace
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/regimen_som_franklin_20261119"; PRE = "docs/research/regimen_som_franklin_20261119/PREREGISTRO.md"
PARCIAL = ROOT / "data/regimen_sf"; FIN = 20260929
SOM_G = dict(fast_ema=[8, 12, 16], trail_ema=[80, 120, 160], trail_start_r=[0.25, 0.5, 0.75], sl_atr_mult=[6.0, 8.0, 10.0])
SOM_FAB = (12, 120, 0.5, 8.0)
FR_FAB = ("1000", "rango", "ninguno")
INST = {"SOM": ("NQ", "ES", "YM"), "FRANKLIN": ("NQ", "ES")}


def _som_nombre(v): return "SOM_" + "_".join(f"{x:g}" for x in v)
def _fr_nombre(c): return "FR_" + "|".join(c)


def _som(inst, D, v):
    from edgelab.research.quantlab_mt5.contracts import SessionOpenMomentumConfig
    from edgelab.research.m1_intradia import SERVIDOR_MENOS_NY
    from edgelab.research.embudo_runners import friccion
    from quantlab_mt5_medir import ops_som, FUENTES
    srv = (D.index + pd.Timedelta(hours=SERVIDOR_MENOS_NY)).tz_localize("UTC")
    df = pd.DataFrame(dict(time=srv, ts_ns=srv.asi8, open=D.o.to_numpy(), high=D.h.to_numpy(), low=D.l.to_numpy(), close=D.c.to_numpy(), volume=D.v.to_numpy()))
    cfg = replace(SessionOpenMomentumConfig(), close_weekend=True, **dict(zip(SOM_G, v)))
    return ops_som(df, cfg, FUENTES.get(inst, (None, "USA500"))[1], friccion(inst)[0])


def _franklin(inst, D, celdas):
    from edgelab.research import estrategias_scrapeadas as X
    from edgelab.research.embudo_runners import friccion
    from reels_20261116 import _en_r
    R = X.franklin_variantes(X.ctx_de_m1(D), celdas=celdas); g = _en_r(R, friccion(inst)[0])
    if "celda" not in g: g["celda"] = R["celda"].values
    return g


def grilla():
    from registro_global import exigir_contada
    from datos import ruta
    from m1_largo import cargar
    from edgelab.research.estrategias_scrapeadas import FRV_CELDAS
    exigir_contada(PRE); PARCIAL.mkdir(parents=True, exist_ok=True)
    for inst in ("NQ", "ES", "YM"):
        D = cargar(inst, ruta("M1NT8"))
        for v in itertools.product(*SOM_G.values()):
            f = PARCIAL / f"{inst}_{_som_nombre(v)}.csv"
            if f.exists(): continue
            _som(inst, D, v).assign(inst=inst, estrategia="SOM", variante=_som_nombre(v)).to_csv(f, index=False)
            print(inst, _som_nombre(v), flush=True)
        if inst in INST["FRANKLIN"] and not (PARCIAL / f"{inst}_FRANKLIN.csv").exists():
            g = _franklin(inst, D, FRV_CELDAS); g["variante"] = ["FR_" + (c if isinstance(c, str) else "|".join(c)) for c in g.celda]
            g.drop(columns=["celda"]).assign(inst=inst, estrategia="FRANKLIN").to_csv(PARCIAL / f"{inst}_FRANKLIN.csv", index=False)
            print(inst, "FRANKLIN", len(g), flush=True)
    pd.concat([pd.read_csv(f) for f in sorted(PARCIAL.glob("*.csv"))]).to_csv(DIR / "OPS.csv.gz", index=False)


def prefijo():
    from datos import ruta
    from m1_largo import cargar
    D = cargar("NQ", ruta("M1NT8")); Dc = D[D.index < "2015-07-01"]; out = {}
    for nom, fn in (("SOM", lambda X: _som("NQ", X, SOM_FAB)), ("FRANKLIN", lambda X: _franklin("NQ", X, [FR_FAB]))):
        a, b = fn(D), fn(Dc); a = a[a.fecha < 20150630].reset_index(drop=True); b = b[b.fecha < 20150630].reset_index(drop=True)
        igual = len(a) == len(b) and np.allclose(a.bruto.to_numpy(float), b.bruto.to_numpy(float)) and np.allclose(a.riesgo.to_numpy(float), b.riesgo.to_numpy(float))
        out[nom] = dict(n_completa=int(len(a)), n_cortada=int(len(b)), identicas=bool(igual))
    (DIR / "PREFIJO.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))


def _vecinos_som():
    vec = []
    for i, b in enumerate(SOM_FAB):
        vals = list(SOM_G.values())[i]; j = vals.index(b)
        for jj in (j - 1, j + 1):
            if 0 <= jj < len(vals): v = list(SOM_FAB); v[i] = vals[jj]; vec.append(_som_nombre(tuple(v)))
    return vec


def _vecinos_fr():
    from edgelab.research.estrategias_scrapeadas import FRV_CELDAS
    return [_fr_nombre(c) for c in FRV_CELDAS if sum(a != b for a, b in zip(c, FR_FAB)) == 1]


def _evaluar(W, col, nombres, fab, vecinos):
    from edgelab.research import g2
    rv = W.groupby("variante")[col].mean().reindex(nombres)
    M = W.assign(mes=(W.fecha // 100)).pivot_table(index="mes", columns="variante", values=col, aggfunc="sum").reindex(columns=nombres).fillna(0.0)
    pbo = g2.pbo_cscv(M.to_numpy().tolist(), s=16)[0]; mv, pv, nv = g2.parameter_sensitivity(rv.to_dict(), fab, vecinos)
    return dict(R_fabrica=float(rv[fab]), frac_positivas=float((rv > 0).mean()), mediana=float(rv.median()), vecinos=dict(mediana=mv, positivos=pv, n=nv),
                pbo=float(pbo), meses=int(len(M)), por_variante=rv.round(4).to_dict())


def _veredicto(e, positivo, frag, rob):
    meseta = e["frac_positivas"] >= 0.70 and (e["vecinos"]["mediana"] or 0) > 0 and (positivo is None or e["mediana"] >= 0.5 * e["R_fabrica"])
    return frag if (e["pbo"] > 0.5 or e["frac_positivas"] < 0.5) else (rob if (meseta and e["pbo"] < 0.3) else "INTERMEDI" + ("A" if rob.startswith("SENAL") else "O"))


def decidir():
    from neto_pistas import _supf
    from edgelab.research.estrategias_scrapeadas import FRV_CELDAS
    G = pd.read_csv(DIR / "OPS.csv.gz"); G = G[(G.riesgo > 0) & (G.fecha <= FIN)]
    out = {}
    for est, nombres, fab, vec in (("SOM", [_som_nombre(v) for v in itertools.product(*SOM_G.values())], _som_nombre(SOM_FAB), _vecinos_som()),
                                   ("FRANKLIN", [_fr_nombre(c) for c in FRV_CELDAS], _fr_nombre(FR_FAB), _vecinos_fr())):
        W = G[G.estrategia == est]
        a = _evaluar(W, "Rb", nombres, fab, vec); a["veredicto"] = _veredicto(a, None, "SENAL_FRAGIL", "SENAL_ROBUSTA")
        f = W[W.variante == fab].sort_values(["fecha", "inst"])
        kq, pq = _supf(f.R.to_numpy(), meses=(f.fecha // 100).to_numpy()); q = int(f.fecha.iloc[kq])
        desde = q if pq <= 0.05 else int(W.fecha.min())
        b = _evaluar(W[W.fecha >= desde], "R", nombres, fab, vec); b["veredicto"] = _veredicto(b, True, "SOBREAJUSTE_PROBABLE", "REGIMEN_ROBUSTO")
        b.update(quiebre=q, p_quiebre=pq, ventana_desde=desde, R_fabrica_antes=float(f[f.fecha < q].R.mean()), R_fabrica_despues=float(f[f.fecha >= q].R.mean()),
                 frac_positivas_antes=float((W[W.fecha < q].groupby("variante").R.mean().reindex(nombres) > 0).mean()))
        an = f.groupby(f.fecha // 10000).R.mean()
        b["anios_positivos_fabrica"] = f"{int((an > 0).sum())}/{len(an)}"; b["R_fabrica_por_anio"] = an.round(3).to_dict()
        b["R_fabrica_por_inst_ventana"] = f[f.fecha >= desde].groupby("inst").R.mean().round(3).to_dict()
        out[est] = dict(senal_bruta=a, regimen_neto=b)
        print(est, "(a)", a["veredicto"], {k: a[k] for k in ("R_fabrica", "frac_positivas", "mediana", "vecinos", "pbo")})
        print(est, "(b)", b["veredicto"], {k: b[k] for k in ("quiebre", "p_quiebre", "ventana_desde", "R_fabrica", "frac_positivas", "mediana", "vecinos", "pbo",
                                                          "R_fabrica_antes", "R_fabrica_despues", "frac_positivas_antes", "anios_positivos_fabrica", "R_fabrica_por_inst_ventana")})
    (DIR / "RESULTADO.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"grilla": grilla, "prefijo": prefijo, "decidir": decidir}[sys.argv[1]]()

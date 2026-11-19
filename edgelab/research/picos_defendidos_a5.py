"""PICOS-DEFENDIDOS en M1 largo con la partición HOLDOUT-A5 (2026-11-19): versión corregida de la campaña del PR #200.

Auditoría: docs/research/agente/AUDITORIA_PICOS_DEFENDIDOS_20261119.md. Pre-registro: docs/research/picos_defendidos_a5_20261119/PREREGISTRO.md.
Reutiliza la detección del PR (`edgelab/research/agente/picos_defendidos.py`: velas_tf, niveles_picos, detectar, _tendencia, _niveles_arr)
sin cambiarla; lo que cambia es QUÉ se mide y DÓNDE:
  - la regla exacta de la captura de Nico primero (ritual «idea vista en el visor»), con su control (tendencia en contra);
  - una familia chica pre-registrada (12 definiciones × 2 ejecuciones) en lugar de 207.360 celdas sobre 8 meses;
  - temporalidades 5, 10 y 15 min (1 y 3 min quedan fuera: el riesgo mínimo de 0,5 ATR de 1 min es del orden de la fricción, K4–K9);
  - contrato de `edgelab/research/tablas.py` + `tools/a5_campana.py` (M1 real de futuros desde 2006, meses DESC/REP de A5, motor único).
Base de la captura (10 min, nivel PAR, tendencia E20 a favor, disparo ALEJA, stop 1 tick detrás del extremo del alejamiento 2):
  PD0   base                                   PD0C  control: igual con la tendencia EN CONTRA
  PD1–PD8  base con cada uno de los otros 8 disparadores (REACERCA_33, REACERCA_50, EMA_TOQUE, EMA_DOBLE_CRUCE, CRUCE_EMAS,
           ESPEJO_75, ESPEJO_100, POC)
  PD9 / PD10  base en 5 y 15 min               PD11  base sin filtro de tendencia (la variante «sin filtro» de Nico)
Ejecuciones: objetivo P + 0,5 A y P + 1 A (precios por fila; stop estructural con riesgo mínimo 0,5 A, como en el PR).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.agente import picos_defendidos as PD
from edgelab.research.zonas_gaps import _atr_causal
from edgelab.research.estrategias._indicadores_ext import ema

NOMBRE = "PICOS-DEF-A5"
TFS = (5, 10, 15)
PICO = 2                                                     # índice de PD.PICOS: "PAR"
DEF = 0                                                      # índice de PD.DEFS: "E20"
D = {n: i for i, n in enumerate(PD.DISPARADORES)}
EJECUCIONES = [("PRECIOS", "obj05", "stop"), ("PRECIOS", "obj1", "stop")]
DEFINICIONES = ["PD0", "PD1", "PD2", "PD3", "PD4", "PD5", "PD6", "PD7", "PD8", "PD9", "PD10", "PD11"]
CONTROL = {"PD0": "PD0C"}
DEPENDENCIAS_KERNEL = ("edgelab.research.agente.picos_defendidos",)


def _filas(ctx) -> pd.DataFrame:
    t = np.asarray(ctx["t"], np.int64); ses_m1 = np.asarray(ctx["ses"], np.int64); tick = float(ctx["tick"])
    o, h, l, c = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c"))
    vps, vpp, vpv = np.asarray(ctx["vp_start"], np.int64), np.asarray(ctx["vp_px"], float), np.asarray(ctx["vp_vol"], float)
    _, r, par = PD.PICOS[PICO]; _, cruce_def, pe, pf, ps = PD.DEFS[DEF]; partes = []
    for tf in TFS:
        O, H, L, C, S, K, _ = PD.velas_tf(t, o, h, l, c, ses_m1, tf)
        if len(C) < 30: continue
        A = _atr_causal(H, L, C); emas = {p: ema(C, p) for p in {pe, pf, ps}}
        for signo, lado in ((1, 1), (-1, -1)):
            xh, xl, xc = (H, L, C) if signo == 1 else (-L, -H, -C)
            ni, nc, npx = PD.niveles_picos(xh, xl, S, A, r, par, 1)
            if not len(ni): continue
            et, ef, es = signo * emas[pe], signo * emas[pf], signo * emas[ps]
            F, desb = PD.detectar(xh, xl, xc, S, A, K, ni, nc, npx, et, ef, es, signo, vps, vpp, vpv, tick,
                                  PD.X1_MIN, PD.D_MAX, PD.X2_MIN, PD.ESPERA, PD.CRUCE_X, PD.MAX_CAND)
            if desb: raise RuntimeError(f"{NOMBRE}: {desb} niveles descartados por tope (tf {tf})")
            if not len(F): continue
            Z = np.array(F, float); i = Z[:, 0].astype(np.int64); td = PD._tendencia(xc, et, ef, es, cruce_def)
            partes.append(pd.DataFrame(dict(k=K[i], lado=lado, tf=tf, tend=td[i], disp=Z[:, 1].astype(np.int64), alej1=Z[:, 4],
                                            cerca=Z[:, 5], alej2=Z[:, 6], P=signo * Z[:, 2], ext2=signo * Z[:, 7], A=Z[:, 3])))
    if not partes: return pd.DataFrame(columns=["k", "lado", "tf", "tend", "disp", "alej1", "cerca", "alej2", "P", "ext2", "A"])
    X = pd.concat(partes, ignore_index=True)
    X = X.sort_values(["k", "tf", "lado", "disp", "alej1"], ascending=[True] * 4 + [False], kind="stable")
    return X.drop_duplicates(["k", "tf", "lado", "disp"]).reset_index(drop=True)      # regla de deduplicación del PR


def eventos(ctx) -> pd.DataFrame:
    X = _filas(ctx)
    base = (X.tf == 10) & (X.tend == 0)
    cols = {"PD0": base & (X.disp == D["ALEJA"]), "PD0C": (X.tf == 10) & (X.tend == 1) & (X.disp == D["ALEJA"])}
    for j, n in enumerate(("REACERCA_33", "REACERCA_50", "EMA_TOQUE", "EMA_DOBLE_CRUCE", "CRUCE_EMAS", "ESPEJO_75", "ESPEJO_100", "POC")):
        cols[f"PD{j + 1}"] = base & (X.disp == D[n])
    cols["PD9"] = (X.tf == 5) & (X.tend == 0) & (X.disp == D["ALEJA"])
    cols["PD10"] = (X.tf == 15) & (X.tend == 0) & (X.disp == D["ALEJA"])
    cols["PD11"] = (X.tf == 10) & (X.disp == D["ALEJA"])
    keep = np.zeros(len(X), bool)
    for v in cols.values(): keep |= v.to_numpy()
    X = X[keep].reset_index(drop=True)
    for n, v in cols.items(): X[n] = v[keep].to_numpy()
    k, lado, P, ext2, A = (X[c].to_numpy() for c in ("k", "lado", "P", "ext2", "A"))
    c = np.asarray(ctx["c"], float); tick = float(ctx["tick"])
    a = PD._niveles_arr(k.astype(np.int64), lado.astype(np.int64), P.astype(float), ext2.astype(float), A.astype(float), c, tick, ("S_ESTR", "T_05"))
    b = PD._niveles_arr(k.astype(np.int64), lado.astype(np.int64), P.astype(float), ext2.astype(float), A.astype(float), c, tick, ("S_ESTR", "T_1"))
    X["stop"], X["obj05"], X["obj1"] = a[:, 4], a[:, 5], b[:, 5]
    X["ref"], X["ext"], X["rg"] = X.P, X.ext2, X.A
    ok = np.isfinite(a[:, 0]) & np.isfinite(b[:, 0])
    return X[ok].reset_index(drop=True)

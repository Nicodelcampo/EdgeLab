#!/usr/bin/env python3
"""Paso 1 de docs/research/urgencia_vs_evidencia_20261117/PROPUESTA.md: vida de una ventaja (edgelab/research/vida_ventaja.py) sobre la
población NO elegida del catálogo SQX (las 68 reglas × instrumento, variante original, 2004/2012 → 2026-09-29; nada del holdout).
Pre-registro: docs/research/urgencia_vs_evidencia_20261117/PREREGISTRO_PASO1.md.

  python tools/vida_ventaja_medir.py potencia     # SÓLO operaciones por mes (sin R): qué τ se detecta con esta estructura
  python tools/vida_ventaja_medir.py medir        # ajuste por familia y conjunto + nulo paramétrico (τ = 0) + BH -> RESULTADO_PASO1.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
OPS = ROOT / "docs/research/sqx_catalogo_20261117/ops"; OUT = ROOT / "docs/research/urgencia_vs_evidencia_20261117"
FAMILIAS = {"tendencia": ("TURTLE_55_20", "TURTLE_20_10", "ADX_TRAIL"), "reversion": ("MR_A", "MR_B", "BUY_DIPS", "PRICE_DIP", "DOUBLE7"),
            "ruptura_corta": ("RANGE_1300", "INSIDE_BAR"), "cot": ("COT1_CROWDING", "COT2_SPREAD", "COT3_TREND"), "volumen": ("VP_POC_USDJPY",)}
B_NULO, SEMILLA, FIN = 500, 20261117, pd.Period("2026-09", "M")


def series(con_R: bool):
    """{familia: [(nombre, suma, n)]}. Sin R (potencia): suma = 0. Cada serie va de su primer mes con operaciones a 2026-09."""
    from edgelab.research.vida_ventaja import mensual
    out = {f: [] for f in FAMILIAS}
    for f in sorted(OPS.glob("*_original.csv.gz")):
        nom = f.name.replace("_original.csv.gz", ""); est = nom.rsplit("_", 1)[0]
        fam = next((k for k, v in FAMILIAS.items() if est in v), None)
        if fam is None: continue
        g = pd.read_csv(f, usecols=["dia", "R"] if con_R else ["dia"]); p = pd.to_datetime(g.dia).dt.to_period("M")
        if not len(g): continue
        ini = p.min(); m = np.asarray((p - ini).apply(lambda x: x.n)); T = (FIN - ini).n + 1
        if con_R: s, n = mensual(g.R.to_numpy(float), m, T)
        else: n = np.bincount(m, minlength=T).astype(float); s = np.zeros(T)
        out[fam].append((nom, s, n))
    return out


def potencia():
    from edgelab.research import vida_ventaja as V
    S = series(con_R=False); res = {}
    grupos = dict(S, conjunto=[x for v in S.values() for x in v])
    for g, lst in grupos.items():
        estr = [n for _, _, n in lst]
        crit = np.quantile([V.ajustar(V.generar_series(estr, 0.9, 0.0, seed=SEMILLA + b))["lr_tau0"] for b in range(100)], 0.95)
        fila = dict(series=len(lst), ops=int(sum(n.sum() for n in estr)), lr_critico_95=float(crit))
        for tau in (0.03, 0.05, 0.1):
            for rho in (0.8, 0.95):
                det = [V.ajustar(V.generar_series(estr, rho, tau, seed=SEMILLA + 1000 + b))["lr_tau0"] > crit for b in range(50)]
                fila[f"tau{tau}_rho{rho}"] = float(np.mean(det))
        res[g] = fila; print(g, fila, flush=True)
    (OUT / "POTENCIA_PASO1.json").write_text(json.dumps(res, indent=1)); return res


def medir():
    from edgelab.research import vida_ventaja as V
    from fundedsync_tanda2 import _bh
    S = series(con_R=True); res = dict(preregistro="docs/research/urgencia_vs_evidencia_20261117/PREREGISTRO_PASO1.md", grupos={})
    grupos = dict(S, conjunto=[x for v in S.values() for x in v])
    for g, lst in grupos.items():
        sr = [(s, n) for _, s, n in lst]; a = V.ajustar(sr)
        nulo = [V.ajustar(V.generar_series([n for _, n in sr], 0.9, 0.0, seed=SEMILLA + b))["lr_tau0"] for b in range(B_NULO)]
        a["p_tau0"] = float((1 + sum(x >= a["lr_tau0"] for x in nulo)) / (B_NULO + 1)); a["series"] = [nom for nom, _, _ in lst]
        res["grupos"][g] = a; print(g, {k: a[k] for k in ("rho", "tau", "lr_tau0", "p_tau0", "vida_media_meses", "ic_rho", "ic_tau")}, flush=True)
    ks = list(res["grupos"]); bh = _bh([res["grupos"][k]["p_tau0"] for k in ks])
    for k, b in zip(ks, bh):
        g = res["grupos"][k]; g["regimen_detectado"] = bool(b and g["tau"] > 0)
    (OUT / "RESULTADO_PASO1.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    {"potencia": potencia, "medir": medir}[sys.argv[1]]()

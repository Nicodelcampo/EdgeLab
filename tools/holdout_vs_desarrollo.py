#!/usr/bin/env python3
"""¿El holdout difiere del resto de los períodos con el código causal? Por regla (12 nominadas + U1-CRUZADO): media neta del holdout
(10-01 → 10-30, sólo sesiones válidas) contra DESC causal, réplica causal y DESC+réplica. Diferencia con IC por bootstrap de sesiones
(cada período remuestreado por separado), p bilateral y Holm sobre las 13 reglas; z de predicción: cuántos errores estándar del
holdout (con el desvío por operación de desarrollo y el n del holdout) separan su media de la de desarrollo.
Reusa _cargar/REGLAS/validas (holdout_individual) y los archivos de la re-medición causal.
  python tools/holdout_vs_desarrollo.py
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from holdout_individual import REGLAS, H, validas, fuente  # noqa: E402
from remedir_canasta_causal import _cargar  # noqa: E402

REM = ROOT / "docs/research/canasta_7_20261030/remedicion_causal_20261102"
U1 = ROOT / "docs/research/areas_expansion_20261022/u1"


def periodo(c, t):
    o = json.loads((REM / f"{c}__{t}.json").read_text()).get("operaciones") or {}
    return np.array(o.get("ses", []), int), np.array(o.get("neto", []), float)


def u1_cruzado():
    ops = pd.concat([pd.read_csv(f) for f in sorted((U1 / "regimen_causal").glob("U1_TOPES_NQ_*_operaciones.csv"))])
    ops = ops[(ops.ejecucion == "E1A/T3/S3") & (ops.tope == "mult:3") & ops.neto.notna()]
    d = ops[ops.ses <= 20260331]; r = ops[ops.ses >= 20260401]
    h = json.loads((U1 / "RESULTADO_HOLDOUT_CAUSAL_U1_CRUZADO.json").read_text())["operaciones"]
    return (d.ses.to_numpy(int), d.neto.to_numpy(float)), (r.ses.to_numpy(int), r.neto.to_numpy(float)), (np.array(h["ses"], int), np.array(h["neto"], float))


def boot_media(s, x, rng, B):
    g = pd.DataFrame(dict(s=s, x=x)).groupby("s").x.agg(["sum", "count"]); k = len(g)
    i = rng.integers(0, k, (B, k)); return g["sum"].to_numpy()[i].sum(1) / g["count"].to_numpy()[i].sum(1)


def main(B=20000, seed=20261102):
    rng = np.random.default_rng(seed); filas = []
    for c in REGLAS + ["U1-CRUZADO"]:
        if c == "U1-CRUZADO":
            de, re_, ho = u1_cruzado(); inst = {"NQ", "USATECHIDXUSD"}
        else:
            de, re_ = periodo(c, "desc"), periodo(c, "oos"); sp = _cargar(c)[0]["spec"]
            o = json.loads((H / f"{c}.json").read_text()).get("operaciones") or {}
            ho = (np.array(o.get("ses", []), int), np.array(o.get("neto", []), float))
            inst = {fuente(sp["sensor"]), fuente(sp.get("ejecucion") or sp["sensor"])}
        v = validas(inst); m = np.isin(ho[0], list(v)); ho = (ho[0][m], ho[1][m])
        dev = (np.r_[de[0], re_[0]], np.r_[de[1], re_[1]])
        f = dict(regla=c, n_desc=len(de[1]), media_desc=float(de[1].mean()), n_rep=len(re_[1]), media_rep=float(re_[1].mean()),
                 n_dev=len(dev[1]), media_dev=float(dev[1].mean()), n_hold=len(ho[1]), media_hold=float(ho[1].mean()) if len(ho[1]) else None)
        if len(ho[1]) >= 2 and len(set(ho[0])) >= 2:
            d = boot_media(*ho, rng, B) - boot_media(*dev, rng, B)
            f.update(dif=f["media_hold"] - f["media_dev"], ic90_dif=[float(np.percentile(d, 5)), float(np.percentile(d, 95))],
                     p_bilateral=float(min(1.0, 2 * min((d <= 0).mean(), (d >= 0).mean()))),
                     z_prediccion=float((f["media_hold"] - f["media_dev"]) / (dev[1].std(ddof=1) / np.sqrt(len(ho[1])))))
        filas.append(f)
    ps = sorted([(i, f["p_bilateral"]) for i, f in enumerate(filas) if "p_bilateral" in f], key=lambda t: t[1]); k = len(ps); acc = 0
    for j, (i, p) in enumerate(ps): acc = max(acc, min(1.0, p * (k - j))); filas[i]["p_holm"] = acc
    out = H / "HOLDOUT_VS_DESARROLLO.json"; out.write_text(json.dumps(filas, indent=1, default=float)); return filas


if __name__ == "__main__":
    F = pd.DataFrame(main())
    print(F[["regla", "n_dev", "media_desc", "media_rep", "media_dev", "n_hold", "media_hold", "dif", "ic90_dif", "z_prediccion", "p_holm"]].round(2).to_string())

#!/usr/bin/env python3
"""Simulación con verdad conocida: ¿cuántos edges reales confirma cada diseño de decisión y cuántos falsos deja pasar?
Sin datos de mercado. Compara el diseño vigente del autopilot (Holm al nivel del alpha-investing, hit = rechazo en réplica) con el
propuesto (tamiz FDR + confirmación LORD++) y con «sin corrección» (lo que hace un script suelto).

  python tools/embudo_simulacion_potencia.py --out docs/research/auditoria_embudo_20261022/SIMULACION_POTENCIA.json
"""
import argparse
import json
import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.funnel.escalera import LordPP, tamiz_fdr  # noqa: E402

N = NormalDist()
pval = np.vectorize(lambda z: 1 - N.cdf(z))


def holm_rechazos(p, a):
    o = np.argsort(p); m = len(p); out = set()
    for k, i in enumerate(o):
        if p[i] <= a / (m - k): out.add(int(i))
        else: break
    return out


def correr(seed, C, m, pi1, mu_d, mu_r, top=3, w0=0.05, payout=0.05, f=0.5, reset=False):
    rng = np.random.default_rng(seed); W = w0; L = LordPP(); LJ = LordPP(gamma="javanmard_montanari")
    res = {k: dict(tp=0, fp=0) for k in ("vigente", "vigente_sin_agotar", "propuesto", "propuesto_gamma_JM", "sin_correccion")}
    reales = 0
    for c in range(C):
        real = rng.random(m) < pi1; reales += int(real.sum())
        zd = rng.normal(np.where(real, mu_d, 0.0), 1); zr = rng.normal(np.where(real, mu_r, 0.0), 1)
        pd_, pr = pval(zd), pval(zr)
        sel = np.argsort(-zd)[:top]                                       # las 3 mejores del descubrimiento van a réplica
        # vigente: Holm sobre m + 3 pruebas planeadas al nivel apostado; cuenta sólo el rechazo en réplica
        for nombre, w in (("vigente", W), ("vigente_sin_agotar", w0)):
            a = f * w / (1 + w); p_all = np.r_[pd_, pr[sel]]
            rej = {i - m for i in holm_rechazos(p_all, a) if i >= m}
            hit = [sel[j] for j in rej]
            res[nombre]["tp"] += int(sum(real[h] for h in hit)); res[nombre]["fp"] += int(sum(not real[h] for h in hit))
            if nombre == "vigente": W = W + payout if hit else W - a / (1 - a); W = max(W, 0.0)
        # propuesto: BH-Storey q=0,10 en descubrimiento (máx. 3 nominadas, las de mayor z) -> réplica con nivel LORD++
        nom = [i for i in tamiz_fdr(pd_, 0.10, "storey")["nominadas"]]
        nom = sorted(nom, key=lambda i: -zd[i])[:top]
        for i in nom:
            r = L.probar(float(pr[i]))
            if r["rechazo"]: res["propuesto"]["tp" if real[i] else "fp"] += 1
            if LJ.probar(float(pr[i]))["rechazo"]: res["propuesto_gamma_JM"]["tp" if real[i] else "fp"] += 1
        # sin corrección: las 3 mejores, réplica a 0,05 cada una
        for i in sel:
            if pr[i] <= 0.05: res["sin_correccion"]["tp" if real[i] else "fp"] += 1
    return res, reales, W


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--reps", type=int, default=200); a = ap.parse_args()
    escenarios = {"sin edges reales (sólo ruido)": (0.0, 0.0), "fuerte (z desc 3,5 / rép 3,0)": (3.5, 3.0), "moderado (3,0 / 2,5)": (3.0, 2.5), "débil (2,5 / 2,0)": (2.5, 2.0)}
    C, m, pi1 = 60, 100, 0.03
    out = dict(diseno=dict(campanias=C, pruebas_por_campania=m, fraccion_real=pi1, replicadas_por_campania=3, reps=a.reps,
                           vigente="alpha-investing w0=0,05 payout=0,05 f=0,5; Holm sobre m+3 al nivel apostado; acierto = rechazo en réplica",
                           propuesto="BH-Storey q=0,10 en descubrimiento, hasta 3 nominadas; réplica con nivel LORD++ (alfa 0,05)"), escenarios={})
    for nom, (md, mr) in escenarios.items():
        agg = {}; tot_real = 0; Ws = []
        for r in range(a.reps):
            res, reales, W = correr(1000 + r, C, m, pi1 if md > 0 else 0.0, md, mr); tot_real += reales; Ws.append(W)
            for k, v in res.items():
                g = agg.setdefault(k, dict(tp=0, fp=0, fdp=[]))
                g["tp"] += v["tp"]; g["fp"] += v["fp"]; g["fdp"].append(v["fp"] / max(v["tp"] + v["fp"], 1))
        out["escenarios"][nom] = {k: dict(edges_reales_confirmados_pct=round(100 * v["tp"] / tot_real, 2) if tot_real else None, falsos_por_corrida=round(v["fp"] / a.reps, 3),
                                          fdr_media=round(float(np.mean(v["fdp"])), 4), confirmados_por_corrida=round((v["tp"] + v["fp"]) / a.reps, 2)) for k, v in agg.items()}
        out["escenarios"][nom]["riqueza_final_vigente_mediana"] = float(np.median(Ws))
        print(nom, json.dumps(out["escenarios"][nom], ensure_ascii=False), flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()

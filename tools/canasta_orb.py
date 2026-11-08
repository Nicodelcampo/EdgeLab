#!/usr/bin/env python3
"""CANASTA-ORB: selección por estabilidad en sub-bloques, correlación y diversificación, con el nulo de la selección completa.
Pre-registro: docs/research/orb_nq_20261108/PREREGISTRO_CANASTA.md (regla global de Nico, docs/DECISIONES_20261108.md).

  python tools/canasta_orb.py docs/research/orb_nq_20261108/ORB_SERIES_DESC.json
"""
import json, sys
import numpy as np

N_BLOQUES, MIN_BLOQUES_POS, T_MIN, CORR_MAX, MAX_REGLAS, MAX_POR_INST, MIN_INST, B, SEED = 5, 4, 1.0, 0.3, 6, 3, 2, 1000, 20261108


def matriz(series: dict):
    """Reglas (sin canastas) × sesiones; 0 donde la regla no operó (R del día = 0)."""
    reglas = sorted(k for k in series if not k.startswith("CANASTA"))
    dias = sorted({int(d) for k in reglas for d in series[k]})
    pos = {d: i for i, d in enumerate(dias)}; X = np.zeros((len(dias), len(reglas)))
    for j, k in enumerate(reglas):
        for d, v in series[k].items(): X[pos[int(d)], j] = v
    return reglas, np.array(dias), X


def t_diario(x):
    s = x.std(ddof=1)
    return float(x.mean() / (s / np.sqrt(len(x)))) if s > 0 else 0.0


def seleccionar(reglas, X):
    """Pasos 1–4 del pre-registro. Devuelve (índices elegidos, t de la canasta)."""
    bloques = np.array_split(np.arange(len(X)), N_BLOQUES)
    pos = np.array([[X[b, j].mean() > 0 for b in bloques] for j in range(X.shape[1])]).sum(1)
    t = np.array([t_diario(X[:, j]) for j in range(X.shape[1])])
    cand = [j for j in np.argsort(-t) if pos[j] >= MIN_BLOQUES_POS and t[j] > T_MIN]
    elegidas, por_inst = [], {}
    C = np.corrcoef(X.T) if X.shape[1] > 1 else np.ones((1, 1))
    for j in cand:
        inst = reglas[j].split("|")[0]
        if por_inst.get(inst, 0) >= MAX_POR_INST or any(C[j, k] >= CORR_MAX for k in elegidas): continue
        elegidas.append(j); por_inst[inst] = por_inst.get(inst, 0) + 1
        if len(elegidas) == MAX_REGLAS: break
    if len(por_inst) < MIN_INST: return [], 0.0
    return elegidas, t_diario(X[:, elegidas].mean(1))


def main(ruta):
    reglas, dias, X = matriz(json.load(open(ruta)))
    el, t_obs = seleccionar(reglas, X)
    rng = np.random.default_rng(SEED); nul = []
    for _ in range(B):
        s = rng.choice((-1.0, 1.0), size=(len(dias), 1)); nul.append(seleccionar(reglas, X * s)[1])
    p = float((1 + sum(x >= t_obs for x in nul)) / (B + 1)) if el else 1.0
    out = dict(reglas=[reglas[j] for j in el], t_canasta=t_obs, p_seleccion=p, sesiones=len(dias),
               media_r_canasta=float(X[:, el].mean(1).mean()) if el else None, nulo_q50_q90=np.quantile(nul, [.5, .9]).tolist(),
               corr_media=float(np.mean([np.corrcoef(X[:, a], X[:, b])[0, 1] for i, a in enumerate(el) for b in el[i + 1:]])) if len(el) > 1 else None)
    print(json.dumps(out, indent=1)); return out


if __name__ == "__main__":
    main(sys.argv[1])

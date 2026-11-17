"""Contracción empírica por selección (paso 2 de docs/research/urgencia_vs_evidencia_20261117/PROPUESTA.md; pre-registro
PREREGISTRO_PASO2.md): cuánto de la media de lo ELEGIDO en descubrimiento sobrevive en su réplica no mirada, medido sobre las pistas de las
campañas cerradas del embudo (`docs/research/*/embudo/*/estado.json`, campo `desc.pistas[].replica_pistas`).

Cada par se estandariza con el desvío por operación del descubrimiento (sd = se · √n, se del IC90): d = media_desc / sd, r = media_rep / sd,
así campañas en puntos y en R se comparan. Contracción b = pendiente por el origen de r sobre d, con cada CAMPAÑA pesando igual (sus pistas
se parecen entre sí); intervalo por bootstrap de campañas. Esperado fuera de muestra de algo elegido así = b × su media de desarrollo.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np

Z90 = 1.6448536


def pares(raiz) -> list:
    """[(campaña, familia, n_pruebas, d, r, conservado_harvey_liu)] de todas las pistas con réplica."""
    out = []
    for f in sorted(glob.glob(str(Path(raiz) / "docs/research/*/embudo/*/estado.json"))):
        d = json.loads(Path(f).read_text(encoding="utf-8")); cid = d.get("spec", {}).get("cid") or Path(f).parent.name
        for p in (d.get("desc") or {}).get("pistas") or []:
            rp = p.get("replica_pistas"); ic = p.get("ic90")
            if not rp or not ic or not p.get("n") or rp.get("media") is None or p.get("media_neta") is None: continue
            sd = (ic[1] - ic[0]) / (2 * Z90) * np.sqrt(p["n"])
            if not sd > 0: continue
            out.append((cid, d["spec"].get("familia"), float(p.get("n_pruebas") or 0), p["media_neta"] / sd, rp["media"] / sd, p.get("conservado")))
    return out


def pendiente(P, idx=None) -> float:
    """b = Σ w d r / Σ w d², w = 1 / (pistas de su campaña)."""
    camp = np.array([p[0] for p in P]); d = np.array([p[3] for p in P]); r = np.array([p[4] for p in P])
    if idx is not None: camp, d, r = camp[idx], d[idx], r[idx]
    _, inv, cnt = np.unique(camp, return_inverse=True, return_counts=True); w = 1.0 / cnt[inv]
    return float((w * d * r).sum() / (w * d * d).sum())


def estimar(P, B: int = 2000, seed: int = 20261117) -> dict:
    camp = np.array([p[0] for p in P]); u = np.unique(camp); por = {c: np.flatnonzero(camp == c) for c in u}
    rng = np.random.default_rng(seed); bs = []
    for _ in range(B):
        idx = np.concatenate([por[c] for c in rng.choice(u, len(u))]); bs.append(pendiente(P, idx))
    d = np.array([p[3] for p in P]); r = np.array([p[4] for p in P])
    return dict(b=pendiente(P), ic90=[float(np.quantile(bs, 0.05)), float(np.quantile(bs, 0.95))], pares=len(P), campanas=len(u),
                d_medio=float(d.mean()), r_medio=float(r.mean()), frac_r_positivo=float((r > 0).mean()),
                mediana_cociente=float(np.median(r / d)) if (d != 0).all() else None)

#!/usr/bin/env python3
"""Análisis CONGELADO de la confirmación de H-ZONAS (docs/research/luximb_hvn_20261111/CONFIRMACION_H_ZONAS.md). Una sola vez,
sobre la tabla de USATECH 2023-01-03 → 2025-07-31. Resuelve la reserva de LORD++ `LUXIMB_HVN::confirmacion_h_zonas_20261111`.
  python tools/luximb_hvn_confirmar.py
H1: E0 stop 0,5·D, objetivo 1,0·D (E0_sl0.5_tp1.0_N); H2: lo mismo con stop 0,35·D (E0_sl0.35_tp1.0_N).
Estadístico: diferencia de R neto medio entre eventos del visor (D3_20_a0_z2) y del control sin zonas que NO son del visor
(D3_20_a0_z0 y no z2). p: permutación de las etiquetas DENTRO de cada sesión (10.000). Sub-bloques: 5 tramos cronológicos de sesiones.
CONFIRMADA = decisión de LORD++ (Simes + BH) sobre las dos p y ≥ 4/5 sub-bloques con diferencia > 0.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.costos import friccion_rt_puntos  # noqa: E402

D = ROOT / "docs/research/luximb_hvn_20261111"
TABLA = D / "confirmacion" / "LXH_USATECHIDXUSD_20230103_20250731.csv.gz"
FAMILIA, RESERVA = "LUXIMB_HVN", "confirmacion_h_zonas_20261111"
HIP = {"H1_stop050": "E0_sl0.5_tp1.0_N", "H2_stop035": "E0_sl0.35_tp1.0_N"}
VISOR, CONTROL = "D3_20_a0_z2", "D3_20_a0_z0"
FRIC = friccion_rt_puntos("NQ")                                     # USATECH: referencia con los costos de NQ (PREREGISTRO §4)
N_PERM = 10000


def diferencia(T: pd.DataFrame, ej: str, rng) -> dict:
    v = T[VISOR].astype(bool).to_numpy(); c = T[CONTROL].astype(bool).to_numpy() & ~v
    y = T[f"r_{ej}"].to_numpy(float) - FRIC / T[f"k_{ej}"].to_numpy(float)
    m = (v | c) & np.isfinite(y); y, v, ses = y[m], v[m], T.ses.to_numpy()[m]
    obs = y[v].mean() - y[~v].mean()
    grupos = [np.flatnonzero(ses == s) for s in np.unique(ses)]
    cnt = 0
    for _ in range(N_PERM):
        vp = v.copy()
        for g in grupos:
            if len(g) > 1: vp[g] = rng.permutation(v[g])
        cnt += (y[vp].mean() - y[~vp].mean()) >= obs
    us = np.unique(ses); bl = np.array_split(us, 5); pos = 0
    for b in bl:
        k = np.isin(ses, b)
        if (k & v).any() and (k & ~v).any(): pos += int(y[k & v].mean() - y[k & ~v].mean() > 0)
    se = np.sqrt(y[v].var(ddof=1) / v.sum() + y[~v].var(ddof=1) / (~v).sum())
    return dict(ejecucion=ej, n_visor=int(v.sum()), n_control=int((~v).sum()), sesiones=int(len(us)), r_visor=float(y[v].mean()),
                r_control=float(y[~v].mean()), diferencia=float(obs), p=float((cnt + 1) / (N_PERM + 1)), bloques_pos=pos, mde80=float(2.49 * se))


def main():
    from edgelab.funnel.libro_lord import LibroLord
    out = D / "RESULTADO_CONFIRMACION_H_ZONAS.json"
    if out.exists(): raise SystemExit("ya confirmado: una sola vez")
    T = pd.read_csv(TABLA); rng = np.random.default_rng(20261111)
    res = {h: diferencia(T, ej, rng) for h, ej in HIP.items()}
    dec = LibroLord().resolver(FAMILIA, RESERVA, [(h, r["p"]) for h, r in res.items()])
    nom = {c["test"] for c in dec.get("confirmadas") or []}
    for h, r in res.items(): r["veredicto"] = "CONFIRMADA" if h in nom and r["bloques_pos"] >= 4 else ("EN_CONTRA" if r["diferencia"] <= 0 else "NO_CONFIRMADA")
    out.write_text(json.dumps(dict(hipotesis=res, decision_lord=dec), indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps(dict(res=res, lord=dec), ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()

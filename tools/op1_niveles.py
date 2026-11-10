#!/usr/bin/env python3
"""Análisis CONGELADO de OP-1 (docs/research/hft_clusters_u1_20261110/PREREGISTRO_OP1.md): R neto de la orden límite en el nivel limpio,
con el filtro que deja el banco de REBOTE_NIVEL_SESION por la regla mecánica del pre-registro.
  python tools/op1_niveles.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.research import banco_eventos as BE  # noqa: E402
from edgelab.research import niveles_sesion as NV  # noqa: E402

D = ROOT / "docs/research/hft_clusters_u1_20261110"; BANCO = ROOT / "docs/research/banco_eventos/REBOTE_NIVEL_SESION/RESULTADO.json"
ORDEN_PREVIAS = ["dist_zona_1800=2", "dist_zona_3600=2", "dist_cluster=2"]


def filtro(res: dict) -> tuple:
    """(rasgos, estratos) por la regla del pre-registro."""
    nom = set(res.get("previas_nominadas") or [])
    for p in ORDEN_PREVIAS:
        if p in nom: r, e = p.split("="); return [r], [int(e)]
    for r in res.get("resultados", []):
        if r["tipo"] == "celda" and r["nominada"] and r["signo"] < 0:
            ps = [x.split("=") for x in r["nombre"].split(" ∧ ")]; return [a for a, _ in ps], [int(b) for _, b in ps]
    return ["dist_zona_1800"], [2]


def mascara(T, rasgos, estratos):
    m = np.ones(len(T), bool)
    for r, s in zip(rasgos, estratos):
        c = {i: tuple(NV.CORTES_FIJOS[r]) for i in T.inst.unique()} if r in NV.CORTES_FIJOS else BE.cortes(T, r, {})
        m &= BE.estrato(T, r, c) == s
    return m


def analizar(T: pd.DataFrame, rasgos, estratos) -> dict:
    T = T[T.placebo == 0].reset_index(drop=True); ses = BE._sesiones(T); out = dict(filtro=dict(rasgos=rasgos, estratos=estratos), grilla={})
    for tipo in NV.TIPOS:
        for m in ("atraviesa", "toca"):
            for g in NV.GEOMETRIAS:
                col = f"op_{m}_{g}"; base = (T.tipo_nivel == tipo).to_numpy() & T[col].notna().to_numpy()
                neto = (T[col] - T.op_costo_r).to_numpy(float); limpio = base & mascara(T, rasgos, estratos)
                e = BE.estabilidad(neto[limpio], T.fecha.to_numpy()[limpio], ses[limpio])
                d, se = BE.dif_sesion(neto[base], ses[base], limpio[base].astype(int))
                out["grilla"][f"{tipo}/{m}/{g}"] = dict(n=int(limpio.sum()), r_neto_limpio=e.get("media"), bloques=e.get("bloques_pos"), p=e.get("p_media"),
                                                       r_neto_todos=float(np.nanmean(neto[base])) if base.any() else None, limpio_menos_resto=d, se=se,
                                                       llenado=float(T.loc[T.tipo_nivel == tipo, f"op_{m}_llena"].mean()))
    pr = out["grilla"]["reloj/atraviesa/g1"]
    out["primaria"] = pr; out["pasa_al_holdout"] = bool(pr["r_neto_limpio"] is not None and pr["r_neto_limpio"] > 0 and (pr["bloques"] or 0) >= 4 and (pr["p"] or 1) < 0.10)
    return out


def main():
    res = json.loads(BANCO.read_text(encoding="utf-8")); r, e = filtro(res)
    out = analizar(pd.read_csv(D / "HFTC_niveles_op_replica.csv"), r, e)
    (D / "RESULTADO_OP1_DESARROLLO.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps(dict(filtro=out["filtro"], primaria=out["primaria"], pasa=out["pasa_al_holdout"]), ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()

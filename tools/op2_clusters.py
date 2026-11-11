#!/usr/bin/env python3
"""Análisis CONGELADO de OP-2 (docs/research/hft_clusters_u1_20261110/PREREGISTRO_OP2.md): R neto de la continuación a mercado en el
primer regreso a un cluster HFT grande, por activo, período (DESC / réplica) y geometría, con estabilidad y real − control.
  python tools/op2_clusters.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.research import banco_eventos as BE  # noqa: E402

D = ROOT / "docs/research/hft_clusters_u1_20261110"
FIN_DESC = 20260331


def bloque(T: pd.DataFrame, g: str) -> dict:
    R = T[T.placebo == 0].reset_index(drop=True)
    if len(R) < 10: return dict(n=int(len(R)))
    neto = (R[f"op_{g}"] - R.op_costo_r).to_numpy(float); e = BE.estabilidad(neto, R.fecha.to_numpy(), BE._sesiones(R))
    S = T.assign(neto=T[f"op_{g}"] - T.op_costo_r); rc = BE.real_menos_control(S, "neto") if (T.placebo == 1).any() else {}
    return dict(n=int(len(R)), r_neto=e.get("media"), bloques=e.get("bloques_pos"), p=e.get("p_media"), r_bruto=float(R[f"op_{g}"].mean()),
                real_menos_control=rc.get("media"), rc_bloques=rc.get("bloques_pos"))


def analizar(T: pd.DataFrame) -> dict:
    T = T.assign(periodo=np.where(T.fecha <= FIN_DESC, "DESC", "REP")); out = dict(grilla={})
    for g in ("g05", "g1", "g2"):
        for per in ("DESC", "REP", "ambos"):
            Tp = T if per == "ambos" else T[T.periodo == per]
            out["grilla"][f"todos/{per}/{g}"] = bloque(Tp, g)
            for i in sorted(T.inst.unique()): out["grilla"][f"{i}/{per}/{g}"] = bloque(Tp[Tp.inst == i], g)
    pasa = lambda k: all((out["grilla"][f"{k}/{p}/g1"].get("r_neto") or -1) > 0 and (out["grilla"][f"{k}/{p}/g1"].get("bloques") or 0) >= 4
                         and (out["grilla"][f"{k}/{p}/g1"].get("p") or 1) < 0.10 for p in ("DESC", "REP"))
    out["primaria"] = {p: out["grilla"][f"todos/{p}/g1"] for p in ("DESC", "REP", "ambos")}
    out["secundaria_YM"] = {p: out["grilla"][f"YM/{p}/g1"] for p in ("DESC", "REP", "ambos")} if "YM" in set(T.inst) else {}
    out["pasa_al_holdout"] = dict(primaria=bool(pasa("todos")), YM=bool("YM" in set(T.inst) and pasa("YM")))
    return out


def main():
    out = analizar(pd.read_csv(D / "HFTC_op2.csv"))
    (D / "RESULTADO_OP2_DESARROLLO.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps(dict(primaria=out["primaria"], YM=out["secundaria_YM"], pasa=out["pasa_al_holdout"]), ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()

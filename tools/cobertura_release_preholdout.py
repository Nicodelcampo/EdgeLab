#!/usr/bin/env python3
"""Cobertura por activo del release líquido de Kaggle hasta la apertura del holdout, desde su índice de sesiones (sin ticks).

  python tools/cobertura_release_preholdout.py <session_index.parquet> <out.json>
El índice se baja de `nicolasbuttaro/edgelab-liquid-ticks-20261014` (`metadata/session_index.parquet`, ~190 KB).
Calendario de referencia: días en que al menos la mitad de los activos tienen fila en el índice (sesiones CME reales).
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.holdout import HOLDOUT_PRIMERA_SESION_INT  # noqa: E402


def main():
    si = pd.read_parquet(sys.argv[1]); out = Path(sys.argv[2])
    assert int((si.trade_date >= HOLDOUT_PRIMERA_SESION_INT).sum()) == 0, "el índice trae filas del holdout"
    n_act = si.instrument.nunique(); dias = si.groupby("trade_date").instrument.nunique()
    ref = sorted(int(d) for d, n in dias.items() if n >= n_act / 2)
    q3 = [d for d in ref if 20260701 <= d < HOLDOUT_PRIMERA_SESION_INT]; ult = [d for d in ref if d >= 20260928]
    res = dict(fuente="nicolasbuttaro/edgelab-liquid-ticks-20261014 metadata/session_index.parquet", sesiones_referencia_jul_sep=len(q3),
               ultimas_sesiones_pre_holdout=ult, por_activo={})
    for a, g in si.groupby("instrument"):
        sel = set(int(x) for x in g[g.status == "SELECTED"].trade_date)
        faltan = [d for d in q3 if d not in sel]
        motivos = g[g.trade_date.isin(faltan)].status.value_counts().to_dict()
        sin_fila = [d for d in faltan if d not in set(int(x) for x in g.trade_date)]
        res["por_activo"][a] = dict(seleccionadas=len(sel), primera=min(sel), ultima=max(sel), jul_sep=len(q3) - len(faltan),
                                    faltan_jul_sep=faltan, motivos={k: int(v) for k, v in motivos.items()}, sin_fila_en_indice=sin_fila,
                                    faltan_ultimos_dias=[d for d in ult if d not in sel])
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    for a, r in res["por_activo"].items():
        print(f"{a:4} hasta {r['ultima']} | jul-sep {r['jul_sep']}/{len(q3)} | faltan ultimos dias {r['faltan_ultimos_dias']}")


if __name__ == "__main__":
    main()

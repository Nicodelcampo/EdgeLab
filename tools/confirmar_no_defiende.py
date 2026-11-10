#!/usr/bin/env python3
"""Análisis CONGELADO de la confirmación «el cluster HFT grande no defiende» (docs/research/hft_clusters_u1_20261110/CONFIRMACION_NO_DEFIENDE.md).
Lee HFTC_ruptura_replica.csv, calcula H1 (real − control, NQ+RTY+YM) y H2 (retroceso, NQ/ES con cortes de DESC), resuelve el lote en
el libro de LORD++ (reserva rep_no_defiende_20261110) y escribe RESULTADO_CONFIRMACION_NO_DEFIENDE.json. Una sola vez.
  python tools/confirmar_no_defiende.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.research import banco_eventos as BE  # noqa: E402

D = ROOT / "docs/research/hft_clusters_u1_20261110"
H1_INST, H2_INST = ("NQ", "RTY", "YM"), ("NQ", "ES")
CORTE_BAJO_DESC = {"NQ": -5.7607, "ES": -3.2444}                     # tercil bajo de tendencia_alineada en DESC (congelado)
FAMILIA, RESERVA = "HFT_RUPTURA", "rep_no_defiende_20261110"


def analizar(T: pd.DataFrame) -> dict:
    h1 = BE.real_menos_control(T[T.inst.isin(H1_INST)], "rompe")
    es = BE.real_menos_control(T[T.inst == "ES"], "rompe")
    por = {i: BE.real_menos_control(T[T.inst == i], "rompe") for i in H1_INST}
    R = T[(T.placebo == 0) & T.inst.isin(H2_INST)].reset_index(drop=True)
    m = np.array([v <= CORTE_BAJO_DESC[i] for i, v in zip(R.inst, R.tendencia_alineada)]) & R.tendencia_alineada.notna().to_numpy()
    h2 = BE.estabilidad(R.rompe.to_numpy(float)[m], R.fecha.to_numpy()[m], BE._sesiones(R)[m]); h2["n"] = int(m.sum())
    return dict(H1=h1, H1_por_activo={i: {k: v for k, v in r.items() if k in ("media", "bloques_pos", "p_media", "sesiones")} for i, r in por.items()},
                ES_diagnostico=es, H2=h2)


def main():
    from edgelab.funnel.libro_lord import LibroLord
    T = pd.read_csv(D / "HFTC_ruptura_replica.csv"); out = analizar(T)
    dec = LibroLord().resolver(FAMILIA, RESERVA, [("H1_no_defiende", out["H1"]["p_media"]), ("H2_retroceso", out["H2"]["p_media"])])
    out["decision_lord"] = dec
    nom = {c["test"] for c in dec.get("confirmadas", [])}
    out["confirmadas"] = [h for h, k in (("H1_no_defiende", "H1"), ("H2_retroceso", "H2")) if h in nom and (out[k].get("bloques_pos") or 0) >= 3]
    (D / "RESULTADO_CONFIRMACION_NO_DEFIENDE.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps(dict(confirmadas=out["confirmadas"], H1=out["H1"].get("media"), H2=out["H2"].get("media"), lord=dec), ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()

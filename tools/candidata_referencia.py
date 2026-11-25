"""Referencia Python de una variante FundedSync tal como la corre `EdgeLabCandidataFS` en NT8 (para la paridad).

La variante se toma de la lista pre-registrada `fundedsync_prop_opt.specs_etapa1_iter4()` (campaña
FUNDEDSYNC_PROP_OPT_20261122, contada): parámetros del módulo de fábrica + ajuste causal en M1 (stop, BE, TP, trail)
con `fundedsync_prop_opt.aplicar_overlay_m1_causal`. Sobre esas operaciones aplica el veto de noticias
(`edgelab.veto_noticias`, ±2 min / FOMC ±5) y escribe las dos listas (sin y con veto).

  python tools/candidata_referencia.py --variante T_stop100_BE15R_calFalse --inst NQ \
      --desde 2008-01-02 --hasta 2025-09-30 --out <carpeta>

Sólo DESC/REP (corta antes del holdout). No elige nada: reproduce una variante ya definida.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import fundedsync_iter2_cartera as IT2  # noqa: E402
import fundedsync_post_il_cadena as BASE  # noqa: E402
import fundedsync_prop_opt as PO  # noqa: E402
from edgelab import veto_noticias as VN  # noqa: E402
from edgelab.research.fundedsyncstack import correr_modulo  # noqa: E402
from edgelab.research.fundedsyncstack.base_series import build_multi_series, load_m1_data  # noqa: E402

M1_DIR = ROOT / "data" / "m1nt8"


def spec(variante: str) -> dict:
    for sp in PO.specs_etapa1_iter4():
        if sp["variante"] == variante:
            return sp
    raise SystemExit(f"variante no está en specs_etapa1_iter4: {variante}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variante", required=True)
    ap.add_argument("--inst", default="NQ")
    ap.add_argument("--desde", default="2019-01-02")   # mismo inicio que el Strategy Analyzer (2019 = calentamiento)
    ap.add_argument("--hasta", default="2026-09-30")   # último día antes del holdout (HOLDOUT-A4)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    sp = spec(a.variante)
    if sp.get("externa") or sp["overlay"].get("banda_miembros"):
        raise SystemExit("variante externa o de banda: no soportada acá")
    t0 = time.time()
    pq = M1_DIR / f"{a.inst}_M1_nonadj_utc.parquet"
    raw = pd.read_parquet(pq, filters=[("datetime", ">=", pd.Timestamp(a.desde)),   # misma fecha de inicio que la corrida de NT8
                                       ("datetime", "<", pd.Timestamp(a.hasta) + pd.Timedelta(days=1))]).reset_index()
    df_m1 = load_m1_data(raw, start=None, end=a.hasta, tz_input="UTC", allow_sellado=False)
    ms = build_multi_series(df_m1, tz_input="UTC", allow_sellado=False)
    ops = correr_modulo(sp["modulo"], ms, perfil="il_fabrica", **sp["params"])
    print(f"[{time.time() - t0:.0f}s] módulo {sp['modulo']} de fábrica: {len(ops)} operaciones")
    atr, _, pv, _ = BASE._cargar_series_sesion(a.inst, m1_dir=M1_DIR)
    orb = IT2._cargar_orb_raw(a.inst, m1_dir=M1_DIR)
    m1 = PO.cargar_m1_arrays_nq(m1_dir=M1_DIR, desde=a.desde)
    ov = sp["overlay"]
    o = PO.aplicar_overlay_m1_causal(ops, sp["modulo"], atr, orb, pv, m1,
                                     sl_atr_k=ov.get("sl_atr_k"), tp_atr_k=ov.get("tp_atr_k"), be_trigger_r=ov.get("be_trigger_r"),
                                     trail_tiers=ov.get("trail_tiers"), tp_r=ov.get("tp_r"),
                                     stop_orb_mult=ov.get("stop_orb_mult", 1.25), stop_min_pts=ov.get("stop_min_pts", 2.0),
                                     stop_max_pts=ov.get("stop_max_pts", 100.0))
    print(f"[{time.time() - t0:.0f}s] overlay {a.variante}: {len(o)} operaciones; columnas {list(o.columns)[:20]}")
    a.out.mkdir(parents=True, exist_ok=True)
    o.to_csv(a.out / f"PY_{a.variante}_{a.inst}.csv", index=False)
    (a.out / f"PY_{a.variante}_{a.inst}.json").write_text(json.dumps(dict(variante=a.variante, inst=a.inst, desde=a.desde, hasta=a.hasta,
                                                                          spec={k: str(v) for k, v in sp.items()}, n=len(o)), indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

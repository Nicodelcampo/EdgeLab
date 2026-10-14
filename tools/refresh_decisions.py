#!/usr/bin/env python3
"""Recalcula las decisiones por sesión de una release YA escrita (p. ej. tras corregir el calendario derivado) SIN reescribir
ticks. Sólo reemplaza las decisiones si el conjunto de sesiones SELECCIONADAS (fecha + contrato) es idéntico al ya escrito;
si difiere, avisa y no toca nada (hay que reconstruir el activo).
Uso: python tools/refresh_decisions.py --release D:/.../release --census D:/.../census
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.data.liquid_release import plan as P  # noqa: E402
from edgelab.data.liquid_release.selection import LiquidityPolicy  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--census", required=True)
    a = ap.parse_args()
    parts = Path(a.release) / "metadata" / "parts"
    cen = Path(a.census)
    chosen = pd.read_parquet(cen / "chosen_sources.parquet")
    chosen = chosen[chosen["trade_date"] < 20261001]
    cal = P.derive_all_calendars(chosen)
    cal.to_parquet(cen / "calendar_derived.parquet", index=False)
    bad = []
    for f in sorted(parts.glob("*_asset.json")):
        inst = f.name.split("_")[0]
        pj = json.loads(f.read_text(encoding="utf-8"))["policy"]
        pol = LiquidityPolicy(pj["version"], pj["min_prev_volume"], pj["min_prev_ticks"], pj["max_prev_spread_p50_ticks"],
                              pj.get("approved_by"), pj.get("notes", ""), pj.get("noncompetitive_frac", 0.01))
        _, _, dec = P.plan_asset(chosen, cal, inst, pol)
        dec.insert(0, "instrument", inst)
        old = pd.read_parquet(parts / f"{inst}_decisions.parquet")
        so = set(map(tuple, old.loc[old["status"] == "SELECTED", ["trade_date", "contract"]].values))
        sn = set(map(tuple, dec.loc[dec["status"] == "SELECTED", ["trade_date", "contract"]].values))
        if so != sn:
            bad.append((inst, len(so - sn), len(sn - so)))
            continue
        dec.to_parquet(parts / f"{inst}_decisions.parquet", index=False)
        print(inst, "decisiones refrescadas:", dec["status"].value_counts().to_dict())
    if bad:
        print("DIFIEREN las sesiones seleccionadas (hay que reconstruir el activo):", bad)
        sys.exit(1)


if __name__ == "__main__":
    main()

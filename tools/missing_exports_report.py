#!/usr/bin/env python3
"""Lista de exports NT8 que faltan para completar o mejorar la release (por activo, contrato y rango de fechas).

Usa sólo metadatos de la release (selection_decisions, session_index, calendario derivado). No lee ticks.
Prioridad: P0 = bloquea o excluye sesiones de la release; P1 = sube la garantía de procedencia (hoy sólo hay parquet derivado).
Uso: python tools/missing_exports_report.py --release D:/.../release --out D:/.../release/metadata
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


def ranges(dates):
    """Fechas yyyymmdd ordenadas -> tramos de días laborables consecutivos (se unen si el hueco es <= 4 días corridos)."""
    ds = sorted(pd.to_datetime([str(int(d)) for d in dates]))
    out, start, prev = [], None, None
    for d in ds:
        if start is None:
            start = prev = d
        elif (d - prev).days <= 4:
            prev = d
        else:
            out.append((start, prev))
            start = prev = d
    if start is not None:
        out.append((start, prev))
    return [(int(s.strftime("%Y%m%d")), int(e.strftime("%Y%m%d"))) for s, e in out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    meta = Path(a.release) / "metadata"
    idx = pd.read_parquet(meta / "session_index.parquet")
    cal = pd.read_parquet(meta / "calendar_derived.parquet")
    rows = []
    # 1) contrato elegido sin datos en la sesión
    x = idx[idx["status"] == "EXCLUDED_SELECTED_CONTRACT_HAS_NO_DATA"]
    for (inst, contract), g in x.groupby(["instrument", "contract"]):
        for s, e in ranges(g["trade_date"]):
            rows.append(dict(priority="P0", instrument=inst, contract=contract, first_trade_date=s, last_trade_date=e,
                             sessions=int(((g["trade_date"] >= s) & (g["trade_date"] <= e)).sum()),
                             reason="El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato)"))
    # 2) competidores sin dato en D-1 (decisión indeterminada)
    u = idx[idx["status"] == "UNDETERMINED"]
    acc = {}
    for r in u.itertuples():
        m = re.search(r"de: (.*)$", r.reason or "")
        for c in (m.group(1).split(",") if m else []):
            acc.setdefault((r.instrument, c.strip()), []).append(r.prev_trade_date)
    for (inst, contract), dates in acc.items():
        for s, e in ranges(dates):
            rows.append(dict(priority="P0", instrument=inst, contract=contract, first_trade_date=s, last_trade_date=e,
                             sessions=int(sum(1 for d in dates if s <= d <= e)),
                             reason="Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada"))
    # 3) días en que los demás activos operaron y éste no tiene ningún contrato
    m = cal[cal["status"] == "MISSING_EXPORT"]
    for inst, g in m.groupby("instrument"):
        for s, e in ranges(g["trade_date"]):
            rows.append(dict(priority="P0", instrument=inst, contract="(todos)", first_trade_date=s, last_trade_date=e,
                             sessions=int(((g["trade_date"] >= s) & (g["trade_date"] <= e)).sum()),
                             reason="Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero"))
    # 4) sesiones incluidas pero sólo con parquet derivado (original de texto ausente)
    p = idx[(idx["status"] == "SELECTED") & (idx["assurance"] == "PARQUET_DERIVED_ORIGINAL_NOT_AVAILABLE")]
    for (inst, contract), g in p.groupby(["instrument", "contract"]):
        for s, e in ranges(g["trade_date"]):
            rows.append(dict(priority="P1", instrument=inst, contract=contract, first_trade_date=s, last_trade_date=e,
                             sessions=int(((g["trade_date"] >= s) & (g["trade_date"] <= e)).sum()),
                             reason="Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia"))
    # el período de la release arranca en 2025-07 (primer export disponible): lo anterior no es "faltante", es fuera de alcance
    rows = [r for r in rows if r["last_trade_date"] >= 20250701]
    df = pd.DataFrame(rows, columns=["priority", "instrument", "contract", "first_trade_date", "last_trade_date", "sessions", "reason"])
    df = df.sort_values(["priority", "instrument", "contract", "first_trade_date"]).reset_index(drop=True)
    out = Path(a.out)
    df.to_csv(out / "missing_exports.csv", index=False)
    L = ["# Exports que faltan (generado por `tools/missing_exports_report.py`)", "", "Estado: VIGENTE (generado; se regenera, no se edita)", "Fecha: 2026-10-14", "",
         "P0 = excluye o bloquea sesiones de la release. P1 = mejora la garantía de procedencia (hoy sólo hay parquet derivado).",
         "Cada fila es un rango de fechas de trading CME por contrato. Se exportan con el AddOn `EdgeLabTickHistory` (un archivo por día NT-local, UTC).", ""]
    for pr in ("P0", "P1"):
        d = df[df["priority"] == pr]
        L += [f"## {pr} — {len(d)} tramos, {int(d['sessions'].sum())} sesiones", ""]
        if len(d):
            L += ["| activo | contrato | desde | hasta | sesiones | motivo |", "|---|---|---|---|---:|---|"]
            L += [f"| {r.instrument} | {r.contract} | {r.first_trade_date} | {r.last_trade_date} | {r.sessions} | {r.reason} |" for r in d.itertuples()]
        L.append("")
    (out / "MISSING_EXPORTS.md").write_text("\n".join(L), encoding="utf-8")
    print(df.groupby(["priority", "instrument"]).agg(tramos=("contract", "size"), sesiones=("sessions", "sum")).to_string())


if __name__ == "__main__":
    main()

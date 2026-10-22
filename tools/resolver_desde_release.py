#!/usr/bin/env python3
"""Genera `docs/data_catalog/RESOLVER.json` desde el release líquido canónico (decisión de Nico, 2026-10-22).

Antes el resolver apuntaba a 10 datasets que en Kaggle están marcados REEMPLAZADO/CUARENTENA desde el 2026-10-14. Ahora cada
sesión sale del índice del release `liquid_tick_v1` (aprobado para research el 2026-10-14, `docs/infra/RELEASE_APPROVAL_20261014.md`):
una fila por (activo, sesión) con el contrato líquido elegido causalmente; dataset `edgelab-liquid-ticks-20261014`, archivo
`data/<ACTIVO>_ticks.parquet` (un Parquet por activo; `edgelab_data.load_ticks` filtra por fecha de sesión). Sesiones con estado
distinto de SELECTED quedan como no aprobadas con su motivo. El formato es el que `edgelab_data.py` (protegido) ya lee: no cambia.
Las secciones de spot (Dukascopy) se conservan del resolver anterior.

  python tools/resolver_desde_release.py <session_index.parquet> <instrument_specs.json> <release_manifest.json> [RESOLVER.json]
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.holdout import HOLDOUT_PRIMERA_SESION, HOLDOUT_PRIMERA_SESION_INT  # noqa: E402

DATASET = "edgelab-liquid-ticks-20261014"


def main():
    si_p, spec_p, man_p = (Path(x) for x in sys.argv[1:4]); out = Path(sys.argv[4]) if len(sys.argv) > 4 else ROOT / "docs/data_catalog/RESOLVER.json"
    si = pd.read_parquet(si_p); specs = json.loads(spec_p.read_text(encoding="utf-8"))
    man_raw = man_p.read_bytes(); man = json.loads(man_raw); man_sha = hashlib.sha256(man_raw).hexdigest()
    if int((si.trade_date >= HOLDOUT_PRIMERA_SESION_INT).sum()):
        raise SystemExit("el índice del release trae filas del holdout: no se genera")
    viejo = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    inst = {}
    for a, g in si.sort_values(["instrument", "trade_date"]).groupby("instrument"):
        ses = []
        for r in g.itertuples(index=False):
            d = str(r.trade_date); ok = r.status == "SELECTED"
            ses.append(dict(date=f"{d[:4]}-{d[4:6]}-{d[6:]}", contract=(str(r.contract).replace(" ", "_") if isinstance(r.contract, str) else None),
                            dataset=DATASET, file=f"data/{a}_ticks.parquet", approved=bool(ok), reason=None if ok else str(r.status),
                            caveat=(str(r.assurance) if getattr(r, "assurance", None) not in (None, "") else None),
                            rows=int(r.rows_written) if pd.notna(r.rows_written) else None))
        inst[a] = dict(verdict="APROBADO_RELEASE", tick_size=specs[a]["tick_size"], tick_value_usd=specs[a]["tick_value_usd"],
                       approved_sessions=sum(s["approved"] for s in ses), sessions=ses)
    res = dict(schema="EDGELAB_RESOLVER_V2_RELEASE", generated_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
               holdout_first_trade_date=HOLDOUT_PRIMERA_SESION,
               release=dict(dataset=f"nicolasbuttaro/{DATASET}", release_id=man.get("release_id"), manifest_sha256=man_sha,
                            approval="docs/infra/RELEASE_APPROVAL_20261014.md"),
               rules=("Una fila por sesión del índice del release liquid_tick_v1: contrato líquido elegido con datos hasta D-1 (política v4, "
                      "aprobada 2026-10-14). approved = status SELECTED; las demás quedan con su motivo. Holdout (HOLDOUT-A4) excluido. "
                      "Reemplaza al resolver v1, que apuntaba a datasets REEMPLAZADO/CUARENTENA."),
               how_to_use=viejo.get("how_to_use", "import edgelab_data as ed; ed.load_ticks('MNQ','2026-01-01','2026-09-30')"),
               spot_complement=viejo.get("spot_complement"), spot_datasets=viejo.get("spot_datasets"), spot_exclusions=viejo.get("spot_exclusions"),
               instruments=inst)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({a: v["approved_sessions"] for a, v in inst.items()}), "manifest", man_sha[:12])


if __name__ == "__main__":
    main()

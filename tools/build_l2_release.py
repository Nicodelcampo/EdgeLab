#!/usr/bin/env python3
"""Arma (y opcionalmente publica) un dataset PRIVADO de Kaggle con el L2 de UN instrumento.

Contenido: por contrato `l2_depth/*.parquet`, `l1_quotes/*.parquet` y `manifests/*.manifest.json` (los de la conversion), mas las
agregaciones `aggregates/<contrato>/*.npz` de `tools/l2_fast_book.py` y un `L2_RELEASE_MANIFEST.json` con bytes y SHA-256 de CADA
archivo, estado de QA por sesion y las politicas de uso. Nunca publica en abierto (isPrivate=true).

Uso:
  python tools/build_l2_release.py --instrument ES --out D:/edgelab_release_work/l2_es_release            # arma y verifica local
  python tools/build_l2_release.py --instrument ES --out ... --create                                    # ademas publica (kaggle datasets create)
El manifiesto declara `research_allowed=false`: usarlo para investigar exige auditoria propia del L2 (como la release v4 de ticks).
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

NORTH_STAR_BODY_SHA256 = "05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421"
SCHEMA = "edgelab_l2_release_v1"
DEV_END = "20261031"      # ventana de desarrollo L2 firmada 2026-09-24; nov-dic = holdout L2 sellado (no existe aun)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", required=True)
    ap.add_argument("--root", default="E:/l2_parquet")
    ap.add_argument("--agg", default="E:/l2_agg")
    ap.add_argument("--out", required=True)
    ap.add_argument("--slug", default=None, help="owner/name; por defecto nicolasbuttaro/edgelab-l2-<inst>-<fecha>")
    ap.add_argument("--limit", type=int, default=0, help="solo para pruebas: primeras N sesiones por contrato")
    ap.add_argument("--create", action="store_true")
    a = ap.parse_args()
    inst = a.instrument.upper()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    slug = a.slug or f"nicolasbuttaro/edgelab-l2-{inst.lower()}-{today}"

    files, sessions = {}, []
    for cdir in sorted(glob.glob(f"{a.root}/{inst}_*")):
        if not os.path.isdir(cdir):
            continue
        contract = os.path.basename(cdir)
        dates = sorted(re.search(r"(20\d{6})", os.path.basename(f)).group(1) for f in glob.glob(f"{cdir}/l2_depth/*.parquet"))
        if a.limit:
            dates = dates[: a.limit]
        for d in dates:
            row = {"contract": contract, "session": d, "files": {}}
            for kind, rel in (("l2_depth", f"l2_depth/{d}.parquet"), ("l1_quotes", f"l1_quotes/{d}.parquet"), ("conversion_manifest", f"manifests/{d}.manifest.json")):
                src = Path(cdir) / rel
                if not src.exists():
                    row["files"][kind] = None
                    continue
                dst = out / "data" / contract / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.exists() or dst.stat().st_size != src.stat().st_size:
                    shutil.copy2(src, dst)
                key = dst.relative_to(out).as_posix()
                files[key] = {"bytes": dst.stat().st_size, "sha256": sha256_file(dst)}
                row["files"][kind] = key
            agg = Path(a.agg) / contract / f"{d}.npz"
            qa = None
            if agg.exists():
                dst = out / "aggregates" / contract / f"{d}.npz"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(agg, dst)
                key = dst.relative_to(out).as_posix()
                files[key] = {"bytes": dst.stat().st_size, "sha256": sha256_file(dst)}
                row["files"]["aggregate"] = key
                import numpy as np
                m = json.loads(str(np.load(agg)["meta"]))
                qa = {"fast_book_status": m["status"], "l2_events": m["l2_events"], "snapshots": m["snapshots"], "abstain_row": m["abstain_row"],
                      "crossed_ratio": round(m["crossed_ratio"], 6)}
            row["qa"] = qa
            sessions.append(row)

    flagged = [s for s in sessions if not s["qa"] or s["qa"]["fast_book_status"] != "PASS"]
    manifest = {
        "schema": SCHEMA, "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "instrument": inst, "slug": slug,
        "north_star_body_sha256": NORTH_STAR_BODY_SHA256,
        "research_allowed": False,
        "research_allowed_reason": "L2 sin auditoria de payload ni aprobacion externa propias (equivalente a la release v4 de ticks). Uso solo para preparacion tecnica hasta entonces.",
        "privacy": {"is_private": True, "raw_l2_outside_pc": "decision de Nico 2026-10-15: se permite subir el L2 de ES a Kaggle privado"},
        "partition_policy": {
            "l2_development_window": f"2026-07-01..{DEV_END[:4]}-{DEV_END[4:6]}-{DEV_END[6:]} (enmienda firmada 2026-09-24)",
            "l2_holdout": "2026-11-01..2026-12-31, sellado; NO incluido (no existe aun)",
            "ticks_holdout_note": "el holdout de ticks sigue desde 2026-10-01: un resultado de ticks en jul-oct no puede combinarse con un modelo L2 entrenado ahi",
        },
        "schema_l2": "NT8_MBP10_REPLAY_V1 (ts_us reloj ART leido como UTC; price_tick enteros; side 0=ASK 1=BID; operation 0 alta/1 cambio/2 baja)",
        "limitations": [
            "clasificacion de agresor del L2 es heuristica sin validar; no se publica ni se usa",
            "5 de 194 archivos L2 del repo tienen el reloj corrido (P-84): verificar antes de usar",
            "sesiones marcadas en `flagged_sessions` no deben usarse (libro no certificable o datos incompletos)",
            "los contratos 09-26 y 12-26 se solapan en fechas: elegir un contrato principal por sesion y declararlo",
        ],
        "sessions": sessions, "flagged_sessions": [{"contract": s["contract"], "session": s["session"], "qa": s["qa"]} for s in flagged],
        "files": files, "totals": {"files": len(files), "bytes": sum(v["bytes"] for v in files.values()), "sessions": len(sessions)},
    }
    (out / "L2_RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (out / "dataset-metadata.json").write_text(json.dumps({
        "title": f"EdgeLab L2 {inst} {today} (CANDIDATE)", "id": slug, "licenses": [{"name": "other"}], "isPrivate": True,
        "subtitle": f"L2 MBP-10 de {inst} en parquet, con manifiesto SHA-256 (sin auditoria de payload)"}, indent=1), encoding="utf-8")
    print(f"armado en {out}: {len(files)} archivos, {manifest['totals']['bytes'] / 1e9:.2f} GB, {len(sessions)} sesiones, {len(flagged)} marcadas")
    if a.create:
        r = subprocess.run(["kaggle", "datasets", "create", "-p", str(out), "--dir-mode", "zip"], capture_output=True, text=True)
        print((r.stdout + r.stderr)[-600:])
        if r.returncode != 0:
            sys.exit(1)


if __name__ == "__main__":
    main()

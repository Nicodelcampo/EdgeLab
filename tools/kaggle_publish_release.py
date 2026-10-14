#!/usr/bin/env python3
"""Publica la release como dataset PRIVADO de Kaggle y verifica lo publicado.

Pasos: (1) escribe dataset-metadata.json (privado, licencia 'other'); (2) `kaggle datasets create --dir-mode zip` (Kaggle
descomprime las carpetas y las deja como data/ y metadata/); (3) espera `ready`; (4) compara nombre y tamaño de CADA archivo
contra el local; (5) con --verify-download baja la versión publicada y corre el lector seguro (tamaño + SHA-256 del manifiesto).

Uso: python tools/kaggle_publish_release.py --release D:/.../release_20261014 [--create] [--version "mensaje"] [--verify-download D:/tmp/dl]
Sin --create sólo verifica un dataset ya publicado. Nunca publica en abierto: isPrivate=true siempre.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.data.liquid_release.release_reader import load_manifest  # noqa: E402

SLUG = "nicolasbuttaro/edgelab-liquid-ticks-20261014"


def sh(*args, check=True):
    r = subprocess.run(list(args), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"fallo {' '.join(args[:4])}: {(r.stdout + r.stderr)[-400:]}")
    return r.stdout + r.stderr


def local_files(root: Path):
    out = {}
    for p in root.rglob("*"):
        if p.is_file() and p.name != "dataset-metadata.json":
            out[p.relative_to(root).as_posix()] = p.stat().st_size
    return out


def remote_files():
    txt = sh("kaggle", "datasets", "files", SLUG, "--page-size", "200")
    out = {}
    for line in txt.splitlines()[2:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            out[parts[0]] = int(parts[1])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--create", action="store_true")
    ap.add_argument("--version")
    ap.add_argument("--verify-download")
    a = ap.parse_args()
    root = Path(a.release)
    man = json.loads((root / "release_manifest.json").read_text(encoding="utf-8"))
    desc = (f"**ESTADO: {man['status']}** — release líquida de ticks CME (un Parquet por activo, {len(man['assets'])} activos). "
            "Un contrato líder causal por sesión, sin holdout (trade date >= 2026-10-01), huso UTC verificado, bloques duplicados descartados con evidencia. "
            "**Leer README_AGENTES.md primero.** La política de liquidez es una propuesta sin aprobar; no autoriza research ni promoción. "
            "Privado, sin redistribución. Informe: docs/infra/LIQUID_RELEASE_20261014.md del repo Nicodelcampo/EdgeLab.")
    meta = {"title": "EdgeLab Liquid Ticks 20261014 (CANDIDATE)", "id": SLUG,
            "subtitle": "Un Parquet por activo, contrato líquido causal, sin holdout", "description": desc,
            "licenses": [{"name": "other"}], "isPrivate": True, "keywords": []}
    (root / "dataset-metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.create:
        out = sh("kaggle", "datasets", "version", "-p", str(root), "-m", a.version or "release", "--dir-mode", "zip") if a.version \
            else sh("kaggle", "datasets", "create", "-p", str(root), "--dir-mode", "zip")
        print(out[-300:])
        for _ in range(120):
            st = sh("kaggle", "datasets", "status", SLUG, check=False).strip().lower()
            print("estado:", st)
            if "ready" in st:
                break
            time.sleep(20)
    loc, rem = local_files(root), remote_files()
    miss = [k for k in loc if k not in rem]
    diff = [(k, loc[k], rem[k]) for k in loc if k in rem and loc[k] != rem[k]]
    extra = [k for k in rem if k not in loc]
    print(f"local {len(loc)} archivos, remoto {len(rem)}; faltan={miss[:5]} tamaño_distinto={diff[:5]} extra={extra[:5]}")
    ok = not miss and not diff
    if a.verify_download:
        dl = Path(a.verify_download)
        dl.mkdir(parents=True, exist_ok=True)
        sh("kaggle", "datasets", "download", SLUG, "-p", str(dl), "--unzip")
        files = load_manifest(dl, verify_hash=True)       # tamaño + SHA-256 de cada Parquet publicado
        print("lector seguro sobre lo publicado: OK,", len(files), "activos verificados por SHA-256")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

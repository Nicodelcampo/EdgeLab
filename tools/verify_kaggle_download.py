#!/usr/bin/env python3
"""Verifica una release PUBLICADA en Kaggle: descarga cada archivo desde Kaggle (no desde la copia local) y compara tamaño y SHA-256 con el
manifiesto publicado. Es la comprobación de que lo que se sube es lo que se baja.

Uso: python tools/verify_kaggle_download.py --slug nicolasbuttaro/edgelab-liquid-ticks-20261014 --work D:/tmp/dl [--keep]
Escribe <work>/kaggle_download_verification.json. No descarta ni modifica nada remoto. Borra cada Parquet descargado al verificarlo salvo --keep.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def sha256_file(p: Path, chunk=16 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                return h.hexdigest()
            h.update(b)


def kaggle_get(slug: str, name: str, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONUTF8="1")
    exe = shutil.which("kaggle") or "kaggle"            # el CLI de Kaggle no está en el venv del repo
    r = subprocess.run([exe, "datasets", "download", slug, "-f", name, "-p", str(out), "-q"], capture_output=True, text=True, env=env)
    p = out / Path(name).name
    z = out / (Path(name).name + ".zip")
    if not p.exists() and z.exists():                      # a veces Kaggle entrega el archivo en un zip
        import zipfile
        with zipfile.ZipFile(z) as zf:
            zf.extractall(out)
        z.unlink()
    if not p.exists():
        raise RuntimeError(f"no se pudo descargar {name}: {(r.stderr or r.stdout)[-300:]}")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    work = Path(a.work)
    man_path = kaggle_get(a.slug, "release_manifest.json", work)
    man = json.loads(man_path.read_text(encoding="utf-8"))
    out = dict(slug=a.slug, manifest_sha256=sha256_file(man_path), release_id=man.get("release_id"), status=man.get("status"), assets={}, metadata={})
    for asset, e in man["assets"].items():
        if a.only and asset not in a.only:
            continue
        p = kaggle_get(a.slug, e["file"], work / "data")
        ok_size, got = p.stat().st_size == int(e["bytes"]), sha256_file(p)
        out["assets"][asset] = dict(file=e["file"], bytes_ok=ok_size, sha256_ok=got == e["sha256"], sha256=got)
        print(f"{asset}: tamaño {'OK' if ok_size else 'DISTINTO'} | SHA-256 {'OK' if got == e['sha256'] else 'DISTINTO'}", flush=True)
        if not a.keep:
            p.unlink()
    for rel, e in (man.get("metadata_files") or {}).items():
        p = kaggle_get(a.slug, rel, work / "metadata")
        got = sha256_file(p)
        out["metadata"][rel] = dict(bytes_ok=p.stat().st_size == int(e["bytes"]), sha256_ok=got == e["sha256"])
        if not a.keep:
            p.unlink()
    out["all_ok"] = all(v["bytes_ok"] and v["sha256_ok"] for v in list(out["assets"].values()) + list(out["metadata"].values()))
    (work / "kaggle_download_verification.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("TODO OK" if out["all_ok"] else "HAY DIFERENCIAS", flush=True)
    sys.exit(0 if out["all_ok"] else 1)


if __name__ == "__main__":
    main()

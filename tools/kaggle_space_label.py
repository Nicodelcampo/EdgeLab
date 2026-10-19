#!/usr/bin/env python3
"""Señaliza el espacio de datasets de Kaggle según config/kaggle_space_map_*.json.

Sólo cambia METADATOS (título con etiqueta si entra en 50 caracteres, subtítulo y descripción con un banner de estado antepuesto
a la descripción original). No toca archivos, versiones ni privacidad: los contenidos son inmutables.
Antes de aplicar, los metadatos originales se respaldan (--backup) y cada cambio se verifica releyendo la API.

  python tools/kaggle_space_label.py --map config/kaggle_space_map_20261014.json --backup D:/.../meta_backup --out D:/.../meta_new          # simulación
  python tools/kaggle_space_label.py ... --apply                                                                                            # aplica
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

OWNER = "nicolasbuttaro"
SHORT = {"ENTRADA": "ENTRADA", "ACTIVO-CANDIDATO": "ACTIVO", "REEMPLAZADO": "REEMPL", "CUARENTENA": "CUARENT",
         "DERIVADO-BLOQUEADO": "BLOQ", "CONTEXTO-L2": "L2", "SPOT": "SPOT", "CODIGO": "CODIGO", "ARCHIVO": "ARCHIVO"}


def load_info(path: Path) -> dict:
    j = json.loads(path.read_text(encoding="utf-8"))
    i = j["info"]
    return ast.literal_eval(i) if isinstance(i, str) else i


def banner(tag: str, note: str, release: str, tags: dict) -> str:
    rel = release.split("/")[-1]
    if tag == "ENTRADA":
        head = f"> **ESTADO 2026-10-14: [ENTRADA]** — Para datos de ticks CME vigentes usar `{release}` (candidata, un Parquet por activo, contrato líquido causal, sin holdout)."
        tail = "> Este catálogo conserva el resolver histórico (v15/v16), que sigue **BLOQUEADO para research causal**. El mapa de todo el espacio está en `KAGGLE_SPACE_INDEX.md`."
    elif tag in ("REEMPLAZADO", "CUARENTENA", "DERIVADO-BLOQUEADO"):
        head = f"> **ESTADO 2026-10-14: [{tag}]** — Reemplazado por `{release}` (un Parquet por activo, contrato líquido causal, sin holdout)."
        tail = "> **No usar para research nuevo.** Se conserva sin cambios de contenido (versiones inmutables) porque campañas históricas lo referencian."
    elif tag == "SPOT":
        head = "> **ESTADO 2026-10-14: [SPOT]** — Cotizaciones spot/CFD de Dukascopy. **No son futuros CME**: bid/ask sin libro ni volumen negociado."
        tail = "> Usar sólo como complemento de potencia con su equivalencia medida; nunca mezclar con ticks CME."
    elif tag == "CODIGO":
        head = "> **ESTADO 2026-10-14: [CODIGO]** — Paquete de código para kernels privados."
        tail = f"> Los módulos de la release líquida están en el repo (`edgelab/data/liquid_release/`), no en este paquete salvo que se indique."
    elif tag == "CONTEXTO-L2":
        head = "> **ESTADO 2026-10-14: [CONTEXTO-L2]** — Contexto de libro (L2)."
        tail = f"> Los ticks de futuros CME vigentes están en `{release}`; los ticks que este dataset contenga quedan reemplazados por ella."
    else:
        head = "> **ESTADO 2026-10-14: [ARCHIVO]** — Artefacto de investigación histórico."
        tail = "> Verificar procedencia y fuentes antes de reutilizar: puede derivar de datos sin sanear."
    return "\n".join([head, tail, f"> Detalle: {note}",
                      "> Holdout (trade date >= 2026-10-01): **no leer**. Privado; sin redistribución.",
                      "> Índice del espacio: `nicolasbuttaro/edgelab-data-catalog` → `KAGGLE_SPACE_INDEX.md`.", ""])


def compose(slug: str, spec: dict, info: dict, mp: dict) -> dict:
    tag = spec["tag"]
    title0 = info.get("title") or slug
    t = f"[{SHORT[tag]}] {title0}"
    title = t if len(t) <= 50 else title0
    sub = f"{tag} 2026-10-14: " + (f"reemplazado por edgelab-liquid-ticks-20261014" if tag in ("REEMPLAZADO", "CUARENTENA", "DERIVADO-BLOQUEADO") else spec["note"])
    sub = sub[:80]
    if len(sub) < 20:
        sub = (sub + " " * 20)[:20]
    desc0 = info.get("description") or ""
    marker = "ESTADO 2026-10-14"
    if marker in desc0:                       # idempotente: no se apila el banner dos veces
        desc0 = desc0.split("\n\n---\n\n", 1)[-1] if "\n\n---\n\n" in desc0 else desc0
    desc = banner(tag, spec["note"], mp["release_slug"], mp["tags"]) + ("\n---\n\n" + desc0 if desc0.strip() else "")
    lic = info.get("licenses") or [{"name": "other"}]
    return {"title": title, "subtitle": sub, "description": desc, "id": f"{OWNER}/{slug}", "licenses": lic,
            "isPrivate": True, "keywords": info.get("keywords") or []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True)
    ap.add_argument("--backup", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    mp = json.loads(Path(a.map).read_text(encoding="utf-8"))
    out = Path(a.out)
    ok = bad = 0
    for slug, spec in mp["datasets"].items():
        if a.only and slug not in a.only:
            continue
        bf = Path(a.backup) / slug / "dataset-metadata.json"
        if not bf.exists():
            print("SIN RESPALDO", slug)
            bad += 1
            continue
        info = load_info(bf)
        md = compose(slug, spec, info, mp)
        d = out / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "dataset-metadata.json").write_text(json.dumps(md, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{'APLICA' if a.apply else 'SIMULA'} {slug:48s} {spec['tag']:18s} título={md['title'][:50]!r}")
        if a.apply:
            r = subprocess.run(["kaggle", "datasets", "metadata", f"{OWNER}/{slug}", "--update", "-p", str(d)], capture_output=True, text=True)
            if r.returncode != 0:
                print("   ERROR:", (r.stdout + r.stderr).strip()[:200])
                bad += 1
                continue
        ok += 1
    print(f"{ok} ok, {bad} con problema")
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Genera KAGGLE_SPACE_INDEX.md/json: el mapa del espacio de Kaggle (datasets por estado y kernels por familia).

Entradas: config/kaggle_space_map_*.json, CSV de `kaggle datasets list --mine -v` y de `kaggle kernels list --mine -v`.
Uso: python tools/kaggle_space_index.py --map ... --datasets-csv ... --kernels-csv ... --out DIR [--release-json release_manifest.json]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

FAMILIES = [
    (r"^edgelab-aggregates|^edgelab-es-nq-aggregates", "Agregados 1/30/60 s sobre resolver v15 (BLOQUEADOS)"),
    (r"^edgelab-avzp2|^edgelab-avzgrid|^edgelab-avzrac|^edgelab-avzpob|^edgelab-avzvol", "AVZP2 / AVZVOL (zonas de volumen y racimos)"),
    (r"^edgelab-avcl|^edgelab-racc|^edgelab-rac25|^edgelab-racimo|^edgelab-rac-", "aVolClusterPOI (campañas AVCL y racimos)"),
    (r"^edgelab-vtd|^edgelab-vela", "VolTicksDef (VTD)"),
    (r"^edgelab-brk", "VTD-BRACKET (estrategia bilateral)"),
    (r"^edgelab-hftret|^edgelab-hftv4", "HFTZones V4 (retorno a zona)"),
    (r"^edgelab-emaz|^edgelab-ema|^edgelab-sep|.*ema3", "EMA (alineación y separación)"),
    (r"^edgelab-probe|^edgelab-multiasset|^edgelab-idm|tickbar|nq0926|contract-regime|nq-contract", "Infra, sondas y diagnósticos"),
    (r"^edgelab-ema-zones|^edgelab-emaz", "EMA zonas (EMAZ)"),
    (r"bt2a|gc-ae|ae-causal|gc-focused|gc-a-support", "BT2A / AE / GC (otras campañas)"),
    (r"crossfamily|phenomena|confluence|continuous|target-free|full-primary|resampling|custody|^edgelab-mnq-(0|1)", "MNQ/GC cross-family y fenómenos (otras campañas)"),
    (r"momentum|mom-short|rty60|rty-sin", "Momentum multiactivo"),
    (r"funnel|synthetic|framework|cgroup|discovery-parity|tbzx", "Funnel, framework sintético y TBZX"),
    (r"^notebook", "Notebooks sin nombre (scratch)"),
]


def family(slug: str) -> str:
    for pat, name in FAMILIES:
        if re.search(pat, slug):
            return name
    return "Otros"


def read_csv(path):
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        for row in r:
            if row and row[0].startswith("nicolasbuttaro/"):
                rows.append(row)
    seen, out = set(), []
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True)
    ap.add_argument("--datasets-csv", required=True)
    ap.add_argument("--kernels-csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--release-json")
    a = ap.parse_args()
    mp = json.loads(Path(a.map).read_text(encoding="utf-8"))
    ds = {r[0].split("/")[1]: r for r in read_csv(a.datasets_csv)}
    ks = read_csv(a.kernels_csv)
    rel = json.loads(Path(a.release_json).read_text(encoding="utf-8")) if a.release_json else None
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    L = ["# Mapa del espacio de Kaggle de EdgeLab — 2026-10-14", "",
         "Generado por `tools/kaggle_space_index.py`. **Todo está en privado.** Las etiquetas viven en el título/subtítulo/descripción de cada dataset;",
         "el contenido (archivos y versiones) no se tocó. Holdout (trade date >= 2026-10-01): no leer.", ""]
    if rel:
        L += ["## Qué usar hoy", "",
              f"**`{mp['release_slug']}`** — estado `{rel['status']}`: un Parquet de ticks por activo ({len(rel['assets'])} activos), sólo sesiones con contrato líquido "
              "elegido causalmente, sin holdout. Leer `README_AGENTES.md` dentro del dataset. La política de liquidez es una **propuesta sin aprobar**.", ""]
    L += ["## Datasets por estado", ""]
    by = defaultdict(list)
    for slug, spec in mp["datasets"].items():
        by[spec["tag"]].append(slug)
    for tag, desc in mp["tags"].items():
        slugs = by.get(tag, [])
        if not slugs and tag != "ACTIVO-CANDIDATO":
            continue
        L += [f"### [{tag}] — {desc}", "", "| dataset | tamaño MB | última actualización | nota |", "|---|---:|---|---|"]
        if tag == "ACTIVO-CANDIDATO":
            L.append(f"| `{mp['release_slug'].split('/')[1]}` | — | 2026-10-14 | release líquida candidata |")
        for s in sorted(slugs):
            r = ds.get(s)
            size = f"{int(r[2]) / 1048576:,.0f}" if r else "?"
            upd = r[3][:10] if r else "?"
            L.append(f"| `{s}` | {size} | {upd} | {mp['datasets'][s]['note']} |")
        L.append("")
    missing = [s for s in ds if s not in mp["datasets"] and s != mp["release_slug"].split("/")[1]]
    if missing:
        L += ["### Sin clasificar (revisar)", ""] + [f"- `{s}`" for s in sorted(missing)] + [""]
    fam = defaultdict(list)
    for r in ks:
        fam[family(r[0].split("/")[1])].append(r)
    L += [f"## Kernels ({len(ks)}) — todos privados y descartables (scratch de campañas)", "",
          "Los kernels son ejecuciones puntuales; **los resultados y su interpretación viven en el repo** (`docs/research/`, `docs/infra/`).",
          "Un kernel no es evidencia por sí mismo. No se borró ninguno.", "", "| familia | cantidad | ejemplos |", "|---|---:|---|"]
    for name, rows in sorted(fam.items(), key=lambda kv: -len(kv[1])):
        ex = ", ".join(f"`{r[0].split('/')[1]}`" for r in rows[:3])
        L.append(f"| {name} | {len(rows)} | {ex} |")
    L.append("")
    (out / "KAGGLE_SPACE_INDEX.md").write_text("\n".join(L), encoding="utf-8")
    (out / "KAGGLE_SPACE_INDEX.json").write_text(json.dumps(dict(
        date=mp["date"], release=mp["release_slug"], datasets={s: dict(tag=sp["tag"], note=sp["note"]) for s, sp in mp["datasets"].items()},
        kernels={n: [r[0].split("/")[1] for r in rows] for n, rows in fam.items()}), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(ds)} datasets, {len(ks)} kernels, {len(fam)} familias")


if __name__ == "__main__":
    main()

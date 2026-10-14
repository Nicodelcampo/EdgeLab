#!/usr/bin/env python3
"""Genera docs/INDEX.md y docs/INDEX.csv: catalogo de toda la documentacion del repo, por familia, con fecha, estado y titulo.

Uso:
  python tools/docs_index.py --write    regenera los dos archivos
  python tools/docs_index.py --check    sale 1 si el indice esta desactualizado o si hay documentos nuevos sin `Estado:`

Es determinista: no usa la fecha actual ni el orden del sistema de archivos. Ver docs/DOCUMENTATION_PROTOCOL.md.
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED = {"docs/INDEX.md", "docs/MODULES.md"}
HEADER_REQUIRED_FROM = "2026-10-14"        # los documentos con fecha >= esta deben declarar `Estado:`
HEAD_LINES = 30

RE_DATE_LINE = re.compile(r"^\W*(?:\*\*)?Fecha(?:\*\*)?\s*:?\s*\**\s*(\d{4}-\d{2}-\d{2})", re.I)
RE_STATE = re.compile(r"^\W*(?:\*\*)?Estado(?: actual)?(?:\*\*)?\s*:\s*(.+)$", re.I)
RE_FILE_DATE = re.compile(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})")


def _read_head(path: Path) -> list[str]:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return [next(f, "").rstrip("\r\n") for _ in range(HEAD_LINES)]
    except OSError:
        return []


def _family(rel: str) -> str:
    p = Path(rel)
    if len(p.parts) == 1:
        return "raiz"
    if p.parts[:2] == ("docs", "research") and len(p.parts) == 3:
        m = re.match(r"([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)[_.]", p.name)
        return (m.group(1).upper() if m else p.stem.upper())
    return "/".join(p.parts[:-1]) if len(p.parts) > 2 else p.parts[0]


def describe(root: Path, path: Path) -> dict:
    rel = path.relative_to(root).as_posix()
    head = _read_head(path)
    title = next((l[2:].strip() for l in head if l.startswith("# ")), "")
    date = ""
    state = ""
    for l in head:
        if not date:
            m = RE_DATE_LINE.match(l)
            if m:
                date = m.group(1)
        if not state:
            m = RE_STATE.match(l)
            if m:
                state = re.sub(r"[*`]", "", m.group(1)).strip()[:80]
    if not date:
        m = RE_FILE_DATE.search(path.name)
        if m:
            date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    superseded = int(any("SUPERADO" in l.upper() for l in head[:15]))
    return dict(path=rel, family=_family(rel), date=date, status=state, superseded=superseded, title=title[:140])


def collect(root: Path = ROOT) -> list[dict]:
    files = [p for p in root.glob("*.md")]
    for sub in ("docs",):
        files += [p for p in (root / sub).rglob("*.md")]
    rows = []
    for p in sorted(set(files), key=lambda q: q.relative_to(root).as_posix()):
        rel = p.relative_to(root).as_posix()
        if rel in GENERATED:
            continue
        rows.append(describe(root, p))
    return rows


def violations(rows: list[dict]) -> list[str]:
    out = []
    for r in rows:
        if r["path"] in GENERATED or "MANIFIESTO" in Path(r["path"]).name.upper():
            continue                        # los manifiestos son inmutables: no se les agrega encabezado despues de congelados
        if r["date"] and r["date"] >= HEADER_REQUIRED_FROM and r["path"].startswith("docs/") and not r["status"]:
            out.append(f"{r['path']}: falta `Estado:` en el encabezado")
    return out


def render_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["path", "family", "date", "status", "superseded", "title"])
    for r in rows:
        w.writerow([r["path"], r["family"], r["date"], r["status"], r["superseded"], r["title"]])
    return buf.getvalue()


def render_md(rows: list[dict]) -> str:
    handoffs = sorted([r for r in rows if Path(r["path"]).name.startswith("HANDOFF_") and r["date"]], key=lambda r: (r["date"], r["path"]))
    cur = handoffs[-1] if handoffs else None
    L = ["# Indice de documentacion de EdgeLab", "",
         "> Generado por `python tools/docs_index.py --write`. **No editar a mano.** Reglas: `docs/DOCUMENTATION_PROTOCOL.md`. Listado completo: `docs/INDEX.csv`.", ""]
    L.append("## Entrada vigente")
    L.append("")
    L.append(f"`{cur['path']}` ({cur['date']})" if cur else "(sin handoff)")
    L += ["", "Despues: `docs/PRODUCT.md` (producto y roadmap) → `docs/MODULES.md` (modulos) → `PENDIENTE.md` (decisiones abiertas).", ""]
    by_area: dict[str, int] = defaultdict(int)
    for r in rows:
        parts = Path(r["path"]).parts
        by_area["raiz" if len(parts) == 1 else "/".join(parts[:2]) if parts[0] == "docs" and len(parts) > 2 else parts[0]] += 1
    L += ["## Por area", "", "| Area | Documentos |", "|---|---:|"]
    for k in sorted(by_area):
        L.append(f"| `{k}` | {by_area[k]} |")
    fam: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["path"].startswith("docs/research/") and Path(r["path"]).parent.as_posix() == "docs/research":
            fam[r["family"]].append(r)
    L += ["", "## Familias en `docs/research` (por actividad reciente)", "", "| Familia | Docs | Ultimo | Fecha | Estado |", "|---|---:|---|---|---|"]
    for f, rs in sorted(fam.items(), key=lambda kv: (max(x["date"] for x in kv[1]) or "", kv[0]), reverse=True)[:60]:
        last = sorted(rs, key=lambda r: (r["date"], r["path"]))[-1]
        L.append(f"| {f} | {len(rs)} | `{Path(last['path']).name}` | {last['date']} | {last['status'] or '-'} |")
    sup = [r for r in rows if r["superseded"]]
    L += ["", f"## Superados ({len(sup)})", ""]
    for r in sup[:80]:
        L.append(f"- `{r['path']}` — {r['status'] or 'SUPERADO'}")
    if len(sup) > 80:
        L.append(f"- … y {len(sup) - 80} mas (ver CSV)")
    v = violations(rows)
    L += ["", f"## Documentos nuevos sin `Estado:` ({len(v)})", ""] + ([f"- {x}" for x in v] or ["Ninguno."])
    L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args()
    rows = collect()
    md, cs = render_md(rows), render_csv(rows)
    md_path, csv_path = ROOT / "docs" / "INDEX.md", ROOT / "docs" / "INDEX.csv"
    if a.write:
        md_path.write_text(md, encoding="utf-8", newline="\n")
        csv_path.write_text(cs, encoding="utf-8", newline="\n")
        print(f"{len(rows)} documentos indexados")
        return 0
    bad = []
    for p, txt in ((md_path, md), (csv_path, cs)):
        cur = p.read_text(encoding="utf-8").replace("\r\n", "\n") if p.exists() else None
        if cur != txt:
            bad.append(f"{p.relative_to(ROOT)} desactualizado: correr --write")
    bad += violations(rows)
    for b in bad:
        print("FALLA:", b)
    print(f"{len(rows)} documentos, {len(bad)} problemas")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

"""Ventanas del holdout ya consumidas y aperturas por familia (revisión del 2026-10-24).

Una mirada al holdout, exploratoria o confirmatoria, CONSUME las sesiones que vio para su familia y para las familias que
derivan de ella (diseño informado por ese resultado). Este libro (append-only, versionado en el repo) lo hace cumplir:
  - `consumida`: familia, desde, hasta (YYYYMMDD) y `relacionadas` (familias cuyo diseño heredó la mirada);
  - `apertura`: la apertura confirmatoria de una familia (una sola por familia, la registra el embudo al escribir el acta).
`problemas(familia, desde, cid)` devuelve por qué una apertura NO puede hacerse; vacío = permitida.
Mover una ventana hacia adelante protege más; ningún registro se borra ni se edita (una corrección es una línea nueva).
"""
from __future__ import annotations
import json, time
from pathlib import Path

LIBRO = Path(__file__).resolve().parents[2] / "docs/research/HOLDOUT_VENTANAS.jsonl"


def leer(libro: Path = LIBRO) -> list:
    p = Path(libro)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def ultima_consumida(familia: str, libro: Path = LIBRO) -> int | None:
    hs = [int(r["hasta"]) for r in leer(libro) if r.get("tipo") == "consumida" and (r["familia"] == familia or familia in r.get("relacionadas", []))]
    return max(hs) if hs else None


def problemas(familia: str, desde: int, cid: str, libro: Path = LIBRO) -> list:
    e = []
    u = ultima_consumida(familia, libro)
    if u is not None and int(desde) <= u:
        e.append(f"holdout.desde={desde} reusa sesiones ya consumidas por la familia {familia} (o una de la que deriva) hasta {u}; debe empezar después")
    otras = [r["cid"] for r in leer(libro) if r.get("tipo") == "apertura" and r["familia"] == familia and r["cid"] != cid]
    if otras: e.append(f"la familia {familia} ya tiene su única apertura del holdout ({otras[0]})")
    return e


def registrar_apertura(familia: str, cid: str, desde: int, n_fijo: int, libro: Path = LIBRO, ahora=None) -> dict:
    if any(r.get("tipo") == "apertura" and r["familia"] == familia and r["cid"] == cid for r in leer(libro)):
        return {}
    row = dict(tipo="apertura", familia=familia, cid=cid, desde=int(desde), n_fijo=int(n_fijo), ts=ahora or time.time())
    Path(libro).parent.mkdir(parents=True, exist_ok=True)
    with Path(libro).open("a", encoding="utf-8", newline="\n") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row

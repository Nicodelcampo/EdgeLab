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


def reuso_autorizado(familia: str, libro: Path = LIBRO) -> dict | None:
    """Decisión de Nico (2026-10-24): una familia cuya regla se congeló ANTES de la mirada exploratoria y no cambió después puede
    reusar esas sesiones, sólo con un estadístico válido ante miradas (e-proceso de edgelab/funnel/secuencial.py) que arranca en
    la frontera. Se reporta siempre también el resultado sin las sesiones miradas."""
    rs = [r for r in leer(libro) if r.get("tipo") == "reuso_autorizado" and r["familia"] == familia]
    return rs[-1] if rs else None


def ultima_consumida(familia: str, libro: Path = LIBRO) -> int | None:
    hs = [int(r["hasta"]) for r in leer(libro) if r.get("tipo") == "consumida" and (r["familia"] == familia or familia in r.get("relacionadas", []))]
    return max(hs) if hs else None


def problemas(familia: str, desde: int, cid: str, libro: Path = LIBRO, estadistico: str | None = None) -> list:
    e = []
    u = ultima_consumida(familia, libro)
    ra = reuso_autorizado(familia, libro)
    if u is not None and int(desde) <= u and ra and estadistico == "e_proceso" and int(desde) >= int(ra["desde"]):
        u = None                                                                 # reuso autorizado: válido sólo con e-proceso
    elif u is not None and int(desde) <= u and ra:
        e.append(f"la familia {familia} tiene reuso autorizado de sus sesiones miradas sólo con estadistico='e_proceso' (válido ante miradas)")
        u = None
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


def sincronizar(origen: Path = LIBRO, destino: Path | None = None) -> int:
    """Agrega a `destino` las filas de `origen` que le faltan (unión append-only; no borra ni reordena). En el Debian el embudo
    escribe sus aperturas en el clon de ESTADO (que sync_state.sh sube a `autopilot/state`), no en el clon de código fijado: antes
    las escribía en `docs/` del clon de código, donde no se publicaban y bloqueaban `update.sh`. Este paso trae al libro del
    estado las ventanas consumidas que se registran en el repo. Devuelve cuántas filas agregó."""
    if destino is None or Path(destino).resolve() == Path(origen).resolve(): return 0
    tiene = {json.dumps(r, sort_keys=True) for r in leer(destino)}
    nuevas = [r for r in leer(origen) if json.dumps(r, sort_keys=True) not in tiene]
    if nuevas:
        Path(destino).parent.mkdir(parents=True, exist_ok=True)
        with Path(destino).open("a", encoding="utf-8", newline="\n") as f:
            for r in nuevas: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(nuevas)

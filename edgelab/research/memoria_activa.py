"""Memoria activa con bloqueo automatico de repeticiones e invalidaciones.

Conecta `docs/research/FACTORES.jsonl` (`NO_REPETIR`), `docs/research/LINAJES.jsonl`
y `edgelab/edge_brain/invalidation.py` como compuerta fail-closed en
`preflight.validar_preregistro` y `puerta_corrida`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from edgelab.edge_brain.invalidation import (
    DependencyEdge,
    INVALIDATED,
    STALE,
    propagate_invalidation,
)
from edgelab.research import factores as FA

ROOT = Path(__file__).resolve().parents[2]
CAMBIO_FALLA_RX = re.compile(
    r"^(?:Cambio respecto a falla previa|Diferencia respecto a NO_REPETIR)\s*:\s*\S+",
    re.M | re.I,
)
_STOPWORDS = {
    "para", "sobre", "entre", "desde", "hasta", "contra", "solo", "como", "cada",
    "cuando", "donde", "tiene", "tienen", "antes", "despues", "durante", "sin",
    "pero", "porque", "segun", "mediante", "todos", "todas", "mismo", "misma",
    "regla", "familia", "mercado", "operacion", "operaciones", "datos", "neto",
    "bruto", "vela", "velas", "sesion", "sesiones", "dia", "dias", "anio", "anios",
}


def _tokens_dominio(texto: str) -> set[str]:
    limpio = re.sub(r"[`*_#>\[\]()\"',.:;/\\|+-]", " ", str(texto or "").lower())
    out = set()
    for tok in limpio.split():
        if len(tok) >= 4 and tok not in _STOPWORDS:
            out.add(tok)
    return out


def _texto_propuesta_sin_antecedentes(texto: str) -> str:
    """Excluye lineas informativas `Antecedentes:` / `Cambio respecto a falla previa:` al detectar colisiones."""
    out = []
    for line in str(texto or "").splitlines():
        low = line.strip().lower()
        if low.startswith(("antecedentes:", "cambio respecto a falla previa:", "diferencia respecto a no_repetir:")):
            continue
        out.append(line)
    return "\n".join(out)


def _ancestros_familia(familia: str | None, root: Path) -> list[str]:
    if not familia:
        return []
    lin_path = root / "docs" / "research" / "LINAJES.jsonl"
    if not lin_path.exists():
        return [familia]
    padres = {}
    for line in lin_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            padres[r["familia"]] = r.get("padres") or []
    vistos: list[str] = []
    cola = [familia]
    while cola:
        f = cola.pop(0)
        if f in vistos:
            continue
        vistos.append(f)
        cola.extend(padres.get(f, []))
    return vistos


def cargar_no_repetir(root: Path | None = None) -> list[dict[str, Any]]:
    """Devuelve todas las entradas vigentes en estado `NO_REPETIR`."""
    base = ROOT if root is None else Path(root)
    libro = base / "docs" / "research" / "FACTORES.jsonl"
    return [e for e in FA.cargar(libro) if e.get("estado") == "NO_REPETIR"]


def detectar_colisiones(
    texto: str,
    familia: str | None = None,
    root: Path | None = None,
    dependencias: Iterable[DependencyEdge] | None = None,
    ids_invalidados: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Detecta colisiones con entradas `NO_REPETIR` e invalidaciones en cadena."""
    base = ROOT if root is None else Path(root)
    no_rep = cargar_no_repetir(base)
    cuerpo = _texto_propuesta_sin_antecedentes(texto)
    cuerpo_tokens = _tokens_dominio(cuerpo)
    cuerpo_up = cuerpo.upper()
    ancestros = {a.upper() for a in _ancestros_familia(familia, base)}

    colisiones_nr: list[dict[str, Any]] = []
    for item in no_rep:
        fid = str(item.get("id", ""))
        motivos: list[str] = []
        if fid and fid.upper() in cuerpo_up:
            motivos.append("mencion_directa_id")
        if ancestros:
            haystack = " ".join([fid, str(item.get("factor", "")), " ".join(item.get("evidencia", []))]).upper()
            if any(re.search(rf"\b{re.escape(a)}\b", haystack) for a in ancestros if len(a) >= 4):
                motivos.append("linaje_familia")
        f_tokens = _tokens_dominio(f"{item.get('factor', '')} {item.get('donde', '')}")
        comunes = cuerpo_tokens & f_tokens
        cobertura = len(comunes) / max(len(f_tokens), 1)
        if len(comunes) >= 4 and cobertura >= 0.45:
            motivos.append(f"solapamiento_semantico({len(comunes)}/{len(f_tokens)}={cobertura:.2f})")
        if motivos:
            colisiones_nr.append({
                "id": fid,
                "factor": item.get("factor", ""),
                "siguiente": item.get("siguiente", ""),
                "motivos": motivos,
                "tokens_comunes": sorted(comunes)[:8],
            })

    invalidados: dict[str, str] = {}
    if ids_invalidados and dependencias:
        estados = propagate_invalidation(ids_invalidados, dependencias)
        objetivos = ({familia} if familia else set()) | ancestros
        for nid, st in estados.items():
            if st in (INVALIDATED, STALE) and (nid in objetivos or nid in texto):
                invalidados[nid] = st

    return {
        "colisiones_no_repetir": colisiones_nr,
        "dependencias_invalidadas": invalidados,
        "tiene_justificacion_cambio": bool(CAMBIO_FALLA_RX.search(texto)),
    }


def verificar_memoria_activa(
    texto: str,
    familia: str | None = None,
    root: Path | None = None,
    dependencias: Iterable[DependencyEdge] | None = None,
    ids_invalidados: Iterable[str] | None = None,
) -> list[str]:
    """Devuelve errores bloqueantes si hay colision NO_REPETIR/INVALIDATED sin justificacion estructural."""
    base = ROOT if root is None else Path(root)
    res = detectar_colisiones(
        texto,
        familia=familia,
        root=base,
        dependencias=dependencias,
        ids_invalidados=ids_invalidados,
    )
    errs: list[str] = []
    if res["colisiones_no_repetir"] and not res["tiene_justificacion_cambio"]:
        ids = ", ".join(c["id"] for c in res["colisiones_no_repetir"][:5])
        errs.append(
            f"memoria activa: colisiona con NO_REPETIR ({ids}) y falta "
            "«Cambio respecto a falla previa: <que cambia estructuralmente>»"
        )
    if res["dependencias_invalidadas"] and not res["tiene_justificacion_cambio"]:
        deps = ", ".join(f"{k}={v}" for k, v in sorted(res["dependencias_invalidadas"].items()))
        errs.append(
            f"memoria activa: artefacto/dependencia invalidada ({deps}); "
            "declarar «Cambio respecto a falla previa: ...»"
        )
    return errs

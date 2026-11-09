"""Registro de FACTORES: lo más valioso que EdgeLab ya descubrió, en un solo lugar (pedido de Nico, 2026-11-09).

Criterio central: economizar esfuerzo. Antes de abrir una familia nueva se indaga lo que ya mostró algo (qué factor dio la ventaja,
dónde, cuánto, y cuál es la prueba más barata que lo confirma o lo mata). Lo refutado con potencia también es un factor: dice qué no
repetir. El libro es `docs/research/FACTORES.jsonl` (se agrega, no se reescribe: corregir = entrada nueva con `reemplaza`); de él se
genera `docs/research/FACTORES_CON_VENTAJA.md`, que va en el núcleo de contexto de todos los roles del agente del Debian.

Un factor no es evidencia para promover nada: ordena la investigación. Toda entrada cita archivos del repo que existen.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIBRO = ROOT / "docs/research/FACTORES.jsonl"
SALIDA = ROOT / "docs/research/FACTORES_CON_VENTAJA.md"
ESTADOS = {  # orden = prioridad de atención
    "PISTA_VIVA": "Mostró algo y no está confirmado ni refutado: es lo primero a indagar",
    "PALANCA_DE_DISENO": "Lección confirmada que se aplica al DISEÑAR reglas (no es un filtro de mercado)",
    "PROPUESTO_META": "Extraído por el meta-analista de una campaña cerrada; falta revisión",
    "EN_SEGUIMIENTO": "Regla congelada que se sigue hacia adelante (papel)",
    "NO_REPETIR": "Refutado con potencia o explicado por un artefacto: no volver a proponerlo igual",
    "SIN_FACTOR": "Campaña cerrada sin nada aprovechable (queda asentado que se miró)",
}
CAMPOS = ("id", "fecha", "estado", "factor", "efecto", "donde", "evidencia", "siguiente", "origen")


def cargar(libro: Path = LIBRO) -> list:
    """Entradas vigentes (las reemplazadas por otra no se devuelven), en orden de alta."""
    if not libro.exists(): return []
    es = [json.loads(l) for l in libro.read_text(encoding="utf-8").splitlines() if l.strip()]
    viejas = {e["reemplaza"] for e in es if e.get("reemplaza")}
    return [e for e in es if e["id"] not in viejas]


def registrar(*, id: str, fecha: str, estado: str, factor: str, efecto: str, donde: str, evidencia: list, siguiente: str,
              origen: str = "humano", reemplaza: str | None = None, libro: Path = LIBRO, root: Path = ROOT) -> dict:
    if estado not in ESTADOS: raise ValueError(f"estado desconocido: {estado}")
    faltan = [p for p in evidencia if not (root / p).exists()]
    if not evidencia or faltan: raise ValueError(f"evidencia inexistente o vacía: {faltan}")
    todas = [json.loads(l) for l in libro.read_text(encoding="utf-8").splitlines() if l.strip()] if libro.exists() else []
    if any(e["id"] == id for e in todas): raise ValueError(f"id repetido: {id}")
    if reemplaza and not any(e["id"] == reemplaza for e in todas): raise ValueError(f"reemplaza un id que no existe: {reemplaza}")
    e = dict(id=id, fecha=fecha, estado=estado, factor=factor, efecto=efecto, donde=donde, evidencia=list(evidencia), siguiente=siguiente, origen=origen)
    if reemplaza: e["reemplaza"] = reemplaza
    with libro.open("a", encoding="utf-8") as f: f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return e


def markdown(libro: Path = LIBRO) -> str:
    es = cargar(libro)
    L = ["# Factores con ventaja — lo más valioso descubierto y qué indagar primero", "",
         "Estado: VIGENTE (GENERADO de `docs/research/FACTORES.jsonl` con `python tools/factores.py --write`; no editar a mano).", "",
         "Regla de uso: **antes de abrir una familia nueva, indagá una PISTA_VIVA o aplicá una PALANCA_DE_DISENO**; lo que está en NO_REPETIR",
         "no se vuelve a proponer igual. Un factor ordena la investigación, no es evidencia para promover.", ""]
    for est, que in ESTADOS.items():
        sub = [e for e in es if e["estado"] == est]
        if not sub: continue
        L += [f"## {est} ({len(sub)})", "", f"_{que}._", ""]
        for e in sorted(sub, key=lambda e: e["fecha"], reverse=True):
            L += [f"- **{e['factor']}** (`{e['id']}`, {e['fecha']}, {e['origen']})", f"  - Efecto: {e['efecto']}", f"  - Dónde: {e['donde']}",
                  f"  - Siguiente: {e['siguiente']}", f"  - Evidencia: {', '.join('`' + p + '`' for p in e['evidencia'])}"]
        L.append("")
    return "\n".join(L)


def escribir() -> None:
    SALIDA.write_text(markdown(), encoding="utf-8")

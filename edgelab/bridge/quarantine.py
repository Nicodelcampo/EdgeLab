# -*- coding: utf-8 -*-
"""Cuarentena de datos por versión/hash del indicador que los generó.

**Decisión B de Nico, 2026-07-26.** El histórico de `AACloseOpenDiffs` anterior a
v1.1 no se mergea nunca más.

## Por qué el filtro tiene que ser ESTRUCTURAL

La versión débil de esta decisión es "acordarse de no usar los datos viejos".
Eso falla de tres maneras previsibles: alguien nuevo no lo sabe, el que lo sabe
se olvida seis meses después, o un script lo lee automáticamente sin que nadie
mire. Y el defecto es **silencioso** — un CSV contaminado se parsea igual de
bien que uno limpio, sólo que le faltan el 47 % de los gaps de 1 tick.

Acá el filtro vive en el camino de ingesta: `oracle.parse_nt8_log()` consulta
esta tabla y **levanta** ante un archivo en cuarentena. No hay que acordarse de
nada; hay que desactivarlo a propósito, y eso deja rastro.

## Qué NO hace

No borra. El material en cuarentena se conserva crudo para forense —es la
evidencia de la magnitud del defecto (43,5 % observado)— pero sale del camino
por el que se consume.
"""
from __future__ import annotations

import os
import re


class DatosEnCuarentena(RuntimeError):
    """Se intentó ingerir datos generados por una versión en cuarentena."""


# ---------------------------------------------------------------------------
# Registro. Una entrada por (indicador, versión mínima limpia).
#
# `min_version_limpia` es INCLUSIVA: todo lo generado con una versión ESTRICTAMENTE
# menor está contaminado. Se compara por tupla de enteros, no lexicográficamente
# — "1.10" < "1.9" como texto y eso sería un bug silencioso el día que haya diez
# versiones menores.
# ---------------------------------------------------------------------------
CUARENTENA = {
    "AACloseOpenDiffs": dict(
        min_version_limpia="1.1",
        fecha="2026-07-26",
        decision="Decisión B de Nico",
        motivo=(
            "v1.0 comparaba el umbral de tamaño en points: "
            "`gapPts < MinDiffTicks * TickSize`. Descartaba el 47,5 % predicho "
            "(43,5 % observado contra el oráculo) de los gaps de EXACTAMENTE "
            "1 tick, por el bug de 1 ULP del feed."),
        sesgo=(
            "NO es ruido aleatorio: es un sesgo SISTEMÁTICO hacia los gaps "
            "grandes, y está CORRELACIONADO con el nivel de precio (depende de "
            "qué niveles caen 1 ULP por debajo de la grilla). Cualquier "
            "estadística de tamaño de gap sobre estos datos está corrida hacia "
            "arriba, y cualquier análisis condicionado a nivel de precio hereda "
            "la correlación."),
        ref="docs/audits/AUDIT-003_barrido_ulp.md",
    ),
}

_RE_META = re.compile(r"indicator\s*=\s*([A-Za-z0-9_]+)")
_RE_VER = re.compile(r"version\s*=\s*([0-9]+(?:\.[0-9]+)*)")


def _tupla(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except (TypeError, ValueError):
        return None


def evaluar_meta(meta: str):
    """Clasifica una línea `# meta` como limpia o en cuarentena.

    Devuelve `dict(estado=..., indicador=..., version=..., motivo=...)`.
    `estado` ∈ {"limpio", "cuarentena", "indeterminado"}.

    **"indeterminado" no es "limpio"**: un archivo de un indicador con
    cuarentena declarada pero sin `version=` legible no se puede afirmar limpio,
    así que se trata como contaminado. Fail-closed, igual que el resto de los
    gates del proyecto.
    """
    m = _RE_META.search(meta or "")
    ind = m.group(1) if m else None
    if ind not in CUARENTENA:
        return dict(estado="limpio", indicador=ind, version=None, motivo=None)

    reg = CUARENTENA[ind]
    mv = _RE_VER.search(meta or "")
    ver = mv.group(1) if mv else None
    t_ver, t_min = _tupla(ver), _tupla(reg["min_version_limpia"])
    if t_ver is None:
        return dict(estado="indeterminado", indicador=ind, version=ver,
                    motivo=("sin `version=` legible en el meta. Un archivo de %s "
                            "sin versión no se puede afirmar limpio ⇒ se trata "
                            "como contaminado (fail-closed)." % ind))
    if t_ver < t_min:
        return dict(estado="cuarentena", indicador=ind, version=ver,
                    motivo=reg["motivo"], sesgo=reg["sesgo"], ref=reg["ref"],
                    min_version_limpia=reg["min_version_limpia"])
    return dict(estado="limpio", indicador=ind, version=ver, motivo=None)


def mensaje(res, path=None):
    reg = CUARENTENA.get(res.get("indicador"), {})
    L = ["DATOS EN CUARENTENA — no se ingieren."]
    if path:
        L.append("  archivo : %s" % path)
    L.append("  indicador: %s  version=%s  (limpio desde v%s)"
             % (res.get("indicador"), res.get("version"),
                reg.get("min_version_limpia", "?")))
    L.append("  motivo   : %s" % res.get("motivo"))
    if res.get("sesgo"):
        L.append("  sesgo    : %s" % res["sesgo"])
    L.append("  decision : %s, %s" % (reg.get("decision", "-"), reg.get("fecha", "-")))
    if res.get("ref"):
        L.append("  detalle  : %s" % res["ref"])
    L.append("  El histórico limpio nace con el re-export de la version limpia.")
    return "\n".join(L)


def verificar(meta: str, path=None, *, strict=True):
    """Punto de entrada del camino de ingesta. Levanta si está en cuarentena."""
    res = evaluar_meta(meta)
    if res["estado"] in ("cuarentena", "indeterminado") and strict:
        raise DatosEnCuarentena(mensaje(res, path))
    return res


def verificar_archivo(path, *, strict=True, max_lineas=40):
    """Igual, leyendo el `# meta` del archivo. No carga el archivo entero."""
    metas = []
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for i, ln in enumerate(f):
            if ln.startswith("#"):
                metas.append(ln.rstrip("\r\n"))
            if i >= max_lineas:
                break
    return verificar(" ".join(metas), path, strict=strict)


def escanear(directorio, patron=".csv"):
    """Inventario de un directorio: qué está limpio y qué contaminado.

    Usado por la auditoría de consumidores — contestar "qué análisis comieron
    datos sucios" exige primero saber qué archivos lo están.
    """
    out = []
    for raiz, _, archivos in os.walk(directorio):
        for a in sorted(archivos):
            if not a.endswith(patron):
                continue
            p = os.path.join(raiz, a)
            try:
                r = verificar_archivo(p, strict=False)
            except OSError as e:
                r = dict(estado="ilegible", motivo=str(e))
            if r.get("indicador") in CUARENTENA or r["estado"] != "limpio":
                out.append(dict(path=p, **r))
    return out

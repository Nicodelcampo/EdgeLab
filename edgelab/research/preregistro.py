# -*- coding: utf-8 -*-
"""Pre-registro sellado. **El runner de EXPLORE se niega a correr sin esto.**

## Por qué es código y no un documento

Un pre-registro que vive en un `.md` es una promesa. Ya vimos hoy cómo termina
una regla que vive en prosa: el filtro del holdout estaba escrito en el
docstring del atlas y el atlas consumió 10 días sellados igual (INC-002).

Acá el pre-registro es un objeto con hash. Si no existe, si el hash no cierra,
o si la configuración con la que se corre no coincide con la sellada, **el
estudio no arranca**. No hay bandera para saltearlo.

## Qué obliga a declarar ANTES de mirar nada

Los campos no tienen default a propósito. Cada uno es un grado de libertad que,
si se deja abierto, se elige después de ver resultados:

- **`direccion_por_side`**: qué significa `trapped_buyers` — ¿el precio sube o
  baja? Sin declararlo, se elige el signo que dio positivo. Es la forma más
  barata de fabricar un edge y no deja rastro.
- **`geometria`**: P, N y horizonte. Re-tunearlos viendo el resultado no es
  rescate: es una hipótesis nueva que gasta su propio turno.
- **`convencion_timeout`**: cómo se valúa la salida por horizonte. Puntuarla
  como 0 hace que las geometrías de objetivo cercano parezcan ventajosas cuando
  la esperanza a mercado es exactamente 0 — el artefacto que se detectó en la
  tabla de decisión del 2026-07-27.
- **`inferencia`**: método y parámetros. Elegir entre bootstrap fijo y
  estacionario después de ver los intervalos es búsqueda de especificación.
- **`que_mata_la_idea`**: el resultado que la refuta sin apelación. Sin esto
  escrito de antemano, cualquier resultado se puede narrar como parcialmente
  alentador.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

CAMPOS_OBLIGATORIOS = (
    "id", "hipotesis_unica", "geometria", "direccion_por_side",
    "universo", "nulo", "metrica", "criterio_exito", "inferencia",
    "friccion_rt_ticks", "convencion_timeout", "que_mata_la_idea",
    "secundarios_no_deciden",
)

SUBCAMPOS = {
    "geometria": ("objetivo_ticks", "stop_ticks", "horizonte_min"),
    "universo": ("tipos_de_dia", "instrumento", "manifiesto"),
    "nulo": ("atlas_config_hash", "estratos"),
    "inferencia": ("bootstrap", "permutacion", "reps"),
}

CONVENCIONES_TIMEOUT = ("a_mercado", "cero")


class PreRegistroError(RuntimeError):
    """Falta el pre-registro, no está sellado, o no coincide con la corrida."""


def _hash(spec):
    """Hash del contenido, excluyendo el propio sello."""
    limpio = {k: v for k, v in spec.items() if k != "sello"}
    return hashlib.sha256(
        json.dumps(limpio, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validar(spec):
    """Todos los campos obligatorios presentes y con valor. Fail-closed."""
    faltan = [c for c in CAMPOS_OBLIGATORIOS if spec.get(c) in (None, "", [], {})]
    if faltan:
        raise PreRegistroError(
            "pre-registro incompleto, faltan: %s. Ninguno tiene default a "
            "proposito: cada uno es un grado de libertad que, si queda abierto, "
            "se elige despues de ver resultados." % ", ".join(faltan))
    for campo, subs in SUBCAMPOS.items():
        f2 = [s for s in subs if spec[campo].get(s) in (None, "", [], {})]
        if f2:
            raise PreRegistroError("`%s` incompleto, faltan: %s" % (campo, ", ".join(f2)))
    if spec["convencion_timeout"] not in CONVENCIONES_TIMEOUT:
        raise PreRegistroError(
            "`convencion_timeout` debe ser uno de %s. Puntuar el timeout como "
            "`cero` no es una convencion de P&L: hace que las geometrias de "
            "objetivo cercano parezcan ventajosas cuando su esperanza a mercado "
            "es exactamente 0." % (CONVENCIONES_TIMEOUT,))
    if not spec["direccion_por_side"]:
        raise PreRegistroError("`direccion_por_side` vacio")
    for k, v in spec["direccion_por_side"].items():
        if v not in (1, -1):
            raise PreRegistroError(
                "direccion de `%s` = %r; tiene que ser +1 o -1, declarado antes "
                "de mirar resultados" % (k, v))
    return True


def sellar(spec, path):
    """Valida, estampa el sello y escribe. Si el archivo existe, NO lo pisa."""
    validar(spec)
    if os.path.exists(path):
        raise PreRegistroError(
            "ya existe un pre-registro sellado en %s. Re-sellar es re-escribir "
            "la hipotesis despues de haberla registrado: si de verdad cambio, "
            "es una hipotesis NUEVA con su propio id y su propio turno." % path)
    spec = dict(spec)
    spec["sello"] = dict(hash=_hash(spec),
                         sellado_utc=datetime.now(timezone.utc).isoformat())
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=1, ensure_ascii=False, sort_keys=True)
    return spec


def cargar_sellado(path):
    """Lee y verifica el sello. Un pre-registro editado a mano no pasa."""
    if not os.path.exists(path):
        raise PreRegistroError(
            "no hay pre-registro sellado en %s. El estudio NO corre sin el." % path)
    with open(path, encoding="utf-8") as fh:
        spec = json.load(fh)
    sello = spec.get("sello") or {}
    if not sello.get("hash"):
        raise PreRegistroError("el pre-registro no esta sellado (falta `sello.hash`)")
    if _hash(spec) != sello["hash"]:
        raise PreRegistroError(
            "el hash NO coincide: el pre-registro se edito despues de sellarlo. "
            "sellado=%s calculado=%s" % (sello["hash"][:16], _hash(spec)[:16]))
    validar(spec)
    return spec


def exigir_coherencia(spec, geometria, universo):
    """La corrida tiene que usar EXACTAMENTE lo sellado.

    Sin este chequeo, el sello no sirve de nada: se sella una geometría y se
    corre otra.
    """
    g = spec["geometria"]
    for k in ("objetivo_ticks", "stop_ticks", "horizonte_min"):
        if geometria.get(k) != g[k]:
            raise PreRegistroError(
                "la corrida usa %s=%r y el pre-registro sello %r" % (k, geometria.get(k), g[k]))
    u = spec["universo"]
    if sorted(universo.get("tipos_de_dia") or []) != sorted(u["tipos_de_dia"]):
        raise PreRegistroError(
            "alcance por tipo de dia distinto del sellado: corrida=%s sellado=%s. "
            "El estudio y su nulo tienen que cubrir los MISMOS tipos."
            % (universo.get("tipos_de_dia"), u["tipos_de_dia"]))
    return True

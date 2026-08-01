# -*- coding: utf-8 -*-
"""PUERTA ÚNICA para cargar los días de un estudio. Nadie lee el manifiesto directo.

## Por qué existe: el incidente del 2026-07-27

El atlas de excursiones nulas consumió **10 días del holdout sellado**
(2026-07-06 → 07-21) entre sus 163 días efectivos. El atlas mide MFE/MAE sobre
horizontes futuros: eso es **retorno**, no es `target_free_validation`, y la
regla sellada dice textualmente *"ningún placebo pisa el holdout"*.

**Causa raíz — y no fue un descuido puntual**: el filtro del holdout existía
**sólo en el docstring** del atlas. `universe.py` no filtra por fecha, y hace
bien: el censo debe cubrir todo el rango, porque verificar integridad no gasta
nada. El atlas asumía que alguien más filtraba. **Ninguna capa era responsable,
así que ninguna lo hizo.** El guard `check_holdout` ya existía y estaba bien
escrito; simplemente nadie lo llamaba desde el camino de los estudios.

Poner el filtro dentro de cada estudio repite el mismo error con más superficie:
el estudio número once se escribe sin él y nadie se entera. Por eso esto es una
**puerta única** y hay un test que falla si alguien la esquiva
(`tests/research/test_puerta_unica_holdout.py`).

## Contrato

- `cargar_dias_de_estudio(...)` **nunca** devuelve días `>= HOLDOUT_START` con
  los parámetros por defecto. No hay forma de obtenerlos "sin querer".
- Para incluirlos hay que pasar `incluir_holdout=True` **y** un `purpose`
  válido; entonces se invoca `check_holdout`, que registra la apertura en
  `docs/holdout_access_log.md` y levanta si el propósito no la autoriza.
- Ningún código de investigación setea ese flag. Si alguna vez hace falta, es
  una decisión de Nico y queda escrita en el log por construcción.
"""
from __future__ import annotations

import json
import os

from edgelab.research.holdout_guard import (HOLDOUT_START_ISO, check_holdout)

HOLDOUT_DESDE = HOLDOUT_START_ISO[:10]      # "2026-07-01"


class UniversoError(RuntimeError):
    """Uso incorrecto de la puerta única."""


def cargar_dias_de_estudio(manifiesto, tipos_de_dia=None, *,
                           incluir_holdout=False, purpose=None, caller="?"):
    """Días admisibles para un estudio. **Único camino sancionado.**

    manifiesto: ruta al `manifiesto_universo.json` del censo, o el dict ya leído.
    tipos_de_dia: lista de tipos admitidos (p. ej. `["COMPLETO",
        "CIERRE_SEMANAL"]`). `None` = todos. Es OBLIGATORIO que el estudio y su
        nulo declaren el MISMO alcance: comparar zonas de un tipo de día contra
        un nulo que no lo cubre es comparar contra el nulo equivocado.
    incluir_holdout: sólo `True` con `purpose` explícito. Ningún código de
        investigación lo setea.
    """
    if isinstance(manifiesto, str):
        with open(manifiesto, encoding="utf-8") as fh:
            manifiesto = json.load(fh)
    dias = list(manifiesto.get("dias", []))

    # fail-closed: un manifiesto viejo sin `tipo_de_dia` no se puede acotar por
    # alcance, y correr sin acotar seria meter domingos sin declararlo.
    if tipos_de_dia is not None:
        faltan = [d for d in dias if not d.get("tipo_de_dia")]
        if faltan:
            raise UniversoError(
                "manifiesto sin `tipo_de_dia` en %d dias: regenerar el censo "
                "antes de usarlo en un estudio" % len(faltan))
        dias = [d for d in dias if d["tipo_de_dia"] in tipos_de_dia]

    validos = []
    en_holdout = []
    for d in dias:
        if not (all(k in d for k in ("fecha", "archivo", "n_ticks"))):
            raise UniversoError("Formato de manifiesto inválido.")

        # --- CUARENTENA PERMANENTE (INC-005) ---
        # 2026-07-01 a 2026-07-16 fueron quemados por contaminación cruzada manual.
        # No pueden ser pre-holdout ni holdout. Se destruyen de manera silenciosa
        # al nivel del estudio.
        if "2026-07-01" <= d["fecha"] <= "2026-07-16":
            continue

        if d["fecha"] >= HOLDOUT_DESDE:
            en_holdout.append(d)
        else:
            validos.append(d)

    if not incluir_holdout:
        return validos, dict(
            descartados_holdout=len(en_holdout),
            fechas_holdout=sorted({d["fecha"] for d in en_holdout}))

    if not purpose:
        raise UniversoError(
            "incluir_holdout=True exige `purpose` explícito. El holdout no se "
            "abre por omisión: si de verdad hace falta, es decisión de Nico y "
            "queda registrada en docs/holdout_access_log.md")
    if not en_holdout:
        return dias, dict(descartados_holdout=0, fechas_holdout=[])
    fechas = sorted({d["fecha"] for d in en_holdout})
    check_holdout(fechas[0] + "T00:00:00", fechas[-1] + "T23:59:59",
                  purpose=purpose, caller=caller)
    return dias, dict(descartados_holdout=0, fechas_holdout=fechas,
                      apertura_registrada=True)

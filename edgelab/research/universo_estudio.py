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
    en_cuarentena = []
    for d in dias:
        if not (all(k in d for k in ("fecha", "archivo", "n_ticks"))):
            raise UniversoError("Formato de manifiesto inválido.")

        # --- CUARENTENA PERMANENTE (INC-005, ampliada) ---
        # 2026-07-01 a 2026-07-24 fueron quemados por contaminación cruzada manual.
        # El censo con min()/max() REALES (no primera/última línea del CSV)
        # confirma que la extracción de oráculos alcanza 2026-07-24T17:59:20
        # (BigTrap2_diag_tick25, BigTrap2_time1_v2, Gaps2). El censo anterior
        # leía primera/última línea, que con corridas concatenadas o campos
        # internos con timestamps futuros daba rangos incorrectos o invertidos.
        # No pueden ser pre-holdout ni holdout.
        #
        # OJO: cuarentena y frontera son mecanismos DISTINTOS y ambos hacen
        # falta. La cuarentena quema días por contaminación de procedencia; la
        # frontera (`holdout_guard.HOLDOUT_START_ISO`) sella por metodología.
        # Que un día caiga en cuarentena no dice nada sobre el sello, y
        # viceversa. Colapsarlos en un solo mecanismo perdería una de las dos.
        # El orden importa y no es cosmético. La versión previa hacía
        # `continue` acá, ANTES de clasificar por el sello: eso hacía
        # desaparecer los días quemados de la contabilidad del holdout, así que
        # `descartados_holdout` daba 0 y la puerta ya no podía demostrar que
        # estaba filtrando. Un día puede estar quemado Y sellado a la vez —de
        # hecho hoy TODOS los quemados caen dentro del sello—, y cada mecanismo
        # se contabiliza por separado.
        quemado = "2026-07-01" <= d["fecha"] <= "2026-07-24"
        if quemado:
            en_cuarentena.append(d)

        if d["fecha"] >= HOLDOUT_DESDE:
            en_holdout.append(d)      # contabilidad del sello, quemado o no
        elif not quemado:
            validos.append(d)
        # quemado y pre-holdout: no entra a `validos` ni a ningún otro lado.

    if not incluir_holdout:
        return validos, dict(
            descartados_holdout=len(en_holdout),
            fechas_holdout=sorted({d["fecha"] for d in en_holdout}),
            descartados_cuarentena=len(en_cuarentena),
            fechas_cuarentena=sorted({d["fecha"] for d in en_cuarentena}))

    if not purpose:
        raise UniversoError(
            "incluir_holdout=True exige `purpose` explícito. El holdout no se "
            "abre por omisión: si de verdad hace falta, es decisión de Nico y "
            "queda registrada en docs/holdout_access_log.md")
    # Ni siquiera una apertura sancionada entrega días quemados: la cuarentena
    # es de PROCEDENCIA (el dato está contaminado y no sirve para nada), no de
    # metodología. Antes esta rama devolvía `dias` crudo y los dejaba pasar.
    quemadas = {d["fecha"] for d in en_cuarentena}
    holdout_servible = [d for d in en_holdout if d["fecha"] not in quemadas]
    info_cuarentena = dict(descartados_cuarentena=len(en_cuarentena),
                           fechas_cuarentena=sorted(quemadas))
    if not holdout_servible:
        return validos, dict(descartados_holdout=0, fechas_holdout=[],
                             **info_cuarentena)
    fechas = sorted({d["fecha"] for d in holdout_servible})
    check_holdout(fechas[0] + "T00:00:00", fechas[-1] + "T23:59:59",
                  purpose=purpose, caller=caller)
    return validos + holdout_servible, dict(
        descartados_holdout=0, fechas_holdout=fechas,
        apertura_registrada=True, **info_cuarentena)


#: La puerta es duena de la RUTA, no solo de la lectura. Si el consumidor
#: escribe el literal por su cuenta, `test_nadie_lee_el_manifiesto_por_fuera_de_
#: la_puerta` lo caza -y bien: cada archivo con su copia de la ruta es la primera
#: mitad de "cada archivo con su copia de la regla de filtrado".
def ruta_por_defecto():
    from pathlib import Path
    return Path(__file__).resolve().parents[2] / "runs" / "censo" / "manifiesto_universo.json"


def huella_del_universo(path=None):
    """Huella del manifiesto: sha256, fecha de generacion y cantidad de dias.

    Vive ACA y no en el consumidor por la regla de la puerta unica. El 2026-08-06
    `tools/estado.py` empezo a leer el manifiesto por su cuenta para publicar
    esta huella, y `test_nadie_lee_el_manifiesto_por_fuera_de_la_puerta` lo cazo
    con el mensaje correcto: *"filtrar por su cuenta es el patron que dejo entrar
    10 dias del holdout el 2026-07-27"*.

    La intencion era buena -el manifiesto NO estaba versionado y los dos clones
    daban veredictos opuestos sobre si el estudio puede empezar- pero el camino
    era el prohibido. Esto NO filtra dias ni los entrega: devuelve una huella. El
    modulo que es dueno del manifiesto es el unico que lo abre.
    """
    import hashlib
    import json as _json
    raw = open(str(path or ruta_por_defecto()), "rb").read()
    d = _json.loads(raw.decode("utf-8"))
    return dict(sha256=hashlib.sha256(raw).hexdigest(),
                generado_utc=d.get("generado_utc"),
                n_dias=len(d.get("dias") or []))

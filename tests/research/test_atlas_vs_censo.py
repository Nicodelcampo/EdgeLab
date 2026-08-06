# -*- coding: utf-8 -*-
"""El atlas sellado y el censo vigente no pueden discrepar en silencio.

## Por qué existe

`2025-10-31` entró al atlas sellado desde un manifiesto anterior a que el censo
la reclasificara como `DEFECTUOSO` (tipo_de_dia imposible para un viernes,
cobertura 17 h < 20 h, cierre 23:37 > 16:00). No hubo agujero de holdout —
`atlas_asimetrico.py:323` llama a `cargar_dias_de_estudio` y no hay ningún
`glob`/`listdir` que elija días — y la materialidad medida fue **0,00%**.

Pero el mecanismo sigue vivo: **el atlas sellado es un artefacto congelado y el
censo se regenera**. Cada regeneración puede reclasificar días, y hoy nada lo
grita. Ya pasó tres veces (`2025-11-19`, `2025-12-15`, `2025-10-31`), y las tres
se descubrieron por arqueología manual, meses después.

Este test convierte esa arqueología en ruido detectable: la discrepancia
permitida es una **lista declarada**. Cualquier diferencia nueva rompe la suite.

## Qué NO hace

No re-emite el atlas ni lo valida. No mira outcomes. Compara dos listas de
fechas y nada más.
"""
from __future__ import annotations

import json
import os

import pytest

from edgelab.research.universo_estudio import cargar_dias_de_estudio

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ATLAS = os.path.join(REPO, "runs", "atlas_pnk", "atlas_asimetrico.json")
MANIFIESTO = os.path.join(REPO, "runs", "censo", "manifiesto_universo.json")

# DISCREPANCIA DECLARADA — fechas que el atlas sellado consumió y que el censo
# vigente ya no entrega. Cada una con su causa. Agregar una entrada acá es una
# decisión consciente que queda en el diff; que aparezca una fecha NUEVA sin
# declarar es exactamente lo que este test tiene que atrapar.
DISCREPANCIA_DECLARADA = set()
# VACIA desde 2026-08-06. Las tres entradas que habia se RESOLVIERON al pasar el
# manifiesto del universo del 2026-07-28 (252 dias) al del 2026-08-04 (256): las
# tres fechas volvieron a estar en el censo, asi que ya no discrepan. Este mismo
# test lo exigio -"una entrada obsoleta es tan peligrosa como una faltante:
# enmascara la proxima discrepancia real en esa misma fecha"-.
#
# Lo que decian, para que quede el rastro y no haya que reconstruirlo:
#
#   2025-10-31  censo.json la marcaba DEFECTUOSO: TIPO_DE_DIA_IMPOSIBLE
#               (COMPLETO con dow=4), COBERTURA_HORARIA_INSUFICIENTE (17 h < 20),
#               CIERRE_SEMANAL_TARDIO (23:37 > 16:00). Materialidad 0,00%.
#   2025-11-19  presentes en manifiesto_PREVIO_2026-07-27.json y ausentes del
#   2025-12-15  vigente entonces: el censo se regenero el 2026-07-28T00:47Z,
#               5 h 16 min DESPUES de que corriera el atlas (2026-07-27T19:31Z).
#
# Agregar una entrada aca sigue siendo una decision consciente que queda en el
# diff; que aparezca una fecha NUEVA sin declarar es lo que el test debe atrapar.

TIPOS = ["COMPLETO", "CIERRE_SEMANAL"]


def _fechas_atlas():
    if not os.path.exists(ATLAS):
        pytest.skip("sin atlas sellado en este entorno")
    with open(ATLAS, encoding="utf-8") as fh:
        a = json.load(fh)
    pdt = a["por_dia_tasas"]
    return set(pdt[sorted(pdt)[0]])


def _fechas_censo():
    if not os.path.exists(MANIFIESTO):
        pytest.skip("sin censo generado en este entorno")
    dias, _ = cargar_dias_de_estudio(MANIFIESTO, tipos_de_dia=TIPOS,
                                     caller="test_atlas_vs_censo")
    return {d["fecha"] for d in dias}


def test_el_atlas_no_consume_fechas_que_el_censo_no_declara():
    """Fechas EN el atlas y NO en el censo vigente: sólo las declaradas."""
    huerfanas = _fechas_atlas() - _fechas_censo()
    nuevas = huerfanas - DISCREPANCIA_DECLARADA
    assert not nuevas, (
        "el atlas sellado consume %d fecha(s) que el censo vigente no entrega y "
        "que NO están declaradas en DISCREPANCIA_DECLARADA: %s. Antes de "
        "agregarlas a la lista hay que averiguar por qué el censo las descarta "
        "(¿DEFECTUOSO? ¿fuera de tipo_de_dia? ¿regeneración posterior?) y medir "
        "la materialidad sobre los resultados que descienden del atlas."
        % (len(nuevas), sorted(nuevas)))


def test_la_discrepancia_declarada_no_quedo_obsoleta():
    """Si una fecha declarada dejó de discrepar, la lista miente.

    Una entrada obsoleta es tan peligrosa como una faltante: enmascara la
    próxima discrepancia real en esa misma fecha."""
    huerfanas = _fechas_atlas() - _fechas_censo()
    obsoletas = DISCREPANCIA_DECLARADA - huerfanas
    assert not obsoletas, (
        "estas fechas están en DISCREPANCIA_DECLARADA pero ya NO discrepan: %s. "
        "Sacarlas de la lista." % sorted(obsoletas))


def test_ninguna_fecha_del_atlas_toca_el_holdout():
    """Control independiente del firewall sobre el artefacto congelado.

    La puerta protege lo que se carga HOY; esto verifica lo que quedó grabado
    en el atlas, que es de donde salen todos los números del MDE."""
    del_holdout = {f for f in _fechas_atlas() if f >= "2026-07-01"}
    assert not del_holdout, (
        "el atlas sellado contiene %d fecha(s) del holdout: %s"
        % (len(del_holdout), sorted(del_holdout)))


def test_ninguna_fecha_del_atlas_cae_en_la_cuarentena_inc005():
    """La cuarentena 2026-07-01 → 2026-07-24 es de PROCEDENCIA, no de sello."""
    quemadas = {f for f in _fechas_atlas() if "2026-07-01" <= f <= "2026-07-24"}
    assert not quemadas, (
        "el atlas sellado contiene fechas en cuarentena INC-005: %s" % sorted(quemadas))

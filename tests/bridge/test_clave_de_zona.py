# -*- coding: utf-8 -*-
"""La clave de zona estable, y por qué va calificada al evento de creación.

## Qué se prueba

El apareo Python↔NT8 estaba subdeterminado (matcher voraz por cercanía de
`created_ms` + geometría). La clave decidida es

    (bar_close_time del ZONE_CREATED, lower_tick, upper_tick)

y los tres campos ya se emiten hoy en ambos lados, con el mismo formato
`yyyy-MM-ddTHH:mm:ss.fff`. Lo que NO estaba escrito era la **calificación al
evento de creación**, y sin ella la clave no es una clave: los eventos de ciclo
de vida (`ZONE_TOUCHED`, `ZONE_INVALIDATED`, `ZONE_EXPIRED`) reemiten la
geometría de la zona con el `bar_close_time` de la barra **en curso**, no el de
su creación. Dos zonas distintas tocadas en la misma barra a la misma altura
colisionan.

Estos tests miden esa diferencia sobre el oráculo real en vez de afirmarla.

## Por qué no hace falta un ordinal

Ambos kernels ordenan las celdas anómalas por tick ascendente y las agrupan en
corridas contiguas (`avolcellpoi2.py::create_zones` y
`aVolCellPOI2.cs::CreateZones`, mismo algoritmo). Los grupos de una barra son
por construcción intervalos de tick **disjuntos y crecientes**, así que
`(lower_tick, upper_tick)` ya es única dentro de la barra. El cuarto componente
que se había conjeturado (ordinal dentro de la barra) es redundante — y este
test lo verifica contra datos, no contra el argumento.

Salvedad declarada: eso vale mientras `bar_close_time` sea único por barra, o
sea para bar_specs de TIEMPO. `aVolCellPOI2` corre en `time:1`
(`tools/correr_gates.py:66`). Para barras de TICK dos barras pueden cerrar en el
mismo milisegundo y ahí sí haría falta el ordinal.
"""
from __future__ import annotations

import collections
import csv
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORACULO = os.path.join(REPO, "oracles", "aVolCellPOI2_6E_0926_v21.csv")

EVENTOS_DE_ZONA = ("ZONE_CREATED", "ZONE_TOUCHED", "ZONE_INVALIDATED", "ZONE_EXPIRED")


def _filas():
    if not os.path.exists(ORACULO):
        pytest.skip("sin el oráculo aVolCellPOI2 v2.1 en este entorno")
    with open(ORACULO, encoding="utf-8") as fh:
        fh.readline()                     # línea `# meta,...`
        return list(csv.DictReader(fh))


def _clave(r):
    return (r["bar_close_time"], r["lower_tick"], r["upper_tick"])


def test_la_clave_es_unica_sobre_zone_created():
    """La condición que hace que la clave sea una clave."""
    filas = [r for r in _filas() if r["event_type"] == "ZONE_CREATED"]
    assert filas, "el oráculo no tiene ZONE_CREATED: no prueba nada"
    claves = [_clave(r) for r in filas]
    dups = [k for k, c in collections.Counter(claves).items() if c > 1]
    assert not dups, (
        "la clave (bar_close_time, lower_tick, upper_tick) colisiona en %d casos "
        "sobre ZONE_CREATED: %s" % (len(dups), dups[:5]))


def test_sin_calificar_al_evento_de_creacion_la_clave_colisiona():
    """El agujero de §108.H punto 1, medido.

    Si este test dejara de ver colisiones, la calificación a ZONE_CREATED
    habría dejado de ser necesaria y habría que revisar por qué — no es un
    test que "debería" pasar a verde con el tiempo."""
    filas = [r for r in _filas() if r["event_type"] in EVENTOS_DE_ZONA]
    claves = [_clave(r) for r in filas]
    colisiones = len(claves) - len(set(claves))
    assert colisiones > 0, (
        "sobre TODOS los eventos de zona la clave no colisionó; revisar, porque "
        "el contrato califica a ZONE_CREATED justamente porque acá colisiona")


def test_el_ordinal_dentro_de_la_barra_es_redundante():
    """Dos zonas creadas en la misma barra nunca comparten `lower_tick`.

    Es la consecuencia observable de que los grupos sean intervalos disjuntos
    y ordenados. Si esto fallara, el ordinal dejaría de ser redundante y la
    clave necesitaría un cuarto componente."""
    filas = [r for r in _filas() if r["event_type"] == "ZONE_CREATED"]
    por_barra = collections.defaultdict(list)
    for r in filas:
        por_barra[r["bar_close_time"]].append(int(r["lower_tick"]))
    multiples = {b: v for b, v in por_barra.items() if len(v) > 1}
    assert multiples, "ninguna barra creó 2+ zonas: el test no probaría nada"
    for barra, lowers in multiples.items():
        assert len(lowers) == len(set(lowers)), (
            "la barra %s creó dos zonas con el mismo lower_tick: %s" % (barra, lowers))


def test_los_tres_campos_de_la_clave_existen_en_el_oraculo_nt8():
    """La clave no exige emisión nueva: los tres campos ya se escriben."""
    filas = _filas()
    for campo in ("bar_close_time", "lower_tick", "upper_tick"):
        assert campo in filas[0], "el oráculo NT8 no emite %r" % campo
    # y el formato con milisegundos, que es lo que la hace comparable 1:1
    assert filas[0]["bar_close_time"].count(":") == 2
    assert "." in filas[0]["bar_close_time"], (
        "bar_close_time sin milisegundos: NT8 emite .fff y Python también "
        "(common.py::ts_str los concatena); si se pierden, la clave deja de "
        "ser comparable en bar_specs de tick")

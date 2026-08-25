"""Paridad de parametros FUERA de su valor default.

Motivo: Puerta 0 se firmo probando cada rama en su valor por defecto, y
MinExportVolume resulto estar leido-y-descartado en Python mientras el .cs SI lo
usaba (linea 561). Al default 1.0 el filtro es inerte —ningun trap tiene volumen
menor que 1— asi que las dos implementaciones coincidian por casualidad.

Estos tests recorren el espacio en el punto donde el defecto ES visible.
"""
from __future__ import annotations

import inspect
import re

import numpy as np
import pytest

from edgelab.bridge.indicators import bigtrap2absorption as M
from edgelab.bridge.indicators.bigtrap2absorption import DEFAULTS, run
from edgelab.bridge.ticks import make_synthetic


def _ticks():
    return make_synthetic(n_sessions=2, ticks_per_session=30000, seed=19)


def _zonas(**over):
    p = dict(DEFAULTS); p.update(over)
    return len(run(_ticks(), params=p)["zones"])


# ---------- el defecto concreto ----------

def test_min_export_volume_filtra_y_no_es_inerte():
    """Subirlo tiene que reducir la poblacion. Si da igual, esta desconectado."""
    base = _zonas(MinExportVolume=1.0)
    alto = _zonas(MinExportVolume=1000.0)
    assert base > 0, "el fixture no genera zonas; el test no probaria nada"
    assert alto < base, (
        f"MinExportVolume no filtra: {base} zonas con 1.0 y {alto} con 1000.0. "
        "Ese es exactamente el sintoma del parametro leido-y-descartado.")


def test_min_export_volume_es_monotono():
    z = [_zonas(MinExportVolume=v) for v in (1.0, 5.0, 20.0, 100.0)]
    assert z == sorted(z, reverse=True), f"deberia ser no creciente, dio {z}"


# ---------- el patron generico: leido y no usado ----------

def _leidos_no_usados():
    src = inspect.getsource(M)
    sosp = []
    for k in DEFAULTS:
        m = re.search(rf'(\w+)\s*=\s*[a-z]*\(?\s*p\["{k}"\]', src)
        if not m:
            continue
        var = m.group(1)
        usos = [l for l in src.splitlines()
                if re.search(rf'\b{var}\b', l) and f'p["{k}"]' not in l]
        if not usos:
            sosp.append(k)
    return sosp


def test_ningun_parametro_se_lee_y_se_descarta():
    """El patron que produjo el defecto: asignar desde params y nunca usar."""
    assert _leidos_no_usados() == [], (
        f"parametros leidos y descartados: {_leidos_no_usados()}. "
        "Cada uno es una divergencia potencial contra el .cs.")


@pytest.mark.parametrize("param,valores", [
    ("MinTrapVolume", (0.0, 50.0)),
    ("MinStackedRows", (1, 3)),
    ("MinTrapFrac", (0.1, 0.5)),
    ("ImbalanceRatio", (2.0, 6.0)),
    ("WickZonePct", (10.0, 50.0)),
])
def test_los_filtros_de_seleccion_no_son_inertes(param, valores):
    """Todo filtro declarado debe MOVER la poblacion entre sus extremos.
    Uno que no la mueve esta desconectado o mal cableado."""
    a, b = (_zonas(**{param: v}) for v in valores)
    assert a != b, f"{param}: {valores[0]} y {valores[1]} dan {a} zonas ambos"


def test_el_orden_del_filtro_coincide_con_el_cs():
    """El .cs evalua nRows==0 || vol<=0 || vol<MinExportVolume ANTES de
    MinTrapVolume. Si el orden difiere, los conteos divergen en los bordes."""
    src = inspect.getsource(M)
    i_exp = src.find("min_export_vol:")
    i_trap = src.find('best_run["vol"] < min_trap_vol')
    assert i_exp != -1 and i_trap != -1
    assert i_exp < i_trap, "MinExportVolume debe evaluarse antes que MinTrapVolume"

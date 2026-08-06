# -*- coding: utf-8 -*-
"""Manifiesto de identidad de `oracles/` — D2.

Lo que estos tests protegen no es el manifiesto: es que **no se convierta en una
copia del contenido**. Versionar un EventLog de ventana sellada es permanente —
git no olvida— así que la línea entre «identidad» y «contenido» tiene que estar
puesta en un test, no en la buena intención de quien lo edite.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools"))

MANIFIESTO = os.path.join(REPO, "docs", "oraculos_manifiesto.json")


def _m():
    if not os.path.exists(MANIFIESTO):
        pytest.skip("sin manifiesto en este entorno")
    return json.load(io.open(MANIFIESTO, encoding="utf-8"))


def test_solo_identidad_ninguna_fila_de_eventos():
    """El manifiesto declara identidad. Si alguien le agrega una clave nueva hay
    que pensarlo: cada campo extra es contenido que sale del holdout al repo."""
    d = _m()
    for nombre, f in d["archivos"].items():
        assert set(f) == {"bytes", "sha256", "meta"}, \
            "%s tiene campos fuera del contrato de identidad: %s" % (nombre, sorted(f))


def test_la_meta_es_configuracion_no_mercado():
    """`# meta` es la config del indicador. No puede traer precios ni zonas."""
    for nombre, f in _m()["archivos"].items():
        m = f.get("meta")
        if m is None:
            continue
        assert m.startswith("# meta"), nombre
        assert "ZONE_" not in m and "TRAP" not in m, \
            "%s: la meta trae tipos de evento, no deberia" % nombre


def test_el_manifiesto_es_chico_por_construccion():
    """13 KB contra 78 MB. Si creciera un orden de magnitud, alguien le metio
    contenido."""
    assert os.path.getsize(MANIFIESTO) < 200_000


def test_los_hashes_tienen_forma_de_sha256():
    for nombre, f in _m()["archivos"].items():
        assert re.fullmatch(r"[0-9a-f]{64}", f["sha256"]), nombre


def test_el_oraculo_de_P5_esta_declarado_con_el_hash_del_acta():
    """`docs/research/K1_T3c…` y el JSON de PRED-004 exigen `7d0f464f…de27`.
    Con esto, T3a se puede verificar en un clon limpio sin tener el archivo."""
    d = _m()["archivos"]
    k = "oracles/BigTrap2_time1_6E_0926_v2.csv"
    if k not in d:
        pytest.skip("el oráculo de P5 no está en esta máquina")
    assert d[k]["sha256"] == (
        "7d0f464fd4e1c90301799e2f854d7b5fb5a17d84f4f6600f082f2d4c0e17de27")
    assert "version=2.1" in (d[k]["meta"] or ""), "es el histórico, no el nuevo"


def test_hay_cuatro_BigTrap2_time1_y_solo_uno_es_el_de_P5():
    """Elegir por nombre era posible; elegir por hash es lo que lo hace
    acreditable. Este test existe porque los cuatro se llaman parecido."""
    d = _m()["archivos"]
    cand = [k for k in d if "BigTrap2_time1" in k]
    if len(cand) < 2:
        pytest.skip("no están todos en esta máquina")
    hashes = {d[k]["sha256"] for k in cand}
    assert len(hashes) == len(cand), "dos oráculos distintos con el mismo hash"


def test_oracles_sigue_ignorado_incluso_en_subdirectorios():
    """El patrón viejo era `oracles/*.csv`, que NO matchea subdirectorios: por
    eso `oracles/split/*.csv` quedó versionado sin que nadie lo decidiera."""
    g = io.open(os.path.join(REPO, ".gitignore"), encoding="utf-8").read()
    assert "oracles/**/*.csv" in g

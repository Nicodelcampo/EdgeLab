"""6J entra al catalogo del bridge: el tick_size se verifica, no se acepta.

P-44 dejo escrito que el arbol tiene parquets de 11 instrumentos y el bridge conoce 6.
6J es el primero que se agrega, y se agrega porque una medicion concreta lo necesitaba
--la sesion asiatica de 6E y YM se midio, y el yen es donde esa sesion ES la principal--
no para completar el catalogo.

El dato no viene de memoria ni de una respuesta en un chat: viene de los manifiestos que
`build_nt8_ticks` escribio al generar los parquets. Este test lo ata a esa fuente.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from edgelab.data.nt8_contract import INSTRUMENT_SPECS

REPO = pathlib.Path(__file__).resolve().parents[2]
MANIFIESTOS = sorted((REPO / "data" / "nt8" / "6J_parquet").glob("6J_*_manifest.json"))


def test_6j_esta_en_el_catalogo():
    assert "6J" in INSTRUMENT_SPECS
    spec = INSTRUMENT_SPECS["6J"]
    assert spec.symbol == "6J"
    assert spec.tick_size == 0.0000005


def test_la_aritmetica_del_contrato_cierra():
    """tick_size x multiplier = tick_value. Si uno de los tres esta mal, no cierra.

    12.500.000 JPY x 0,0000005 USD/JPY = 6,25 USD, el mismo tick_value que 6E
    (125.000 x 0,00005). Es un chequeo barato que atrapa el error tipico de agregar un
    instrumento: acertar el tick y errar el tamano del contrato."""
    for simbolo, spec in INSTRUMENT_SPECS.items():
        producto = spec.tick_size * spec.multiplier
        assert producto == pytest.approx(spec.tick_value, rel=1e-9), (
            "%s: tick_size x multiplier = %r, pero tick_value dice %r"
            % (simbolo, producto, spec.tick_value))


@pytest.mark.skipif(not MANIFIESTOS, reason="parquets de 6J no presentes en esta maquina")
def test_el_tick_size_coincide_con_los_manifiestos_de_los_parquets():
    """La fuente del numero. Si un manifiesto declara otro tick_size, el catalogo esta
    mintiendo sobre los datos que efectivamente se cargan."""
    esperado = INSTRUMENT_SPECS["6J"].tick_size
    for m in MANIFIESTOS:
        d = json.loads(m.read_text(encoding="utf-8"))
        assert d["instrument"] == "6J"
        assert d["tick_size"] == esperado, (
            "%s declara tick_size %r y el catalogo dice %r"
            % (m.name, d["tick_size"], esperado))

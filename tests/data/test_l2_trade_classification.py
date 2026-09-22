"""Clasificacion heuristica de agresor de cada trade L2 (tools/build_l2_viewer_bundle.py)."""
import importlib.util
import sys
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "build_l2", Path(__file__).resolve().parents[2] / "tools" / "build_l2_viewer_bundle.py")
B = importlib.util.module_from_spec(SPEC)
sys.modules["build_l2"] = B
SPEC.loader.exec_module(B)


def test_regla_de_cotizacion_precede_al_tick_test():
    assert B.classify_aggressor(105, 100, 105, None) == 1     # toca o cruza el ask: compra agresiva
    assert B.classify_aggressor(106, 100, 105, None) == 1     # por encima del ask tambien
    assert B.classify_aggressor(100, 100, 105, None) == -1    # toca o cruza el bid: venta agresiva
    assert B.classify_aggressor(99, 100, 105, None) == -1


def test_tick_test_de_respaldo_dentro_del_spread():
    assert B.classify_aggressor(102, 100, 105, 101) == 1      # sube respecto del trade anterior
    assert B.classify_aggressor(102, 100, 105, 103) == -1     # baja respecto del trade anterior
    assert B.classify_aggressor(102, 100, 105, 102) == 0      # igual al anterior: neutral


def test_sin_libro_ni_trade_previo_es_neutral():
    assert B.classify_aggressor(102, None, None, None) == 0


def test_sin_un_lado_del_libro_usa_el_otro_o_el_tick_test():
    assert B.classify_aggressor(105, None, 105, None) == 1    # solo hay ask: toca -> compra
    assert B.classify_aggressor(100, 100, None, None) == -1   # solo hay bid: toca -> venta
    assert B.classify_aggressor(102, None, None, 100) == 1    # ningun lado: tick test

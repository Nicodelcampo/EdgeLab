"""Clasificacion heuristica de agresor de cada trade L2 (tools/build_l2_viewer_bundle.py).

`classify_aggressor` devuelve `(direccion, metodo)`: la direccion (+1/-1/0) y CUAL de los dos mecanismos la
produjo ("quote_rule" | "tick_test" | "neutral") -- auditoria 2026-09-21, para que el % de cada metodo quede
medible (`meta.trade_classification.method_quote_rule` / `method_tick_test` / `method_neutral`) en vez de
presentarse como un unico numero sin decir de donde salio.
"""
import importlib.util
import sys
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "build_l2", Path(__file__).resolve().parents[2] / "tools" / "build_l2_viewer_bundle.py")
B = importlib.util.module_from_spec(SPEC)
sys.modules["build_l2"] = B
SPEC.loader.exec_module(B)


def test_regla_de_cotizacion_precede_al_tick_test():
    assert B.classify_aggressor(105, 100, 105, None) == (1, "quote_rule")     # toca o cruza el ask: compra agresiva
    assert B.classify_aggressor(106, 100, 105, None) == (1, "quote_rule")     # por encima del ask tambien
    assert B.classify_aggressor(100, 100, 105, None) == (-1, "quote_rule")    # toca o cruza el bid: venta agresiva
    assert B.classify_aggressor(99, 100, 105, None) == (-1, "quote_rule")


def test_tick_test_de_respaldo_dentro_del_spread():
    assert B.classify_aggressor(102, 100, 105, 101) == (1, "tick_test")      # sube respecto del trade anterior
    assert B.classify_aggressor(102, 100, 105, 103) == (-1, "tick_test")     # baja respecto del trade anterior
    assert B.classify_aggressor(102, 100, 105, 102) == (0, "neutral")        # igual al anterior: neutral


def test_sin_libro_ni_trade_previo_es_neutral():
    assert B.classify_aggressor(102, None, None, None) == (0, "neutral")


def test_sin_un_lado_del_libro_usa_el_otro_o_el_tick_test():
    assert B.classify_aggressor(105, None, 105, None) == (1, "quote_rule")    # solo hay ask: toca -> compra
    assert B.classify_aggressor(100, 100, None, None) == (-1, "quote_rule")   # solo hay bid: toca -> venta
    assert B.classify_aggressor(102, None, None, 100) == (1, "tick_test")     # ningun lado: tick test


def test_locked_market_bid_igual_ask_toca_se_resuelve_por_quote_rule():
    """Mercado "locked" (bid == ask, sin cruce): un trade AL precio locked toca ambos a la vez; la regla de
    cotizacion (precio >= ask primero) lo resuelve como compra, de forma determinista."""
    assert B.classify_aggressor(100, 100, 100, None) == (1, "quote_rule")


def test_crossed_market_bid_mayor_que_ask_no_rompe_la_clasificacion():
    """Mercado "crossed" (bid > ask: libro invalido/transitorio). La regla sigue evaluando en orden fijo
    (ask primero) sin lanzar excepcion; el llamador es responsable de degradar la certificacion del libro
    (ver ABSTAIN_CROSSED_BOOK en build_l2_viewer_bundle.build), no esta funcion."""
    assert B.classify_aggressor(101, 105, 100, None) == (1, "quote_rule")     # >= ask=100 -> compra
    assert B.classify_aggressor(99, 105, 100, None) == (-1, "quote_rule")     # <= bid=105 -> venta


def test_trade_inside_spread_sin_historial_es_neutral_no_se_inventa_lado():
    assert B.classify_aggressor(102, 100, 105, None) == (0, "neutral")


def test_secuencia_de_precios_iguales_mantiene_neutral_hasta_que_cambia():
    prev = None
    resultados = []
    for px in (100, 100, 100, 101, 101, 99):
        d, m = B.classify_aggressor(px, None, None, prev)
        resultados.append((d, m))
        prev = px
    assert resultados == [(0, "neutral"), (0, "neutral"), (0, "neutral"), (1, "tick_test"), (0, "neutral"), (-1, "tick_test")]

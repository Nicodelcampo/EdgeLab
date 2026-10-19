"""Regla de selección hot de aVolClusterPOI: `median` (v0.5) vs `topk` (robusta).

El cambio se autorizó para reducir la fragilidad medida: sobre los 22.507 bloques
de NQ 06-26 120t, el **89,60 %** tiene al menos una celda a un contrato del umbral
`mediana × multiplicador`, así que un contrato de diferencia entre NT8 y el
parquet cambia el conjunto hot. Acta: `docs/research/avolcluster_decision_rule_20260903/`.

Estos tests fijan el contrato del cambio: que `median` siga siendo el default
exacto, que `topk` preserve el tamaño del conjunto, y que sea determinista.
"""
import random

from edgelab.bridge.indicators.avolclusterpoi import (
    RESEARCH_DEFAULTS, cluster_hot_ticks, select_hot_ticks)


def _block(seed, n=90):
    rng = random.Random(seed)
    base = 100_000
    cells = {}
    for i in range(n):
        cells[base + i] = rng.randint(1, 8)
    for i in range(n // 2 - 3, n // 2 + 4):        # núcleo concentrado
        cells[base + i] = rng.randint(30, 90)
    return cells


def test_median_sigue_siendo_el_default():
    assert RESEARCH_DEFAULTS["hot_selection"] == "median"
    cells = _block(1)
    por_default = cluster_hot_ticks(cells, 2.0, 1, 2)
    explicito = cluster_hot_ticks(cells, 2.0, 1, 2, "median", 0.17)
    assert por_default == explicito, "el default no debe cambiar la detección v0.5"


def test_topk_preserva_el_tamano_del_conjunto():
    cells = _block(2)
    hot = select_hot_ticks(cells, 2.0, 2, "topk", 0.17)
    assert len(hot) == round(0.17 * len(cells))


def test_topk_es_determinista_y_rompe_empates_por_tick_ascendente():
    cells = {10: 5, 11: 5, 12: 5, 13: 5, 20: 1, 21: 1}
    hot = select_hot_ticks(cells, 2.0, 2, "topk", 0.5)
    assert hot == [10, 11, 12], "empates: gana el tick más bajo, en orden"
    revertido = select_hot_ticks(dict(reversed(list(cells.items()))), 2.0, 2, "topk", 0.5)
    assert hot == revertido, "el orden de inserción no debe influir"


def test_topk_no_depende_de_un_umbral_cruzable():
    """El caso patológico: una celda exactamente en el umbral de la mediana.

    Con `median`, un contrato la mete o la saca del conjunto. Con `topk` la
    decisión es de ranking y esa celda no está en el borde.
    """
    cells = {i: 4 for i in range(100_000, 100_060)}
    for i in range(100_020, 100_026):
        cells[i] = 40
    cells[100_030] = 8                      # justo en mediana(4) * 2
    con = select_hot_ticks(cells, 2.0, 2, "median")
    cells_ruido = dict(cells)
    cells_ruido[100_030] = 7                # un contrato menos
    sin = select_hot_ticks(cells_ruido, 2.0, 2, "median")
    assert 100_030 in con and 100_030 not in sin, "así de frágil es la regla original"

    a = select_hot_ticks(cells, 2.0, 2, "topk", 0.17)
    b = select_hot_ticks(cells_ruido, 2.0, 2, "topk", 0.17)
    assert a == b, "topk no debe moverse por ese contrato"


def test_topk_siempre_produce_conjunto_no_vacio_con_pocas_celdas():
    cells = {1: 3, 2: 9, 3: 4}
    hot = select_hot_ticks(cells, 2.0, 2, "topk", 0.17)
    assert len(hot) == 2, "K nunca baja de min_cluster_ticks"

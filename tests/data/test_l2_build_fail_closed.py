"""Integracion: `build()` de tools/build_l2_viewer_bundle.py falla cerrado ante un libro no certificable.

Construye DataFrames sinteticos minimos (mismo esquema que los parquets `l1_quotes`/`l2_depth` reales) y llama a
`build()` directamente -- sin tocar disco ni datos reales -- para probar el contrato de la seccion C de la
auditoria 2026-09-21: nivel invalido, inversion de reloj y libro cruzado sostenido ABORTAN por default, y solo
siguen si se pide `exploratory=True`.
"""
import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

SPEC = importlib.util.spec_from_file_location(
    "build_l2", Path(__file__).resolve().parents[2] / "tools" / "build_l2_viewer_bundle.py")
B = importlib.util.module_from_spec(SPEC)
sys.modules["build_l2"] = B
SPEC.loader.exec_module(B)

TICK_SIZE = 0.1
US = 1_000_000


def l2_df(rows):
    """rows: lista de (source_row, side, op, level, price_tick, size, ts_us)."""
    return pd.DataFrame(rows, columns=["source_row", "side", "operation", "level", "price_tick", "size", "ts_us"])


def l1_df(rows):
    """rows: lista de (source_row, side, price_tick, size, ts_us). price = price_tick*TICK_SIZE."""
    df = pd.DataFrame(rows, columns=["source_row", "side", "price_tick", "size", "ts_us"])
    df["price"] = df["price_tick"] * TICK_SIZE
    return df


def _build_direct(l1, l2, **kw):
    """LLama al cuerpo de `build()` pasando DataFrames ya construidos en vez de rutas de parquet, monkeypateando
    `pq.read_table` para devolverlos (build() solo los usa una vez cada uno, en orden l1 luego l2)."""
    calls = iter([l1, l2])

    class _FakeTable:
        def __init__(self, df):
            self._df = df

        def to_pandas(self):
            return self._df

    orig = B.pq.read_table
    B.pq.read_table = lambda path: _FakeTable(next(calls))
    try:
        return B.build(Path("l1"), Path("l2"), 1, TICK_SIZE, **kw)
    finally:
        B.pq.read_table = orig


def test_nivel_invalido_aborta_por_default_y_marca_el_source_row():
    l2 = l2_df([
        (0, B.BID, 0, 0, 1000, 5, 0),
        (1, B.BID, 1, 3, 1000, 9, US),      # CHANGE en level=3 sin que exista: invalido (libro tiene 1 nivel)
    ])
    l1 = l1_df([])
    with pytest.raises(B.BookAbstain) as exc:
        _build_direct(l1, l2)
    assert exc.value.status == B.ABSTAIN_INVALID_LEVEL
    assert exc.value.row == 1


def test_inversion_de_reloj_aborta_por_default():
    l2 = l2_df([
        (0, B.BID, 0, 0, 1000, 5, 5 * US),
        (1, B.BID, 0, 1, 999, 5, 4 * US),   # ts_us RETROCEDE respecto del evento anterior
    ])
    l1 = l1_df([])
    with pytest.raises(B.BookAbstain) as exc:
        _build_direct(l1, l2)
    assert exc.value.status == B.ABSTAIN_CLOCK_INVERSION


def test_libro_cruzado_sostenido_aborta_por_default():
    """Todas las filas dejan bid >= ask (cruzado) de punta a punta: por encima del umbral de tolerancia."""
    rows = []
    for i in range(0, 20, 2):
        rows.append((i, B.ASK, 0 if i == 0 else 1, 0, 1000, 5, i * US))
        rows.append((i + 1, B.BID, 0 if i == 0 else 1, 0, 1005, 5, (i + 1) * US))   # bid(1005) > ask(1000): cruzado
    l2 = l2_df(rows)
    l1 = l1_df([])
    with pytest.raises(B.BookAbstain) as exc:
        _build_direct(l1, l2)
    assert exc.value.status == B.ABSTAIN_CROSSED_BOOK


def test_modo_exploratorio_no_aborta_y_marca_el_bundle():
    l2 = l2_df([
        (0, B.BID, 0, 0, 1000, 5, 0),
        (1, B.BID, 1, 3, 1000, 9, US),      # mismo nivel invalido que el primer test
        (2, B.BID, 0, 1, 999, 4, 2 * US),   # sigue leyendo despues del evento descartado
    ])
    l1 = l1_df([])
    bar, l2b, trades, val, trclass, manip, info = _build_direct(l1, l2, exploratory=True)
    assert val["book_status"] == B.ABSTAIN_INVALID_LEVEL
    assert val["exploratory_mode"] is True
    assert val["invalid_change_count"] == 1
    assert val["abstain_source_row"] == 1


def test_sesion_incompleta_sin_trades_no_rompe_y_da_book_status_pass():
    l2 = l2_df([(0, B.ASK, 0, 0, 1000, 5, 0), (1, B.BID, 0, 0, 995, 5, US)])
    l1 = l1_df([])   # sin cotizaciones ni trades: sesion "incompleta" pero valida
    bar, l2b, trades, val, trclass, manip, info = _build_direct(l1, l2)
    assert val["book_status"] == B.PASS
    assert info["trades"] == 0
    assert trades["t"] == []                     # sin trades, sin celdas de burbujas -- no se inventa actividad


def test_microsegundos_dentro_del_mismo_segundo_cambian_el_resultado_del_detector():
    """Regresion directa del hallazgo de la auditoria: truncar a segundos antes de alimentar los detectores perdia
    el orden/la distancia real entre eventos del mismo segundo. Dos secuencias identicas salvo por la posicion
    submicrosegundo del trade dentro de la ventana de consumo deben poder dar resultados distintos."""
    def candidatos(consume_delta_us):
        """El trade ocurre en ts_us=0; el evento de consumo ocurre `consume_delta_us` despues."""
        l2 = l2_df([
            (0, B.BID, 0, 0, 1000, 100, 0),
            (2, B.BID, 1, 0, 1000, 10, consume_delta_us),        # consumo, a `consume_delta_us` del trade
            (3, B.BID, 1, 0, 1000, 95, consume_delta_us + 1),    # relleno
        ])
        l1 = l1_df([(1, B.LAST_SIDE, 1000, 90, 0)])   # trade en ts_us=0, source_row=1: entre el evento 0 y el 2
        _, _, _, _, _, manip, _ = _build_direct(l1, l2, iceberg_kwargs=dict(
            min_refills=1, trade_window_us=1, refill_window_us=10, min_avg_size={}))
        return len(manip["icebergs"])
    # con ventana de consumo de 1us: si el evento de consumo cae DENTRO de esa ventana (1us despues del trade)
    # cuenta; el mismo consumo un microsegundo mas tarde (fuera de la ventana de 1us) no debe contar -- la
    # diferencia entre ambos casos es de UN microsegundo, invisible si el tiempo se trunca a segundos.
    assert candidatos(1) == 1
    assert candidatos(2) == 0

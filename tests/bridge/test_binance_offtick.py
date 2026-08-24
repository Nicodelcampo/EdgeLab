"""Precios fuera de la grilla de tick: abortan por default, se excluyen sólo si se declara."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from decimal import Decimal

from edgelab.crypto.binance_usdm import offtick_mask


def test_offtick_mask_marca_solo_lo_desalineado():
    v = np.array([100.0, 100.1, 100.15, 100.2], dtype=np.float64)
    m = offtick_mask(v, Decimal("0.10"))
    assert m.tolist() == [False, False, True, False]


def test_offtick_mask_no_aborta():
    """A diferencia de _prices_to_ticks, marca en vez de levantar."""
    v = np.array([1.005], dtype=np.float64)
    assert offtick_mask(v, Decimal("0.01")).tolist() == [True]


def test_offtick_mask_tolera_ruido_de_punto_flotante():
    v = np.array([70344.8, 69856.9], dtype=np.float64)
    assert not offtick_mask(v, Decimal("0.10")).any()


@pytest.mark.parametrize("tick,precio,esperado", [
    ("0.10", 70344.83, True),
    ("0.01", 70344.83, False),
    ("0.10", 70344.80, False),
])
def test_offtick_depende_del_tick_declarado(tick, precio, esperado):
    """El mismo precio esta dentro o fuera segun el tick_size: por eso el tick
    es argumento obligatorio y no se infiere del dato."""
    assert bool(offtick_mask(np.array([precio]), Decimal(tick))[0]) is esperado


def test_modo_diagnostico_excluye_cuenta_y_marca(tmp_path):
    """Con el flag: no aborta, pero deja rastro imborrable en el reporte."""
    from tests.bridge.test_binance_usdm import _write_pair, _contract
    from edgelab.crypto.binance_usdm import load_binance_usdm_pair

    tp, bp = _write_pair(tmp_path)
    trades = pd.read_csv(tp, header=None)
    trades.iloc[0, 1] = 100.15
    trades.to_csv(tp, index=False, header=False)

    out = load_binance_usdm_pair(tp, bp, _contract(), allow_offtick_prices=True)
    assert out.report.n_offtick_prices_excluded == 1
    assert out.report.offtick_exclusion_invoked is True
    assert out.report.offtick_price_sample[0]["price"] == pytest.approx(100.15)
    assert out.report.outcomes_opened is False


def test_sin_offtick_el_flag_no_marca_nada(tmp_path):
    """El flag encendido sobre datos limpios no debe marcar la corrida."""
    from tests.bridge.test_binance_usdm import _write_pair, _contract
    from edgelab.crypto.binance_usdm import load_binance_usdm_pair

    tp, bp = _write_pair(tmp_path)
    out = load_binance_usdm_pair(tp, bp, _contract(), allow_offtick_prices=True)
    assert out.report.n_offtick_prices_excluded == 0
    assert out.report.offtick_exclusion_invoked is False


# ---------- precedencia de estado (auditoria 2026-08-24, punto 1) ----------

def test_exclusion_offtick_nunca_emite_pilot_accepted(tmp_path):
    from tests.bridge.test_binance_usdm import _write_pair, _contract
    from edgelab.crypto.binance_usdm import load_binance_usdm_pair
    tp, bp = _write_pair(tmp_path, trade_ids=(10, 12))   # ademas fuerza un gap
    trades = pd.read_csv(tp, header=None)
    trades.iloc[0, 1] = 100.15
    trades.to_csv(tp, index=False, header=False)
    out = load_binance_usdm_pair(tp, bp, _contract(), allow_offtick_prices=True)
    assert out.report.status == "DIAGNOSTIC_OFFTICK_EXCLUSION"
    assert not out.report.status.startswith("PILOT_ACCEPTED")
    assert out.report.promotion_eligible is False


def test_corrida_limpia_sigue_siendo_promocionable(tmp_path):
    from tests.bridge.test_binance_usdm import _write_pair, _contract
    from edgelab.crypto.binance_usdm import load_binance_usdm_pair
    tp, bp = _write_pair(tmp_path)
    out = load_binance_usdm_pair(tp, bp, _contract(), allow_offtick_prices=True)
    assert out.report.promotion_eligible is True
    assert out.report.status.startswith("PILOT_ACCEPTED")


# ---------- gaps raw vs analisis (punto 2) ----------

def _trio(tmp_path, precio_medio):
    """3 trades contiguos + book suficiente. El fixture compartido solo hace 2."""
    B = 1711756800000
    pd.DataFrame([[10, 100.1, 0.002, 0.2002, B,     "false"],
                  [11, precio_medio, 0.003, 0.3, B + 1, "true"],
                  [12, 100.0, 0.004, 0.4, B + 2, "false"]]).to_csv(
        tmp_path / "t.csv", index=False, header=False)
    pd.DataFrame([[1, 100.0, 2.0, 100.1, 3.0, B - 1, B - 1],
                  [2, 100.1, 2.0, 100.2, 3.0, B,     B],
                  [3, 99.9,  2.0, 100.0, 3.0, B + 1, B + 1]]).to_csv(
        tmp_path / "b.csv", index=False, header=False)
    return tmp_path / "t.csv", tmp_path / "b.csv"


def test_los_gaps_creados_por_la_exclusion_se_declaran(tmp_path):
    """Excluir un trade crea un gap que NO es del venue. Hay que distinguirlo."""
    from tests.bridge.test_binance_usdm import _contract
    from edgelab.crypto.binance_usdm import load_binance_usdm_pair
    tp, bp = _trio(tmp_path, 100.15)          # el del medio queda off-tick
    out = load_binance_usdm_pair(tp, bp, _contract(), allow_offtick_prices=True)
    r = out.report
    assert r.raw_id_gap_ranges == 0, "la poblacion raw 10,11,12 es contigua"
    assert r.analysis_id_gap_ranges == 1, "al excluir el 11 se abre un hueco"
    assert r.id_gaps_created_by_exclusion == 1


def test_sin_exclusion_no_se_inventan_gaps(tmp_path):
    from tests.bridge.test_binance_usdm import _contract
    from edgelab.crypto.binance_usdm import load_binance_usdm_pair
    tp, bp = _trio(tmp_path, 100.0)           # los tres alineados
    r = load_binance_usdm_pair(tp, bp, _contract()).report
    assert r.raw_id_gap_ranges == r.analysis_id_gap_ranges == 0
    assert r.id_gaps_created_by_exclusion == 0


# ---------- book off-tick (punto 5) ----------

def test_book_todo_offtick_aborta_explicitamente(tmp_path):
    """bid Y ask fuera de grilla, pero ask > bid para no disparar el gate de cruzado."""
    from tests.bridge.test_binance_usdm import _write_pair, _contract
    from edgelab.crypto.binance_usdm import load_binance_usdm_pair
    tp, bp = _write_pair(tmp_path)
    book = pd.read_csv(bp, header=None)
    book.iloc[:, 1] = 100.05      # bid off-tick
    book.iloc[:, 3] = 100.15      # ask off-tick, sigue > bid
    book.to_csv(bp, index=False, header=False)
    with pytest.raises(ValueError, match="TODAS"):
        load_binance_usdm_pair(tp, bp, _contract(), allow_offtick_prices=True)


def test_unidad_declara_fuente_y_estado_de_exchange():
    """Los valores ya no tienen default: se pasan explicitos y quedan en el
    contrato. Este test cambio de premisa en la ronda 2 de auditoria."""
    from edgelab.crypto.binance_usdm import BinanceUsdmContract
    c = BinanceUsdmContract(symbol="BTCUSDT", tick_size="0.10", quantity_unit_base="0.001",
                            quantity_unit_status="PROVISIONAL_EXCHANGE_STEP_SIZE",
                            quantity_unit_source="exchangeInfo.LOT_SIZE.stepSize")
    assert c.quantity_unit_status == "PROVISIONAL_EXCHANGE_STEP_SIZE"
    assert c.quantity_unit_source == "exchangeInfo.LOT_SIZE.stepSize"
    assert "USER_SUPPLIED" not in c.quantity_unit_status
    assert c.to_dict()["quantity_unit_source"] == "exchangeInfo.LOT_SIZE.stepSize"


# ---------- auditoria 2026-08-24 ronda 2 ----------

def test_unidad_sin_procedencia_falla_cerrado():
    """No hay default: afirmar exchangeInfo sin que nadie lo declare seria
    inventar la fuente en el manifest."""
    from edgelab.crypto.binance_usdm import BinanceUsdmContract
    with pytest.raises(ValueError, match="quantity_unit_status"):
        BinanceUsdmContract(symbol="BTCUSDT", tick_size="0.10", quantity_unit_base="0.001")
    with pytest.raises(ValueError, match="quantity_unit_source"):
        BinanceUsdmContract(symbol="BTCUSDT", tick_size="0.10", quantity_unit_base="0.001",
                            quantity_unit_status="PROVISIONAL_EXCHANGE_STEP_SIZE")


def test_gaps_creados_se_calculan_por_poblacion_no_por_conteo_de_rangos():
    """Restar cantidades de rangos da mal cuando una exclusion PARTE un rango
    existente: 1 rango puede volverse 2 sin que falte ningun ID nuevo."""
    import numpy as np
    from edgelab.crypto.binance_usdm import _missing_id_set
    raw = np.array([10, 11, 15, 16], dtype=np.int64)      # falta 12,13,14 -> 1 rango
    assert _missing_id_set(raw) == {12, 13, 14}
    # al excluir el 15, el hueco crece pero NO aparecen rangos nuevos
    post = np.array([10, 11, 16], dtype=np.int64)
    creados = _missing_id_set(post) - _missing_id_set(raw)
    assert creados == {15}, "el creado es el ID excluido, no una diferencia de rangos"
    assert len(creados) == 1


def test_el_invariante_de_promocion_es_excepcion_no_assert():
    """python -O elimina los assert; el invariante debe sobrevivir."""
    import inspect
    from edgelab.crypto import binance_usdm as M
    src = inspect.getsource(M.load_binance_usdm_pair)
    assert "raise RuntimeError" in src
    assert "assert not (offtick_invoked" not in src


def test_las_herramientas_del_piloto_compilan():
    """Los tests no importan tools/, asi que un SyntaxError ahi pasa la suite.
    Este test cierra ese hueco: compila los entrypoints sin ejecutarlos."""
    import py_compile
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[2]
    for rel in ("tools/binance_bt2_pilot.py",):
        py_compile.compile(str(raiz / rel), doraise=True)

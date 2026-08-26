import numpy as np
import pytest

from edgelab.bridge.bars import BarSeries
from diag.tasa_senales.avolcluster_bar_type_decision import (
    block_volumes,
    autocorr_lag1,
    homoscedasticity_ratio,
    tick_candidates_from_paso0,
    label,
)


def _bars(volumes):
    n = len(volumes)
    z = np.zeros(n, dtype=np.int64)
    return BarSeries(z, z, z, z, z, z, np.asarray(volumes, dtype=np.float64), 0.10, "time", 1, z)


def test_block_volumes_agrupa_de_a_window_bars_y_descarta_parcial():
    # 25 barras de volumen 1 cada una, window=10 -> 2 bloques completos (20),
    # las ultimas 5 (bloque parcial) se descartan
    bars = _bars([1.0] * 25)
    v = block_volumes(bars, window_bars=10)
    assert v.tolist() == [10.0, 10.0]


def test_block_volumes_menos_de_un_bloque_da_vacio():
    bars = _bars([1.0] * 5)
    v = block_volumes(bars, window_bars=10)
    assert v.size == 0


def test_autocorr_lag1_serie_constante_es_none_no_nan():
    # varianza cero -> no calculable, NUNCA devolver NaN silencioso
    v = np.asarray([5.0, 5.0, 5.0, 5.0])
    assert autocorr_lag1(v) is None


def test_autocorr_lag1_serie_perfectamente_correlacionada():
    v = np.asarray([1.0, 2.0, 3.0, 4.0, 5.0])
    r = autocorr_lag1(v)
    assert r == pytest.approx(1.0, abs=1e-9)


def test_autocorr_lag1_muy_corta_es_none():
    assert autocorr_lag1(np.asarray([1.0, 2.0])) is None


def test_homoscedasticity_ratio_identica_dispersion_da_uno():
    v = np.asarray([1.0, 3.0, 1.0, 3.0, 1.0, 3.0, 1.0, 3.0, 1.0])
    r = homoscedasticity_ratio(v)
    assert r == pytest.approx(1.0, rel=1e-6)


def test_homoscedasticity_ratio_pocos_bloques_es_none():
    v = np.asarray([1.0, 2.0, 3.0])
    assert homoscedasticity_ratio(v) is None


def test_homoscedasticity_ratio_varianza_final_cero_es_none():
    v = np.asarray([1.0, 5.0, 1.0, 5.0, 1.0, 5.0, 3.0, 3.0, 3.0])
    assert homoscedasticity_ratio(v) is None


def test_label_formatea_tiempo_y_ticks_distinto():
    assert label("time", 3) == "3m"
    assert label("tick", 180) == "180t"


def test_tick_candidates_redondea_a_multiplo_de_5(tmp_path, monkeypatch):
    import json
    import diag.tasa_senales.avolcluster_bar_type_decision as mod
    paso0 = {"agregado": {"ticks_por_min_p50": 61.0}}
    p = tmp_path / "paso0.json"
    p.write_text(json.dumps(paso0), encoding="utf-8")
    monkeypatch.setattr(mod, "PASO0_PATH", p)
    cands = tick_candidates_from_paso0()
    assert cands == [60, 185, 305]  # 61,183,305 redondeados a multiplo de 5
    assert all(c % 5 == 0 for c in cands)

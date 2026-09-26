import pytest

from diag.tasa_senales.avolcluster_60t_paridad_warmup import (
    match_zones,
    _to_epoch_seconds,
)


def test_to_epoch_seconds_suma_3h_de_art_a_utc():
    # 2026-01-30T13:34:35.620 ART (UTC-3) -> 16:34:35.620 UTC
    ts = _to_epoch_seconds("2026-01-30T13:34:35.620")
    assert ts == pytest.approx(1769780075.620 + 3 * 3600, abs=0.01)


def test_match_zones_exacto_geometria_y_tiempo():
    py = [{"lower_tick": 100, "upper_tick": 120, "ts_epoch": 1000.0, "trade_date": "20260101"}]
    oracle = [{"lower_tick": 100, "upper_tick": 120, "ts_epoch": 1000.5}]
    r = match_zones(py, oracle, tol_seconds=2.0)
    assert r["n_matched"] == 1
    assert r["match_rate_vs_oracle"] == pytest.approx(1.0)
    assert r["delta_seconds_mediana"] == pytest.approx(0.5)


def test_match_zones_geometria_distinta_no_matchea():
    py = [{"lower_tick": 100, "upper_tick": 120, "ts_epoch": 1000.0, "trade_date": "20260101"}]
    oracle = [{"lower_tick": 100, "upper_tick": 121, "ts_epoch": 1000.0}]
    r = match_zones(py, oracle, tol_seconds=2.0)
    assert r["n_matched"] == 0
    assert r["n_unmatched_oracle"] == 1
    assert r["n_unmatched_python"] == 1


def test_match_zones_fuera_de_tolerancia_temporal_no_matchea():
    py = [{"lower_tick": 100, "upper_tick": 120, "ts_epoch": 1000.0, "trade_date": "20260101"}]
    oracle = [{"lower_tick": 100, "upper_tick": 120, "ts_epoch": 1005.0}]
    r = match_zones(py, oracle, tol_seconds=2.0)
    assert r["n_matched"] == 0


def test_match_zones_sin_reemplazo_no_dobla_matches():
    # dos zonas python identicas en geometria, solo una zona oraculo -- solo 1 match
    py = [{"lower_tick": 100, "upper_tick": 120, "ts_epoch": 1000.0, "trade_date": "20260101"},
          {"lower_tick": 100, "upper_tick": 120, "ts_epoch": 1000.1, "trade_date": "20260101"}]
    oracle = [{"lower_tick": 100, "upper_tick": 120, "ts_epoch": 1000.0, "trade_date": "20260101"}]
    r = match_zones(py, oracle, tol_seconds=2.0)
    assert r["n_matched"] == 1
    assert r["n_unmatched_python"] == 1


def test_match_zones_elige_el_mas_cercano_en_tiempo_entre_varios_candidatos():
    py = [{"lower_tick": 100, "upper_tick": 120, "ts_epoch": 1000.0, "trade_date": "20260101"}]
    oracle = [
        {"lower_tick": 100, "upper_tick": 120, "ts_epoch": 998.0},   # dt=2.0, borde
        {"lower_tick": 100, "upper_tick": 120, "ts_epoch": 1000.3},  # dt=0.3, mejor
    ]
    r = match_zones(py, oracle, tol_seconds=2.0)
    assert r["n_matched"] == 1
    assert r["delta_seconds_mediana"] == pytest.approx(0.3)


def test_match_zones_vacio_no_rompe():
    r = match_zones([], [], tol_seconds=2.0)
    assert r["n_matched"] == 0
    assert r["match_rate_vs_oracle"] is None

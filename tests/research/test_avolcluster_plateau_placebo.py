import numpy as np
import pytest

from edgelab.bridge.bars import build_tick_bars
from edgelab.bridge.ticks import TickSeries
from diag.tasa_senales.avolcluster_plateau_placebo import (
    block_cells_and_meta,
    permute_cells,
    zone_metrics,
    plateau_check,
)


def _ticks(prices, vols, ts_start_ns=0, step_ns=1_000_000_000):
    n = len(prices)
    ts = np.arange(ts_start_ns, ts_start_ns + n * step_ns, step_ns, dtype=np.int64)[:n]
    return TickSeries(
        ts_ns=ts, price_ticks=np.asarray(prices, dtype=np.int64),
        volume=np.asarray(vols, dtype=np.float64),
        bid_ticks=None, ask_ticks=None, sequence=np.arange(n, dtype=np.int64),
        tick_size=0.10, instrument="GC", contract="GC 04-26", source="test",
    )


def test_block_cells_agrupa_volumen_por_precio_dentro_del_bloque():
    # 20 ticks de a 1 por barra (ticks_per_bar=1), window_bars=10 -> 2 bloques.
    # Bloque 0: precios 100,101,100,101,... Bloque 1: precios 200,201,...
    prices = [100, 101] * 5 + [200, 201] * 5
    vols = [1.0] * 20
    ticks = _ticks(prices, vols)
    bars = build_tick_bars(ticks, ticks_per_bar=1, reiniciar_por_sesion=False)
    cells_by_block, close_by_block, end_by_block = block_cells_and_meta(ticks, bars, window_bars=10)
    assert set(cells_by_block.keys()) == {0, 1}
    assert cells_by_block[0] == {100: 5.0, 101: 5.0}
    assert cells_by_block[1] == {200: 5.0, 201: 5.0}
    assert len(close_by_block) == 2


def test_block_cells_descarta_bloque_parcial():
    # 25 ticks, window_bars=10, ticks_per_bar=1 -> 2 bloques completos, 5 sueltos descartados
    prices = list(range(25))
    vols = [1.0] * 25
    ticks = _ticks(prices, vols)
    bars = build_tick_bars(ticks, ticks_per_bar=1, reiniciar_por_sesion=False)
    cells_by_block, *_ = block_cells_and_meta(ticks, bars, window_bars=10)
    assert set(cells_by_block.keys()) == {0, 1}
    total_vol = sum(sum(c.values()) for c in cells_by_block.values())
    assert total_vol == 20.0  # no 25 -- el parcial se descarta


def test_block_cells_menos_de_un_bloque_da_vacio():
    ticks = _ticks([100] * 5, [1.0] * 5)
    bars = build_tick_bars(ticks, ticks_per_bar=1, reiniciar_por_sesion=False)
    cells_by_block, close_by_block, end_by_block = block_cells_and_meta(ticks, bars, window_bars=10)
    assert cells_by_block == {}
    assert close_by_block.size == 0


def test_permute_cells_preserva_ticks_activos_y_multiset_de_volumen():
    cells = {100: 5.0, 101: 12.0, 102: 3.0, 105: 20.0}
    rng = np.random.default_rng(42)
    fake = permute_cells(cells, rng)
    assert set(fake.keys()) == set(cells.keys())
    assert sorted(fake.values()) == sorted(cells.values())
    assert sum(fake.values()) == pytest.approx(sum(cells.values()))


def test_permute_cells_es_determinista_con_semilla():
    cells = {100: 5.0, 101: 12.0, 102: 3.0, 105: 20.0}
    a = permute_cells(cells, np.random.default_rng(7))
    b = permute_cells(cells, np.random.default_rng(7))
    assert a == b


def test_permute_cells_menos_de_dos_ticks_no_rompe():
    assert permute_cells({100: 5.0}, np.random.default_rng(1)) == {100: 5.0}
    assert permute_cells({}, np.random.default_rng(1)) == {}


def test_zone_metrics_espesor_y_aislamiento():
    zonas = [
        {"trade_date": "20260101", "lower_tick": 100, "upper_tick": 102, "centro_tick": 101},
        {"trade_date": "20260101", "lower_tick": 200, "upper_tick": 201, "centro_tick": 200},
        {"trade_date": "20260102", "lower_tick": 500, "upper_tick": 505, "centro_tick": 502},
    ]
    m = zone_metrics(zonas)
    assert m["n_zonas"] == 3
    # anchos: (102-100+1)=3, (201-200+1)=2, (505-500+1)=6 -> mediana 3
    assert m["espesor_mediana"] == pytest.approx(3.0)
    # aislamiento solo DENTRO de la misma sesion: 20260101 tiene 2 zonas, gap=|200-101|=99
    # 20260102 tiene 1 sola zona -> no aporta gap
    assert m["aislamiento_ticks_mediana"] == pytest.approx(99.0)


def test_zone_metrics_vacio_no_rompe():
    m = zone_metrics([])
    assert m["n_zonas"] == 0
    assert m["espesor_mediana"] is None
    assert m["aislamiento_ticks_mediana"] is None


def test_plateau_check_detecta_dentro_y_fuera_de_tolerancia():
    landscape = [
        {"_key": "60t_98p_2.0m", "_axis": "block_size",
         "metrics": {"espesor_mediana": 4.0, "frecuencia_normalizada_x100bloques": 2.0,
                     "aislamiento_ticks_mediana": 50.0}},
        {"_key": "50t_98p_2.0m", "_axis": "block_size",
         "metrics": {"espesor_mediana": 4.2, "frecuencia_normalizada_x100bloques": 2.1,
                     "aislamiento_ticks_mediana": 52.0}},  # dentro de 15%
        {"_key": "40t_98p_2.0m", "_axis": "block_size",
         "metrics": {"espesor_mediana": 8.0, "frecuencia_normalizada_x100bloques": 2.0,
                     "aislamiento_ticks_mediana": 50.0}},  # espesor duplica -> fuera
    ]
    out = plateau_check(landscape, "60t_98p_2.0m", "block_size",
                         ("espesor_mediana", "frecuencia_normalizada_x100bloques", "aislamiento_ticks_mediana"))
    assert out["50t_98p_2.0m"]["dentro_de_meseta"] is True
    assert out["40t_98p_2.0m"]["dentro_de_meseta"] is False


def test_plateau_check_ignora_ejes_distintos():
    landscape = [
        {"_key": "base", "_axis": "block_size", "metrics": {"m": 1.0}},
        {"_key": "otro_eje", "_axis": "percentile_multiplier", "metrics": {"m": 999.0}},
    ]
    out = plateau_check(landscape, "base", "block_size", ("m",))
    assert "otro_eje" not in out

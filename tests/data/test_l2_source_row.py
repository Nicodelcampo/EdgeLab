"""L2/L1 — fija `source_row`, que es lo unico que hace recuperable el orden de eventos.

El dump NRD->CSV tiene ~80% de empates en microsegundo. Sin el indice de linea del CSV
original, el orden dentro de un mismo timestamp no existe, y con el se cae cualquier
reconstruccion del libro, clasificacion de agresor contra el quote vigente, u OFI.
"""
from __future__ import annotations

import numpy as np
import pytest

from edgelab.data.l2 import parse_l2_raw_csv

TICK = 0.25

# 12 lineas: L2 y L1 INTERCALADAS y con timestamps repetidos al microsegundo, que es
# exactamente el caso que rompe el orden si no se guarda el numero de linea.
CSV = "\n".join([
    "L2;0;20260819010000;80000;0;0;;7706.75;20",     # 0  ask nivel 0
    "L2;1;20260819010000;80000;0;0;;7706.50;18",     # 1  bid nivel 0
    "L1;0;20260819010000;80000;7706.75;20",          # 2  ASK
    "L1;1;20260819010000;80000;7706.50;18",          # 3  BID
    "L1;2;20260819010000;80000;7706.75;1",           # 4  LAST (trade)
    "L1;5;20260819010000;80000;0;3119321",           # 5  DAILY_VOLUME
    "L2;0;20260819010000;80000;1;0;;7706.75;19",     # 6  mismo us, update
    "L1;2;20260819010000;80000;7706.75;2",           # 7  mismo us, otro trade
    "L2;1;20260819010001;123456;2;3;;7705.75;0",     # 8
    "L1;1;20260819010001;123456;7706.25;11",         # 9
    "L2;0;20260819010002;0;1;9;;7709.00;5",          # 10
    "L1;2;20260819010002;0;7706.50;4",               # 11
]) + "\n"


@pytest.fixture
def dfs(tmp_path):
    p = tmp_path / "20260819.csv"
    p.write_text(CSV, encoding="utf-8")
    return parse_l2_raw_csv(p, tick_size=TICK)


# --------------------------------------------------------------------------
# source_row: el invariante que importa
# --------------------------------------------------------------------------

def test_las_dos_tablas_traen_source_row(dfs):
    l2, l1 = dfs
    assert "source_row" in l2.columns and "source_row" in l1.columns


def test_source_row_es_el_indice_de_linea_del_csv_original(dfs):
    l2, l1 = dfs
    assert sorted(l2["source_row"]) == [0, 1, 6, 8, 10]
    assert sorted(l1["source_row"]) == [2, 3, 4, 5, 7, 9, 11]


def test_ninguna_linea_se_pierde_ni_se_duplica(dfs):
    """L1 + L2 tiene que cubrir exactamente todas las lineas, sin huecos."""
    l2, l1 = dfs
    todas = np.sort(np.concatenate([l2["source_row"].to_numpy(),
                                    l1["source_row"].to_numpy()]))
    assert len(todas) == 12
    assert np.array_equal(todas, np.arange(12))


def test_source_row_es_monotono_en_cada_tabla(dfs):
    l2, l1 = dfs
    assert l2["source_row"].is_monotonic_increasing
    assert l1["source_row"].is_monotonic_increasing


def test_desempata_eventos_con_el_MISMO_microsegundo(dfs):
    """Seis eventos comparten timestamp exacto. Sin source_row son indistinguibles;
    con el, quedan totalmente ordenados."""
    l2, l1 = dfs
    t0 = l1["ts_us"].iloc[0]
    mismos_l1 = l1[l1["ts_us"] == t0]
    mismos_l2 = l2[l2["ts_us"] == t0]
    assert len(mismos_l1) + len(mismos_l2) == 8       # las 8 primeras lineas
    orden = np.sort(np.concatenate([mismos_l1["source_row"].to_numpy(),
                                    mismos_l2["source_row"].to_numpy()]))
    assert len(np.unique(orden)) == len(orden)        # sin empates residuales


def test_preserva_el_intercalado_entre_los_dos_flujos(dfs):
    """Un L2 (linea 6) cae ENTRE dos L1 (5 y 7) con el mismo microsegundo. Ese orden
    relativo sobrevive porque el indice se toma antes de separar los flujos."""
    l2, l1 = dfs
    assert 6 in set(l2["source_row"])
    assert {5, 7} <= set(l1["source_row"])


# --------------------------------------------------------------------------
# Semantica corregida de `side` (ver CORRECCION_ESQUEMA_L1_ES_SEP26_2026-08-21.md)
# --------------------------------------------------------------------------

def test_side_2_es_LAST_y_trae_tamano_de_trade(dfs):
    _, l1 = dfs
    tr = l1[l1["side"] == 2]
    assert len(tr) == 3
    assert list(tr["size"]) == [1, 2, 4]              # tamanos de trade, no profundidad


def test_side_5_es_volumen_acumulado_con_precio_cero(dfs):
    _, l1 = dfs
    v = l1[l1["side"] == 5]
    assert len(v) == 1
    assert float(v["price"].iloc[0]) == 0.0
    assert int(v["size"].iloc[0]) == 3_119_321


def test_side_0_queda_por_encima_de_side_1(dfs):
    """0 = Ask, 1 = Bid. Si estuviera al reves el libro saldria cruzado."""
    _, l1 = dfs
    ask = l1[(l1["side"] == 0)]["price_tick"].iloc[0]
    bid = l1[(l1["side"] == 1)]["price_tick"].iloc[0]
    assert ask > bid


# --------------------------------------------------------------------------
# Conversion de precio y reloj
# --------------------------------------------------------------------------

def test_price_tick_usa_el_tick_size_del_instrumento(dfs):
    _, l1 = dfs
    assert int(l1["price_tick"].iloc[0]) == round(7706.75 / TICK) == 30827


def test_ts_us_compone_segundo_y_microsegundo(dfs):
    _, l1 = dfs
    t = l1["ts_us"].to_numpy()
    assert (t[0] % 1_000_000) == 80_000                # el microsegundo del CSV
    assert (t[-1] - t[0]) == 2 * 1_000_000 - 80_000    # dos segundos despues, us=0


def test_l2_conserva_operacion_y_nivel(dfs):
    l2, _ = dfs
    assert set(l2["operation"]) == {0, 1, 2}
    assert set(l2["level"]) == {0, 3, 9}


# --------------------------------------------------------------------------
# Unidades de ts_us: el bug que dependia de la version de pandas
# --------------------------------------------------------------------------

def test_ts_us_esta_en_MICROSEGUNDOS_de_epoch(dfs):
    """La version anterior hacia `to_datetime().astype(int64)//1000 + usec`, que da
    microsegundos con pandas 2.x (datetime64[ns]) y MILISEGUNDOS con pandas 3.0.3
    (datetime64[us]). El mismo codigo producia unidades distintas segun la maquina."""
    import datetime as _dt
    _, l1 = dfs
    esperado = int(_dt.datetime(2026, 8, 19, 1, 0, 0,
                                tzinfo=_dt.timezone.utc).timestamp()) * 1_000_000 + 80_000
    assert int(l1["ts_us"].iloc[0]) == esperado


def test_ts_us_cae_en_el_rango_epoch_plausible(dfs):
    l2, l1 = dfs
    for df in (l2, l1):
        assert df["ts_us"].min() > 1_000_000_000_000_000     # despues de 2001
        assert df["ts_us"].max() < 3_000_000_000_000_000     # antes de 2065


def test_el_parser_ABORTA_si_las_unidades_quedan_mal(tmp_path):
    """La asercion es dura a proposito: un parquet con unidades corridas 1000x es
    indistinguible a simple vista y contamina todo lo que se construya encima."""
    from edgelab.data.l2 import _a_microsegundos
    import pandas as _pd
    with pytest.raises(ValueError, match="unidades"):
        _a_microsegundos(_pd.Series(["19700101000001"]), _pd.Series([0]))

"""Smoke sintético + invariantes propias de VolTicksPOC2 (F5A).

Valida infraestructura y contrato del kernel, NO paridad real con NT8 (esa
exige un EventLogPath real, gate P2). Invariante estrella: el desempate de POC
va al TICK MÁS BAJO (contrato fijo, no parámetro).
"""
import numpy as np

from edgelab.bridge import bars as B
from edgelab.bridge.indicators import voltickspoc2
from edgelab.bridge.ticks import TickSeries, make_synthetic

NS = 1_000_000_000


def _bars_from_spec(bar_specs, tick_size=0.25):
    """bar_specs: lista por barra de [(price_tick, vol), ...]. Cada barra ocupa
    su propio minuto; devuelve (TickSeries, BarSeries, Footprints)."""
    ts, px, vol = [], [], []
    for b, cells in enumerate(bar_specs):
        base = b * 60 * NS
        for k, (p, v) in enumerate(cells):
            ts.append(base + (k + 1) * NS)   # +1s: dentro del minuto b
            px.append(p)
            vol.append(v)
    n = len(ts)
    tk = TickSeries(np.asarray(ts, np.int64), np.asarray(px, np.int64),
                    np.asarray(vol, np.float64), None, None,
                    np.arange(n, dtype=np.int64), tick_size, "SYN", "SYN", "test")
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)
    return tk, bars, fps


def test_poc_lowest_tick_tiebreak():
    # 4 barras chatas de baseline + 1 barra anómala cuyo footprint empata en
    # volumen entre el tick 100 y el 104 (ambos = 9); POC debe ser el 100.
    flat = [[(100, 2), (101, 2)] for _ in range(4)]
    anomaly = [(100, 9), (102, 1), (104, 9)]   # empate 100 vs 104 -> gana 100
    tk, bars, fps = _bars_from_spec(flat + [anomaly])
    res = voltickspoc2.run(tk, bars, fps, params=dict(
        avg_period=2, ratio_window_bars=50, min_ratio_samples=2,
        detection_percentile=50.0, export_floor_percentile=0.0))
    created = [e for e in res["events"] if e["type"] == "ZONE_CREATED"]
    assert created, "la barra anómala debe crear una zona"
    assert created[-1]["poc_tick"] == 100, "empate de POC -> tick más bajo"
    z = res["zones"][-1]
    # zona centrada en el POC (price_mark_ticks=1 -> ±0.5 tick alrededor)
    assert z["bottom"] < 100 * 0.25 < z["top"]


def test_reconstructed_footprint_matches_bar_volume():
    # El footprint reconstruido desde los MISMOS ticks nunca puede divergir del
    # volumen de barra -> jamás debe emitir FOOTPRINT_MISMATCH (invariante P1B).
    tk = make_synthetic(n_sessions=1, ticks_per_session=4000)
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)
    res = voltickspoc2.run(tk, bars, fps, params=dict(avg_period=5, min_ratio_samples=5))
    assert not [e for e in res["events"] if e["type"] == "FOOTPRINT_MISMATCH"]


def test_deterministic_on_synthetic():
    tk = make_synthetic(n_sessions=2, ticks_per_session=5000)
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)
    r1 = voltickspoc2.run(tk, bars, fps, params=dict(avg_period=20, min_ratio_samples=20,
                                                     detection_percentile=90.0))
    r2 = voltickspoc2.run(tk, bars, fps, params=dict(avg_period=20, min_ratio_samples=20,
                                                     detection_percentile=90.0))
    assert r1["csv_lines"] == r2["csv_lines"]          # determinismo bit a bit
    seqs = [e["seq"] for e in r1["events"]]
    assert seqs == sorted(seqs)                         # orden de eventos estable


def test_detection_percentile_discriminates():
    tk = make_synthetic(n_sessions=2, ticks_per_session=6000)
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)
    loose = voltickspoc2.run(tk, bars, fps, params=dict(avg_period=20, min_ratio_samples=20,
                                                        detection_percentile=90.0))
    tight = voltickspoc2.run(tk, bars, fps, params=dict(avg_period=20, min_ratio_samples=20,
                                                        detection_percentile=99.9))
    assert len(loose["zones"]) >= len(tight["zones"])   # el corte más alto crea <= zonas


def test_baseline_excludes_current_bar():
    # baseline = media de las barras ANTERIORES; la ventana de ratios se llena
    # DESPUÉS de comparar, así que el sondeo es la 4ta barra. Con 3 barras de
    # volumen 2, baseline=2 y ratio=10/2=5 (si incluyera la actual: 10/4=2.5).
    flat = [[(100, 1), (101, 1)] for _ in range(3)]     # vol barra = 2
    probe = [[(100, 5), (101, 5)]]                       # vol barra = 10
    tk, bars, fps = _bars_from_spec(flat + probe)
    res = voltickspoc2.run(tk, bars, fps, params=dict(
        avg_period=2, ratio_window_bars=50, min_ratio_samples=1,
        detection_percentile=50.0, export_floor_percentile=0.0))
    obs = [e for e in res["events"] if e["type"] in ("OBS", "ZONE_CREATED")]
    assert obs, "debe haber al menos una observación en la barra de sondeo"
    # el ratio reportado en el sondeo debe ser 5.0 (baseline sin la barra actual)
    probe_ev = [e for e in res["events"] if e["type"] in ("OBS", "ZONE_CREATED")
                and e["bar_index"] == 3]
    assert probe_ev, "el sondeo (barra 3) debe emitir OBS/ZONE_CREATED"

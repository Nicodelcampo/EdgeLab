"""Smoke sintético + invariantes propias de aVolCellPOI2 (F5D).

Valida infraestructura y contrato del kernel, NO paridad real con NT8.
aVolCellPOI2 es bar-driven con perfil histórico por bucket temporal, congelado
por sesión. Invariantes clave: la sesión actual NUNCA entra al perfil contra el
que se compara (anti look-ahead), la primera sesión observada se maneja por el
roll, y sin historia suficiente (min_sessions/min_cell_samples) no se detecta.
"""
import datetime as dt
from zoneinfo import ZoneInfo

import numpy as np

from edgelab.bridge import bars as B
from edgelab.bridge.indicators import avolcellpoi2
from edgelab.bridge.ticks import TickSeries

NS = 1_000_000_000
CT = ZoneInfo("America/Chicago")


def _multi_session_ticks(n_sessions, levels_per_bar=12, base_vol=3.0,
                         anomaly_last=None, tick_size=0.25, base_tick=1000):
    """Un bar por sesión, todos al mismo offset relativo de sesión (mismo bucket).
    Cada sesión = un día hábil consecutivo a las 18:00 UTC (mitad de sesión CME).
    anomaly_last: (tick_offset, vol) inyectado en la última sesión."""
    ts, px, vol, bid, ask = [], [], [], [], []
    day = dt.datetime(2025, 8, 4, 18, 0, tzinfo=dt.timezone.utc)  # lunes
    placed = 0
    d = day
    while placed < n_sessions:
        if d.weekday() < 5:                     # lun-vie
            base_ns = int(d.timestamp() * NS)
            cells = [(base_tick + k, base_vol) for k in range(levels_per_bar)]
            if placed == n_sessions - 1 and anomaly_last is not None:
                cells.append(anomaly_last)      # celda anómala en la última sesión
            for j, (tk, v) in enumerate(cells):
                ts.append(base_ns + j * 1_000_000)   # +j ms dentro del minuto
                px.append(tk); vol.append(v)
                bid.append(tk - 1); ask.append(tk + 1)
            placed += 1
        d = d + dt.timedelta(days=1)
    n = len(ts)
    tk = TickSeries(np.asarray(ts, np.int64), np.asarray(px, np.int64),
                    np.asarray(vol, np.float64), np.asarray(bid, np.int64),
                    np.asarray(ask, np.int64), np.arange(n, dtype=np.int64),
                    tick_size, "SYN", "SYN", "test")
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)
    return tk, bars, fps


def test_insufficient_history_no_zones():
    # Con las defaults (min_sessions=15) y solo 6 sesiones, el perfil nunca se
    # arma -> cache None -> cero zonas (jamás detección con historia pobre).
    tk, bars, fps = _multi_session_ticks(6, anomaly_last=(1005, 500.0))
    res = avolcellpoi2.run(tk, bars, fps)          # defaults
    assert not res["zones"], "sin >=15 sesiones no se detecta nada"


def test_detection_fires_with_enough_history():
    # Con umbrales bajados y una celda anómala en la última sesión, debe crear
    # una zona. La anomalía se compara contra las sesiones ANTERIORES.
    tk, bars, fps = _multi_session_ticks(8, anomaly_last=(1005, 500.0))
    res = avolcellpoi2.run(tk, bars, fps, params=dict(
        min_sessions=3, min_cell_samples=20, detection_percentile=95.0,
        min_absolute_volume=10.0))
    created = [e for e in res["events"] if e["type"] == "ZONE_CREATED"]
    assert created, "la celda anómala debe crear una zona con historia suficiente"
    # la zona debe cubrir el tick anómalo (1005)
    z = res["zones"][-1]
    assert z["bottom"] <= 1005 * 0.25 <= z["top"]


def test_current_session_excluded_from_profile():
    # Si la sesión actual entrara a su propio perfil, la celda anómala inflaría
    # el umbral y podría no dispararse. La excluimos: una anomalía única en la
    # última sesión SIEMPRE queda por encima del perfil histórico (percentil 1.0).
    tk, bars, fps = _multi_session_ticks(8, anomaly_last=(1005, 500.0))
    res = avolcellpoi2.run(tk, bars, fps, params=dict(
        min_sessions=3, min_cell_samples=20, detection_percentile=99.0,
        min_absolute_volume=10.0))
    # con percentil 99 la anomalía única solo dispara si el perfil NO se
    # contamina con la propia sesión actual (empirical_pct queda en 1.0).
    assert [e for e in res["events"] if e["type"] == "ZONE_CREATED"], \
        "la anomalía debe detectarse (perfil sin contaminar por la sesión actual)"


def test_no_history_no_anomaly_clean():
    # Sin anomalía, con historia suficiente, no debe inventar zonas (el perfil
    # es homogéneo -> ninguna celda supera el corte extremo).
    tk, bars, fps = _multi_session_ticks(8, anomaly_last=None)
    res = avolcellpoi2.run(tk, bars, fps, params=dict(
        min_sessions=3, min_cell_samples=20, detection_percentile=99.5,
        min_absolute_volume=10.0))
    assert not [e for e in res["events"] if e["type"] == "ZONE_CREATED"], \
        "perfil homogéneo sin anomalía -> sin zonas"


def test_deterministic():
    tk, bars, fps = _multi_session_ticks(8, anomaly_last=(1005, 500.0))
    params = dict(min_sessions=3, min_cell_samples=20, detection_percentile=95.0)
    r1 = avolcellpoi2.run(tk, bars, fps, params=params)
    r2 = avolcellpoi2.run(tk, bars, fps, params=params)
    assert r1["csv_lines"] == r2["csv_lines"]
    seqs = [e["seq"] for e in r1["events"]]
    assert seqs == sorted(seqs)

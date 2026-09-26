"""Smoke sintético + invariantes propias de HFTZones2 (F5C).

Valida infraestructura y contrato del kernel, NO paridad real con NT8. HFTZones2
es tick-driven con calibración adaptativa por sesión (congelada intra-sesión).
Invariantes clave: CALIBRATION_PENDING en la primera sesión sin calibración,
sampler determinista por stride, FIX#1 (dur_sec piso 1 ms).
"""
import numpy as np

from edgelab.bridge import bars as B
from edgelab.bridge import sessions
from edgelab.bridge.indicators import hftzones2
from edgelab.bridge.indicators.hftzones2 import _Sampler
from edgelab.bridge.ticks import make_synthetic

NS = 1_000_000_000


def test_session_calendar_cme_eth():
    # Cierre de sesión CME = 16:00 CT lun-vie; apertura 17:00 CT del día previo.
    # Un instante a mediodía de un miércoles cae en la sesión que cierra ese día.
    import datetime as dt
    from zoneinfo import ZoneInfo
    ct = ZoneInfo("America/Chicago")
    wed_noon = dt.datetime(2025, 8, 6, 12, 0, tzinfo=ct)   # miércoles
    ns = int(wed_noon.timestamp() * NS)
    end = sessions.session_end_ns(ns)
    beg = sessions.session_begin_ns(ns)
    end_ct = dt.datetime.fromtimestamp(end / 1e9, tz=ct)
    beg_ct = dt.datetime.fromtimestamp(beg / 1e9, tz=ct)
    assert (end_ct.hour, end_ct.minute) == (16, 0) and end_ct.weekday() == 2  # miér 16:00
    assert (beg_ct.hour, beg_ct.minute) == (17, 0) and beg_ct.weekday() == 1  # mar 17:00
    assert beg < ns < end


def test_sampler_deterministic_stride_and_cap():
    # AddSample decima por stride y al llegar al cap se queda con las mitades
    # (vals[1::2]) y duplica el stride — determinista, nunca aleatorio.
    s = _Sampler(cap=4)
    for v in range(1, 9):     # 1..8
        s.add(float(v))
    # con cap 4: entran 1,2,3,4 -> al 5º se colapsa a [2,4] stride=2, sigue...
    assert s.stride >= 2
    assert len(s.vals) <= 4
    # determinismo: misma secuencia -> mismo estado
    s2 = _Sampler(cap=4)
    for v in range(1, 9):
        s2.add(float(v))
    assert s.vals == s2.vals and s.stride == s2.stride


def test_first_session_emits_calibration_pending():
    # Sin calibración previa (adaptive), la primera sesión debe emitir
    # CALIBRATION_PENDING exactamente una vez y no crear zonas todavía.
    tk = make_synthetic(n_sessions=1, ticks_per_session=8000)
    bars = B.build_time_bars(tk, minutes=1)
    res = hftzones2.run(tk, bars, params=dict(adaptive_mode=True))
    pend = [e for e in res["events"] if e["type"] == "CALIBRATION_PENDING"]
    assert len(pend) == 1, "CALIBRATION_PENDING una sola vez en la 1ra sesión"
    assert not res["zones"], "sin calibración congelada no se crean zonas"


def test_manual_mode_ready_from_start():
    # En modo manual calib_ready arranca en True: no hay CALIBRATION_PENDING.
    tk = make_synthetic(n_sessions=1, ticks_per_session=8000)
    bars = B.build_time_bars(tk, minutes=1)
    res = hftzones2.run(tk, bars, params=dict(
        adaptive_mode=False, manual_min_total_vol=1.0, manual_min_vol_rate=1.0,
        min_export_valid_steps=3, min_pasos=3, min_absorb_pasos=3))
    assert not [e for e in res["events"] if e["type"] == "CALIBRATION_PENDING"]


def test_recalibration_across_sessions():
    # Con varias sesiones y suficientes muestras debe emitir al menos una
    # CALIBRATION (calibración congelada para la sesión siguiente).
    tk = make_synthetic(n_sessions=3, ticks_per_session=9000)
    bars = B.build_time_bars(tk, minutes=1)
    res = hftzones2.run(tk, bars, params=dict(adaptive_mode=True, min_calib_samples=1000))
    calib = [e for e in res["events"] if e["type"] == "CALIBRATION"]
    assert calib, "debe recalibrar al cruzar bordes de sesión con muestras suficientes"


def test_deterministic_on_synthetic():
    tk = make_synthetic(n_sessions=3, ticks_per_session=9000)
    bars = B.build_time_bars(tk, minutes=1)
    r1 = hftzones2.run(tk, bars, params=dict(adaptive_mode=True, min_calib_samples=1000))
    r2 = hftzones2.run(tk, bars, params=dict(adaptive_mode=True, min_calib_samples=1000))
    assert r1["csv_lines"] == r2["csv_lines"]
    seqs = [e["seq"] for e in r1["events"]]
    assert seqs == sorted(seqs)

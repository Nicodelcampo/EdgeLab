"""El store point-in-time no puede mirar hacia adelante ni traer outcomes."""
from __future__ import annotations

import inspect
import re

import numpy as np

from tools import bt2_absorption_param_sweep as S

PROHIBIDOS = ("mfe", "mae", "pnl", "win_rate", "winrate", "hit_rate",
              "retorno", "d_hat", "net_ticks", "take_profit", "stop_loss")


def _rec(t0, bkt_ts, tape_ts, spread):
    zone = {"sig_ts": t0, "lo": 100.0, "hi": 100.2, "nrows": 2, "frac": .3, "vol": 9.0}
    dat = [{"a_score": "1.5", "a_thr": "1.0", "a_pass": "True", "n_hist": "500",
            "signed_flow": "7", "d_ticks": "-3", "n_ticks": "25", "residual": "False"}
           for _ in bkt_ts]
    return S._pit_record("k", zone, "20260101", "long", "GC 02-26", 0.1,
                         np.asarray(bkt_ts, dtype=np.int64), dat,
                         np.asarray(tape_ts, dtype=np.int64), np.asarray(spread, dtype=np.int64))


def test_feature_available_at_nunca_supera_el_evento():
    n = S.PIT_TAPE_WINDOW + 10
    tape = list(range(0, n * 1000, 1000))
    t0 = tape[-5]
    r = _rec(t0, [t0 - 5000, t0 - 1000, t0 + 9999], tape, [1] * n)
    assert r["as_of_ok"] is True
    assert r["feature_available_at_ns"] <= r["event_time_ns"]


def test_ignora_la_cubeta_posterior_a_t0():
    """Si existe una cubeta con t_start > t0, no debe usarse."""
    n = S.PIT_TAPE_WINDOW + 10
    tape = list(range(0, n * 1000, 1000))
    t0 = tape[-5]
    r = _rec(t0, [t0 - 1000, t0 + 500], tape, [1] * n)
    assert r["feature_available_at_ns"] <= t0


def test_sin_historial_suficiente_marca_as_of_ok_false():
    r = _rec(50_000, [40_000], [0, 1000, 2000], [1, 1, 1])
    assert r["as_of_ok"] is False
    assert r["spread_p50_ticks"] is None
    assert r["tape_rate_per_s"] is None


def test_sin_cubeta_previa_no_inventa_estado():
    n = S.PIT_TAPE_WINDOW + 10
    tape = list(range(0, n * 1000, 1000))
    t0 = tape[-1]
    r = _rec(t0, [t0 + 10_000], tape, [1] * n)
    assert r["as_of_ok"] is False
    assert r["a_score"] is None and r["n_hist"] is None


def test_el_registro_no_contiene_ningun_campo_de_outcome():
    n = S.PIT_TAPE_WINDOW + 10
    tape = list(range(0, n * 1000, 1000))
    t0 = tape[-5]
    r = _rec(t0, [t0 - 1000], tape, [1] * n)
    for campo in r:
        assert not any(p in campo.lower() for p in PROHIBIDOS), f"campo de outcome: {campo}"


def test_la_fuente_no_menciona_outcomes_en_el_pit():
    src = inspect.getsource(S._pit_record)
    for p in PROHIBIDOS:
        assert not re.search(rf'"[^"]*{p}[^"]*"\s*:', src, re.I), f"clave prohibida: {p}"


def test_event_keys_sigue_siendo_el_formato_congelado():
    """La extension es aditiva: event_keys no cambia."""
    src = inspect.getsource(S.summarize_run)
    assert '''f"{contract}|{session}|{direction}|{int(zone['sig_ts'])}|{lo2}|{hi2}"''' in src

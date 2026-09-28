"""Auditoría 059 §5: el pool del nulo termina estrictamente antes de la vela 100t del evento (sintético, sin outcomes)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import espejo_nico_descubrimiento as E  # noqa: E402


def _trip(n, tag):
    t = np.zeros((n, 3)); t[:, 0] = np.arange(n) + tag     # la columna 0 hace de "reloj": índice de subvela 25t
    return t


def test_pool_excludes_event_bar_subcandles():
    trip = _trip(4 * 100, 0)
    k = 60
    pool = E.null_pool(trip, k, None)
    assert len(pool) == 4 * k
    assert pool[:, 0].max() < k * E.MULT                     # la última terna es la subvela 4k-1, anterior a la vela k


def test_agg100_groups_four_25t():
    h = np.arange(12, dtype=float); l = h - 1; c = h - 0.5
    H, L, C = E.agg100(h, l, c)
    assert len(C) == 3 and H[0] == 3 and L[0] == -1 and C[0] == 2.5


def test_previous_session_only_when_short():
    prev = _trip(300, 10_000)
    long_pool = E.null_pool(_trip(400, 0), 20, prev)          # 80 propias >= 50: no toca la sesión previa
    assert long_pool[:, 0].max() < 10_000 and len(long_pool) == 80
    short = E.null_pool(_trip(400, 0), 5, prev)               # 20 propias < 50: completa con la cola previa hasta 200
    assert len(short) == 200 and (short[:180, 0] >= 10_000).all() and short[-1, 0] == 19


def test_outcome_ambiguous_and_horizon():
    H = np.array([10, 10, 12, 10.]); L = np.array([8, 8, 5, 8.])
    assert E.outcome(H, L, 0, 6, 12, 1, 3)[0] == "ambigua"   # misma vela toca A (<=6) y más allá de B (>=12)
    assert E.outcome(H, L, 0, 6, 12, 1, 1)[0] == "censurada"

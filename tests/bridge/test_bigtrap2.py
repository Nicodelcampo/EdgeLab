"""Smoke sintético + invariantes propias de BigTrap2 (F5B).

Valida infraestructura y contrato del kernel, NO paridad real con NT8. BigTrap2
corre sobre barras de TIEMPO o de TICK (5t/25t/…); cada resolución es una
configuración distinta. Invariantes clave: FloorDiv (grilla absoluta, correcta
con ticks negativos), formato pipe con seq desde 0, barra 0 descartada.
"""
import numpy as np

from edgelab.bridge import bars as B
from edgelab.bridge.common import floor_div
from edgelab.bridge.indicators import bigtrap2
from edgelab.bridge.viewer_export import bar_key_of, param_set_id
from edgelab.bridge.ticks import TickSeries, make_synthetic

NS = 1_000_000_000


def _mk(ts, px, vol, bid, ask, tick_size=0.25):
    n = len(ts)
    return TickSeries(np.asarray(ts, np.int64), np.asarray(px, np.int64),
                      np.asarray(vol, np.float64), np.asarray(bid, np.int64),
                      np.asarray(ask, np.int64), np.arange(n, dtype=np.int64),
                      tick_size, "SYN", "SYN", "test")


def test_floor_div_negative_matches_csharp():
    # C# FloorDiv: q=a/b; if((a%b!=0)&&((a<0)!=(b<0))) q--; == Python a//b.
    assert floor_div(-3, 5) == -1        # -3 // 5 = -1 (no 0, como truncado)
    assert floor_div(-5, 5) == -1
    assert floor_div(-6, 5) == -2
    assert floor_div(7, 5) == 1
    assert floor_div(-1, 5) == -1


def test_negative_ticks_anchor_to_contiguous_rows():
    # Ticks alrededor de 0 (algunos negativos) con ticks_per_row=5 deben anclar
    # en filas contiguas por FloorDiv: {-5..-1}->-1, {0..4}->0, {5..9}->1.
    expected = {-5: -1, -4: -1, -3: -1, -2: -1, -1: -1,
                0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 1, 9: 1}
    for tk, row in expected.items():
        assert floor_div(tk, 5) == row, f"tick {tk} debe anclar en fila {row}"


def test_pipe_format_and_seq_from_zero():
    tk = make_synthetic(n_sessions=1, ticks_per_session=3000)
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)
    res = bigtrap2.run(tk, bars, fps, params=dict(min_export_volume=1.0, imbalance_ratio=1.5))
    assert res["header"] is None                       # BigTrap2 usa formato pipe, sin header
    assert res["csv_lines"], "debe emitir al menos un evento (TRAP/mismatch)"
    first = res["csv_lines"][0]
    parts = first.split("|", 3)
    assert len(parts) == 4                             # seq|iso|type|payload
    assert parts[0] == "0"                             # seq post-incremento desde 0
    assert "T" in parts[1] and parts[1].count(".") == 1  # iso "o": ...T..:..:..fffffff
    assert len(parts[1].split(".")[1]) == 7            # 7 decimales (100 ns)


def test_bar_zero_discarded():
    tk = make_synthetic(n_sessions=1, ticks_per_session=3000)
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)
    res = bigtrap2.run(tk, bars, fps, params=dict(imbalance_ratio=1.5))
    assert all(e["bar_index"] != 0 for e in res["events"]), "la barra 0 no genera eventos"


def test_reconstructed_footprint_matches_bar_volume():
    tk = make_synthetic(n_sessions=1, ticks_per_session=4000)
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)
    res = bigtrap2.run(tk, bars, fps, params=dict(imbalance_ratio=2.0))
    assert not [e for e in res["events"] if e["type"] == "FOOTPRINT_MISMATCH"]


def test_bar_key_is_identity_dimension():
    # La misma parametrización sobre resoluciones de barra distintas debe dar
    # param_set_id distintos (el bar_key entra al hash de identidad).
    tk = make_synthetic(n_sessions=1, ticks_per_session=5000)
    t_bars = B.build_time_bars(tk, minutes=1)
    k5 = B.build_tick_bars(tk, ticks_per_bar=5)
    k25 = B.build_tick_bars(tk, ticks_per_bar=25)
    params = dict(bigtrap2.DEFAULTS)
    psid_t = param_set_id(params, bar_key_of(t_bars))
    psid_5 = param_set_id(params, bar_key_of(k5))
    psid_25 = param_set_id(params, bar_key_of(k25))
    assert len({psid_t, psid_5, psid_25}) == 3
    assert bar_key_of(k5) == "tick_5" and bar_key_of(k25) == "tick_25"


def test_runs_on_tick_bars():
    # BigTrap2 debe correr sobre barras de tick (su caso de uso real: 25t).
    tk = make_synthetic(n_sessions=1, ticks_per_session=6000)
    k25 = B.build_tick_bars(tk, ticks_per_bar=25)
    fps = B.build_footprints(tk, k25)
    res = bigtrap2.run(tk, k25, fps, params=dict(imbalance_ratio=2.0))
    assert res["indicator"] == "BigTrap2"
    # determinismo bit a bit
    res2 = bigtrap2.run(tk, k25, fps, params=dict(imbalance_ratio=2.0))
    assert res["csv_lines"] == res2["csv_lines"]

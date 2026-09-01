"""Invariante de auto-consistencia barras/footprints (canal del auditor, entrada 025, item 4).

En Python, `build_footprints` asigna cada tick a su barra via `tick_bar_idx` y
`_ohlc` deriva `low_t`/`high_t` de EXACTAMENTE esos ticks: ningun footprint
puede contener un precio fuera del `[low_t, high_t]` de su barra. El filtro de
rango del contrato de `nt8/aVolClusterPOI.cs` (item 3: "ticks fuera de
[lowTick, highTick] de la barra primaria se ignoran") defiende contra la
dessincronia entre las DOS series internas de NT8 (serie de barras primarias
vs subserie 1-tick, clase TICKBAR-001) -- una inconsistencia que el build
Python no tiene. Si alguien cambia el builder y esta invariante se rompe, la
traduccion de la paridad de aVolClusterPOI (y de cualquier kernel que acumule
footprints por barra) hay que revisarla ANTES de interpretar diffs de oraculo.

Verde en sandbox del auditor antes de commitear: 4 semillas x 3 modos
(time:1, tick:120 legacy, tick:120 con reinicio por sesion), 0 violaciones.
"""
from edgelab.bridge import bars as bars_mod
from edgelab.bridge import ticks as ticks_mod


def _assert_footprints_within_bar_range(bars, fps):
    for b in range(len(bars)):
        lo, hi = int(bars.low_t[b]), int(bars.high_t[b])
        for price_tick in fps.total[b]:
            assert lo <= int(price_tick) <= hi, (
                f"bar {b}: footprint contiene tick {price_tick} fuera de [{lo}, {hi}]"
            )


def test_footprint_within_bar_range_tick_bars_session_restart():
    tk = ticks_mod.make_synthetic(seed=7, n_sessions=3, ticks_per_session=20000)
    bars = bars_mod.build_tick_bars(tk, 120)
    fps = bars_mod.build_footprints(tk, bars)
    _assert_footprints_within_bar_range(bars, fps)


def test_footprint_within_bar_range_tick_bars_legacy_no_restart():
    tk = ticks_mod.make_synthetic(seed=13, n_sessions=3, ticks_per_session=20000)
    bars = bars_mod.build_tick_bars(tk, 120, reiniciar_por_sesion=False)
    fps = bars_mod.build_footprints(tk, bars)
    _assert_footprints_within_bar_range(bars, fps)


def test_footprint_within_bar_range_time_bars():
    tk = ticks_mod.make_synthetic(seed=11, n_sessions=2, ticks_per_session=20000)
    bars = bars_mod.build_time_bars(tk, 1)
    fps = bars_mod.build_footprints(tk, bars)
    _assert_footprints_within_bar_range(bars, fps)

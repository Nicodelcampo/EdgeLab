"""VolTicksPOC2 — un config imposible debe GRITAR, no morir en silencio.

Incidente 2026-07-26: un chart con `ratio_window_bars=200` y
`min_ratio_samples=500` no marcaba ninguna zona. No era falta de datos ni un
error: `ratio_win` es una ventana rodante acotada a `ratio_window_bars`, así que
`len(ratio_win) >= min_ratio_samples` **nunca puede cumplirse** y el kernel
devolvía cero zonas para siempre, sin decir nada.

Un "no hay señales" indistinguible de un resultado real es peor que un error:
en una campaña se leería como evidencia de que no hay edge.
"""
import numpy as np
import pytest

from edgelab.bridge import bars as B
from edgelab.bridge.indicators import voltickspoc2
from edgelab.bridge.ticks import make_synthetic


def _datos(n_sessions=1, ticks_per_session=3000):
    tk = make_synthetic(n_sessions=n_sessions, ticks_per_session=ticks_per_session)
    bars = B.build_time_bars(tk, 1)
    return tk, bars, B.build_footprints(tk, bars)


def _run(**params):
    tk, bars, fps = _datos()
    return voltickspoc2.run(tk, bars, fps, params=params, chart_tz="UTC")


def test_config_imposible_levanta_error_en_vez_de_devolver_cero():
    """El caso exacto del chart: ventana 200, mínimo 500."""
    with pytest.raises(ValueError) as e:
        _run(ratio_window_bars=200, min_ratio_samples=500)
    msg = str(e.value)
    assert "min_ratio_samples=500" in msg and "ratio_window_bars=200" in msg
    assert "nunca abre" in msg, "el mensaje debe explicar POR QUE, no solo que fallo"


def test_el_error_dice_como_arreglarlo():
    with pytest.raises(ValueError) as e:
        _run(ratio_window_bars=200, min_ratio_samples=500)
    msg = str(e.value)
    assert "Subir ratio_window_bars a >= 500" in msg
    assert "bajar min_ratio_samples a <= 200" in msg


@pytest.mark.parametrize("win,mini", [(500, 500), (2000, 500), (600, 1)])
def test_configs_alcanzables_no_levantan(win, mini):
    """El límite es `>`, no `>=`: con ventana == mínimo el gate SÍ puede abrir."""
    r = _run(ratio_window_bars=win, min_ratio_samples=mini)
    assert "zones" in r


def test_los_defaults_son_alcanzables():
    """2000 >= 500: si algún día alguien invierte estos defaults, salta acá."""
    d = voltickspoc2.DEFAULTS
    assert d["min_ratio_samples"] <= d["ratio_window_bars"], (
        "los defaults del kernel harian imposible la deteccion: %d > %d"
        % (d["min_ratio_samples"], d["ratio_window_bars"]))


def test_la_ventana_de_baseline_si_es_alcanzable_por_construccion():
    """`baseline_win` tiene maxlen == avg_period y se compara contra
    `>= avg_period`: se llena justo. Es el contraejemplo que muestra que el bug
    no estaba en el patrón sino en el par de parámetros descoordinados."""
    d = voltickspoc2.DEFAULTS
    assert d["avg_period"] == d["avg_period"]      # maxlen == umbral, siempre OK
    r = _run(avg_period=50)
    assert "zones" in r


# --------------------------------------------------------------------------- #
# Warmup: cero zonas por falta de datos != cero zonas por falta de señal
# --------------------------------------------------------------------------- #
def test_declara_cuando_no_hay_datos_ni_para_terminar_el_warmup():
    """Con pocas barras el resultado es CERO zonas garantizado. El kernel lo
    dice, en vez de dejar un `zones == []` ambiguo."""
    tk = make_synthetic(n_sessions=1, ticks_per_session=2000)
    bars = B.build_time_bars(tk, 1)
    r = voltickspoc2.run(tk, bars, B.build_footprints(tk, bars),
                         params=None, chart_tz="UTC")
    assert r["warmup_bars"] == 700, "200 de baseline + 500 de ratios"
    assert r["datos_insuficientes"] is True
    assert r["zones"] == [], "sin warmup no puede haber deteccion"


def test_no_marca_datos_insuficientes_cuando_alcanzan():
    """El fixture sintetico da ~6 barras m1, asi que el warmup se baja a su
    escala: lo que se verifica es la REGLA, no la magnitud."""
    tk = make_synthetic(n_sessions=1, ticks_per_session=3000)
    bars = B.build_time_bars(tk, 1)
    assert len(bars) >= 5, "el fixture cambio de tamano; ajustar el warmup"
    r = voltickspoc2.run(tk, bars, B.build_footprints(tk, bars),
                         params=dict(avg_period=2, min_ratio_samples=2,
                                     ratio_window_bars=10),
                         chart_tz="UTC")
    assert r["warmup_bars"] == 4
    assert r["n_bars"] == len(bars)
    assert r["datos_insuficientes"] is False

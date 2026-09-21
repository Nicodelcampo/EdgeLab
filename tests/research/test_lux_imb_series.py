"""LUX-IMB en serie: la version vectorizada = la referencia escalar, y el ciclo de vida respeta sus fronteras."""
from datetime import datetime, timezone

import numpy as np
import pytest

from edgelab.research import lux_imb as L
from edgelab.research import lux_imb_series as S


def _bars(n, seed):
    rng = np.random.default_rng(seed)
    o = np.round(100 + np.cumsum(rng.normal(0, 0.3, n)), 2)
    c = np.round(o + rng.normal(0, 0.25, n), 2)
    h = np.round(np.maximum(o, c) + np.abs(rng.normal(0, 0.1, n)), 2)
    l = np.round(np.minimum(o, c) - np.abs(rng.normal(0, 0.1, n)), 2)
    return o, h, l, c


@pytest.mark.parametrize("geometry", ["body", "wick"])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_serie_vectorizada_igual_a_la_referencia_escalar(geometry, seed):
    o, h, l, c = _bars(3000, seed)
    z = S.detect_series(o, h, l, c, og_geometry=geometry)
    B = [L.OhlcBar(datetime.fromtimestamp(60 * i, timezone.utc), o[i], h[i], l[i], c[i]) for i in range(len(o))]
    ref = sorted((i - 1, 0 if q.family == "OG" else 1, 1 if q.direction == "bullish" else -1,
                  round(q.top, 9), round(q.bottom, 9))
                 for i in range(1, len(B)) for q in L.detect_og_vi(B[i - 1], B[i], og_geometry=geometry))
    vec = sorted((int(a), int(b), int(d), round(float(t), 9), round(float(m), 9))
                 for a, b, d, t, m in zip(z["i_prev"], z["family"], z["direction"], z["top"], z["bottom"]))
    assert ref == vec and len(ref) > 50


def test_og_cuerpo_vs_mecha_difieren_solo_en_el_borde_no_en_los_sucesos():
    o, h, l, c = _bars(3000, 7)
    zb = S.detect_series(o, h, l, c, og_geometry="body")
    zw = S.detect_series(o, h, l, c, og_geometry="wick")
    assert (zb["i_prev"] == zw["i_prev"]).all() and (zb["direction"] == zw["direction"]).all()
    og = zb["family"] == S.OG
    assert not np.allclose(zb["top"][og], zw["top"][og])            # hay OG donde el cuerpo difiere de la mecha
    assert np.allclose(zb["top"][~og], zw["top"][~og])              # VI no depende de la geometria OG


def test_geometria_invalida_falla_cerrado():
    o, h, l, c = _bars(10, 1)
    with pytest.raises(ValueError):
        S.detect_series(o, h, l, c, og_geometry="otra")


def _gap_serie(extra):
    """barra 0 y barra 1 forman un OG alcista (low1 > high0); despues, `extra` = lista de (high, low)."""
    o = [10.0, 11.0]; h = [10.5, 11.5]; l = [9.5, 10.8]; c = [10.0, 11.0]
    for hh, ll in extra:
        o.append(11.4); c.append(11.4); h.append(hh); l.append(ll)
    return o, h, l, c


def test_toque_cruce_estricto_y_ventana_de_500_barras():
    fill = 10.5                                      # OG alcista: borde inferior = high de la barra previa (mecha) / cuerpo 10.0
    # con geometria mecha el fill es 10.5 y hay que cruzarlo estrictamente hacia abajo
    def run(k_touch, level):
        extra = [(11.8, 11.0)] * 700
        extra[k_touch - 2] = (11.8, level)          # indice absoluto k_touch = 2 + posicion en `extra`
        o, h, l, c = _gap_serie(extra)
        z = S.detect_series(o, h, l, c, og_geometry="wick")
        assert list(z["i_prev"]) == [0] and z["bottom"][0] == fill
        return bool(S.lifecycle(z, np.arange(len(o)) * 60, h, l)["touched"][0])
    assert run(2, 10.4) is True                     # primera barra elegible: i_prev + 2
    assert run(500, 10.4) is True                   # ultima barra elegible: i_prev + 500
    assert run(501, 10.4) is False                  # la barra i_prev+501 es el vencimiento: no cuenta
    assert run(10, 10.5) is False                   # igualdad no es cruce


def test_vencimiento_proyectado_mas_alla_de_los_datos():
    o, h, l, c = _gap_serie([(11.8, 11.0)] * 10)
    t = np.arange(len(o)) * 60 + 1_000
    z = S.detect_series(o, h, l, c, og_geometry="wick")
    lc = S.lifecycle(z, t, h, l, extend_bars=500, bar_seconds=60)
    assert lc["t1"][0] == t[-1] + (0 + 1 + 500 - (len(o) - 1)) * 60
    assert lc["t0"][0] == t[0]

"""LiqHeat: mapa de intensidad por nivel de precio.

Fija las tres decisiones que definen el objeto:

1. las zonas **no mueren por distancia** al precio — decisión explícita;
2. mueren **lenta y progresivamente** por tiempo y por toques;
3. la escala se **normaliza contra un percentil**, no contra un absoluto, que es
   lo que evita que el mapa salga siempre demasiado claro o demasiado opaco.
"""
from edgelab.bridge.indicators.liqheat import (
    RESEARCH_DEFAULTS, crossing_speed, intensity_map, normalize, zone_weight)


def _z(far, near=None, created=0, touches=0, state="ACTIVE", n_pivots=2,
       band_lo=None, band_hi=None):
    return dict(far_edge_tick=far, near_edge_tick=near if near is not None else far,
                created_bar=created, touches=touches, state=state,
                n_pivots=n_pivots, band_lo=band_lo, band_hi=band_hi)


def test_NO_muere_por_distancia():
    """La decisión más importante, y va contra la intuición del chart.

    Una zona lejos del precio sigue siendo inventario en el libro. El peso no
    depende de dónde está el precio — de hecho `zone_weight` ni lo recibe.
    """
    z = _z(far=1000, created=0)
    assert zone_weight(z, 100) == zone_weight(z, 100)
    # el peso sólo depende de edad, toques y estado: no hay parámetro de precio
    import inspect
    firma = inspect.signature(zone_weight).parameters
    assert "price" not in firma and "distance" not in firma


def test_decae_por_tiempo_con_vida_media():
    z = _z(far=1000, created=0)
    p = {"half_life_bars": 100, "weight_by_pivots": False}
    assert zone_weight(z, 0, p) == 1.0
    assert abs(zone_weight(z, 100, p) - 0.5) < 1e-9, "una vida media = la mitad"
    assert abs(zone_weight(z, 200, p) - 0.25) < 1e-9
    # sin decaimiento temporal el peso no cae
    assert zone_weight(z, 10_000, {"half_life_bars": 0,
                                   "weight_by_pivots": False}) == 1.0


def test_decae_por_toques():
    p = {"half_life_bars": 0, "touch_decay": 0.5, "weight_by_pivots": False}
    assert zone_weight(_z(1000, touches=0), 10, p) == 1.0
    assert zone_weight(_z(1000, touches=1), 10, p) == 0.5
    assert zone_weight(_z(1000, touches=3), 10, p) == 0.125


def test_el_estado_pesa_distinto():
    p = {"half_life_bars": 0, "weight_by_pivots": False,
         "swept_weight": 0.5, "broken_weight": 0.0}
    assert zone_weight(_z(1000, state="ACTIVE"), 10, p) == 1.0
    assert zone_weight(_z(1000, state="SWEPT"), 10, p) == 0.5
    assert zone_weight(_z(1000, state="BROKEN"), 10, p) == 0.0, "rota = dejó de existir"


def test_las_zonas_se_acumulan_por_nivel():
    zonas = [_z(far=100, near=100), _z(far=100, near=100), _z(far=105, near=105)]
    m = intensity_map(zonas, 0, {"half_life_bars": 0, "weight_by_pivots": False})
    assert m[100] == 2.0, "dos zonas en el mismo nivel suman"
    assert m[105] == 1.0
    assert 102 not in m, "un nivel sin zonas no aparece: es un hueco"


def test_la_banda_de_liquidez_entra_en_el_span():
    z = _z(far=100, near=100, band_lo=101, band_hi=103)
    m = intensity_map([z], 0, {"half_life_bars": 0, "weight_by_pivots": False})
    assert set(m) == {100, 101, 102, 103}


def test_una_zona_futura_no_cuenta():
    m = intensity_map([_z(far=100, created=50)], 10)
    assert m == {}, "no se puede usar una zona antes de que exista"


def test_la_normalizacion_es_por_PERCENTIL_no_por_absoluto():
    """La respuesta al problema de calibración.

    Con escala fija, el mismo umbral sale claro en un instrumento y saturado en
    otro. El percentil hace que el mapa se autoescale.
    """
    flojo = {i: 1.0 for i in range(100)}
    fuerte = {i: 50.0 for i in range(100)}
    assert max(normalize(flojo).values()) == max(normalize(fuerte).values()) == 1.0

    # con escala fija, en cambio, el flojo queda casi invisible
    nf = normalize(flojo, {"max_intensity": 50})
    assert max(nf.values()) == 0.02


def test_la_escala_fija_sirve_para_comparar_entre_corridas():
    m = {1: 10.0, 2: 20.0}
    n = normalize(m, {"max_intensity": 40})
    assert n[1] == 0.25 and n[2] == 0.5


def test_crossing_speed_agrupa_por_decil_de_intensidad():
    hi = [100 + (i % 20) for i in range(400)]
    lo = [90 + (i % 20) for i in range(400)]
    zonas = [_z(far=105, near=105, created=0, n_pivots=4)]
    r = crossing_speed(hi, lo, zonas, {"half_life_bars": 0}, sample_every=25)
    assert r, "tiene que devolver algo con lo que medir"
    for v in r.values():
        assert "barras_por_tick" in v


def test_defaults_declarados():
    assert RESEARCH_DEFAULTS["half_life_bars"] == 500
    assert RESEARCH_DEFAULTS["touch_decay"] == 0.70
    assert RESEARCH_DEFAULTS["broken_weight"] == 0.0
    assert RESEARCH_DEFAULTS["normalize_pct"] == 95

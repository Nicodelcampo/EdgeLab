"""LiqPool: cadenas de puntos sobre un nivel.

El modelo pasó por cuatro versiones antes de esta, y cada corrección vino de ver
el detector contra un chart real. Los tests fijan las tres reglas que sobrevivieron:

1. **un punto es la mecha de una vela**, no un pivote de K barras;
2. **corta la cadena romper el nivel, no alejarse de él** — que el precio se vaya
   y vuelva no corta nada;
3. **la escalera no puede ser empinada**: la deriva del nivel está acotada.

Y sólo dos de las cuatro combinaciones son zonas: mínimos que suben o se
mantienen, y máximos que bajan o se mantienen.
"""
from edgelab.bridge.indicators.liqpool import (
    RESEARCH_DEFAULTS, build_chains, census, detect, points)

P = dict(min_pivots=5, touch_tolerance_ticks=1, max_total_drift_ticks=6,
         max_slope_ticks=1, slope_per_bars=20, max_step_bars=400)


def _lows(lows, extra=None):
    hi = [max(lows) + 30] * len(lows)
    p = dict(P)
    if extra:
        p.update(extra)
    return [z for z in build_chains(hi, lows, p) if z["side"] == "L"]


def _highs(highs, extra=None):
    lo = [min(highs) - 30] * len(highs)
    p = dict(P)
    if extra:
        p.update(extra)
    return [z for z in build_chains(highs, lo, p) if z["side"] == "H"]


def test_un_punto_es_la_mecha_de_cada_vela():
    hi = [10, 12, 11]
    lo = [5, 4, 6]
    assert points(hi, lo, "H") == [(0, 10), (1, 12), (2, 11)]
    assert points(hi, lo, "L") == [(0, 5), (1, 4), (2, 6)]
    # el modo viejo sigue disponible para contrastar
    assert points(hi, lo, "H", {"point_mode": "pivot"}) != points(hi, lo, "H")


def test_alejarse_del_nivel_NO_corta_la_cadena():
    """El caso del chart: dos grupos de mínimos unidos por una loma en el medio.

    Es la corrección más importante. La versión anterior cortaba en cuanto el
    precio se iba, y por eso nunca unía los dos grupos que Nico traza con una
    sola línea.
    """
    serie = [60, 60, 61, 60, 60] + [70, 75, 80, 78, 72] + [60, 61, 60, 60, 60]
    z = _lows(serie)
    assert len(z) == 1
    assert z[0]["n_pivots"] == 10, "los diez toques, a los dos lados de la loma"
    assert z[0]["span_bars"] >= 14


def test_romper_el_nivel_SI_corta():
    serie = [60, 60, 60, 60, 60] + [50] + [60, 60, 60, 60, 60]
    z = _lows(serie)
    assert all(z_["n_pivots"] <= 5 for z_ in z), "el mínimo que rompe parte la cadena"


def test_serrucho_plano():
    z = _lows([60, 60, 60, 61, 60, 60, 61, 60])
    assert len(z) == 1
    assert z[0]["direction"] == 0
    assert z[0]["n_pivots"] == 8


def test_escalera_suave_es_zona():
    z = _lows([60] * 20 + [61] * 20 + [62] * 20)
    assert len(z) == 1
    assert z[0]["direction"] == 1


def test_escalera_empinada_NO_es_zona():
    """«No puede ser empinada la escalera», textual."""
    assert _lows(list(range(60, 80))) == []


def test_solo_dos_de_las_cuatro_combinaciones():
    """El filtro elimina la DIRECCIÓN inválida, no los tramos planos.

    Matiz que apareció al testear: una bajada escalonada de mínimos, con el filtro
    puesto, no desaparece — se parte en los **serruchos planos** que la componen,
    y cada uno de ésos sí es una zona legítima. Lo que no puede existir es una
    cadena de mínimos con dirección descendente.
    """
    sube = [60] * 20 + [61] * 20 + [62] * 20
    baja = [62] * 20 + [61] * 20 + [60] * 20

    assert any(z["direction"] == 1 for z in _lows(sube)), "mínimos que suben = soporte"
    assert all(z["direction"] != -1 for z in _lows(baja)),         "ninguna cadena de mínimos puede ir hacia abajo"
    assert any(z["direction"] == -1 for z in _highs(baja)), "máximos que bajan = resistencia"
    assert all(z["direction"] != 1 for z in _highs(sube)),         "ninguna cadena de máximos puede ir hacia arriba"

    # apagando el filtro, la dirección inválida vuelve a aparecer
    assert any(z["direction"] == -1
               for z in _lows(baja, {"only_compressing_chains": False}))


def test_min_pivots_exige_varios_puntos():
    corta = [60, 60, 60]
    assert _lows(corta, {"min_pivots": 5}) == []
    assert _lows(corta, {"min_pivots": 3})


def test_el_nivel_operativo_es_el_ultimo_toque():
    z = _lows([60] * 20 + [61] * 20 + [62] * 20)[0]
    assert z["level_tick"] == 62


def test_volver_al_nivel_EXTIENDE_la_cadena_en_vez_de_tocarla():
    """Consecuencia del modelo, y conviene tenerla escrita.

    Si el precio vuelve al nivel dentro de `max_step_bars`, esos puntos **entran a
    la cadena**: no son un «toque» sobre una zona ya cerrada. El ciclo de vida
    (TOUCHED / SWEPT) recién aplica una vez que la cadena se cerró.
    """
    serie = [60] * 8 + [70] * 20 + [60] * 3 + [70] * 10
    z = [x for x in _lows(serie) if x["level_tick"] == 60]
    assert z and z[0]["n_pivots"] == 11, "los 8 iniciales más los 3 del regreso"
    assert z[0]["span_bars"] >= 30


def test_la_cadena_cerrada_y_tocada_NO_se_borra():
    # con la ventana corta, la cadena inicial se cierra antes de que el precio vuelva
    serie = [60] * 8 + [70] * 30 + [60] * 3
    hi = [100] * len(serie)
    z = [x for x in detect(hi, serie, dict(P, max_step_bars=10, invalidation_ticks=99))
         if x["side"] == "L" and x["level_tick"] == 60 and x["created_bar"] < 10]
    assert z, "la cadena inicial tiene que estar en el censo"
    assert z[0]["touched_bar"] is not None, "y quedar marcada como tocada, no borrada"
    assert z[0]["state"] == "TOUCHED"


def test_censo_cuenta_las_nunca_tocadas():
    serie = [60] * 8 + [70] * 30
    hi = [100] * len(serie)
    c = census(detect(hi, serie, dict(P, invalidation_ticks=99)))
    assert "nunca_tocadas" in c


def test_defaults_declarados():
    assert RESEARCH_DEFAULTS["point_mode"] == "bar_extreme"
    assert RESEARCH_DEFAULTS["only_compressing_chains"] is True
    assert RESEARCH_DEFAULTS["round_ticks"] == 32, "ZB: 32 ticks = 1 punto"

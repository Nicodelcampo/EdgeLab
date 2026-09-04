"""LiqPool: cadenas escalonadas de pivotes consecutivos.

El objeto NO es «picos al mismo precio». Es una **escalera**: pivotes consecutivos
que bajan (o suben) escalón por escalón, y donde **el pico que supera al anterior
corta la cadena**. Ese criterio lo dio Nico textualmente y es el que estos tests
fijan, porque la primera versión buscaba niveles horizontales y por eso casi no
coincidía con lo que él marca a mano.

Los máximos iguales quedan como **caso particular** —el escalón plano— no como el
objeto entero.
"""
from edgelab.bridge.indicators.liqpool import (
    RESEARCH_DEFAULTS, build_chains, census, detect, find_pivots)


def _serie(picos, largo=120, base=80, piso=70):
    """Serie plana con máximos locales en `picos` = [(barra, precio)]."""
    hi = [base] * largo
    lo = [piso] * largo
    for b, v in picos:
        hi[b] = v
    return hi, lo


def _serie_lows(picos, largo=120, base=80, techo=90):
    hi = [techo] * largo
    lo = [base] * largo
    for b, v in picos:
        lo[b] = v
    return hi, lo


P = {"pivot_strength": 3, "min_pivots": 3, "max_step_ticks": 4}


def _altos(hi, lo, extra=None):
    p = dict(P)
    if extra:
        p.update(extra)
    return [z for z in build_chains(hi, lo, p) if z["side"] == "H"]


def test_escalera_descendente_de_maximos():
    hi, lo = _serie([(10, 100), (22, 98), (34, 96), (46, 94)])
    c = _altos(hi, lo)
    assert len(c) == 1
    assert c[0]["pivot_levels"] == [100, 98, 96, 94]
    assert c[0]["direction"] == -1
    assert c[0]["total_drop_ticks"] == 6


def test_el_pico_que_supera_al_anterior_CORTA_la_cadena():
    """El criterio textual de Nico, y el que la primera versión no tenía."""
    hi, lo = _serie([(10, 100), (22, 98), (34, 96), (46, 110), (58, 108), (70, 106)])
    c = _altos(hi, lo)
    niveles = [z["pivot_levels"] for z in c]
    assert [100, 98, 96] in niveles, "la primera escalera termina donde el pico la supera"
    assert not any(110 in n and 96 in n for n in niveles), \
        "el pico que supera no puede quedar en la misma cadena"


def test_el_escalon_plano_no_rompe_y_los_maximos_iguales_son_un_caso_particular():
    hi, lo = _serie([(10, 100), (22, 100), (34, 100), (46, 98)])
    c = _altos(hi, lo)
    assert len(c) == 1
    assert c[0]["flat_steps"] == 2
    assert c[0]["pivot_levels"] == [100, 100, 100, 98]

    sin_planos = _altos(hi, lo, {"allow_equal_steps": False})
    assert sin_planos == [], "con allow_equal_steps=False el plano corta"


def test_un_salto_de_precio_grande_corta_la_cadena():
    hi, lo = _serie([(10, 100), (22, 98), (34, 96), (46, 80)])   # salto de 16
    c = _altos(hi, lo, {"max_step_ticks": 4})
    assert all(80 not in z["pivot_levels"] for z in c)


def test_demasiada_distancia_temporal_corta_la_cadena():
    hi, lo = _serie([(10, 100), (22, 98), (34, 96), (110, 94)], largo=200)
    c = _altos(hi, lo, {"max_step_bars": 20})
    assert all(94 not in z["pivot_levels"] for z in c)
    # con la ventana amplia, el mismo pico sí entra
    c2 = _altos(hi, lo, {"max_step_bars": 300})
    assert any(94 in z["pivot_levels"] for z in c2)


def test_escalera_ascendente_de_minimos():
    hi, lo = _serie_lows([(10, 60), (22, 62), (34, 64), (46, 66)])
    c = [z for z in build_chains(hi, lo, P) if z["side"] == "L"]
    assert len(c) == 1
    assert c[0]["direction"] == 1
    assert c[0]["pivot_levels"] == [60, 62, 64, 66]


def test_el_nivel_operativo_es_el_ultimo_escalon():
    """Los escalones previos ya fueron superados por la propia escalera."""
    hi, lo = _serie([(10, 100), (22, 98), (34, 96)])
    z = _altos(hi, lo)[0]
    assert z["level_tick"] == 96
    assert z["level_hi"] == 96


def test_min_pivots_exige_escalones():
    hi, lo = _serie([(10, 100), (22, 98)])
    assert _altos(hi, lo, {"min_pivots": 3}) == []
    assert len(_altos(hi, lo, {"min_pivots": 2})) == 1


def test_registra_span_y_excursion_para_estratificar():
    hi, lo = _serie([(10, 100), (14, 98), (18, 96)])          # microzona
    lejos_hi, lejos_lo = _serie([(10, 100), (50, 98), (90, 96)], largo=160)
    m = _altos(hi, lo)[0]
    l = _altos(lejos_hi, lejos_lo, {"max_step_bars": 300})[0]
    assert m["span_bars"] < l["span_bars"]
    assert "excursion_ticks" in m and "step_ticks" in m


def test_la_cadena_tocada_NO_se_borra():
    hi, lo = _serie([(10, 100), (22, 98), (34, 96)], largo=160)
    for b in range(60, 65):
        hi[b] = 96
    z = [x for x in detect(hi, lo, dict(P, invalidation_ticks=99)) if x["side"] == "H"]
    assert z and z[0]["touched_bar"] is not None
    assert z[0]["state"] == "TOUCHED"


def test_censo_cuenta_las_nunca_tocadas():
    hi, lo = _serie([(10, 100), (22, 98), (34, 96)], largo=160)
    c = census(detect(hi, lo, dict(P, invalidation_ticks=99)))
    assert "nunca_tocadas" in c and c["n"] > 0


def test_defaults_declarados():
    assert RESEARCH_DEFAULTS["min_pivots"] == 3
    assert RESEARCH_DEFAULTS["allow_equal_steps"] is True
    assert RESEARCH_DEFAULTS["round_ticks"] == 32, "ZB: 32 ticks = 1 punto"

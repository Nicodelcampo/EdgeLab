"""LiqPool v2 — modelo EQH/EQL portado de las implementaciones de referencia.

Los tests fijan las tres correcciones que trajo el porte
(`docs/research/H-LIQPOOL_FUENTES_COMPARADAS_2026-09-03.md`):

1. **tolerancia relativa**, no fija en ticks — todas las referencias usan % o ATR;
2. **sweep en el borde lejano**, y **mecha ≠ cierre** — tres estados;
3. **pivotes cortos** con longitudes izquierda/derecha separadas.

Más la regla que evita el sesgo: una zona barrida o rota **no se borra**.
"""
import pytest

from edgelab.bridge.indicators.liqpool import (
    RESEARCH_DEFAULTS, build_zones, census, detect, find_pivots, tolerance_ticks)

P = dict(pivot_left=2, pivot_right=2, min_pivots=2, eq_tolerance_ticks=1)


def _serie(picos, largo=80, techo=3500, piso=3400):
    """Serie con máximos locales en `picos` = [(barra, tick)]."""
    hi = [piso + 5] * largo
    lo = [piso] * largo
    for b, v in picos:
        hi[b] = v
    return hi, lo, list(hi)


# ---------------------------------------------------------------- tolerancia

def test_la_tolerancia_es_RELATIVA_al_precio():
    """0,1 % es lo que usan LuxAlgo y SMC-Liquidity-Hunter."""
    # ZB a 108 puntos = 3456 ticks de 1/32 -> 0,1 % ≈ 3 ticks, no 1
    assert tolerance_ticks(3456, {"eq_tolerance_pct": 0.10}) == 3
    # un instrumento con muchos más ticks da una tolerancia mayor, en ticks
    assert tolerance_ticks(100_000, {"eq_tolerance_pct": 0.10}) == 100
    # nunca baja de 1 tick
    assert tolerance_ticks(10, {"eq_tolerance_pct": 0.10}) == 1


def test_el_valor_fijo_pisa_al_porcentaje_solo_para_contrastar():
    assert tolerance_ticks(3456, {"eq_tolerance_pct": 0.10,
                                  "eq_tolerance_ticks": 7}) == 7


# ---------------------------------------------------------------- pivotes

def test_una_meseta_produce_UN_pivote_en_su_ultima_barra():
    """Con `>` a los dos lados (como Pine) una meseta no daría ningún pivote.

    En ZB las mesetas son constantes por el tick grueso, así que perderlas sería
    perder casi todos los puntos. La asimetría `>=` izquierda / `>` derecha deja
    exactamente uno, en la **última** barra: la defensa más reciente del nivel.
    """
    hi = [10, 12, 12, 11, 10]
    lo = [1] * 5
    piv = [x for x in find_pivots(hi, lo, {"pivot_left": 1, "pivot_right": 1})
           if x[1] == "H"]
    assert [b for b, _, _ in piv] == [2], "la última barra de la meseta"


def test_pivot_right_es_el_retardo_de_confirmacion():
    hi = [10, 20, 10, 10, 10]
    lo = [1] * 5
    assert [x[0] for x in find_pivots(hi, lo, {"pivot_left": 1, "pivot_right": 1})
            if x[1] == "H"] == [1]
    # con right=3 el mismo pivote sigue siendo válido, pero necesita 3 barras más
    assert [x[0] for x in find_pivots(hi, lo, {"pivot_left": 1, "pivot_right": 3})
            if x[1] == "H"] == [1]


# ---------------------------------------------------------------- zonas

def test_dos_maximos_iguales_forman_una_EQH():
    hi, lo, cl = _serie([(10, 3500), (30, 3500)])
    z = [x for x in build_zones(hi, lo, P) if x["side"] == "H"]
    assert len(z) == 1
    assert z[0]["n_pivots"] == 2
    assert z[0]["far_edge_tick"] == 3500


def test_dentro_de_la_tolerancia_siguen_siendo_iguales():
    hi, lo, cl = _serie([(10, 3500), (30, 3503)])
    assert [x for x in build_zones(hi, lo, dict(P, eq_tolerance_ticks=3))
            if x["side"] == "H"]
    assert not [x for x in build_zones(hi, lo, dict(P, eq_tolerance_ticks=1))
                if x["side"] == "H"]


def test_el_borde_lejano_es_el_pivote_mas_extremo():
    hi, lo, cl = _serie([(10, 3500), (30, 3502), (50, 3501)])
    z = [x for x in build_zones(hi, lo, dict(P, eq_tolerance_ticks=3))
         if x["side"] == "H"][0]
    assert z["far_edge_tick"] == 3502, "el más alto del cluster"
    assert z["near_edge_tick"] == 3500


def test_min_pivots_y_max_span():
    hi, lo, cl = _serie([(10, 3500), (30, 3500)])
    assert not [x for x in build_zones(hi, lo, dict(P, min_pivots=3))
                if x["side"] == "H"]
    assert not [x for x in build_zones(hi, lo, dict(P, max_span_bars=5))
                if x["side"] == "H"]


# ---------------------------------------------------------------- ciclo de vida

def test_mecha_a_traves_es_SWEPT_y_cierre_a_traves_es_BROKEN():
    """La distinción de PyIndicators, que es la que pide Osler.

    Mecha a través = cascada de stops sin aceptación. Cierre a través = el nivel
    dejó de existir. Mezclarlas en un solo estado pierde el mecanismo.
    """
    hi, lo, cl = _serie([(10, 3500), (30, 3500)], largo=80)
    # barra 50: la mecha pasa por encima pero el cierre queda debajo
    hi[50] = 3510
    cl[50] = 3495
    z = [x for x in detect(hi, lo, cl, P) if x["side"] == "H"][0]
    assert z["state"] == "SWEPT"
    assert z["swept_bar"] == 50 and z["broken_bar"] is None

    hi2, lo2, cl2 = _serie([(10, 3500), (30, 3500)], largo=80)
    hi2[50] = 3510
    cl2[50] = 3508                      # ahora CIERRA por encima
    z2 = [x for x in detect(hi2, lo2, cl2, P) if x["side"] == "H"][0]
    assert z2["state"] == "BROKEN"
    assert z2["broken_bar"] == 50


def test_la_zona_barrida_NO_se_borra():
    hi, lo, cl = _serie([(10, 3500), (30, 3500)], largo=80)
    hi[50] = 3510
    cl[50] = 3508
    z = [x for x in detect(hi, lo, cl, P) if x["side"] == "H"]
    assert z, "la zona rota tiene que seguir en el censo"
    assert z[0]["state"] == "BROKEN"
    assert z[0]["age_at_sweep"] == 50 - z[0]["created_bar"]


def test_los_toques_se_cuentan_para_el_score():
    """Más toques previos ⇒ más rebote (arXiv 2101.07410 y SMC-Liquidity-Hunter)."""
    hi, lo, cl = _serie([(10, 3500), (30, 3500)], largo=120)
    for b in (50, 70, 90):
        hi[b] = 3500                    # vuelve al nivel sin pasarlo
        cl[b] = 3490
    # Con `merge_neighbours` los regresos al MISMO nivel se funden como pivotes
    # más del cluster —comportamiento correcto de LuxAlgo, «2x EQH»— y entonces no
    # son «toques». Para aislar el conteo de toques hay que apagar la fusión.
    z = [x for x in detect(hi, lo, cl, dict(P, max_span_bars=25,
                                            merge_neighbours=False))
         if x["side"] == "H" and x["created_bar"] == 30][0]
    assert z["touches"] == 3
    assert z["first_touch_bar"] == 50


def test_el_censo_cuenta_las_nunca_tocadas_y_nunca_barridas():
    hi, lo, cl = _serie([(10, 3500), (30, 3500)], largo=80)
    c = census(detect(hi, lo, cl, P))
    assert c["n"] >= 1
    assert "nunca_tocadas" in c and "nunca_barridas" in c


def test_fusion_de_zonas_vecinas():
    """El «2x EQH» de LuxAlgo."""
    hi, lo, cl = _serie([(10, 3500), (20, 3500), (40, 3501), (50, 3501)], largo=90)
    con = [x for x in build_zones(hi, lo, dict(P, eq_tolerance_ticks=1,
                                               merge_neighbours=True))
           if x["side"] == "H"]
    sin = [x for x in build_zones(hi, lo, dict(P, eq_tolerance_ticks=1,
                                               merge_neighbours=False))
           if x["side"] == "H"]
    assert len(con) <= len(sin)
    assert max(z["n_pivots"] for z in con) >= max(z["n_pivots"] for z in sin)


def test_defaults_del_modelo_de_referencia():
    assert RESEARCH_DEFAULTS["eq_tolerance_pct"] == 0.10, "LuxAlgo y SMC-Hunter"
    assert RESEARCH_DEFAULTS["pivot_left"] == 2 and RESEARCH_DEFAULTS["pivot_right"] == 2
    assert RESEARCH_DEFAULTS["min_pivots"] == 2, "EQH/EQL clásico son dos"
    assert RESEARCH_DEFAULTS["round_ticks"] == 32, "ZB: 32 ticks = 1 punto"

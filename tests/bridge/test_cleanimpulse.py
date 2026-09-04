"""CleanImpulse: impulsos largos sin zonas creadas adentro.

Fija las tres decisiones del objeto:

1. los tramos van de un pivote **al opuesto** — dos máximos seguidos no delimitan uno;
2. el corte del 5 % es **causal**: sólo con tramos ya cerrados, nunca con el chart
   entero, porque eso clasificaría con información del futuro;
3. cuenta zonas **creadas adentro**, no zonas presentes.
"""
from edgelab.bridge.indicators.cleanimpulse import (
    RESEARCH_DEFAULTS, build_legs, census, detect, find_swings, zones_inside)

P = dict(pivot_left=2, pivot_right=2, window_legs=50, top_pct=20.0)


def _zigzag(picos, largo=400, base=1000):
    """Serie que sube y baja entre los niveles dados, cada 20 barras."""
    hi, lo = [], []
    for i in range(largo):
        k = min(i // 20, len(picos) - 1)
        v = base + picos[k]
        hi.append(v + 1)
        lo.append(v - 1)
    return hi, lo


def test_los_tramos_van_de_un_pivote_al_OPUESTO():
    hi, lo = _zigzag([0, 30, 5, 60, 10])
    sw = find_swings(hi, lo, P)
    tipos = [t for _, t, _ in sw]
    assert all(a != b for a, b in zip(tipos, tipos[1:])), "tienen que alternar"


def test_el_largo_es_el_desplazamiento_en_ticks():
    hi, lo = _zigzag([0, 30, 5])
    legs = build_legs(hi, lo, P)
    assert legs, "tiene que haber tramos"
    assert all(l["length_ticks"] == abs(l["end_tick"] - l["start_tick"]) for l in legs)
    assert all(l["direction"] in (1, -1) for l in legs)


def test_el_corte_del_top_pct_es_CAUSAL():
    """Con el percentil de todo el chart, un tramo quedaría clasificado con
    información posterior. Acá el corte de cada tramo usa sólo los anteriores.
    """
    hi, lo = _zigzag([0, 20, 0, 20, 0, 20, 0, 200, 0])
    legs = detect(hi, lo, [], P)
    assert legs[0]["cut_ticks"] is None, "el primer tramo no tiene con qué comparar"
    # el tramo enorme llega DESPUÉS, así que no puede haber subido el corte antes
    idx = max(range(len(legs)), key=lambda i: legs[i]["length_ticks"])
    previos = [l["cut_ticks"] for l in legs[:idx] if l["cut_ticks"] is not None]
    if previos:
        assert max(previos) < legs[idx]["length_ticks"]


def test_marca_solo_los_largos_SIN_zonas_creadas_adentro():
    hi, lo = _zigzag([0, 20, 0, 20, 0, 20, 0, 200, 0])
    legs_sin = detect(hi, lo, [], P)
    largos = [l for l in legs_sin if l["is_long"]]
    assert largos, "algún tramo tiene que quedar en el top"
    assert all(l["is_clean"] for l in largos), "sin zonas, todos los largos son limpios"

    # ahora una zona creada dentro del tramo más largo
    mayor = max(legs_sin, key=lambda l: l["length_ticks"])
    zona = dict(start_bar=(mayor["start_bar"] + mayor["end_bar"]) // 2)
    legs_con = detect(hi, lo, [zona], P)
    igual = [l for l in legs_con if l["start_bar"] == mayor["start_bar"]][0]
    assert igual["zones_inside"] == 1
    assert igual["is_long"] and not igual["is_clean"], "deja de ser limpio"


def test_una_zona_FUERA_del_tramo_no_lo_ensucia():
    hi, lo = _zigzag([0, 20, 0, 200, 0])
    legs = detect(hi, lo, [], P)
    mayor = max(legs, key=lambda l: l["length_ticks"])
    fuera = dict(start_bar=mayor["end_bar"] + 5)
    assert zones_inside(mayor, [fuera]) == []


def test_una_zona_creada_ANTES_y_todavia_viva_no_cuenta():
    """El pedido distingue si el impulso GENERO zonas mientras corría."""
    leg = dict(start_bar=100, end_bar=150)
    previa = dict(start_bar=40, end_bar=200)      # existía antes y sigue viva
    assert zones_inside(leg, [previa]) == []


def test_el_censo_devuelve_TODOS_los_tramos_no_solo_los_marcados():
    hi, lo = _zigzag([0, 20, 0, 20, 0, 200, 0])
    legs = detect(hi, lo, [], P)
    c = census(legs)
    assert c["n"] == len(legs) > c["largos"] >= c["limpios"]
    assert "pct_limpios_entre_largos" in c


def test_min_leg_ticks_es_un_piso_absoluto():
    hi, lo = _zigzag([0, 5, 0, 5, 0, 5])
    legs = detect(hi, lo, [], dict(P, min_leg_ticks=1000))
    assert not any(l["is_long"] for l in legs)


def test_defaults_declarados():
    assert RESEARCH_DEFAULTS["top_pct"] == 5.0, "el 5 % más largo, textual"
    assert RESEARCH_DEFAULTS["window_legs"] == 200

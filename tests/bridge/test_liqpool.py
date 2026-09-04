"""LiqPool: contrato del detector de zonas de máximos/mínimos repetidos.

Estos tests fijan las decisiones que la literatura dictó
(`docs/research/H-LIQPOOL-ZB_ESTADO_DEL_ARTE_2026-09-03.md`) y las que evitan el
sesgo que arruina este tipo de objeto:

- nivel y banda de liquidez son objetos SEPARADOS y están de lados opuestos;
- una zona tocada NO se borra;
- `span_bars` y `excursion_ticks` distinguen microzona de zona separada;
- los pivotes son estrictos, para que un tramo plano no genere uno por barra.
"""
from edgelab.bridge.indicators.liqpool import (
    RESEARCH_DEFAULTS, build_zones, census, detect, find_pivots)


def _serie(picos, base=10_000, largo=60, altura=6):
    """Serie con máximos locales en las barras de `picos`, todos al mismo nivel."""
    hi = [base] * largo
    lo = [base - altura] * largo
    for b in picos:
        hi[b] = base + altura
        lo[b] = base - 1
    return hi, lo


def test_pivote_estricto_ignora_mesetas():
    """Con el tick grueso de ZB los empates abundan; un plano no es un pivote."""
    hi = [100, 101, 102, 102, 102, 101, 100]
    lo = [90] * 7
    assert find_pivots(hi, lo, 1) == [] or all(p[1] != "H" for p in find_pivots(hi, lo, 1))


def test_detecta_un_par_de_maximos_al_mismo_nivel():
    hi, lo = _serie([10, 30])
    z = build_zones(hi, lo, {"pivot_strength": 3, "min_pivots": 2})
    altos = [x for x in z if x["side"] == "H"]
    assert len(altos) == 1
    assert altos[0]["n_pivots"] == 2
    assert altos[0]["span_bars"] == 20


def test_min_pivots_filtra_como_dice():
    hi, lo = _serie([10, 30])
    assert [x for x in build_zones(hi, lo, {"min_pivots": 3}) if x["side"] == "H"] == []
    hi2, lo2 = _serie([10, 25, 40])
    z = [x for x in build_zones(hi2, lo2, {"min_pivots": 3}) if x["side"] == "H"]
    assert len(z) == 1 and z[0]["n_pivots"] == 3


def test_nivel_y_banda_estan_de_lados_opuestos():
    """La separación viene de Osler: TP en el nivel, stops MÁS ALLÁ.

    Mezclarlos en un solo rectángulo hace imposible separar rebote de cascada,
    que la literatura dice que son efectos opuestos.
    """
    hi, lo = _serie([10, 30])
    z = [x for x in build_zones(hi, lo, {"liquidity_band_ticks": 3}) if x["side"] == "H"][0]
    assert z["level_hi"] == z["level_tick"]
    assert z["band_lo"] > z["level_tick"], "la banda de un máximo va POR ENCIMA"
    assert z["band_hi"] - z["band_lo"] + 1 == 3
    # y para un mínimo, al revés
    zl = [x for x in build_zones(hi, lo, {"liquidity_band_ticks": 3}) if x["side"] == "L"]
    if zl:
        assert zl[0]["band_hi"] < zl[0]["level_tick"]


def test_microzona_vs_zona_separada_se_distinguen_por_los_dos_ejes():
    micro_hi, micro_lo = _serie([10, 14])          # picos juntos
    lejos_hi, lejos_lo = _serie([10, 45])          # picos lejanos
    m = [x for x in build_zones(micro_hi, micro_lo) if x["side"] == "H"][0]
    l = [x for x in build_zones(lejos_hi, lejos_lo) if x["side"] == "H"][0]
    assert m["span_bars"] < l["span_bars"]
    assert "excursion_ticks" in m and "excursion_ticks" in l


def test_la_zona_tocada_NO_se_borra():
    """El sesgo de supervivencia entra por acá si se borra al ser mitigada."""
    hi, lo = _serie([10, 30], largo=80)
    for b in range(50, 55):
        hi[b] = 10_000 + 6                          # vuelve a tocar el nivel
    z = detect(hi, lo, {"invalidation_ticks": 99})
    altos = [x for x in z if x["side"] == "H"]
    assert altos, "la zona debe seguir en el censo después del toque"
    assert altos[0]["touched_bar"] is not None
    assert altos[0]["state"] == "TOUCHED"


def test_barrida_se_marca_pero_tambien_queda():
    hi, lo = _serie([10, 30], largo=80)
    for b in range(50, 55):
        hi[b] = 10_000 + 40                         # atraviesa muy por encima
    altos = [x for x in detect(hi, lo, {"invalidation_ticks": 4}) if x["side"] == "H"]
    assert altos[0]["state"] == "SWEPT"
    assert altos[0]["swept_bar"] is not None


def test_expiracion_y_nunca_tocadas_quedan_en_el_censo():
    hi, lo = _serie([10, 30], largo=200)
    z = detect(hi, lo, {"max_age_bars": 20, "invalidation_ticks": 99})
    c = census(z)
    assert c["n"] > 0
    assert "nunca_tocadas" in c, "el censo debe contar las que el ojo no ve"


def test_confluencia_con_numero_redondo():
    hi, lo = _serie([10, 30], base=10_000)          # 10000 % 32 = 16 -> lejos
    z = [x for x in build_zones(hi, lo, {"round_ticks": 32}) if x["side"] == "H"][0]
    assert 0 <= z["round_confluence_ticks"] <= 16


def test_defaults_declarados():
    assert RESEARCH_DEFAULTS["pivot_strength"] == 3
    assert RESEARCH_DEFAULTS["min_pivots"] == 2
    assert RESEARCH_DEFAULTS["round_ticks"] == 32, "ZB: 32 ticks = 1 punto"

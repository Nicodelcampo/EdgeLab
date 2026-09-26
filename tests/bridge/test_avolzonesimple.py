"""AVolZoneSimple: contrato de la definición y de su estabilidad.

Estos tests fijan lo que hace que el indicador sea barrible y reproducible:
aritmética entera, sin estado, empates deterministas, y la propiedad que
justifica el rediseño — que un contrato de diferencia no mueva la zona.
"""
from edgelab.bridge.indicators.avolzonesimple import (
    RESEARCH_DEFAULTS, concentration, detect_block, narrowest_area, sweep_grid)


def _bloque(pico_lo=100_010, pico_hi=100_018, cola=3, pico=60, n=90):
    """Bloque con núcleo NO plano.

    El pico se hace triangular a propósito: una meseta perfectamente plana crea
    empates exactos de ancho y volumen entre ventanas vecinas, y ahí sí un
    contrato puede correr la zona un tick. Los bloques reales no son planos —por
    eso el turnover medido sobre los 22.507 bloques es 4,97 % y no 0 %— pero la
    distinción hay que dejarla escrita, no esconderla en un fixture cómodo.
    """
    cells = {100_000 + i: cola for i in range(n)}
    centro = (pico_lo + pico_hi) // 2
    for t in range(pico_lo, pico_hi + 1):
        cells[t] = pico - 4 * abs(t - centro)
    return cells


def test_la_zona_es_el_rango_mas_angosto_con_el_porcentaje():
    cells = _bloque()
    lo, hi, zvol, total, span = narrowest_area(cells, 30, 12)
    assert lo >= 100_010 and hi <= 100_018, "debe caer sobre el pico"
    assert zvol * 100 >= total * 30, "tiene que alcanzar el porcentaje pedido"
    assert (hi - lo + 1) <= 12


def test_aritmetica_entera_en_la_decision():
    r = detect_block(_bloque(), close_tick=100_050)
    for k in ("zone_ticks", "zone_volume", "block_volume", "block_ticks", "concentration"):
        assert isinstance(r[k], int), f"{k} debe ser entero"


def test_concentracion_1000_es_uniforme():
    # 10 ticks de zona en 100 de bloque con el 10% del volumen -> exactamente uniforme
    assert concentration(zone_vol=100, block_vol=1000, zone_ticks=10, block_ticks=100) == 1000
    assert concentration(zone_vol=200, block_vol=1000, zone_ticks=10, block_ticks=100) == 2000


def test_no_depende_del_orden_de_insercion():
    cells = _bloque()
    a = detect_block(cells, close_tick=100_050)
    b = detect_block(dict(reversed(list(cells.items()))), close_tick=100_050)
    assert a == b


def test_sin_estado_entre_llamadas():
    cells = _bloque()
    primera = detect_block(cells, close_tick=100_050)
    for _ in range(5):
        detect_block(_bloque(pico_lo=100_040, pico_hi=100_048), close_tick=100_000)
    assert detect_block(cells, close_tick=100_050) == primera


def test_abstiene_cuando_no_entra_en_el_ancho():
    plano = {100_000 + i: 10 for i in range(200)}      # volumen repartido
    r = detect_block(plano, {"max_zone_ticks": 5})
    assert r["decision"] == "ABSTAIN_TOO_WIDE"


def test_abstiene_por_concentracion_baja_pero_publica_la_geometria():
    plano = {100_000 + i: 10 for i in range(60)}
    r = detect_block(plano, {"max_zone_ticks": 60, "min_concentration": 5000})
    assert r["decision"] == "ABSTAIN_LOW_CONCENTRATION"
    assert r["lower_tick"] is not None, "el bloque debe quedar auditable igual"


def test_lado_respecto_del_cierre():
    cells = _bloque()
    r = detect_block(cells, close_tick=100_090)
    assert r["side"] == "SUPPORT" and r["distance_ticks"] > 0
    assert detect_block(cells, close_tick=99_990)["side"] == "RESISTANCE"
    dentro = (r["lower_tick"] + r["upper_tick"]) // 2
    assert detect_block(cells, close_tick=dentro)["side"] == "AT_PRICE"


def test_un_contrato_mueve_la_zona_a_lo_sumo_un_tick():
    """La propiedad real del diseño, dicha con precisión.

    La regla vieja tenía, en el 89,60 % de los bloques reales, una celda a un
    contrato del umbral `mediana × 2`: ahí un contrato cambiaba el conjunto hot
    y el clustering por gap podía fusionar o partir clusters, moviendo la zona
    arbitrariamente.

    Acá **la zona no es invariante**, y conviene decirlo: sumar un contrato sube
    el volumen del bloque, y con él `necesario = techo(total × share / 100)`.
    Cuando ese entero cruza, la ventana ganadora puede correrse. Lo que sí está
    acotado es CUÁNTO: un tick, porque la ventana es contigua y ordenada por
    ancho. Sobre los 22.507 bloques reales eso da 4,97 % de turnover por
    igualdad exacta — ver `docs/research/avolzonesimple_20260903/`.
    """
    cells = _bloque()
    base = detect_block(cells, close_tick=100_090)
    assert base["decision"] == "CREATE"
    for t in sorted(cells):
        movido = dict(cells)
        movido[t] += 1
        r = detect_block(movido, close_tick=100_090)
        assert r["decision"] == "CREATE", f"un contrato en {t} cambió la decisión"
        assert abs(r["lower_tick"] - base["lower_tick"]) <= 1, f"tick {t}"
        assert abs(r["upper_tick"] - base["upper_tick"]) <= 1, f"tick {t}"
        assert r["zone_ticks"] == base["zone_ticks"], f"el ancho no debe cambiar (tick {t})"



def test_una_meseta_plana_si_puede_correrse_un_tick():
    """Límite honesto del diseño, y medido: con empates exactos hay indeterminación.

    Es parte del residuo de 4,97 % que la definición NO elimina. Queda escrito
    como test para que nadie lo descubra como sorpresa en una campaña.
    """
    plana = {100_000 + i: 3 for i in range(90)}
    for t in range(100_010, 100_019):
        plana[t] = 60                      # meseta perfectamente plana
    base = detect_block(plana, close_tick=100_090)
    movido = dict(plana)
    movido[100_014] += 1
    r = detect_block(movido, close_tick=100_090)
    assert r["decision"] == base["decision"] == "CREATE"
    assert abs(r["lower_tick"] - base["lower_tick"]) <= 1, "a lo sumo un tick"



def test_el_barrido_devuelve_el_landscape_completo():
    bloques = [_bloque(pico_lo=100_010 + i, pico_hi=100_018 + i) for i in range(20)]
    grid = [{"area_share_pct": s, "min_concentration": c}
            for s in (25, 30) for c in (1500, 2000)]
    out = sweep_grid(bloques, grid)
    assert len(out) == 4, "una fila por celda de la grilla, sin seleccionar"
    for row in out:
        assert row["n_blocks"] == 20
        assert sum(row["decisions"].values()) == 20


def test_defaults_declarados():
    assert RESEARCH_DEFAULTS == dict(bars_per_block=10, area_share_pct=30,
                                     max_zone_ticks=12, min_concentration=1500)

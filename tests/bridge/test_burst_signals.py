"""Señales por racha de ráfagas de `HFTImpulseZones_P`.

Estos tests fijan las dos decisiones de diseño que hacen que el conteo signifique
algo, y que son fáciles de romper sin notarlo:

1. sólo cuentan ráfagas **no solapadas** — si no, una racha de 12 sería el mismo
   impulso visto doce veces;
2. **una señal por racha** — si no, la población queda dominada por las rachas
   largas, que contarían muchas veces cada una.

Más los tres cortes de la racha: dirección, distancia entre ráfagas y sesión.
"""
from edgelab.bridge.indicators.parity_first import detect_burst_signals


def _impulso(desde, ticks_por_barra=3, barras=12):
    """Un tramo recto: dispara impulso con eficiencia 10000 bps."""
    return list(range(desde, desde + barras * ticks_por_barra, ticks_por_barra))


def _quieto(precio, barras=12):
    return [precio] * barras


def _serie(closes):
    return closes, [c + 1 for c in closes], [c - 1 for c in closes], [10] * len(closes)


def _tres_rafagas_alcistas():
    c = []
    for k in range(3):
        c += _impulso(100 + k * 40) + _quieto(100 + k * 40 + 33)
    return _serie(c)


def test_tres_rafagas_no_solapadas_dan_una_senal():
    c, h, l, v = _tres_rafagas_alcistas()
    s = detect_burst_signals(c, h, l, v)
    assert len(s) == 1
    assert s[0]["direction"] == 1
    assert s[0]["burst_count"] == 3
    assert s[0]["burst_displacement_ticks"] >= 48


def test_una_sola_senal_por_racha_aunque_la_racha_siga():
    """Cuatro y cinco ráfagas siguen siendo UN evento, no dos ni tres."""
    for n in (4, 5, 6):
        c = []
        for k in range(n):
            c += _impulso(100 + k * 40) + _quieto(100 + k * 40 + 33)
        s = detect_burst_signals(*_serie(c))
        assert len(s) == 1, f"con {n} ráfagas deberían seguir siendo 1 señal"


def test_las_rafagas_solapadas_no_inflan_la_racha():
    """Un único movimiento largo dispara en muchas barras consecutivas.

    Si se contaran todas, cualquier tendencia sostenida daría una racha enorme
    sin que haya más mercado. Con el conteo no solapado, un tramo recto de 24
    barras aporta a lo sumo dos ráfagas, así que no alcanza el umbral de tres.
    """
    c = _impulso(100, barras=24) + _quieto(100 + 23 * 3)
    s = detect_burst_signals(*_serie(c))
    assert s == [], "un solo movimiento no debería ser una racha de muchas ráfagas"


def test_cambiar_de_direccion_corta_la_racha():
    c = _impulso(100) + _quieto(133)
    c += list(range(133, 133 - 12 * 3, -3)) + _quieto(100)      # bajista
    c += _impulso(100) + _quieto(133)
    s = detect_burst_signals(*_serie(c))
    assert s == [], "dos alcistas separadas por una bajista no son racha de tres"


def test_la_distancia_maxima_corta_la_racha():
    c = []
    for k in range(3):
        c += _impulso(100 + k * 40) + _quieto(100 + k * 40 + 33, barras=200)
    s = detect_burst_signals(*_serie(c), params={"max_bars_between_bursts": 20})
    assert s == [], "con ráfagas muy separadas la racha no debería sostenerse"


def test_la_racha_no_cruza_la_frontera_de_sesion():
    c, h, l, v = _tres_rafagas_alcistas()
    sin_sesiones = detect_burst_signals(c, h, l, v)
    assert len(sin_sesiones) == 1
    # la misma serie, partida en dos sesiones justo en el medio
    ses = [0] * (len(c) // 2) + [1] * (len(c) - len(c) // 2)
    con_corte = detect_burst_signals(c, h, l, v, session_ids=ses)
    assert len(con_corte) == 0, "la racha no debe sobrevivir al cambio de sesión"


def test_el_desplazamiento_minimo_filtra_rachas_de_ruido():
    c, h, l, v = _tres_rafagas_alcistas()
    assert detect_burst_signals(c, h, l, v,
                                params={"min_burst_displacement_ticks": 10_000}) == []


def test_min_bursts_mueve_CUANDO_dispara_la_racha_no_cuantas_senales_hay():
    """Semántica de `min_bursts_for_signal`, que es fácil de leer al revés.

    NO significa «una señal por ráfaga». La regla «una señal por racha» manda: con
    umbral 1 la racha dispara en su PRIMERA ráfaga en vez de en la tercera, pero
    sigue siendo un solo evento. Lo que el parámetro cambia es *qué rachas
    califican* y *en qué momento* se emiten — no cuántas señales genera una racha.

    Para el barrido esto importa: bajarlo agranda la población porque entran
    rachas que nunca habrían llegado a tres, no porque las rachas largas cuenten
    más veces.
    """
    c, h, l, v = _tres_rafagas_alcistas()
    s = detect_burst_signals(c, h, l, v, params={"min_bursts_for_signal": 1,
                                                 "min_burst_displacement_ticks": 0})
    assert len(s) == 1, "sigue siendo UNA racha, y una racha emite una vez"
    assert s[0]["burst_count"] == 1, "pero dispara en la primera ráfaga, no en la tercera"
    assert s[0]["bar"] < detect_burst_signals(c, h, l, v)[0]["bar"], "y dispara antes"


def test_la_senal_publica_la_zona_que_la_disparo():
    c, h, l, v = _tres_rafagas_alcistas()
    s = detect_burst_signals(c, h, l, v)[0]
    assert s["zone_lower_tick"] < s["zone_upper_tick"]
    assert s["burst_first_bar"] < s["bar"]
    assert isinstance(s["burst_displacement_ticks"], int)

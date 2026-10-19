"""Rechazo en bordes de cluster: fija las decisiones del canal direccional.

Lo que se clava acá, más que la aritmética: que un contacto no se cuente varias veces,
que el desenlace se resuelva por lo que pasa **primero**, que los indefinidos queden
fuera del denominador, y que el contraste se lea estratificado y no agregado.
"""
import pytest

from edgelab.research import cluster_rejection as cr

P = cr._p()


def _b(lo, hi, close=None):
    return dict(lo=lo, hi=hi, close=close if close is not None else hi)


# ------------------------------------------------------------------ contactos

def test_un_contacto_exige_venir_DE_LEJOS():
    """Tocar un nivel a un tick de distancia no es una aproximación."""
    barras = [_b(100, 100, 100), _b(100, 101, 101)]
    assert cr.contactos(barras, 1, dict(P, dist_min_ticks=4)) == []
    barras = [_b(100, 100, 100), _b(100, 110, 110)]
    niveles = [tk for tk, _ in cr.contactos(barras, 1, dict(P, dist_min_ticks=4))]
    assert 104 in niveles and 110 in niveles
    assert 101 not in niveles, "a 1 tick del close previo no cuenta"


def test_un_nivel_ya_tocado_NO_vuelve_a_contar():
    """Si no, la misma aproximación se cuenta muchas veces y N se infla sin información."""
    barras = [_b(100, 110, 110), _b(100, 100, 100), _b(100, 110, 110)]
    niveles = [tk for tk, _ in cr.contactos(barras, 2, dict(P, ventana_previa=30))]
    assert niveles == [], "todos esos niveles se tocaron en la barra 0"


def test_el_lado_dice_desde_donde_vino():
    barras = [_b(100, 100, 100), _b(100, 120, 120)]
    lados = dict(cr.contactos(barras, 1, P))
    assert lados[115] == 1, "subiendo"
    barras = [_b(200, 200, 200), _b(180, 200, 180)]
    lados = dict(cr.contactos(barras, 1, P))
    assert lados[185] == -1, "bajando"


# ------------------------------------------------------------------ desenlace

def test_rechazo_es_volver_por_donde_vino():
    barras = [_b(100, 100, 100), _b(100, 110, 110)]
    barras += [_b(104, 108, 105)]          # vuelve 6 ticks abajo del nivel 110
    d = cr.desenlace(barras, 1, nivel=110, lado=1, p=dict(P, retro_ticks=4))
    assert d == "rechaza"


def test_cruce_es_seguir_de_largo():
    barras = [_b(100, 100, 100), _b(100, 110, 110), _b(112, 116, 115)]
    d = cr.desenlace(barras, 1, nivel=110, lado=1, p=dict(P, penetracion_ticks=4))
    assert d == "cruza"


def test_se_resuelve_por_LO_QUE_PASA_PRIMERO():
    """No por dónde queda el precio al final: eso dependería del horizonte, que es un
    parámetro nuestro, no del mercado."""
    barras = [_b(100, 100, 100), _b(100, 110, 110)]
    barras += [_b(105, 106, 106)]           # primero rechaza
    barras += [_b(114, 120, 118)]           # despues cruza
    assert cr.desenlace(barras, 1, 110, 1, dict(P, retro_ticks=4,
                                                penetracion_ticks=4)) == "rechaza"


def test_indefinido_cuando_no_pasa_ninguna_de_las_dos():
    barras = [_b(100, 100, 100), _b(100, 110, 110)]
    barras += [_b(109, 111, 110) for _ in range(5)]
    assert cr.desenlace(barras, 1, 110, 1, dict(P, horizonte=5)) == "indefinido"


def test_sin_horizonte_devuelve_None():
    barras = [_b(100, 100, 100), _b(100, 110, 110)]
    assert cr.desenlace(barras, 1, 110, 1, P) is None


# ------------------------------------------------------------------ borde vs dentro

def test_borde_y_dentro_son_objetos_DISTINTOS():
    """La hipótesis es sobre los extremos. Un nivel del medio es otra cosa."""
    cl = [dict(lower_tk=100, upper_tk=120)]
    assert cr.es_borde_de_cluster(100, cl) and cr.es_borde_de_cluster(120, cl)
    assert not cr.es_borde_de_cluster(110, cl), "el medio no es borde"
    assert cr.esta_dentro(110, cl)


def test_la_tolerancia_del_borde_es_explicita():
    cl = [dict(lower_tk=100, upper_tk=120)]
    assert cr.es_borde_de_cluster(101, cl, tolerancia=1)
    assert not cr.es_borde_de_cluster(103, cl, tolerancia=1)


# ------------------------------------------------------------------ la tabla

def _m(borde, des, dist=10, sigma=1.0):
    return dict(borde=borde, desenlace=des, distancia=dist, sigma=sigma)


def test_los_INDEFINIDOS_quedan_fuera_del_denominador():
    """Meterlos adentro haría que la tasa dependa del horizonte elegido."""
    ms = ([_m(True, "rechaza")] * 3 + [_m(True, "cruza")] * 1
          + [_m(True, "indefinido")] * 96)
    a = cr.agregado(ms)
    assert a["borde"]["n"] == 4
    assert a["borde"]["rechazo"] == pytest.approx(0.75)
    assert a["borde"]["indefinidos"] == 96


def test_la_tabla_contrasta_borde_contra_no_borde_DENTRO_del_estrato():
    ms = ([_m(True, "rechaza", dist=5)] * 40 + [_m(True, "cruza", dist=5)] * 60
          + [_m(False, "rechaza", dist=5)] * 20 + [_m(False, "cruza", dist=5)] * 80)
    t = cr.tabla(ms, P)
    assert len(t) == 1
    f = t[0]
    assert f["rechazo_borde"] == pytest.approx(0.4)
    assert f["rechazo_sin_borde"] == pytest.approx(0.2)
    assert f["contraste"] == pytest.approx(0.2)
    assert f["suficiente"] is True


def test_un_estrato_flaco_se_publica_igual_pero_marcado():
    ms = [_m(True, "rechaza", dist=5)] * 5 + [_m(False, "cruza", dist=5)] * 5
    t = cr.tabla(ms, P, minimo=30)
    assert t[0]["suficiente"] is False
    assert t[0]["n_borde"] == 5


def test_el_agregado_puede_MENTIR_respecto_del_estratificado():
    """Paradoja de Simpson. Con exposición al cluster dependiente de la distancia no
    es un riesgo teórico: por eso el agregado se publica junto a la tabla, nunca solo.
    """
    ms = []
    # estrato CERCA, tasas altas: pocos contactos en borde, muchos sin borde
    ms += [_m(True, "rechaza", dist=5)] * 9 + [_m(True, "cruza", dist=5)] * 1
    ms += [_m(False, "rechaza", dist=5)] * 80 + [_m(False, "cruza", dist=5)] * 20
    # estrato LEJOS, tasas bajas: al reves, muchos en borde y pocos sin borde
    ms += [_m(True, "rechaza", dist=50)] * 20 + [_m(True, "cruza", dist=50)] * 80
    ms += [_m(False, "rechaza", dist=50)] * 1 + [_m(False, "cruza", dist=50)] * 9
    t = cr.tabla(ms, P, minimo=1)
    assert all(f["contraste"] > 0 for f in t), "en CADA estrato el borde rechaza mas"
    a = cr.agregado(ms)
    assert a["contraste"] < 0, "y sin embargo el agregado da al reves"


# ------------------------------------------------- escalon 5

def test_borde_de_devuelve_CUAL_cluster_es():
    """Sin saber cuál, no se puede medir hace cuánto que no se actualiza."""
    cl = [dict(lower_tk=100, upper_tk=120, ultima=5),
          dict(lower_tk=200, upper_tk=220, ultima=9)]
    assert cr.borde_de(200, cl)["ultima"] == 9
    assert cr.borde_de(110, cl) is None, "el interior no es borde"


def _mi(borde, des, intensidad):
    return dict(borde=borde, categoria="borde" if borde else "libre",
                desenlace=des, distancia=10, sigma=1.0, intensidad=intensidad)


def test_estratificar_por_intensidad_puede_APAGAR_el_contraste():
    """El punto del escalón 5.

    Si el contraste agregado sale de que los bordes viven en régimen de alta actividad
    y en ese régimen el precio rechaza más, estratificando desaparece. Este fixture
    construye exactamente ese caso: dentro de cada estrato el contraste es cero.
    """
    ms = []
    # intensidad BAJA: casi todo libre, tasa de rechazo 20 %
    ms += [_mi(False, "rechaza", 1)] * 200 + [_mi(False, "cruza", 1)] * 800
    ms += [_mi(True, "rechaza", 1)] * 2 + [_mi(True, "cruza", 1)] * 8
    # intensidad ALTA: casi todo borde, tasa 80 % — pero igual para los dos
    ms += [_mi(False, "rechaza", 100)] * 8 + [_mi(False, "cruza", 100)] * 2
    ms += [_mi(True, "rechaza", 100)] * 800 + [_mi(True, "cruza", 100)] * 200

    ag = cr.agregado(ms)
    assert ag["contraste"] > 0.4, "el agregado muestra un efecto grande"
    t = cr.tabla_por(ms, "intensidad", cr.DEFAULTS["bordes_intensidad"], minimo=1)
    for f in t:
        assert abs(f["contraste"]) < 1e-9, "y dentro de cada estrato no hay nada"


def test_el_holdout_exige_que_el_objeto_no_se_haya_movido():
    assert cr.DEFAULTS["lag_holdout"] == 30
    assert cr.DEFAULTS["ventana_intensidad"] == 100


# --- agregado_limpio: el control no puede incluir el interior del cluster ---

def _c(cat, des, lag=None):
    d = dict(categoria=cat, borde=(cat == "borde"), desenlace=des,
             distancia=5.0, sigma=3.0, intensidad=10)
    if lag is not None:
        d["lag"] = lag
    return d


def test_agregado_limpio_excluye_el_interior_del_control():
    # 'dentro' rechaza poco; si entra al control, infla el contraste.
    ms = ([_c("borde", "rechaza")] * 6 + [_c("borde", "cruza")] * 4 +
          [_c("libre", "rechaza")] * 5 + [_c("libre", "cruza")] * 5 +
          [_c("dentro", "rechaza")] * 1 + [_c("dentro", "cruza")] * 9)
    limpio = cr.agregado_limpio(ms)
    sucio = cr.agregado(ms)
    assert limpio["borde"]["n"] == 10 and limpio["libre"]["n"] == 10
    assert limpio["dentro"]["n"] == 10
    assert limpio["contraste"] == pytest.approx(0.6 - 0.5)
    # el agregado por booleano mezcla libre con dentro y da otro numero
    assert sucio["sin_borde"]["n"] == 20
    assert sucio["contraste"] == pytest.approx(0.6 - 0.3)
    assert limpio["contraste"] < sucio["contraste"]


def test_agregado_limpio_sin_libres_no_inventa_contraste():
    ms = [_c("borde", "rechaza"), _c("dentro", "cruza")]
    assert cr.agregado_limpio(ms)["contraste"] is None


# --- contraste_lag: fresco vs rancio ---

def test_contraste_lag_separa_fresco_de_rancio():
    ms = ([_c("borde", "rechaza", lag=1)] * 80 + [_c("borde", "cruza", lag=1)] * 20 +
          [_c("borde", "rechaza", lag=50)] * 30 + [_c("borde", "cruza", lag=50)] * 70 +
          [_c("libre", "rechaza")] * 50 + [_c("libre", "cruza")] * 50)
    r = cr.contraste_lag(ms, lag=30, deff=1.0)
    assert r["fresco"]["n"] == 100 and r["fresco"]["rechazo"] == pytest.approx(0.8)
    assert r["rancio"]["n"] == 100 and r["rancio"]["rechazo"] == pytest.approx(0.3)
    assert r["libre"]["n"] == 100
    assert r["fresco"]["contraste"] == pytest.approx(0.3)
    assert r["rancio"]["contraste"] == pytest.approx(-0.2)
    assert r["diferencia"]["valor"] == pytest.approx(0.5)
    assert r["diferencia"]["z"] > 5.0
    assert r["diferencia"]["p_valor"] < 1e-6


def test_contraste_lag_deff_ensancha_el_error():
    ms = ([_c("borde", "rechaza", lag=1)] * 60 + [_c("borde", "cruza", lag=1)] * 40 +
          [_c("borde", "rechaza", lag=99)] * 40 + [_c("borde", "cruza", lag=99)] * 60 +
          [_c("libre", "rechaza")] * 50 + [_c("libre", "cruza")] * 50)
    a = cr.contraste_lag(ms, lag=30, deff=1.0)
    b = cr.contraste_lag(ms, lag=30, deff=5.0)
    assert a["diferencia"]["valor"] == pytest.approx(b["diferencia"]["valor"])
    assert b["diferencia"]["se"] == pytest.approx(a["diferencia"]["se"] * 5 ** 0.5)
    assert abs(b["diferencia"]["z"]) < abs(a["diferencia"]["z"])


def test_contraste_lag_ignora_bordes_sin_lag_y_los_indefinidos():
    ms = ([_c("borde", "rechaza", lag=1)] * 10 + [_c("borde", "rechaza")] * 99 +
          [_c("borde", "indefinido", lag=1)] * 99 + [_c("libre", "cruza")] * 10)
    r = cr.contraste_lag(ms, lag=30)
    assert r["fresco"]["n"] == 10
    assert r["rancio"]["n"] == 0
    assert r["rancio"]["contraste"] is None

"""HFTClusterZones: clusters de zonas HFT por halo gaussiano.

Fija las decisiones que definen el objeto, y **clava las rarezas del `.cs`** que este
módulo replica a propósito para servir de oráculo de paridad. Un test que falla acá
significa una de dos cosas: o se rompió el espejo, o el original cambió y hay que
volver a mirarlo. No relajar el test sin averiguar cuál de las dos.
"""
import math

import pytest

from edgelab.bridge.indicators.hftclusterzones import (
    ACTIVE, DEPLETED, EXPIRED, INVALIDATED, RESEARCH_DEFAULTS, TOUCHED_POC,
    ClusterEngine, as_of, census, halo_density, segment_islands)

TICK = 0.25


def _z(lower_tk, upper_tk, start_bar=0, vol=100.0, cvd=0.0):
    return dict(lower=lower_tk * TICK, upper=upper_tk * TICK,
                start_bar=start_bar, total_vol=vol, cvd=cvd)


def _motor(**over):
    # min_density 1.5: con dos zonas apiladas la densidad maxima es 2.0, asi que el
    # default de 3.0 no dispararia ningun cluster en fixtures de dos zonas.
    p = dict(min_capacity_volume=100.0, max_age_bars=500, min_density=1.5)
    p.update(over)
    return ClusterEngine(TICK, p)


# ---------------------------------------------------------------- campo de halo

def test_una_zona_sola_no_hace_campo():
    """Hace falta confluencia. Una zona no es una aglomeración."""
    d, _ = halo_density([_z(100, 101)], TICK)
    assert d == {}


def test_el_peso_es_maximo_DENTRO_de_la_zona_y_decae_afuera():
    zonas = [_z(100, 104), _z(100, 104)]
    d, _ = halo_density(zonas, TICK, dict(min_density=0.0, halo_sigma_ticks=3.0))
    # dentro del rango, distancia 0 -> peso 1 por zona
    assert d[102] == pytest.approx(2.0)
    assert d[100] == pytest.approx(2.0)
    # afuera decae de forma monótona
    assert d[104] > d[106] > d[108] > 0


def test_el_kernel_decae_como_gaussiana():
    zonas = [_z(100, 100), _z(100, 100)]
    p = dict(min_density=0.0, halo_sigma_ticks=2.0)
    d, _ = halo_density(zonas, TICK, p)
    assert d[105] == pytest.approx(2 * math.exp(-25 / 8))   # 5 ticks
    assert d[106] == pytest.approx(2 * math.exp(-36 / 8))   # 6 ticks


def test_la_ENVOLVENTE_recorta_el_kernel_antes_que_su_propio_corte():
    """Hallazgo del espejo, replicado del original: los dos radios no coinciden.

    El kernel dice aportar hasta `kernel_cutoff_sigmas` (3.5σ), pero la grilla se
    construye con `envelope_sigmas` (3.0σ) alrededor de las zonas. Los 0.5σ de afuera
    nunca se evalúan. No es un bug del espejo: es lo que hace el `.cs`, y hay que
    saberlo antes de interpretar el ancho de un cluster de borde.
    """
    zonas = [_z(100, 100), _z(100, 100)]
    p = dict(min_density=0.0, halo_sigma_ticks=2.0)
    d, _ = halo_density(zonas, TICK, p)
    assert max(d) == 106, "3σ = 6 ticks, aunque el corte del kernel sea 7"
    assert 107 not in d


def test_min_density_es_el_umbral_que_dispara_el_cluster():
    zonas = [_z(100, 100), _z(100, 100), _z(100, 100)]
    alto, _ = halo_density(zonas, TICK, dict(min_density=2.99))
    bajo, _ = halo_density(zonas, TICK, dict(min_density=3.01))
    assert 100 in alto and 100 not in bajo, "tres zonas apiladas dan densidad 3.0"


def test_sigma_ensancha_el_cluster():
    """σ es un parámetro de investigación, no de dibujo: cambia el objeto."""
    zonas = [_z(100, 100), _z(100, 100), _z(100, 100)]
    angosto, _ = halo_density(zonas, TICK, dict(halo_sigma_ticks=1.0, min_density=1.5))
    ancho, _ = halo_density(zonas, TICK, dict(halo_sigma_ticks=6.0, min_density=1.5))
    assert len(ancho) > len(angosto)


# ---------------------------------------------------------------- islas y POC

def test_las_islas_se_cortan_por_hueco():
    assert segment_islands([1, 2, 3, 7, 8]) == [[1, 2, 3], [7, 8]]
    assert segment_islands([1, 2, 4, 5], gap=1) == [[1, 2], [4, 5]]
    assert segment_islands([1, 2, 4, 5], gap=2) == [[1, 2, 4, 5]]


def test_el_POC_es_la_maxima_densidad__no_el_maximo_volumen():
    """El desempate por volumen es sólo eso: un desempate.

    Con σ ancho el campo es unimodal y el POC cae en el **centro geométrico** de las
    zonas, no en la de más volumen. Conviene tenerlo claro antes de interpretar el POC
    como "el nivel donde está el dinero": no lo es.
    """
    zonas = [_z(100, 100, vol=10.0), _z(110, 110, vol=1000.0)]
    m = _motor(min_density=0.9, halo_sigma_ticks=8.0, min_capacity_volume=1.0)
    ev = m.on_zone_created(zonas, bar=10)
    assert ev, "tiene que nacer al menos un cluster"
    assert round(ev[0]["poc"] / TICK) == 105, "el centro, pese a los 1000 contratos"


def test_el_desempate_por_volumen_actua_cuando_la_densidad_EMPATA():
    """Dos picos idénticos y aislados: ahí sí manda el volumen ponderado.

    σ chico y corte del kernel a 1.75 ticks hacen que ninguna zona alcance a la otra,
    así que ambos ticks valen exactamente 1.0. `gap_ticks=2` los une en una sola isla
    para forzar el empate dentro del mismo cluster.
    """
    zonas = [_z(100, 100, vol=10.0), _z(102, 102, vol=1000.0)]
    m = _motor(min_density=0.5, halo_sigma_ticks=0.5, gap_ticks=2,
               min_capacity_volume=1.0)
    ev = m.on_zone_created(zonas, bar=10)
    assert ev, "tiene que nacer un cluster"
    assert round(ev[0]["poc"] / TICK) == 102, "gana el tick con mas volumen detras"


# ---------------------------------------------------------------- ciclo de vida

def test_nace_activo_y_registra_sus_contribuyentes():
    zonas = [_z(100, 102, vol=500.0), _z(101, 103, vol=500.0)]
    m = _motor()
    ev = m.on_zone_created(zonas, bar=5)[0]
    assert ev["event"] == "CLUSTER_CREATED"
    assert ev["state"] == ACTIVE
    assert ev["contributing_zones"] == 2
    assert ev["seed_volume"] == 1000.0
    assert ev["capacity_volume"] == 1000.0 * RESEARCH_DEFAULTS["capacity_multiplier"]


def test_el_toque_del_POC_no_mata_al_cluster():
    """Es el evento de interés, no un desenlace. El cluster sigue consumiendo."""
    m = _motor()
    c = m.on_zone_created([_z(100, 104, vol=10.0), _z(100, 104, vol=10.0)], bar=1)[0]
    ev = m.on_tick(c["poc"], vol=1.0, side=1, bar=2)
    assert [e["event"] for e in ev] == ["CLUSTER_TOUCHED_POC"]
    assert m.clusters[0]["state"] == TOUCHED_POC
    assert m.remaining_pct(m.clusters[0]) > 0


def test_muere_DEPLETED_cuando_se_consume_la_capacidad():
    m = _motor(min_capacity_volume=50.0)
    c = m.on_zone_created([_z(100, 104, vol=1.0), _z(100, 104, vol=1.0)], bar=1)[0]
    assert c["capacity_volume"] == 50.0
    m.on_tick(101 * TICK, vol=49.0, side=1, bar=2)
    assert m.clusters[0]["state"] != DEPLETED
    ev = m.on_tick(101 * TICK, vol=1.0, side=1, bar=3)
    assert any(e["event"] == "CLUSTER_DEPLETED" for e in ev)


def test_muere_INVALIDATED_solo_si_la_capacidad_NO_estaba_casi_agotada():
    """La regla del original: perforar un cluster ya consumido no lo invalida.

    Importa para el análisis de riesgos competitivos: un cluster muy operado que
    después se perfora **no** entra en la incidencia de invalidación, y si nadie mira
    esto, esa incidencia queda sesgada hacia abajo.
    """
    zonas = [_z(100, 104, vol=1.0), _z(100, 104, vol=1.0)]

    virgen = _motor(min_capacity_volume=100.0, invalidation_ticks=2)
    virgen.on_zone_created(zonas, bar=1)
    ev = virgen.on_tick(120 * TICK, vol=1.0, side=1, bar=2)
    assert any(e["event"] == "CLUSTER_INVALIDATED" for e in ev)

    gastado = _motor(min_capacity_volume=100.0, invalidation_ticks=2)
    gastado.on_zone_created(zonas, bar=1)
    gastado.on_tick(101 * TICK, vol=85.0, side=1, bar=2)   # 85 % de capacidad
    ev = gastado.on_tick(120 * TICK, vol=1.0, side=1, bar=3)
    assert not any(e["event"] == "CLUSTER_INVALIDATED" for e in ev)


def test_muere_EXPIRED_por_edad_medida_desde_el_NACIMIENTO():
    m = _motor(max_age_bars=10)
    c = m.on_zone_created([_z(100, 104), _z(100, 104)], bar=1)[0]
    assert m.on_bar(c["start_bar"] + 10) == []
    ev = m.on_bar(c["start_bar"] + 11)
    assert [e["event"] for e in ev] == ["CLUSTER_EXPIRED"]


def test_un_cluster_muerto_ya_no_consume():
    m = _motor(min_capacity_volume=10.0)
    m.on_zone_created([_z(100, 104, vol=1.0), _z(100, 104, vol=1.0)], bar=1)
    m.on_tick(101 * TICK, vol=10.0, side=1, bar=2)
    assert m.clusters[0]["state"] == DEPLETED
    antes = m.clusters[0]["volume_inside"]
    m.on_tick(101 * TICK, vol=999.0, side=1, bar=3)
    assert m.clusters[0]["volume_inside"] == antes


# ------------------------------------------------- rarezas del .cs, clavadas

def test_PARIDAD_la_expansion_usa_marcas_de_agua_que_nunca_bajan():
    """Por esto el estado final NO es evidencia admisible.

    Un cluster que se expande se queda con el máximo histórico de densidad, volumen
    semilla y capacidad. Leer el objeto al final del gráfico devuelve un cluster que
    nunca existió con esos valores simultáneamente.
    """
    m = _motor()
    m.on_zone_created([_z(100, 104, vol=1000.0), _z(100, 104, vol=1000.0)], bar=1)
    pico = m.clusters[0]["peak_density"]
    cap = m.clusters[0]["capacity_volume"]

    # segunda evaluación, con zonas mas flojas que se solapan
    m.on_zone_created([_z(103, 106, vol=1.0), _z(103, 106, vol=1.0)], bar=2)
    assert m.clusters[0]["peak_density"] >= pico
    assert m.clusters[0]["capacity_volume"] == cap, "la capacidad no baja"
    assert len(m.clusters) == 1, "se expandió, no nació otro"


def test_PARIDAD_un_cluster_EXPIRED_todavia_puede_expandirse():
    """Rareza real del original: el filtro de expansión no excluye EXPIRED.

    No revive —su estado sigue siendo EXPIRED y no vuelve a consumir— pero su
    geometría se actualiza y se emite un evento. Cualquier análisis de supervivencia
    tiene que decidir explícitamente qué hace con eso.
    """
    m = _motor(max_age_bars=5)
    m.on_zone_created([_z(100, 104), _z(100, 104)], bar=1)
    m.on_bar(20)
    assert m.clusters[0]["state"] == EXPIRED

    ev = m.on_zone_created([_z(100, 104, start_bar=19), _z(101, 105, start_bar=19)],
                           bar=20)
    assert any(e["event"] == "CLUSTER_EXPANDED" for e in ev)
    assert m.clusters[0]["state"] == EXPIRED, "no revive"


def test_PARIDAD_un_cluster_DEPLETED_no_absorbe_expansiones():
    m = _motor(min_capacity_volume=10.0)
    m.on_zone_created([_z(100, 104, vol=1.0), _z(100, 104, vol=1.0)], bar=1)
    m.on_tick(101 * TICK, vol=10.0, side=1, bar=2)
    assert m.clusters[0]["state"] == DEPLETED
    m.on_zone_created([_z(100, 104, start_bar=3, vol=1.0),
                       _z(101, 105, start_bar=3, vol=1.0)], bar=3)
    assert len(m.clusters) == 2, "nace uno nuevo en vez de expandir el muerto"


# ---------------------------------------------------------------- censo as-of

def test_as_of_devuelve_el_estado_de_ENTONCES_no_el_final():
    """El punto entero del censo. Sin esto no se puede medir nada."""
    m = _motor()
    m.on_zone_created([_z(100, 104, vol=1000.0), _z(100, 104, vol=1000.0)], bar=1)
    ancho_inicial = m.clusters[0]["upper"] - m.clusters[0]["lower"]

    m.on_zone_created([_z(106, 110, start_bar=5, vol=1000.0),
                       _z(105, 109, start_bar=5, vol=1000.0)], bar=5)

    viejo = as_of(m.events, bar=1)[1]
    assert viejo["upper"] - viejo["lower"] == pytest.approx(ancho_inicial)
    assert m.clusters[0]["upper"] - m.clusters[0]["lower"] > ancho_inicial


def test_el_censo_cuenta_los_CENSURADOS_no_solo_los_que_murieron():
    """Una tabla que sólo cuenta muertes sobreestima la incidencia acumulada."""
    m = _motor(max_age_bars=5)
    m.on_zone_created([_z(100, 104), _z(100, 104)], bar=1)
    m.on_zone_created([_z(200, 204, start_bar=2), _z(200, 204, start_bar=2)], bar=2)
    m.on_bar(3)
    c = census(m.events)
    assert c["n"] == 2 and c["censurados"] == 2 and c["expired"] == 0
    m.on_bar(30)
    c = census(m.events)
    assert c["expired"] == 2 and c["censurados"] == 0


def test_defaults_declarados():
    assert RESEARCH_DEFAULTS["halo_sigma_ticks"] == 3.0
    assert RESEARCH_DEFAULTS["min_density"] == 3.0
    assert RESEARCH_DEFAULTS["max_age_bars"] == 500
    assert RESEARCH_DEFAULTS["invalidation_capacity_pct"] == 0.8

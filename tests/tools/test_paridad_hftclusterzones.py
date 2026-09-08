r"""Paridad de la capa de clusters: fija las decisiones del arnés de reproducción.

El espejo ya tiene sus propios tests. Acá se clava lo que decide el **arnés**, que es
donde se rompe la comparación sin que ningún test del espejo se entere: en qué barra se
le entrega cada zona al motor, cómo se deriva el lado del tick, y cómo se emparejan y
comparan los eventos contra el oráculo.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.paridad_hftclusterzones import (  # noqa: E402
    _igual, _norm_evento, barra_de_entrega, barra_de_nacimiento, comparar, lados)


# ------------------------------------------------------- lado del tick

def test_el_lado_sigue_la_regla_del_tick_con_ARRASTRE():
    """`side = cl > clP ? 1 : (cl < clP ? -1 : lastSide)` — el empate hereda."""
    assert lados([100, 101, 101, 101, 100, 100, 102]) == [0, 1, 1, 1, -1, -1, 1]


def test_el_primer_tick_no_tiene_lado():
    assert lados([100]) == [0]
    assert lados([]) == []


def test_una_serie_plana_arrastra_el_cero_inicial():
    """Sin movimiento previo no hay signo que heredar: queda 0, no 1."""
    assert lados([100, 100, 100]) == [0, 0, 0]


# ------------------------------------------- entrega vs nacimiento de la zona

def _z(idx_start, idx_end):
    return dict(idx_start=idx_start, idx_end=idx_end)


def test_la_zona_se_ENTREGA_en_la_barra_donde_TERMINA():
    """Es la diferencia con los runners de investigación, que usan la de inicio.

    El `.cs` llama a `EvaluarHaloClusters` al finalizar el streak. Una zona que empieza
    en la barra 0 y termina en la 2 crea su cluster en la 2, no en la 0.
    """
    z = _z(idx_start=10, idx_end=60)          # barras de 25 ticks: 0 -> 2
    assert barra_de_nacimiento(z, 25, 100) == 0
    assert barra_de_entrega(z, 25, 100) == 2


def test_una_zona_corta_nace_y_se_entrega_en_la_misma_barra():
    z = _z(idx_start=3, idx_end=20)
    assert barra_de_nacimiento(z, 25, 100) == barra_de_entrega(z, 25, 100) == 0


def test_las_dos_barras_se_recortan_al_ultimo_indice_valido():
    """El troceo del parquet descarta una cola de menos de 2 ticks: sin el recorte,
    una zona que termina ahí apuntaría a una barra que no existe."""
    z = _z(idx_start=240, idx_end=260)
    assert barra_de_entrega(z, 25, 10) == 9
    assert barra_de_nacimiento(z, 25, 10) == 9


# ------------------------------------------------------- normalizacion

@pytest.mark.parametrize("crudo,esperado", [
    ("CLUSTER_CREATED", "CREATED"),
    ("CLUSTER_TOUCHED_POC", "TOUCHED_POC"),
    ("cluster_expired", "EXPIRED"),
    ("EXPANDED", "EXPANDED"),
])
def test_los_nombres_de_evento_se_normalizan_de_los_dos_lados(crudo, esperado):
    assert _norm_evento(crudo) == esperado


def test_igual_compara_estados_sin_importar_mayusculas():
    assert _igual("Active", "ACTIVE")
    assert not _igual("Active", "Expired")


def test_igual_tolera_el_ultimo_bit_pero_no_medio_tick():
    assert _igual(1.0, 1.0 + 1e-9)
    assert not _igual(1.0, 1.125)


# ------------------------------------------------------------- comparacion

def _fila(start_ms, update_ms, event, lower=10.0, upper=12.0, state="Active"):
    # el orden es el de COLS
    return (1, start_ms, update_ms, lower, upper, 11.0, 3.5, 100.0, 0.0,
            400.0, 0.0, 0.0, 1.0, state, event, update_ms)


def _ev(start_ms, update_ms, event, lower=10.0, upper=12.0, state="Active"):
    return dict(start_ms=start_ms, update_ms=update_ms, event=event,
                lower=lower, upper=upper, poc=11.0, peak_density=3.5,
                seed_volume=100.0, seed_cvd=0.0, capacity_volume=400.0,
                volume_inside=0.0, delta_inside=0.0, remaining_cap_pct=1.0,
                state=state)


def test_un_evento_identico_cuenta_como_exacto():
    r = comparar([_fila(1000, 2000, "CREATED")],
                 [_ev(1000, 2000, "CLUSTER_CREATED")], 0.25)
    assert (r["exactos"], r["con_diferencia"], r["sin_par"]) == (1, 0, 0)


def test_una_diferencia_de_campo_se_reporta_con_su_nombre():
    r = comparar([_fila(1000, 2000, "CREATED", upper=12.0)],
                 [_ev(1000, 2000, "CLUSTER_CREATED", upper=99.0)], 0.25)
    assert r["con_diferencia"] == 1 and r["exactos"] == 0
    assert r["diferencias_por_campo"] == {"upper": 1}
    assert r["ejemplos"][0]["campo"] == "upper"


def test_el_MISMO_evento_en_otra_barra_NO_se_cuenta_como_defecto_del_espejo():
    """Es el tercer grupo del reporte: campos idénticos, timestamp distinto.

    Apunta a que las barras del arnés no están alineadas con las de NT8, que es un
    problema del arnés y no del espejo. Confundirlo con una diferencia de campo
    mandaría a depurar el lugar equivocado.
    """
    r = comparar([_fila(1000, 2000, "CREATED")],
                 [_ev(1000, 7777, "CLUSTER_CREATED")], 0.25)
    assert r["emparejados_en_otra_barra"] == 1
    assert r["con_diferencia"] == 0 and r["sin_par"] == 0


def test_un_evento_que_el_espejo_no_produce_queda_SIN_PAR():
    r = comparar([_fila(1000, 2000, "DEPLETED")], [], 0.25)
    assert r["sin_par"] == 1 and r["emparejados_en_otra_barra"] == 0


def test_el_conteo_por_tipo_de_evento_sale_del_ORACULO():
    orac = [_fila(1, 2, "CREATED"), _fila(1, 3, "EXPANDED"), _fila(1, 4, "EXPANDED")]
    r = comparar(orac, [], 0.25)
    assert r["eventos_del_oraculo"] == {"CREATED": 1, "EXPANDED": 2}


def test_entre_varios_candidatos_se_elige_el_de_MENOS_diferencias():
    """Dos eventos del espejo con la misma clave: gana el más parecido, no el primero."""
    orac = [_fila(1000, 2000, "CREATED", lower=10.0, upper=12.0)]
    espejo = [_ev(1000, 2000, "CLUSTER_CREATED", lower=88.0, upper=99.0),
              _ev(1000, 2000, "CLUSTER_CREATED", lower=10.0, upper=12.0)]
    r = comparar(orac, espejo, 0.25)
    assert r["exactos"] == 1

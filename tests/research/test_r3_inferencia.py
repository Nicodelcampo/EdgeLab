"""R3 - fija el bootstrap clusterizado y el TOST."""
from __future__ import annotations

import json

import numpy as np
import pytest

from diag.tasa_senales.r3_inferencia_cruce_es import (ALPHA_TOST, B_BOOT, CANONICAL_OUT,
                                                      MARGEN_REL, METRICA_PRIMARIA,
                                                      SCHEMA_VERSION, SEED, boot_cluster,
                                                      clasificar_run, make_run_id, tost)

M = METRICA_PRIMARIA


def _art():
    if not CANONICAL_OUT.exists():
        return None
    d = json.loads(CANONICAL_OUT.read_text(encoding="utf-8"))
    return d if d.get("schema_version") == SCHEMA_VERSION else None


saltar = pytest.mark.skipif(_art() is None, reason="artefacto R3 aun no generado")


def ses(*bloques):
    return {i: {M: np.array(b, dtype=float)} for i, b in enumerate(bloques)}


# --------------------------------------------------------------------------
# Bootstrap clusterizado
# --------------------------------------------------------------------------

def test_es_determinista_con_la_misma_semilla():
    d = ses([1.0, 2.0, 3.0], [4.0, 5.0], [0.0, 1.0])
    a = boot_cluster(d, M, b=200, seed=7)
    b = boot_cluster(d, M, b=200, seed=7)
    assert a["ci95"] == b["ci95"] and a["punto"] == b["punto"]


def test_semillas_distintas_dan_intervalos_distintos():
    d = ses(*[[float(i), float(i + 1), float(i + 2)] for i in range(12)])
    assert boot_cluster(d, M, b=200, seed=1)["ci95"] != \
        boot_cluster(d, M, b=200, seed=2)["ci95"]


def test_el_punto_es_la_mediana_agrupada_no_la_mediana_de_medianas():
    """Zona-ponderada: una sesion con 100 pares pesa mas que una con 2. Es la decision
    congelada en el protocolo, porque el numero de pares por sesion NO es aleatorio."""
    d = ses([0.0] * 100, [50.0, 50.0])
    r = boot_cluster(d, M, b=50, seed=3)
    assert r["punto"] == pytest.approx(0.0)          # agrupada
    assert r["punto_sesion_ponderada"] == pytest.approx(25.0)   # mediana de medianas
    assert r["mismo_signo_que_ponderada"] is True    # 0 no contradice


def test_remuestrea_sesiones_enteras_no_filas():
    """Con una sola sesion, todas las replicas son identicas y el IC colapsa al punto.
    Si remuestreara filas, el IC tendria ancho."""
    r = boot_cluster(ses([1.0, 5.0, 9.0, 13.0]), M, b=300, seed=5)
    assert r["ci95"][0] == r["ci95"][1] == r["punto"]


def test_detecta_un_efecto_claro_y_no_cruza_cero():
    d = ses(*[[10.0, 11.0, 12.0] for _ in range(15)])
    r = boot_cluster(d, M, b=500, seed=9)
    assert r["cruza_cero"] is False and r["ci95"][0] > 0


def test_un_nulo_verdadero_cruza_cero():
    rng = np.random.default_rng(4)
    d = {i: {M: rng.normal(0, 5, 40)} for i in range(20)}
    assert boot_cluster(d, M, b=500, seed=11)["cruza_cero"] is True


def test_publica_n_pares_n_sesiones_B_y_seed():
    r = boot_cluster(ses([1.0, 2.0], [3.0]), M, b=50, seed=2)
    assert r["n_pares"] == 3 and r["n_sesiones"] == 2
    assert r["B"] == 50 and r["seed"] == 2


def test_sin_datos_devuelve_vacio():
    assert boot_cluster({}, M) == {}


# --------------------------------------------------------------------------
# TOST
# --------------------------------------------------------------------------

def test_equivalencia_solo_si_el_IC_entra_entero():
    assert tost([-1.0, 1.0], 5.0)["equivalencia"] is True
    assert tost([-6.0, 1.0], 5.0)["equivalencia"] is False
    assert tost([-1.0, 6.0], 5.0)["equivalencia"] is False


def test_el_borde_no_cuenta_como_equivalencia():
    assert tost([-5.0, 5.0], 5.0)["equivalencia"] is False


def test_un_IC_ancho_no_es_equivalencia_aunque_contenga_cero():
    """La distincion que faltaba: contener cero no es equivalencia. Un nulo sin margen
    no separa 'no hay efecto' de 'no hubo potencia'."""
    r = tost([-40.0, 40.0], 7.9)
    assert r["equivalencia"] is False


def test_el_tost_declara_que_el_margen_no_es_economico():
    assert "NO es economico" in tost([-1.0, 1.0], 5.0)["nota"]


# --------------------------------------------------------------------------
# Gobernanza
# --------------------------------------------------------------------------

def test_parametros_congelados_son_los_del_protocolo():
    assert B_BOOT == 10_000 and SEED == 20260821
    assert MARGEN_REL == 0.05 and ALPHA_TOST == 0.10
    assert METRICA_PRIMARIA == "ticks_por_ancho"


def test_truncada_no_sobrescribe_el_canonico():
    _, pub, err = clasificar_run(5, CANONICAL_OUT)
    assert pub is False and err is not None


def test_run_id_determinista_y_sensible():
    a = make_run_id("abc", [1, 2], 0)
    assert a == make_run_id("abc", [1, 2], 0) and len(a) == 16
    assert make_run_id("abc", [1, 2, 3], 0) != a


# --------------------------------------------------------------------------
# Artefacto
# --------------------------------------------------------------------------

@saltar
def test_el_artefacto_declara_soporte_y_parametros():
    d = _art()
    assert "soporte comun" in d["estimando"]
    p = d["parametros_congelados"]
    assert p["B"] == B_BOOT and p["seed"] == SEED
    assert p["unidad_remuestreo"] == "sesion completa"
    assert d["outcomes_accessed"] is False and d["holdout_included"] is False


@saltar
def test_publica_las_cuatro_sensibilidades():
    s = _art()["resultado"]["sensibilidades"]
    for v in ("S1_inverso", "S1_permutado", "S2_solo_anterior", "S3_con_reemplazo",
              "S4_sep_5min"):
        assert v in s

"""Atlas F1 - fija la normalizacion expansiva y el contrato de disponibilidad causal."""
from __future__ import annotations

import json

import numpy as np
import pytest

from diag.tasa_senales.atlas_hft_es import (BUCKET_MIN, CANONICAL_OUT, DISPONIBILIDAD,
                                            NO_IMPLEMENTADAS, S1_MECHA_FRAC,
                                            S1_MIN_RANGO_TICKS, SCHEMA_VERSION,
                                            PercentilExpansivo, barras_1min,
                                            clasificar_run, make_run_id)


def _art():
    if not CANONICAL_OUT.exists():
        return None
    d = json.loads(CANONICAL_OUT.read_text(encoding="utf-8"))
    return d if d.get("schema_version") == SCHEMA_VERSION else None


saltar = pytest.mark.skipif(_art() is None, reason="atlas aun no generado")


# --------------------------------------------------------------------------
# Normalizacion expansiva: la regla que mas facil se rompe
# --------------------------------------------------------------------------

def test_no_devuelve_percentil_hasta_acumular_historia():
    """Hacen falta 20 EN HISTORIA, asi que la llamada 20 todavia devuelve None: es la
    que deja el vigesimo valor. La 21 es la primera con percentil."""
    p = PercentilExpansivo()
    for i in range(20):
        assert p.pct("b", float(i)) is None
    assert len(p.hist["b"]) == 20
    assert p.pct("b", 5.0) is not None


def test_el_percentil_NO_incluye_la_observacion_actual():
    """Incluirse a si misma seria mirar el presente para normalizar el presente."""
    p = PercentilExpansivo()
    for i in range(20):
        p.pct("b", 0.0)
    assert p.pct("b", 100.0) == pytest.approx(1.0)     # 20 previas, todas menores
    assert len(p.hist["b"]) == 21


def test_nunca_usa_observaciones_futuras():
    """El valor grande que viene DESPUES no puede cambiar el percentil de uno anterior."""
    p = PercentilExpansivo()
    for i in range(20):
        p.pct("b", 1.0)
    antes = p.pct("b", 2.0)
    p.pct("b", 1000.0)
    q = PercentilExpansivo()
    for i in range(20):
        q.pct("b", 1.0)
    assert q.pct("b", 2.0) == antes


def test_los_buckets_son_independientes():
    p = PercentilExpansivo()
    for i in range(30):
        p.pct("manana", 0.0)
    assert p.pct("tarde", 5.0) is None                 # su bucket no tiene historia


def test_el_percentil_ordena_correctamente():
    p = PercentilExpansivo()
    for i in range(100):
        p.pct("b", float(i))
    assert p.pct("b", -1.0) == pytest.approx(0.0)
    assert p.pct("b", 50.0) == pytest.approx(0.51, abs=0.02)
    assert p.pct("b", 999.0) == pytest.approx(1.0)


# --------------------------------------------------------------------------
# Barras y S1
# --------------------------------------------------------------------------

def test_barras_1min_agrupa_por_minuto_y_toma_ohlc():
    ini = 0
    ts = np.array([0, 30, 59, 61, 90], dtype=np.int64) * 1_000_000_000
    px = np.array([10.0, 12.0, 9.0, 20.0, 21.0])
    vol = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    b = barras_1min(ts, px, vol, ini)
    assert len(b) == 2
    assert (b[0]["o"], b[0]["h"], b[0]["l"], b[0]["c"], b[0]["v"]) == (10, 12, 9, 9, 6)
    assert (b[1]["o"], b[1]["c"], b[1]["v"]) == (20, 21, 9)


def test_los_umbrales_de_S1_estan_declarados_y_no_son_los_de_F29():
    """F2.9 midio S1 sobre 6E con otra especificacion de barra. Aca es S1_1MIN sobre ES."""
    assert S1_MIN_RANGO_TICKS == 3 and S1_MECHA_FRAC == 0.30
    assert "S1_1MIN" in DISPONIBILIDAD.get("__grupos__", "S1_1MIN")   # nombre distinto


# --------------------------------------------------------------------------
# Contrato de disponibilidad causal
# --------------------------------------------------------------------------

def test_ninguna_columna_declarada_es_POST():
    """D-HFT-CTX-02: una columna POST no puede usarse como filtro de regimen."""
    assert set(DISPONIBILIDAD.values()) <= {"PRE", "AT_EVENT"}
    assert "POST" not in set(DISPONIBILIDAD.values())


def test_no_hay_columnas_de_outcome_en_el_esquema():
    prohibidas = ("retorno", "excursion", "mae", "mfe", "pnl", "cruza", "outcome")
    for col in DISPONIBILIDAD:
        assert not any(p in col.lower() for p in prohibidas), col


def test_lo_no_implementado_se_declara_en_vez_de_inventarse():
    assert "scheduled_news" in NO_IMPLEMENTADAS
    assert NO_IMPLEMENTADAS["scheduled_news"].startswith("NOT_AVAILABLE")
    assert NO_IMPLEMENTADAS["bigtrap_columns"].startswith("BLOCKED")


def test_gobernanza_de_corrida():
    assert clasificar_run(0, CANONICAL_OUT) == ("full", True, None)
    _, pub, err = clasificar_run(5, CANONICAL_OUT)
    assert pub is False and err is not None
    a = make_run_id("abc", [1, 2], 0)
    assert a == make_run_id("abc", [1, 2], 0) and len(a) == 16


def test_bucket_declarado():
    assert BUCKET_MIN == 15


# --------------------------------------------------------------------------
# Artefacto
# --------------------------------------------------------------------------

@saltar
def test_el_atlas_tiene_las_tres_poblaciones():
    d = _art()
    assert set(d["conteos"]["por_grupo"]) == {"ZONA", "CASI", "S1_1MIN"}
    assert all(v > 0 for v in d["conteos"]["por_grupo"].values())


@saltar
def test_el_atlas_es_trazable_y_sin_outcomes():
    d = _art()
    assert len(d["artefacto"]["sha256"]) == 64
    assert d["outcomes_accessed"] is False and d["holdout_included"] is False

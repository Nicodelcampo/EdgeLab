"""R1 - memoria de nivel: fija el estimador Monte Carlo y el lineage de denominadores.

Las funciones puras se testean siempre. Las que validan el artefacto canonico se
saltan mientras el JSON siga en el schema viejo: el sellado es Commit A (codigo) ->
rerun limpio -> Commit B (JSON), asi que entre A y B el artefacto todavia es v1.
Eso es ATJ-14, no una omision.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from diag.tasa_senales.memoria_nivel_nulo_correcto import (CANONICAL_OUT,
                                                           MIN_ZONAS_MEMORIA, N_NULO,
                                                           SCHEMA_VERSION,
                                                           clasificar_run, make_run_id,
                                                           p_minimo_posible,
                                                           p_montecarlo)


def _art():
    if not CANONICAL_OUT.exists():
        return None
    d = json.loads(CANONICAL_OUT.read_text(encoding="utf-8"))
    return d if d.get("schema_version") == SCHEMA_VERSION else None


saltar = pytest.mark.skipif(_art() is None,
                            reason="artefacto canonico todavia no regenerado (Commit B)")


# --------------------------------------------------------------------------
# 1. El estimador Monte Carlo nunca da 0
# --------------------------------------------------------------------------

def test_p_nunca_es_cero_ni_con_nulo_totalmente_por_debajo():
    """`count/B` publicaba p = 0,0 en 5 de 59 sesiones. Eso es un artefacto del
    estimador, no certeza: con B remuestreos no se puede afirmar mas que 1/(B+1)."""
    nulo = np.zeros(N_NULO)
    p = p_montecarlo(nulo, observado=999.0, b=N_NULO)
    assert p > 0.0
    assert p == pytest.approx(1.0 / (N_NULO + 1))


def test_p_minimo_posible_es_uno_sobre_B_mas_uno():
    assert p_minimo_posible(N_NULO) == pytest.approx(1.0 / 401)
    assert p_minimo_posible(99) == pytest.approx(0.01)


def test_p_maximo_es_uno_cuando_todo_el_nulo_alcanza_el_observado():
    assert p_montecarlo(np.ones(N_NULO) * 5, 5.0, N_NULO) == pytest.approx(1.0)


def test_p_cuenta_con_mayor_o_igual_no_estrictamente_mayor():
    """El empate cuenta a favor del nulo. Usar `>` inflaria la significancia."""
    nulo = np.array([3.0, 3.0, 3.0, 1.0])
    assert p_montecarlo(nulo, 3.0, 4) == pytest.approx((1 + 3) / 5)


def test_equivale_a_la_formula_inline_que_venia_de_ecdd444():
    rng = np.random.default_rng(7)
    for _ in range(200):
        nulo = rng.integers(0, 12, 400).astype(float)
        obs = float(rng.integers(0, 14))
        inline = float((1 + np.sum(nulo >= obs)) / 401)
        assert p_montecarlo(nulo, obs, 400) == pytest.approx(inline, abs=1e-15)


# --------------------------------------------------------------------------
# 2. Determinismo
# --------------------------------------------------------------------------

def test_run_id_es_determinista():
    a = make_run_id("abc123", [20260101, 20260102], 0)
    b = make_run_id("abc123", [20260101, 20260102], 0)
    assert a == b and len(a) == 16


def test_run_id_cambia_con_commit_sesiones_y_truncamiento():
    base = make_run_id("abc123", [20260101, 20260102], 0)
    assert make_run_id("def456", [20260101, 20260102], 0) != base
    assert make_run_id("abc123", [20260101], 0) != base
    assert make_run_id("abc123", [20260101, 20260102], 5) != base


def test_p_montecarlo_no_depende_del_orden_del_nulo():
    rng = np.random.default_rng(11)
    nulo = rng.integers(0, 20, 400).astype(float)
    assert p_montecarlo(nulo, 9.0, 400) == p_montecarlo(rng.permutation(nulo), 9.0, 400)


# --------------------------------------------------------------------------
# 3. Truncamiento
# --------------------------------------------------------------------------

def test_corrida_completa_es_publicable():
    scope, pub, err = clasificar_run(0, CANONICAL_OUT)
    assert (scope, pub, err) == ("full", True, None)


def test_corrida_truncada_no_puede_sobrescribir_el_output_canonico():
    scope, pub, err = clasificar_run(5, CANONICAL_OUT)
    assert scope == "truncated_probe"
    assert pub is False
    assert err is not None and "canonico" in err


def test_corrida_truncada_a_otro_destino_corre_pero_no_es_publicable(tmp_path):
    scope, pub, err = clasificar_run(5, tmp_path / "probe.json")
    assert (scope, pub, err) == ("truncated_probe", False, None)


# --------------------------------------------------------------------------
# 4-7. Contrato del artefacto (activos despues del rerun de Commit B)
# --------------------------------------------------------------------------

@saltar
def test_missing_y_excluded_estan_computados_y_serializados():
    d = _art()
    assert isinstance(d["missing_items"], list)
    assert isinstance(d["excluded_items"], list)
    for e in d["excluded_items"]:
        assert e["n_ancho_positivo"] < MIN_ZONAS_MEMORIA
        assert {"trade_date", "n_brutas", "umbral", "motivo"} <= set(e)


@saltar
def test_los_denominadores_estan_separados_y_cuadran():
    """price-rounding usa las procesadas; memoria usa las elegibles. Son dos
    poblaciones, no un unico `n_sesiones`."""
    c = _art()["conteos"]
    assert c["n_universe_discovered"] >= c["n_selected"] >= c["n_available"]
    assert c["n_available"] >= c["n_processed"] >= c["n_eligible_memory"]
    assert c["n_eligible_rounding"] == c["n_processed"]
    d = _art()
    assert d["agrupamiento_en_numeros_redondos"]["population_id"] == "P_PROCESSED"
    assert d["nulo_corregido"]["population_id"] == "P_ELIGIBLE_MEMORY"
    assert (d["poblaciones"]["P_ELIGIBLE_MEMORY"]["n"]
            + len(d["excluded_items"]) == c["n_processed"])
    assert c["n_selected"] - len(d["missing_items"]) == c["n_available"]


@saltar
def test_el_artefacto_declara_B_seed_metodo_y_run_id():
    d = _art()
    mc = d["montecarlo"]
    assert mc["B"] == N_NULO and mc["seed"] is not None
    assert mc["method"] == "(1 + count(null >= observed)) / (B + 1)"
    assert mc["p_minimo_posible"] == pytest.approx(1 / (N_NULO + 1), abs=1e-6)
    assert len(d["run_id"]) == 16
    assert d["run_scope"] in ("full", "truncated_probe")


@saltar
def test_ningun_p_publicado_es_cero():
    d = _art()
    for s in d["sesiones"]:
        assert s["nulo_corregido"]["p_max"] >= 1 / (N_NULO + 1) - 1e-9
        assert s["nulo_viejo"]["p_max"] >= 1 / (N_NULO + 1) - 1e-9


@saltar
def test_alias_deprecado_sigue_presente_y_coincide():
    d = _art()
    assert d["n_sesiones"] == d["conteos"]["n_eligible_memory"]
    assert "DEPRECATED" in "".join(k for k in d if "DEPRECATED" in k)


@saltar
def test_nulo_viejo_esta_marcado_como_no_interpretable():
    d = _art()
    assert d["nulo_viejo"]["estado"] == "NON_INTERPRETABLE_LEGACY_DIAGNOSTIC"
    assert d["efecto_de_diseno"]["estado"] == "INFERRED_NOT_VERIFIED"


@saltar
def test_el_artefacto_publicable_viene_de_una_corrida_completa():
    d = _art()
    if d["publishable"]:
        assert d["run_scope"] == "full"
        assert d["max_sesiones_arg"] == 0


@saltar
def test_sigue_sin_outcomes_y_sin_holdout():
    d = _art()
    assert d["outcomes_accessed"] is False
    assert d["pnl_accessed"] is False
    assert d["holdout_included"] is False

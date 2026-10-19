"""R2 - fija la logica de emparejamiento y los diagnosticos de balance.

Las funciones se testean con fixtures chicos y deterministas. La corrida completa
necesita el snapshot congelado y no entra en la suite; los tests del artefacto se
activan cuando el JSON exista (ATJ-14: Commit A -> rerun -> Commit B).
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from diag.tasa_senales.r2_matchability_es import (CANONICAL_OUT, MAX_SEPARACION_MS,
                                                  SCHEMA_VERSION, SMD_REFERENCIA,
                                                  clasificar_run, emparejar, fase_de,
                                                  ks_max, make_run_id, ratio_varianza,
                                                  smd)


def _art():
    if not CANONICAL_OUT.exists():
        return None
    d = json.loads(CANONICAL_OUT.read_text(encoding="utf-8"))
    return d if d.get("schema_version") == SCHEMA_VERSION else None


saltar = pytest.mark.skipif(_art() is None, reason="artefacto R2 aun no generado")


def z(t, w):
    return dict(start_ts=t, ancho_ticks=w)


def c(t, w):
    return dict(start_ts=t, ancho_ticks=w)


def pool_de(cs):
    p = {}
    for x in cs:
        p.setdefault(x["ancho_ticks"], []).append(x)
    return p


# --------------------------------------------------------------------------
# Emparejamiento
# --------------------------------------------------------------------------

def test_empareja_por_ancho_exacto_y_no_cruza_anchos():
    zonas = [z(1000, 3)]
    pool = pool_de([c(1001, 4), c(1002, 2)])       # ninguno de ancho 3
    assert emparejar(zonas, pool)[0] is None


def test_elige_el_mas_cercano_en_tiempo():
    zonas = [z(1000, 3)]
    pool = pool_de([c(1500, 3), c(1050, 3), c(9000, 3)])
    j, d = emparejar(zonas, pool)[0]
    assert pool[3][j]["start_ts"] == 1050
    assert d == 50


def test_el_delta_se_publica_CON_signo_aunque_el_criterio_use_valor_absoluto():
    """El criterio es |dt|, asi que admite controles POSTERIORES. El delta publicado
    conserva el signo para que se pueda auditar cuantos vienen del futuro."""
    assert emparejar([z(1000, 3)], pool_de([c(900, 3)]))[0][1] == -100
    assert emparejar([z(1000, 3)], pool_de([c(1100, 3)]))[0][1] == +100


def test_un_control_futuro_gana_si_esta_mas_cerca():
    zonas = [z(1000, 3)]
    pool = pool_de([c(700, 3), c(1100, 3)])        # pasado a 300, futuro a 100
    j, d = emparejar(zonas, pool)[0]
    assert d == +100 and pool[3][j]["start_ts"] == 1100


def test_respeta_el_tope_de_separacion():
    lejos = MAX_SEPARACION_MS + 1
    assert emparejar([z(0, 3)], pool_de([c(lejos, 3)]))[0] is None
    assert emparejar([z(0, 3)], pool_de([c(MAX_SEPARACION_MS, 3)]))[0] is not None


def test_sin_reemplazo_un_control_se_usa_una_sola_vez():
    zonas = [z(1000, 3), z(1010, 3)]
    pool = pool_de([c(1005, 3)])                   # un solo candidato
    r = emparejar(zonas, pool, con_reemplazo=False)
    assert sum(1 for v in r.values() if v) == 1


def test_con_reemplazo_el_mismo_control_sirve_para_las_dos():
    zonas = [z(1000, 3), z(1010, 3)]
    pool = pool_de([c(1005, 3)])
    r = emparejar(zonas, pool, con_reemplazo=True)
    assert all(v is not None for v in r.values())
    assert r[0][0] == r[1][0]


def test_el_orden_cambia_la_asignacion_cuando_hay_competencia():
    """Greedy: la primera zona en el orden se queda con el mejor candidato. Por eso R2
    mide la dependencia del orden en vez de asumirla inocua."""
    zonas = [z(1000, 3), z(1200, 3)]
    pool = pool_de([c(1100, 3)])
    directo = emparejar(zonas, pool)
    inverso = emparejar(zonas, pool, orden=[1, 0])
    assert (directo[0] is not None) and (directo[1] is None)
    assert (inverso[0] is None) and (inverso[1] is not None)


def test_sin_competencia_el_orden_no_cambia_nada():
    zonas = [z(1000, 3), z(5000, 3)]
    pool = pool_de([c(1010, 3), c(5010, 3)])
    assert emparejar(zonas, pool) == emparejar(zonas, pool, orden=[1, 0])


# --------------------------------------------------------------------------
# Diagnosticos de balance
# --------------------------------------------------------------------------

def test_smd_es_cero_para_grupos_identicos():
    x = [1.0, 2.0, 3.0, 4.0]
    assert smd(x, x) == pytest.approx(0.0)


def test_smd_conocido():
    """a: media 0,5 var 1/3 · b: media 2,5 var 1/3 · sd agrupada sqrt(1/3)
    -> smd = -2 / sqrt(1/3) = -2*sqrt(3)."""
    a, b = [0.0, 0.0, 1.0, 1.0], [2.0, 2.0, 3.0, 3.0]
    assert np.var(a, ddof=1) == pytest.approx(1 / 3)
    assert smd(a, b) == pytest.approx(-2.0 * np.sqrt(3.0), rel=1e-9)


def test_smd_signo_y_referencia():
    assert smd([10.0] * 5 + [11.0] * 5, [0.0] * 5 + [1.0] * 5) > SMD_REFERENCIA
    assert abs(smd([1.0, 2.0, 3.0], [1.0, 2.0, 3.1])) < 1.0


def test_ratio_varianza():
    assert ratio_varianza([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)
    assert ratio_varianza([0.0, 4.0], [0.0, 2.0]) == pytest.approx(4.0)


def test_ks_max_entre_distribuciones_disjuntas_es_uno():
    assert ks_max([0.0, 1.0, 2.0], [10.0, 11.0]) == pytest.approx(1.0)


def test_ks_max_entre_identicas_es_cero():
    assert ks_max([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(0.0)


def test_los_diagnosticos_devuelven_None_sin_datos_suficientes():
    assert smd([1.0], [2.0]) is None
    assert ratio_varianza([1.0], [2.0]) is None


# --------------------------------------------------------------------------
# Fases y gobernanza de corrida
# --------------------------------------------------------------------------

def test_fases_cubren_el_reloj_y_asia_cruza_medianoche():
    assert fase_de(19.0) == "asia" and fase_de(1.0) == "asia"
    assert fase_de(4.0) == "europa"
    assert fase_de(10.0) == "rth_am" and fase_de(14.0) == "rth_pm"
    assert fase_de(17.0) == "cierre"
    for h in np.arange(0, 24, 0.25):
        assert fase_de(float(h)) != "otro"


def test_truncada_no_sobrescribe_el_canonico():
    scope, pub, err = clasificar_run(5, CANONICAL_OUT)
    assert scope == "truncated_probe" and pub is False and err is not None


def test_completa_es_publicable():
    assert clasificar_run(0, CANONICAL_OUT) == ("full", True, None)


def test_run_id_determinista():
    a = make_run_id("abc", [1, 2], 0)
    assert a == make_run_id("abc", [1, 2], 0) and len(a) == 16
    assert make_run_id("abc", [1], 0) != a


# --------------------------------------------------------------------------
# Contrato del artefacto
# --------------------------------------------------------------------------

@saltar
def test_el_artefacto_no_toca_outcomes():
    d = _art()
    assert d["outcomes_accessed"] is False and d["pnl_accessed"] is False
    assert d["holdout_included"] is False


@saltar
def test_los_conteos_cuadran():
    c_ = _art()["conteos"]
    assert c_["n_matched"] + c_["n_unmatched"] == c_["n_zonas"]
    assert c_["n_universe_discovered"] >= c_["n_selected"] >= c_["n_available"]


@saltar
def test_publica_soporte_orden_reemplazo_y_separacion():
    d = _art()
    for k in ("soporte_comun", "reemplazo", "dependencia_del_orden",
              "separacion_temporal", "balance_par", "matched_vs_unmatched",
              "cobertura"):
        assert d.get(k), k

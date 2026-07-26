# -*- coding: utf-8 -*-
"""Identidad reproducible del modelo, adaptador no instalado y costo de cómputo."""
import pytest

from edgelab.external import feasibility as F
from edgelab.external.contract import ContractError, ModelIdentity
from edgelab.external.kronos import (
    DISPONIBLE, KronosNoInstalado, KronosPredictor, identidad_kronos)
from edgelab.external.mock import identidad_mock

W = "a" * 64


def test_sin_hash_de_pesos_no_hay_identidad():
    """El nombre del modelo no alcanza: el mismo tag puede mover los pesos."""
    with pytest.raises(ContractError) as e:
        ModelIdentity(name="Kronos-small", revision="main", weights_sha256="",
                      context_bars=512, lookback_bars=400, horizon_bars=12,
                      n_paths=30, seed=1, bar_spec="time:5")
    assert "weights_sha256" in str(e.value)


def test_lookback_mayor_al_contexto_es_error():
    """Truncar en silencio hace que el feature no sea lo que dice ser."""
    with pytest.raises(ContractError) as e:
        ModelIdentity(name="Kronos-small", revision="main", weights_sha256=W,
                      context_bars=512, lookback_bars=900, horizon_bars=12,
                      n_paths=30, seed=1, bar_spec="time:5")
    assert "trunca en silencio" in str(e.value)


def test_el_model_id_cambia_con_todo_lo_que_cambia_la_salida():
    base = identidad_kronos(W)
    assert identidad_kronos(W).model_id == base.model_id          # estable
    for kw in (dict(seed=999), dict(n_paths=10), dict(lookback_bars=200),
               dict(horizon_bars=24), dict(bar_spec="time:1"),
               dict(name="Kronos-base")):
        assert identidad_kronos(W, **kw).model_id != base.model_id, kw
    assert identidad_kronos("b" * 64).model_id != base.model_id   # otros pesos


def test_kronos_mini_declara_su_contexto_largo():
    assert identidad_kronos(W, name="Kronos-mini", lookback_bars=2000).context_bars == 2048


@pytest.mark.skipif(DISPONIBLE, reason="torch instalado")
def test_el_adaptador_falla_ruidosamente_y_no_cae_a_un_heuristico():
    """Un feature que a veces es Kronos y a veces otra cosa no es un feature."""
    with pytest.raises(KronosNoInstalado) as e:
        KronosPredictor(identidad_kronos(W))
    assert "MockPredictor" in str(e.value)


def test_la_identidad_mock_no_se_puede_confundir_con_pesos_reales():
    assert set(identidad_mock().weights_sha256) == {"0"}


# ------------------------------------------------------------- factibilidad
def test_el_caso_que_motiva_el_modulo_es_inviable_bar_a_bar():
    """2 años de MNQ 1min a ~2 s por llamada: días, no horas."""
    r = F.estimar(700_000, s_por_llamada=2.0)
    assert r["dias"] > 10
    assert not r["viable_en_una_noche"]


def test_la_cadencia_lo_vuelve_viable_y_el_costo_es_lineal():
    caro = F.estimar(700_000, s_por_llamada=2.0, cadencia_bars=1)
    barato = F.estimar(700_000, s_por_llamada=2.0, cadencia_bars=60)
    assert barato["segundos"] == pytest.approx(caro["segundos"] / 60, rel=1e-3)


def test_el_muestreo_por_evento_es_la_politica_mas_barata():
    """Las zonas ya son el evento de interés: predecir sólo ahí."""
    filas = F.comparar(700_000, 2.0, cadencias=(1, 15, 60), n_eventos=1500)
    assert filas[-1]["politica"].startswith("por evento")
    assert filas[-1]["viable_en_una_noche"]


def test_la_cadencia_define_cuan_vieja_llega_a_estar_la_prediccion():
    bar_ns = 60 * 10**9
    assert F.staleness_de_cadencia(15, bar_ns) == 15 * bar_ns


def test_presupuesto_inverso_contesta_la_pregunta_al_reves():
    assert F.presupuesto_inverso(8, 2.0) == 14400
    assert F.presupuesto_inverso(8, 2.0, paralelismo=4) == 57600


def test_formatear_no_explota_y_dice_si_entra_en_una_noche():
    txt = F.formatear(F.comparar(100_000, 0.5), "prueba")
    assert "una noche?" in txt and ("si" in txt or "NO" in txt)

# -*- coding: utf-8 -*-
"""Tests truth-known del validador del contrato multiframe.

Cada test construye datos sintéticos con un defecto conocido y verifica que
el validador lo detecte. No se leen datos reales, outcomes ni holdout.
"""
from __future__ import annotations

import pandas as pd
import pytest

from edgelab.research.multiframe import dataset_contract as dc

NS = 1_000_000_000


def _windows(n=10, null_frac=0.5, origin="grid"):
    rows = []
    for i in range(n):
        rows.append(
            dict(
                session_key="6E|09-26|2026-06-%02d" % (i % 5 + 1),
                cutoff_ns=1000 * NS + i * 60 * NS,
                window_spec_id="w60",
                cutoff_origin=origin,
                active_frame_count=0 if i < int(n * null_frac) else 2,
            )
        )
    return pd.DataFrame(rows)


def _targets_from(windows, start_offset_ns=1, horizon_ns=60 * NS):
    rows = []
    for _, w in windows.iterrows():
        rows.append(
            dict(
                session_key=w["session_key"],
                cutoff_ns=w["cutoff_ns"],
                window_spec_id=w["window_spec_id"],
                target_id="touch_60s",
                target_start_ns=w["cutoff_ns"] + start_offset_ns,
                target_end_ns=w["cutoff_ns"] + horizon_ns,
                label_horizon_ns=horizon_ns,
            )
        )
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# Causalidad
# ----------------------------------------------------------------------

def test_target_que_empieza_en_el_cutoff_es_fail():
    w = _windows()
    t = _targets_from(w, start_offset_ns=0)  # empieza exactamente en el cutoff
    res = dc.check_causality(w, t)
    assert res.passed is False
    assert "target_start<=cutoff=10" in res.detail


def test_target_estrictamente_posterior_es_pass():
    w = _windows()
    t = _targets_from(w, start_offset_ns=1)
    assert dc.check_causality(w, t).passed is True


def test_target_huerfano_es_fail():
    w = _windows(n=3)
    t = _targets_from(_windows(n=4))
    res = dc.check_causality(w, t)
    assert res.passed is False
    assert "huérfanos=1" in res.detail


def test_evento_de_barra_todavia_abierta_es_fail():
    cutoff = 1000 * NS
    ev = pd.DataFrame(
        [
            dict(available_at_ns=cutoff - 5 * NS, bar_end_ns=cutoff - 5 * NS),
            dict(available_at_ns=cutoff - 1 * NS, bar_end_ns=cutoff + 1 * NS),
        ]
    )
    res = dc.check_event_availability(ev, cutoff)
    assert res.passed is False
    assert "bar_end>cutoff=1" in res.detail


# ----------------------------------------------------------------------
# Grupo de control y muestreo de cutoffs
# ----------------------------------------------------------------------

def test_sin_ventanas_nulas_no_hay_grupo_de_control():
    w = _windows(n=10, null_frac=0.0)
    res = dc.check_null_window_fraction(w, minimum=0.20)
    assert res.passed is False


def test_fraccion_nula_suficiente_es_pass():
    w = _windows(n=10, null_frac=0.5)
    assert dc.check_null_window_fraction(w, minimum=0.20).passed is True


def test_cutoffs_solo_event_driven_es_fail():
    w = _windows(origin="event")
    assert dc.check_cutoff_grid_independence(w).passed is False


# ----------------------------------------------------------------------
# Folds
# ----------------------------------------------------------------------

def test_sesion_train_y_test_en_el_mismo_fold_es_fail():
    folds = pd.DataFrame(
        [
            dict(fold_plan_id="p1", outer_fold=0, session_key="S1", role="train"),
            dict(fold_plan_id="p1", outer_fold=0, session_key="S1", role="test"),
            dict(fold_plan_id="p1", outer_fold=0, session_key="S2", role="test"),
        ]
    )
    res = dc.check_fold_roles(folds)
    assert res.passed is False
    assert "conflictos train/test=1" in res.detail


def test_fold_sin_sesiones_de_test_es_fail():
    folds = pd.DataFrame(
        [
            dict(fold_plan_id="p1", outer_fold=0, session_key="S1", role="train"),
            dict(fold_plan_id="p1", outer_fold=0, session_key="S2", role="train"),
        ]
    )
    res = dc.check_fold_roles(folds)
    assert res.passed is False
    assert "folds sin test=1" in res.detail


def test_rol_invalido_es_fail():
    folds = pd.DataFrame(
        [
            dict(fold_plan_id="p1", outer_fold=0, session_key="S1", role="validation"),
            dict(fold_plan_id="p1", outer_fold=0, session_key="S2", role="test"),
        ]
    )
    assert dc.check_fold_roles(folds).passed is False


def test_plan_de_folds_valido_es_pass():
    folds = pd.DataFrame(
        [
            dict(fold_plan_id="p1", outer_fold=0, session_key="S1", role="test"),
            dict(fold_plan_id="p1", outer_fold=0, session_key="S2", role="train"),
            dict(fold_plan_id="p1", outer_fold=1, session_key="S1", role="train"),
            dict(fold_plan_id="p1", outer_fold=1, session_key="S2", role="test"),
        ]
    )
    assert dc.check_fold_roles(folds).passed is True


def test_sesion_de_ventanas_ausente_del_plan_de_folds_es_fail():
    w = _windows(n=5)
    folds = pd.DataFrame(
        [dict(fold_plan_id="p1", outer_fold=0, session_key="OTRA", role="test")]
    )
    assert dc.check_sessions_declared_in_folds(w, folds).passed is False


# ----------------------------------------------------------------------
# Firewall, embargo, leakage e identidad
# ----------------------------------------------------------------------

def test_firewall_detecta_filas_de_holdout():
    holdout_start_ns = 2000 * NS
    df = pd.DataFrame(
        [dict(cutoff_ns=1999 * NS), dict(cutoff_ns=holdout_start_ns)]
    )
    res = dc.check_firewall(df, "cutoff_ns", holdout_start_ns, "windows_ml")
    assert res.passed is False
    assert "1 filas" in res.detail


def test_embargo_menor_al_horizonte_es_fail():
    t = _targets_from(_windows(n=3), horizon_ns=120 * NS)
    assert dc.check_embargo(None, t, embargo_ns=60 * NS).passed is False
    assert dc.check_embargo(None, t, embargo_ns=120 * NS).passed is True


@pytest.mark.parametrize(
    "bad_col", ["target__touch", "y_touch", "future_return", "outcome_pnl"]
)
def test_columnas_de_outcome_en_features_son_fail(bad_col):
    w = _windows()
    w[bad_col] = 1.0
    res = dc.check_target_leakage_columns(w)
    assert res.passed is False
    assert bad_col in res.offenders


def test_manifiesto_con_codigo_sucio_es_fail():
    manifest = dict(dataset_id="abc", code_commit="deadbeef", code_dirty=True)
    res = dc.check_manifest(manifest, ["dataset_id", "code_commit", "code_dirty"])
    assert res.passed is False


def test_manifiesto_completo_y_limpio_es_pass():
    manifest = dict(dataset_id="abc", code_commit="deadbeef", code_dirty=False)
    res = dc.check_manifest(manifest, ["dataset_id", "code_commit", "code_dirty"])
    assert res.passed is True


# ----------------------------------------------------------------------
# Fail-closed
# ----------------------------------------------------------------------

def test_columna_faltante_no_produce_pass_silencioso():
    w = _windows().drop(columns=["active_frame_count"])
    res = dc.check_null_window_fraction(w, minimum=0.20)
    assert res.passed is False
    assert "no se puede verificar" in res.detail


def test_tabla_vacia_no_produce_pass_silencioso():
    empty = pd.DataFrame(columns=["active_frame_count"])
    assert dc.check_null_window_fraction(empty, minimum=0.0).passed is False


def test_reporte_vacio_no_es_pass():
    assert dc.ValidationReport().passed is False


def test_clave_primaria_duplicada_es_fail():
    w = pd.concat([_windows(n=2), _windows(n=2)], ignore_index=True)
    res = dc.check_primary_key_unique(
        w, ["session_key", "cutoff_ns", "window_spec_id"], "windows_ml"
    )
    assert res.passed is False

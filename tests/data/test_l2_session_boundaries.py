"""Continuidad entre sesiones L2 consecutivas (tools/validate_l2_session_boundaries.py).

Un downloader puede confirmar que el archivo de un dia llego; no prueba que el libro
empalme sin discontinuidad real contra el dia anterior. Estos tests fijan fixtures
sinteticas minimas para los tres casos que importan: empalme normal, fin de semana, e
inversion de reloj -- y confirman que un gap que no calza con ninguno de los dos patrones
esperados queda explicitamente para revision, nunca aceptado en silencio.
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tools.validate_l2_session_boundaries import (
    EXPECTED_CONTINUOUS, EXPECTED_WEEKEND, FAIL_CLOCK_INVERSION, GAP_UNCLASSIFIED,
    classify_gap, validate_boundaries)

US = 1_000_000
TICK = 0.1


def _write_session(base, session: str, first_ts_us: int, last_ts_us: int) -> None:
    """Sesion minima: una fila L2 y una L1 en cada extremo del rango (basta para medir bounds)."""
    l2 = pd.DataFrame(dict(
        side=[0, 0], operation=[0, 0], level=[0, 0], size=[5, 5],
        source_row=[0, 1], ts_us=[first_ts_us, last_ts_us], price_tick=[1000, 1000]))
    l1 = pd.DataFrame(dict(
        side=[2, 2], size=[1, 1], source_row=[2, 3],
        ts_us=[first_ts_us, last_ts_us], price_tick=[1000, 1000]))
    (base / "l2_depth").mkdir(parents=True, exist_ok=True)
    (base / "l1_quotes").mkdir(parents=True, exist_ok=True)
    (base / "manifests").mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(l2, preserve_index=False), base / "l2_depth" / f"{session}.parquet")
    pq.write_table(pa.Table.from_pandas(l1, preserve_index=False), base / "l1_quotes" / f"{session}.parquet")
    (base / "manifests" / f"{session}.manifest.json").write_text(
        json.dumps(dict(conversion=dict(tick_size=TICK))), encoding="utf-8")


# --------------------------------------------------------------------------------- classify_gap (pura, sin IO)

def test_lunes_a_martes_gap_chico_es_continuo():
    assert classify_gap(date(2026, 6, 15), date(2026, 6, 16), 2.0) == EXPECTED_CONTINUOUS


def test_domingo_a_lunes_gap_chico_es_continuo():
    """Medido contra los 30 dias reales de GC: domingo tambien empalma liso con el lunes."""
    assert classify_gap(date(2026, 6, 14), date(2026, 6, 15), 1.5) == EXPECTED_CONTINUOUS


def test_viernes_a_lunes_gap_grande_es_fin_de_semana_esperado():
    assert classify_gap(date(2026, 6, 12), date(2026, 6, 15), 56 * 3600) == EXPECTED_WEEKEND


def test_viernes_a_domingo_gap_grande_es_fin_de_semana_esperado():
    assert classify_gap(date(2026, 6, 12), date(2026, 6, 14), 48 * 3600) == EXPECTED_WEEKEND


def test_cualquier_gap_negativo_es_inversion_de_reloj():
    """Retractacion 2026-09-23: el 'solapamiento de bootstrap' (-4 a -8s) era un artefacto del bug de
    unidades de la fraccion de segundo (100 ns sumados como us). No hay excepcion: todo gap negativo falla."""
    assert classify_gap(date(2026, 6, 15), date(2026, 6, 16), -1.0) == FAIL_CLOCK_INVERSION
    assert classify_gap(date(2026, 6, 15), date(2026, 6, 16), -7.6) == FAIL_CLOCK_INVERSION
    assert classify_gap(date(2026, 6, 12), date(2026, 6, 15), -1.0) == FAIL_CLOCK_INVERSION
    assert classify_gap(date(2026, 6, 15), date(2026, 6, 16), 0.0) == EXPECTED_CONTINUOUS

def test_lunes_a_martes_con_gap_de_dias_queda_sin_clasificar():
    """Dos lunes-a-martes 'nominales' pero con un gap de horas (ej: un dia faltante en el
    medio que el downloader no bajo) NO se acepta como continuo solo porque el dia-de-semana
    calzaba -- tiene que quedar marcado para revision."""
    assert classify_gap(date(2026, 6, 15), date(2026, 6, 16), 10 * 3600) == GAP_UNCLASSIFIED


def test_viernes_a_lunes_con_gap_chico_no_es_fin_de_semana_de_verdad():
    """Un gap de 10s entre un viernes y el lunes siguiente NO es plausible como cierre de
    semana real -- algo esta mal (archivo truncado, fechas mal puestas) y no se clasifica."""
    assert classify_gap(date(2026, 6, 12), date(2026, 6, 15), 10.0) == GAP_UNCLASSIFIED


def test_miercoles_a_jueves_calendario_no_consecutivo_queda_sin_clasificar():
    """Si faltan dias en el medio (calendar_days != 1) no se acepta como EXPECTED_CONTINUOUS
    aunque el gap en segundos sea chico -- la regla exige adyacencia de calendario real."""
    assert classify_gap(date(2026, 6, 15), date(2026, 6, 18), 2.0) == GAP_UNCLASSIFIED


# --------------------------------------------------------------------------------- validate_boundaries (con IO)

def test_dos_sesiones_consecutivas_normales_dan_pass(tmp_path):
    base = tmp_path / "base"
    # 20260615 (lunes) 01:00:00 -> 00:59:59; 20260616 (martes) 01:00:00 -> ...
    t0 = int(pd.Timestamp("2026-06-15 01:00:00", tz="UTC").timestamp()) * US
    t0_end = int(pd.Timestamp("2026-06-16 00:59:58", tz="UTC").timestamp()) * US
    t1 = int(pd.Timestamp("2026-06-16 01:00:00", tz="UTC").timestamp()) * US
    t1_end = int(pd.Timestamp("2026-06-17 00:59:58", tz="UTC").timestamp()) * US
    _write_session(base, "20260615", t0, t0_end)
    _write_session(base, "20260616", t1, t1_end)

    summary = validate_boundaries(base, tmp_path / "out", TICK, skip_book_check=True)
    assert summary["boundaries_checked"] == 1
    b = summary["boundaries"][0]
    assert b["continuity_status"] == "PASS"
    assert b["gap_classification"] == EXPECTED_CONTINUOUS
    assert b["right_book_bootstrap"] == "SKIPPED"


def test_inversion_de_reloj_entre_sesiones_da_fail(tmp_path):
    base = tmp_path / "base"
    t0 = int(pd.Timestamp("2026-06-15 01:00:00", tz="UTC").timestamp()) * US
    t0_end = int(pd.Timestamp("2026-06-16 01:30:00", tz="UTC").timestamp()) * US   # a proposito, mas tarde que...
    t1 = int(pd.Timestamp("2026-06-16 01:00:00", tz="UTC").timestamp()) * US       # ...el primer evento de D+1
    t1_end = int(pd.Timestamp("2026-06-17 00:59:58", tz="UTC").timestamp()) * US
    _write_session(base, "20260615", t0, t0_end)
    _write_session(base, "20260616", t1, t1_end)

    summary = validate_boundaries(base, tmp_path / "out", TICK, skip_book_check=True)
    b = summary["boundaries"][0]
    assert b["continuity_status"] == "FAIL_CLOCK_INVERSION"
    assert b["gap_classification"] == FAIL_CLOCK_INVERSION
    assert summary["fail_count"] == 1


def test_gap_no_clasificado_queda_en_review_no_en_pass(tmp_path):
    """Un 'agujero' de un dia entero faltante entre dos sesiones nominalmente lunes-martes
    (calendar_days=2, no 1) tiene que quedar REVIEW, nunca colarse como PASS."""
    base = tmp_path / "base"
    t0 = int(pd.Timestamp("2026-06-15 01:00:00", tz="UTC").timestamp()) * US
    t0_end = int(pd.Timestamp("2026-06-16 00:59:58", tz="UTC").timestamp()) * US
    t1 = int(pd.Timestamp("2026-06-17 01:00:00", tz="UTC").timestamp()) * US        # salta el 16
    t1_end = int(pd.Timestamp("2026-06-18 00:59:58", tz="UTC").timestamp()) * US
    _write_session(base, "20260615", t0, t0_end)
    _write_session(base, "20260617", t1, t1_end)

    summary = validate_boundaries(base, tmp_path / "out", TICK, skip_book_check=True)
    b = summary["boundaries"][0]
    assert b["continuity_status"] == "REVIEW_GAP_UNCLASSIFIED"
    assert summary["review_count"] == 1
    assert summary["fail_count"] == 0


def test_boundary_manifest_se_escribe_a_disco_por_frontera(tmp_path):
    base = tmp_path / "base"
    t0 = int(pd.Timestamp("2026-06-15 01:00:00", tz="UTC").timestamp()) * US
    t0_end = int(pd.Timestamp("2026-06-16 00:59:58", tz="UTC").timestamp()) * US
    t1 = int(pd.Timestamp("2026-06-16 01:00:00", tz="UTC").timestamp()) * US
    t1_end = int(pd.Timestamp("2026-06-17 00:59:58", tz="UTC").timestamp()) * US
    _write_session(base, "20260615", t0, t0_end)
    _write_session(base, "20260616", t1, t1_end)

    out = tmp_path / "out"
    validate_boundaries(base, out, TICK, skip_book_check=True)
    man = json.loads((out / "boundaries" / "20260615__20260616.json").read_text(encoding="utf-8"))
    assert man["left_session"] == "20260615" and man["right_session"] == "20260616"
    assert {"left_last_ts_us", "right_first_ts_us", "gap_seconds", "gap_classification",
            "same_contract", "right_book_bootstrap", "continuity_status"} <= set(man)


def test_book_bootstrap_roto_en_D_mas_1_degrada_a_review(tmp_path):
    """Con --skip-book-check desactivado (default), una sesion D+1 cuyo libro no reconstruye
    (nivel invalido) tiene que degradar la frontera a REVIEW aunque el gap este bien clasificado."""
    base = tmp_path / "base"
    t0 = int(pd.Timestamp("2026-06-15 01:00:00", tz="UTC").timestamp()) * US
    t0_end = int(pd.Timestamp("2026-06-16 00:59:58", tz="UTC").timestamp()) * US
    t1 = int(pd.Timestamp("2026-06-16 01:00:00", tz="UTC").timestamp()) * US
    t1_end = int(pd.Timestamp("2026-06-17 00:59:58", tz="UTC").timestamp()) * US
    _write_session(base, "20260615", t0, t0_end)

    # 20260616 con un evento L2 invalido: CHANGE en level=5 sin que exista (libro vacio) -> ABSTAIN
    l2_bad = pd.DataFrame(dict(
        side=[0, 0], operation=[1, 1], level=[5, 5], size=[5, 5],
        source_row=[0, 1], ts_us=[t1, t1_end], price_tick=[1000, 1000]))
    l1_bad = pd.DataFrame(dict(
        side=[2, 2], size=[1, 1], source_row=[2, 3], ts_us=[t1, t1_end], price_tick=[1000, 1000]))
    (base / "l2_depth").mkdir(parents=True, exist_ok=True)
    (base / "l1_quotes").mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(l2_bad, preserve_index=False), base / "l2_depth" / "20260616.parquet")
    pq.write_table(pa.Table.from_pandas(l1_bad, preserve_index=False), base / "l1_quotes" / "20260616.parquet")
    (base / "manifests" / "20260616.manifest.json").write_text(
        json.dumps(dict(conversion=dict(tick_size=TICK))), encoding="utf-8")

    summary = validate_boundaries(base, tmp_path / "out", TICK, skip_book_check=False)
    b = summary["boundaries"][0]
    assert b["right_book_bootstrap"] == "ABSTAIN_INVALID_LEVEL"
    assert b["continuity_status"] == "REVIEW_BOOK_BOOTSTRAP"

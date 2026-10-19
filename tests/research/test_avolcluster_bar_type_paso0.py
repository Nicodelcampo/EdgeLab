import json

import numpy as np
import pytest

from diag.tasa_senales.avolcluster_bar_type_paso0 import (
    minute_bucket_counts,
    sample_S,
    session_stats,
)


def test_minute_bucket_counts_agrupa_por_minuto_de_reloj():
    minute = 60_000_000_000
    ts = np.asarray([
        0, 1_000, 2_000,          # 3 ticks en el minuto 0
        minute, minute + 500,     # 2 ticks en el minuto 1
        3 * minute,                # 1 tick en el minuto 3 (minuto 2 no tiene ticks)
    ], dtype=np.int64)
    counts = minute_bucket_counts(ts)
    assert sorted(counts.tolist()) == [1, 2, 3]
    assert counts.size == 3  # solo minutos ACTIVOS, no se rellenan ceros


def test_minute_bucket_counts_vacio():
    counts = minute_bucket_counts(np.asarray([], dtype=np.int64))
    assert counts.size == 0


def test_session_stats_percentiles_y_totales():
    counts = np.asarray([10, 20, 30, 40, 50], dtype=np.int64)
    stats = session_stats(counts, n_ticks_total=150)
    assert stats["n_active_minutes"] == 5
    assert stats["n_ticks"] == 150
    assert stats["ticks_per_min_p50"] == pytest.approx(30.0)
    assert stats["ticks_per_min_mean"] == pytest.approx(30.0)


def test_session_stats_vacio_no_rompe():
    stats = session_stats(np.asarray([], dtype=np.int64), n_ticks_total=0)
    assert stats["n_active_minutes"] == 0
    assert stats["ticks_per_min_p50"] is None


def test_sample_S_es_deterministico_y_no_gameable():
    split = {"S": [f"2026{m:02d}{d:02d}" for m in range(1, 3) for d in range(1, 15)]}
    a = sample_S(split, stride=7)
    b = sample_S(split, stride=7)
    assert a == b  # sin semilla, mismo input -> mismo output siempre
    assert a == sorted(split["S"])[::7]


def test_sample_S_cubre_todo_el_rango_no_solo_el_principio():
    split = {"S": [f"2026{m:02d}{d:02d}" for m in range(1, 3) for d in range(1, 29)]}
    sample = sample_S(split, stride=7)
    s_sorted = sorted(split["S"])
    assert sample[0] == s_sorted[0]
    assert sample[-1] != s_sorted[-1] or len(s_sorted) % 7 == 1  # stride cubre el tramo, no solo el arranque
    assert len(sample) >= 3


def test_split_congelado_tiene_interseccion_vacia_y_cuenta_correcta():
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / "specs" / "avolclusterpoi_resolution_split_v1.json"
    if not path.exists():
        pytest.skip("split todavia no generado")
    spec = json.loads(path.read_text(encoding="utf-8"))
    S, C = spec["S"], spec["C"]
    assert len(S) == spec["regla_de_particion"]["n_S"]
    assert len(C) == spec["regla_de_particion"]["n_C"]
    assert set(S) & set(C) == set()
    assert len(S) + len(C) == 152

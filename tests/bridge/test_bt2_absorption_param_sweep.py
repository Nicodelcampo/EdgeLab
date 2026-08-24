from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import re
import inspect

import numpy as np

from edgelab.bridge.indicators.bigtrap2absorption import DEFAULTS, PARAM_SPEC, run
from edgelab.bridge.ticks import make_synthetic
from tools import bt2_absorption_param_sweep as S

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "specs" / "bt2_absorption_target_free_sweep_v1.json"
SPLIT = ROOT / "specs" / "bt2_absorption_gate1_split_v1.json"
CHAIN = ROOT / "docs" / "research" / "CADENA_FRONTMONTH_GC.json"


def test_spec_cubre_exactamente_los_21_parametros_y_grid_no_duplica_headline():
    spec = S.load_json(SPEC)
    S.validate_campaign_spec(spec, DEFAULTS, PARAM_SPEC)
    oat = S.build_configs(spec, DEFAULTS, stage="oat")
    all_configs = S.build_configs(spec, DEFAULTS, stage="all")
    assert len(DEFAULTS) == 21
    assert len(oat) == 51
    assert len(all_configs) == 99
    assert len({row["config_id"] for row in all_configs}) == 99
    assert {row["axis"] for row in oat if row["stage"] == "oat"} == set(DEFAULTS)


def test_split_real_reproduce_152_133_19_y_fechas_selladas():
    assignment, sessions, p1, sealed = S.derive_universe(
        S.load_json(CHAIN), S.load_json(SPLIT)
    )
    assert (len(sessions), len(p1), len(sealed)) == (152, 133, 19)
    assert sealed == [
        "20251205", "20251217", "20251230", "20260112", "20260122",
        "20260203", "20260213", "20260225", "20260309", "20260319",
        "20260331", "20260413", "20260423", "20260505", "20260515",
        "20260527", "20260608", "20260618", "20260630",
    ]
    assert all(assignment[day].startswith("GC ") for day in sessions)


def test_session_canonica_no_depende_del_td_crudo_y_corta_a_las_17_ct():
    ct = ZoneInfo("America/Chicago")
    before = int(datetime(2026, 3, 24, 16, 59, tzinfo=ct).timestamp() * 1e9)
    opening = int(datetime(2026, 3, 24, 17, 0, tzinfo=ct).timestamp() * 1e9)
    assert list(S.session_dates_from_ns(np.array([before, opening], dtype=np.int64))) == [
        "20260324", "20260325"
    ]
    assert "td" not in inspect.signature(S.session_dates_from_ns).parameters


def test_overlap_exacto_y_tolerante_son_uno_a_uno():
    a = {
        "GC 02-26|20260105|long|100000000000|200|202",
        "GC 02-26|20260105|short|200000000000|210|212",
    }
    b = {
        "GC 02-26|20260105|long|110000000000|202|204",
        "GC 02-26|20260105|short|400000000000|210|212",
    }
    assert S.exact_jaccard(a, a) == 1.0
    assert S.exact_jaccard(a, b) == 0.0
    assert S.tolerant_jaccard(
        a, b, time_tolerance_seconds=60, price_tolerance_ticks=2
    ) == 1 / 3


def test_min_export_volume_y_draw_zone_band_son_noop_en_kernel_actual():
    ticks = make_synthetic(n_sessions=1, ticks_per_session=6000, seed=19)
    base = run(ticks, params=DEFAULTS)
    export = run(ticks, params={**DEFAULTS, "MinExportVolume": 1000.0})
    draw = run(ticks, params={**DEFAULTS, "DrawZoneBand": False})
    assert export["events"] == base["events"]
    assert export["zones"] == base["zones"]
    assert draw["events"] == base["events"]
    assert draw["zones"] == base["zones"]


def test_runner_no_importa_motor_de_outcomes():
    source = inspect.getsource(S)
    assert "from edgelab.engine" not in source
    assert "import edgelab.engine" not in source
    # Insensible al espaciado del JSON: el runner usa separadores compactos.
    # Ademas exige que NUNCA se emita True, que es la propiedad que importa.
    flags = re.findall(r'"outcomes_opened"\s*:\s*(True|False)', source)
    assert flags, "el runner no declara outcomes_opened en ninguna salida"
    assert set(flags) == {"False"}, f"outcomes_opened emitido como True: {flags}"
    sealed = re.findall(r'"sealed_outcomes_opened"\s*:\s*(True|False)', source)
    assert set(sealed) == {"False"}, f"sealed_outcomes_opened emitido como True: {sealed}"


def test_subconjunto_de_contratos_nunca_declara_cobertura_completa():
    """Un --contracts parcial debe marcarse como parcial, no como COMPLETE_TARGET_FREE."""
    source = inspect.getsource(S)
    # el estado parcial existe y es alcanzable
    assert "COMPLETE_TARGET_FREE_PARTIAL_CONTRACTS" in source
    # y el resultado declara explicitamente que contratos se midieron y cuales no
    for campo in ("contracts_measured", "contracts_omitted", "full_contract_coverage"):
        assert campo in source, f"el resultado no declara {campo}"
    # COMPLETE_TARGET_FREE a secas debe estar condicionado a la igualdad con CONTRACTS
    assert "set(contracts)==set(CONTRACTS)" in source


def test_finalize_respeta_el_subconjunto_de_contratos():
    """finalize() debe iterar el subconjunto recibido, no la constante global."""
    src = inspect.getsource(S.finalize)
    assert "for contract in contracts:" in src
    assert "for contract in CONTRACTS:" not in src

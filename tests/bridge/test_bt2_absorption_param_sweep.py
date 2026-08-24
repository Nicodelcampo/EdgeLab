from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pytest
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



# ---------- finalize: tests funcionales, no de inspeccion de fuente ----------

def _partial(tmp, cfg_id, contract, sessions, *, commit="abc123", ev=None):
    """Escribe un parcial minimo con la forma que finalize espera."""
    import json
    d = tmp / "partials"; d.mkdir(exist_ok=True)
    if ev is None:   # formato real: contract|session|dir|ts_ns|lo2|hi2
        ev = tuple(f"{contract}|{s}|long|{1764118034836000000 + i}|83421|83427"
                   for i, s in enumerate(sessions))
    rec = {"schema": "bt2_absorption_target_free_partial_v1", "target_free": True,
           "outcomes_opened": False, "config_id": cfg_id, "contract": contract,
           "input_sha256": "sha_" + contract, "code_commit": commit,
           "params_sha256": "p", "elapsed_seconds": 1.0,
           "result": {"contract": contract, "event_keys": list(ev),
                      "sessions": {s: {"n_buckets": 10, "n_zones": 1, "n_pass": 1,
                                       "n_residual": 0, "n_long": 1, "n_short": 0,
                                       "n_active": 1, "n_invalidated": 0, "n_expired": 0,
                                       "touches_sum": 0, "pass_rate": 0.1} for s in sessions}}}
    (d / f"{cfg_id}__{contract.replace(' ', '_')}.json").write_text(
        json.dumps(rec), encoding="utf-8")
    return rec


def _fake_git(head):
    """rev-parse devuelve el head; status devuelve vacio (arbol limpio)."""
    def g(*a):
        return "" if "status" in a else head
    return g


def _cfgs(cfg_id):
    return [{"config_id": cfg_id, "stage": "headline", "axis": None, "params": {"a": 1}}]


def _spec():
    return {"overlap": {"time_tolerance_seconds": 0, "price_tolerance_ticks": 0}}


def test_subconjunto_de_contratos_no_exige_sesiones_ajenas(tmp_path, monkeypatch):
    """GC 02-26 aporta sus sesiones; finalize no debe pedir las de los otros tres."""
    cid = "cfg1"
    _partial(tmp_path, cid, "GC 02-26", ["20251126", "20251127"])
    monkeypatch.setattr(S, "_git", _fake_git("abc123"))
    out = S.finalize(tmp_path, _cfgs(cid),
                     {"GC 02-26": {"sha256": "sha_GC 02-26"}},
                     head_start="abc123", spec=_spec(),
                     p1_sessions=["20251126", "20251127"], contracts=("GC 02-26",))
    assert out["status"] == "COMPLETE_TARGET_FREE_PARTIAL_CONTRACTS"
    assert out["contracts_measured"] == ["GC 02-26"]
    assert out["promotion_eligible"] is False, "subconjunto nunca es promocionable"


def test_sesion_faltante_aborta_y_dice_cual(tmp_path, monkeypatch):
    cid = "cfg1"
    _partial(tmp_path, cid, "GC 02-26", ["20251126"])
    monkeypatch.setattr(S, "_git", _fake_git("abc123"))
    with pytest.raises(ValueError) as e:
        S.finalize(tmp_path, _cfgs(cid), {"GC 02-26": {"sha256": "sha_GC 02-26"}},
                   head_start="abc123", spec=_spec(),
                   p1_sessions=["20251126", "20251127"], contracts=("GC 02-26",))
    assert "20251127" in str(e.value), "el error debe nombrar la sesion faltante"
    assert "1/2" in str(e.value)


def test_procedencia_mezclada_no_puede_ser_complete(tmp_path, monkeypatch):
    """Parciales de otro commit que el de finalize => diagnostico, no COMPLETE."""
    cid = "cfg1"
    _partial(tmp_path, cid, "GC 02-26", ["20251126"], commit="viejo999")
    monkeypatch.setattr(S, "_git", _fake_git("nuevo111"))
    out = S.finalize(tmp_path, _cfgs(cid), {"GC 02-26": {"sha256": "sha_GC 02-26"}},
                     head_start="nuevo111", spec=_spec(),
                     p1_sessions=["20251126"], contracts=("GC 02-26",))
    assert out["status"] == "DIAGNOSTIC_REAGGREGATION_MIXED_CODE"
    assert out["finalize_matches_partials"] is False
    assert out["promotion_eligible"] is False
    assert out["partials_code_commit"] == ["viejo999"]


def test_commit_desconocido_invalida_igual_que_una_mezcla(tmp_path, monkeypatch):
    cid = "cfg1"
    rec = _partial(tmp_path, cid, "GC 02-26", ["20251126"])
    import json
    f = tmp_path / "partials" / f"{cid}__GC_02-26.json"
    rec.pop("code_commit")                      # parcial sin procedencia
    f.write_text(json.dumps(rec), encoding="utf-8")
    monkeypatch.setattr(S, "_git", _fake_git("abc123"))
    out = S.finalize(tmp_path, _cfgs(cid), {"GC 02-26": {"sha256": "sha_GC 02-26"}},
                     head_start="abc123", spec=_spec(),
                     p1_sessions=["20251126"], contracts=("GC 02-26",))
    assert out["partials_code_commit"] == ["?"]
    assert out["status"] == "DIAGNOSTIC_REAGGREGATION_MIXED_CODE"
    assert out["promotion_eligible"] is False

import pytest

from edgelab.data.contract_regime import build_contract_regime
from edgelab.research.nq_contract_regime_manifest_build import (
    build_nq_manifest_inputs, contract_metadata_from_daily, parse_contract_label,
)


def test_parse_contract_label_underscore_and_space():
    assert parse_contract_label("NQ 09-25") == {
        "root": "NQ", "contract": "NQ 09-25", "expiry_ordinal": 202509}
    assert parse_contract_label("NQ_03-26") == {
        "root": "NQ", "contract": "NQ 03-26", "expiry_ordinal": 202603}


def test_parse_contract_label_rejects_unknown_shape():
    with pytest.raises(ValueError):
        parse_contract_label("NQ-2025-09")


def test_contract_metadata_derives_bounds_from_observed_dates():
    meta = contract_metadata_from_daily("NQ 09-25", [20260201, 20260115, 20260228])
    assert meta["first_trade_date"] == 20260115
    assert meta["last_trade_date"] == 20260228


def test_build_nq_manifest_inputs_feeds_a_valid_regime():
    per_contract = {
        "NQ 03-26": {20260201: 100.0, 20260202: 400.0, 20260203: 500.0},
        "NQ 06-26": {20260202: 50.0, 20260203: 600.0},
    }
    inputs = build_nq_manifest_inputs(per_contract, {"dataset": "test-fixture"})
    manifest = build_contract_regime(**inputs)
    assert manifest["schema_version"] == "contract_regime_manifest_v1"
    by_date = {row["trade_date"]: row for row in manifest["daily_assignments"]}
    # dia 1: sin sesion previa -> no elegible
    assert by_date[20260201]["eligible"] is False
    # dia 2: usa volumen de dia 1 (solo NQ 03-26 tenia dato) -> inicializa en 03-26
    assert by_date[20260202]["active_contract"] == "NQ 03-26"
    # dia 3: usa volumen de dia 2 -- 03-26=400 vs 06-26=50, 03-26 sigue liderando
    assert by_date[20260203]["active_contract"] == "NQ 03-26"


def test_build_nq_manifest_inputs_rejects_empty():
    with pytest.raises(ValueError):
        build_nq_manifest_inputs({}, {"dataset": "x"})

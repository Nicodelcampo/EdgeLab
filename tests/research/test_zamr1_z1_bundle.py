# -*- coding: utf-8 -*-
import json
from pathlib import Path

import pytest

from edgelab.research.zamr1.z1_bundle import (
    deterministic_identity,
    materialize_static_bundle,
    validate_source_observation,
    write_hash_ledger,
)


def source():
    return {"filename": "ticks.parquet", "sha256": "a" * 64, "contract": "06-26"}


def instrument():
    return {"instrument": "6E", "tick_size": 0.00005}


def observed():
    return {
        "filename": "ticks.parquet",
        "sha256": "a" * 64,
        "instrument": "6E",
        "contract": "06-26",
        "tick_size": 0.00005,
    }


def test_source_contract_match_passes():
    validate_source_observation(source(), observed(), instrument())


def test_source_contract_mismatch_fails_closed():
    bad = observed()
    bad["contract"] = "09-26"
    with pytest.raises(RuntimeError, match="SOURCE_CONTRACT_MISMATCH"):
        validate_source_observation(source(), bad, instrument())


def test_missing_observation_fails_closed():
    bad = observed()
    del bad["tick_size"]
    with pytest.raises(RuntimeError, match="SOURCE_OBSERVATION_INCOMPLETE"):
        validate_source_observation(source(), bad, instrument())


def test_deterministic_identity_has_no_runtime_fields():
    a = deterministic_identity(
        plan_sha256="p" * 64,
        code_commit="c" * 40,
        sources=[observed()],
        data_artifacts={"events_long.parquet": "e" * 64},
    )
    b = deterministic_identity(
        plan_sha256="p" * 64,
        code_commit="c" * 40,
        sources=[observed()],
        data_artifacts={"events_long.parquet": "e" * 64},
    )
    assert a == b
    assert not ({"created_at_utc", "seconds", "ru_maxrss", "hostname"} & set(a))


def test_static_bundle_and_hash_ledger(tmp_path):
    root = tmp_path / "repo"
    plan = root / "specs/zamr1_z1_pilot_plan_2026-08-12.json"
    files = {
        plan: "{}\n",
        root / "specs/zamr1_structural_contract_v0.json": "{}\n",
        root / "specs/zamr1_parameter_registry_v0.json": "{}\n",
        root / "edgelab/research/zamr1/structural_contract.py": "PASS = True\n",
    }
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, "utf-8")
    out = tmp_path / "bundle"
    copied = materialize_static_bundle(out, root, plan)
    assert set(copied) == {"contract.json", "parameter_registry.json", "structural_contract.py", "pilot_plan.json"}
    hashes = write_hash_ledger(out, list(copied))
    assert hashes == copied
    assert len((out / "hashes.sha256").read_text("utf-8").splitlines()) == 4

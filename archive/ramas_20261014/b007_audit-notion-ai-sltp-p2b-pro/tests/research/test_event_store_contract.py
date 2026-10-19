# -*- coding: utf-8 -*-
import copy

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from edgelab.research.event_store_contract import (
    EventStoreContractError,
    normalize_rows,
    stamp_identity,
    validate_parquet_against_rows,
)


def contract():
    return {
        "exact_columns": True,
        "fields": [
            {"name": "event_id", "type": "str", "nullable": False, "non_empty": True},
            {"name": "identity_sha256", "type": "str", "nullable": False, "non_empty": True},
            {"name": "ordinal", "type": "int", "nullable": False},
            {"name": "score", "type": "float", "nullable": False},
        ],
        "sort_keys": ["ordinal", "event_id"],
        "identity_column": "identity_sha256",
        "identity_fields": ["event_id", "ordinal", "score"],
        "unique_fields": ["event_id", "identity_sha256"],
    }


def row(event_id="a", ordinal=0, score=1.0):
    return stamp_identity(
        {"event_id": event_id, "identity_sha256": "", "ordinal": ordinal, "score": score},
        contract(),
    )


def test_canonical_rows_are_sorted_and_typed():
    out = normalize_rows([row("b", 2), row("a", 1)], contract())
    assert [x["event_id"] for x in out] == ["a", "b"]
    assert all(type(x["score"]) is float for x in out)


def test_duplicate_event_id_is_rejected():
    with pytest.raises(EventStoreContractError, match="duplicate values"):
        normalize_rows([row("a", 1, 1.0), row("a", 2, 2.0)], contract())


def test_identity_mutation_is_rejected():
    mutated = row()
    mutated["score"] = 2.0
    with pytest.raises(EventStoreContractError, match="identity_sha256 mismatch"):
        normalize_rows([mutated], contract())


def test_undeclared_outcome_column_is_rejected():
    mutated = row()
    mutated["mfe_ticks"] = 99
    with pytest.raises(EventStoreContractError, match="undeclared fields"):
        normalize_rows([mutated], contract())


def test_parquet_transport_can_change_but_logical_rows_match(tmp_path):
    rows = [row("a", 1, 1.0), row("b", 2, 2.0)]
    path = tmp_path / "events.parquet"
    pq.write_table(pa.Table.from_pylist(list(reversed(rows))), path, compression="gzip")
    result = validate_parquet_against_rows(path, rows, contract())
    assert result["ready"] is True
    assert result["logical_identity"] == "PASS"
    assert result["parquet_matches_checkpoints_1to1"] is True


def test_logical_mutation_fails_even_with_same_schema_and_row_count(tmp_path):
    expected = [row("a", 1, 1.0), row("b", 2, 2.0)]
    mutated = copy.deepcopy(expected)
    mutated[0]["score"] = 3.0
    mutated[0] = stamp_identity(mutated[0], contract())
    path = tmp_path / "mutated.parquet"
    pq.write_table(pa.Table.from_pylist(mutated), path)
    with pytest.raises(EventStoreContractError, match="logical payload differs"):
        validate_parquet_against_rows(path, expected, contract())

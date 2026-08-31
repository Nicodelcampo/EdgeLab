# -*- coding: utf-8 -*-
"""Synthetic ground-truth tests for tools/export_bt2_v2_coords_parquet.py.

Pure target-free unit tests on the aggregation/verification logic -- no real
ticks, no Kaggle runtime, no fail-closed gate bypass. The fail-closed gates
themselves (verify_runtime_execution_gates etc.) are already covered by
tests/research/test_bigtrap2_nq_tickframes_sweep.py; this file only tests the
code this tool adds: raw per-zone row schema and the frozen-result cross-check.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from tools.export_bt2_v2_coords_parquet import (
    COORD_COLUMNS,
    TARGET_CFG_ID,
    verify_against_frozen_result,
)


def _fake_row(session_id: str, contract: str = "NQ 09-25") -> dict:
    return {
        "contract": contract,
        "session_id": session_id,
        "bar_time_ns": 1_000_000_000,
        "side": "B",
        "top": 100.5,
        "bottom": 100.0,
        "width_ticks": 2.0,
        "bar_idx": 5,
    }


class TestVerifyAgainstFrozenResult:
    def test_matching_count_and_coverage_passes(self, tmp_path):
        rows = [_fake_row(f"2026010{i}") for i in range(1, 4)]  # 3 rows, 3 sessions
        frozen = {
            "results": [
                {"cfg_id": TARGET_CFG_ID, "total_events": 3, "sessions_with_events": 3},
                {"cfg_id": "other_cfg", "total_events": 999, "sessions_with_events": 999},
            ]
        }
        frozen_path = tmp_path / "frozen.json"
        frozen_path.write_text(json.dumps(frozen), encoding="utf-8")

        check = verify_against_frozen_result(rows, frozen_path)
        assert check["total_events"] == 3
        assert check["sessions_with_events"] == 3
        assert check["matches_frozen_v2_result"] is True

    def test_event_count_mismatch_raises(self, tmp_path):
        rows = [_fake_row("20260101"), _fake_row("20260101")]  # 2 rows, 1 session
        frozen = {"results": [{"cfg_id": TARGET_CFG_ID, "total_events": 5, "sessions_with_events": 1}]}
        frozen_path = tmp_path / "frozen.json"
        frozen_path.write_text(json.dumps(frozen), encoding="utf-8")

        with pytest.raises(RuntimeError, match="event count disagrees"):
            verify_against_frozen_result(rows, frozen_path)

    def test_session_coverage_mismatch_raises(self, tmp_path):
        rows = [_fake_row("20260101"), _fake_row("20260101")]  # 2 rows, 1 session
        frozen = {"results": [{"cfg_id": TARGET_CFG_ID, "total_events": 2, "sessions_with_events": 2}]}
        frozen_path = tmp_path / "frozen.json"
        frozen_path.write_text(json.dumps(frozen), encoding="utf-8")

        with pytest.raises(RuntimeError, match="session coverage disagrees"):
            verify_against_frozen_result(rows, frozen_path)

    def test_missing_cfg_id_in_frozen_result_raises(self, tmp_path):
        rows = [_fake_row("20260101")]
        frozen = {"results": [{"cfg_id": "not_the_target", "total_events": 1, "sessions_with_events": 1}]}
        frozen_path = tmp_path / "frozen.json"
        frozen_path.write_text(json.dumps(frozen), encoding="utf-8")

        with pytest.raises(RuntimeError, match="absent from frozen V2 result"):
            verify_against_frozen_result(rows, frozen_path)

    def test_zero_rows_matches_zero_frozen_events(self, tmp_path):
        frozen = {"results": [{"cfg_id": TARGET_CFG_ID, "total_events": 0, "sessions_with_events": 0}]}
        frozen_path = tmp_path / "frozen.json"
        frozen_path.write_text(json.dumps(frozen), encoding="utf-8")

        check = verify_against_frozen_result([], frozen_path)
        assert check["total_events"] == 0
        assert check["matches_frozen_v2_result"] is True


class TestCoordSchema:
    def test_rows_convert_to_dataframe_with_expected_columns(self):
        rows = [_fake_row("20260101"), _fake_row("20260102", contract="NQ 12-25")]
        df = pd.DataFrame(rows, columns=COORD_COLUMNS)
        assert list(df.columns) == COORD_COLUMNS
        assert len(df) == 2
        assert df["side"].isin(["B", "S"]).all()

    def test_dataframe_roundtrips_through_parquet(self, tmp_path):
        rows = [_fake_row("20260101")]
        df = pd.DataFrame(rows, columns=COORD_COLUMNS)
        path = tmp_path / "coords.parquet"
        df.to_parquet(path, index=False)
        reloaded = pd.read_parquet(path)
        assert reloaded.equals(df)

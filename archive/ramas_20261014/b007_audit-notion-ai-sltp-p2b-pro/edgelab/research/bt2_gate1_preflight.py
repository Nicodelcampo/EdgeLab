"""Fail-closed, target-free preflight for BT2Absorption Gate 1.

This module deliberately contains only identity, integrity, ordering, and
coverage checks. The CLI loads the analytical runner only after this preflight
has passed and the caller has supplied the frozen authorization token.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Any

import numpy as np

REQUIRED_COLUMNS = (
    "ts_utc_ns", "ts_local_ns", "sequence", "price_ticks", "bid_ticks",
    "ask_ticks", "volume", "aggressor", "tick_type", "instrument",
    "contract", "source_file", "source_row",
)
PARTITION_COLUMNS = (
    "ts_utc_ns", "source_row", "sequence", "price_ticks", "bid_ticks",
    "ask_ticks", "volume",
)


def file_sha256(path: Path) -> str:
    h = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("utf-8")
    return sha256(raw).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git_state(repo_root: Path) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", *args], cwd=repo_root, text=True
        ).strip()
    return {
        "head": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "dirty": bool(git("status", "--porcelain")),
    }


def cme_session_dates(ts_ns: np.ndarray) -> np.ndarray:
    """CME ETH trade date, [17:00 CT, next 17:00 CT), DST-aware."""
    import pandas as pd
    idx = pd.to_datetime(np.asarray(ts_ns, dtype=np.int64), unit="ns", utc=True)
    local = idx.tz_convert("America/Chicago")
    days = np.asarray(local.normalize().tz_localize(None), dtype="datetime64[D]")
    days = days + (np.asarray(local.hour) >= 17).astype("timedelta64[D]")
    return np.char.replace(np.datetime_as_string(days, unit="D"), "-", "").astype("U8")


def _update_partition_hash(handle, arrays: dict[str, np.ndarray], sl: slice) -> None:
    matrix = np.column_stack([
        np.asarray(arrays[name][sl], dtype="<i8") for name in PARTITION_COLUMNS
    ])
    handle.update(np.ascontiguousarray(matrix, dtype="<i8").tobytes(order="C"))


def _expected_registry_map(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = registry.get("sessions")
    if not isinstance(rows, list) or not rows:
        raise ValueError("registry.sessions must be a non-empty list")
    out = {}
    for row in rows:
        sid = str(row["cme_session_id"])
        if sid in out:
            raise ValueError(f"duplicate session in registry: {sid}")
        out[sid] = row
    if len(out) != int(registry["selection"]["n_sessions"]):
        raise ValueError("registry session count does not match selection.n_sessions")
    return out


def validate_registry(registry: dict[str, Any], input_registry: dict[str, Any]) -> None:
    if registry.get("schema") != "bt2a_gate1_session_registry_v1":
        raise ValueError("unexpected session registry schema")
    if registry.get("frozen_before_outcomes") is not True:
        raise ValueError("session registry is not frozen before outcomes")
    if registry.get("campaign_outcomes_opened") is not False:
        raise ValueError("registry says campaign outcomes were already opened")
    selected = tuple(registry["selection"]["contracts"])
    if selected != ("GC 02-26", "GC 04-26"):
        raise ValueError(f"clean-76 contract set changed: {selected}")
    if int(registry["selection"]["n_sessions"]) != 76:
        raise ValueError("clean-76 amendment must contain exactly 76 sessions")
    _expected_registry_map(registry)
    if input_registry.get("schema") != "bt2a_gate1_input_registry_v1":
        raise ValueError("unexpected input registry schema")
    if tuple(input_registry["selected_contracts"]) != selected:
        raise ValueError("input and session registries disagree on selected contracts")


def scan_selected_inputs(
    data_dir: Path,
    registry: dict[str, Any],
    input_registry: dict[str, Any],
    *,
    batch_size: int = 262_144,
) -> dict[str, Any]:
    """Recompute every selected invariant and session digest from Parquet.

    Files may contain inventory rows outside the selected sessions. Those rows
    are audited but never admitted into the selected universe.
    """
    import pyarrow.parquet as pq

    expected_sessions = _expected_registry_map(registry)
    selected_contracts = tuple(registry["selection"]["contracts"])
    observed = {
        sid: {
            "rows": 0,
            "first_ts_utc_ns": None,
            "last_ts_utc_ns": None,
            "partition": sha256(),
        }
        for sid in expected_sessions
    }
    contracts_out: dict[str, Any] = {}

    for contract in selected_contracts:
        spec = input_registry["contracts"][contract]
        path = Path(data_dir) / str(spec["parquet_file"])
        if not path.is_file():
            raise FileNotFoundError(path)
        actual_hash = file_sha256(path)
        if actual_hash != spec["parquet_sha256"]:
            raise ValueError(f"{contract}: parquet sha256 mismatch")
        parquet = pq.ParquetFile(path)
        if tuple(parquet.schema_arrow.names) != REQUIRED_COLUMNS:
            raise ValueError(f"{contract}: canonical_tick_v1 schema mismatch")
        if parquet.metadata.num_rows != int(spec["rows"]):
            raise ValueError(f"{contract}: row count mismatch")

        n = 0
        previous_ts = previous_source = None
        sessions_in_file: set[str] = set()
        domains = defaultdict(set)
        for batch in parquet.iter_batches(
            batch_size=batch_size, columns=list(REQUIRED_COLUMNS), use_threads=True
        ):
            arrays = {
                name: batch.column(i).to_numpy(zero_copy_only=False)
                for i, name in enumerate(REQUIRED_COLUMNS)
            }
            k = len(arrays["ts_utc_ns"])
            expected_order = np.arange(n, n + k, dtype=np.int64)
            ts = np.asarray(arrays["ts_utc_ns"], dtype=np.int64)
            source = np.asarray(arrays["source_row"], dtype=np.int64)
            sequence = np.asarray(arrays["sequence"], dtype=np.int64)
            if not np.array_equal(source, expected_order):
                raise ValueError(f"{contract}: source_row is not exact physical order")
            if not np.array_equal(sequence, expected_order):
                raise ValueError(f"{contract}: sequence is not exact physical order")
            if not np.array_equal(
                np.asarray(arrays["ts_local_ns"], dtype=np.int64), ts
            ):
                raise ValueError(f"{contract}: UTC/local identity changed")
            if previous_ts is not None and (
                ts[0] < previous_ts or
                (ts[0] == previous_ts and source[0] <= previous_source)
            ):
                raise ValueError(f"{contract}: order regressed across a batch")
            if k > 1:
                dt = np.diff(ts)
                ds = np.diff(source)
                if np.any(dt < 0) or np.any((dt == 0) & (ds <= 0)):
                    raise ValueError(f"{contract}: unstable causal order")
            previous_ts, previous_source = int(ts[-1]), int(source[-1])
            price = np.asarray(arrays["price_ticks"], dtype=np.int64)
            bid = np.asarray(arrays["bid_ticks"], dtype=np.int64)
            ask = np.asarray(arrays["ask_ticks"], dtype=np.int64)
            volume = np.asarray(arrays["volume"])
            if np.any(volume <= 0):
                raise ValueError(f"{contract}: non-positive volume")
            if np.any(bid > ask):
                raise ValueError(f"{contract}: bid > ask")
            if np.any((price < bid) | (price > ask)):
                raise ValueError(f"{contract}: trade outside spread")
            for key in ("instrument", "contract", "tick_type"):
                domains[key].update(str(x) for x in np.unique(arrays[key]).tolist())

            dates = cme_session_dates(ts)
            cuts = np.flatnonzero(dates[1:] != dates[:-1]) + 1 if k > 1 else np.array([], dtype=np.int64)
            starts = np.concatenate(([0], cuts))
            ends = np.concatenate((cuts, [k]))
            for lo, hi in zip(starts, ends):
                sid = str(dates[lo])
                sessions_in_file.add(sid)
                target = expected_sessions.get(sid)
                if target is None or target["contract"] != contract:
                    continue
                rec = observed[sid]
                rec["rows"] += int(hi - lo)
                first, last = int(ts[lo]), int(ts[hi - 1])
                if rec["first_ts_utc_ns"] is None:
                    rec["first_ts_utc_ns"] = first
                rec["last_ts_utc_ns"] = last
                _update_partition_hash(rec["partition"], arrays, slice(int(lo), int(hi)))
            n += k

        expected_domains = {
            "instrument": {"GC"}, "contract": {contract}, "tick_type": {"trade"}
        }
        if {k: set(v) for k, v in domains.items()} != expected_domains:
            raise ValueError(f"{contract}: domain mismatch {dict(domains)}")
        contracts_out[contract] = {
            "parquet_file": path.name,
            "sha256": actual_hash,
            "rows": n,
            "sessions_in_file": len(sessions_in_file),
        }

    missing, mismatched = [], []
    selected_rows = []
    for sid, expected in expected_sessions.items():
        got = observed[sid]
        if not got["rows"]:
            missing.append(sid)
            continue
        actual = {
            "cme_session_id": sid,
            "contract": expected["contract"],
            "rows": got["rows"],
            "first_ts_utc_ns": got["first_ts_utc_ns"],
            "last_ts_utc_ns": got["last_ts_utc_ns"],
            "partition_sha256": got["partition"].hexdigest(),
        }
        for field in ("rows", "first_ts_utc_ns", "last_ts_utc_ns", "partition_sha256"):
            if field in expected and actual[field] != expected[field]:
                mismatched.append({"session": sid, "field": field,
                                   "expected": expected[field], "actual": actual[field]})
        selected_rows.append(actual)
    if missing or mismatched:
        raise ValueError(
            f"selected universe failed: missing={missing[:5]} mismatches={mismatched[:3]}"
        )
    if len(selected_rows) != 76:
        raise AssertionError("selected universe did not reproduce 76 sessions")
    return {"contracts": contracts_out, "sessions": selected_rows}


def run_preflight(
    *,
    data_dir: Path,
    session_registry_path: Path,
    input_registry_path: Path,
    repo_root: Path | None = None,
    require_clean_git: bool = True,
) -> dict[str, Any]:
    registry = load_json(session_registry_path)
    inputs = load_json(input_registry_path)
    validate_registry(registry, inputs)
    git = None
    if repo_root is not None:
        git = git_state(repo_root)
        if require_clean_git and git["dirty"]:
            raise RuntimeError("formal preflight requires a clean git worktree")
    scanned = scan_selected_inputs(Path(data_dir), registry, inputs)
    return {
        "schema": "bt2a_gate1_preflight_result_v1",
        "status": "PASS_TARGET_FREE_READY",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "CAMPAIGN_OUTCOMES_OPENED": False,
        "PREEXISTING_OUTCOME_EXPOSURE": "YES_OUTSIDE_SELECTED_76",
        "EDGE_DECLARED": False,
        "selected_contracts": registry["selection"]["contracts"],
        "selected_sessions": len(scanned["sessions"]),
        "git": git,
        "inputs": scanned["contracts"],
        "session_registry_sha256": file_sha256(session_registry_path),
        "input_registry_sha256": file_sha256(input_registry_path),
    }

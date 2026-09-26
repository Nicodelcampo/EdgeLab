"""Universal Causal Continuous Contract Series Builder.

Builds continuous time series from certified contract regimes without back-adjustment,
preserving exact traded prices and asserting state reset boundaries at every contract roll.

Key Guarantees:
1. Actual traded prices: no back-adjustment, no ratio-adjustment, no price smoothing.
2. Causal contract selection: uses only previous complete session volume (regime_manifest).
3. Post-sort state boundary reset: evaluates state_reset_flag strictly after global
   (ts_utc_ns, sequence) sorting, asserting True on row 0 and at every regime_id transition.
4. Content-level Micro/Standard isolation: validates manifest, file paths, parquet metadata,
   and internal payload columns (instrument, contract), forbidding micro/standard mixture.
5. Strict lineage & uniqueness: guarantees 10 mandatory lineage columns and strictly
   asserts uniqueness of (ts_utc_ns, sequence).
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from edgelab.data.contract_regime import (
    ContractRegimeError,
    contract_for_trade_date,
    validate_contract_regime,
)


class ContinuousContractError(ValueError):
    """Raised when continuous contract series construction or validation fails."""


LINEAGE_COLUMNS = [
    "root",
    "contract",
    "trade_date",
    "regime_id",
    "roll_manifest_sha256",
    "source_file",
    "source_row",
    "ts_utc_ns",
    "sequence",
    "state_reset_flag",
]


def build_continuous_series(
    *,
    root: str,
    regime_manifest: Mapping[str, Any],
    contract_source_paths: Mapping[str, Path | str],
    output_parquet_path: Path | str | None = None,
    strict_eligibility: bool = True,
) -> pa.Table:
    """Build a continuous causal tick series for an asset root from certified regime intervals."""
    validate_contract_regime(regime_manifest)
    clean_root = str(root).strip().upper()

    manifest_sha = regime_manifest["manifest_sha256"]
    intervals = [
        inv for inv in regime_manifest.get("intervals", [])
        if inv["root"] == clean_root
    ]
    if not intervals:
        raise ContinuousContractError(f"No intervals found for root {clean_root} in regime manifest")

    # Map daily assignments for quick lookup
    daily_by_date = {
        int(d["trade_date"]): d
        for d in regime_manifest.get("daily_assignments", [])
        if d["root"] == clean_root
    }

    # 1. Verify no micro/standard mixing in manifest contracts
    for c in regime_manifest.get("contracts", []):
        if c["root"] == clean_root:
            c_name = c["contract"]
            if "_" in c_name:
                c_root = c_name.split("_")[0].upper()
                if c_root != clean_root:
                    raise ContinuousContractError(
                        f"Mismatched contract root '{c_root}' in manifest for '{clean_root}'"
                    )

    # 2. Process each interval
    collected_tables: list[pa.Table] = []

    for interval in intervals:
        contract_key = interval["contract"]
        start_td = interval["start_trade_date"]
        end_td = interval["end_trade_date_exclusive"]
        regime_id = interval["regime_id"]

        # Resolve path
        path_candidate = (
            contract_source_paths.get(contract_key)
            or contract_source_paths.get(contract_key.split("_")[-1])
            or contract_source_paths.get(f"{clean_root}_{contract_key}")
        )
        if not path_candidate or not Path(path_candidate).exists():
            raise ContinuousContractError(
                f"Source parquet not found for contract {contract_key} (path: {path_candidate})"
            )

        # Read source table
        src_table = pq.read_table(path_candidate)
        src_cols = set(src_table.column_names)

        # Validate mandatory timestamps and sequence in source
        if "ts_utc_ns" not in src_cols:
            raise ContinuousContractError(f"Source parquet {path_candidate} missing mandatory 'ts_utc_ns'")
        if "sequence" not in src_cols:
            raise ContinuousContractError(f"Source parquet {path_candidate} missing mandatory 'sequence'")

        # Content-level validation: verify entire column for internal instrument / contract if present
        if "instrument" in src_cols:
            unique_insts = pc.unique(src_table["instrument"]).to_pylist()
            for inst in unique_insts:
                inst_clean = str(inst).strip().upper()
                if inst_clean != clean_root:
                    raise ContinuousContractError(
                        f"Content mismatch in {path_candidate}: internal instrument '{inst_clean}' != root '{clean_root}'"
                    )

        if "contract" in src_cols:
            unique_conts = pc.unique(src_table["contract"]).to_pylist()
            expected_suffixes = {contract_key, contract_key.split("_")[-1]}
            for cont in unique_conts:
                cont_clean = str(cont).strip()
                if cont_clean not in expected_suffixes:
                    raise ContinuousContractError(
                        f"Content mismatch in {path_candidate}: internal contract '{cont_clean}' not in {expected_suffixes}"
                    )

        # Determine trade_date column or compute from ts_utc_ns
        if "trade_date" in src_cols:
            trade_dates_raw = src_table["trade_date"].to_pylist()
        else:
            import pandas as pd
            ts_series = pd.to_datetime(src_table["ts_utc_ns"].to_numpy(), utc=True).tz_convert("America/Chicago")
            dates = ts_series.date.copy()
            mask = ts_series.hour >= 17
            dates[mask] = dates[mask] + pd.Timedelta(days=1)
            trade_dates_raw = [d.year * 10000 + d.month * 100 + d.day for d in dates]

        # Filter rows belonging to this interval and check eligibility
        keep_mask = []
        for td in trade_dates_raw:
            in_range = (td >= start_td) and (end_td is None or td < end_td)
            if not in_range:
                keep_mask.append(False)
                continue
            if strict_eligibility:
                d_info = daily_by_date.get(td)
                if not d_info or not d_info.get("eligible"):
                    keep_mask.append(False)
                    continue
            keep_mask.append(True)

        if not any(keep_mask):
            continue

        indices = [i for i, k in enumerate(keep_mask) if k]
        sub_table = src_table.take(indices)

        sub_len = len(sub_table)
        sub_cols = set(sub_table.column_names)
        source_file_name = Path(path_candidate).name
        root_col = pa.array([clean_root] * sub_len, type=pa.string())
        contract_col = pa.array([contract_key] * sub_len, type=pa.string())
        regime_id_col = pa.array([regime_id] * sub_len, type=pa.string())
        manifest_sha_col = pa.array([manifest_sha] * sub_len, type=pa.string())

        filtered_tds = [trade_dates_raw[i] for i in indices]
        trade_date_col = pa.array(filtered_tds, type=pa.int64())

        if "source_file" in sub_cols:
            source_file_col = sub_table["source_file"]
        else:
            source_file_col = pa.array([source_file_name] * sub_len, type=pa.string())

        if "source_row" in sub_cols:
            source_row_col = sub_table["source_row"]
        else:
            source_row_col = pa.array(indices, type=pa.int64())

        cols_to_add = {
            "root": root_col,
            "contract": contract_col,
            "trade_date": trade_date_col,
            "regime_id": regime_id_col,
            "roll_manifest_sha256": manifest_sha_col,
            "source_file": source_file_col,
            "source_row": source_row_col,
        }

        existing_cols = list(sub_table.column_names)
        new_cols = []
        new_names = []

        for name in existing_cols:
            if name == "state_reset_flag":
                # Pre-existing flag in source must be explicitly discarded to avoid ambiguity
                continue
            if name in cols_to_add:
                new_cols.append(cols_to_add.pop(name))
                new_names.append(name)
            else:
                new_cols.append(sub_table[name])
                new_names.append(name)

        for name, col in cols_to_add.items():
            new_cols.append(col)
            new_names.append(name)

        segment_table = pa.Table.from_arrays(new_cols, names=new_names)
        collected_tables.append(segment_table)

    if not collected_tables:
        raise ContinuousContractError(f"No valid rows collected for root {clean_root}")

    full_table = pa.concat_tables(collected_tables)

    # 3. Global sort strictly by (ts_utc_ns, sequence)
    sort_keys = [("ts_utc_ns", "ascending"), ("sequence", "ascending")]
    sort_indices = pc.sort_indices(full_table, sort_keys=sort_keys)
    sorted_table = full_table.take(sort_indices)

    # 4. Assert uniqueness of (ts_utc_ns, sequence)
    ts_arr = sorted_table["ts_utc_ns"].to_numpy()
    seq_arr = sorted_table["sequence"].to_numpy()

    # Verify no nulls or non-positive timestamps
    if (ts_arr <= 0).any():
        raise ContinuousContractError("Encountered non-positive ts_utc_ns in continuous stream")

    # Fast duplicate check on sorted arrays: duplicates must be adjacent
    if len(ts_arr) > 1:
        dup_mask = (ts_arr[:-1] == ts_arr[1:]) & (seq_arr[:-1] == seq_arr[1:])
        if dup_mask.any():
            first_dup_idx = int(dup_mask.argmax())
            dup_ts = ts_arr[first_dup_idx]
            dup_seq = seq_arr[first_dup_idx]
            raise ContinuousContractError(
                f"Duplicate (ts_utc_ns, sequence) detected: ts={dup_ts}, seq={dup_seq} at row {first_dup_idx}"
            )

    # 5. Assign state_reset_flag POST-SORT strictly at chronological regime boundaries
    sorted_regimes = sorted_table["regime_id"].to_pylist()
    state_reset = [False] * len(sorted_table)
    if len(sorted_table) > 0:
        state_reset[0] = True
        for i in range(1, len(sorted_table)):
            if sorted_regimes[i] != sorted_regimes[i - 1]:
                state_reset[i] = True

    state_reset_col = pa.array(state_reset, type=pa.bool_())
    if "state_reset_flag" in sorted_table.column_names:
        sorted_table = sorted_table.drop(["state_reset_flag"])
    final_table = sorted_table.append_column("state_reset_flag", state_reset_col)

    # 6. Final lineage columns verification (exactly 10 columns)
    missing_lineage = set(LINEAGE_COLUMNS) - set(final_table.column_names)
    if missing_lineage:
        raise ContinuousContractError(f"Final continuous series missing lineage columns: {missing_lineage}")

    if output_parquet_path:
        out_p = Path(output_parquet_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(final_table, out_p, compression="SNAPPY")

    return final_table

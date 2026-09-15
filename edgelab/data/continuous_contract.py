"""Universal Causal Continuous Contract Series Builder.

Builds continuous time series from certified contract regimes without back-adjustment,
preserving exact traded prices and asserting state reset boundaries at every contract roll.

Key Guarantees:
1. Actual traded prices: no back-adjustment, no ratio-adjustment, no price smoothing.
2. Causal contract selection: uses only previous complete session volume (regime_manifest).
3. State boundary reset: flags state_reset_flag=True at rolls to force downstream indicator reset.
4. Micro / Standard isolation: strictly forbids mixing root symbols (e.g. NQ vs MNQ).
5. Immutable lineage: every row carries root, contract, trade_date, regime_id,
   roll_manifest_sha256, source_file, source_row, ts_utc_ns, sequence.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
import pyarrow as pa
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

    # Verify no micro/standard mixing in manifest contracts
    for c in regime_manifest.get("contracts", []):
        if c["root"] == clean_root:
            c_name = c["contract"]
            # e.g. NQ_06-26 or 06-26. If it has a root prefix, it must match clean_root
            if "_" in c_name:
                c_root = c_name.split("_")[0].upper()
                if c_root != clean_root:
                    raise ContinuousContractError(
                        f"Mismatched contract root {c_root} in regime for {clean_root}"
                    )

    # Process each interval in chronological order
    collected_tables: list[pa.Table] = []
    current_regime_id: str | None = None

    for interval_idx, interval in enumerate(intervals):
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

        # Determine trade_date column or compute from ts_utc_ns
        if "trade_date" in src_cols:
            trade_dates_raw = src_table["trade_date"].to_pylist()
        else:
            # Derive trade_date using America/Chicago 17:00 CT boundary
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

        # Build lineage columns
        sub_len = len(sub_table)
        sub_cols = set(sub_table.column_names)
        source_file_name = Path(path_candidate).name
        root_col = pa.array([clean_root] * sub_len, type=pa.string())
        contract_col = pa.array([contract_key] * sub_len, type=pa.string())
        regime_id_col = pa.array([regime_id] * sub_len, type=pa.string())
        manifest_sha_col = pa.array([manifest_sha] * sub_len, type=pa.string())

        filtered_tds = [trade_dates_raw[i] for i in indices]
        trade_date_col = pa.array(filtered_tds, type=pa.int64())

        # Source file and source row
        if "source_file" in sub_cols:
            source_file_col = sub_table["source_file"]
        else:
            source_file_col = pa.array([source_file_name] * sub_len, type=pa.string())

        if "source_row" in sub_cols:
            source_row_col = sub_table["source_row"]
        else:
            source_row_col = pa.array(indices, type=pa.int64())

        # State reset flag: True on first row of whole series, and True on first row of new regime_id
        state_reset = [False] * sub_len
        if current_regime_id != regime_id:
            state_reset[0] = True
            current_regime_id = regime_id
        state_reset_col = pa.array(state_reset, type=pa.bool_())

        # Assemble new / updated table
        cols_to_add = {
            "root": root_col,
            "contract": contract_col,
            "trade_date": trade_date_col,
            "regime_id": regime_id_col,
            "roll_manifest_sha256": manifest_sha_col,
            "source_file": source_file_col,
            "source_row": source_row_col,
            "state_reset_flag": state_reset_col,
        }

        # Preserve original columns, replacing or appending lineage
        existing_cols = list(sub_table.column_names)
        new_cols = []
        new_names = []

        for name in existing_cols:
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

    # Sort strictly by ts_utc_ns, sequence if present
    if "sequence" in full_table.column_names:
        sort_keys = [("ts_utc_ns", "ascending"), ("sequence", "ascending")]
    else:
        sort_keys = [("ts_utc_ns", "ascending")]
    
    # pyarrow sort indices
    import pyarrow.compute as pc
    sort_indices = pc.sort_indices(full_table, sort_keys=sort_keys)
    sorted_table = full_table.take(sort_indices)

    if output_parquet_path:
        out_p = Path(output_parquet_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(sorted_table, out_p, compression="SNAPPY")

    return sorted_table

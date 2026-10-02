"""Build the causal pre-holdout MGC continuous tick stream.

This follows EdgeLab's current contract policy:

* CME trade dates in America/Chicago (17:00 -> 16:00 CT).
* Contract for D is selected only from volume of complete session D-1.
* Strict volume crossover and monotonic forward rolls.
* No back-adjustment: all execution and indicator prices are actual traded prices.
* Explicit state reset at each contract-regime transition.
* Holdout is sealed by trade date, not by a naive UTC timestamp.

Input is the private Kaggle raw archive downloaded under /data/raw/mgc.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from edgelab.data.contract_regime import (
    build_contract_regime,
    canonical_sha256,
    validate_contract_regime,
)
from edgelab.kaggle.sessions_cme import (
    is_maintenance_break,
    trade_date_ymd,
    ymd_weekday,
)


RAW_DIR = Path("/data/raw/mgc")
OUT_DIR = Path("/data/analysis/mgc")
OUT_TICKS = OUT_DIR / "mgc_ticks_canonical_preholdout.parquet"
OUT_REGIME = OUT_DIR / "mgc_contract_regime_preholdout.json"
OUT_MANIFEST = OUT_DIR / "mgc_canonical_build_manifest.json"

ROOT = "MGC"
TICK_SIZE = 0.1
HOLDOUT_FIRST_TRADE_DATE = 20260401
LAST_DISCOVERY_TRADE_DATE = 20260331
MIN_USABLE_ROWS = 100_000


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def expiry_ordinal(path: Path) -> int:
    month, yy = path.stem.split("_")[1].split("-")
    return (2000 + int(yy)) * 100 + int(month)


def date_range(start: int, end: int) -> list[int]:
    a = date(start // 10000, (start // 100) % 100, start % 100)
    b = date(end // 10000, (end // 100) % 100, end % 100)
    out: list[int] = []
    while a <= b:
        if a.weekday() < 5:
            out.append(a.year * 10000 + a.month * 100 + a.day)
        a += timedelta(days=1)
    return out


def session_inventory(path: Path) -> dict:
    pf = pq.ParquetFile(path)
    rows = pf.metadata.num_rows
    sessions: dict[int, dict[str, int]] = defaultdict(
        lambda: {"volume": 0, "ticks": 0, "first_utc_ns": 2**63 - 1, "last_utc_ns": 0}
    )
    key_duplicates = 0
    prev_ts: int | None = None
    prev_seq: int | None = None

    for batch in pf.iter_batches(
        columns=["ts_utc_ns", "volume", "sequence"], batch_size=1_000_000
    ):
        ts = batch["ts_utc_ns"].to_numpy(zero_copy_only=False).astype(np.int64)
        vol = batch["volume"].to_numpy(zero_copy_only=False).astype(np.int64)
        seq = batch["sequence"].to_numpy(zero_copy_only=False).astype(np.int64)
        td = trade_date_ymd(ts)
        maint = is_maintenance_break(ts)
        weekday = np.fromiter((ymd_weekday(int(x)) for x in td), np.int8, len(td))
        valid = (weekday < 5) & (~maint)

        if len(ts) > 1:
            key_duplicates += int(((ts[1:] == ts[:-1]) & (seq[1:] == seq[:-1])).sum())
        if prev_ts is not None:
            key_duplicates += int(ts[0] == prev_ts and seq[0] == prev_seq)
        prev_ts, prev_seq = int(ts[-1]), int(seq[-1])

        tdv = td[valid]
        tsv = ts[valid]
        volv = vol[valid]
        for d in np.unique(tdv):
            m = tdv == d
            rec = sessions[int(d)]
            rec["volume"] += int(volv[m].sum())
            rec["ticks"] += int(m.sum())
            rec["first_utc_ns"] = min(rec["first_utc_ns"], int(tsv[m].min()))
            rec["last_utc_ns"] = max(rec["last_utc_ns"], int(tsv[m].max()))

    return {
        "contract": path.stem,
        "path": path,
        "rows": rows,
        "expiry_ordinal": expiry_ordinal(path),
        "sha256": file_sha256(path),
        "sessions": dict(sessions),
        "key_duplicates": key_duplicates,
    }


def build_regime(inventories: list[dict]) -> dict:
    first = min(min(x["sessions"]) for x in inventories)
    calendar = date_range(first, LAST_DISCOVERY_TRADE_DATE)
    contracts = []
    daily_volumes = []
    for inv in inventories:
        dates = sorted(inv["sessions"])
        first_d, last_d = dates[0], min(dates[-1], LAST_DISCOVERY_TRADE_DATE)
        contracts.append(
            {
                "root": ROOT,
                "contract": inv["contract"],
                "expiry_ordinal": inv["expiry_ordinal"],
                "first_trade_date": first_d,
                "last_trade_date": last_d,
            }
        )
        for d in calendar:
            if first_d <= d <= last_d:
                daily_volumes.append(
                    {
                        "root": ROOT,
                        "contract": inv["contract"],
                        "trade_date": d,
                        "volume": float(inv["sessions"].get(d, {}).get("volume", 0)),
                        "complete_session": True,
                    }
                )

    source_identity = {
        "dataset": "nicolasbuttaro/edgelab-mgc-nt8-raw-parquet-20261002",
        "inventory_sha256": canonical_sha256(
            [{"contract": x["contract"], "sha256": x["sha256"]} for x in inventories]
        ),
        "holdout_first_trade_date": HOLDOUT_FIRST_TRADE_DATE,
        "raw_schema": "MGC_RAW_PARQUET_ARCHIVE_V1",
    }
    manifest = build_contract_regime(
        contracts=contracts,
        daily_volumes=daily_volumes,
        calendar_trade_dates=calendar,
        source_identity=source_identity,
    )
    validate_contract_regime(manifest)
    return manifest


def write_canonical(inventories: list[dict], regime: dict) -> dict:
    assignment = {
        int(x["trade_date"]): x
        for x in regime["daily_assignments"]
        if x["eligible"] and int(x["trade_date"]) < HOLDOUT_FIRST_TRADE_DATE
    }
    inv_by_contract = {x["contract"]: x for x in inventories}
    writer: pq.ParquetWriter | None = None
    output_rows = 0
    prior_ts: int | None = None
    prior_seq: int | None = None
    prior_regime: str | None = None
    output_key_duplicates = 0
    output_backwards = 0
    counts_by_contract: dict[str, int] = defaultdict(int)

    intervals = [x for x in regime["intervals"] if x["root"] == ROOT]
    for interval in intervals:
        contract = interval["contract"]
        inv = inv_by_contract[contract]
        pf = pq.ParquetFile(inv["path"])
        regime_id = interval["regime_id"]
        start_td = int(interval["start_trade_date"])
        end_td = interval["end_trade_date_exclusive"]
        eligible_dates = np.array(
            sorted(d for d, a in assignment.items() if a["active_contract"] == contract),
            dtype=np.int32,
        )

        for batch in pf.iter_batches(batch_size=750_000):
            table = pa.Table.from_batches([batch])
            ts = table["ts_utc_ns"].to_numpy(zero_copy_only=False).astype(np.int64)
            seq = table["sequence"].to_numpy(zero_copy_only=False).astype(np.int64)
            td = trade_date_ymd(ts)
            keep = td >= start_td
            if end_td is not None:
                keep &= td < int(end_td)
            keep &= td < HOLDOUT_FIRST_TRADE_DATE
            keep &= np.isin(td, eligible_dates)
            if not keep.any():
                continue
            idx = np.flatnonzero(keep)
            sub = table.take(pa.array(idx))
            sub_ts = ts[idx]
            sub_seq = seq[idx]
            sub_td = td[idx]

            # Fail closed if the daily assignment and interval disagree.
            for d in np.unique(sub_td):
                a = assignment.get(int(d))
                if a is None or a["active_contract"] != contract:
                    raise RuntimeError(f"regime mismatch for {contract} trade_date={int(d)}")

            if prior_ts is not None:
                output_backwards += int(sub_ts[0] < prior_ts)
                output_key_duplicates += int(sub_ts[0] == prior_ts and sub_seq[0] == prior_seq)
            if len(sub_ts) > 1:
                output_backwards += int((np.diff(sub_ts) < 0).sum())
                output_key_duplicates += int(
                    ((sub_ts[1:] == sub_ts[:-1]) & (sub_seq[1:] == sub_seq[:-1])).sum()
                )

            last = sub["last"].to_numpy(zero_copy_only=False)
            bid = sub["bid"].to_numpy(zero_copy_only=False)
            ask = sub["ask"].to_numpy(zero_copy_only=False)
            price_ticks = np.rint(last / TICK_SIZE).astype(np.int32)
            bid_ticks = np.rint(bid / TICK_SIZE).astype(np.int32)
            ask_ticks = np.rint(ask / TICK_SIZE).astype(np.int32)

            reset = np.zeros(len(sub), dtype=bool)
            if prior_regime != regime_id:
                reset[0] = True

            additions = {
                "root": pa.array([ROOT] * len(sub)),
                "contract": pa.array([contract] * len(sub)),
                "trade_date": pa.array(sub_td.astype(np.int32)),
                "regime_id": pa.array([regime_id] * len(sub)),
                "roll_manifest_sha256": pa.array([regime["manifest_sha256"]] * len(sub)),
                "source_file": pa.array([inv["path"].name] * len(sub)),
                "state_reset_flag": pa.array(reset),
                "price_ticks": pa.array(price_ticks),
                "bid_ticks": pa.array(bid_ticks),
                "ask_ticks": pa.array(ask_ticks),
            }
            for name, col in additions.items():
                sub = sub.append_column(name, col)

            if writer is None:
                metadata = dict(sub.schema.metadata or {})
                metadata.update(
                    {
                        b"schema_version": b"canonical_tick_mgc_v1",
                        b"tick_size": str(TICK_SIZE).encode(),
                        b"price_adjustment": b"NONE_ACTUAL_TRADED_PRICES",
                        b"holdout_first_trade_date": str(HOLDOUT_FIRST_TRADE_DATE).encode(),
                        b"roll_schedule_sha256": regime["manifest_sha256"].encode(),
                    }
                )
                sub = sub.replace_schema_metadata(metadata)
                writer = pq.ParquetWriter(
                    OUT_TICKS, sub.schema, compression="zstd", compression_level=9
                )
            writer.write_table(sub, row_group_size=250_000)
            output_rows += len(sub)
            counts_by_contract[contract] += len(sub)
            prior_ts, prior_seq = int(sub_ts[-1]), int(sub_seq[-1])
            prior_regime = regime_id

    if writer is not None:
        writer.close()
    if output_backwards or output_key_duplicates:
        raise RuntimeError(
            f"canonical key failure: backwards={output_backwards}, duplicates={output_key_duplicates}"
        )
    return {
        "rows": output_rows,
        "counts_by_contract": dict(counts_by_contract),
        "timestamp_backwards": output_backwards,
        "duplicate_ts_sequence": output_key_duplicates,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    inventories = [
        session_inventory(p)
        for p in sorted(RAW_DIR.glob("MGC_*.parquet"), key=expiry_ordinal)
        if pq.ParquetFile(p).metadata.num_rows >= MIN_USABLE_ROWS
        and expiry_ordinal(p) <= 202606
    ]
    if any(x["key_duplicates"] for x in inventories):
        raise RuntimeError(
            f"source duplicate keys: {[(x['contract'], x['key_duplicates']) for x in inventories]}"
        )

    regime = build_regime(inventories)
    OUT_REGIME.write_text(json.dumps(regime, indent=2), encoding="utf-8")
    build = write_canonical(inventories, regime)
    manifest = {
        "schema_version": "mgc_canonical_build_manifest_v1",
        "root": ROOT,
        "tick_size": TICK_SIZE,
        "holdout_first_trade_date": HOLDOUT_FIRST_TRADE_DATE,
        "price_adjustment": "NONE_ACTUAL_TRADED_PRICES",
        "state_boundary": "RESET_AT_CONTRACT_ROLL",
        "source_files": [
            {
                "contract": x["contract"],
                "path": str(x["path"]),
                "rows": x["rows"],
                "sha256": x["sha256"],
                "first_trade_date": min(x["sessions"]),
                "last_trade_date": max(x["sessions"]),
            }
            for x in inventories
        ],
        "roll_schedule_sha256": regime["manifest_sha256"],
        "intervals": regime["intervals"],
        "build": build,
        "output": {
            "path": str(OUT_TICKS),
            "sha256": file_sha256(OUT_TICKS),
            "bytes": OUT_TICKS.stat().st_size,
        },
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
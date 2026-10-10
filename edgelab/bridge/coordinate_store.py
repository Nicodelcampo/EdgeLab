"""Proyección point-in-time de coordenadas de zona.

No contiene estado final, touches ni ended_ms. Es una capa de consulta rápida;
``events.parquet`` del Store v2 continúa siendo la fuente de verdad.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone

from . import identity, sessions, store

SCHEMA_VERSION = "indicator_coordinate_store_v1"
HOLDOUT_START_NS = int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp() * 1e9)
ALLOWED_PARITY_STATES = {"parity_exact", "parity_covered"}
CREATE_EVENT_TYPES = {"ZONE_CREATED", "ZONE_CREATE", "CREATED"}

COORDINATE_COLUMNS = (
    "coordinate_key", "run_id", "dataset_id", "kernel_id", "config_id",
    "indicator", "instrument", "contract", "bar_key", "zone_id", "kind",
    "side", "direction", "session_id", "created_ms", "created_ns",
    "created_event_seq", "available_ns", "available_event_seq",
    "created_source_row", "bottom", "top", "lower_tick", "upper_tick",
)
FORBIDDEN_FUTURE_FIELDS = {
    "ended_ms", "ended_ns", "final_state", "state", "touches", "end_reason",
    "mfe", "mae", "return", "pnl",
}


def _side_and_direction(zone: dict) -> tuple[str, int | None]:
    raw_dir = zone.get("dir")
    if raw_dir in (1, -1):
        return ("up" if raw_dir == 1 else "down"), int(raw_dir)
    if isinstance(raw_dir, str):
        low = raw_dir.lower()
        if low == "long":
            return "long", 1
        if low == "short":
            return "short", -1
    text = str(zone.get("kind") or zone.get("side") or "none").lower()
    if any(token in text for token in ("bull", "buyers", "support")):
        return "bull", None
    if any(token in text for token in ("bear", "sellers", "resist")):
        return "bear", None
    return "none", None


def _event_ns(event: dict) -> int | None:
    if event.get("unix_ms") is not None:
        return int(event["unix_ms"]) * 1_000_000
    try:
        payload = json.loads(event.get("payload") or "{}")
        text = payload.get("ts")
        if not text:
            return None
        dt = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1e9)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _creation_events(kernel_result: dict) -> dict[str, dict]:
    rows = store.build_event_rows(
        kernel_result.get("csv_lines", []), kernel_result.get("header")
    )
    out = {}
    for row in rows:
        zid = row.get("zone_id")
        if zid is None or row.get("event_type") not in CREATE_EVENT_TYPES:
            continue
        out.setdefault(str(zid), row)
    return out


def build_coordinate_rows(*, kernel_result: dict, run_id: str, dataset_id: str,
                          kernel_id: str, config_id: str, indicator: str,
                          instrument: str, contract: str, bar_key: str,
                          tick_size: float) -> list[dict]:
    creates = _creation_events(kernel_result)
    rows = []
    for zone in kernel_result.get("zones", []):
        if zone.get("created_ms") is None:
            raise ValueError(f"{indicator}: zona sin created_ms")
        if zone.get("bottom") is None or zone.get("top") is None:
            raise ValueError(f"{indicator}: zona sin geometría bottom/top")
        zone_id = str(zone["id"])
        event = creates.get(zone_id)
        if event is None:
            raise ValueError(
                f"{indicator}: zona {zone_id} sin evento causal ZONE_CREATED"
            )
        created_ms = int(zone["created_ms"])
        created_ns = created_ms * 1_000_000
        available_ns = _event_ns(event)
        if available_ns is None:
            available_ns = created_ns
        if available_ns < created_ns:
            raise ValueError(f"{indicator}: disponibilidad anterior a creación")
        bottom = float(zone["bottom"])
        top = float(zone["top"])
        lower_tick = int(round(bottom / tick_size))
        upper_tick = int(round(top / tick_size))
        side, direction = _side_and_direction(zone)
        create_seq = int(event["seq"])
        coordinate_key = identity.zone_key(
            run_id, zone_id, create_seq, created_ms, lower_tick, upper_tick, side
        )
        rows.append({
            "coordinate_key": coordinate_key,
            "run_id": run_id,
            "dataset_id": dataset_id,
            "kernel_id": kernel_id,
            "config_id": config_id,
            "indicator": indicator,
            "instrument": instrument,
            "contract": contract,
            "bar_key": bar_key,
            "zone_id": zone_id,
            "kind": str(zone.get("kind") or ""),
            "side": side,
            "direction": direction,
            "session_id": sessions.session_key(available_ns),
            "created_ms": created_ms,
            "created_ns": created_ns,
            "created_event_seq": create_seq,
            "available_ns": available_ns,
            "available_event_seq": create_seq,
            "created_source_row": (
                int(zone["sig_idx"]) if zone.get("sig_idx") is not None else
                int(zone["created_bar"]) if zone.get("created_bar") is not None else
                None
            ),
            "bottom": bottom,
            "top": top,
            "lower_tick": lower_tick,
            "upper_tick": upper_tick,
        })
    validate_coordinate_rows(rows)
    return rows


def validate_coordinate_rows(rows: list[dict]) -> None:
    keys = set()
    for row in rows:
        leaked = FORBIDDEN_FUTURE_FIELDS.intersection(row)
        if leaked:
            raise ValueError(f"campos futuros prohibidos: {sorted(leaked)}")
        if row["coordinate_key"] in keys:
            raise ValueError("coordinate_key duplicado")
        keys.add(row["coordinate_key"])
        if int(row["lower_tick"]) > int(row["upper_tick"]):
            raise ValueError("geometría inválida: lower_tick > upper_tick")
        if int(row["available_ns"]) >= HOLDOUT_START_NS:
            raise ValueError("HOLDOUT_DATA_DETECTED: available_ns >= 2026-07-01")
        if int(row["available_ns"]) < int(row["created_ns"]):
            raise ValueError("available_ns anterior a created_ns")


def coordinate_partition_dir(root, *, instrument, contract, indicator, kernel_id,
                             bar_key, config_id, run_id):
    return os.path.join(
        str(root), "coordinates", f"instrument={store._san(instrument)}",
        f"contract={store._san(contract)}", f"indicator={store._san(indicator)}",
        f"kernel_id={store._san(kernel_id)}", f"bar_key={store._san(bar_key)}",
        f"config_id={store._san(config_id)}", f"run_id={store._san(run_id)}",
    )


def _digest(rows: list[dict]) -> str:
    h = hashlib.sha256()
    for row in sorted(rows, key=lambda r: r["coordinate_key"]):
        h.update(identity.canonical_json(row).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _write_parquet(rows: list[dict], path: str) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    schema = pa.schema([
        ("coordinate_key", pa.string()), ("run_id", pa.string()),
        ("dataset_id", pa.string()), ("kernel_id", pa.string()),
        ("config_id", pa.string()), ("indicator", pa.string()),
        ("instrument", pa.string()), ("contract", pa.string()),
        ("bar_key", pa.string()), ("zone_id", pa.string()),
        ("kind", pa.string()), ("side", pa.string()),
        ("direction", pa.int8()), ("session_id", pa.string()),
        ("created_ms", pa.int64()), ("created_ns", pa.int64()),
        ("created_event_seq", pa.int64()), ("available_ns", pa.int64()),
        ("available_event_seq", pa.int64()), ("created_source_row", pa.int64()),
        ("bottom", pa.float64()), ("top", pa.float64()),
        ("lower_tick", pa.int64()), ("upper_tick", pa.int64()),
    ])
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, path, compression="zstd")


def publish_coordinates(root, *, rows: list[dict], run_manifest: dict,
                        parity_state: str) -> dict:
    if parity_state not in ALLOWED_PARITY_STATES:
        raise ValueError(f"paridad no autorizada: {parity_state}")
    validate_coordinate_rows(rows)
    digest = _digest(rows)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_manifest["run_id"],
        "dataset_id": run_manifest["dataset_id"],
        "kernel_id": run_manifest["kernel_id"],
        "config_id": run_manifest["config_id"],
        "indicator": run_manifest["indicator"],
        "instrument": run_manifest["instrument"],
        "contract": run_manifest["contract"],
        "bar_key": run_manifest["bar_key"],
        "parity_state": parity_state,
        "coordinate_count": len(rows),
        "coordinate_sha256": digest,
        "firewall": {
            "CAMPAIGN_OUTCOMES_OPENED": False,
            "PNL_ACCESSED": False,
            "HOLDOUT_TOUCHED": False,
            "WINNER_SELECTED": False,
            "EDGE_DECLARED": False,
        },
    }
    pdir = coordinate_partition_dir(
        root, instrument=manifest["instrument"], contract=manifest["contract"],
        indicator=manifest["indicator"], kernel_id=manifest["kernel_id"],
        bar_key=manifest["bar_key"], config_id=manifest["config_id"],
        run_id=manifest["run_id"],
    )
    manifest_path = os.path.join(pdir, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as fh:
            previous = json.load(fh)
        if previous.get("coordinate_sha256") == digest:
            return previous
        raise store.DeterminismError(
            f"{manifest['run_id']}: coordenadas divergentes; no se sobrescribe"
        )
    tmp = pdir + ".tmp"
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp, exist_ok=True)
    _write_parquet(rows, os.path.join(tmp, "coordinates.parquet"))
    with open(os.path.join(tmp, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    os.makedirs(os.path.dirname(pdir), exist_ok=True)
    os.replace(tmp, pdir)
    return manifest

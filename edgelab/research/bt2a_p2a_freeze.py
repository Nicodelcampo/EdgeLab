"""Fail-closed identity and decision rules for the frozen BT2A P2-A diagnostic."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from edgelab.research.bt2a_event_store import canonical_sha256, validate_event_checkpoint


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def validate_canonical_event_store(
    event_store_dir: str | Path,
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify manifest, Parquet and every checkpoint against the frozen identity."""
    root = Path(event_store_dir)
    expected = spec.get("canonical_event_store")
    checks: dict[str, bool] = {}
    errors: list[str] = []
    if not isinstance(expected, Mapping):
        return {"ready": False, "checks": {}, "errors": ["missing canonical_event_store in spec"]}

    def mark(name: str, ok: bool, detail: str | None = None) -> None:
        checks[name] = bool(ok)
        if not ok:
            errors.append(detail or name)

    def same(name: str, actual: Any, wanted: Any) -> None:
        mark(name, actual == wanted, f"{name}: expected={wanted!r} actual={actual!r}")

    manifest_path = root / "run_manifest.json"
    if not manifest_path.is_file():
        return {"ready": False, "checks": {"manifest_exists": False}, "errors": ["missing run_manifest.json"]}
    try:
        manifest = json.loads(manifest_path.read_text())
    except Exception as exc:
        return {"ready": False, "checks": {"manifest_json": False}, "errors": [f"invalid run_manifest.json: {type(exc).__name__}"]}
    if not isinstance(manifest, dict):
        return {"ready": False, "checks": {"manifest_object": False}, "errors": ["run manifest must be an object"]}

    same("manifest_status", manifest.get("status"), spec.get("input", {}).get("required_manifest_status"))
    for key in (
        "n_sessions",
        "n_events",
        "events_payload_sha256",
        "runtime_sha256",
        "input_registry_payload_sha256",
        "sample_registry_payload_sha256",
    ):
        same(f"manifest_{key}", manifest.get(key), expected.get(key))
    same("manifest_counts_by_contract", manifest.get("counts"), expected.get("counts_by_contract"))
    manifest_totals: Counter[str] = Counter()
    if isinstance(manifest.get("counts"), dict):
        try:
            for arms in manifest["counts"].values():
                if isinstance(arms, dict):
                    manifest_totals.update({str(arm): int(count) for arm, count in arms.items()})
        except Exception:
            mark("manifest_counts_parseable", False, "manifest counts are not integer-valued")
    same("manifest_counts_total", dict(manifest_totals), expected.get("counts_total"))
    builder = manifest.get("builder_git") if isinstance(manifest.get("builder_git"), dict) else {}
    same("builder_git_commit", builder.get("commit"), expected.get("builder_git_commit"))
    same("builder_git_branch", builder.get("branch"), expected.get("builder_git_branch"))
    same("builder_git_dirty", builder.get("dirty"), expected.get("builder_git_dirty"))
    same("manifest_canonical_gate1_commit", manifest.get("canonical_gate1_commit"), expected.get("canonical_gate1_commit"))

    parquet_meta = manifest.get("parquet") if isinstance(manifest.get("parquet"), dict) else {}
    same("manifest_parquet_sha256", parquet_meta.get("sha256"), expected.get("parquet_sha256"))
    parquet_path = root / str(parquet_meta.get("path") or "bt2a_gate1_canonical_events_all5.parquet")
    mark("parquet_exists", parquet_path.is_file(), f"missing parquet: {parquet_path.name}")
    if parquet_path.is_file():
        same("actual_parquet_sha256", file_sha256(parquet_path), expected.get("parquet_sha256"))

    checkpoint_dir = root / "checkpoints"
    checkpoint_paths = sorted(checkpoint_dir.glob("session_*.json")) if checkpoint_dir.is_dir() else []
    wanted_n = int(expected.get("n_sessions", -1))
    same("checkpoint_count", len(checkpoint_paths), wanted_n)
    wanted_names = [f"session_{i:03d}.json" for i in range(max(0, wanted_n))]
    same("checkpoint_names", [p.name for p in checkpoint_paths], wanted_names)

    aggregate_events: list[dict[str, Any]] = []
    observed_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    checkpoint_errors: list[str] = []
    if [p.name for p in checkpoint_paths] == wanted_names:
        for index, path in enumerate(checkpoint_paths):
            try:
                checkpoint = json.loads(path.read_text())
                if not isinstance(checkpoint, dict):
                    raise RuntimeError("checkpoint is not an object")
                if checkpoint.get("schema") != "bt2a_gate1_canonical_event_store_session_v1":
                    raise RuntimeError("checkpoint schema mismatch")
                if int(checkpoint.get("session_index", -1)) != index:
                    raise RuntimeError("checkpoint session_index mismatch")
                if checkpoint.get("runtime_sha256") != expected.get("runtime_sha256"):
                    raise RuntimeError("checkpoint runtime mismatch")
                if checkpoint.get("canonical_gate1_commit") != expected.get("canonical_gate1_commit"):
                    raise RuntimeError("checkpoint Gate1 commit mismatch")
                events = validate_event_checkpoint(
                    checkpoint,
                    contract=str(checkpoint.get("contract")),
                    session=str(checkpoint.get("cme_session")),
                    sample_registry_sha256=str(expected.get("sample_registry_payload_sha256")),
                    input_registry_sha256=str(expected.get("input_registry_payload_sha256")),
                )
                counts = dict(sorted(Counter(str(e["arm"]) for e in events).items()))
                if checkpoint.get("counts") != counts:
                    raise RuntimeError("checkpoint count mismatch")
                for event in events:
                    observed_counts[str(event["contract"])][str(event["arm"])] += 1
                aggregate_events.extend(events)
            except Exception as exc:
                checkpoint_errors.append(f"{path.name}: {type(exc).__name__}: {exc}")
    else:
        checkpoint_errors.append("checkpoint name set is not exact")
    mark("checkpoint_payloads_valid", not checkpoint_errors, "; ".join(checkpoint_errors[:20]))

    if not checkpoint_errors:
        same("actual_checkpoint_event_count", len(aggregate_events), expected.get("n_events"))
        same("actual_events_payload_sha256", canonical_sha256(aggregate_events), expected.get("events_payload_sha256"))
        actual_counts = {
            contract: dict(sorted(arms.items()))
            for contract, arms in sorted(observed_counts.items())
        }
        same("actual_checkpoint_counts_by_contract", actual_counts, expected.get("counts_by_contract"))
        ids = [str(event.get("event_id")) for event in aggregate_events]
        identities = [str(event.get("identity_sha256")) for event in aggregate_events]
        mark("actual_event_ids_unique", len(ids) == len(set(ids)), "duplicate event_id across checkpoints")
        mark("actual_identity_sha256_unique", len(identities) == len(set(identities)), "duplicate identity_sha256 across checkpoints")

    return {
        "ready": not errors and all(checks.values()),
        "checks": checks,
        "errors": errors,
        "manifest_path": str(manifest_path),
        "parquet_path": str(parquet_path),
    }


def validate_p2a_session_checkpoint(
    value: Mapping[str, Any],
    *,
    expected_index: int,
    expected_contract: str,
    expected_session: str,
    expected_spec_payload_sha256: str,
    expected_source_event_checkpoint_sha256: str,
    expected_control_replications: int,
    barriers: Sequence[int],
    tick_horizons: Sequence[int],
    clock_horizons: Sequence[int],
) -> dict[str, Any]:
    """Validate one P2-A output checkpoint before it can enter finalization."""
    errors: list[str] = []
    if not isinstance(value, Mapping):
        return {"ready": False, "errors": ["P2-A checkpoint is not an object"]}

    def expect(ok: bool, message: str) -> None:
        if not ok:
            errors.append(message)

    expect(value.get("schema") == "bt2a_gate2_p2a_session_v1", "schema mismatch")
    expect(value.get("status") == "COMPLETE_POST_OUTCOME_DIAGNOSTIC_SESSION", "status mismatch")
    expect(value.get("session_index") == int(expected_index), "session_index mismatch")
    expect(value.get("contract") == expected_contract, "contract mismatch")
    expect(value.get("cme_session") == expected_session, "session mismatch")
    expect(value.get("spec_payload_sha256") == expected_spec_payload_sha256, "spec payload mismatch")
    expect(value.get("source_event_checkpoint_sha256") == expected_source_event_checkpoint_sha256, "source Event Store checkpoint mismatch")
    expect(value.get("control_replications") == int(expected_control_replications), "control replication mismatch")
    expect(value.get("CAMPAIGN_OUTCOMES_OPENED") is True, "outcome-opened flag mismatch")
    expect(value.get("EDGE_DECLARED") is False, "edge flag mismatch")
    expect(value.get("confirmatory_eligible") is False, "confirmatory flag mismatch")
    payload = value.get("payload_sha256")
    body = {k: v for k, v in value.items() if k != "payload_sha256"}
    expect(isinstance(payload, str) and payload == canonical_sha256(body), "P2-A checkpoint payload hash mismatch")

    expected_grid = {
        (int(b), "ticks", int(h)) for b in barriers for h in tick_horizons
    } | {
        (int(b), "seconds", int(h)) for b in barriers for h in clock_horizons
    }
    cells = value.get("cells")
    if not isinstance(cells, list):
        errors.append("cells must be a list")
    else:
        seen: set[tuple[int, str, int]] = set()
        for cell in cells:
            try:
                key = (int(cell["barrier_ticks"]), str(cell["horizon_type"]), int(cell["horizon_value"]))
                if key in seen:
                    errors.append(f"duplicate cell {key}")
                seen.add(key)
                contrasts = cell.get("contrasts")
                if not isinstance(contrasts, Mapping):
                    errors.append(f"missing contrasts in {key}")
                else:
                    for name in ("K_ABS_minus_N_RAND", "K_ABS_minus_K_ABS_SHUFFLE", "K_ABS_minus_K_BT2"):
                        number = float(contrasts[name])
                        if not math.isfinite(number):
                            errors.append(f"non-finite {name} in {key}")
            except Exception as exc:
                errors.append(f"malformed cell: {type(exc).__name__}: {exc}")
        if seen != expected_grid:
            errors.append(f"cell grid mismatch; missing={sorted(expected_grid-seen)} extra={sorted(seen-expected_grid)}")
    return {"ready": not errors, "errors": errors}


def _inconclusive(reason: str, errors: Sequence[str], n_cells: int = 0) -> dict[str, Any]:
    return {
        "label": "P2_DIAGNOSTIC_INCONCLUSIVE",
        "reason": reason,
        "validation_errors": list(errors),
        "familywise_alpha": None,
        "n_primary_cells": int(n_cells),
        "positive_cells": [],
        "negative_cells": [],
        "secondary_evidence_used": False,
        "winner_selected": False,
        "edge_declared": False,
        "promotion_eligible": False,
    }


def classify_mechanism(
    primary_family: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the frozen familywise P2-A label without choosing a winning cell."""
    p2a = spec.get("p2a", {})
    rule = spec.get("decision_rule", {})
    try:
        barriers = tuple(int(x) for x in p2a.get("barriers_ticks", ()))
        horizons = tuple(int(x) for x in p2a.get("primary_horizons_ticks", ()))
        alpha = float(rule.get("familywise_alpha", 0.05))
    except Exception as exc:
        return _inconclusive("INVALID_FROZEN_DECISION_RULE", [f"{type(exc).__name__}: {exc}"])
    if not math.isfinite(alpha) or not 0 < alpha < 1:
        return _inconclusive("INVALID_FROZEN_DECISION_RULE", ["familywise alpha outside (0,1)"])
    expected_grid = {(b, h) for b in barriers for h in horizons}
    cells: dict[tuple[int, int], Mapping[str, Any]] = {}
    validation_errors: list[str] = []
    for row in primary_family:
        try:
            key = (int(row["barrier_ticks"]), int(row["horizon_ticks"]))
            if key in cells:
                validation_errors.append(f"duplicate primary cell: {key}")
            cells[key] = row
        except Exception as exc:
            validation_errors.append(f"malformed primary cell: {type(exc).__name__}: {exc}")
    if set(cells) != expected_grid:
        validation_errors.append(f"primary family mismatch; missing={sorted(expected_grid-set(cells))} extra={sorted(set(cells)-expected_grid)}")
    if validation_errors:
        return _inconclusive("INVALID_OR_INCOMPLETE_PRIMARY_FAMILY", validation_errors, len(cells))

    contrast_name = str(rule.get("primary_contrast", "K_ABS_MINUS_N_RAND"))
    result_key = "K_ABS_minus_N_RAND" if contrast_name == "K_ABS_MINUS_N_RAND" else contrast_name
    positive: list[dict[str, int]] = []
    negative: list[dict[str, int]] = []
    for key in sorted(cells):
        contrast = cells[key].get("contrasts", {}).get(result_key)
        if not isinstance(contrast, Mapping):
            return _inconclusive("INVALID_PRIMARY_CELL", [f"missing frozen contrast in cell {key}"], len(cells))
        try:
            point = float(contrast["point"])
            lower = float(contrast["lower"])
            upper = float(contrast["upper"])
            p_holm = float(contrast["p_holm_16"])
        except Exception as exc:
            return _inconclusive("INVALID_PRIMARY_CELL", [f"cell {key}: {type(exc).__name__}: {exc}"], len(cells))
        if not all(math.isfinite(x) for x in (point, lower, upper, p_holm)) or not 0 <= p_holm <= 1 or lower > upper:
            return _inconclusive("INVALID_PRIMARY_CELL", [f"non-finite or out-of-range inference in cell {key}"], len(cells))
        if point > 0 and lower > 0 and p_holm <= alpha:
            positive.append({"barrier_ticks": key[0], "horizon_ticks": key[1]})
        if point < 0 and upper < 0 and p_holm <= alpha:
            negative.append({"barrier_ticks": key[0], "horizon_ticks": key[1]})
    if positive and negative:
        label = "P2_DIAGNOSTIC_INCONCLUSIVE"
        reason = "CONFLICTING_FAMILYWISE_POSITIVE_AND_NEGATIVE_CELLS"
    elif positive:
        label = "P2_DIAGNOSTIC_MECHANISM_SUPPORTED"
        reason = "AT_LEAST_ONE_POSITIVE_CELL_AND_ZERO_NEGATIVE_CELLS"
    else:
        label = "P2_DIAGNOSTIC_MECHANISM_NOT_SUPPORTED"
        reason = "ZERO_POSITIVE_CELLS_EVIDENCE_THRESHOLD_NOT_MET"
    return {
        "label": label,
        "reason": reason,
        "validation_errors": [],
        "familywise_alpha": alpha,
        "n_primary_cells": len(cells),
        "positive_cells": positive,
        "negative_cells": negative,
        "secondary_evidence_used": False,
        "winner_selected": False,
        "edge_declared": False,
        "promotion_eligible": False,
    }

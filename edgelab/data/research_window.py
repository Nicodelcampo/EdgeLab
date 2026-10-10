"""Gated multi-session window reader built only from certified single-session shards.

Fail-closed replacement for using ``continuous_contract.build_continuous_series`` as a
research input: every calendar session of the requested window must either pass the
metadata gate or appear as a caller-declared exclusion, and the whole window is gated
BEFORE any source file is opened. Hashes are caller pins, not approval; see
docs/DATA_CONSUMER_MATRIX.md.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from edgelab.data.research_data_gate import DataEligibilityError, _day, require_research_eligibility
from edgelab.data.research_session import read_research_session


def read_research_window(*, shard_paths, start_trade_date, end_trade_date_exclusive, certificate,
        regime_manifest, root, liquidity_limits, expected_certificate_sha256, expected_regime_sha256,
        expected_liquidity_limits_sha256, declared_exclusions=None):
    """Read every calendar session in ``[start, end)`` or fail before opening any file.

    ``shard_paths`` maps trade_date -> shard path and must cover exactly the
    non-excluded sessions. ``declared_exclusions`` maps trade_date -> non-empty reason;
    an excluded session is never read and is reported in the evidence. A session that is
    neither eligible nor declared aborts the window: no implicit omission or filling.
    """
    start, end = _day(start_trade_date), _day(end_trade_date_exclusive)
    if end <= start:
        raise DataEligibilityError("empty or inverted window")
    if not isinstance(shard_paths, Mapping):
        raise DataEligibilityError("shard paths: expected object")
    exclusions = dict(declared_exclusions or {})
    for day, reason in exclusions.items():
        _day(day)
        if not isinstance(reason, str) or not reason.strip():
            raise DataEligibilityError("every exclusion needs an explicit reason")
    calendar = regime_manifest.get("calendar_trade_dates") if isinstance(regime_manifest, Mapping) else None
    if not isinstance(calendar, list) or not calendar:
        raise DataEligibilityError("missing full trading calendar")
    window = [_day(d) for d in calendar if isinstance(d, int) and not isinstance(d, bool) and start <= d < end]
    if not window:
        raise DataEligibilityError("window has no calendar sessions")
    if set(exclusions) - set(window):
        raise DataEligibilityError("exclusion outside the requested window")
    wanted = [d for d in window if d not in exclusions]
    if not wanted:
        raise DataEligibilityError("every session excluded")
    if sorted(shard_paths) != wanted:
        raise DataEligibilityError("shard paths must cover exactly the non-excluded window sessions")
    pins = dict(certificate=certificate, regime_manifest=regime_manifest, root=root,
        liquidity_limits=liquidity_limits, expected_certificate_sha256=expected_certificate_sha256,
        expected_regime_sha256=expected_regime_sha256,
        expected_liquidity_limits_sha256=expected_liquidity_limits_sha256)
    # Whole window gated on metadata first: one bad session means zero files opened.
    for day in wanted:
        require_research_eligibility(trade_date=day, **pins)

    import pyarrow as pa
    import pyarrow.compute as pc

    tables, sessions, previous_regime = [], [], None
    for day in wanted:
        table, evidence = read_research_session(path=Path(shard_paths[day]), trade_date=day, **pins)
        n = len(table)
        if "ts_utc_ns" in table.column_names and "sequence" in table.column_names:
            table = table.take(pc.sort_indices(table, sort_keys=[("ts_utc_ns", "ascending"),
                                                                 ("sequence", "ascending")]))
        reset = [False] * n
        if n and evidence["regime_id"] != previous_regime:
            reset[0] = True
        previous_regime = evidence["regime_id"] if n else previous_regime
        if "state_reset_flag" in table.column_names:
            table = table.drop(["state_reset_flag"])
        table = table.append_column("regime_id", pa.array([evidence["regime_id"]] * n, type=pa.string()))
        table = table.append_column("state_reset_flag", pa.array(reset, type=pa.bool_()))
        tables.append(table)
        sessions.append({k: evidence[k] for k in ("trade_date", "contract", "regime_id", "source_sha256", "rows")})
    out = pa.concat_tables(tables)
    if "ts_utc_ns" in out.column_names and "sequence" in out.column_names and len(out) > 1:
        ts, seq = out["ts_utc_ns"].to_numpy(), out["sequence"].to_numpy()
        if ((ts[1:] < ts[:-1]) | ((ts[1:] == ts[:-1]) & (seq[1:] <= seq[:-1]))).any():
            raise DataEligibilityError("sessions overlap or repeat (ts_utc_ns, sequence) across shards")
    evidence = {"root": root, "start_trade_date": start, "end_trade_date_exclusive": end,
        "sessions": sessions, "declared_exclusions": {d: exclusions[d] for d in sorted(exclusions)},
        "data_certificate_sha256": expected_certificate_sha256, "roll_schedule_sha256": expected_regime_sha256,
        "liquidity_limits_sha256": expected_liquidity_limits_sha256, "reader_contract": "research_window_v1",
        "promotion_allowed": False, "authority_authenticated": False,
        "independent_review_verified_by_reader": False}
    return out, evidence

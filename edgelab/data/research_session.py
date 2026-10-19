"""Opt-in single-session Parquet reader; never a whole-contract filter-after-read.

Gate before file open, homogeneous identity stats before hashing/payload, exact
caller-pinned shard bytes before deserialization. Requires audited truthful Parquet
metadata; this is not a sandbox against malicious files or a global holdout firewall.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from edgelab.data.research_data_gate import DataEligibilityError, _sha, require_research_eligibility

IDENTITY_COLUMNS = ("root", "contract", "trade_date")


def read_research_session(*, path, certificate, regime_manifest, root, trade_date,
        liquidity_limits, expected_certificate_sha256, expected_regime_sha256,
        expected_liquidity_limits_sha256):
    """Read ONLY a certified, homogeneous single-session shard, with evidence.

    Session certificate must bind shard basename, byte size, SHA256 and row count.
    This API is not automatically used by nt8_reader, continuous_contract, array
    CLI, builders or Kaggle. Independent review and campaign/D2 authority are
    external prerequisites; hashes alone do not grant either.
    """
    decision = require_research_eligibility(certificate=certificate,
        regime_manifest=regime_manifest, root=root, trade_date=trade_date,
        liquidity_limits=liquidity_limits, expected_certificate_sha256=expected_certificate_sha256,
        expected_regime_sha256=expected_regime_sha256,
        expected_liquidity_limits_sha256=expected_liquidity_limits_sha256)
    target = certificate["sessions"][f"{root}|{decision['contract']}|{trade_date}"]
    shard = target.get("shard")
    file = Path(path)
    if not isinstance(shard, dict) or shard.get("basename") != file.name or not _sha(shard.get("sha256")):
        raise DataEligibilityError("missing/mismatched pinned session shard identity")
    for key in ("size_bytes", "rows"):
        if type(shard.get(key)) is not int or shard[key] <= 0:
            raise DataEligibilityError("invalid pinned shard " + key)
    # Optional Arrow dependency is imported only after metadata gate passes.
    import pyarrow as pa
    import pyarrow.parquet as pq
    with file.open("rb") as handle:
        # Same open descriptor for metadata, hash and data, avoiding path replacement.
        handle.seek(0, 2)
        if handle.tell() != shard["size_bytes"]:
            raise DataEligibilityError("session shard size mismatch")
        handle.seek(0)
        parquet = pq.ParquetFile(handle)
        metadata = parquet.metadata
        schema = parquet.schema_arrow
        if metadata.num_rows != shard["rows"] or metadata.num_row_groups == 0:
            raise DataEligibilityError("session shard row count mismatch")
        if not all(c in schema.names for c in IDENTITY_COLUMNS):
            raise DataEligibilityError("session shard missing canonical identity columns")
        if not (pa.types.is_string(schema.field("root").type) and
                pa.types.is_string(schema.field("contract").type) and
                pa.types.is_integer(schema.field("trade_date").type)):
            raise DataEligibilityError("invalid canonical identity column types")
        expected = {"root": root, "contract": decision["contract"], "trade_date": trade_date}
        # Every row group must belong to this exact session. Never read then filter.
        for i in range(metadata.num_row_groups):
            group = metadata.row_group(i)
            columns = {group.column(j).path_in_schema: group.column(j) for j in range(group.num_columns)}
            for name, value in expected.items():
                stats = columns[name].statistics
                if (stats is None or not stats.has_min_max or not stats.has_null_count
                        or stats.null_count != 0 or stats.min != value or stats.max != value):
                    raise DataEligibilityError("mixed/unknown shard identity statistics: " + name)
        handle.seek(0)
        hasher = hashlib.sha256()
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
        if hasher.hexdigest() != shard["sha256"]:
            raise DataEligibilityError("session shard SHA256 mismatch")
        table = parquet.read()
        # Redundant actual identity validation; not protection against forged metadata.
        for name, value in expected.items():
            if any(x != value for x in table[name].to_pylist()):
                raise DataEligibilityError("actual session identity mismatch: " + name)
    evidence = dict(decision, source_sha256=shard["sha256"], rows=len(table),
        reader_contract="single_session_shard_v1", upstream_features_audited=False,
        existing_consumers_rewired=False, independent_review_verified_by_reader=False)
    return table, evidence

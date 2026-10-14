"""Bounded independent liquid-release audit. Real inputs execute only in Kaggle.

No outcomes, trading signals, source edits, release approval or tick exports.
Opaque checksum reads precede a GLOBAL dual-clock footer gate; only after every
asset passes may any market column be deserialized. Receipts contain aggregates.
"""
from __future__ import annotations

import hashlib
import json
import os
try:
    import resource                       # no existe en Windows
except ImportError:                       # pragma: no cover
    resource = None
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

CUTOFF_NS = 1_790_805_600_000_000_000
CUTOFF_TD = 20261001
BATCH_ROWS = 262144
MAX_BYTES = 12_000_000_000
EXPECTED_TYPES = {
    "ts_utc_ns": pa.int64(), "price_ticks": pa.int64(), "bid_ticks": pa.int64(),
    "ask_ticks": pa.int64(), "volume": pa.int64(), "aggressor": pa.int8(),
    "regime_id": pa.int16(), "trade_date": pa.int32(), "outside_regular": pa.bool_(),
    "source_id": pa.int16(), "source_row": pa.int64(), "release_row": pa.int64(),
}
ALL_COLUMNS = set(EXPECTED_TYPES) | {"root", "contract"}


class AuditStop(RuntimeError):
    pass


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, obj):
    path = Path(path)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, sort_keys=True, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def checked_path(root, relative):
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise AuditStop("invalid relative file path")
    dest = Path(root) / p
    if not dest.resolve().is_relative_to(Path(root).resolve()) or dest.is_symlink():
        raise AuditStop("file outside release root or symlink")
    return dest


def verify_files(root, manifest_sha):
    """Hashes are identity checks, not approval. Does not deserialize Parquet."""
    mp = checked_path(root, "release_manifest.json")
    if sha(mp) != manifest_sha:
        raise AuditStop("manifest identity mismatch")
    m = json.loads(mp.read_text())
    if m.get("schema") != "edgelab_liquid_release_v1" or not m.get("assets"):
        raise AuditStop("manifest schema/assets invalid")
    entries = {v["file"]: v for v in m["assets"].values()}
    if len(entries) != len(m["assets"]) or entries.keys() & m["metadata_files"].keys():
        raise AuditStop("duplicate manifest paths")
    entries.update(m["metadata_files"])
    if sum(int(v["bytes"]) for v in entries.values()) > MAX_BYTES:
        raise AuditStop("input byte budget")
    for rel, info in entries.items():
        p = checked_path(root, rel)
        if not p.is_file() or p.stat().st_size != int(info["bytes"]) or sha(p) != info["sha256"]:
            raise AuditStop("file identity mismatch: " + rel)
    actual = {str(p.relative_to(root)) for p in Path(root).rglob("*") if p.is_file()}
    if actual != set(entries) | {"release_manifest.json"}:
        raise AuditStop("unexpected or missing release files")
    return m, len(entries) + 1


def footer_gate(path):
    """No read_table/read_row_group/iter_batches calls permitted here."""
    pf = pq.ParquetFile(path)
    schema = pf.schema_arrow
    if set(schema.names) != ALL_COLUMNS or len(schema.names) != len(ALL_COLUMNS):
        raise AuditStop("unexpected market schema")
    for name, typ in EXPECTED_TYPES.items():
        if schema.field(name).type != typ:
            raise AuditStop("market column type mismatch: " + name)
    for name in ("root", "contract"):
        typ = schema.field(name).type
        if not pa.types.is_dictionary(typ) or typ.value_type != pa.string():
            raise AuditStop("dictionary identity column required: " + name)
    summary = []
    for g in range(pf.metadata.num_row_groups):
        rg = pf.metadata.row_group(g)
        if rg.num_rows <= 0:
            raise AuditStop("empty market row group")
        stats = {}
        for name in ("trade_date", "ts_utc_ns"):
            st = rg.column(schema.names.index(name)).statistics
            if st is None or not st.has_min_max or st.null_count != 0:
                raise AuditStop("missing/null dual-clock statistics")
            stats[name] = (int(st.min), int(st.max))
        lo, hi = stats["trade_date"]
        tlo, thi = stats["ts_utc_ns"]
        if lo != hi or hi >= CUTOFF_TD or thi >= CUTOFF_NS or tlo < 0 or thi < tlo:
            raise AuditStop("reserved, mixed or invalid dual-clock row group")
        try:
            day = datetime.strptime(str(lo), "%Y%m%d")
        except ValueError:
            raise AuditStop("invalid trading date") from None
        ct = ZoneInfo("America/Chicago")
        lower = int(((day - timedelta(days=1)).replace(hour=17, tzinfo=ct)).timestamp() * 10**9)
        upper = int(day.replace(hour=17, tzinfo=ct).timestamp() * 10**9)
        # Outside-regular prints may be retained, but their trading-date label
        # must still be consistent with the product's declared CT session clock.
        if tlo < lower or thi >= upper:
            raise AuditStop("timestamp/trading-date footer disagreement")
        summary.append(dict(group=g, trade_date=lo, rows=rg.num_rows))
    if not summary:
        raise AuditStop("empty asset")
    return pf, summary


def metadata_audit(root):
    """Granular tables remain in Kaggle; only counts leave this function."""
    meta = Path(root) / "metadata"
    frames = {n: pd.read_parquet(meta / (n + ".parquet")) for n in (
        "selection_decisions", "session_index", "source_manifest", "contract_runs",
        "excluded_sessions", "calendar_derived", "source_conflicts", "dup_blocks")}
    dec, idx = frames["selection_decisions"], frames["session_index"]
    for name, frame in [("decisions", dec), ("session_index", idx)]:
        if frame.duplicated(["instrument", "trade_date"]).any():
            raise AuditStop("duplicate " + name + " identity")
        if (frame["trade_date"] >= CUTOFF_TD).any():
            raise AuditStop("reserved session metadata")
    if set(zip(dec.instrument, dec.trade_date)) != set(zip(idx.instrument, idx.trade_date)):
        raise AuditStop("decision/index identity mismatch")
    fields = ["instrument", "trade_date", "status", "contract"]
    # Nullable contract values compare as the same explicit missing token.
    a = dec[fields].fillna("<NULL>").sort_values(fields[:2]).reset_index(drop=True)
    b = idx[fields].fillna("<NULL>").sort_values(fields[:2]).reset_index(drop=True)
    if not a.equals(b):
        raise AuditStop("decision/index content mismatch")
    selected_unknown_spread = 0
    selected_without_candidate = 0
    for row in dec.itertuples():
        if row.status != "SELECTED":
            continue
        candidates = json.loads(row.candidates)
        match = [x for x in candidates if x["contract"] == row.contract]
        if len(match) != 1:
            selected_without_candidate += 1
        elif match[0].get("spread_p50") is None or not np.isfinite(float(match[0]["spread_p50"])):
            selected_unknown_spread += 1
    tz = pd.read_csv(meta / "tz_verdicts.csv")
    missing = pd.read_csv(meta / "missing_exports.csv")
    policy = json.loads((meta / "liquidity_policy.json").read_text())
    summary = {
        "decision_states": {str(k): int(v) for k, v in dec.status.value_counts().items()},
        "selected_unknown_spread": selected_unknown_spread,
        "selected_without_unique_candidate": selected_without_candidate,
        "decisions_with_noncompetitive_assumption": int(dec.assumptions.fillna("").ne("").sum()),
        "source_rows": len(frames["source_manifest"]),
        "source_conflict_rows": len(frames["source_conflicts"]),
        "source_conflict_contract_sessions": len(frames["source_conflicts"][["contract", "trade_date"]].drop_duplicates()),
        "duplicate_block_rows": len(frames["dup_blocks"]),
        "timezone_verdicts": {str(k): int(v) for k, v in tz.verdict.value_counts().items()},
        "unapproved_policies": sum(not p.get("approved_by") for p in policy.values()),
        "missing_export_report_rows": len(missing),
        "future_availability_impact": "NOT_IDENTIFIABLE_FROM_PUBLISHED_SIDECARS_NEEDS_PRESELECTION_CENSUS",
    }
    return frames, summary


def audit_asset(asset, pf, groups, info, frames):
    idx = frames["session_index"]
    expected = idx[(idx.instrument == asset) & (idx.status == "SELECTED")].set_index("trade_date")
    src = frames["source_manifest"].query("instrument == @asset")
    if src.duplicated("source_id").any() or src.empty:
        raise AuditStop("source identity duplicate/absent")
    source_contract = dict(zip(src.source_id.astype(int), src.contract))
    last_source_row = {}
    counts = Counter()
    per_day = Counter()
    previous_ts = -1
    previous_td = -1
    previous_regime = 0
    total = 0
    for group in groups:
        td = group["trade_date"]
        if td not in expected.index:
            raise AuditStop("payload session has no selected decision")
        exp = expected.loc[td]
        for batch in pf.iter_batches(batch_size=BATCH_ROWS, row_groups=[group["group"]], use_threads=False):
            n = batch.num_rows
            for name in batch.schema.names:
                counts["null:" + name] += batch.column(name).null_count
            if any(batch.column(name).null_count for name in batch.schema.names):
                raise AuditStop("null payload value")
            v = {name: batch.column(name).to_numpy(zero_copy_only=False) for name in EXPECTED_TYPES}
            ts, dates, regimes = v["ts_utc_ns"], v["trade_date"], v["regime_id"]
            # Recheck metadata truth on allowed payload. Reserved footer inputs
            # have already been globally rejected, never admitted to this loop.
            if (ts >= CUTOFF_NS).any() or (dates >= CUTOFF_TD).any():
                raise AuditStop("payload contradicts dual-clock footer")
            counts["timestamp_backwards"] += int((np.diff(ts) < 0).sum()) + int(ts[0] < previous_ts)
            counts["trading_date_backwards"] += int((np.diff(dates) < 0).sum()) + int(dates[0] < previous_td)
            counts["regime_backwards"] += int((np.diff(regimes) < 0).sum()) + int(regimes[0] < previous_regime)
            counts["wrong_trade_date"] += int((dates != td).sum())
            counts["wrong_regime"] += int((regimes != int(exp.regime_id)).sum())
            counts["wrong_release_row"] += int((v["release_row"] != np.arange(total, total+n, dtype=np.int64)).sum())
            roots = pc.unique(pc.cast(batch.column("root"), pa.string())).to_pylist()
            contracts = pc.unique(pc.cast(batch.column("contract"), pa.string())).to_pylist()
            counts["batches_wrong_root"] += int(roots != [asset])
            counts["batches_wrong_contract"] += int(contracts != [exp.contract])
            px, bid, ask, volume = (v[k] for k in ("price_ticks", "bid_ticks", "ask_ticks", "volume"))
            counts["nonpositive_price"] += int((px <= 0).sum())
            counts["nonpositive_volume"] += int((volume <= 0).sum())
            q = (bid > 0) & (ask > 0)
            counts["crossed_quote"] += int((q & (bid > ask)).sum())
            counts["locked_quote"] += int((q & (bid == ask)).sum())
            counts["missing_quote"] += int((~q).sum())
            counts["invalid_quote_encoding"] += int((((bid <= 0) & (bid != -1)) | ((ask <= 0) & (ask != -1))).sum())
            ag = np.zeros(n, dtype=np.int8)
            regular_book = q & (ask > bid)
            ag[regular_book & (px >= ask)] = 1
            ag[regular_book & (px <= bid)] = -1
            counts["quote_rule_disagreement"] += int((ag != v["aggressor"]).sum())
            counts["invalid_aggressor"] += int((~np.isin(v["aggressor"], [-1, 0, 1])).sum())
            counts["unclassified_aggressor"] += int((v["aggressor"] == 0).sum())
            counts["outside_regular"] += int(v["outside_regular"].sum())
            counts["negative_source_row"] += int((v["source_row"] < 0).sum())
            for sid in np.unique(v["source_id"]):
                sid = int(sid)
                if sid not in source_contract or source_contract[sid] != exp.contract:
                    raise AuditStop("source identity/contract mismatch")
                sr = v["source_row"][v["source_id"] == sid]
                counts["source_row_nonincreasing"] += int((np.diff(sr) <= 0).sum()) + int(sr[0] <= last_source_row.get(sid, -1))
                last_source_row[sid] = int(sr[-1])
            previous_ts, previous_td, previous_regime = int(ts[-1]), int(dates[-1]), int(regimes[-1])
            total += n
            per_day[td] += n
    per_day_expected = {int(d): int(r.rows_written) for d, r in expected.iterrows()}
    if dict(per_day) != per_day_expected:
        raise AuditStop("session-index row recount mismatch")
    if total != int(info["rows"]) or len(per_day) != int(info["sessions"]):
        raise AuditStop("manifest row/session recount mismatch")
    if min(per_day) != int(info["first_trade_date"]) or max(per_day) != int(info["last_trade_date"]):
        raise AuditStop("manifest coverage boundary mismatch")
    informational = {"locked_quote", "missing_quote", "unclassified_aggressor", "outside_regular"}
    failures = {k: int(v) for k, v in counts.items() if v and k not in informational}
    return dict(asset=asset, rows=total, sessions=len(per_day), row_groups=len(groups),
                counts=dict(counts), failures=failures, technical_checks_passed=not failures)


def run_audit(root, manifest_sha, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    result = dict(schema="liquid_release_payload_audit_v1", status="STARTED",
                  manifest_sha256=manifest_sha, assets=[], market_payload_batches_started=False,
                  research_approved=False, promotion_approved=False, pnl_computed=False,
                  canonical_brain_written=False)
    try:
        m, checked = verify_files(root, manifest_sha)
        result["identity"] = dict(release_id=m["release_id"], files_verified=checked,
                                  declared_code=m.get("code"), declared_status=m["status"])
        gated = {asset: footer_gate(checked_path(root, info["file"])) for asset, info in m["assets"].items()}
        result["global_dual_clock_footer_gate"] = "PASS"
        result["footer_rows"] = sum(pf.metadata.num_rows for pf, _ in gated.values())
        frames, result["metadata"] = metadata_audit(root)
        write_json(output / "progress.json", result)
        for asset, info in m["assets"].items():
            result["market_payload_batches_started"] = True
            pf, groups = gated[asset]
            result["assets"].append(audit_asset(asset, pf, groups, info, frames))
            result["elapsed_seconds"] = time.monotonic() - start
            write_json(output / "progress.json", result)
            print("AUDITED", asset, result["assets"][-1]["rows"], flush=True)
        result["status"] = "CONTENT_CHECKS_PASS_NOT_RESEARCH_APPROVED" if all(a["technical_checks_passed"] for a in result["assets"]) else "CONTENT_FINDINGS_NOT_RESEARCH_APPROVED"
        result["row_count"] = sum(a["rows"] for a in result["assets"])
        result["session_asset_count"] = sum(a["sessions"] for a in result["assets"])
        if result["row_count"] != result["footer_rows"]:
            raise AuditStop("independent footer/payload recount mismatch")
    except AuditStop as exc:
        result.update(status="STOP", reason=str(exc))
    except Exception as exc:
        # Never serialize raw private frames, paths, signed URLs or data values.
        result.update(status="ERROR", error_type=type(exc).__name__)
    result["elapsed_seconds"] = time.monotonic() - start
    result["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None
    write_json(output / "receipt.json", result)
    return result


def download_inputs(root, manifest, sources):
    """Network only inside Kaggle. Source URLs are transport, never authority."""
    if not Path("/kaggle/working").is_dir() or not Path(root).resolve().is_relative_to(Path("/kaggle/temp")):
        raise AuditStop("real input downloads restricted to Kaggle temporary storage")
    entries = {x["file"]: x for x in manifest["assets"].values()}
    entries.update(manifest["metadata_files"])
    entries["release_manifest.json"] = {"bytes": sources["manifest_bytes"], "sha256": sources["manifest_sha256"]}
    if set(entries) != set(sources["urls"]) or sum(v["bytes"] for v in entries.values()) > MAX_BYTES:
        raise AuditStop("transport inventory mismatch/budget")
    for relative, e in entries.items():
        url = sources["urls"][relative]
        u = urllib.parse.urlparse(url)
        prefix = "/kagglesdsdata/datasets/12574934/20729690/"
        if u.scheme != "https" or u.netloc != "storage.googleapis.com" or u.path != prefix + relative:
            raise AuditStop("unexpected transport destination")
        p = checked_path(root, relative)
        p.parent.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256()
        n = 0
        # No transparent retries/resubmission. Exceptions must not print URLs.
        with urllib.request.urlopen(url, timeout=120) as response, open(p, "wb") as f:
            if response.geturl() != url:
                raise AuditStop("transport redirect rejected")
            for chunk in iter(lambda: response.read(8 << 20), b""):
                n += len(chunk)
                if n > e["bytes"]:
                    raise AuditStop("transport size overrun")
                h.update(chunk)
                f.write(chunk)
        if n != e["bytes"] or h.hexdigest() != e["sha256"]:
            raise AuditStop("transport byte/hash mismatch")
        print("FETCHED", relative, n, flush=True)
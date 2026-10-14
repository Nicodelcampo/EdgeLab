#!/usr/bin/env python3
"""Synthetic defect probes for liquid-release producer 705229bc.

No market inputs. Run against an isolated export of that commit, not the
research branch's working tree. Observed defects are not assertions that the
published release contains corrupt ticks. This is NOT an approval test suite.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
from unittest import mock

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

SOURCE_COMMIT = "705229bc67d6eb4ff3e0762b0bbd2d80da6bd8d9"
CUTOFF = 1_790_805_600_000_000_000


def load(path, name):
    import sys
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run(source_root):
    root = Path(source_root)
    base = root / "edgelab/data/liquid_release"
    sel = load(base / "selection.py", "_liquid_selection_probe")
    rr = load(base / "release_reader.py", "_liquid_reader_probe")
    policy = sel.LiquidityPolicy("synthetic-fixed", 1000, 100, 4)
    days = [20260105, 20260106, 20260107, 20260108]
    cols = ["contract", "trade_date", "vol", "n", "spread_p50", "coverage"]
    findings = []

    def decide(rows, calendar=days):
        return sel.select_sessions(pd.DataFrame(rows, columns=cols), calendar, policy)

    rows = [("ES 03-26", d, 5000, 500, 1, sel.OK) for d in days]
    rows += [("ES 06-26", days[0], 4000, 500, 1, sel.OK)]
    a = decide(rows).set_index("trade_date").loc[days[2], "status"]
    b = decide(rows + [("ES 06-26", days[3], 4000, 500, 1, sel.OK)]).set_index("trade_date").loc[days[2], "status"]
    assert (a, b) == (sel.SELECTED, sel.UNDETERMINED)
    findings.append(dict(id="LRA-01", observed=True, before=a, after=b,
                         meaning="Adding only a future candidate row changes an earlier decision."))

    mutated = [(k, d, (10**9 if k == "ES 06-26" else 1) if d >= days[2] else v, n, sp, cv)
               for k, d, v, n, sp, cv in rows]
    aa = decide(rows).query("trade_date <= 20260107")["contract"].fillna("").tolist()
    bb = decide(mutated).query("trade_date <= 20260107")["contract"].fillna("").tolist()
    assert aa == bb
    findings.append(dict(id="CONTROL-FUTURE-VALUES", observed=True,
                         meaning="Mutating future volumes alone does not change these earlier choices."))

    for spread, label in [(None, "None"), (float("nan"), "NaN")]:
        d = decide([("ES 03-26", days[0], 5000, 500, spread, sel.OK)], days[:2])
        assert d.iloc[0]["status"] == sel.SELECTED
        findings.append(dict(id="LRA-02-" + label, observed=True,
                             meaning="Candidate with unknown spread passes the absolute spread gate."))
    d = decide([("ES 03-26", days[0], 5000, 500, 9, sel.OK)], days[:2])
    assert d.iloc[0]["status"] == sel.NO_ELIGIBLE
    findings.append(dict(id="CONTROL-HIGH-SPREAD", observed=True,
                         meaning="Known high spread correctly fails."))

    for coverage in [sel.UNKNOWN, sel.MISSING]:
        rs = [("ES 03-26", days[0], 5000, 500, 1, sel.OK),
              ("ES 03-26", days[1], 5000, 500, 1, sel.OK),
              ("ES 06-26", days[0], 4000, 500, 1, sel.OK),
              ("ES 06-26", days[1], 4000, 500, 1, coverage)]
        status = decide(rs, days[:3]).iloc[-1]["status"]
        if coverage == sel.UNKNOWN:
            assert status == sel.UNDETERMINED
        else:
            assert status == sel.SELECTED
        findings.append(dict(id="LRA-03-" + coverage, observed=True, status=status,
                             meaning="MISSING does not block like UNKNOWN. Production asset_frame assigns OK; live reachability unmeasured."))

    with tempfile.TemporaryDirectory() as td:
        release = Path(td)
        (release / "data").mkdir()
        path = release / "data/ES_ticks.parquet"
        t = pa.table({"trade_date": pa.array([20260930], pa.int32()),
                      "ts_utc_ns": pa.array([CUTOFF + 1], pa.int64()),
                      "price_ticks": pa.array([1], pa.int64())})
        pq.write_table(t, path)
        man = dict(schema=rr.SCHEMA, status="CANDIDATE_NOT_RESEARCH_APPROVED",
                   research_allowed=False, promotion_allowed=False,
                   liquidity_policy_approved=False,
                   assets={"ES": dict(file="data/ES_ticks.parquet", bytes=path.stat().st_size,
                                      sha256=rr.sha256_file(path), rows=1)},
                   metadata_files={"metadata/missing.json": dict(bytes=10, sha256="0"*64)})
        (release / "release_manifest.json").write_text(json.dumps(man))
        reads = []
        orig = pq.ParquetFile.read_row_groups
        with mock.patch.object(pq.ParquetFile, "read_row_groups", autospec=True,
                               side_effect=lambda self, groups, **kw:
                               (reads.append(list(groups)), orig(self, groups, **kw))[1]):
            got = rr.read_asset(release, "ES", 20260930, 20260930)
        assert len(got) == 1 and reads == [[0]]
        findings.append(dict(id="LRA-04", observed=True, payload_reads=len(reads),
                             meaning="Reserved timestamp with pre-holdout trade_date is read; timestamp footer is not checked."))
        assert rr.load_manifest(release)["ES"].rows == 1
        findings.append(dict(id="LRA-05", observed=True,
                             meaning="Reader admits a candidate manifest and ignores absent/hash-listed metadata; external admission gate is required."))
        man["assets"]["ES"]["sha256"] = "0"*64
        (release / "release_manifest.json").write_text(json.dumps(man))
        try:
            rr.load_manifest(release)
            raise AssertionError("tampered hash accepted")
        except rr.ReleaseStop:
            pass
        findings.append(dict(id="CONTROL-TAMPER", observed=True,
                             meaning="Default content hash validation correctly rejects a mismatch."))

    # Import the verifier from the isolated source tree; it needs no exports
    # because expected_rows is replaced by a one-row synthetic expectation.
    import sys
    sys.path.insert(0, str(root))
    verifier = load(root / "tools/verify_release.py", "_liquid_verifier_probe")
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "reserved.parquet"
        t = pa.table({"trade_date": pa.array([20261001], pa.int32()),
                      "ts_utc_ns": pa.array([CUTOFF + 1], pa.int64()),
                      "price_ticks": pa.array([1], pa.int64()),
                      "bid_ticks": pa.array([1], pa.int64()),
                      "ask_ticks": pa.array([2], pa.int64()),
                      "contract": ["ES 12-26"], "regime_id": pa.array([1], pa.int16())})
        pq.write_table(t, path)
        reads = []
        orig = pq.ParquetFile.read_row_group
        with mock.patch.object(verifier, "expected_rows", return_value=(
                pd.Series({20261001: 1}), pd.Series({20261001: "ES 12-26"}))), \
             mock.patch.object(pq.ParquetFile, "read_row_group", autospec=True,
                               side_effect=lambda self, group, **kw:
                               (reads.append(group), orig(self, group, **kw))[1]):
            result = verifier.verify_asset("ES", dict(file=path.name, rows=1), td, None, None, None)
        assert reads == [0] and result["ok"] is False
        findings.append(dict(id="LRA-06", observed=True, payload_reads=len(reads),
                             subsequently_rejected=True,
                             meaning="Verifier reads reserved row-group payload, then flags holdout; post-read rejection is too late."))

    return dict(schema="liquid_release_synthetic_probes_v1", source_commit=SOURCE_COMMIT,
                market_data_read=False, published_release_impact_measured=False,
                source_sha256={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [base / "selection.py", base / "release_reader.py",
                                         root / "tools/verify_release.py"]},
                probes=findings, assertions_passed=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    result = run(a.source_root)
    Path(a.out).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(assertions_passed=True, probes=len(result["probes"]),
                          market_data_read=False)))
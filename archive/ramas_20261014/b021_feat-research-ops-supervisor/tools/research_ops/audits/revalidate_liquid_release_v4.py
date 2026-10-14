"""Independent synthetic repair checks; no real market inputs or approval.

Run in a fresh process against a separate checkout/export of producer commit
7afe22d49295dbf8c3c51f5ba80c0b22ff45795d. Not a payload audit.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def run(source_root):
    sys.path.insert(0, str(Path(source_root).resolve()))
    from edgelab.data.liquid_release import release_reader as rr
    from edgelab.data.liquid_release import selection as s
    from edgelab.data.liquid_release.plan import propose_policy
    checks = []
    days = [20260105, 20260106, 20260107, 20260108]
    cols = ["contract", "trade_date", "vol", "n", "spread_p50", "coverage"]
    policy = s.LiquidityPolicy("independent-synthetic", 1000, 100, 4)

    def decide(rows, cal=days):
        return s.select_sessions(pd.DataFrame(rows, columns=cols), cal, policy).set_index("trade_date")

    rows = [("ES 03-26", d, 5000, 500, 1, s.OK) for d in days]
    rows += [("ES 06-26", days[0], 4000, 500, 1, s.OK)]
    before = decide(rows)
    after = decide(rows + [("ES 06-26", days[3], 4000, 500, 1, s.OK)])
    assert before.loc[20260107, "status"] == after.loc[20260107, "status"] == s.UNDETERMINED
    checks.append("future_candidate_availability_no_longer_changes_earlier_decision")
    for spread in [None, float("nan")]:
        assert decide([("ES 03-26", days[0], 5000, 500, spread, s.OK)], days[:2]).iloc[0].status == s.NO_ELIGIBLE
    checks.append("None_and_NaN_spread_rejected_without_exception")
    for coverage in [s.MISSING, s.UNKNOWN]:
        rs = rows + [("ES 06-26", days[1], 4000, 500, 1, coverage)]
        assert decide(rs).loc[20260107, "status"] == s.UNDETERMINED
    checks.append("MISSING_and_UNKNOWN_block_significant_missing_competitor")

    df = pd.DataFrame([dict(instrument="ES", trade_date=int(d.strftime("%Y%m%d")),
                           n_reg=5000+i, vol_reg=10000+i, spread_p50=1)
                       for i, d in enumerate(pd.bdate_range("2025-01-01", periods=90))])
    pol = propose_policy(df, "ES")
    changed = df.copy()
    changed.loc[80:, ["n_reg", "vol_reg", "spread_p50"]] = 10**9
    assert propose_policy(changed, "ES") == pol
    checks.append("policy_unchanged_by_values_after_80_session_calibration_window")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "data").mkdir()
        path = root / "data/ES_ticks.parquet"

        def make(ts, td):
            pq.write_table(pa.table({"trade_date": pa.array([td], pa.int32()),
                                      "ts_utc_ns": pa.array([ts], pa.int64()),
                                      "price_ticks": pa.array([1], pa.int64())}), path)
            m = dict(schema=rr.SCHEMA, research_allowed=False,
                     status="CANDIDATE_NOT_RESEARCH_APPROVED", metadata_files={},
                     assets={"ES": dict(file="data/ES_ticks.parquet", bytes=path.stat().st_size,
                                        sha256=rr.sha256_file(path), rows=1)})
            (root / "release_manifest.json").write_text(json.dumps(m))
            return m

        for ts, td in [(rr.HOLDOUT_FIRST_TS_NS, 20260930), (rr.HOLDOUT_FIRST_TS_NS-1, 20261001)]:
            make(ts, td)
            with mock.patch.object(pq.ParquetFile, "read_row_groups", side_effect=AssertionError("payload read")) as spy:
                try:
                    rr.read_asset(root, "ES", 20260930, 20260930, purpose="audit")
                    raise AssertionError("reserved clock admitted")
                except rr.ReleaseStop:
                    pass
                assert spy.call_count == 0
        checks.append("both_reserved_clocks_stop_before_reader_payload")
        m = make(rr.HOLDOUT_FIRST_TS_NS-1, 20260930)
        for kwargs in [{}, {"purpose": "research"}]:
            try:
                rr.load_manifest(root, **kwargs)
                raise AssertionError("undeclared/unapproved admission")
            except rr.ReleaseStop:
                pass
        assert len(rr.read_asset(root, "ES", 20260930, 20260930, purpose="audit")) == 1
        checks.append("purpose_required_and_unapproved_research_stopped_audit_allowed")
        # Explicitly disclose this mode; its name alone is not trusted authority.
        assert rr.load_manifest(root, purpose="provisional_research")
        provisional_admits_candidate = True
        m["metadata_files"]["metadata/absent.json"] = dict(bytes=2, sha256="0"*64)
        (root / "release_manifest.json").write_text(json.dumps(m))
        try:
            rr.load_manifest(root, purpose="audit")
            raise AssertionError("missing listed metadata accepted")
        except rr.ReleaseStop:
            pass
        checks.append("missing_listed_metadata_rejected")
        make(rr.HOLDOUT_FIRST_TS_NS, 20261001)
        spec = importlib.util.spec_from_file_location("v4_verify_independent", Path(source_root)/"tools/verify_release.py")
        verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(verifier)
        with mock.patch.object(pq.ParquetFile, "read_row_group", side_effect=AssertionError("payload read")) as spy:
            try:
                verifier.verify_asset("ES", dict(file="data/ES_ticks.parquet", rows=1), root, None, None, None)
                raise AssertionError("reserved verifier input admitted")
            except rr.ReleaseStop:
                pass
            assert spy.call_count == 0
        checks.append("verifier_stops_reserved_input_before_payload_or_census")

    sources = ["edgelab/data/liquid_release/selection.py", "edgelab/data/liquid_release/plan.py",
               "edgelab/data/liquid_release/release_reader.py", "tools/verify_release.py"]
    return dict(schema="liquid_release_v4_independent_repair_checks_v1",
                source_commit="7afe22d49295dbf8c3c51f5ba80c0b22ff45795d",
                checks_passed=checks, check_groups=len(checks),
                source_sha256={p: hashlib.sha256((Path(source_root)/p).read_bytes()).hexdigest() for p in sources},
                provisional_research_mode_admits_candidate=provisional_admits_candidate,
                provisional_mode_requires_separate_job_authorization=True,
                real_market_data_read=False, live_payload_verified=False,
                canonical_approval=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--out", required=True)
    a = parser.parse_args()
    result = run(a.source_root)
    Path(a.out).write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({"independent_check_groups_passed": result["check_groups"], "real_market_data_read": False}))
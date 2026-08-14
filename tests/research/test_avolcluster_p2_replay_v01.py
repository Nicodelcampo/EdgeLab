# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import tempfile

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from diag.tasa_senales.avolcluster_p2_replay_v01 import (
    TZ,
    decide_p2,
    match_one_to_one,
    parse_oracle,
    run,
    seal_payload,
    session_begin_utc_ns,
)


def z(t, lo=10, hi=12, direction=1):
    return {"time": t, "lower_tick": lo, "upper_tick": hi, "direction": direction}


def test_one_to_one_does_not_reuse_python_row():
    t = datetime(2026, 4, 10, 6, 22)
    diff = match_one_to_one([z(t), z(t)], [z(t)])
    assert diff["matched"] == 1
    assert len(diff["unmatched_oracle"]) == 1
    assert len(diff["unmatched_python"]) == 0
    assert decide_p2(True, "PASS", diff) == "ABSTAIN_P2"


def test_extra_python_zone_fails_p2():
    t = datetime(2026, 4, 10, 6, 22)
    diff = match_one_to_one([z(t)], [z(t), z(t, lo=20, hi=22)])
    assert len(diff["unmatched_python"]) == 1
    assert decide_p2(True, "PASS", diff) == "ABSTAIN_P2"


def test_exact_bijection_passes_and_60_seconds_is_inclusive():
    t = datetime(2026, 4, 10, 6, 22)
    p = z(datetime(2026, 4, 10, 6, 23))
    diff = match_one_to_one([z(t)], [p])
    assert diff["matched"] == 1
    assert not diff["unmatched_oracle"] and not diff["unmatched_python"]
    assert decide_p2(True, "PASS", diff) == "P2_PASS"


def test_hash_mismatch_short_circuits_before_oracle_and_pyarrow():
    root = Path(tempfile.mkdtemp())
    bad_parquet = root / "not_canonical.parquet"
    bad_parquet.write_bytes(b"PAR1-not-the-canonical-file-PAR1")
    missing_oracle = root / "does_not_exist.csv"
    payload = run(bad_parquet, missing_oracle)
    assert payload["label"] == "ABSTAIN_INPUT"
    assert payload["input"]["hash_ok"] is False
    assert payload["input"]["oracle_instrument_ok"] is None
    assert payload["source_of_truth"]["oracle_meta_instrument"] is None
    assert payload["oracle_rows"] is None
    assert payload["formal_race_executed"] is False
    assert payload["outcomes_accessed"] is False
    assert payload["pnl_accessed"] is False
    assert "p1a_gate" not in payload


def test_input_and_p1a_fail_closed():
    empty = {"unmatched_oracle": [], "unmatched_python": []}
    assert decide_p2(False, "PASS", empty) == "ABSTAIN_INPUT"
    assert decide_p2(True, "FAIL", empty) == "ABSTAIN_P2"


def test_session_begin_matches_cme_eth_and_dst():
    # 2026-04-10 06:22 CT belongs to session beginning 2026-04-09 17:00 CT.
    local = pd.Timestamp("2026-04-10 06:22:00", tz=TZ)
    got_ns = session_begin_utc_ns(int(local.tz_convert("UTC").value))
    got = pd.Timestamp(got_ns, unit="ns", tz="UTC").tz_convert(TZ)
    assert got.strftime("%Y-%m-%d %H:%M:%S %z") == "2026-04-09 17:00:00 -0500"


def test_oracle_parser_reads_meta_and_zone_created_only():
    text = "\n".join([
        "# meta,indicator=aVolClusterPOI,version=0.5,instrument=6E 09-26",
        "event_seq,event_type,bar_close_time,zone_id,lower_tick,upper_tick,direction",
        "1,ZONE_CREATED,2026-04-10T06:22:00.000,7,23564,23572,SHORT",
        "2,FIRST_TOUCH,2026-04-10T06:23:00.000,7,23564,23572,SHORT",
    ])
    p = Path(tempfile.mkdtemp()) / "oracle.csv"
    p.write_text(text, encoding="utf-8")
    meta, rows = parse_oracle(p)
    assert meta["instrument"] == "6E 09-26"
    assert len(rows) == 1 and rows[0]["direction"] == -1


def test_payload_seal_is_deterministic_and_self_excluding():
    a = seal_payload({"b": 2, "a": 1})
    b = seal_payload({"a": 1, "b": 2, "payload_sha256": "old"})
    assert a["payload_sha256"] == b["payload_sha256"]
    assert len(a["payload_sha256"]) == 64


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test(); print("PASS", test.__name__)
    print("TODOS LOS TESTS P2 v0.1 PASARON")

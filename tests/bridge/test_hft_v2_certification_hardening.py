import sqlite3

from tools.validate_hft_v2_certification import validate


def database(with_reason=True):
    con = sqlite3.connect(":memory:")
    con.execute("""CREATE TABLE hft_ticks_v2 (
      instrument TEXT, contract TEXT, session_id TEXT, tick_seq INTEGER,
      timestamp_ns INTEGER, price_ticks INTEGER, volume REAL)""")
    reason = ", termination_reason TEXT" if with_reason else ""
    con.execute(f"""CREATE TABLE hft_zones_v2 (
      instrument TEXT, contract TEXT, session_id TEXT, zone_seq INTEGER,
      start_tick_seq INTEGER, end_tick_seq INTEGER, start_ts_ns INTEGER,
      end_ts_ns INTEGER, available_ts_ns INTEGER, direction INTEGER,
      lo_ticks INTEGER, hi_ticks INTEGER, pasos INTEGER, vol REAL,
      avg_ms REAL, total_ms REAL, volume_rate REAL,
      parameter_manifest_sha256 TEXT, indicator_source_sha256 TEXT{reason})""")
    for seq, ts in enumerate((100, 101, 101), start=1):
        con.execute("INSERT INTO hft_ticks_v2 VALUES (?,?,?,?,?,?,?)", ("NQ JUN26", "NQ 06-26", "S1", seq, ts, 80000 + seq, 1.0))
    cols = "instrument,contract,session_id,zone_seq,start_tick_seq,end_tick_seq,start_ts_ns,end_ts_ns,available_ts_ns,direction,lo_ticks,hi_ticks,pasos,vol,avg_ms,total_ms,volume_rate,parameter_manifest_sha256,indicator_source_sha256"
    vals = ["NQ JUN26", "NQ 06-26", "S1", 1, 1, 2, 100, 101, 102, 1, 80001, 80002, 2, 2.0, 1.0, 1.0, 2.0, "a" * 64, "b" * 64]
    if with_reason:
        cols += ",termination_reason"
        vals.append("REVERSAL")
    con.execute(f"INSERT INTO hft_zones_v2 ({cols}) VALUES ({','.join('?' for _ in vals)})", vals)
    con.commit()
    return con


def test_clean_single_contract_preflight_passes_but_is_not_full_certification():
    con = database()
    result = validate(con, "NQ JUN26")
    assert result["is_pass"] is True
    assert result["status"] == "PASS_HARDENED_PREFLIGHT_NOT_FULL_PARITY"
    assert "PREFLIGHT_ONLY" in result["certification_scope"]


def test_missing_termination_reason_fails_closed():
    result = validate(database(with_reason=False), "NQ JUN26")
    assert result["is_pass"] is False
    assert any(error["code"] == "MISSING_ZONE_COLUMNS" for error in result["errors"])


def test_available_before_end_fails():
    con = database()
    con.execute("UPDATE hft_zones_v2 SET available_ts_ns=end_ts_ns-1")
    result = validate(con, "NQ JUN26")
    assert any(error["code"] == "AVAILABLE_BEFORE_END" for error in result["errors"])


def test_timestamp_inversion_fails():
    con = database()
    con.execute("UPDATE hft_ticks_v2 SET timestamp_ns=99 WHERE tick_seq=3")
    result = validate(con, "NQ JUN26")
    assert any(error["code"] == "NONMONOTONIC_TICK_TIMESTAMPS" for error in result["errors"])


def test_tick_sequence_gap_fails():
    con = database()
    con.execute("UPDATE hft_ticks_v2 SET tick_seq=4 WHERE tick_seq=3")
    result = validate(con, "NQ JUN26")
    assert any(error["code"] == "NONCONTIGUOUS_TICK_SEQUENCE" for error in result["errors"])


def test_multiple_contracts_abstain_until_reset_is_fixed():
    con = database()
    con.execute("UPDATE hft_ticks_v2 SET contract='NQ 09-26' WHERE tick_seq=3")
    result = validate(con, "NQ JUN26")
    assert any(error["code"] == "MULTICONTRACT_COMPARATOR_NOT_YET_CERTIFIABLE" for error in result["errors"])

"""Parser del EventLog NT8 (formato CSV Gaps2 + pipe BigTrap2) y matcher de
paridad (PASS/WARN/FAIL). Fixtures de texto sintéticas con el MISMO formato que
NT8 exporta — no son oráculos reales y no acreditan paridad real."""
from edgelab.bridge.oracle import parse_nt8_log
from edgelab.bridge.parity import match_zones

GAPS2_CSV = """# meta indicator=Gaps2 version=2.0
event_seq,event_type,ts,unix_ms,gap_id,created_unix_ms,top,bottom,size_ticks,is_bullish,atr_at_creation,vol_at_creation,vol_baseline,vol_ratio,state,max_pen_pct,touches,bars_since,price_at_event,extra
1,ZONE_CREATED,2025-08-01 15:10:00.000,1754061000000,G000001,1754061000000,1.158000,1.157000,20,1,,3.00,,,VIRGIN,0.0000,0,0,1.158000,
2,ZONE_TOUCHED,2025-08-01 15:20:00.000,1754061600000,G000001,1754061000000,1.158000,1.157000,20,1,,3.00,,,TOUCHED,0.2000,1,1,1.157800,epoch=1
3,ZONE_INVALIDATED,2025-08-01 15:40:00.000,1754062800000,G000001,1754061000000,1.158000,1.157000,20,1,,3.00,,,INVALIDATED,1.0000,1,2,1.156900,full_fill
"""

BIGTRAP_PIPE = """# meta indicator=BigTrap2 version=2.0
1|2025-08-01T15:10:00.000|ZONE_CREATED|zone_id=T0001;side=bull;lo=1.157000;hi=1.158000
2|2025-08-01T15:30:00.000|ZONE_INVALIDATED|zone_id=T0001;reason=fill
"""


def test_parse_gaps2_csv(tmp_path):
    p = tmp_path / "g.csv"
    p.write_text(GAPS2_CSV, encoding="utf-8")
    orc = parse_nt8_log(str(p), chart_tz="UTC", tick_size=0.00005)
    assert orc["indicator"] == "Gaps2"
    assert len(orc["zones"]) == 1
    z = orc["zones"][0]
    assert z["id"] == "G000001" and z["state"] == "INVALIDATED"
    assert z["created_ms"] == 1754061000000 and z["ended_ms"] == 1754062800000
    assert z["touches"] == 1 and abs(z["top"] - 1.158) < 1e-12


def test_parse_bigtrap_pipe(tmp_path):
    p = tmp_path / "t.log"
    p.write_text(BIGTRAP_PIPE, encoding="utf-8")
    orc = parse_nt8_log(str(p), chart_tz="UTC")
    assert orc["indicator"] == "BigTrap2"
    z = orc["zones"][0]
    assert z["id"] == "T0001" and z["state"] == "INVALIDATED"
    assert z["top"] == 1.158 and z["bottom"] == 1.157
    assert z["end_reason"] == "fill"


def _z(zid, top_t, bot_t, ms, state="VIRGIN", touches=0, tick=0.00005):
    return dict(id=zid, top=top_t * tick, bottom=bot_t * tick,
                created_ms=ms, ended_ms=None, state=state, touches=touches)


def test_matcher_pass():
    py = [_z("G1", 23160, 23140, 1000)]
    nt = [_z("N1", 23160, 23140, 1200)]      # 200ms < strict tol
    r = match_zones(py, nt, 0.00005)
    assert r["gate"] == "PASS" and r["summary"]["matched_pairs"] == 1


def test_matcher_warn_timestamp_and_feature():
    py = [_z("G1", 23160, 23140, 1000, touches=2)]
    nt = [_z("N1", 23160, 23140, 5000, touches=3)]   # 4s > strict, < tol
    r = match_zones(py, nt, 0.00005)
    assert r["gate"] == "WARN"
    assert r["summary"]["counts"].get("TIMESTAMP_DIFF") == 1
    assert r["summary"]["counts"].get("FEATURE_DIFF") == 1


def test_matcher_fail_geometry_and_orphans():
    py = [_z("G1", 23160, 23140, 1000), _z("G2", 23000, 22990, 99000)]
    nt = [_z("N1", 23163, 23140, 1000)]              # 3 ticks de diff geom
    r = match_zones(py, nt, 0.00005, tol_geom_ticks=0)
    assert r["gate"] == "FAIL"
    assert r["summary"]["counts"].get("GEOMETRY_DIFF") == 1
    assert r["summary"]["counts"].get("MISSING_IN_NT8") == 1


def test_matcher_extra_diags_warn():
    py = [_z("G1", 23160, 23140, 1000)]
    nt = [_z("N1", 23160, 23140, 1000)]
    r = match_zones(py, nt, 0.00005,
                    extra_diags=[dict(code="CALIBRATION_DIFF", py_id=None, nt8_id=None,
                                      detail="feriado CME no modelado")])
    assert r["gate"] == "WARN"
    assert r["summary"]["counts"]["CALIBRATION_DIFF"] == 1

"""Conversor NT8 .Last.txt -> parquet canónico + verificación de timezone por
schedule-fit contra el calendario CME (DST-aware). Fixtures 100% sintéticos."""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")
NS = 1_000_000_000


def _utcns(iso):
    return int(np.datetime64(iso, "ns").astype("int64"))


def _week_in_session_utc():
    """Instantes UTC reales, en sesión CME, cada hora durante una semana."""
    from edgelab.data.nt8_timezone import cme_forbidden
    base = _utcns("2025-07-27T22:00:00")   # domingo apertura (17:00 CDT)
    hrs = base + np.arange(0, 5 * 24, dtype="int64") * 3600 * NS
    idx = pd.DatetimeIndex(hrs.astype("datetime64[ns]")).tz_localize("UTC").tz_convert(CT)
    return hrs[~cme_forbidden(idx.weekday.to_numpy(), idx.hour.to_numpy())]


def test_cme_forbidden_basic():
    from edgelab.data.nt8_timezone import cme_forbidden
    # sábado (5) prohibido; martes (1) 10:00 CT permitido; L-J 16:00 CT halt
    assert cme_forbidden([5], [10])[0]
    assert not cme_forbidden([1], [10])[0]
    assert cme_forbidden([1], [16])[0]


def test_verify_utc_true():
    from edgelab.data.nt8_timezone import verify_offset
    r = verify_offset(_week_in_session_utc(), offset_s=0)
    assert r.verified
    assert r.score < 0.01 and r.art_score > r.score + 0.02


def test_verify_utc_false_for_art_export():
    from edgelab.data.nt8_timezone import verify_offset
    # export ART: wall-clock local = UTC - 3h -> tratado como UTC cae fuera de sesión
    ts_art = _week_in_session_utc() - 3 * 3600 * NS
    assert not verify_offset(ts_art, offset_s=0).verified


def _line_from_ns(ns, last, bid, ask, vol):
    dt = np.datetime64(int(ns), "ns").astype("datetime64[s]").astype(object)
    return f"{dt:%Y%m%d %H%M%S} 0000000;{last};{bid};{ask};{vol}"


def _fixture_lines(bad_price=False):
    ts = _week_in_session_utc()
    lines = []
    for i, t in enumerate(ts):
        last = "1.17831" if (bad_price and i == 3) else ("1.17835" if i % 2 else "1.1783")
        lines.append(_line_from_ns(t, last, "1.1783", "1.17835", 1))
    return lines


def test_convert_file_utc_passes_and_writes(tmp_path):
    from databuild.build_nt8_ticks import convert_file
    p = tmp_path / "6E 09-25.Last.txt"
    p.write_text("\n".join(_fixture_lines()) + "\n", encoding="utf-8")
    s = convert_file(str(p), "6E 09-25", str(tmp_path / "out"))
    assert s["status"] in ("PASS", "PASS_WITH_WARNINGS"), s["fails"]
    assert s["metrics"]["tz_verification"]["verified_utc"] is True
    assert s["parquet"] is not None
    t = pq.read_table(s["parquet"])
    assert set(t.column_names) >= {"ts_utc_ns", "ts_local_ns", "price_ticks", "bid_ticks",
                                   "ask_ticks", "aggressor", "contract", "sequence"}
    assert t.column("ts_utc_ns").to_pylist() == t.column("ts_local_ns").to_pylist()  # offset 0
    assert set(t.column("aggressor").to_pylist()) <= {"buy", "sell", "unclassified"}


def test_convert_misaligned_price_fails(tmp_path):
    from databuild.build_nt8_ticks import convert_file
    p = tmp_path / "6E 09-25.Last.txt"
    p.write_text("\n".join(_fixture_lines(bad_price=True)) + "\n", encoding="utf-8")
    s = convert_file(str(p), "6E 09-25", str(tmp_path / "out"))
    assert s["status"] == "FAIL"
    assert any("desalinead" in f for f in s["fails"])
    assert s["parquet"] is None

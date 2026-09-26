# -*- coding: utf-8 -*-
"""Synthetic tests for the hardened aVolClusterPOI formal runner (v2.1).

Worlds: null (no planted edge), planted (zone always hit first),
misaligned zone log (must abstain). No real data, no outcomes.
v2.1 adds: control pad keeps controls out of the forming block and the
random-control diagnostic family is deterministic.
"""
import importlib.util
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "avolcluster_formal", ROOT / "diag" / "tasa_senales" / "avolcluster_formal.py"
)
af = importlib.util.module_from_spec(spec)
spec.loader.exec_module(af)

TICK = 5e-5


def _bars(n_per_session=1200, n_sessions=32, seed=7):
    random.seed(seed)
    bars = []
    t = datetime(2026, 4, 13, 18, 0)
    price = 22000
    for _s in range(n_sessions):
        for _i in range(n_per_session):
            price += random.choice([-1, 0, 1])
            hi = price + random.randint(0, 2)
            lo = price - random.randint(0, 2)
            bars.append((t, (price - 1) * TICK, hi * TICK, lo * TICK, price * TICK, 100.0))
            t += timedelta(minutes=1)
        t += timedelta(hours=2)  # session gap
    return bars


def _write_m1_headerless(bars, path):
    with open(path, "w") as f:
        for t, o, h, l, c, v in bars:
            f.write("%s;%s;%s;%s;%s;%s\n" % (t.strftime("%Y%m%d %H%M%S"), o, h, l, c, v))


def _write_m1_headered(bars, path):
    with open(path, "w") as f:
        f.write("Time,Open,High,Low,Close,Volume\n")
        for t, o, h, l, c, v in bars:
            f.write("%s,%s,%s,%s,%s,%s\n" % (t.strftime("%Y-%m-%d %H:%M:%S"), o, h, l, c, v))


def _write_zones(bars, idxs, path, time_shift=None):
    with open(path, "w") as f:
        f.write("event_seq,event_type,bar_close_time,lower_tick,upper_tick,session_index\n")
        for k, i in enumerate(idxs):
            t, o, h, l, c, v = bars[i]
            if time_shift is not None:
                t = t + time_shift
            ct = af.price_to_tick(c)
            f.write("%d,ZONE_CREATED,%s,%d,%d,%d\n" % (k, t.strftime("%Y-%m-%d %H:%M:%S"), ct + 2, ct + 2, k))


def _world(tmp_path):
    bars = _bars()
    creators = list(range(50, len(bars) - 60, 500))
    _write_m1_headerless(bars, tmp_path / "m1.csv")
    _write_zones(bars, creators, tmp_path / "zones.csv")
    return bars, creators


def test_parse_both_formats(tmp_path):
    bars, creators = _world(tmp_path)
    _write_m1_headered(bars, tmp_path / "m1h.csv")
    z = af.load_zones(tmp_path / "zones.csv")
    b1 = af.load_m1(tmp_path / "m1.csv")
    b2 = af.load_m1(tmp_path / "m1h.csv")
    assert len(z) == len(creators)
    assert len(b1) == len(bars) == len(b2)
    assert b1[10]["time"] == bars[10][0] == b2[10]["time"]


def test_alignment_and_geometry(tmp_path):
    bars, _ = _world(tmp_path)
    z = af.load_zones(tmp_path / "zones.csv")
    b1 = af.load_m1(tmp_path / "m1.csv")
    align = af.choose_alignment(z, b1)
    assert align["offset_min"] == 0 and align["match_rate"] == 1.0 and align["by_time_ok"]
    by_time = {b["time"]: i for i, b in enumerate(b1)}
    g = af.zone_geometry(z[0], b1, by_time, 0)
    assert g["d"] == 2 and g["w"] == 1 and g["side"] == "above"
    assert (g["m_lo"], g["m_hi"]) == (2 * g["anchor"] - g["hi"], 2 * g["anchor"] - g["lo"])
    assert g["m_hi"] < g["lo"]  # disjoint


def test_session_split(tmp_path):
    bars, _ = _world(tmp_path)
    ses = af.split_sessions(af.load_m1(tmp_path / "m1.csv"))
    assert max(ses) + 1 == 32


def test_null_world_no_spurious_edge(tmp_path):
    bars, creators = _world(tmp_path)
    out = af.run(str(tmp_path / "zones.csv"), str(tmp_path / "m1.csv"))
    assert out["label"] == "AVOL_NO_EDGE"
    assert out["zones"]["n"] == len(creators)
    assert out["match_rate_control"] >= 0.40
    assert out["zones"]["ic"]["n_sessions"] >= 30
    lo, hi = out["zones"]["ic"]["ci95_lower"], out["zones"]["ic"]["ci95_upper"]
    assert lo <= 0 <= hi
    assert "control_random" in out and "contrast_zone_minus_control_random" in out
    assert out["by_side"]["above"]["n"] == len(creators)


def test_planted_signal_detected(tmp_path):
    bars, creators = _world(tmp_path)
    bars2 = list(bars)
    for i in creators:
        ct = af.price_to_tick(bars2[i][4])
        t2, o2, h2, l2, c2, v2 = bars2[i + 1]
        bars2[i + 1] = (t2, o2, (ct + 4) * TICK, (ct + 1) * TICK, (ct + 4) * TICK, v2)
    _write_m1_headerless(bars2, tmp_path / "m1p.csv")
    out = af.run(str(tmp_path / "zones.csv"), str(tmp_path / "m1p.csv"))
    assert out["zones"]["p_zone_over_decided"] > 0.9
    assert out["label"] == "AVOL_ZONE_EDGE"


def test_misaligned_log_abstains(tmp_path):
    bars, creators = _world(tmp_path)
    _write_zones(bars, creators, tmp_path / "zones_bad.csv", time_shift=timedelta(hours=7))
    out = af.run(str(tmp_path / "zones_bad.csv"), str(tmp_path / "m1.csv"))
    assert out["label"] == "ABSTAIN_ALIGNMENT"


def test_control_pad_and_random_determinism(tmp_path):
    bars, creators = _world(tmp_path)
    b1 = af.load_m1(tmp_path / "m1.csv")
    ses = af.split_sessions(b1)
    creator_set = set(creators)
    geo = {"bar": creators[5]}
    j = af.pick_control_bar(geo, ses, creator_set, len(b1))
    assert j is not None
    assert all(abs(j - c) > af.CONTROL_PAD_BARS for c in creator_set)
    r1 = af.pick_random_control_bar(geo, ses, creator_set, len(b1))
    r2 = af.pick_random_control_bar(geo, ses, creator_set, len(b1))
    assert r1 == r2 and r1 is not None
    assert all(abs(r1 - c) > af.CONTROL_PAD_BARS for c in creator_set)

# -*- coding: utf-8 -*-
"""aVolClusterPOI v0.5 — formal first-passage race, OFF_PRICE vs mirror + bar control.

Hardened 2026-08-13 after F2.7/F2.8 audit lessons. Replaces the quick v1 tool.

Rules inherited from the F2.7 saga:
  - r_i = 0 (tie or double censor) ENTERS the session mean.
  - Ties are NOT double censoring; categories are reported separately.
  - Contrast vs control is PAIRED by session, never sqrt(se1^2+se2^2).
  - Half-tick-safe price->tick (no bare banker's round on price/tick_size).
  - Alignment between NT8 zone log and M1 export is a fail-closed gate.

Population: ZONE_CREATED (OFF_PRICE) rows of the NT8 v0.5 CSV.
Bars: NT8 1-minute export. Both headerless NT8 format
  yyyyMMdd HHmmss;Open;High;Low;Close;Volume
and headered CSV (Time,Open,High,Low,Close[,Volume]) are accepted.

outcomes_accessed=False, pnl_accessed=False, holdout_included=False.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

SCHEMA_VERSION = "avolcluster_formal_v2"
TICK = 5e-5
HORIZON_BARS = 2000
SESSION_GAP_MINUTES = 30
RESOLUTION_MIN = 0.30
TIE_FRAC_MAX = 0.10
MATCH_RATE_MIN = 0.40
ALIGN_MATCH_MIN = 0.95
ALIGN_ADJACENCY_MIN = 0.80
MIN_SESSIONS = 30


def price_to_tick(price):
    return int(math.floor(float(price) / TICK + 0.5))


# ---------------------------------------------------------------- parsers

_TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%Y%m%d %H%M%S",
    "%Y%m%d %H%M",
)


def parse_time(text):
    t = (text or "").strip()[:19] if "T" in (text or "") else (text or "").strip()
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(t, fmt)
        except ValueError:
            continue
    raise ValueError("unparseable time: %r" % text)


def _sniff_delim(line):
    return ";" if line.count(";") > line.count(",") else ","


def load_zones(path):
    """NT8 aVol v0.5 CSV -> ZONE_CREATED rows (OFF_PRICE only)."""
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    header_i = next(
        (i for i, ln in enumerate(lines) if "event_type" in ln and "lower_tick" in ln),
        None,
    )
    if header_i is None:
        raise RuntimeError("no header with event_type/lower_tick found in %s" % path)
    delim = _sniff_delim(lines[header_i])
    rows = list(csv.DictReader(lines[header_i:], delimiter=delim))
    out = []
    for r in rows:
        if (r.get("event_type") or "").strip() != "ZONE_CREATED":
            continue
        out.append(
            dict(
                bar_close_time=parse_time(r.get("bar_close_time") or r.get("time")),
                lo=int(float(r["lower_tick"])),
                hi=int(float(r["upper_tick"])),
                session_index=r.get("session_index"),
            )
        )
    if not out:
        raise RuntimeError("no ZONE_CREATED rows in %s" % path)
    return out


def load_m1(path):
    """M1 bars. Accepts headerless NT8 export or headered CSV."""
    lines = [ln for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError("empty M1 file %s" % path)
    first = lines[0]
    bars = []
    if any(ch.isalpha() for ch in first):
        delim = _sniff_delim(first)
        for row in csv.DictReader(lines, delimiter=delim):
            t = row.get("Time") or row.get("time") or row.get("Date") or row.get("bar_close_time")
            h = row.get("High") or row.get("high")
            l = row.get("Low") or row.get("low")
            c = row.get("Close") or row.get("close")
            if t is None or h is None or l is None or c is None:
                continue
            bars.append(dict(time=parse_time(t), high=float(h), low=float(l), close=float(c)))
    else:
        delim = _sniff_delim(first)
        for ln in lines:
            parts = ln.split(delim)
            if len(parts) < 5:
                continue
            bars.append(
                dict(
                    time=parse_time(parts[0].strip()),
                    high=float(parts[2]),
                    low=float(parts[3]),
                    close=float(parts[4]),
                )
            )
    if not bars:
        raise RuntimeError("no bars parsed from %s" % path)
    bars.sort(key=lambda b: b["time"])
    for b in bars:
        b["high_t"] = price_to_tick(b["high"])
        b["low_t"] = price_to_tick(b["low"])
        b["close_t"] = price_to_tick(b["close"])
    return bars


# ---------------------------------------------------------------- structure

def split_sessions(bars, gap_minutes=SESSION_GAP_MINUTES):
    """CME ETH: bars are 1 min apart inside a session; the daily break is a gap.
    Gap-based split avoids depending on the chart timezone."""
    gap = timedelta(minutes=gap_minutes)
    ses = [0] * len(bars)
    s = 0
    for i in range(1, len(bars)):
        if bars[i]["time"] - bars[i - 1]["time"] > gap:
            s += 1
        ses[i] = s
    return ses


def choose_alignment(zones, bars):
    """Try bar_close_time as close-time (offset 0) and as next-bar open (offset -1m).
    Gate: match_rate >= .95 and adjacency (close within 25 ticks of the band) >= .80.
    Fail-closed otherwise."""
    by_time = {b["time"]: i for i, b in enumerate(bars)}
    best = None
    for off_min in (0, -1):
        matched, adjacent = 0, 0
        for z in zones:
            t = z["bar_close_time"] + timedelta(minutes=off_min)
            i = by_time.get(t)
            if i is None:
                continue
            matched += 1
            close_t = bars[i]["close_t"]
            d_edge = close_t - z["hi"] if close_t > z["hi"] else (z["lo"] - close_t if close_t < z["lo"] else 0)
            if 0 <= d_edge <= 25:
                adjacent += 1
        match_rate = matched / len(zones)
        adjacency = adjacent / matched if matched else 0.0
        cand = dict(offset_min=off_min, match_rate=match_rate, adjacency=adjacency)
        if best is None or (match_rate, adjacency) > (best["match_rate"], best["adjacency"]):
            best = cand
    best["by_time_ok"] = best["match_rate"] >= ALIGN_MATCH_MIN and best["adjacency"] >= ALIGN_ADJACENCY_MIN
    return best


# ---------------------------------------------------------------- race

def first_hit(bars, start_i, lo_t, hi_t, end_i):
    i = start_i + 1
    while i <= end_i:
        if bars[i]["low_t"] <= hi_t and bars[i]["high_t"] >= lo_t:
            return i
        i += 1
    return None


def race(bars, i, lo, hi, m_lo, m_hi, horizon=HORIZON_BARS):
    end = min(len(bars) - 1, i + horizon)
    z = first_hit(bars, i, lo, hi, end)
    m = first_hit(bars, i, m_lo, m_hi, end)
    if z is None and m is None:
        return 0.0, "double_censor"
    if z is None:
        return -1.0, "mirror_first"
    if m is None:
        return 1.0, "zone_first"
    if z == m:
        return 0.0, "tie_same_bar"  # M1 only: cannot resolve intra-bar without ticks
    return (1.0, "zone_first") if z < m else (-1.0, "mirror_first")


def zone_geometry(zone, bars, by_time, offset_min):
    i = by_time.get(zone["bar_close_time"] + timedelta(minutes=offset_min))
    if i is None:
        return None
    close_t = bars[i]["close_t"]
    lo, hi = zone["lo"], zone["hi"]
    if lo <= close_t <= hi:
        return dict(bar=i, error="close_inside_band")  # not OFF_PRICE geometry
    if close_t > hi:
        d, side = close_t - hi, "below"   # band below close
    else:
        d, side = lo - close_t, "above"   # band above close
    w = hi - lo + 1
    m_lo, m_hi = 2 * close_t - hi, 2 * close_t - lo
    return dict(bar=i, lo=lo, hi=hi, d=d, w=w, side=side, anchor=close_t, m_lo=m_lo, m_hi=m_hi)


def pick_control_bar(geo, ses, creator_bars, n_bars, search_pad=3):
    """Nearest non-creator bar in the same gap-session, >= 3 bars away from any
    creator bar. Same-session pool, no imputation."""
    s = ses[geo["bar"]]
    best = None
    lo_i, hi_i = bars_ses_lo_hi(ses, s)
    for j in range(lo_i, hi_i + 1):
        if j in creator_bars:
            continue
        if any(abs(j - c) <= search_pad for c in creator_bars):
            continue
        if j + 5 >= n_bars:
            continue
        dist = abs(j - geo["bar"])
        if best is None or dist < best[0]:
            best = (dist, j)
    return None if best is None else best[1]


_session_span_cache = {}


def bars_ses_lo_hi(ses, s):
    span = _session_span_cache.get(id(ses), {}).get(s)
    if span is None:
        idx = [i for i, v in enumerate(ses) if v == s]
        span = (idx[0], idx[-1]) if idx else (0, -1)
        _session_span_cache.setdefault(id(ses), {})[s] = span
    return span


# ---------------------------------------------------------------- inference

def hac_bartlett_ci(values):
    """Bartlett HAC over the chronological series of session means.
    Mirrors the F2.7 approach: lag = ceil(sqrt(n)), weights 1 - k/(L+1)."""
    n = len(values)
    if n < MIN_SESSIONS:
        return dict(mean=None, se_hac=None, ci95_lower=None, ci95_upper=None,
                    lag=None, n_sessions=n, abstain_inferencia=True)
    mean = sum(values) / n
    L = max(1, math.ceil(math.sqrt(n)))
    d = [v - mean for v in values]
    var = sum(t * t for t in d) / n
    for k in range(1, L + 1):
        g = sum(d[t] * d[t - k] for t in range(k, n)) / n
        var += 2.0 * (1.0 - k / (L + 1)) * g
    se = math.sqrt(max(var / n, 0.0))
    return dict(mean=mean, se_hac=se, ci95_lower=mean - 1.96 * se,
                ci95_upper=mean + 1.96 * se, lag=L, n_sessions=n,
                abstain_inferencia=False)


def summarize(rows):
    """rows: list of dicts with session, r, category. Session-equal weight, zeros in."""
    by_s = {}
    for row in rows:
        by_s.setdefault(row["session"], []).append(row)
    ses_means = []
    cats = {"zone_first": 0, "mirror_first": 0, "tie_same_bar": 0, "double_censor": 0}
    for s in sorted(by_s):
        rs = by_s[s]
        ses_means.append(sum(r["r"] for r in rs) / len(rs))
        for r in rs:
            cats[r["category"]] = cats.get(r["category"], 0) + 1
    ic = hac_bartlett_ci(ses_means)
    n = len(rows)
    decided = cats.get("zone_first", 0) + cats.get("mirror_first", 0)
    return dict(
        n=n,
        n_sessions=len(ses_means),
        session_means=ses_means,
        ic=ic,
        cats=cats,
        n_decided=decided,
        frac_resolved=decided / n if n else 0.0,
        frac_tie=cats.get("tie_same_bar", 0) / n if n else 0.0,
        p_zone_over_decided=(cats.get("zone_first", 0) / decided) if decided else None,
    )


def paired_contrast(zone_rows, ctrl_rows):
    """Per-session difference of means, only sessions with both arms."""
    zm, cm = {}, {}
    for r in zone_rows:
        zm.setdefault(r["session"], []).append(r["r"])
    for r in ctrl_rows:
        cm.setdefault(r["session"], []).append(r["r"])
    diffs = []
    for s in sorted(set(zm) & set(cm)):
        diffs.append(sum(zm[s]) / len(zm[s]) - sum(cm[s]) / len(cm[s]))
    ic = hac_bartlett_ci(diffs)
    ic["n_paired_sessions"] = len(diffs)
    return ic


def decide(zones_sum, contrast, gates_ok, match_rate):
    ic = zones_sum["ic"]
    if not gates_ok or ic["abstain_inferencia"] or match_rate < MATCH_RATE_MIN:
        return "AVOL_UNDERPOWERED"
    if ic["ci95_upper"] is not None and ic["ci95_upper"] < 0:
        return "AVOL_FADE_POCKET"
    if ic["ci95_lower"] is not None and ic["ci95_lower"] > 0:
        if not contrast["abstain_inferencia"] and contrast["ci95_lower"] is not None and contrast["ci95_lower"] > 0:
            return "AVOL_ZONE_EDGE"
        return "AVOL_BAR_CONTEXT"
    return "AVOL_NO_EDGE"


# ---------------------------------------------------------------- main

def run(nt8_csv, m1_csv, horizon=HORIZON_BARS, out_path=None):
    zones = load_zones(nt8_csv)
    bars = load_m1(m1_csv)
    ses = split_sessions(bars)
    by_time = {b["time"]: i for i, b in enumerate(bars)}

    align = choose_alignment(zones, bars)
    if not align["by_time_ok"]:
        return dict(schema_version=SCHEMA_VERSION, label="ABSTAIN_ALIGNMENT",
                    alignment=align, outcomes_accessed=False)
    off = align["offset_min"]

    geo_rows, skipped = [], {"missing_bar": 0, "close_inside_band": 0}
    creator_bars = set()
    for z in zones:
        g = zone_geometry(z, bars, by_time, off)
        if g is None:
            skipped["missing_bar"] += 1
            continue
        if "error" in g:
            skipped[g["error"]] += 1
            continue
        geo_rows.append(g)
        creator_bars.add(g["bar"])

    zone_rows, ctrl_rows, matched_ctrl = [], [], 0
    for g in geo_rows:
        s = ses[g["bar"]]
        r, cat = race(bars, g["bar"], g["lo"], g["hi"], g["m_lo"], g["m_hi"], horizon)
        zone_rows.append(dict(session=s, r=r, category=cat, d=g["d"], w=g["w"], side=g["side"]))
        j = pick_control_bar(g, ses, creator_bars, len(bars))
        if j is None:
            continue
        anchor_c = bars[j]["close_t"]
        if g["side"] == "above":
            c_lo, c_hi = anchor_c + g["d"], anchor_c + g["d"] + g["w"] - 1
        else:
            c_hi, c_lo = anchor_c - g["d"], anchor_c - g["d"] - g["w"] + 1
        cm_lo, cm_hi = 2 * anchor_c - c_hi, 2 * anchor_c - c_lo
        rc, catc = race(bars, j, c_lo, c_hi, cm_lo, cm_hi, horizon)
        ctrl_rows.append(dict(session=s, r=rc, category=catc))
        matched_ctrl += 1

    zones_sum = summarize(zone_rows)
    match_rate = matched_ctrl / len(geo_rows) if geo_rows else 0.0
    ctrl_sum = summarize(ctrl_rows)
    contrast = paired_contrast(zone_rows, ctrl_rows)

    gates = dict(
        sessions_ge_30=zones_sum["n_sessions"] >= MIN_SESSIONS,
        resolution=zones_sum["frac_resolved"] >= RESOLUTION_MIN,
        ties=zones_sum["frac_tie"] <= TIE_FRAC_MAX,
        match_rate=match_rate >= MATCH_RATE_MIN,
    )
    gates_ok = all(gates.values())
    label = decide(zones_sum, contrast, gates_ok, match_rate)

    payload = dict(
        schema_version=SCHEMA_VERSION,
        label=label,
        alignment=align,
        skipped=skipped,
        horizon_bars=horizon,
        zones=zones_sum,
        control=ctrl_sum,
        contrast_zone_minus_control=contrast,
        match_rate_control=match_rate,
        gates=gates,
        outcomes_accessed=False,
        pnl_accessed=False,
        holdout_included=False,
    )
    raw = json.dumps(payload, sort_keys=True, default=str).encode()
    payload["payload_sha256"] = hashlib.sha256(raw).hexdigest()
    if out_path:
        Path(out_path).write_text(json.dumps(payload, indent=2, default=str), "utf-8")
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("nt8_csv")
    ap.add_argument("m1_csv")
    ap.add_argument("--horizon", type=int, default=HORIZON_BARS)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    print(json.dumps(run(args.nt8_csv, args.m1_csv, args.horizon, args.out), indent=2, default=str))


if __name__ == "__main__":
    main()

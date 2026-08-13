# -*- coding: utf-8 -*-
"""OFF_PRICE first-passage vs same-width mirror.

Needs 1-minute OHLC (NT8 export or bars from ticks). Not P&L.
Zeros inside the band do not count as a hit. Same-bar double hit = censor.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def load_nt8_off(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    header_i = next(i for i, line in enumerate(lines) if line.startswith("event_seq"))
    rows = list(csv.DictReader(lines[header_i:]))
    return [r for r in rows if r["event_type"] == "ZONE_CREATED"]


def load_m1(path: Path):
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    bars = []
    for row in rows:
        t = row.get("Time") or row.get("time") or row.get("bar_close_time")
        bars.append(dict(
            time=t,
            high=float(row.get("High") or row.get("high")),
            low=float(row.get("Low") or row.get("low")),
            close=float(row.get("Close") or row.get("close")),
        ))
    return bars


def price_to_tick(price, tick_size=5e-5):
    return int(round(price / tick_size))


def first_hit(bars, start_i, lo, hi):
    for i in range(start_i + 1, len(bars)):
        high_t = price_to_tick(bars[i]["high"])
        low_t = price_to_tick(bars[i]["low"])
        if low_t <= hi and high_t >= lo:
            return i
    return None


def run(nt8_csv, m1_csv, horizon=2000):
    zones = load_nt8_off(Path(nt8_csv))
    bars = load_m1(Path(m1_csv))
    by_time = {b["time"][:19]: i for i, b in enumerate(bars)}
    wins = dict(zone=0, mirror=0, tie=0, none=0, missing_bar=0)
    for z in zones:
        key = (z["bar_close_time"] or "")[:19]
        i = by_time.get(key)
        if i is None:
            wins["missing_bar"] += 1
            continue
        lo, hi = int(z["lower_tick"]), int(z["upper_tick"])
        width = hi - lo + 1
        close_t = price_to_tick(bars[i]["close"])
        if close_t > hi:
            m_lo, m_hi = close_t + (close_t - hi), close_t + (close_t - lo)
        elif close_t < lo:
            m_lo, m_hi = close_t - (hi - close_t), close_t - (lo - close_t)
        else:
            wins["none"] += 1
            continue
        end = min(len(bars) - 1, i + int(horizon))
        z_hit = first_hit(bars[: end + 1], i, lo, hi)
        m_hit = first_hit(bars[: end + 1], i, m_lo, m_hi)
        if z_hit is None and m_hit is None:
            wins["none"] += 1
        elif z_hit is None:
            wins["mirror"] += 1
        elif m_hit is None:
            wins["zone"] += 1
        elif z_hit == m_hit:
            wins["tie"] += 1
        elif z_hit < m_hit:
            wins["zone"] += 1
        else:
            wins["mirror"] += 1
    n = wins["zone"] + wins["mirror"]
    p = wins["zone"] / n if n else None
    return dict(wins=wins, n_decided=n, p_zone=p, n_off=len(zones))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("nt8_csv")
    ap.add_argument("m1_csv")
    args = ap.parse_args()
    print(run(args.nt8_csv, args.m1_csv))


if __name__ == "__main__":
    main()

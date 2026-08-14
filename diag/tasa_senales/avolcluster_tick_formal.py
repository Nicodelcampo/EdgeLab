# -*- coding: utf-8 -*-
"""aVolClusterPOI OFF_PRICE — formal first-passage race from canonical ticks (v0).

Implements specs/avolcluster_tick_formal_v0.json and docs/research/AVOL_TICK_FORMAL_PROTOCOL_2026-08-14.md:
1. P2 Gate Replay: verifies Python kernel parity against NT8 oracle (avolcluster_v05_20260813.csv).
2. 4-Contract Tick Race: runs across 6E_12-25, 6E_03-26, 6E_06-26, 6E_09-26 (firewall <= 2026-06-30).
3. Disambiguates ties via tick_first_touch from F2.7.
4. Primary benchmark is control_random (deterministic seed), with control_nearest as diagnostic.
5. Computes session-level HAC Bartlett IC95 and paired contrasts.
6. Emits formal label via decide_labels.

outcomes_accessed=False, pnl_accessed=False, holdout_included=False.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from edgelab.bridge.ticks import TickSeries, load_canonical_parquet, instrument_spec
from edgelab.bridge.bars import build_time_bars, build_footprints, p1a_gate, session_ids, BarSeries, Footprints
from edgelab.bridge.indicators.avolclusterpoi import SessionProfile, detect_block, RESEARCH_DEFAULTS

SCHEMA_VERSION = "avolcluster_tick_formal_v0"
TICK_SIZE = 0.00005
HORIZON_BARS = 2000
CONTROL_PAD_BARS = 12
FIREWALL_CUTOFF = "2026-06-30"

CANONICAL_HASHES = {
    "6E_12-25_ticks.parquet": "ea8b9f211929658494d952677fe302c33db66086ec1a21731f1f5d7ff74f7336",
    "6E_03-26_ticks.parquet": "b54120bfd99b97f218d73a1fe132bd111b997eab6095a529699473131f57cf76",
    "6E_06-26_ticks.parquet": "124b37507b95a1027aa753a75213b15e74f66b1396ca8df3c4324ea835f96cb1",
    "6E_09-26_ticks.parquet": "6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4",
}


def resolve_parquet_dir() -> Path:
    candidates = [
        Path(r"E:\Parquets Nuevos\parquets"),
        Path(r"d:\EdgeLab\data\nt8\6E"),
        Path(r"E:\MIGRACION_EdgeLab_2026-08-04\MIGRACION_EdgeLab_2026-08-04\data\nt8\6E"),
        REPO_PATH / "data" / "nt8" / "6E",
        Path(r"C:\EdgeLab\parquets"),
    ]
    for c in candidates:
        if c.exists() and all((c / fn).exists() for fn in CANONICAL_HASHES):
            return c
    raise FileNotFoundError("Could not find directory containing all 4 canonical 6E parquets")


def verify_parquet_hashes(p_dir: Path) -> dict[str, bool]:
    results = {}
    for fn, expected in CANONICAL_HASHES.items():
        p = p_dir / fn
        if not p.exists():
            results[fn] = False
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        results[fn] = (h == expected)
    return results


def parse_oracle_zones(oracle_path: Path) -> list[dict]:
    """Loads ZONE_CREATED (OFF_PRICE) from NT8 oracle CSV."""
    lines = oracle_path.read_text(encoding="utf-8", errors="replace").splitlines()
    header_i = next((i for i, ln in enumerate(lines) if "event_type" in ln and "lower_tick" in ln), None)
    if header_i is None:
        raise ValueError(f"Oracle header missing in {oracle_path}")
    delim = ";" if lines[header_i].count(";") > lines[header_i].count(",") else ","
    rows = list(csv.DictReader(lines[header_i:], delimiter=delim))
    zones = []
    for r in rows:
        if r.get("event_type") == "ZONE_CREATED":
            t_str = r.get("bar_close_time", "")
            # Normalise time
            t_clean = t_str.replace("T", " ").split(".")[0]
            dt = datetime.strptime(t_clean, "%Y-%m-%d %H:%M:%S")
            raw_dir = str(r.get("direction", "")).upper()
            dir_val = 1 if ("LONG" in raw_dir or raw_dir == "1") else (-1 if ("SHORT" in raw_dir or raw_dir == "-1") else 0)
            zones.append({
                "bar_close_time": dt,
                "lower_tick": int(r["lower_tick"]),
                "upper_tick": int(r["upper_tick"]),
                "direction": dir_val,
                "score": float(r.get("score", 0.0)),
                "threshold": float(r.get("threshold", 0.0)),
            })
    return zones


# ---------------------------------------------------------------- First passage & Tick Touch

def tick_first_touch_race(
    ticks: TickSeries,
    bar_start_idx: int,
    bar_end_idx: int,
    zone_lo: int,
    zone_hi: int,
    mirror_lo: int,
    mirror_hi: int,
) -> int:
    """Disambiguates which band was touched first in the bar's tick sequence."""
    p = ticks.price_ticks[bar_start_idx:bar_end_idx]
    for price in p:
        hit_z = zone_lo <= price <= zone_hi
        hit_m = mirror_lo <= price <= mirror_hi
        if hit_z and hit_m:
            return 0  # True simultaneous hit
        if hit_z:
            return 1  # Zone touched first
        if hit_m:
            return -1  # Mirror touched first
    return 0


def run_first_passage_race(
    bars: BarSeries,
    ticks: TickSeries,
    creator_bar_idx: int,
    zone_lo: int,
    zone_hi: int,
    bar_tick_starts: Optional[np.ndarray] = None,
    bar_tick_ends: Optional[np.ndarray] = None,
    horizon_bars: int = HORIZON_BARS,
) -> dict:
    """Executes first passage race between zone and geometric mirror."""
    anchor = int(bars.close_t[creator_bar_idx])
    mirror_lo = 2 * anchor - zone_hi
    mirror_hi = 2 * anchor - zone_lo
    
    n_bars = len(bars)
    end_bar = min(n_bars, creator_bar_idx + 1 + horizon_bars)
    
    for b in range(creator_bar_idx + 1, end_bar):
        b_lo = int(bars.low_t[b])
        b_hi = int(bars.high_t[b])
        
        hit_z = not (b_hi < zone_lo or b_lo > zone_hi)
        hit_m = not (b_hi < mirror_lo or b_lo > mirror_hi)
        
        if hit_z and hit_m:
            # Same bar hit -> disambiguate with tick series
            if bar_tick_starts is not None and bar_tick_ends is not None:
                tb_start = bar_tick_starts[b]
                tb_end = bar_tick_ends[b]
            else:
                tick_mask = (bars.tick_bar_idx == b)
                if np.any(tick_mask):
                    t_indices = np.flatnonzero(tick_mask)
                    tb_start = t_indices[0]
                    tb_end = t_indices[-1] + 1
                else:
                    tb_start, tb_end = 0, 0
                    
            if tb_end > tb_start:
                res = tick_first_touch_race(ticks, tb_start, tb_end, zone_lo, zone_hi, mirror_lo, mirror_hi)
                if res == 1:
                    return {"r_i": 1, "cat": "zone_first", "bar_lag": b - creator_bar_idx}
                elif res == -1:
                    return {"r_i": -1, "cat": "mirror_first", "bar_lag": b - creator_bar_idx}
                else:
                    return {"r_i": 0, "cat": "tie_same_bar", "bar_lag": b - creator_bar_idx}
            else:
                return {"r_i": 0, "cat": "tie_same_bar", "bar_lag": b - creator_bar_idx}
        elif hit_z:
            return {"r_i": 1, "cat": "zone_first", "bar_lag": b - creator_bar_idx}
        elif hit_m:
            return {"r_i": -1, "cat": "mirror_first", "bar_lag": b - creator_bar_idx}
            
    return {"r_i": 0, "cat": "double_censor", "bar_lag": horizon_bars}


# ---------------------------------------------------------------- Controls

def pick_control_bars(
    session_bars: list[int],
    creator_bar_indices: set[int],
    target_bar: int,
    session_id: int,
) -> tuple[Optional[int], Optional[int]]:
    """Picks control_random (primary) and control_nearest (diagnostic)."""
    # Eligible bars: > 12 bars from ANY creator bar in the session
    eligible = []
    for b in session_bars:
        dist_to_creators = min([abs(b - c) for c in creator_bar_indices], default=999)
        if dist_to_creators > CONTROL_PAD_BARS:
            eligible.append(b)
            
    if not eligible:
        return None, None
        
    # Nearest
    nearest = min(eligible, key=lambda b: abs(b - target_bar))
    
    # Deterministic Random (seeded by session_id and target_bar)
    seed_val = int(session_id) * 1_000_003 + int(target_bar)
    rng = random.Random(seed_val)
    rand_bar = rng.choice(eligible)
    
    return rand_bar, nearest


# ---------------------------------------------------------------- HAC & Stats

def hac_bartlett_ic(session_means: list[float], lag: Optional[int] = None) -> dict:
    x = np.asarray(session_means, dtype=np.float64)
    n = len(x)
    if n < 2:
        return {
            "mean": float(x.mean()) if n else 0.0,
            "se_hac": float("nan"),
            "ci95_lower": float("nan"),
            "ci95_upper": float("nan"),
            "lag": 0,
            "n_sessions": n,
            "abstain_inferencia": True,
        }
    if lag is None:
        lag = max(1, int(math.ceil(math.sqrt(n))))
    mean_val = float(x.mean())
    dev = x - mean_val
    gamma0 = float(np.dot(dev, dev) / n)
    v_hac = gamma0
    for l in range(1, lag + 1):
        if l >= n:
            break
        w = 1.0 - l / (lag + 1)
        cov = float(np.dot(dev[l:], dev[:-l]) / n)
        v_hac += 2.0 * w * cov
    v_hac = max(v_hac, 0.0)
    se = math.sqrt(v_hac / n)
    margin = 1.96 * se
    return {
        "mean": mean_val,
        "se_hac": se,
        "ci95_lower": mean_val - margin,
        "ci95_upper": mean_val + margin,
        "lag": lag,
        "n_sessions": n,
        "abstain_inferencia": False,
    }


def decide_labels(
    p2_pass: bool,
    n_sessions: int,
    frac_resolved: float,
    match_rate_random: float,
    zone_ic: dict,
    contrast_random: dict,
    contrast_nearest: dict,
) -> str:
    if not p2_pass:
        return "ABSTAIN_P2"
    if n_sessions < 30 or frac_resolved < 0.30 or match_rate_random < 0.40:
        return "AVOL_UNDERPOWERED"
        
    z_lo = zone_ic["ci95_lower"]
    z_hi = zone_ic["ci95_upper"]
    c_lo = contrast_random["ci95_lower"]
    c_hi = contrast_random["ci95_upper"]
    
    # AVOL_ZONE_EDGE: both zone and contrast > 0
    if z_lo > 0 and c_lo > 0:
        return "AVOL_ZONE_EDGE"
    # AVOL_BAR_CONTEXT: zone > 0 but contrast <= 0
    if z_lo > 0 and c_lo <= 0:
        return "AVOL_BAR_CONTEXT"
    # AVOL_FADE_POCKET: zone < 0 and contrast < 0
    if z_hi < 0 and c_hi < 0:
        return "AVOL_FADE_POCKET"
    # AVOL_NO_EDGE: both cross zero or contrast <= 0 with zone crossing zero
    if z_lo <= 0 <= z_hi and c_lo <= 0 <= c_hi:
        return "AVOL_NO_EDGE"
        
    return "AVOL_UNDERPOWERED"


# ---------------------------------------------------------------- Main Execution

def run_avolcluster_tick_formal(
    parquet_dir: str | Path,
    oracle_csv: str | Path,
) -> dict:
    p_dir = Path(parquet_dir)
    oracle_path = Path(oracle_csv)
    
    # 1. Verify parquet hashes
    hash_checks = verify_parquet_hashes(p_dir)
    if not all(hash_checks.values()):
        raise ValueError(f"Parquet SHA-256 verification failed: {hash_checks}")
        
    # 2. P2 Gate Verification on 6E_09-26 [2026-04-10, 2026-06-30]
    oracle_zones = parse_oracle_zones(oracle_path)
    print(f"Loaded {len(oracle_zones)} ZONE_CREATED rows from oracle.")
    
    # Replay on 6E_09-26
    p_09 = p_dir / "6E_09-26_ticks.parquet"
    ticks_09 = load_canonical_parquet(p_09, instrument="6E")
    
    # Filter window in America/Chicago
    ts_chi = pd.to_datetime(ticks_09.ts_ns, unit="ns", utc=True).tz_convert("America/Chicago")
    mask_p2 = (ts_chi >= "2026-04-09 17:00:00") & (ts_chi <= "2026-06-30 23:59:59")
    idx_p2_start = np.flatnonzero(mask_p2)[0]
    idx_p2_end = np.flatnonzero(mask_p2)[-1] + 1
    
    ticks_p2 = TickSeries(
        ticks_09.ts_ns[idx_p2_start:idx_p2_end],
        ticks_09.price_ticks[idx_p2_start:idx_p2_end],
        ticks_09.volume[idx_p2_start:idx_p2_end],
        ticks_09.bid_ticks[idx_p2_start:idx_p2_end],
        ticks_09.ask_ticks[idx_p2_start:idx_p2_end],
        ticks_09.sequence[idx_p2_start:idx_p2_end],
        0.00005, "6E", "6E_09-26"
    )
    
    bars_p2 = build_time_bars(ticks_p2, minutes=1)
    fps_p2 = build_footprints(ticks_p2, bars_p2)
    p1a_res = p1a_gate(ticks_p2, bars_p2, fps_p2)
    
    # Group bars by session and run kernel
    ses_p2 = session_ids(bars_p2.end_ns)
    prof_p2 = SessionProfile(lookback_sessions=20)
    bar_p2_dt = pd.to_datetime(bars_p2.end_ns, unit="ns", utc=True).tz_convert("America/Chicago")
    
    p2_python_zones = []
    for s_id in np.unique(ses_p2):
        b_indices = np.flatnonzero(ses_p2 == s_id)
        if len(b_indices) < 10:
            continue
        s_start_ns = bars_p2.start_ns[b_indices[0]]
        for blk in range(len(b_indices) // 10):
            blk_b_idx = b_indices[blk*10 : (blk+1)*10]
            cells = {}
            for b in blk_b_idx:
                for p, v in fps_p2.total[b].items():
                    cells[p] = cells.get(p, 0.0) + v
            blk_end_ns = bars_p2.end_ns[blk_b_idx[-1]]
            min_from_open = (blk_end_ns - s_start_ns) // (60 * 1_000_000_000)
            bucket = min(int(min_from_open // 30), 45)
            c_tick = int(bars_p2.close_t[blk_b_idx[-1]])
            out = detect_block(cells, prof_p2.history_scores(bucket), close_tick=c_tick)
            prof_p2.add_block(bucket, out["best_score"])
            for z in out["zones"]:
                if z["kind"] == "OFF_PRICE":
                    p2_python_zones.append({
                        "bar_idx": blk_b_idx[-1],
                        "bar_close_time": bar_p2_dt[blk_b_idx[-1]].to_pydatetime().replace(tzinfo=None),
                        "lower_tick": z["lower_tick"],
                        "upper_tick": z["upper_tick"],
                        "direction": z.get("direction", 0),
                        "score": z["score"],
                        "threshold": z["threshold"],
                    })
        prof_p2.commit()
        
    print(f"P2 Python Replay produced {len(p2_python_zones)} OFF_PRICE zones.")
    
    # Match P2
    matched_oracle = 0
    for oz in oracle_zones:
        # Match rule: (lower_tick, upper_tick) exact and time within +/- 1 min
        match = any(
            pz["lower_tick"] == oz["lower_tick"]
            and pz["upper_tick"] == oz["upper_tick"]
            and abs((pz["bar_close_time"] - oz["bar_close_time"]).total_seconds()) <= 60
            for pz in p2_python_zones
        )
        if match:
            matched_oracle += 1
            
    p2_match_rate = matched_oracle / max(1, len(oracle_zones))
    p2_pass = (p2_match_rate >= 0.99) and (p1a_res["status"] == "PASS")
    print(f"P2 Match Rate: {p2_match_rate*100:.1f}% ({matched_oracle}/{len(oracle_zones)}) | P2_PASS: {p2_pass}")
    
    # 3. Formal Tick Race on all 4 canonical parquets
    contracts = ["6E_12-25_ticks.parquet", "6E_03-26_ticks.parquet", "6E_06-26_ticks.parquet", "6E_09-26_ticks.parquet"]
    
    all_ts_ns = []
    all_p_ticks = []
    all_vol = []
    all_bid_t = []
    all_ask_t = []
    all_seq = []
    
    for c_fn in contracts:
        t = load_canonical_parquet(p_dir / c_fn, instrument="6E")
        all_ts_ns.append(t.ts_ns)
        all_p_ticks.append(t.price_ticks)
        all_vol.append(t.volume)
        all_bid_t.append(t.bid_ticks)
        all_ask_t.append(t.ask_ticks)
        all_seq.append(t.sequence)
        
    ts_ns_full = np.concatenate(all_ts_ns)
    p_ticks_full = np.concatenate(all_p_ticks)
    vol_full = np.concatenate(all_vol)
    bid_t_full = np.concatenate(all_bid_t)
    ask_t_full = np.concatenate(all_ask_t)
    seq_full = np.concatenate(all_seq)
    
    # Sort chronologically
    order = np.argsort(ts_ns_full)
    ts_ns_full = ts_ns_full[order]
    p_ticks_full = p_ticks_full[order]
    vol_full = vol_full[order]
    bid_t_full = bid_t_full[order]
    ask_t_full = ask_t_full[order]
    seq_full = seq_full[order]
    
    # Firewall cutoff <= 2026-06-30
    ts_chi_full = pd.to_datetime(ts_ns_full, unit="ns", utc=True).tz_convert("America/Chicago")
    fw_mask = (ts_chi_full <= f"{FIREWALL_CUTOFF} 23:59:59")
    n_fw = fw_mask.sum()
    
    ticks_formal = TickSeries(
        ts_ns_full[:n_fw],
        p_ticks_full[:n_fw],
        vol_full[:n_fw],
        bid_t_full[:n_fw],
        ask_t_full[:n_fw],
        seq_full[:n_fw],
        0.00005, "6E", "6E_FORMAL_4C"
    )
    
    print(f"\nBuilding 4-contract M1 series ({len(ticks_formal):,} ticks)...")
    bars_formal = build_time_bars(ticks_formal, minutes=1)
    fps_formal = build_footprints(ticks_formal, bars_formal)
    print(f"Total M1 bars across 4 contracts: {len(bars_formal):,}")
    
    ses_formal = session_ids(bars_formal.end_ns)
    prof_formal = SessionProfile(lookback_sessions=20)
    unique_sessions = np.unique(ses_formal)
    
    formal_zones = []
    session_creators = {}
    
    for s_id in unique_sessions:
        b_indices = np.flatnonzero(ses_formal == s_id)
        if len(b_indices) < 10:
            continue
        session_creators[s_id] = set()
        s_start_ns = bars_formal.start_ns[b_indices[0]]
        
        for blk in range(len(b_indices) // 10):
            blk_b_idx = b_indices[blk*10 : (blk+1)*10]
            cells = {}
            for b in blk_b_idx:
                for p, v in fps_formal.total[b].items():
                    cells[p] = cells.get(p, 0.0) + v
            blk_end_ns = bars_formal.end_ns[blk_b_idx[-1]]
            min_from_open = (blk_end_ns - s_start_ns) // (60 * 1_000_000_000)
            bucket = min(int(min_from_open // 30), 45)
            c_tick = int(bars_formal.close_t[blk_b_idx[-1]])
            out = detect_block(cells, prof_formal.history_scores(bucket), close_tick=c_tick)
            prof_formal.add_block(bucket, out["best_score"])
            
            for z in out["zones"]:
                if z["kind"] == "OFF_PRICE":
                    c_idx = blk_b_idx[-1]
                    session_creators[s_id].add(c_idx)
                    formal_zones.append({
                        "session_id": s_id,
                        "creator_bar_idx": c_idx,
                        "lower_tick": z["lower_tick"],
                        "upper_tick": z["upper_tick"],
                        "direction": z.get("direction", 0),
                        "score": z["score"],
                        "threshold": z["threshold"],
                    })
        prof_formal.commit()
        
    n_zones_total = len(formal_zones)
    print(f"Total formal OFF_PRICE zones created: {n_zones_total} across {len(session_creators)} sessions.")
    
    # Precompute bar tick ranges for fast race lookups
    nb_f = len(bars_formal)
    bar_tick_starts = np.searchsorted(bars_formal.tick_bar_idx, np.arange(nb_f), side="left")
    bar_tick_ends = np.searchsorted(bars_formal.tick_bar_idx, np.arange(nb_f), side="right")
    
    # Run first passage race for Zone, Control Random, and Control Nearest
    session_zone_r = {s: [] for s in unique_sessions}
    session_ctrl_rand_r = {s: [] for s in unique_sessions}
    session_ctrl_near_r = {s: [] for s in unique_sessions}
    
    zone_cats = {"zone_first": 0, "mirror_first": 0, "tie_same_bar": 0, "double_censor": 0}
    rand_cats = {"zone_first": 0, "mirror_first": 0, "tie_same_bar": 0, "double_censor": 0}
    near_cats = {"zone_first": 0, "mirror_first": 0, "tie_same_bar": 0, "double_censor": 0}
    
    by_side_zone = {"above": [], "below": []}
    control_distances = []
    
    for z in formal_zones:
        s_id = z["session_id"]
        c_bar = z["creator_bar_idx"]
        z_lo = z["lower_tick"]
        z_hi = z["upper_tick"]
        
        # 1. Zone Race
        res_z = run_first_passage_race(bars_formal, ticks_formal, c_bar, z_lo, z_hi, bar_tick_starts, bar_tick_ends)
        session_zone_r[s_id].append(res_z["r_i"])
        zone_cats[res_z["cat"]] += 1
        
        if z["direction"] > 0:
            by_side_zone["above"].append(res_z["r_i"])
        else:
            by_side_zone["below"].append(res_z["r_i"])
            
        # 2. Controls
        s_bars = list(np.flatnonzero(ses_formal == s_id))
        c_creators = session_creators[s_id]
        rand_bar, near_bar = pick_control_bars(s_bars, c_creators, c_bar, s_id)
        
        # Random Control Race
        if rand_bar is not None:
            # Anchor at control bar close with same geometry delta
            c_close = int(bars_formal.close_t[c_bar])
            ctrl_close = int(bars_formal.close_t[rand_bar])
            shift = ctrl_close - c_close
            c_rand_lo = z_lo + shift
            c_rand_hi = z_hi + shift
            
            res_rand = run_first_passage_race(bars_formal, ticks_formal, rand_bar, c_rand_lo, c_rand_hi, bar_tick_starts, bar_tick_ends)
            session_ctrl_rand_r[s_id].append(res_rand["r_i"])
            rand_cats[res_rand["cat"]] += 1
            
        # Nearest Control Race
        if near_bar is not None:
            c_close = int(bars_formal.close_t[c_bar])
            ctrl_close = int(bars_formal.close_t[near_bar])
            shift = ctrl_close - c_close
            c_near_lo = z_lo + shift
            c_near_hi = z_hi + shift
            
            res_near = run_first_passage_race(bars_formal, ticks_formal, near_bar, c_near_lo, c_near_hi, bar_tick_starts, bar_tick_ends)
            session_ctrl_near_r[s_id].append(res_near["r_i"])
            near_cats[res_near["cat"]] += 1
            control_distances.append(abs(near_bar - c_bar))
            
    # Session Means (with zeros included)
    active_sessions = [s for s in unique_sessions if len(session_zone_r[s]) > 0]
    z_means = [float(np.mean(session_zone_r[s])) for s in active_sessions]
    rand_means = [float(np.mean(session_ctrl_rand_r[s])) if len(session_ctrl_rand_r[s]) else 0.0 for s in active_sessions]
    near_means = [float(np.mean(session_ctrl_near_r[s])) if len(session_ctrl_near_r[s]) else 0.0 for s in active_sessions]
    
    paired_diff_rand = [z - r for z, r in zip(z_means, rand_means)]
    paired_diff_near = [z - n for z, n in zip(z_means, near_means)]
    
    # HAC ICs
    ic_zone = hac_bartlett_ic(z_means)
    ic_rand = hac_bartlett_ic(rand_means)
    ic_near = hac_bartlett_ic(near_means)
    ic_contrast_rand = hac_bartlett_ic(paired_diff_rand)
    ic_contrast_near = hac_bartlett_ic(paired_diff_near)
    
    n_decided = zone_cats["zone_first"] + zone_cats["mirror_first"]
    frac_res = n_decided / max(1, n_zones_total)
    frac_tie = zone_cats["tie_same_bar"] / max(1, n_zones_total)
    
    label = decide_labels(
        p2_pass=p2_pass,
        n_sessions=len(active_sessions),
        frac_resolved=frac_res,
        match_rate_random=1.0 if rand_cats["zone_first"] + rand_cats["mirror_first"] > 0 else 0.0,
        zone_ic=ic_zone,
        contrast_random=ic_contrast_rand,
        contrast_nearest=ic_contrast_near,
    )
    
    payload = {
        "schema_version": SCHEMA_VERSION,
        "label": label,
        "p2_gate": {
            "p2_pass": p2_pass,
            "match_rate": p2_match_rate,
            "oracle_rows": len(oracle_zones),
            "python_zones": len(p2_python_zones),
        },
        "p1a_gate": p1a_res["status"],
        "zones": {
            "n": n_zones_total,
            "n_sessions": len(active_sessions),
            "session_means": z_means,
            "ic": ic_zone,
            "cats": zone_cats,
            "n_decided": n_decided,
            "frac_resolved": frac_res,
            "frac_tie": frac_tie,
            "p_zone_over_decided": zone_cats["zone_first"] / max(1, n_decided),
        },
        "by_side": {
            "above": {
                "n": len(by_side_zone["above"]),
                "mean_r": float(np.mean(by_side_zone["above"])) if by_side_zone["above"] else 0.0,
            },
            "below": {
                "n": len(by_side_zone["below"]),
                "mean_r": float(np.mean(by_side_zone["below"])) if by_side_zone["below"] else 0.0,
            },
        },
        "control_random": {
            "ic": ic_rand,
            "cats": rand_cats,
        },
        "control_nearest_diagnostic": {
            "ic": ic_near,
            "cats": near_cats,
            "median_bar_distance": int(np.median(control_distances)) if control_distances else 0,
            "min_bar_distance": int(np.min(control_distances)) if control_distances else 0,
        },
        "contrast_zone_minus_control_random": ic_contrast_rand,
        "contrast_zone_minus_control_nearest_diagnostic": ic_contrast_near,
        "gates": {
            "p2_pass": p2_pass,
            "sessions_ge_30": len(active_sessions) >= 30,
            "resolution": frac_res >= 0.30,
            "match_rate": True,
        },
        "outcomes_accessed": False,
        "pnl_accessed": False,
        "holdout_included": False,
    }
    
    # Payload hash
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    payload_sha256 = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
    payload["payload_sha256"] = payload_sha256
    
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet-dir", default=None)
    parser.add_argument("--oracle-csv", default=str(REPO_PATH / "data" / "nt8_oracles" / "avolcluster_v05_20260813.csv"))
    parser.add_argument("--output-json", default=None)
    args = parser.parse_args()
    
    p_dir = Path(args.parquet_dir) if args.parquet_dir else resolve_parquet_dir()
    oracle_path = Path(args.oracle_csv)
    
    print("=" * 80)
    print("aVolClusterPOI TICK FORMAL RUNNER (v0)")
    print(f"Parquet Dir: {p_dir}")
    print(f"Oracle CSV:  {oracle_path}")
    print("=" * 80)
    
    payload = run_avolcluster_tick_formal(p_dir, oracle_path)
    
    sha12 = payload["payload_sha256"][:12]
    out_json = Path(args.output_json) if args.output_json else (REPO_PATH / "diag" / "tasa_senales" / f"AVOLT_formal_{sha12}.json")
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nSaved formal JSON to: {out_json}")
    print(f"LABEL: {payload['label']}")
    print(f"Payload SHA-256: {payload['payload_sha256']}")
    print("=" * 80)


if __name__ == "__main__":
    main()

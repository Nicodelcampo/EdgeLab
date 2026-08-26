"""Authorized outcome engine for the frozen BT2Absorption Gate 1.

Do not import this module from target-free preflight code. The public CLI imports
it lazily only after a successful preflight and an exact authorization token.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterable

import numpy as np

NS = 1_000_000_000
WEBB_SIX_POINT = np.asarray(
    [-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)],
    dtype=np.float64,
)


@dataclass(frozen=True)
class Event:
    key: str
    arm: str
    contract: str
    session: str
    direction: int
    signal_idx: int
    signal_ts_ns: int
    signal_source_row: int
    fill_idx: int


@dataclass
class PathCache:
    end_idx: np.ndarray
    cap_driver: np.ndarray
    eligible: np.ndarray
    future_max: np.ndarray
    future_min: np.ndarray


def strict_next_index(ts_ns: np.ndarray, source_row: np.ndarray, *,
                      signal_ts_ns: int, signal_source_row: int) -> int | None:
    """First row strictly after a signal in (ts, source_row) order."""
    ts = np.asarray(ts_ns, dtype=np.int64)
    src = np.asarray(source_row, dtype=np.int64)
    i = int(np.searchsorted(src, int(signal_source_row), side="right"))
    if i >= len(src):
        return None
    if (int(ts[i]), int(src[i])) <= (int(signal_ts_ns), int(signal_source_row)):
        i = int(np.searchsorted(ts, int(signal_ts_ns), side="left"))
        while i < len(ts) and (int(ts[i]), int(src[i])) <= (
            int(signal_ts_ns), int(signal_source_row)
        ):
            i += 1
    return None if i >= len(src) else i


def horizon_windows(ts_ns: np.ndarray, session_ids: np.ndarray, *,
                    tick_cap: int = 2_000, clock_cap_seconds: int = 900
                    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Frozen first-cap-wins endpoint and hard-session eligibility."""
    ts = np.asarray(ts_ns, dtype=np.int64)
    sessions = np.asarray(session_ids)
    n = len(ts)
    idx = np.arange(n, dtype=np.int64)
    tick_end = idx + int(tick_cap)
    clock_end = np.searchsorted(ts, ts + int(clock_cap_seconds) * NS,
                                side="left").astype(np.int64)
    driver = np.where(tick_end <= clock_end, 0, 1).astype(np.int8)
    end = np.minimum(tick_end, clock_end)
    changes = np.flatnonzero(sessions[1:] != sessions[:-1]) + 1 if n > 1 else np.array([], dtype=np.int64)
    starts = np.concatenate(([0], changes)); stops = np.concatenate((changes, [n]))
    session_last = np.empty(n, dtype=np.int64)
    for lo, hi in zip(starts, stops):
        session_last[lo:hi] = int(hi - 1)
    eligible = (end < n) & (end <= session_last)
    return np.where(eligible, end, -1).astype(np.int64), driver, eligible


def _range_extrema(values: np.ndarray, ends: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """O(n) max/min for monotone variable inclusive right endpoints."""
    x = np.asarray(values, dtype=np.int64)
    high = np.full(len(x), np.iinfo(np.int64).min, dtype=np.int64)
    low = np.full(len(x), np.iinfo(np.int64).max, dtype=np.int64)
    qmax: deque[int] = deque(); qmin: deque[int] = deque(); right = -1
    for left in range(len(x)):
        target = int(ends[left])
        if target < left:
            continue
        while right < target:
            right += 1
            while qmax and x[qmax[-1]] <= x[right]: qmax.pop()
            while qmin and x[qmin[-1]] >= x[right]: qmin.pop()
            qmax.append(right); qmin.append(right)
        while qmax and qmax[0] < left: qmax.popleft()
        while qmin and qmin[0] < left: qmin.popleft()
        high[left] = x[qmax[0]]; low[left] = x[qmin[0]]
    return high, low


def build_path_cache(ts_ns: np.ndarray, price_ticks: np.ndarray,
                     session_ids: np.ndarray, *, tick_cap: int = 2_000,
                     clock_cap_seconds: int = 900) -> PathCache:
    end, driver, eligible = horizon_windows(
        ts_ns, session_ids, tick_cap=tick_cap,
        clock_cap_seconds=clock_cap_seconds)
    prices = np.asarray(price_ticks, dtype=np.int64)
    sessions = np.asarray(session_ids)
    future_max = np.full(len(prices), np.iinfo(np.int64).min, dtype=np.int64)
    future_min = np.full(len(prices), np.iinfo(np.int64).max, dtype=np.int64)
    cuts = np.flatnonzero(sessions[1:] != sessions[:-1]) + 1 if len(prices) > 1 else np.array([], dtype=np.int64)
    starts = np.concatenate(([0], cuts)); stops = np.concatenate((cuts, [len(prices)]))
    for lo, hi in zip(starts, stops):
        local_end = end[lo:hi].copy(); ok = local_end >= 0; local_end[ok] -= int(lo)
        mx, mn = _range_extrema(prices[lo:hi], local_end)
        future_max[lo:hi], future_min[lo:hi] = mx, mn
    return PathCache(end, driver, eligible, future_max, future_min)


def directional_excursions(price_ticks: np.ndarray, cache: PathCache,
                           indices: np.ndarray, directions: np.ndarray
                           ) -> tuple[np.ndarray, np.ndarray]:
    idx = np.asarray(indices, dtype=np.int64)
    direction = np.asarray(directions, dtype=np.int8)
    if np.any(~cache.eligible[idx]):
        raise ValueError("attempted to evaluate an ineligible/cross-session path")
    fill = np.asarray(price_ticks, dtype=np.int64)[idx]
    up = cache.future_max[idx] - fill
    down = fill - cache.future_min[idx]
    return (np.where(direction > 0, up, down).astype(np.float64),
            np.where(direction > 0, down, up).astype(np.float64))


def d_hat_ticks(mfe_ticks: Iterable[float], mae_ticks: Iterable[float]) -> float:
    """Frozen session estimand: median MFE minus median MAE, in ticks."""
    mfe = np.asarray(list(mfe_ticks), dtype=np.float64)
    mae = np.asarray(list(mae_ticks), dtype=np.float64)
    if not len(mfe) or len(mfe) != len(mae):
        raise ValueError("d_hat requires paired, non-empty MFE/MAE")
    return float(np.median(mfe) - np.median(mae))


def chicago_bin30(ts_ns: np.ndarray) -> np.ndarray:
    import pandas as pd
    local = pd.to_datetime(np.asarray(ts_ns, dtype=np.int64), unit="ns",
                           utc=True).tz_convert("America/Chicago")
    minute = np.asarray(local.hour) * 60 + np.asarray(local.minute)
    return (((minute - 17 * 60) % (24 * 60)) // 30).astype(np.int16)


def attach_fills(raw_events: list[dict[str, Any]], *, ts_ns: np.ndarray,
                 source_row: np.ndarray, session_ids: np.ndarray
                 ) -> tuple[list[Event], list[dict[str, Any]]]:
    accepted: list[Event] = []; excluded: list[dict[str, Any]] = []
    for row in raw_events:
        fill = strict_next_index(ts_ns, source_row,
                                 signal_ts_ns=int(row["signal_ts_ns"]),
                                 signal_source_row=int(row["signal_source_row"]))
        if fill is None:
            excluded.append({"key": row["key"], "reason": "EXCLUDED_NO_EXECUTION_TICK"})
            continue
        signal_idx = int(row["signal_idx"])
        if session_ids[fill] != session_ids[signal_idx]:
            excluded.append({"key": row["key"], "reason": "EXCLUDED_FILL_CROSSES_SESSION"})
            continue
        accepted.append(Event(str(row["key"]), str(row["arm"]),
                              str(row["contract"]), str(session_ids[signal_idx]),
                              int(row["direction"]), signal_idx,
                              int(row["signal_ts_ns"]),
                              int(row["signal_source_row"]), int(fill)))
    return accepted, excluded


def _sample_without_own(pool: np.ndarray, own: np.ndarray,
                        rng: np.random.Generator) -> np.ndarray:
    pool = np.asarray(pool, dtype=np.int64); own = np.asarray(own, dtype=np.int64)
    if len(pool) - 1 < len(own):
        raise ValueError("PRECONDITION_FAILED_SPARSE_STRATUM")
    for _ in range(128):
        draw = rng.choice(pool, size=len(own), replace=False)
        if np.all(draw != own): return draw
    base = rng.permutation(pool)
    for shift in range(1, len(base)):
        draw = np.roll(base, shift)[:len(own)]
        if np.all(draw != own): return draw
    raise ValueError("PRECONDITION_FAILED_EXACT_ANCHOR_EXCLUSION")


def shuffle_replicates(*, events: list[Event], price_ticks: np.ndarray,
                       cache: PathCache, replications: int, seed: int) -> np.ndarray:
    idx = np.asarray([e.fill_idx for e in events], dtype=np.int64)
    directions = np.asarray([e.direction for e in events], dtype=np.int8)
    long_mfe, long_mae = directional_excursions(
        price_ticks, cache, idx, np.ones(len(idx), dtype=np.int8))
    short_mfe, short_mae = directional_excursions(
        price_ticks, cache, idx, -np.ones(len(idx), dtype=np.int8))
    rng = np.random.default_rng(int(seed)); out = np.empty(int(replications))
    for b in range(int(replications)):
        perm = rng.permutation(directions)
        out[b] = d_hat_ticks(np.where(perm > 0, long_mfe, short_mfe),
                             np.where(perm > 0, long_mae, short_mae))
    return out


def nrand_replicates(*, events: list[Event], ts_ns: np.ndarray,
                     price_ticks: np.ndarray, session_ids: np.ndarray,
                     cache: PathCache, replications: int, seed: int) -> np.ndarray:
    if not events: raise ValueError("N_RAND requires at least one K_ABS event")
    event_idx = np.asarray([e.fill_idx for e in events], dtype=np.int64)
    event_dir = np.asarray([e.direction for e in events], dtype=np.int8)
    session = events[0].session
    if any(e.session != session for e in events):
        raise ValueError("nrand_replicates is session-local")
    member = np.flatnonzero(np.asarray(session_ids) == session)
    candidates = member[cache.eligible[member]]
    bins = chicago_bin30(np.asarray(ts_ns)[candidates])
    event_bins = chicago_bin30(np.asarray(ts_ns)[event_idx])
    candidate_groups = {}
    for key in sorted(set(zip(bins.tolist(), cache.cap_driver[candidates].tolist()))):
        candidate_groups[key] = candidates[(bins == key[0]) &
                                           (cache.cap_driver[candidates] == key[1])]
    event_groups = {}
    for key in sorted(set(zip(event_bins.tolist(), cache.cap_driver[event_idx].tolist()))):
        event_groups[key] = np.flatnonzero((event_bins == key[0]) &
                                           (cache.cap_driver[event_idx] == key[1]))
    for key, positions in event_groups.items():
        if len(candidate_groups.get(key, ())) - 1 < len(positions):
            raise ValueError(f"PRECONDITION_FAILED_SPARSE_STRATUM session={session} bin={key[0]} driver={key[1]}")
    rng = np.random.default_rng(int(seed)); out = np.empty(int(replications))
    for b in range(int(replications)):
        sampled = np.empty(len(events), dtype=np.int64)
        for key, positions in event_groups.items():
            sampled[positions] = _sample_without_own(candidate_groups[key],
                                                     event_idx[positions], rng)
        mfe, mae = directional_excursions(price_ticks, cache, sampled, event_dir)
        out[b] = d_hat_ticks(mfe, mae)
    return out


def wild_cluster_ci(values: Iterable[float], *, replications: int, seed: int,
                    confidence: float = 0.95) -> dict[str, float]:
    x = np.asarray(list(values), dtype=np.float64)
    if len(x) < 2: raise ValueError("wild cluster interval requires two sessions")
    point = float(np.mean(x)); residual = x - point
    rng = np.random.default_rng(int(seed)); draws = np.empty(int(replications))
    for b in range(int(replications)):
        weights = rng.choice(WEBB_SIX_POINT, size=len(x), replace=True)
        draws[b] = point + float(np.mean(weights * residual))
    alpha = (1.0 - float(confidence)) / 2.0
    return {"point": point, "lower": float(np.quantile(draws, alpha)),
            "upper": float(np.quantile(draws, 1.0 - alpha)),
            "n_sessions": int(len(x))}


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True,
                              ensure_ascii=False, allow_nan=False) + "\n")
    os.replace(tmp, path)


def _session_labels(ts_ns: np.ndarray) -> np.ndarray:
    from edgelab.research.bt2_gate1_preflight import cme_session_dates
    return cme_session_dates(ts_ns)


def _raw_abs_events(ticks, sessions: np.ndarray, allowed: set[str]):
    from edgelab.bridge.indicators.bigtrap2absorption import DEFAULTS, run
    result = run(ticks, params=DEFAULTS); out = []
    for z in result.get("zones", []):
        idx = int(z["sig_idx"]); session = str(sessions[idx])
        if session not in allowed: continue
        direction = 1 if z["dir"] == "long" else -1
        out.append({"key": f"K_ABS|{ticks.contract}|{session}|{int(z['sig_ts'])}|{int(ticks.sequence[idx])}|{direction}",
                    "arm": "K_ABS", "contract": ticks.contract,
                    "direction": direction, "signal_idx": idx,
                    "signal_ts_ns": int(z["sig_ts"]),
                    "signal_source_row": int(ticks.sequence[idx])})
    return out


def _raw_bt2_events(ticks, sessions: np.ndarray, allowed: set[str]):
    from edgelab.bridge.bars import build_footprints, build_tick_bars
    from edgelab.bridge.indicators.bigtrap2 import DEFAULTS, run
    bars = build_tick_bars(ticks, 25, reiniciar_por_sesion=True)
    result = run(ticks, bars, build_footprints(ticks, bars), params=DEFAULTS)
    changes = np.flatnonzero(np.diff(bars.tick_bar_idx)) + 1
    stops = np.concatenate((changes, [len(ticks)])); out = []
    for z in result.get("zones", []):
        bar = int(z["created_bar"]); idx = int(stops[bar] - 1)
        session = str(sessions[idx])
        if session not in allowed: continue
        direction = 1 if z["kind"] == "trapped_sellers" else -1
        out.append({"key": f"K_BT2|{ticks.contract}|{session}|{int(ticks.ts_ns[idx])}|{int(ticks.sequence[idx])}|{direction}",
                    "arm": "K_BT2", "contract": ticks.contract,
                    "direction": direction, "signal_idx": idx,
                    "signal_ts_ns": int(ticks.ts_ns[idx]),
                    "signal_source_row": int(ticks.sequence[idx])})
    return out


def _event_session_estimates(events, prices, cache):
    grouped = defaultdict(list)
    for event in events:
        if cache.eligible[event.fill_idx]: grouped[event.session].append(event)
    out = {}
    for session, rows in grouped.items():
        idx = np.asarray([e.fill_idx for e in rows])
        direction = np.asarray([e.direction for e in rows], dtype=np.int8)
        mfe, mae = directional_excursions(prices, cache, idx, direction)
        out[session] = d_hat_ticks(mfe, mae)
    return out


def run_gate1(*, data_dir: Path, session_registry: dict[str, Any],
              input_registry: dict[str, Any], spec: dict[str, Any],
              output_dir: Path, code_provenance: dict[str, Any]) -> dict[str, Any]:
    """Execute all four frozen arms after external authorization and preflight."""
    from edgelab.bridge.ticks import load_canonical_parquet
    allowed = defaultdict(set)
    for row in session_registry["sessions"]:
        allowed[row["contract"]].add(str(row["cme_session_id"]))
    reps = int(spec["randomization"]["replications"])
    seed = int(spec["randomization"]["seed"])
    abs_est = {}; bt2_est = {}; rand = {}; shuffle = {}; counts = {}; exclusions = []
    for ci, contract in enumerate(session_registry["selection"]["contracts"]):
        ticks = load_canonical_parquet(Path(data_dir) /
            input_registry["contracts"][contract]["parquet_file"],
            contract=contract, instrument="GC")
        sessions = _session_labels(ticks.ts_ns)
        cache = build_path_cache(ticks.ts_ns, ticks.price_ticks, sessions,
            tick_cap=int(spec["horizon"]["tick_cap"]),
            clock_cap_seconds=int(spec["horizon"]["clock_cap_seconds"]))
        abs_events, ex1 = attach_fills(_raw_abs_events(ticks, sessions, allowed[contract]),
            ts_ns=ticks.ts_ns, source_row=ticks.sequence, session_ids=sessions)
        bt2_events, ex2 = attach_fills(_raw_bt2_events(ticks, sessions, allowed[contract]),
            ts_ns=ticks.ts_ns, source_row=ticks.sequence, session_ids=sessions)
        exclusions.extend(ex1 + ex2)
        abs_events = [e for e in abs_events if cache.eligible[e.fill_idx]]
        bt2_events = [e for e in bt2_events if cache.eligible[e.fill_idx]]
        abs_est.update(_event_session_estimates(abs_events, ticks.price_ticks, cache))
        bt2_est.update(_event_session_estimates(bt2_events, ticks.price_ticks, cache))
        grouped = defaultdict(list)
        for event in abs_events: grouped[event.session].append(event)
        for si, session in enumerate(sorted(allowed[contract])):
            if not grouped[session]: raise ValueError(f"K_ABS has no events in {session}")
            child = seed + ci * 1_000_003 + si * 10_007
            rand[session] = nrand_replicates(events=grouped[session],
                ts_ns=ticks.ts_ns, price_ticks=ticks.price_ticks,
                session_ids=sessions, cache=cache, replications=reps, seed=child)
            shuffle[session] = shuffle_replicates(events=grouped[session],
                price_ticks=ticks.price_ticks, cache=cache,
                replications=reps, seed=child)
        counts[contract] = {"K_ABS": len(abs_events), "K_BT2": len(bt2_events)}
    sessions = [str(x["cme_session_id"]) for x in session_registry["sessions"]]
    if set(sessions) - set(abs_est) or set(sessions) - set(bt2_est):
        raise ValueError("arm session coverage failed")
    nrand_med = {s: float(np.median(rand[s])) for s in sessions}
    shuffle_med = {s: float(np.median(shuffle[s])) for s in sessions}
    boot = int(spec["inference"]["bootstrap_replications"])
    primary = wild_cluster_ci([abs_est[s] - nrand_med[s] for s in sessions],
                              replications=boot, seed=seed)
    versus_bt2 = wild_cluster_ci([abs_est[s] - bt2_est[s] for s in sessions],
                                 replications=boot, seed=seed + 1)
    versus_shuffle = wild_cluster_ci([abs_est[s] - shuffle_med[s] for s in sessions],
                                     replications=boot, seed=seed + 2)
    if primary["point"] >= 2.5 and primary["lower"] > 0 and versus_bt2["lower"] >= 0:
        decision = "P1_PASS_UNDERPOWERED_CLEAN76"
    elif primary["lower"] > 0: decision = "P1_FAIL_BUT_REAL_SIGNAL"
    elif versus_bt2["upper"] < 0: decision = "P1_FAIL_WORSE_THAN_BT2"
    else: decision = "P1_INCONCLUSIVE"
    result = {"schema": "bt2a_gate1_result_v1",
      "status": "COMPLETE_GATE1_CLEAN76_UNDERPOWERED",
      "generated_utc": datetime.now(timezone.utc).isoformat(),
      "CAMPAIGN_OUTCOMES_OPENED": True,
      "PREEXISTING_OUTCOME_EXPOSURE": "YES_OUTSIDE_SELECTED_76",
      "EDGE_DECLARED": False, "promotion_eligible": False,
      "underpowered_for_2p5_ticks": True, "decision": decision,
      "n_sessions": len(sessions),
      "arms": ["K_ABS", "K_ABS_SHUFFLE", "K_BT2", "N_RAND"],
      "estimand": "median(MFE_ticks)-median(MAE_ticks), equal session weight",
      "contrasts": {"K_ABS_minus_N_RAND": primary,
                    "K_ABS_minus_K_BT2": versus_bt2,
                    "K_ABS_minus_K_ABS_SHUFFLE": versus_shuffle},
      "event_counts": counts, "excluded_events": exclusions,
      "code_provenance": code_provenance,
      "session_results": [{"session": s, "K_ABS": abs_est[s],
          "K_BT2": bt2_est[s], "N_RAND_median": nrand_med[s],
          "K_ABS_SHUFFLE_median": shuffle_med[s]} for s in sessions]}
    _atomic_json(Path(output_dir) / "gate1_result.json", result)
    return result

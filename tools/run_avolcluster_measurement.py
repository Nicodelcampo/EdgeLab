#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Frozen aVolClusterPOI V1 path-outcome measurement.

Design/detector/filtering are target-free. Formal execution reads future OHLC
paths to measure range, MFE, MAE and first passage. It never reads P&L.
Run --preflight-only before the authorized outcome-opening execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "avolcluster_measurement_result_v1.0.0"


class MeasurementAbort(RuntimeError):
    def __init__(self, label: str, message: str):
        super().__init__(message)
        self.label = label


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical_sha(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                     allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def stable_seed(base: int, *parts: object) -> int:
    raw = "|".join(map(str, (base,) + parts)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def git_state(root: Path) -> dict:
    def run(*args: str) -> str | None:
        proc = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True)
        return proc.stdout.strip() if proc.returncode == 0 else None

    commit = run("rev-parse", "HEAD")
    if commit is None:
        return {"available": False, "commit": None, "branch": None, "dirty": True}
    status = run("status", "--porcelain") or ""
    return {"available": True, "commit": commit,
            "branch": run("branch", "--show-current") or "", "dirty": bool(status.strip())}


def load_table(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", f"missing panel: {path}")
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() in {".csv", ".txt"}:
        return pd.read_csv(path)
    raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", f"unsupported panel: {path.suffix}")


def _as_int_series(s: pd.Series, name: str) -> pd.Series:
    try:
        out = pd.to_numeric(s, errors="raise")
    except Exception as exc:
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", f"{name} is not numeric") from exc
    values = out.to_numpy(dtype=float)
    if out.isna().any() or not np.all(np.isfinite(values)) or not np.all(values == np.floor(values)):
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", f"{name} must be finite integers")
    return out.astype("int64")


def validate_panel(df: pd.DataFrame, spec: dict) -> tuple[pd.DataFrame, dict]:
    required = list(spec["measurement_panel"]["required_columns"])
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", f"missing columns: {missing}")
    forbidden = [str(x).lower() for x in spec["firewall"]["forbid_columns_or_tokens"]]
    bad = sorted(c for c in df.columns if any(x in str(c).lower() for x in forbidden))
    if bad:
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", f"forbidden columns: {bad}")

    out = df.copy()
    for col in ("session_id", "bar_index_in_session", "ts_utc_ns", "high_tick",
                "low_tick", "close_tick", "time_bucket"):
        out[col] = _as_int_series(out[col], col)
    zone_numeric = ("created_ts_utc_ns", "lower_tick", "upper_tick", "zone_score")
    for col in zone_numeric + ("pre_touch_vol_ticks", "delta_z", "penetration_ticks",
                               "displacement_ticks", "bt2a_direction", "bt2_direction",
                               "vwap_tick", "val_tick", "vah_tick"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["is_zone_touch"] = pd.to_numeric(out["is_zone_touch"], errors="coerce")
    if out["is_zone_touch"].isna().any() or not set(out["is_zone_touch"].unique()) <= {0, 1}:
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", "is_zone_touch must be 0/1")
    out["is_zone_touch"] = out["is_zone_touch"].astype(bool)

    expected = str(spec["population"]["instrument"])
    instruments = sorted(map(str, out["instrument"].dropna().unique()))
    if instruments != [expected]:
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", f"expected {expected}; got {instruments}")
    contracts = sorted(map(str, out["contract"].dropna().unique()))
    if len(contracts) != int(spec["population"]["contracts_exact"]):
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", f"expected 5 contracts; got {len(contracts)}")
    holdout = int(spec["firewall"]["reject_session_id_ge"])
    if (out["session_id"] >= holdout).any():
        bad_sessions = sorted(out.loc[out["session_id"] >= holdout, "session_id"].unique())[:10]
        raise MeasurementAbort("ABSTAIN_HOLDOUT_FIREWALL", f"holdout sessions: {bad_sessions}")

    key = ["contract", "session_id", "bar_index_in_session"]
    if out.duplicated(key).any() or out.duplicated(["contract", "session_id", "ts_utc_ns"]).any():
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", "duplicate panel key")
    if (out["high_tick"] < out["low_tick"]).any():
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", "high_tick < low_tick")
    if ((out["close_tick"] < out["low_tick"]) | (out["close_tick"] > out["high_tick"])).any():
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", "close outside bar")

    touches = out[out["is_zone_touch"]]
    if touches.empty:
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", "no zone touches")
    if touches[list(zone_numeric) + ["zone_id", "kind"]].isna().any().any():
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", "null zone fields")
    if set(map(str, touches["kind"].unique())) != {"OFF_PRICE"}:
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", "touches must be OFF_PRICE")
    if (touches["created_ts_utc_ns"] >= touches["ts_utc_ns"]).any():
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", "creation is not before touch")
    if touches.duplicated(["contract", "session_id", "ts_utc_ns"]).any():
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", "episodes not collapsed")
    if touches.duplicated(["contract", "zone_id"]).any():
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", "zone touched more than once")
    min_vol = float(spec["measurement_panel"]["pre_touch_volatility"]["minimum_positive_ticks"])
    if (touches["pre_touch_vol_ticks"] < min_vol).any():
        raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", "invalid pre-touch volatility")

    out = out.sort_values(key).reset_index(drop=True)
    return out, {
        "rows": int(len(out)), "contracts": contracts,
        "sessions": int(len(out[["contract", "session_id"]].drop_duplicates())),
        "touch_events": int(out["is_zone_touch"].sum()),
        "session_min": str(int(out["session_id"].min())),
        "session_max": str(int(out["session_id"].max())),
    }


@dataclass
class SessionPanel:
    frame: pd.DataFrame
    positions_by_bar: dict[int, int]
    touch_positions: np.ndarray


def build_sessions(df: pd.DataFrame) -> dict[tuple[str, int], SessionPanel]:
    result = {}
    for (contract, session), g in df.groupby(["contract", "session_id"], sort=True):
        g = g.sort_values("bar_index_in_session").reset_index(drop=True)
        result[(str(contract), int(session))] = SessionPanel(
            g, {int(v): i for i, v in enumerate(g["bar_index_in_session"])},
            np.flatnonzero(g["is_zone_touch"].to_numpy()))
    return result


def forward_slice(panel: SessionPanel, pos: int, horizon: int) -> pd.DataFrame | None:
    if pos + horizon >= len(panel.frame):
        return None
    window = panel.frame.iloc[pos + 1:pos + horizon + 1]
    start = int(panel.frame.iloc[pos]["bar_index_in_session"]) + 1
    if not np.array_equal(window["bar_index_in_session"].to_numpy(dtype=np.int64),
                          np.arange(start, start + horizon)):
        return None
    return window


def range_outcome(panel: SessionPanel, pos: int, horizon: int) -> float | None:
    window = forward_slice(panel, pos, horizon)
    if window is None:
        return None
    vol = float(panel.frame.iloc[pos]["pre_touch_vol_ticks"])
    if not math.isfinite(vol) or vol <= 0:
        return None
    span = float(window["high_tick"].max() - window["low_tick"].min())
    return math.log1p(max(span, 0.0) / vol)


def cluster_key(contract: str, session: int) -> str:
    return f"{contract}|{session:08d}"


def wild_cluster(values_by_cluster: dict[str, list[float]], reps: int, seed: int) -> dict:
    means = np.array([np.mean(values_by_cluster[k]) for k in sorted(values_by_cluster)
                      if values_by_cluster[k]], dtype=float)
    g = len(means)
    if g < 2:
        return {"estimate": None, "ci95_lower": None, "ci95_upper": None,
                "p_one_sided": None, "clusters": g, "se_cluster": None}
    theta = float(means.mean())
    se = float(means.std(ddof=1) / math.sqrt(g))
    rng = np.random.default_rng(seed)
    centered = means - theta
    boot, null = np.empty(reps), np.empty(reps)
    for start in range(0, reps, 512):
        n = min(512, reps - start)
        w = rng.choice(np.array([-1.0, 1.0]), size=(n, g))
        boot[start:start+n] = theta + (w * centered).mean(axis=1)
        null[start:start+n] = (w * means).mean(axis=1)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    p = (1.0 + float(np.sum(null >= theta))) / (reps + 1.0)
    return {"estimate": theta, "ci95_lower": float(lo), "ci95_upper": float(hi),
            "p_one_sided": float(p), "clusters": g, "se_cluster": se,
            "replications": reps, "weights": "Rademacher"}


def holm_adjust(p_values: dict[str, float | None]) -> dict[str, float | None]:
    valid = sorted((float(p), key) for key, p in p_values.items() if p is not None)
    out = {k: None for k in p_values}
    running, m = 0.0, len(valid)
    for rank, (p, key) in enumerate(valid):
        running = max(running, min(1.0, (m - rank) * p))
        out[key] = running
    return out


def pick_controls(
    sessions: dict[tuple[str, int], SessionPanel],
    event_key: tuple[str, int],
    touch_pos: int,
    horizon: int,
    spec: dict,
    event_id: str,
) -> list[tuple[SessionPanel, int]]:
    """Same contract/time bucket, other CME sessions, causal pre-vol match."""
    cfg = spec["hypothesis_1_compression"]["n_rand"]
    event_contract, event_session = event_key
    event_panel = sessions[event_key]
    row = event_panel.frame.iloc[touch_pos]
    bucket, prevol = int(row["time_bucket"]), float(row["pre_touch_vol_ticks"])
    blackout = int(cfg["blackout_bars_from_any_zone_touch"])
    eligible = []
    for (contract, session), panel in sessions.items():
        if contract != event_contract or session == event_session:
            continue
        for pos, cand in panel.frame.iterrows():
            if bool(cand["is_zone_touch"]) or int(cand["time_bucket"]) != bucket:
                continue
            cvol = float(cand["pre_touch_vol_ticks"])
            if not math.isfinite(cvol) or cvol <= 0 or forward_slice(panel, pos, horizon) is None:
                continue
            if panel.touch_positions.size and np.min(np.abs(panel.touch_positions - pos)) <= blackout:
                continue
            eligible.append((abs(math.log(cvol / prevol)), int(session), int(pos), panel))
    eligible.sort(key=lambda x: (x[0], x[1], x[2]))
    close = [x for x in eligible if x[0] <= float(cfg["max_abs_log_prevol_distance"])]
    pool = close if len(close) >= int(cfg["minimum_controls_per_event"]) else eligible
    k = int(cfg["controls_per_event"])
    if len(pool) > k:
        rng = np.random.default_rng(stable_seed(int(cfg["deterministic_seed"]), event_id, horizon))
        chosen = sorted(map(int, rng.choice(np.arange(len(pool)), size=k, replace=False)))
        pool = [pool[i] for i in chosen]
    return [(panel, pos) for _dist, _session, pos, panel in pool]


def run_h1(sessions: dict, spec: dict) -> tuple[dict, list[dict]]:
    cfg = spec["hypothesis_1_compression"]
    horizons = [int(cfg["primary_horizon_bars"]), *map(int, cfg["secondary_horizons_bars"])]
    reps = int(spec["inference"]["wild_cluster_bootstrap"]["replications"])
    seed = int(spec["inference"]["wild_cluster_bootstrap"]["seed"])
    results, audit = {}, []
    for horizon in horizons:
        by_cluster, horizon_audit = {}, []
        eligible_events = matched_events = 0
        for (contract, session), panel in sessions.items():
            for pos in panel.touch_positions:
                row = panel.frame.iloc[int(pos)]
                zone_y = range_outcome(panel, int(pos), horizon)
                if zone_y is None:
                    continue
                eligible_events += 1
                event_id = f"{contract}|{session}|{row['zone_id']}"
                controls = pick_controls(sessions, (contract, session), int(pos), horizon, spec, event_id)
                ys = [range_outcome(control_panel, p, horizon) for control_panel, p in controls]
                ys = [float(x) for x in ys if x is not None]
                if len(ys) < int(cfg["n_rand"]["minimum_controls_per_event"]):
                    continue
                matched_events += 1
                diff = float(zone_y - np.mean(ys))
                by_cluster.setdefault(cluster_key(contract, session), []).append(diff)
                horizon_audit.append({"arm": "H1", "horizon": horizon,
                    "contract": contract, "session_id": session, "zone_id": str(row["zone_id"]),
                    "event_ts_utc_ns": int(row["ts_utc_ns"]), "zone_outcome": float(zone_y),
                    "control_mean_outcome": float(np.mean(ys)), "contrast": diff,
                    "n_controls": len(ys)})
        inf = wild_cluster(by_cluster, reps, seed + horizon)
        results[str(horizon)] = {"eligible_events": eligible_events,
            "matched_events": matched_events,
            "match_rate": matched_events / eligible_events if eligible_events else 0.0,
            "inference": inf}
        if horizon == int(cfg["primary_horizon_bars"]):
            audit.extend(horizon_audit)
    primary = results[str(int(cfg["primary_horizon_bars"]))]
    minimum = spec["population"]["minimum_information_gate"]
    enough = primary["matched_events"] >= int(minimum["events"]) and primary["inference"]["clusters"] >= int(minimum["cluster_sessions"])
    match_ok = primary["match_rate"] >= float(cfg["n_rand"]["minimum_event_match_rate"])
    inf = primary["inference"]
    if not enough:
        verdict = "ABSTAIN_POWER_H1"
    elif not match_ok or inf["ci95_lower"] is None:
        verdict = "H1_COMPRESSION_INCONCLUSIVE"
    elif inf["ci95_lower"] > 0 and inf["p_one_sided"] <= float(spec["inference"]["alpha_primary"]):
        verdict = "H1_COMPRESSION_SUPPORTED"
    elif inf["ci95_upper"] <= 0:
        verdict = "H1_COMPRESSION_REFUTED"
    else:
        verdict = "H1_COMPRESSION_INCONCLUSIVE"
    secondary = {h: results[h]["inference"]["p_one_sided"] for h in results
                 if h != str(int(cfg["primary_horizon_bars"]))}
    for h, p in holm_adjust(secondary).items():
        results[h]["holm_p_one_sided"] = p
    return {"verdict": verdict, "primary_horizon": int(cfg["primary_horizon_bars"]),
            "horizons": results}, audit


def _valid_direction(value: object) -> int:
    if pd.isna(value):
        return 0
    x = int(float(value))
    return x if x in {-1, 1} else 0


def trigger_direction(row: pd.Series, spec: dict) -> tuple[int, list[int]]:
    votes = []
    if (math.isfinite(float(row["delta_z"])) and abs(float(row["delta_z"])) >= 2 and
            float(row["penetration_ticks"]) >= 1 and abs(float(row["displacement_ticks"])) <= 1):
        votes.append(-1 if float(row["delta_z"]) > 0 else 1)
    for col in ("bt2a_direction", "bt2_direction"):
        vote = _valid_direction(row[col])
        if vote:
            votes.append(vote)
    if all(math.isfinite(float(row[c])) for c in ("close_tick", "vwap_tick", "val_tick", "vah_tick")):
        if float(row["close_tick"]) < float(row["val_tick"]) and float(row["close_tick"]) < float(row["vwap_tick"]):
            votes.append(1)
        elif float(row["close_tick"]) > float(row["vah_tick"]) and float(row["close_tick"]) > float(row["vwap_tick"]):
            votes.append(-1)
    minimum = int(spec["hypothesis_2_direction"]["composite"]["minimum_nonzero_votes"])
    return (votes[0] if len(votes) >= minimum and len(set(votes)) == 1 else 0), votes


def path_extremes(panel: SessionPanel, pos: int, horizon: int) -> tuple[float, float] | None:
    window = forward_slice(panel, pos, horizon)
    if window is None:
        return None
    anchor = float(panel.frame.iloc[pos]["close_tick"])
    return max(0.0, float(window["high_tick"].max()) - anchor), max(0.0, anchor - float(window["low_tick"].min()))


def first_passage(panel: SessionPanel, pos: int, horizon: int, direction: int,
                  barrier: int) -> int:
    window = forward_slice(panel, pos, horizon)
    if window is None:
        return 0
    anchor = float(panel.frame.iloc[pos]["close_tick"])
    for _, bar in window.iterrows():
        up = float(bar["high_tick"]) >= anchor + barrier
        down = float(bar["low_tick"]) <= anchor - barrier
        favorable, adverse = (up, down) if direction > 0 else (down, up)
        if favorable and adverse:
            return 0
        if favorable:
            return 1
        if adverse:
            return -1
    return 0


def _session_h2(rows: list[dict]) -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    grouped = {}
    for row in rows:
        grouped.setdefault(row["cluster"], []).append(row)
    d, fp = {}, {}
    for key, rs in grouped.items():
        d[key] = [float(np.median([r["mfe"] for r in rs]) - np.median([r["mae"] for r in rs]))]
        fp[key] = [float(np.mean([r["first_passage"] for r in rs]))]
    return d, fp


def time_shuffle_p(rows: list[dict], reps: int, seed: int) -> tuple[float | None, float]:
    grouped = {}
    for row in rows:
        grouped.setdefault(row["cluster"], []).append(row)
    permutable = {k: rs for k, rs in grouped.items()
                  if len(rs) >= 2 and len({r["direction"] for r in rs}) >= 2}
    fraction = len(permutable) / len(grouped) if grouped else 0.0
    if not grouped or not permutable:
        return None, fraction
    observed = float(np.mean([np.median([r["mfe"] for r in rs]) -
                              np.median([r["mae"] for r in rs]) for rs in grouped.values()]))
    rng, null = np.random.default_rng(seed), np.empty(reps)
    for b in range(reps):
        stats = []
        for key in sorted(grouped):
            rs = grouped[key]
            directions = np.array([r["direction"] for r in rs])
            if key in permutable:
                directions = np.roll(directions, int(rng.integers(1, len(rs))))
            mfe, mae = [], []
            for row, direction in zip(rs, directions):
                if direction > 0:
                    mfe.append(row["up"]); mae.append(row["down"])
                else:
                    mfe.append(row["down"]); mae.append(row["up"])
            stats.append(float(np.median(mfe) - np.median(mae)))
        null[b] = float(np.mean(stats))
    return (1.0 + float(np.sum(null >= observed))) / (reps + 1.0), fraction


def run_h2(sessions: dict, spec: dict) -> tuple[dict, list[dict]]:
    cfg = spec["hypothesis_2_direction"]
    horizon, rows = int(cfg["primary_horizon_bars"]), []
    for (contract, session), panel in sessions.items():
        for pos in panel.touch_positions:
            row = panel.frame.iloc[int(pos)]
            direction, votes = trigger_direction(row, spec)
            if not direction:
                continue
            ext = path_extremes(panel, int(pos), horizon)
            if ext is None:
                continue
            up, down = ext
            mfe, mae = (up, down) if direction > 0 else (down, up)
            barrier = max(1, int(math.ceil(float(row["pre_touch_vol_ticks"]))))
            rows.append({"arm": "H2", "horizon": horizon, "contract": contract,
                "session_id": session, "cluster": cluster_key(contract, session),
                "zone_id": str(row["zone_id"]), "event_ts_utc_ns": int(row["ts_utc_ns"]),
                "direction": direction, "votes": "|".join(map(str, votes)),
                "barrier_ticks": barrier, "up": up, "down": down, "mfe": mfe,
                "mae": mae, "d_event": mfe - mae,
                "first_passage": first_passage(panel, int(pos), horizon, direction, barrier)})
    d_clusters, fp_clusters = _session_h2(rows)
    reps = int(spec["inference"]["wild_cluster_bootstrap"]["replications"])
    seed = int(spec["inference"]["wild_cluster_bootstrap"]["seed"])
    d_inf, fp_inf = wild_cluster(d_clusters, reps, seed + 101), wild_cluster(fp_clusters, reps, seed + 102)
    global_d = float(np.median([r["mfe"] for r in rows]) - np.median([r["mae"] for r in rows])) if rows else None
    grouped = {}
    for row in rows:
        grouped.setdefault(row["cluster"], []).append(row)
    logs = [math.log((float(np.median([r["mfe"] for r in rs])) + .5) /
                     (float(np.median([r["mae"] for r in rs])) + .5)) for rs in grouped.values()]
    ratio = math.exp(float(np.mean(logs))) if logs else None
    shuffle = cfg["null_models"]["time_shuffle"]
    shuffle_p, perm_frac = time_shuffle_p(rows, int(shuffle["replications"]), int(shuffle["seed"]))
    minimum = spec["population"]["minimum_information_gate"]
    enough = len(rows) >= int(minimum["events"]) and d_inf["clusters"] >= int(minimum["cluster_sessions"])
    null_ok = shuffle_p is not None and perm_frac >= float(shuffle["minimum_permutable_session_fraction"])
    if not enough:
        verdict = "ABSTAIN_POWER_H2"
    elif (d_inf["ci95_lower"] is not None and fp_inf["ci95_lower"] is not None and
          d_inf["ci95_lower"] > 0 and fp_inf["ci95_lower"] > 0 and null_ok and
          shuffle_p <= float(spec["inference"]["alpha_primary"])):
        verdict = "H2_DIRECTION_SUPPORTED"
    elif (d_inf["ci95_upper"] is not None and fp_inf["ci95_upper"] is not None and
          d_inf["ci95_upper"] <= 0 and fp_inf["ci95_upper"] <= 0):
        verdict = "H2_DIRECTION_REFUTED"
    else:
        verdict = "H2_DIRECTION_INCONCLUSIVE"
    return {"verdict": verdict, "horizon": horizon, "eligible_composite_events": len(rows),
        "cluster_sessions": d_inf["clusters"], "d_hat_global_ticks": global_d,
        "session_equal_d_inference": d_inf, "mfe_mae_ratio_secondary": ratio,
        "first_passage_inference": fp_inf,
        "mirror_null": {"d_estimate": None if d_inf["estimate"] is None else -d_inf["estimate"],
            "observed_minus_mirror_d": None if d_inf["estimate"] is None else 2*d_inf["estimate"],
            "first_passage_estimate": None if fp_inf["estimate"] is None else -fp_inf["estimate"],
            "observed_minus_mirror_first_passage": None if fp_inf["estimate"] is None else 2*fp_inf["estimate"]},
        "time_shuffle": {"p_one_sided": shuffle_p, "permutable_session_fraction": perm_frac,
                         "replications": int(shuffle["replications"]), "seed": int(shuffle["seed"])}}, rows


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False,
                               allow_nan=False) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=REPO_ROOT / "specs/avolcluster_poi_compression_v1.json")
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        if spec.get("status") != "FROZEN_METHOD":
            raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", "spec not frozen")
        gs = git_state(REPO_ROOT)
        if gs["dirty"] and not (args.preflight_only and args.allow_dirty):
            raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY", "dirty/unavailable worktree")
        panel, diag = validate_panel(load_table(args.panel), spec)
        expected_sessions = int(spec["population"]["sessions_expected"])
        if diag["sessions"] != expected_sessions:
            raise MeasurementAbort("ABSTAIN_INPUT_INTEGRITY",
                                   f"expected {expected_sessions} contract-sessions; got {diag['sessions']}")
        base = {"schema_version": SCHEMA, "generated_utc": datetime.now(timezone.utc).isoformat(),
                "spec_path": str(args.spec), "spec_sha256": sha256_file(args.spec),
                "panel_path": str(args.panel), "panel_sha256": sha256_file(args.panel),
                "git_state": gs, "preflight": diag, "DESIGN_TARGET_FREE": True,
                "PNL_ACCESSED": False, "HOLDOUT_TOUCHED": False}
        if args.preflight_only:
            result = {**base, "status": "READY", "FUTURE_PRICE_PATH_ACCESSED": False}
            result["payload_sha256"] = canonical_sha(result)
            write_json(args.output_dir / "avolcluster_measurement_preflight.json", result)
            print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
            return 0
        sessions = build_sessions(panel)
        h1, audit_h1 = run_h1(sessions, spec)
        h2, audit_h2 = run_h2(sessions, spec)
        result = {**base, "status": "COMPLETE_PATH_DIAGNOSTIC",
                  "FUTURE_PRICE_PATH_ACCESSED": True, "hypothesis_1": h1,
                  "hypothesis_2": h2, "EDGE_DECLARED": False, "PROMOTION_ELIGIBLE": False}
        result["payload_sha256"] = canonical_sha(result)
        result_path = args.output_dir / spec["outputs"]["json"]
        write_json(result_path, result)
        audit_path = args.output_dir / spec["outputs"]["event_audit_csv"]
        pd.DataFrame(audit_h1 + audit_h2).to_csv(audit_path, index=False)
        manifest = {"schema_version": "avolcluster_measurement_manifest_v1.0.0",
            "result_file": result_path.name, "result_sha256": sha256_file(result_path),
            "audit_file": audit_path.name, "audit_sha256": sha256_file(audit_path),
            "spec_sha256": sha256_file(args.spec), "panel_sha256": sha256_file(args.panel),
            "git_state": gs, "rows_audited": len(audit_h1) + len(audit_h2),
            "FUTURE_PRICE_PATH_ACCESSED": True, "PNL_ACCESSED": False,
            "HOLDOUT_TOUCHED": False, "EDGE_DECLARED": False}
        manifest["payload_sha256"] = canonical_sha(manifest)
        write_json(args.output_dir / spec["outputs"]["manifest"], manifest)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except MeasurementAbort as exc:
        payload = {"schema_version": SCHEMA, "status": exc.label, "message": str(exc),
                   "FUTURE_PRICE_PATH_ACCESSED": False, "PNL_ACCESSED": False,
                   "HOLDOUT_TOUCHED": exc.label == "ABSTAIN_HOLDOUT_FIREWALL"}
        write_json(args.output_dir / "avolcluster_measurement_abstain.json", payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

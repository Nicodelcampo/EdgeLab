# -*- coding: utf-8 -*-
"""Fail-Closed Creation-Only Micro-Tick & Fast-Bar Sweep for BigTrap2 on NQ (V2).

Strictly target-free:
1. Time-bounded PyArrow loading preventing holdout row decoding (cutoff: 2026-06-30T22:00:00Z).
2. Input hash and size verification against canonical input registry before loading.
3. Creation-only detector: zero lifecycle, zero update_zones, zero look-ahead.
4. Spec, commit, clean worktree, and execution token validation at runtime (conjunctive gate).
5. Pre- and post-execution git verification.
6. Preserves output without overwriting retrospective V1 results.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import TickSeries, load_canonical_parquet
from edgelab.bridge.bars import build_time_bars, build_tick_bars, build_footprints
from edgelab.bridge.indicators.bigtrap2_creation_only import detect_creations_only
from tools.build_event_store_all5_v2 import expand_sessions

CT = ZoneInfo("America/Chicago")
HOLDOUT_CUTOFF_UTC_NS = 1782856800000000000  # 2026-06-30T22:00:00Z (20260701 CME start)


def compute_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def cme_session_to_utc_bounds_ns(session_id: str) -> tuple[int, int]:
    """Convert YYYYMMDD CME session ID to [start_utc_ns, end_utc_ns).
    
    Session closes at 16:00 CT on the trade-date.
    Session opens at 17:00 CT on the preceding calendar day (Sunday 17:00 CT for Monday trade-date).
    """
    dt_close = datetime.strptime(session_id, "%Y%m%d").replace(hour=16, minute=0, second=0, microsecond=0, tzinfo=CT)
    dt_open = (dt_close - timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
    start_ns = int(dt_open.astimezone(timezone.utc).timestamp() * 1_000_000_000)
    end_ns = int(dt_close.astimezone(timezone.utc).timestamp() * 1_000_000_000)
    return start_ns, end_ns


def cme_session_dates(ts_ns: np.ndarray) -> np.ndarray:
    sec = ts_ns // 1_000_000_000
    dt = pd.to_datetime(sec, unit="s", utc=True).tz_convert("America/Chicago")
    is_after_17 = dt.hour >= 17
    trade_dt = dt + pd.to_timedelta(np.where(is_after_17, 1, 0), unit="D")
    return trade_dt.strftime("%Y%m%d").to_numpy()


def verify_inputs_fail_closed(data_dir: Path, input_reg: dict[str, Any]) -> dict[str, Path]:
    """Verify size and sha256 for all required contracts from canonical input registry dict."""
    verified_paths: dict[str, Path] = {}
    contracts_dict = input_reg.get("contracts", {})
    if not contracts_dict:
        raise ValueError("[FAIL_CLOSED] Input registry missing 'contracts' dictionary")

    for c_name, c_info in contracts_dict.items():
        exp_sha = c_info["parquet_sha256"]
        exp_size = c_info["bytes"]
        pq_name = c_info.get("parquet_file", f"{c_name.replace(' ', '_')}_ticks.parquet")
        
        pq_path = data_dir / pq_name
        if not pq_path.exists():
            raise FileNotFoundError(f"[FAIL_CLOSED] Required input parquet missing: {pq_path}")
            
        actual_size = pq_path.stat().st_size
        if actual_size != exp_size:
            raise ValueError(f"[FAIL_CLOSED] Size mismatch for {c_name}: expected {exp_size}, got {actual_size}")
            
        actual_sha = compute_sha256(pq_path)
        if actual_sha != exp_sha:
            raise ValueError(f"[FAIL_CLOSED] SHA256 mismatch for {c_name}: expected {exp_sha}, got {actual_sha}")
            
        verified_paths[c_name] = pq_path
    return verified_paths


def verify_git_clean_and_head(expected_commit: str) -> None:
    """Verify git HEAD matches expected commit and worktree is completely clean."""
    try:
        head_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_ROOT, text=True).strip()
    except Exception as e:
        raise RuntimeError(f"[FAIL_CLOSED] Failed to query git state: {e}")

    if status:
        raise RuntimeError(f"[FAIL_CLOSED] Working tree is dirty. Clean before running sweep:\n{status}")

    if head_commit != expected_commit:
        raise ValueError(f"[FAIL_CLOSED] HEAD commit {head_commit} does not match expected commit {expected_commit}")


def verify_runtime_execution_gates(spec: dict[str, Any], expected_commit: str, execution_token: str | None) -> None:
    """Strict conjunctive runtime execution gate:
    spec.status == FROZEN_PREFLIGHT_READY
    AND spec.execution_authorized == true
    AND spec.execution_token == execution_token
    AND spec.frozen_commit == expected_commit
    AND HEAD == expected_commit
    AND worktree clean
    """
    if spec.get("status") != "FROZEN_PREFLIGHT_READY":
        raise PermissionError(
            f"[FAIL_CLOSED] Spec status must be 'FROZEN_PREFLIGHT_READY', got '{spec.get('status')}'. "
            "Draft specs cannot be executed regardless of tokens provided."
        )

    if not spec.get("execution_authorized", False):
        raise PermissionError("[FAIL_CLOSED] Spec execution is not authorized (execution_authorized=false).")

    spec_token = spec.get("execution_token")
    if not spec_token or not execution_token or execution_token != spec_token:
        raise PermissionError("[FAIL_CLOSED] Invalid or missing execution token.")

    spec_commit = spec.get("frozen_commit")
    if not spec_commit or spec_commit != expected_commit:
        raise ValueError(
            f"[FAIL_CLOSED] Spec frozen_commit ({spec_commit}) does not match --expected-commit ({expected_commit})"
        )

    verify_git_clean_and_head(expected_commit)


def run_creation_grid_for_contract(
    pq_path: Path,
    contract: str,
    min_start_ns: int,
    max_end_ns: int,
    valid_sessions: set[str],
    bar_series_types: dict[str, Any],
    grid_configs: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Run creation-only grid on strictly bounded ticks for one contract."""
    effective_max_end = min(max_end_ns, HOLDOUT_CUTOFF_UTC_NS)
    
    # Strictly pushdown filtered PyArrow load preventing any holdout rows from entering memory
    ticks = load_canonical_parquet(
        path=pq_path,
        contract=contract,
        start_utc_ns=min_start_ns,
        end_utc_ns=effective_max_end,
        instrument="NQ",
    )
    
    if np.any(ticks.ts_ns >= HOLDOUT_CUTOFF_UTC_NS):
        raise RuntimeError(f"[FAIL_CLOSED] Holdout tick leaked into memory for {contract}: max_ts={ticks.ts_ns.max()}")

    contract_events: dict[str, list[dict[str, Any]]] = {cfg["cfg_id"]: [] for cfg in grid_configs}

    for b_type, b_info in bar_series_types.items():
        type_configs = [c for c in grid_configs if c["bar_type"] == b_type]
        if not type_configs:
            continue
            
        if b_info["kind"] == "time":
            bars = build_time_bars(ticks, b_info["param"])
        else:
            bars = build_tick_bars(ticks, b_info["param"], reiniciar_por_sesion=True)
            
        fps = build_footprints(ticks, bars)
        ses_ids = cme_session_dates(bars.end_ns)

        for cfg in type_configs:
            cfg_id = cfg["cfg_id"]
            imb = cfg["imbalance_ratio"]
            min_vol = cfg["min_trap_volume"]

            cfg_params = {
                "imbalance_ratio": imb,
                "min_trap_volume": min_vol,
                "min_export_volume": min_vol,
                "use_wick_filter": False,
            }
            # Pure creation-only detection (NO lifecycle, NO touches, NO invalidation)
            zones = detect_creations_only(ticks, bars, fps, params=cfg_params)

            for z in zones:
                b_idx = z["bar_idx"]
                if 0 <= b_idx < len(ses_ids) and ses_ids[b_idx] in valid_sessions:
                    contract_events[cfg_id].append({
                        "contract": contract,
                        "session_id": ses_ids[b_idx],
                        "bar_time_ns": z["bar_time_ns"],
                        "side": z["side"],
                        "top": z["top"],
                        "bottom": z["bottom"],
                        "width_ticks": z["width_ticks"],
                        "bar_idx": b_idx,
                    })

        del bars, fps, ses_ids
        gc.collect()

    del ticks
    gc.collect()
    return contract_events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True, help="Path to execution spec JSON")
    parser.add_argument("--data-dir", type=Path, default=Path(r"E:\EdgeLab\data\nt8\NQ_parquet"))
    parser.add_argument("--expected-commit", type=str, required=True, help="Expected git commit SHA")
    parser.add_argument("--execution-token", type=str, required=True, help="Secret authorization token from spec")
    parser.add_argument("--output-json", type=Path, default=None)
    args = parser.parse_args()

    if not args.spec.exists():
        raise FileNotFoundError(f"[FAIL_CLOSED] Spec not found: {args.spec}")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    
    # Gate 1: Conjunctive authorization and runtime environment validation
    verify_runtime_execution_gates(spec, args.expected_commit, args.execution_token)

    sess_reg_path = REPO_ROOT / spec["binding"]["session_registry_path"]
    inp_reg_path = REPO_ROOT / spec["binding"]["input_registry_path"]

    # Gate 2: Physical registry hash check against spec binding
    actual_sess_sha = compute_sha256(sess_reg_path)
    if actual_sess_sha != spec["binding"]["session_registry_sha256"]:
        raise ValueError(
            f"[FAIL_CLOSED] Session registry SHA mismatch: "
            f"actual {actual_sess_sha} != bound {spec['binding']['session_registry_sha256']}"
        )

    actual_inp_sha = compute_sha256(inp_reg_path)
    if actual_inp_sha != spec["binding"]["input_registry_sha256"]:
        raise ValueError(
            f"[FAIL_CLOSED] Input registry SHA mismatch: "
            f"actual {actual_inp_sha} != bound {spec['binding']['input_registry_sha256']}"
        )

    sess_reg = json.loads(sess_reg_path.read_text(encoding="utf-8"))
    input_reg = json.loads(inp_reg_path.read_text(encoding="utf-8"))
    
    contracts = sess_reg["selection"]["contracts"]
    expanded = expand_sessions(sess_reg)
    
    sessions_by_contract: dict[str, set[str]] = {}
    time_bounds_by_contract: dict[str, tuple[int, int]] = {}
    
    for row in expanded:
        c = row["contract"]
        sid = row["cme_session_id"]
        sessions_by_contract.setdefault(c, set()).add(sid)
        
        # Canonical CME session UTC boundary calculation
        s_ns, e_ns = cme_session_to_utc_bounds_ns(sid)
        if c not in time_bounds_by_contract:
            time_bounds_by_contract[c] = (s_ns, e_ns)
        else:
            cur_s, cur_e = time_bounds_by_contract[c]
            time_bounds_by_contract[c] = (min(cur_s, s_ns), max(cur_e, e_ns))

    total_valid_sessions = sum(len(v) for v in sessions_by_contract.values())
    if total_valid_sessions != 234:
        raise ValueError(f"[FAIL_CLOSED] Expected exactly 234 registered sessions, found {total_valid_sessions}")

    # Verify input integrity
    print("Verifying input Parquets against canonical input registry...")
    verified_paths = verify_inputs_fail_closed(args.data_dir, input_reg)
    print("Input verification PASS: all 5 contracts match canonical SHA256 and size.")

    bar_series_types = spec["grid"]["bar_series_types"]
    grid_configs = []
    for b_type in bar_series_types.keys():
        for imb in spec["grid"]["imbalance_ratios"]:
            for m_vol in spec["grid"]["min_trap_volumes"]:
                cid = f"{b_type}_IMB{int(imb*10)}_VOL{m_vol}"
                grid_configs.append({
                    "cfg_id": cid,
                    "bar_type": b_type,
                    "imbalance_ratio": imb,
                    "min_trap_volume": m_vol,
                })

    all_events: dict[str, list[dict[str, Any]]] = {cfg["cfg_id"]: [] for cfg in grid_configs}
    start_all = time.time()

    for contract in contracts:
        pq_path = verified_paths[contract]
        min_s, max_e = time_bounds_by_contract[contract]
        print(f"[{contract}] Running creation sweep on window [{min_s}, {max_e})...")
        c_events = run_creation_grid_for_contract(
            pq_path=pq_path,
            contract=contract,
            min_start_ns=min_s,
            max_end_ns=max_e,
            valid_sessions=sessions_by_contract[contract],
            bar_series_types=bar_series_types,
            grid_configs=grid_configs,
        )
        for cfg_id, ev_list in c_events.items():
            all_events[cfg_id].extend(ev_list)

    elapsed_all = time.time() - start_all

    results = []
    for cfg in grid_configs:
        cid = cfg["cfg_id"]
        evts = all_events[cid]
        n_ev = len(evts)
        ses_with_ev = len(set(e["session_id"] for e in evts))
        n_buy = sum(1 for e in evts if e["side"] == "B")
        n_sell = sum(1 for e in evts if e["side"] == "S")
        widths = [e["width_ticks"] for e in evts] if evts else [0]

        results.append({
            "cfg_id": cid,
            "bar_type": cfg["bar_type"],
            "imbalance_ratio": cfg["imbalance_ratio"],
            "min_trap_volume": cfg["min_trap_volume"],
            "total_events": n_ev,
            "sessions_with_events": ses_with_ev,
            "coverage_pct": round(ses_with_ev / total_valid_sessions * 100.0, 2),
            "buy_events": n_buy,
            "sell_events": n_sell,
            "buy_ratio": round(n_buy / n_ev, 4) if n_ev else 0.0,
            "events_per_session": round(n_ev / total_valid_sessions, 2),
            "mean_width_ticks": round(float(np.mean(widths)), 2),
            "median_width_ticks": round(float(np.median(widths)), 2),
            "p95_width_ticks": round(float(np.percentile(widths, 95)), 2) if evts else 0.0,
        })

    results.sort(key=lambda x: x["total_events"], reverse=True)

    summary_doc = {
        "schema_version": "bigtrap2_nq_tickframes_sweep_v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "total_configs": len(grid_configs),
        "total_cme_sessions": total_valid_sessions,
        "elapsed_seconds": round(elapsed_all, 1),
        "firewalls": {
            "future_price_path_accessed": False,
            "first_touch_accessed": False,
            "mfe_mae_accessed": False,
            "pnl_accessed": False,
            "holdout_rows_decoded": False,
            "holdout_touched": False,
            "winner_selected": False,
            "edge_declared": False,
            "promotion_eligible": False,
        },
        "results": results,
    }

    out_path = args.output_json or (REPO_ROOT / spec["binding"]["output_result_path"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary_doc, indent=2), encoding="utf-8")
    print(f"\n[Sweep Complete] Output saved to: {out_path}")

    # Final Gate: Post-execution git integrity check
    verify_git_clean_and_head(args.expected_commit)


if __name__ == "__main__":
    main()

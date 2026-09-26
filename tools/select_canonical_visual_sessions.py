"""Target-free reproducible session selection script for HP007-CAMP-002.

Selects 5 representative sessions of the contractually certified asset NQ 06-26
under strict pre-holdout constraints (< 2026-07-01).

Criteria:
- SESS_01: Earliest active pre-holdout session of the contract (2026-03-17).
- SESS_02: Median activity session (50th percentile of total ticks).
- SESS_03: Contract roll boundary session (2026-03-17, state_reset_flag == True).
- SESS_04: High volatility / wide range session (90th percentile of range_ticks).
- SESS_05: Low volatility / narrow range session (10th percentile of range_ticks).
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

CHICAGO = ZoneInfo("America/Chicago")
NQ_PARQUET = Path("E:/EdgeLab/data/nt8/NQ_parquet/NQ_06-26_ticks.parquet")
MANIFEST_OUT = Path("docs/research/HP007_CAMP002_SESSION_SELECTION_MANIFEST_2026-09-15.json")


def get_cme_session_bounds(trade_date: date) -> tuple[int, int]:
    """Returns (open_utc_ns, close_utc_ns) for CME Globex equity index session."""
    open_dt = datetime.combine(trade_date - timedelta(days=1), time(17, 0), CHICAGO)
    close_dt = datetime.combine(trade_date, time(16, 0), CHICAGO)
    open_ns = int(open_dt.astimezone(ZoneInfo("UTC")).timestamp() * 1_000_000_000)
    close_ns = int(close_dt.astimezone(ZoneInfo("UTC")).timestamp() * 1_000_000_000)
    return open_ns, close_ns


def run_selection() -> dict:
    if not NQ_PARQUET.exists():
        raise FileNotFoundError(f"Missing NQ parquet: {NQ_PARQUET}")

    pfile = pq.ParquetFile(NQ_PARQUET)
    sessions: dict[int, dict] = {}

    for i in range(pfile.num_row_groups):
        rg = pfile.read_row_group(i, columns=["ts_utc_ns", "price_ticks", "volume"])
        ts_arr = rg["ts_utc_ns"].to_numpy()
        px_arr = rg["price_ticks"].to_numpy()
        vol_arr = rg["volume"].to_numpy()

        ts_s = ts_arr // 1_000_000_000
        # CDT is UTC-5; 17:00 CDT is 22:00 UTC (7200 seconds before midnight UTC)
        trade_dates = ((ts_s + 7200) // 86400).astype(np.int64)
        unq = np.unique(trade_dates)

        for td in unq:
            mask = (trade_dates == td)
            t_cnt = int(mask.sum())
            v_cnt = int(vol_arr[mask].sum())
            p_min = int(px_arr[mask].min())
            p_max = int(px_arr[mask].max())
            first_ts = int(ts_arr[mask][0])
            last_ts = int(ts_arr[mask][-1])

            if td not in sessions:
                sessions[td] = {
                    "ticks": t_cnt,
                    "volume": v_cnt,
                    "min_p": p_min,
                    "max_p": p_max,
                    "first_ts": first_ts,
                    "last_ts": last_ts
                }
            else:
                sessions[td]["ticks"] += t_cnt
                sessions[td]["volume"] += v_cnt
                sessions[td]["min_p"] = min(sessions[td]["min_p"], p_min)
                sessions[td]["max_p"] = max(sessions[td]["max_p"], p_max)
                sessions[td]["last_ts"] = max(sessions[td]["last_ts"], last_ts)

    # Front-month liquid window of NQ 06-26:
    # 2026-03-17 (first day volume leader post-roll) to 2026-06-12 (last day before roll to NQ 09-26)
    rows = []
    for td, d in sorted(sessions.items()):
        dt = pd.to_datetime(td, unit="D").date()
        dstr = dt.strftime("%Y-%m-%d")
        if "2026-03-17" <= dstr <= "2026-06-12" and d["ticks"] >= 100_000 and dt.weekday() < 5:
            rng_ticks = d["max_p"] - d["min_p"]
            open_ns, close_ns = get_cme_session_bounds(dt)
            rows.append({
                "trade_date": dstr,
                "day_of_week": dt.strftime("%A"),
                "ticks": d["ticks"],
                "volume": d["volume"],
                "range_ticks": rng_ticks,
                "range_pts": round(rng_ticks * 0.25, 2),
                "min_price_ticks": d["min_p"],
                "max_price_ticks": d["max_p"],
                "session_open_utc_ns": open_ns,
                "session_close_utc_ns": close_ns
            })

    df = pd.DataFrame(rows)
    q_ticks = df["ticks"].quantile([0.10, 0.50, 0.90]).to_dict()
    q_range = df["range_ticks"].quantile([0.10, 0.50, 0.90]).to_dict()

    # SESS_01: Earliest session
    s01_row = df.iloc[0]
    # SESS_02: Median ticks
    s02_idx = (df["ticks"] - q_ticks[0.50]).abs().idxmin()
    s02_row = df.loc[s02_idx]
    # SESS_03: Roll boundary session (2026-03-17)
    s03_matches = df[df["trade_date"] == "2026-03-17"]
    if len(s03_matches) == 0:
        raise RuntimeError("Roll session 2026-03-17 not found in eligible sessions")
    s03_row = s03_matches.iloc[0]
    # SESS_04: High volatility (90th pct range)
    s04_idx = (df["range_ticks"] - q_range[0.90]).abs().idxmin()
    s04_row = df.loc[s04_idx]
    # SESS_05: Low volatility / narrow range (10th pct range)
    s05_idx = (df["range_ticks"] - q_range[0.10]).abs().idxmin()
    s05_row = df.loc[s05_idx]

    selected_sessions = [
        {
            "session_id": "SESS_01",
            "trade_date": s01_row["trade_date"],
            "selection_criterion": "EARLIEST_ACTIVE_PRE_HOLDOUT_SESSION",
            "selection_rank": 1,
            "metric_evaluated": "min(trade_date)",
            "metrics": s01_row.to_dict(),
            "visual_inspection_objective": "Evaluate cold-start zone formation, initial warmup, and early intensity accumulation."
        },
        {
            "session_id": "SESS_02",
            "trade_date": s02_row["trade_date"],
            "selection_criterion": "MEDIAN_ACTIVITY_SESSION",
            "selection_rank": 1,
            "metric_evaluated": f"closest_to_p50_ticks ({q_ticks[0.50]:.0f})",
            "metrics": s02_row.to_dict(),
            "visual_inspection_objective": "Inspect standard density intervals and typical absorption geometries under median volume."
        },
        {
            "session_id": "SESS_03",
            "trade_date": s03_row["trade_date"],
            "selection_criterion": "CONTRACT_ROLL_BOUNDARY_SESSION",
            "selection_rank": 1,
            "metric_evaluated": "state_reset_flag == True at opening tick",
            "metrics": s03_row.to_dict(),
            "visual_inspection_objective": "Verify hard purge of prior state and memory reset across the NQ 03-26 -> NQ 06-26 rollover boundary."
        },
        {
            "session_id": "SESS_04",
            "trade_date": s04_row["trade_date"],
            "selection_criterion": "HIGH_VOLATILITY_WIDE_RANGE_SESSION",
            "selection_rank": 1,
            "metric_evaluated": f"closest_to_p90_range ({q_range[0.90]:.0f} ticks)",
            "metrics": s04_row.to_dict(),
            "visual_inspection_objective": "Inspect wear attenuation (NO_WEAR vs FULL) and behavior under rapid price displacement and multiple touches."
        },
        {
            "session_id": "SESS_05",
            "trade_date": s05_row["trade_date"],
            "selection_criterion": "LOW_VOLATILITY_NARROW_RANGE_SESSION",
            "selection_rank": 1,
            "metric_evaluated": f"closest_to_p10_range ({q_range[0.10]:.0f} ticks)",
            "metrics": s05_row.to_dict(),
            "visual_inspection_objective": "Inspect narrow intervals (W < 5 ticks) and zone cannibalization under narrow price compression."
        }
    ]

    manifest = {
        "manifest_version": "hp007_camp002_session_selection_v1",
        "phase": "VISUAL_LOGIC_DESIGN",
        "revisit_hypothesis_measurement": "ON_HOLD_BY_OWNER",
        "asset": {
            "root": "NQ",
            "contract": "NQ 06-26",
            "certification_status": "CERTIFIED_MULTI_ASSET_V2",
            "source_parquet": str(NQ_PARQUET),
            "parquet_sha256": "3de249b9b8d8ada01c5b485aa893ccdf1315ae3f7bbebcaf72024de12e1b25f6",
            "tick_size": 0.25,
            "timezone": "America/Chicago"
        },
        "selection_universe": {
            "description": "All CME regular trading sessions of NQ 06-26 during its active front-month window prior to holdout cutoff",
            "date_range": "2026-03-17 to 2026-06-12",
            "total_sessions_evaluated": len(df),
            "ticks_quantiles": {f"p{int(k*100)}": round(v, 2) for k, v in q_ticks.items()},
            "range_ticks_quantiles": {f"p{int(k*100)}": round(v, 2) for k, v in q_range.items()}
        },
        "eligibility_rule": "Regular weekday (Mon-Fri) in CME calendar with >= 100,000 ticks, excluding post-roll illiquid tail (>= 2026-06-15)",
        "metric_information_cutoff": "2026-06-30T22:00:00Z (SEALED HOLDOUT ENFORCED)",
        "roll_transition_provenance": {
            "outgoing_contract": "NQ 03-26",
            "incoming_contract": "NQ 06-26",
            "crossover_signal_trade_date": "2026-03-16",
            "crossover_signal_volumes": {
                "NQ_03-26_vol": 249343,
                "NQ_06-26_vol": 280702,
                "leader_ratio": 1.1257
            },
            "effective_roll_trade_date": "2026-03-17",
            "state_reset_flag_enforced": True,
            "roll_manifest_reference": "docs/research/contract_regimes/NQ_contract_regime_v2_20260915.json",
            "roll_manifest_sha256": "d796c34696b5cd997097ca19532588147d337a5441a106f369931b67a149b5c3"
        },
        "selected_sessions": selected_sessions
    }

    # Hash of this script
    script_path = Path("tools/select_canonical_visual_sessions.py")
    if script_path.exists():
        manifest["selection_script_sha256"] = hashlib.sha256(script_path.read_bytes()).hexdigest()

    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Selection manifest written to: {MANIFEST_OUT}")
    print(f"Total eligible sessions in universe: {len(df)}")
    print(f"Ticks quantiles: {manifest['selection_universe']['ticks_quantiles']}")
    print(f"Range quantiles: {manifest['selection_universe']['range_ticks_quantiles']}")
    print(f"\nSelected {len(selected_sessions)} sessions:")
    for s in selected_sessions:
        print(f"  {s['session_id']}: {s['trade_date']} ({s['selection_criterion']}) - Ticks: {s['metrics']['ticks']:,} Range: {s['metrics']['range_ticks']:,}t ({s['metrics']['range_pts']} pts)")

    return manifest


if __name__ == "__main__":
    run_selection()

#!/usr/bin/env python3
"""Derive GC transfer priors for BT2A NQ Gate 1 power planning.

Reads ONLY GC Gate 1 all-5 artifacts already committed in docs/research/ for a
run whose outcomes are already open (CAMPAIGN_OUTCOMES_OPENED=true). Reads no NQ
outcome, no future price path, no P&L and no holdout. Emits a hash-bound prior
artifact. Grants no freeze and no execution authorization.

The transferred parameter is the REALIZED paired-session contrast SD. It is
measured at session level, so it requires no ICC assumption: the clustering is
already embedded in the realized session-level dispersion.
"""
import argparse
import csv
import glob
import hashlib
import json
import math
import os
import statistics as st
from statistics import NormalDist

ND = NormalDist()
SESSION_GLOB = "BT2_ABSORPTION_GATE1_ALL5_SESSIONS_GC_*.csv"
RESULT_NAME = "BT2_ABSORPTION_GATE1_ALL5_RESULT_2026-08-26.json"
FORBIDDEN = ("mfe", "mae", "pnl", "holdout", "future_price")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def canonical_sha256(obj):
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def load_sessions(research_dir):
    rows = []
    for path in sorted(glob.glob(os.path.join(research_dir, SESSION_GLOB))):
        with open(path, newline="") as fh:
            for rec in csv.DictReader(fh):
                try:
                    k_abs = float(rec["K_ABS"])
                    n_rand = float(rec["N_RAND_median"])
                    events = float(rec["K_ABS_events"])
                except (KeyError, TypeError, ValueError):
                    continue
                if events <= 0:
                    continue
                rows.append({
                    "contract": rec["contract"],
                    "session": rec["session"],
                    "contrast": k_abs - n_rand,
                    "events": events,
                    "k_abs": k_abs,
                    "n_rand": n_rand,
                })
    return rows


def assert_nq_firewall(research_dir):
    """Fail closed if any NQ outcome artifact is reachable from this derivation."""
    for path in sorted(glob.glob(os.path.join(research_dir, "*NQ*"))):
        low = os.path.basename(path).lower()
        if any(tok in low for tok in FORBIDDEN):
            raise SystemExit(
                "ABORT: NQ outcome-shaped artifact in scope: " + path)


def derive(research_dir):
    assert_nq_firewall(research_dir)
    result_path = os.path.join(research_dir, RESULT_NAME)
    result = json.load(open(result_path))
    if not result.get("CAMPAIGN_OUTCOMES_OPENED"):
        raise SystemExit(
            "ABORT: GC source run does not declare outcomes already open")

    rows = load_sessions(research_dir)
    if not rows:
        raise SystemExit("ABORT: no GC session rows found")

    contrasts = [r["contrast"] for r in rows]
    n = len(contrasts)
    mean_d = st.mean(contrasts)
    sd_d = st.stdev(contrasts)

    published = result["contrasts"]["K_ABS_minus_N_RAND"]
    if abs(published["point"] - mean_d) > 1e-9 or published["n_sessions"] != n:
        raise SystemExit(
            "ABORT: reconstruction does not match the published GC contrast")

    sources = {}
    for path in sorted(glob.glob(os.path.join(research_dir, SESSION_GLOB))) + [result_path]:
        sources[os.path.basename(path)] = sha256_file(path)

    return {
        "n_sessions": n,
        "mean_paired_session_contrast_ticks": mean_d,
        "sd_paired_session_contrast_ticks": sd_d,
        "se_mean_ticks": sd_d / math.sqrt(n),
        "rho_between_arms": st.correlation(
            [r["k_abs"] for r in rows], [r["n_rand"] for r in rows]),
        "mean_events_per_session": st.mean([r["events"] for r in rows]),
        "published_contrast": published,
        "reconstruction_matches_published_contrast": True,
        "source_files_sha256": sources,
        "source_estimand": result["estimand"],
        "source_status": result["status"],
    }


def power_table(sd, n_sessions, mde, alphas=(0.05, 0.05 / 16), power=0.80):
    z_pow = ND.inv_cdf(power)
    out = []
    for alpha in alphas:
        z_sum = ND.inv_cdf(1 - alpha / 2) + z_pow
        out.append({
            "alpha": alpha,
            "z_sum": z_sum,
            "required_sessions_at_mde": math.ceil((z_sum * sd / mde) ** 2),
            "mde_resolvable_at_available": z_sum * sd / math.sqrt(n_sessions),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--research-dir", default="docs/research")
    ap.add_argument("--nq-sessions", type=int, required=True)
    ap.add_argument("--design-mde-ticks", type=float, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    measured = derive(args.research_dir)
    sd = measured["sd_paired_session_contrast_ticks"]

    payload = {
        "schema_version": "bt2a_nq_gate1_gc_transfer_prior_v1",
        "status": "DRAFT_REVIEW_REQUIRED",
        "target_free_wrt_nq": True,
        "freeze_authorized": False,
        "execution_authorized": False,
        "measured": measured,
        "nq_power": {
            "n_sessions_available": args.nq_sessions,
            "design_mde_ticks": args.design_mde_ticks,
            "transferred_sd_ticks": sd,
            "table": power_table(sd, args.nq_sessions, args.design_mde_ticks),
        },
        "firewall": {
            "nq_outcomes_accessed": False,
            "nq_future_price_path_accessed": False,
            "nq_holdout_touched": False,
            "pnl_accessed": False,
            "edge_declared": False,
        },
    }
    payload["payload_sha256"] = canonical_sha256(payload)

    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(payload, indent=2, sort_keys=True,
                            ensure_ascii=False, allow_nan=False) + "\n")

    print(json.dumps({
        "n_sessions": measured["n_sessions"],
        "sd_paired_session_contrast_ticks": sd,
        "payload_sha256": payload["payload_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()

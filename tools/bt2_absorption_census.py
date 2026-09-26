#!/usr/bin/env python3
"""Censo target-free de BigTrap2Absorption.

Reconstruye el anillo causal desde ABS_SCORE, valida el modo fuente contra el
export y, solamente si la reproduccion es exacta, calcula los tres censos del
§4 para el headline AbsMagnitude. No calcula caminos, MFE, MAE, retornos ni P&L.

Ejemplo:
  python tools/bt2_absorption_census.py export_directional.csv \
      --source-mode AbsDirectional --headline-export export_magnitude.csv \
      --json-out censo.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path


def percentile(values, q):
    if not values:
        return float("nan")
    if len(values) == 1:
        return float(values[0])
    xs = sorted(values)
    pos = max(0.0, min(100.0, float(q))) / 100.0 * (len(xs) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return float(xs[lo])
    return float(xs[lo] + (xs[hi] - xs[lo]) * (pos - lo))


def parse_kv(text):
    out = {}
    for item in text.split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            out[key] = value
    return out


def as_bool(value):
    return str(value).strip().lower() == "true"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_export(path):
    rows, zones = [], []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("|", 3)
            if len(parts) != 4:
                continue
            event, data = parts[2], parse_kv(parts[3])
            if event == "ABS_SCORE":
                rows.append({
                    "bar": int(data["bar"]),
                    "residual": as_bool(data["residual"]),
                    "signed_flow": float(data["signed_flow"]),
                    "d_ticks": float(data["d_ticks"]),
                    "a_score": float(data["a_score"]),
                    "a_thr": float(data["a_thr"]) if data["a_thr"] != "NaN" else float("nan"),
                    "a_pass": as_bool(data["a_pass"]),
                    "n_hist": int(data["n_hist"]),
                    "td": data["td"],
                })
            elif event == "ZONE_CREATED":
                zones.append({"dir": data["dir"], "td": data["td"]})
    return rows, zones


def reconstruct(rows, mode, residuals_enter_ring, pct, lookback, min_history):
    ring, out = [], []
    for row in rows:
        sf, dt = row["signed_flow"], row["d_ticks"]
        if mode == "AbsDirectional":
            sign = 1.0 if sf > 0 else (-1.0 if sf < 0 else 0.0)
            denominator = 1.0 + max(0.0, sign * dt)
        elif mode == "AbsMagnitude":
            denominator = 1.0 + abs(dt)
        else:
            raise ValueError(mode)
        score = abs(sf) / denominator
        n_hist = len(ring)
        if n_hist >= min_history:
            threshold = percentile(ring, pct)
            passed = score >= threshold
        else:
            threshold, passed = float("nan"), False
        if row["residual"]:
            passed = False
        out.append({
            "a_score": score, "a_thr": threshold, "a_pass": passed,
            "n_hist": n_hist, "denom": denominator, "td": row["td"],
            "residual": row["residual"], "signed_flow": sf, "d_ticks": dt,
        })
        if row["residual"] and not residuals_enter_ring:
            continue
        if len(ring) == lookback:
            ring.pop(0)
        ring.append(score)
    return out


def same_float(a, b, tol=1e-9):
    return (math.isnan(a) and math.isnan(b)) or (
        not math.isnan(a) and not math.isnan(b) and abs(a - b) <= tol
    )


def validation(sim, rows):
    return {
        "a_score": sum(same_float(a["a_score"], b["a_score"]) for a, b in zip(sim, rows)),
        "a_thr": sum(same_float(a["a_thr"], b["a_thr"]) for a, b in zip(sim, rows)),
        "a_pass": sum(a["a_pass"] == b["a_pass"] for a, b in zip(sim, rows)),
        "n_hist": sum(a["n_hist"] == b["n_hist"] for a, b in zip(sim, rows)),
        "total": len(rows),
    }


def corr(x, y):
    if len(x) < 2:
        return float("nan")
    mx, my = st.fmean(x), st.fmean(y)
    xx = sum((v - mx) ** 2 for v in x)
    yy = sum((v - my) ** 2 for v in y)
    if xx == 0 or yy == 0:
        return float("nan")
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(xx * yy)


def zone_mix(zones):
    by_session = defaultdict(lambda: {"long": 0, "short": 0})
    for zone in zones:
        by_session[zone["td"]][zone["dir"]] += 1
    longs = sum(v["long"] for v in by_session.values())
    shorts = sum(v["short"] for v in by_session.values())
    return {
        "n": longs + shorts,
        "long": longs,
        "short": shorts,
        "long_fraction": longs / (longs + shorts) if longs + shorts else None,
        "by_session": {
            td: {**v, "long_fraction": v["long"] / (v["long"] + v["short"])}
            for td, v in sorted(by_session.items())
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("export", type=Path, help="Export usado para la auto-validacion")
    ap.add_argument("--source-mode", choices=("AbsDirectional", "AbsMagnitude"), default="AbsDirectional")
    ap.add_argument("--headline-export", type=Path, help="Opcional: export AbsMagnitude para contar sus zonas")
    ap.add_argument("--abs-pct", type=float, default=90.0)
    ap.add_argument("--lookback", type=int, default=500)
    ap.add_argument("--min-history", type=int, default=200)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    rows, source_zones = parse_export(args.export)
    if not rows:
        raise SystemExit("No se encontraron eventos ABS_SCORE")

    validations, exact = {}, []
    for residuals_enter in (True, False):
        sim = reconstruct(rows, args.source_mode, residuals_enter, args.abs_pct, args.lookback, args.min_history)
        check = validation(sim, rows)
        validations[str(residuals_enter).lower()] = check
        if all(check[k] == check["total"] for k in ("a_score", "a_thr", "a_pass", "n_hist")):
            exact.append(residuals_enter)
    if len(exact) != 1:
        raise SystemExit(f"Gate de reconstruccion no univoco: {validations}")

    residuals_enter = exact[0]
    headline = reconstruct(rows, "AbsMagnitude", residuals_enter, args.abs_pct, args.lookback, args.min_history)
    n = len(headline)

    d_fav_le_zero = sum(
        (1.0 if r["signed_flow"] > 0 else (-1.0 if r["signed_flow"] < 0 else 0.0)) * r["d_ticks"] <= 0
        for r in rows
    )
    passed = [r for r in headline if r["a_pass"]]
    denom_one_all = sum(r["denom"] == 1.0 for r in headline)
    denom_one_pass = sum(r["denom"] == 1.0 for r in passed)

    thresholds = defaultdict(list)
    pass_counts = defaultdict(lambda: [0, 0])
    for row in headline:
        if not math.isnan(row["a_thr"]):
            thresholds[row["td"]].append(row["a_thr"])
            pass_counts[row["td"]][1] += 1
            pass_counts[row["td"]][0] += int(row["a_pass"])

    threshold_sessions = {}
    for td, values in sorted(thresholds.items()):
        p10, p50, p90 = percentile(values, 10), percentile(values, 50), percentile(values, 90)
        threshold_sessions[td] = {
            "n": len(values), "min": min(values), "p10": p10, "p50": p50,
            "p90": p90, "max": max(values),
            "p90_p10_ratio": p90 / p10 if p10 else None,
            "max_min_ratio": max(values) / min(values) if min(values) else None,
            "a_pass": pass_counts[td][0],
            "a_pass_rate": pass_counts[td][0] / pass_counts[td][1],
        }

    zone_source = source_zones
    zone_path = args.export
    if args.headline_export:
        _, zone_source = parse_export(args.headline_export)
        zone_path = args.headline_export

    result = {
        "schema": "bt2_absorption_census_v1",
        "target_free": True,
        "outcomes_opened": False,
        "inputs": {
            "validation_export": str(args.export),
            "validation_sha256": sha256(args.export),
            "source_mode": args.source_mode,
            "headline_zone_export": str(zone_path),
            "headline_zone_sha256": sha256(zone_path),
        },
        "parameters": {"abs_pct": args.abs_pct, "lookback": args.lookback, "min_history": args.min_history},
        "reconstruction_gate": {
            "validations": validations,
            "exact": True,
            "residuals_enter_ring": residuals_enter,
        },
        "section_4_1": {
            "d_fav_le_zero": d_fav_le_zero,
            "total": n,
            "fraction": d_fav_le_zero / n,
        },
        "section_4_2": {
            "denom_one_all": denom_one_all,
            "denom_one_all_fraction": denom_one_all / n,
            "a_pass_total": len(passed),
            "denom_one_a_pass": denom_one_pass,
            "denom_one_a_pass_fraction": denom_one_pass / len(passed),
            "denom_a_pass_median": st.median(r["denom"] for r in passed),
            "corr_score_abs_flow_all": corr([r["a_score"] for r in headline], [abs(r["signed_flow"]) for r in headline]),
            "corr_score_abs_flow_a_pass": corr([r["a_score"] for r in passed], [abs(r["signed_flow"]) for r in passed]),
        },
        "section_4_3": {"by_session": threshold_sessions},
        "headline_zone_mix": zone_mix(zone_source),
    }

    text = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
    print(text)
    if args.json_out:
        args.json_out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

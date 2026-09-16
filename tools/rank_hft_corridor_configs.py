"""Evaluate target-free visual ranking of HFT corridor configurations."""
from __future__ import annotations

import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.research.hft_corridors import (
    evaluate_visual_configurations,
    causal_domain,
    normalize_hft_zones,
    HFT_VISUAL_CONFIGS,
    HFT_PARITY_STATUS,
)
from tools.build_hft_corridor_bundle import read_zones


def main():
    zones_path = Path("data/nt8_oracles/hft_zones_nq_20260603_20260611.csv")
    raw_zones = read_zones(zones_path)
    zones = normalize_hft_zones(raw_zones)

    # Load bundle candles
    bundle_path = Path("viewer/nt8_bridge/hft_nq_bundle.js")
    raw_js = bundle_path.read_text(encoding="utf-8")
    prefix = "window.HFT_NQ_CORRIDOR_BUNDLE="
    idx = raw_js.find(prefix)
    if idx < 0:
        raise ValueError("Invalid bundle format: missing window.HFT_NQ_CORRIDOR_BUNDLE prefix")
    json_str = raw_js[idx + len(prefix):].rstrip(";\n ")
    bundle = json.loads(json_str)
    candles = bundle["candles"]

    times = [c["time_ns"] for c in candles]
    tick_size = float(bundle["meta"]["tick_size"])
    price_ticks = [c["price_tick"] for c in candles]

    # Pick 8 causal evaluation timestamps across the timeline (20% to 90%)
    n_candles = len(times)
    fractions = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
    t_refs = [times[int(n_candles * frac)] for frac in fractions]

    domains = {}
    for t_ref in t_refs:
        pmin, pmax = causal_domain(price_ticks, times, t_ref, zones, tick_size, margin_ticks=20)
        domains[t_ref] = (pmin, pmax)

    ranking = evaluate_visual_configurations(zones, t_refs, tick_size, domains)

    out_path = Path("docs/research/HP007_CAMP002_HFT_CORRIDOR_VISUAL_RANKING.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(ranking, indent=2), encoding="utf-8")

    print("Target-Free Visual Ranking Successfully Generated:")
    print(f"Status: {ranking['status']}")
    print(f"Parity Status: {ranking['parity_status']}")
    print(f"Recommended for owner review: {ranking['recommended_for_owner_review']}")
    print("Configurations ranked:")
    for r in ranking["configurations"]:
        print(f"  - {r['configuration_id']}: score={r['target_free_visual_score']} | "
              f"coverage={r['median_positive_fraction']} | CV={r['median_cv']} | "
              f"intervals={r['median_interval_count']}")
    print(f"Saved ranking report to {out_path}")


if __name__ == "__main__":
    main()


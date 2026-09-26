#!/usr/bin/env python3
"""Auditoria reproducible de potencia para Puerta 1 de BigTrap2Absorption.

Distingue tres cantidades que no deben confundirse:
1) semiancho esperado del IC 95 %;
2) potencia de que el limite inferior del IC 95 % supere cero;
3) N necesario para potencia objetivo.

No lee datos de mercado ni outcomes.
"""
from __future__ import annotations

import argparse
import json
import math


def phi(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def power_two_sided_ci(effect, sd, n, zcrit=1.959963984540054):
    mu = effect * math.sqrt(n) / sd
    return 1.0 - phi(zcrit - mu) + phi(-zcrit - mu)


def n_for_power(effect, sd, zcrit=1.959963984540054, zpower=0.8416212335729143):
    return math.ceil(((zcrit + zpower) * sd / effect) ** 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, default=120)
    ap.add_argument("--sd-ratio", type=float, default=0.282)
    ap.add_argument("--ratio-per-tick", type=float, default=0.0275)
    ap.add_argument("--legacy-effect", type=float, default=0.053)
    ap.add_argument("--adjusted-effect", type=float, default=0.0374)
    ap.add_argument("--economic-ticks", type=float, default=2.5)
    args = ap.parse_args()

    z95, z80 = 1.959963984540054, 0.8416212335729143
    econ_ratio = args.economic_ticks * args.ratio_per_tick
    halfwidth = z95 * args.sd_ratio / math.sqrt(args.sessions)
    mde80 = (z95 + z80) * args.sd_ratio / math.sqrt(args.sessions)
    effects = {
        "legacy_bigtrap2_ratio": args.legacy_effect,
        "mix_adjusted_illustrative_ratio": args.adjusted_effect,
        "economic_2_5_ticks_ratio": econ_ratio,
    }
    out = {
        "sessions": args.sessions,
        "assumptions": {
            "paired_session_sd_ratio": args.sd_ratio,
            "ratio_per_tick": args.ratio_per_tick,
            "criterion": "lower bound of two-sided 95% CI > 0",
            "target_power": 0.80,
            "normal_approximation": True,
        },
        "precision": {
            "expected_95pct_halfwidth_ratio": halfwidth,
            "expected_95pct_halfwidth_ticks": halfwidth / args.ratio_per_tick,
            "mde_80pct_ratio": mde80,
            "mde_80pct_ticks": mde80 / args.ratio_per_tick,
        },
        "effects": {
            name: {
                "effect_ratio": effect,
                "effect_ticks": effect / args.ratio_per_tick,
                "power_at_n": power_two_sided_ci(effect, args.sd_ratio, args.sessions),
                "sessions_for_80pct": n_for_power(effect, args.sd_ratio),
            }
            for name, effect in effects.items()
        },
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

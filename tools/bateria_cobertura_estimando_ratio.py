"""Cobertura de G2 para theta_trade=sum_d(u_d)/sum_d(v_d).

Batería declarada para n=160,197,250. Usa la API productiva bootstrap-t:
bloques estacionarios de pares (u,v), b PPW sobre psi=u-theta*v y HAC lag=b.
El criterio mínimo 0.90 es de adopción interna; no redefine el nominal 0.95.
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass

from edgelab.stats.cluster_estimand import (
    SessionAggregate,
    studentized_stationary_interval,
)

SEED_BASE = 20330803
SIZES = (160, 197, 250)
NOMINAL = 0.95
CRITERION_MIN = 0.90


@dataclass(frozen=True)
class Scenario:
    name: str
    true_theta: float


SCENARIOS = (
    Scenario("balanced_iid", 0.20),
    Scenario("informative_size", 2.0 / 7.0),
    Scenario("heavy_tail", 0.20),
    Scenario("serial_ar07", 0.20),
)


def generate(scenario, *, n_sessions, seed):
    rng = random.Random(seed)
    rows, ar = [], 0.0
    for d in range(n_sessions):
        if scenario.name == "balanced_iid":
            n, mu, shock = 5, scenario.true_theta, rng.gauss(0.0, 0.6)
        elif scenario.name == "informative_size":
            draw = rng.random()
            if draw < 0.20:
                n, mu = 0, 0.0
            elif draw < 0.70:
                n, mu = 1, -1.0
            else:
                n, mu = 10, 0.5
            shock = rng.gauss(0.0, 0.5)
        elif scenario.name == "heavy_tail":
            n, mu = 5, scenario.true_theta
            shock = (rng.gauss(0.0, 3.0) if rng.random() < 0.08
                     else rng.gauss(0.0, 0.35))
        elif scenario.name == "serial_ar07":
            n, mu = 5, scenario.true_theta
            ar = 0.7 * ar + rng.gauss(0.0, 0.6 * (1 - 0.7 ** 2) ** 0.5)
            shock = ar
        else:
            raise ValueError(scenario.name)
        pnl = 0.0 if n == 0 else sum(
            mu + shock + rng.gauss(0.0, 1.0) for _ in range(n))
        rows.append(SessionAggregate("d%04d" % d, pnl, n))
    return tuple(rows)


def evaluate(scenario, *, n_sessions, sims, reps, seed_base):
    covered = valid = 0
    widths, biases, blocks = [], [], []
    for i in range(sims):
        rows = generate(scenario, n_sessions=n_sessions, seed=seed_base + i)
        try:
            ci = studentized_stationary_interval(
                rows, n_replicates=reps, seed=seed_base + 100000 + i)
        except Exception:
            continue
        valid += 1
        covered += ci.lower <= scenario.true_theta <= ci.upper
        widths.append(ci.upper - ci.lower)
        biases.append(ci.observed - scenario.true_theta)
        blocks.append(ci.block_length)
    ordered = sorted(blocks)
    return dict(
        scenario=scenario.name, true_theta=scenario.true_theta,
        n=n_sessions, sims=sims, reps=reps, valid=valid,
        coverage=covered / valid if valid else 0.0,
        mean_width=sum(widths) / valid if valid else None,
        mean_bias=sum(biases) / valid if valid else None,
        block_median=ordered[len(ordered) // 2] if ordered else None,
        block_min=min(blocks) if blocks else None,
        block_max=max(blocks) if blocks else None,
        passed=bool(valid == sims and covered / valid >= CRITERION_MIN),
    )


def run(*, sims=200, reps=400, seed_base=SEED_BASE):
    results = []
    for scenario in SCENARIOS:
        for n in SIZES:
            results.append(evaluate(
                scenario, n_sessions=n, sims=sims, reps=reps,
                seed_base=seed_base + n * 1000))
    return dict(
        seed_base=seed_base, nominal=NOMINAL, criterion_min=CRITERION_MIN,
        method="stationary_bootstrap_t_ppw_influence_hac",
        sizes=list(SIZES), scenarios=[asdict(x) for x in SCENARIOS],
        all_passed=all(r["passed"] for r in results), results=results)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--sims", type=int, default=200)
    parser.add_argument("--reps", type=int, default=400)
    parser.add_argument("--seed", type=int, default=SEED_BASE)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = run(sims=args.sims, reps=args.reps, seed_base=args.seed)
    text = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(text)
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

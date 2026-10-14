#!/usr/bin/env python3
"""Synthetic continuation vs failed-break classifier; no market input support."""
import argparse
import json
from edgelab.kaggle.avzvol_reactions import Band, Bar, Policy, classify_synthetic_reaction


def synthetic_cases():
    band = Band("SYNTHETIC-BAND", 100, 110, -1, -1)
    policy = Policy("SYNTHETIC-NOT-APPROVED-MARKET-POLICY", 0, 1, 10, "inside",
                    "strictly_later_bar", "terminate_unknown")
    def bar(n, low, high, close):
        return Bar(str(n), "SYNTHETIC-SESSION", n * 10, n * 10, n, high, low, close, True)
    prefix = [bar(0, 101, 109, 105), bar(1, 111, 115, 114), bar(2, 109, 113, 112)]
    cases = {"continuation": prefix + [bar(3, 111, 115, 114)],
             "failed_break": prefix + [bar(3, 104, 109, 105)], "touch_only": prefix}
    results = {name: classify_synthetic_reaction(band, bars, policy=policy,
                cohort="zone_candidate", purpose="synthetic") for name, bars in cases.items()}
    assert {k: v["state"] for k, v in results.items()} == {
        "continuation": "CONTINUATION_TRIGGER", "failed_break": "FAILED_BREAK_TRIGGER",
        "touch_only": "RETEST_OBSERVED"}
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purpose", choices=("synthetic", "research"), default="synthetic")
    args = parser.parse_args(argv)
    if args.purpose != "synthetic":
        print(json.dumps({"status": "STOP_MARKET_REPLAY_NOT_IMPLEMENTED_OR_AUTHORIZED",
                          "inputs_opened": False, "outcomes_computed": False}))
        return 2
    print(json.dumps({"scope": "SYNTHETIC_ONLY", "cases": synthetic_cases()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

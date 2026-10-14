#!/usr/bin/env python3
"""Synthetic measurement demo only, no market loader or implicit policies."""
import argparse
import json
from edgelab.kaggle.avzvol_reaction_response import (
    Decision, ResponseBar, ResponsePolicy, measure_synthetic_response)


def synthetic_cases():
    d = Decision("D", "SYNTHETIC-BAND", "SYNTHETIC-TRIGGER", "SYNTHETIC-SESSION",
                 100, 10, 113, 1, "CONTINUATION_TRIGGER")
    p = ResponsePolicy("SYNTHETIC-NOT-MARKET-POLICY", (20, 40), 5, 10)
    b = ResponseBar("F1", "SYNTHETIC-SESSION", 101, 110, 110, 11, 20, 120, 112, 118, True)
    def result(bars, until):
        return measure_synthetic_response(d, bars, policy=p, observed_until_ns=until,
                                          termination_reason="WINDOW_END", purpose="synthetic")
    cases = {"complete": result([b], 140), "censored": result([b], 115),
             "no_completed_bar": result([], 140)}
    assert cases["complete"]["results"][0]["signed_close_response_exit_ticks"] == 5
    assert cases["censored"]["results"][0]["signed_close_response_exit_ticks"] is None
    assert cases["no_completed_bar"]["results"][0]["signed_close_response_exit_ticks"] is None
    return cases


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purpose", choices=("synthetic", "research"), default="synthetic")
    args = parser.parse_args(argv)
    if args.purpose != "synthetic":
        print(json.dumps({"status": "STOP_NEW_MARKET_OUTCOMES_NOT_IMPLEMENTED_OR_AUTHORIZED",
                          "inputs_opened": False}))
        return 2
    print(json.dumps({"scope": "INVENTED_PATHS_ONLY_NOT_EFFECT_ESTIMATES",
                      "cases": synthetic_cases()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

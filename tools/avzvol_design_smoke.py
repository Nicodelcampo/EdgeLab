#!/usr/bin/env python3
"""Synthetic AVZVOL match smoke only. Research STOP before input access."""
import argparse
import json
from edgelab.kaggle.avzvol_design import FEATURES, plan_covariate_matches


def synthetic_fixture():
    def row(identity, minute, value):
        return {'event_id': identity, 'contract': 'SYNTHETIC-MNQ', 'session': '2026-01-05',
                'cell': 'SYNTHETIC-CELL', 'clock_bucket': 'SYNTHETIC-BUCKET', 'trend_sign': 1,
                'anchor_utc': f'2026-01-05T15:{minute:02d}:00Z',
                'feature_asof_utc': f'2026-01-05T15:{minute:02d}:00Z',
                'prewindow_complete': True, 'features': {f: value for f in FEATURES}}
    policy = {'schema': 'edgelab_avzvol_match_policy_v1', 'min_controls': 1, 'max_controls': 2,
              'minimum_separation_seconds': 1,
              'calipers': {f: .5 for f in FEATURES}, 'scales': {f: 1. for f in FEATURES}}
    return [row('SYNTHETIC-R1', 0, 1.), row('SYNTHETIC-R2-UNSUPPORTED', 1, 10.)], [
        row('SYNTHETIC-C1', 10, 1.1), row('SYNTHETIC-C2', 11, 1.2)], policy


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--purpose', choices=('synthetic', 'research'), default='synthetic')
    args = parser.parse_args(argv)
    if args.purpose == 'research':
        print(json.dumps({'status': 'STOP_AVZVOL_RESEARCH_NOT_IMPLEMENTED',
                          'research_authorized': False, 'inputs_opened': False}))
        return 2
    reals, controls, policy = synthetic_fixture()
    result = plan_covariate_matches(reals, controls, policy=policy, holdout_start='2026-10-01')
    result['fixture'] = 'SYNTHETIC_ONLY_NOT_MARKET_THRESHOLDS'
    print(json.dumps(result, allow_nan=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

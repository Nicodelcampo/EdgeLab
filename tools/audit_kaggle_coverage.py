#!/usr/bin/env python3
"""Full date/interval diagnostics, never calendar/liquidity certification.

Daily inventory includes private source identities and timestamp intervals. Keep
it local/private. Only publish the summary after reviewing disclosure policy.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.kaggle.coverage_inventory import audit_coverage


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for field in ('store','resolver','catalog','expected-manifest-sha256',
                  'expected-resolver-sha256','expected-catalog-sha256','out-dir'):
        p.add_argument('--'+field, required=True)
    args = vars(p.parse_args()); dest = Path(args.pop('out_dir'))
    if dest.exists(): raise ValueError('preserve previous evidence: output directory exists')
    summary, daily = audit_coverage(**args)
    dest.mkdir(parents=True, exist_ok=False)
    for name, value in [('summary.json', summary), ('private_daily_inventory.json', daily)]:
        with (dest/name).open('x') as f: json.dump(value, f, indent=2, allow_nan=False)
    print(json.dumps({'diagnostic_status':summary['status'], 'research_allowed':False}))
    return 0  # Successful diagnostics != research eligibility.


if __name__ == '__main__': raise SystemExit(main())

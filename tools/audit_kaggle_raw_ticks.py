#!/usr/bin/env python3
"""Structural canonical_tick_v1 QA only, never sanitation/liquidity approval."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.kaggle.raw_tick_audit import audit_canonical_tick_file


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--include-clock-diagnostics',action='store_true',
        help='Count 16:00-17:00 Chicago observations; NOT a reviewed maintenance calendar')
    for name in ('path','expected-sha256','instrument','contract','out-dir'):
        p.add_argument('--'+name,required=True)
    for name in ('expected-bytes','expected-rows'):
        p.add_argument('--'+name,required=True,type=int)
    args=vars(p.parse_args());dest=Path(args.pop('out_dir'))
    if dest.exists():raise ValueError('preserve previous evidence: output directory exists')
    report,totals=audit_canonical_tick_file(**args)
    dest.mkdir(parents=True,exist_ok=False)
    for name,value in [('summary.json',report),('private_session_totals.json',totals)]:
        with (dest/name).open('x') as f:json.dump(value,f,indent=2,allow_nan=False)
    print(json.dumps({'status':report['status'],'research_allowed':False}))
    return 2 if any(report['errors'].values()) else 0


if __name__=='__main__':raise SystemExit(main())

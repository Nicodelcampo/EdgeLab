#!/usr/bin/env python3
"""Structural QA only. Never emits sanitation/liquidity certification or permission."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.kaggle.aggregate_audit import audit_aggregate_store


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store',required=True);p.add_argument('--resolver',required=True)
    p.add_argument('--expected-manifest-sha256',required=True);p.add_argument('--expected-resolver-sha256',required=True)
    p.add_argument('--out',required=True,help='New JSON report, never overwrite previous QA')
    a=p.parse_args();out=Path(a.out)
    if out.exists():raise ValueError('report already exists; preserve previous evidence')
    report,_=audit_aggregate_store(store=a.store,resolver=a.resolver,
        expected_manifest_sha256=a.expected_manifest_sha256,expected_resolver_sha256=a.expected_resolver_sha256)
    with out.open('x') as f:json.dump(report,f,indent=2,allow_nan=False)
    print(json.dumps({'status':report['status'],'research_status':report['research_status'],'research_allowed':False}))
    return 2 if report['errors'] else 0

if __name__=='__main__':raise SystemExit(main())

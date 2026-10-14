#!/usr/bin/env python3
"""Check pinned eligibility metadata only. Never opens market-data source files.

PASS_METADATA_ONLY is not campaign authority, independent review or promotion.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.data.research_data_gate import DataEligibilityError, require_research_eligibility


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',required=True,help='JSON object: schema_version + request; externally approved hashes required')
    args=parser.parse_args()
    try:
        bundle=json.loads(Path(args.bundle).read_text())
        if not isinstance(bundle,dict) or bundle.get('schema_version')!='research_gate_request_v1' or not isinstance(bundle.get('request'),dict):
            raise DataEligibilityError('invalid request bundle')
        decision=require_research_eligibility(**bundle['request'])
    except (DataEligibilityError, TypeError, ValueError, OSError) as exc:
        print(json.dumps({'status':'BLOCKED_METADATA','reason':str(exc),
                          'market_data_read':False,'promotion_allowed':False}))
        return 2
    print(json.dumps({'status':'PASS_METADATA_ONLY','market_data_read':False,
                      'decision':decision},allow_nan=False))
    return 0

if __name__=='__main__':
    raise SystemExit(main())

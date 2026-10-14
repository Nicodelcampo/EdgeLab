#!/usr/bin/env python3
"""Validate target-free BT2A NQ Gate 1 design contracts; never reads outcomes."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from tools.bt2a_nq_gate1_contracts import load_json,power_missing,validate_macro_policy,validate_runner_contract

def main(argv=None):
 ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--require-frozen',action='store_true'); a=ap.parse_args(argv)
 paths={'macro':ROOT/'specs/bt2a_nq_gate1_macro_policy_v1.draft.json','power':ROOT/'specs/bt2a_nq_gate1_power_design_v1.draft.json','runner':ROOT/'specs/bt2a_nq_gate1_runner_contract_v1.draft.json'}
 missing=[]
 missing += validate_macro_policy(load_json(paths['macro']),a.require_frozen)
 missing += power_missing(load_json(paths['power']),a.require_frozen)
 missing += validate_runner_contract(load_json(paths['runner']))
 out={'schema_version':'bt2a_nq_gate1_contract_audit_v1','status':'PASS_CONTRACTS_COMPLETE' if not missing else 'NOT_READY','missing_or_unresolved':sorted(set(missing)),'OUTCOMES_ACCESSED':False,'FUTURE_PRICE_PATH_ACCESSED':False,'PNL_ACCESSED':False,'HOLDOUT_TOUCHED':False}
 print(json.dumps(out,indent=2,sort_keys=True)); return 0 if not missing else 2
if __name__=='__main__': raise SystemExit(main())

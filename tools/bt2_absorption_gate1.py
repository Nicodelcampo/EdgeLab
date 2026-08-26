#!/usr/bin/env python3
"""BT2Absorption Gate 1: target-free preflight and explicitly authorized run."""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path: sys.path.insert(0, str(REPO_ROOT))
from edgelab.research.bt2_gate1_preflight import git_state, load_json, run_preflight
AUTHORIZATION_TOKEN = "OPEN_GATE1_OUTCOMES_20260826"
DEFAULT_SPEC = REPO_ROOT / "specs/bt2_absorption_gate1_clean76_amendment_2026-08-26.json"
DEFAULT_SESSIONS = REPO_ROOT / "specs/bt2_absorption_gate1_clean76_sessions.json"
DEFAULT_INPUTS = REPO_ROOT / "specs/bt2_absorption_gate1_input_registry_v1.json"

def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n")
    os.replace(tmp,path)

def common(p):
    p.add_argument("--data-dir",type=Path,required=True); p.add_argument("--session-registry",type=Path,default=DEFAULT_SESSIONS)
    p.add_argument("--input-registry",type=Path,default=DEFAULT_INPUTS); p.add_argument("--output",type=Path,required=True)

def preflight(args):
    result=run_preflight(data_dir=args.data_dir,session_registry_path=args.session_registry,input_registry_path=args.input_registry,repo_root=REPO_ROOT,require_clean_git=not args.allow_dirty)
    atomic_json(args.output/"gate1_preflight.json",result); print(json.dumps(result,indent=2,ensure_ascii=False)); return 0

def run(args):
    if args.authorization != AUTHORIZATION_TOKEN: raise SystemExit("outcomes remain closed: exact --authorization token required")
    start=git_state(REPO_ROOT)
    if start["dirty"]: raise SystemExit("formal Gate 1 run requires a clean worktree")
    check=run_preflight(data_dir=args.data_dir,session_registry_path=args.session_registry,input_registry_path=args.input_registry,repo_root=REPO_ROOT,require_clean_git=True)
    atomic_json(args.output/"gate1_preflight.json",check)
    from edgelab.research.bt2_gate1_outcomes import run_gate1
    result=run_gate1(data_dir=args.data_dir,session_registry=load_json(args.session_registry),input_registry=load_json(args.input_registry),spec=load_json(args.spec),output_dir=args.output,code_provenance={"head_start":start["head"],"branch":start["branch"]})
    end=git_state(REPO_ROOT)
    if end["head"]!=start["head"] or end["dirty"]:
        result["status"]="INVALID_PROVENANCE"; result["promotion_eligible"]=False; result["code_provenance"].update(head_end=end["head"],dirty_end=end["dirty"]); atomic_json(args.output/"gate1_result.json",result); return 3
    print(json.dumps({"status":result["status"],"decision":result["decision"],"CAMPAIGN_OUTCOMES_OPENED":True,"EDGE_DECLARED":False},indent=2)); return 0

def parser():
    root=argparse.ArgumentParser(description=__doc__); sub=root.add_subparsers(dest="command",required=True)
    p=sub.add_parser("preflight"); common(p); p.add_argument("--allow-dirty",action="store_true")
    r=sub.add_parser("run"); common(r); r.add_argument("--spec",type=Path,default=DEFAULT_SPEC); r.add_argument("--authorization",required=True)
    return root

def main(argv=None):
    args=parser().parse_args(argv); return preflight(args) if args.command=="preflight" else run(args)
if __name__=="__main__": raise SystemExit(main())

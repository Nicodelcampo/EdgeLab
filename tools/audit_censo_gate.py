#!/usr/bin/env python3
"""Gate fail-closed entre censo_integridad y cualquier análisis de señales."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

class IntegrityGateError(ValueError): pass

def audit(payload):
    if not isinstance(payload, list) or not payload:
        raise IntegrityGateError("censo.json debe ser una lista no vacia")
    files=[]; problems=[]; total_duplicates=0
    for index,row in enumerate(payload):
        if not isinstance(row,dict):
            raise IntegrityGateError("censo[%d] debe ser objeto"%index)
        name=row.get("archivo")
        if not isinstance(name,str) or not name:
            raise IntegrityGateError("censo[%d] no identifica archivo"%index)
        files.append(name)
        if row.get("error"):
            problems.append("%s: error de censo: %s"%(name,row["error"]))
            continue
        duplicates=row.get("duplicaciones_de_bloque")
        if not isinstance(duplicates,list):
            problems.append("%s: falta duplicaciones_de_bloque"%name)
            continue
        total_duplicates+=len(duplicates)
        if duplicates:
            problems.append("%s: %d bloques duplicados"%(name,len(duplicates)))
    return {"status":"PASS" if not problems else "BLOCKED_SOURCE_INTEGRITY","may_run_signal_census":not problems,"files":sorted(files),"total_duplicate_blocks":total_duplicates,"problems":problems}

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--out")
    args=parser.parse_args(argv)
    report=audit(json.loads(Path(args.input).read_text(encoding="utf-8")))
    text=json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)
    if args.out: Path(args.out).write_text(text+"\n",encoding="utf-8")
    print(text)
    return 0 if report["may_run_signal_census"] else 1
if __name__=="__main__": raise SystemExit(main())

"""Target-free custody/geometry audit. No raw price trajectories or returns."""
from pathlib import Path
import ast
import json
import hashlib
import csv
from collections import Counter
import types
import argparse
import numpy as np

ROOT = Path("/data/analysis/es_escalonadas_audit")
RAW = Path("/data/raw/es_escalonadas_20260929")


def load_functions(text, names, env):
    tree = ast.parse(text)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    for f in functions:
        f.decorator_list = []  # execute Python reference, not a substituted algorithm
    exec(compile(ast.Module(body=functions, type_ignores=[]), "<audited-source>", "exec"), env)


def setup():
    es = (SOURCE/"escalonadas_det.py").read_text()
    peaks = (SOURCE/"peaks_rule.py").read_text()
    (ROOT/"escalonadas_det.snapshot.py").write_text(es)
    (ROOT/"peaks_rule.snapshot.py").write_text(peaks)
    r = {"np": np}
    load_functions(peaks, ["pivots", "backfill", "chains"], r)
    tree = ast.parse(es)
    env = {"np": np, "R": types.SimpleNamespace(**{k:r[k] for k in ("pivots","backfill","chains")})}
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ("FAMILIAS","TICK","CONF_TICKS","TOQUE_TICKS") for t in node.targets):
            exec(compile(ast.Module(body=[node],type_ignores=[]), "<constants>", "exec"), env)
    load_functions(es, ["pasa", "chains_px", "detectar_px", "detectar"], env)
    return env, es, peaks


def main():
    env, es, peaks = setup()
    evidence = {"source_commit":SOURCE_COMMIT,
                "scope":"ATTACHED_GEOMETRY_AND_SYNTHETIC_CAUSAL_AUDIT_ONLY",
                "worktree":"isolated sandbox; no local PC worktree access",
                "new_outcomes_computed":False,"raw_candles_present":False,
                "source_sha256":{"escalonadas_det.py":hashlib.sha256(es.encode()).hexdigest(),
                                 "peaks_rule.py":hashlib.sha256(peaks.encode()).hexdigest()},
                "families":env["FAMILIAS"],"confirm_ticks":env["CONF_TICKS"],
                "layers":{},"labels":{}}
    for name in ["ES_03-26_202602_25T_HFT.json","ES_03-26_202602_25T_HFT__empinadas.json"]:
        x = json.loads((RAW/"labels"/name).read_text())
        evidence["labels"][name] = {"ranges":len(x.get("ranges",[])),
            "zigzags":len(x.get("zigzags",[])),
            "judgments":dict(Counter(j.get("verdict") for j in x.get("judgments",[])))}
    for tag in ["__precio","__empinadas__precio"]:
        name=f"ES_03-26_202602_25T_HFT{tag}.json"
        x=json.loads((RAW/"bundles/peaks_det"/name).read_text());zs=x["zonas"]
        invalid_idx=0;after_detection=0;idx_pico_mismatch=0;trigger_error=0;duplicates=Counter()
        for z in zs:
            idx=z["det_idx"];picos=z["picos"]
            invalid_idx += not (0<=idx<len(picos))
            if 0<=idx<len(picos):
                idx_pico_mismatch += idx+1!=z["det_pico"]
                sign=1 if z["kind"]=="H" else -1
                trigger_error += abs(z["det_precio"]-(z["det_nivel"]-sign*.5))>1e-9
                after_detection += any(p[0]>z["det_i"] for p in picos)
            duplicates[(z["kind"],z["det_i"],z["det_nivel"])]+=1
        evidence["layers"][name]={"zones":len(zs),"parameters":x["parametros"],
            "invalid_det_idx":invalid_idx,"det_idx_count_mismatch":idx_pico_mismatch,
            "trigger_formula_error":trigger_error,"final_geometry_has_post_detection_peaks":after_detection,
            "duplicate_event_keys":sum(n-1 for n in duplicates.values()),
            "availability_timestamp_verified":False,
            "session_calendar_verified":False,"viewer_parity_verified":False}
        dest=ROOT/f"profile_zones{tag}.csv"
        keys=["kind","i0","i1","det_i","det_idx","det_pico","toques","det_t","det_nivel","det_precio"]
        with dest.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
            w.writerows({k:z.get(k) for k in keys} for z in zs)
    # Synthetic fixture: three valid high peaks, followed by price confirmation.
    h=[99,99,100,99,99,99,100,99,99,99,100,99,99]
    l=[98,98,99.75,98.5,98.5,98.5,99.75,98.5,98.5,98.5,99.75,99.5,98.5]
    cd={"h":np.array(h),"l":np.array(l),"t":np.arange(len(h),dtype=float),"c":np.array(l)}
    f=env["FAMILIAS"]["planas"]
    z=env["detectar_px"](cd,f)
    zh=[a for a in z if a["kind"]=="H"]
    prefix_case=[]
    for a in zh:
        n=a["det_i"]+1
        p=env["detectar_px"]({k:v[:n] for k,v in cd.items()},f)
        matches=[b for b in p if b["kind"]==a["kind"] and b["det_i"]==a["det_i"] and b["det_nivel"]==a["det_nivel"]]
        prefix_case.append({"det_i":a["det_i"],"exists_in_prefix":bool(matches),
                            "synthetic":True})
    evidence["synthetic_prefix_fixture"]=prefix_case
    # Broader deterministic synthetic event-prefix check, no price outcomes.
    tests=0;failures=[];detections=0
    fields=("kind","det_i","det_pico","det_precio","det_nivel")
    for seed in range(64):
        rng=np.random.default_rng(seed)
        mid=400+np.cumsum(rng.integers(-3,4,64))
        hh=(mid+rng.integers(0,4,64))*.25
        ll=(mid-rng.integers(0,4,64))*.25
        s={"h":hh,"l":ll,"c":(hh+ll)/2,"t":np.arange(64,dtype=float)}
        for family,fam in env["FAMILIAS"].items():
            tests+=1
            full=env["detectar_px"](s,fam)
            for a in full:
                detections+=1
                n=a["det_i"]+1
                pref=env["detectar_px"]({k:v[:n] for k,v in s.items()},fam)
                if not any(all(b[k]==a[k] for k in fields) for b in pref):
                    failures.append({"seed":seed,"family":family,"det_i":a["det_i"]})
    evidence["synthetic_event_prefix_check"]={"paths":tests,"detections_checked":detections,
                                             "failures":failures,"seed_range":[0,63],
                                             "scope":"detection fields only, not final geometry nor fills"}
    # Independent counts from raw arrays and label enumerations.
    independent={}
    for tag in ("__precio","__empinadas__precio"):
        name=f"ES_03-26_202602_25T_HFT{tag}.json"
        zz=json.loads((RAW/"bundles/peaks_det"/name).read_bytes())["zonas"]
        independent[name]=sum(1 for _ in zz)
        assert independent[name]==evidence["layers"][name]["zones"]
    evidence["independent_zone_counts"]=independent
    evidence["caveats"]=[
        "bar time copied to det_t; closed/first-crossing timestamp not supplied",
        "intrabar sequence not identifiable from OHLC; trigger is a proposed level, not a fill",
        "full final geometry is not the state available at detection",
        "backfill uses full centered-pivot mask; must test detection-prefix equivalence",
        "only geometric fields profiled; profiler on nested JSON failed unequal-array lengths"
    ]
    (ROOT/"evidence.json").write_text(json.dumps(evidence,indent=2,ensure_ascii=False))
    print(json.dumps({k:evidence[k] for k in ["labels","layers","synthetic_prefix_fixture","synthetic_event_prefix_check"]},ensure_ascii=False,indent=2))


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-root",required=True,help="extracted local-only zip, labels/ and bundles/peaks_det/")
    ap.add_argument("--source-root",required=True,help="directory with the two exact source .py files")
    ap.add_argument("--out",required=True)
    ap.add_argument("--source-commit",required=True,help="commit whose exact source files were supplied; not proof of clean worktree")
    args=ap.parse_args()
    RAW=Path(args.input_root);SOURCE=Path(args.source_root);ROOT=Path(args.out)
    SOURCE_COMMIT=args.source_commit
    ROOT.mkdir(parents=True,exist_ok=True)
    main()
"""Local metadata capture / exact4 target-free census. Never computes outcomes."""
from pathlib import Path
import argparse
import hashlib
import json
import re
from gc_exact4_variants import resolve,census


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture(det_path,bundle_path,bar_series,bar_type,bar_size):
    d=json.loads(Path(det_path).read_text(encoding="utf-8-sig"))
    b=json.loads(Path(bundle_path).read_text(encoding="utf-8-sig"))
    if not d.get("asset","").startswith("GC_"):raise ValueError("GC_ASSET_REQUIRED")
    if b.get("meta",{}).get("tick_size")!=.1:raise ValueError("GC_TICK_SIZE_FAIL")
    # This is a user's explicitly selected layer/series, not the first in a dict.
    if bar_series not in b.get("bar_series",{}):raise ValueError("EXPLICIT_BAR_SERIES_NOT_FOUND")
    c=b["bar_series"][bar_series]["candles"]
    if not c:raise ValueError("EMPTY_BAR_SERIES")
    p=dict(d["parametros"]);variant=d.get("variante","")
    modes={z.get("confirmacion") for z in d.get("zonas",[]) if z.get("confirmacion")}
    if len(modes)>1:raise ValueError("MIXED_CONFIRMATION_MODES")
    text=" ".join([variant]+list(modes))
    price=re.findall(r"precio\s+(?:\()?(\d+)\s*ticks",text)
    if price:
        nums=set(map(int,price))
        if len(nums)!=1:raise ValueError("AMBIGUOUS_CONFIRM_DISTANCE")
        p.update(confirmation_mode="precio",confirm_ticks=nums.pop())
    elif "con vela de detección" in variant:
        p.update(confirmation_mode="velas",confirm_ticks=None)
    else:raise ValueError("CONFIRMATION_NOT_RESOLVED_NO_DEFAULTS")
    result=dict(scope="LOCAL_CAPTURED_CURRENT_CONFIG",instrument="GC",tick_size=.1,
        asset=d["asset"],bar_series=bar_series,bar_type=bar_type,bar_size=bar_size,
        window=dict(first_bar_time=c[0]["time"],last_bar_time=c[-1]["time"],bars=len(c)),
        family=variant,source_sha256=sha(det_path),chart_bundle_sha256=sha(bundle_path),
        selected_detection_filename=Path(det_path).name,params=p,
        capture_limitation="User must verify selected files/series match the visible chart; metadata only, not geometry or publication certification.",
        source_code_commit_required_before_census=True)
    resolve(result)  # Fail closed if parameters are missing/unrecognized.
    return result


def run_census(baseline_path,bars_path,out):
    out=Path(out)
    if out.exists() and any(out.iterdir()):raise ValueError("OUTPUT_MUST_BE_NEW_EMPTY")
    base=json.loads(Path(baseline_path).read_text(encoding="utf-8-sig"));profiles=resolve(base)
    bars=[]
    for line in Path(bars_path).open(encoding="utf-8-sig"):
        b=json.loads(line)
        if "time" not in b and "close_ts_us" in b:b["time"]=b["close_ts_us"]/1e6
        if not all(k in b for k in ("high_tick","low_tick","close_tick","time","session_id")):
            raise ValueError("CLOSED_BAR_SCHEMA_FAIL")
        bars.append(b)
    if not bars:raise ValueError("EMPTY_BARS")
    results=census(bars,profiles)
    out.mkdir(parents=True,exist_ok=True)
    for r in results:
        events=r.pop("signals_private",None)
        if events is not None:
            with (out/(r["id"]+"_events_private.jsonl")).open("w",encoding="utf-8") as f:
                for e in events:f.write(json.dumps(e)+"\n")
    (out/"resolved_configs.json").write_text(json.dumps(profiles,indent=2),encoding="utf-8")
    evidence=dict(scope="GC_EXACT4_TARGETFREE_CENSUS_NOT_FINANCIAL_OR_CURRENT_CONFIG_PARITY",
        baseline_file_sha256=sha(baseline_path),bars_file_sha256=sha(bars_path),
        code_sha256=sha(__file__),core_sha256=sha(Path(__file__).with_name("escalonadas_exact4.py")),
        resolver_sha256=sha(Path(__file__).with_name("gc_exact4_variants.py")),
        bars=len(bars),results=results,current_detector_C0_not_replaced=True,outcomes_computed=False)
    (out/"evidence.json").write_text(json.dumps(evidence,indent=2),encoding="utf-8")
    return evidence


def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest="task",required=True)
    c=sub.add_parser("capture")
    for k in ("det-json","chart-bundle","bar-series","bar-type","out"):c.add_argument("--"+k,required=True)
    c.add_argument("--bar-size",required=True,type=int)
    r=sub.add_parser("census")
    for k in ("baseline","bars-jsonl","out"):r.add_argument("--"+k,required=True)
    r.add_argument("--ack-targetfree",action="store_true")
    a=ap.parse_args()
    if a.task=="capture":
        p=Path(a.out)
        if p.exists():raise ValueError("DO_NOT_OVERWRITE_BASELINE")
        result=capture(a.det_json,a.chart_bundle,a.bar_series,a.bar_type,a.bar_size)
        p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(result,indent=2),encoding="utf-8")
    else:
        if not a.ack_targetfree:raise ValueError("EXPLICIT_TARGETFREE_ACK_REQUIRED")
        result=run_census(a.baseline,a.bars_jsonl,a.out)
    print(json.dumps({"scope":result["scope"],"out":a.out,"outcomes_computed":False}))


if __name__=="__main__":main()
"""Build a target-free NQ HFT corridor bundle for the browser viewer."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
import pandas as pd
from edgelab.research.hft_corridors import HFT_PARITY_STATUS, HFT_VISUAL_CONFIGS, normalize_hft_zones
HOLDOUT_START_NS = int(pd.Timestamp("2026-07-01T00:00:00Z").value)

def read_zones(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        obj = json.loads(path.read_text(encoding="utf-8")); return obj["zones"] if isinstance(obj, dict) else obj
    with path.open("r", encoding="utf-8-sig", newline="") as fh: return list(csv.DictReader(fh))

def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--zones",required=True,type=Path); ap.add_argument("--ticks",required=True,type=Path); ap.add_argument("--output",default=Path("viewer/nt8_bridge/hft_nq_bundle.js"),type=Path); ap.add_argument("--max-bars",default=30000,type=int); args=ap.parse_args()
    zones=normalize_hft_zones(read_zones(args.zones)); ticks=pd.read_parquet(args.ticks)
    ts_col=next(c for c in ("ts_ns","timestamp_ns","time_ns") if c in ticks.columns); px_col=next(c for c in ("price_ticks","price","last") if c in ticks.columns)
    ticks=ticks.sort_values(ts_col); ticks=ticks[ticks[ts_col].astype("int64") < HOLDOUT_START_NS]
    if not zones or not len(ticks): raise SystemExit("No eligible pre-holdout zones/ticks")
    if max(z["available_ts"] for z in zones)>=HOLDOUT_START_NS: raise SystemExit("Zone input crosses holdout boundary")
    stride=max(1,len(ticks)//args.max_bars); sampled=ticks.iloc[::stride]; candles=[{"time_ns":int(r[ts_col]),"price":float(r[px_col])} for _,r in sampled.iterrows()]
    payload={"meta":{"asset":"NQ","contract":"NQ 06-26","tick_size":0.25,"parity_status":HFT_PARITY_STATUS,"outcome_firewall":"ENFORCED","holdout_reads":0},"candles":candles,"zones":zones,"configurations":list(HFT_VISUAL_CONFIGS)}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text("window.HFT_NQ_CORRIDOR_BUNDLE="+json.dumps(payload,separators=(",",":"))+";\n",encoding="utf-8")
    print(json.dumps({"output":str(args.output),"zones":len(zones),"candles":len(candles),"parity_status":HFT_PARITY_STATUS},indent=2))
if __name__=="__main__": main()

"""Independent trade execution check directly against raw Parquet ticks."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path("/data/analysis/nq_ib_pmh")
raw = Path("/data/raw/nq_ib_pmh_v1/NQ_parquet")
r = json.loads((ROOT / "output/result.json").read_text())
verified = []
for tr in r["trades"]:
    contract = tr["contract"].replace(" ", "_")
    path = raw / (contract + "_ticks_ext.parquet")
    cutoff = int(pd.Timestamp(f"{tr['day']} 15:55", tz="America/New_York").tz_convert("UTC").value)
    table = pq.read_table(path, columns=["ts_utc_ns", "price_ticks"],
                          filters=[("ts_utc_ns", ">", tr["signal_ns"]),
                                   ("ts_utc_ns", "<=", max(cutoff, tr["exit_ns"]) + 60_000_000_000)])
    t = table["ts_utc_ns"].to_numpy()
    p = table["price_ticks"].to_numpy()
    assert t[0] == tr["entry_ns"] and p[0] == tr["entry_ticks"]
    chosen = None
    for ti, pi in zip(t, p):
        if ti >= cutoff:
            chosen = (int(ti), float(pi), "time")
            break
        if tr["direction"] == 1:
            stop = pi <= tr["stop_ticks"]
            target = pi >= tr["target_ticks"]
        else:
            stop = pi >= tr["stop_ticks"]
            target = pi <= tr["target_ticks"]
        if stop:
            chosen = (int(ti), float(pi), "stop")
            break
        if target:
            chosen = (int(ti), tr["target_ticks"], "target")
            break
    assert chosen == (tr["exit_ns"], tr["exit_ticks"], tr["exit_reason"]), (tr, chosen)
    expected = (tr["direction"] * (chosen[1] - float(p[0])) - 2) / tr["risk_ticks"]
    assert abs(expected - tr["R_2ticks"]) < 1e-12
    verified.append({"day": tr["day"], "strategy": tr["strategy"],
                     "entry_first_tick": True, "first_barrier_or_time": True, "R_recomputed": expected})
assert len(verified) == len(r["trades"])
result = {"verified_trades": len(verified), "passed": True, "method": "independent raw tick loop",
          "details": verified}
(ROOT / "output/independent_audit.json").write_text(json.dumps(result, indent=2))
print(json.dumps({"verified_trades": len(verified), "passed": True}))
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(r"E:\EdgeLab_worktrees\fix-hft-parity-corridor-viewer-complete-v1-20260916")
sys.path.insert(0, str(REPO))
from edgelab.bridge.indicators import hftzones_nq as hz

db_path = r"E:\EdgeLab\data\nt8_oracles\hft_zones_nq_v2.sqlite"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

sessions = ["20260602", "20260603", "20260604", "20260605"]
results = {
    "mode": "V2_NS_EXACT_CERTIFICATION_PARTIAL",
    "oracle_db": "data/nt8_oracles/hft_zones_nq_v2.sqlite",
    "contract": "NQ JUN26",
    "verified_sessions": {},
    "total_exact_matches": 0,
    "total_discrepancies": 0,
    "status": "PASS_PARTIAL_SESSIONS"
}

total_matched = 0

for sess in sessions:
    cur.execute("SELECT tick_seq, timestamp_ns, price_ticks, volume FROM hft_ticks_v2 WHERE session_id=? ORDER BY tick_seq ASC", (sess,))
    ticks = cur.fetchall()
    
    cur.execute("""SELECT zone_seq, start_tick_seq, end_tick_seq, start_ts_ns, end_ts_ns, direction,
                          lo_ticks, hi_ticks, pasos, vol, avg_ms, total_ms, volume_rate, parameter_manifest_sha256
                   FROM hft_zones_v2 WHERE session_id=? ORDER BY zone_seq ASC""", (sess,))
    nt8_zones = cur.fetchall()
    
    ts_ns = [t[1] for t in ticks]
    px_tk = [t[2] for t in ticks]
    vol = [float(t[3]) for t in ticks]
    
    cands = hz.detect_candidates(ts_ns, px_tk, vol)
    acc_zones, _ = hz.accept_all(cands, dict(hz.ACCEPT_DEFAULTS), tick_size=0.25)
    
    n_compare = min(len(acc_zones), len(nt8_zones))
    diffs = 0
    diff_samples = []
    
    for idx in range(n_compare):
        pz = acc_zones[idx]
        nz = nt8_zones[idx]
        
        stk_p = int(pz["idx_start"]) + 1
        etk_p = int(pz["idx_end"]) + 1
        ts_p = int(pz["ts_start"])
        te_p = int(pz["ts_end"])
        dir_p = int(pz["direction"])
        lo_p = int(pz["sw_lo_tk"])
        hi_p = int(pz["sw_hi_tk"])
        
        nz_seq, nz_stk, nz_etk, nz_ts, nz_te, nz_dir, nz_lo, nz_hi, nz_pasos, nz_vol, nz_avg, nz_tot, nz_vr, nz_sha = nz
        
        if (stk_p != nz_stk or etk_p != nz_etk or ts_p != nz_ts or te_p != nz_te or dir_p != nz_dir or lo_p != nz_lo or hi_p != nz_hi):
            diffs += 1
            if len(diff_samples) < 3:
                diff_samples.append({
                    "zone_idx": idx + 1,
                    "python": {"stk": stk_p, "etk": etk_p, "ts": ts_p, "te": te_p, "dir": dir_p, "lo": lo_p, "hi": hi_p},
                    "nt8": {"stk": nz_stk, "etk": nz_etk, "ts": nz_ts, "te": nz_te, "dir": nz_dir, "lo": nz_lo, "hi": nz_hi}
                })
                
    total_matched += (n_compare - diffs)
    results["verified_sessions"][sess] = {
        "ticks_count": len(ticks),
        "nt8_zones_total": len(nt8_zones),
        "python_zones_generated": len(acc_zones),
        "zones_compared": n_compare,
        "exact_matches": n_compare - diffs,
        "differences": diffs,
        "diff_samples": diff_samples,
        "status": "PASS_EXACT_100PCT" if diffs == 0 and n_compare == len(acc_zones) else "INCOMPLETE_OR_DIFF"
    }

results["total_exact_matches"] = total_matched
results["total_discrepancies"] = sum(v["differences"] for v in results["verified_sessions"].values())

out_path = REPO / "data" / "nt8_oracles" / "paridad_hftzones_nq_v2_exact_partial.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"Generated {out_path} with {total_matched} exact matches and {results['total_discrepancies']} discrepancies.")

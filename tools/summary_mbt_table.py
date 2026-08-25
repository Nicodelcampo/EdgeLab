#!/usr/bin/env python3
import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.analyze_mbt_apriori import parse_export, percentile
import numpy as np
import pandas as pd
from collections import defaultdict
import hashlib
import json

files = sorted(Path("E:/DatosNT8/mbt_apriori").glob("mbt_export__TW*.csv"))

summary_rows = []
manifest = []

for f in files:
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    sha = h.hexdigest()
    size = f.stat().st_size

    meta, bars, scores, traps, zones, fills = parse_export(f)
    tw = int(meta.get("tape_window", 25))

    bkt_by_session = defaultdict(int)
    for s in scores:
        if s.get("residual") == "False":
            bkt_by_session[s["td"]] += 1

    all_sessions = sorted(set(s["td"] for s in scores))
    front_sessions = [td for td in all_sessions if bkt_by_session[td] >= 100]
    preroll_sessions = [td for td in all_sessions if 0 < bkt_by_session[td] < 100]

    bkt_counts_front = [bkt_by_session[td] for td in front_sessions]

    a_scores_series = [(int(s["bar"]), s.get("residual") == "True", float(s["a_score"]), s["td"]) for s in scores]

    def get_thr_map(q, min_hist=100, lookback=500):
        thr_by_bar = {}
        ring_cap = lookback
        pos = 0
        count = 0
        ring_buf = [0.0] * ring_cap
        for bar, res, score, td in a_scores_series:
            if count >= min_hist:
                s_arr = ring_buf[:count] if count < ring_cap else ring_buf
                thr_by_bar[bar] = percentile(s_arr, q)
            else:
                thr_by_bar[bar] = float("nan")
            if not res:
                ring_buf[pos] = score
                pos = (pos + 1) % ring_cap
                if count < ring_cap:
                    count += 1
        return thr_by_bar

    burnin_bar = None
    burnin_td = None
    cnt = 0
    for bar, res, score, td in a_scores_series:
        if cnt >= 100:
            burnin_bar = bar
            burnin_td = td
            break
        if not res:
            cnt += 1

    manifest.append({
        "file": f.name,
        "sha256": sha,
        "bytes": size,
        "tw": tw,
        "n_bars": len(bars),
        "n_scores": len(scores),
        "n_traps": len(traps),
        "n_zones": len(zones),
        "n_fills": len(fills),
        "first_td": all_sessions[0],
        "last_td": all_sessions[-1],
        "total_sessions": len(all_sessions),
        "front_sessions_count": len(front_sessions),
        "burnin_bar_100": burnin_bar,
        "burnin_td_100": burnin_td,
    })

    q_stats = {}
    for q in [90.0, 95.0, 97.5, 99.0]:
        thr_map = get_thr_map(q)
        ev_front = defaultdict(int)
        tot_ev = 0
        for tr in traps:
            bar = int(tr["bar"])
            thr = thr_map.get(bar, float("nan"))
            if np.isnan(thr) or float(tr["a_score"]) < thr or tr.get("side_match") != "True":
                continue
            if int(tr.get("run_rows", 0)) < 2 or float(tr.get("run_frac", 0.0)) < 0.20:
                continue
            tot_ev += 1
            if tr["td"] in front_sessions:
                ev_front[tr["td"]] += 1
        counts = [ev_front[td] for td in front_sessions]
        pct = (tot_ev / sum(bkt_counts_front) * 100) if sum(bkt_counts_front) else 0.0
        q_stats[q] = {
            "tot": tot_ev,
            "pct": pct,
            "med": float(np.median(counts)) if counts else 0.0,
            "p25": float(np.percentile(counts, 25)) if counts else 0.0,
            "p75": float(np.percentile(counts, 75)) if counts else 0.0,
            "p10": float(np.percentile(counts, 10)) if counts else 0.0,
            "p90": float(np.percentile(counts, 90)) if counts else 0.0,
            "max": int(max(counts)) if counts else 0,
            "min": int(min(counts)) if counts else 0,
        }

    thr_map_95 = get_thr_map(95.0)
    rows_stats = {}
    for r_cut in [1, 2, 3]:
        tot = sum(
            1
            for tr in traps
            if not np.isnan(thr_map_95.get(int(tr["bar"]), float("nan")))
            and float(tr["a_score"]) >= thr_map_95[int(tr["bar"])]
            and tr.get("side_match") == "True"
            and int(tr.get("run_rows", 0)) >= r_cut
            and float(tr.get("run_frac", 0.0)) >= 0.20
        )
        rows_stats[r_cut] = tot

    frac_stats = {}
    for f_cut in [0.10, 0.20, 0.30]:
        tot = sum(
            1
            for tr in traps
            if not np.isnan(thr_map_95.get(int(tr["bar"]), float("nan")))
            and float(tr["a_score"]) >= thr_map_95[int(tr["bar"])]
            and tr.get("side_match") == "True"
            and int(tr.get("run_rows", 0)) >= 2
            and float(tr.get("run_frac", 0.0)) >= f_cut
        )
        frac_stats[f_cut] = tot

    summary_rows.append({
        "tw": tw,
        "bkt_med_front": float(np.median(bkt_counts_front)),
        "bkt_p25_front": float(np.percentile(bkt_counts_front, 25)),
        "bkt_p75_front": float(np.percentile(bkt_counts_front, 75)),
        "q_stats": q_stats,
        "rows_stats": rows_stats,
        "frac_stats": frac_stats,
    })

print("=== MANIFEST ===")
print(json.dumps(manifest, indent=2))

print("\n=== COMPARATIVA TW ===")
for s in summary_rows:
    tw = s["tw"]
    print(f"\n--- TW = {tw} ---")
    print(f"Cubetas/sesion front (mediana [p25-p75]): {s['bkt_med_front']:.1f} [{s['bkt_p25_front']:.1f} - {s['bkt_p75_front']:.1f}]")
    print("Tasa de eventos por q (MinStackedRows=2, MinTrapFrac=0.20):")
    for q, st in s["q_stats"].items():
        ratio = st["p90"] / max(st["p10"], 0.1)
        print(f"  q={q:4.1f}: {st['tot']:4d} zonas, {st['pct']:5.2f}% cubetas, med/ses={st['med']:4.1f} [p25={st['p25']:4.1f}, p75={st['p75']:4.1f}, p90/p10={ratio:.1f}x]")
    r1 = s["rows_stats"][1]
    r2 = s["rows_stats"][2]
    r3 = s["rows_stats"][3]
    print(f"Sensibilidad MinStackedRows (q=95): 1={r1}, 2={r2}, 3={r3} (ratio 1/2={r1/max(r2,1):.2f}x, ratio 2/3={r2/max(r3,1):.2f}x)")
    f1 = s["frac_stats"][0.10]
    f2 = s["frac_stats"][0.20]
    f3 = s["frac_stats"][0.30]
    print(f"Sensibilidad MinTrapFrac (q=95): 0.1={f1}, 0.2={f2}, 0.3={f3} (ratio 0.1/0.3={f1/max(f3,1):.2f}x)")

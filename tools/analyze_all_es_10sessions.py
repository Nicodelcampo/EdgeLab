#!/usr/bin/env python3
"""Analiza los 8 exports de ES sobre las 10 sesiones completas."""
import sys
from pathlib import Path
import json
import hashlib
from collections import defaultdict
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.analyze_mbt_apriori import parse_export, percentile

DIR = Path("E:/DatosNT8/es_apriori")

def analyze_all():
    files = sorted(DIR.glob("es_export__*.csv"))
    print(f"[*] Analizando {len(files)} exports en {DIR}...")
    
    manifest = []
    results = []
    
    for f in files:
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            for c in iter(lambda: fh.read(1 << 20), b""):
                h.update(c)
        sha = h.hexdigest()
        
        meta, bars, scores, traps, zones, fills = parse_export(f)
        
        tw = int(meta.get("tape_window", 25))
        min_rows_native = int(meta.get("min_stacked_rows", 2))
        tpr_native = int(meta.get("ticks_per_row", 1))
        min_trap_frac_native = float(meta.get("min_trap_frac", 0.20))
        
        # Group bars and scores by trade date
        td_bars = defaultdict(int)
        for b in bars:
            td_bars[b["td"]] += 1
            
        sessions = sorted(td_bars.keys())
        
        # Calculate thresholds by bar
        # Vectorized ring lookback
        lookback = int(meta.get("absorption_lookback", 500))
        min_hist = int(meta.get("min_history", 200))
        
        score_vals = [float(s["a_score"]) for s in scores if s.get("residual") == "False"]
        
        trap_bars = {int(tr["bar"]) for tr in traps}
        q_thr_map = {90.0: {}, 95.0: {}, 97.5: {}, 99.0: {}}
        ring = []
        for s in scores:
            b_idx = int(s["bar"])
            val = float(s["a_score"])
            if s.get("residual") == "False":
                ring.append(val)
                if len(ring) > lookback:
                    ring.pop(0)
            if b_idx in trap_bars:
                if len(ring) >= min_hist:
                    for q in [90.0, 95.0, 97.5, 99.0]:
                        q_thr_map[q][b_idx] = percentile(ring, q)
                else:
                    for q in [90.0, 95.0, 97.5, 99.0]:
                        q_thr_map[q][b_idx] = float("nan")
            
        # Evaluate event counts per session and total
        q_eval = {}
        for q in [90.0, 95.0, 97.5, 99.0]:
            thr_map = q_thr_map[q]
            ses_counts = defaultdict(int)
            total_pass = 0
            for tr in traps:
                b_idx = int(tr["bar"])
                thr = thr_map.get(b_idx, float("nan"))
                if np.isnan(thr) or float(tr["a_score"]) < thr or tr.get("side_match") != "True":
                    continue
                # Native run_rows and run_frac
                if int(tr.get("run_rows", 0)) < min_rows_native or float(tr.get("run_frac", 0.0)) < min_trap_frac_native:
                    continue
                total_pass += 1
                ses_counts[tr["td"]] += 1
                
            counts_list = [ses_counts[s] for s in sessions]
            bkt_counts = [td_bars[s] for s in sessions]
            pct = (total_pass / sum(bkt_counts) * 100) if sum(bkt_counts) else 0.0
            
            q_eval[q] = {
                "total": total_pass,
                "pct_cubetas": pct,
                "by_session": dict(ses_counts),
                "med": float(np.median(counts_list)),
                "p25": float(np.percentile(counts_list, 25)),
                "p75": float(np.percentile(counts_list, 75)),
                "min": int(min(counts_list)),
                "max": int(max(counts_list))
            }
            
        manifest.append({
            "file": f.name,
            "sha256": sha,
            "bytes": f.stat().st_size,
            "tw": tw,
            "min_stacked_rows": min_rows_native,
            "ticks_per_row": tpr_native,
            "n_bars": len(bars),
            "n_traps": len(traps),
            "n_zones": len(zones),
            "total_sessions": len(sessions),
            "first_td": sessions[0] if sessions else None,
            "last_td": sessions[-1] if sessions else None,
            "sessions": sessions
        })
        
        results.append({
            "file": f.name,
            "tw": tw,
            "rows": min_rows_native,
            "tpr": tpr_native,
            "sessions": sessions,
            "bkt_by_session": dict(td_bars),
            "bkt_med": float(np.median(list(td_bars.values()))),
            "q_eval": q_eval
        })
        
    print("\n=== MANIFEST ===")
    print(json.dumps(manifest, indent=2))
    
    print("\n=== TABLA COMPARATIVA COMPLETA (10 SESIONES) ===")
    for r in results:
        print(f"\n=======================================================")
        print(f"Export: {r['file']}")
        print(f"Config: TW={r['tw']}, MinStackedRows={r['rows']}, TicksPerRow={r['tpr']}")
        print(f"Cubetas/sesion: Mediana={r['bkt_med']:.1f} (Rango: {min(r['bkt_by_session'].values())} - {max(r['bkt_by_session'].values())})")
        print(f"-------------------------------------------------------")
        print(f"Desglose por q (tasa global y medianas por sesion):")
        for q in [90.0, 95.0, 97.5, 99.0]:
            qe = r["q_eval"][q]
            print(f"  q={q:4.1f}: Total={qe['total']:4d} zonas ({qe['pct_cubetas']:5.2f}% cubetas) | Med/ses={qe['med']:4.1f} [p25={qe['p25']:4.1f}, p75={qe['p75']:4.1f}, min={qe['min']}, max={qe['max']}]")
        print(f"-------------------------------------------------------")
        print(f"Conteo sesion por sesion (q=95.0):")
        q95 = r["q_eval"][95.0]
        for s in r["sessions"]:
            print(f"  Sesion {s}: {q95['by_session'].get(s, 0):3d} zonas (de {r['bkt_by_session'][s]:5d} cubetas)")

if __name__ == '__main__':
    analyze_all()

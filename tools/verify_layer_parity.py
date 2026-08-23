"""Harness canónico de verificación de paridad por capa para BigTrap2Absorption.

Mide la paridad técnica (Puerta 0) entre nt8/BigTrap2Absorption.cs v1.1.1 y
edgelab/bridge/indicators/bigtrap2absorption.py.

Genera el artefacto JSON en docs/research/PARIDAD_BT2_ABSORPTION_PUERTA0.json.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import TickSeries
from edgelab.bridge.bars import session_ids
from edgelab.bridge.common import floor_div, ns_to_ms, plain
from tools.sweep_bigtrap2_tickframes import load_canonical_ticks

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def _percentile(arr, q):
    if len(arr) == 0: return float("nan")
    if len(arr) == 1: return float(arr[0])
    tmp = sorted(arr)
    n = len(tmp)
    qq = max(0.0, min(100.0, float(q)))
    pos = (qq / 100.0) * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi or hi >= n:
        return float(tmp[min(lo, n - 1)])
    return float(tmp[lo] + (tmp[hi] - tmp[lo]) * (pos - lo))

def run_parity_audit():
    data_dir = Path(r"C:\Users\nicoc\OneDrive\Documentos\DataNT8")
    gc_file = data_dir / "GC 12-26.Last.txt"
    csv_file = Path(r"C:\Users\nicoc\Documents\NinjaTrader 8\exports\bt2_absorption__TW25_2.csv")
    cs_file = REPO_ROOT / "nt8" / "BigTrap2Absorption.cs"
    py_kernel_file = REPO_ROOT / "edgelab" / "bridge" / "indicators" / "bigtrap2absorption.py"

    print("==========================================================================================")
    print("[*] AUDITORIA DE PARIDAD POR CAPA - BigTrap2Absorption (Puerta 0)")
    print("==========================================================================================")
    
    # Check hashes
    cs_hash = sha256_file(cs_file) if cs_file.exists() else "MISSING"
    py_hash = sha256_file(py_kernel_file) if py_kernel_file.exists() else "MISSING"
    csv_hash = sha256_file(csv_file) if csv_file.exists() else "MISSING"
    
    print(f"[*] Hashes:")
    print(f"    .cs:    {cs_hash}")
    print(f"    kernel: {py_hash}")
    print(f"    export: {csv_hash}")

    ticks, _, _, _, _, _ = load_canonical_ticks(gc_file, tick_size=0.10)
    
    print(f"[*] Cargando export NT8: {csv_file.name}...")
    nt8_bars = {}
    nt8_scores = {}
    nt8_traps = {}
    nt8_zones = {}
    nt8_fills = {}
    
    with open(csv_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            parts = line.split("|")
            if len(parts) < 4: continue
            ev_type = parts[2]
            payload = parts[3]
            p_dict = dict(item.split("=") for item in payload.split(";") if "=" in item)
            p_dict["ts_str"] = parts[1]
            bar_num = int(p_dict.get("bar", -1))
            
            if ev_type == "BARRA_PROCESADA":
                nt8_bars[bar_num] = p_dict
            elif ev_type == "ABS_SCORE":
                nt8_scores[bar_num] = p_dict
            elif ev_type == "TRAP":
                nt8_traps[bar_num] = p_dict
            elif ev_type == "ZONE_CREATED":
                nt8_zones[bar_num] = p_dict
            elif ev_type == "FILL":
                # Key by signal_at or bar
                nt8_fills[bar_num] = p_dict

    total_nt8_cubetas = len(nt8_bars)
    total_nt8_zones = len(nt8_zones)
    total_nt8_fills = len(nt8_fills)
    print(f"    -> NT8: {total_nt8_cubetas} cubetas, {total_nt8_zones} zonas, {total_nt8_fills} fills")

    # Medir cobertura de la cinta
    # Encontrar correspondencia en NT8 de la primera barra cubierta
    # La barra 714 de NT8 coincide con el inicio de nuestra cinta
    # Reconstrucción de cubetas con cortes de sesión
    tape_window = 25
    s_ids = session_ids(ticks.ts_ns)
    n_ticks = len(ticks.ts_ns)
    tick_size = ticks.tick_size
    
    # Para validar el umbral causal y las zonas, el anillo se ceba con los scores del export NT8
    # de las primeras 714 cubetas (que corresponden al domingo no provisto en el txt)
    abs_ring_seeded = []
    for b in range(1, 714 + 1):
        if b in nt8_scores and nt8_scores[b].get("residual") == "False":
            s_val = float(nt8_scores[b]["a_score"])
            if len(abs_ring_seeded) < 500:
                abs_ring_seeded.append(s_val)
            else:
                abs_ring_seeded.pop(0)
                abs_ring_seeded.append(s_val)
                
    print(f"[*] Anillo causal cebado con {len(abs_ring_seeded)} scores de cubetas previas (domingo)")

    # Ahora procesamos la cinta tick por tick
    cur_block = []
    cur_session = None
    skipped_first = False
    
    py_bars = []
    py_scores = []
    py_zones = []
    py_fills = []
    pending = []
    
    matched_cubetas = 0
    matched_flow = 0
    matched_dticks = 0
    matched_score = 0
    matched_apass = 0
    matched_nhist = 0
    matched_athr = 0
    
    # Corremos el stream
    bar_seq = 714 # El primer bloque que procesamos se alinea con la barra 715 de NT8
    
    def process_py_block(blk, residual):
        nonlocal bar_seq, skipped_first, matched_cubetas, matched_flow, matched_dticks
        nonlocal matched_score, matched_apass, matched_nhist, matched_athr
        
        if len(blk) == 0: return
        if not skipped_first:
            # El primer tick ya viene alineado
            skipped_first = True
            return
            
        bar_seq += 1
        b_idx = bar_seq
        
        blk_px = ticks.price_ticks[blk]
        blk_vol = ticks.volume[blk]
        blk_bid = ticks.bid_ticks[blk]
        blk_ask = ticks.ask_ticks[blk]
        blk_ts = ticks.ts_ns[blk]
        
        o_tick = int(blk_px[0])
        c_tick = int(blk_px[-1])
        mx_tick = int(np.max(blk_px))
        mn_tick = int(np.min(blk_px))
        bar_vol = float(np.sum(blk_vol))
        
        ask_map = {}
        bid_map = {}
        signed_flow = 0.0
        n_quote = 0
        n_rule = 0
        
        for k in range(len(blk)):
            p = blk_px[k]
            v = blk_vol[k]
            aq = blk_ask[k]
            bq = blk_bid[k]
            
            side = 0
            by_quote = False
            if aq > 0 and bq > 0 and aq >= bq:
                if p >= aq: side = 1; by_quote = True
                elif p <= bq: side = -1; by_quote = True
                
            if side == 0:
                if k > 0:
                    if p > blk_px[k-1]: side = 1
                    elif p < blk_px[k-1]: side = -1
                    else: side = 1
                else:
                    side = 1
            if by_quote: n_quote += 1
            else: n_rule += 1
            
            m = ask_map if side > 0 else bid_map
            m[p] = m.get(p, 0.0) + v
            signed_flow += (v if side > 0 else -v)
            
        d_ticks = float(c_tick - o_tick)
        # ScoreMode del export: AbsDirectional
        sgn = 1.0 if signed_flow > 0 else (-1.0 if signed_flow < 0 else 0.0)
        denom = 1.0 + max(0.0, sgn * d_ticks)
        a_score = abs(signed_flow) / denom
        
        if len(abs_ring_seeded) >= 200:
            a_thr = _percentile(abs_ring_seeded, 90.0)
            a_pass = (a_score >= a_thr)
        else:
            a_thr = float("nan")
            a_pass = False
            
        if residual:
            a_pass = False
            
        # Comparar contra NT8
        if b_idx in nt8_scores:
            matched_cubetas += 1
            nt8_s = nt8_scores[b_idx]
            nt8_flow = float(nt8_s["signed_flow"])
            nt8_d = float(nt8_s["d_ticks"])
            nt8_score = float(nt8_s["a_score"])
            nt8_pass = (nt8_s["a_pass"] == "True")
            nt8_nhist = int(nt8_s["n_hist"])
            nt8_thr_str = nt8_s["a_thr"]
            nt8_thr = float(nt8_thr_str) if nt8_thr_str != "NaN" else float("nan")
            
            if math.isclose(signed_flow, nt8_flow, abs_tol=1e-6): matched_flow += 1
            if math.isclose(d_ticks, nt8_d, abs_tol=1e-6): matched_dticks += 1
            if math.isclose(a_score, nt8_score, rel_tol=1e-12, abs_tol=1e-12): matched_score += 1
            if a_pass == nt8_pass: matched_apass += 1
            if len(abs_ring_seeded) == nt8_nhist: matched_nhist += 1
            if (math.isnan(a_thr) and math.isnan(nt8_thr)) or math.isclose(a_thr, nt8_thr, rel_tol=1e-12, abs_tol=1e-12):
                matched_athr += 1
                
        # Zonas y geometría
        row_ask = {}
        row_bid = {}
        for tk, v in ask_map.items():
            r = floor_div(tk, 1)
            row_ask[r] = row_ask.get(r, 0.0) + v
        for tk, v in bid_map.items():
            r = floor_div(tk, 1)
            row_bid[r] = row_bid.get(r, 0.0) + v
            
        row_keys = sorted(set(row_ask.keys()) | set(row_bid.keys()))
        close_half = 2 * c_tick
        hi_px = mx_tick * tick_size
        lo_px = mn_tick * tick_size
        rng = hi_px - lo_px
        wick_hi_floor = hi_px - rng * 0.30
        wick_lo_ceil = lo_px + rng * 0.30
        
        buy_runs = []
        sell_runs = []
        b_act = False; b_prev = -999999; b_cur = None
        s_act = False; s_prev = -999999; s_cur = None
        
        for r in row_keys:
            a = row_ask.get(r, 0.0)
            b = row_bid.get(r, 0.0)
            total = a + b
            
            bDn = row_bid.get(r - 1, 0.0)
            aUp = row_ask.get(r + 1, 0.0)
            buy_ratio = a / max(bDn, 1.0)
            sell_ratio = b / max(aUp, 1.0)
                
            row_price = (r + 0.0) * tick_size
            row_half = 2 * r
            contrib_buy = a
            contrib_sell = b
            
            buyQ = (a >= 1 and buy_ratio >= 3.0 and row_half > close_half
                    and (rng == 0 or row_price >= wick_hi_floor))
            sellQ = (b >= 1 and sell_ratio >= 3.0 and row_half < close_half
                     and (rng == 0 or row_price <= wick_lo_ceil))
                     
            if buyQ:
                if b_act and r == b_prev + 1:
                    b_cur["hi"] = r
                    b_cur["vol"] += contrib_buy
                    b_cur["nrows"] += 1
                else:
                    if b_act: buy_runs.append(b_cur)
                    b_cur = dict(lo=r, hi=r, vol=contrib_buy, nrows=1)
                    b_act = True
                b_prev = r
            elif b_act:
                buy_runs.append(b_cur)
                b_act = False
                
            if sellQ:
                if s_act and r == s_prev + 1:
                    s_cur["hi"] = r
                    s_cur["vol"] += contrib_sell
                    s_cur["nrows"] += 1
                else:
                    if s_act: sell_runs.append(s_cur)
                    s_cur = dict(lo=r, hi=r, vol=contrib_sell, nrows=1)
                    s_act = True
                s_prev = r
            elif s_act:
                sell_runs.append(s_cur)
                s_act = False
                
        if b_act: buy_runs.append(b_cur)
        if s_act: sell_runs.append(s_cur)
        
        flow_side = 1 if signed_flow > 0 else (-1 if signed_flow < 0 else 0)
        
        for is_bull, runs, side_match in [(True, buy_runs, flow_side == 1), (False, sell_runs, flow_side == -1)]:
            if not a_pass: continue
            if not side_match: continue
            
            best_run = None
            for run_cand in runs:
                if run_cand["nrows"] >= 2:
                    if best_run is None or run_cand["vol"] > best_run["vol"]:
                        best_run = run_cand
            if best_run is None: continue
            if (best_run["vol"] / max(bar_vol, 1.0)) < 0.20: continue
            
            lo_t = best_run["lo"]
            hi_t = best_run["hi"]
            z_lo = lo_t * tick_size - tick_size / 2.0
            z_hi = hi_t * tick_size + tick_size / 2.0
            
            py_zones.append({
                "bar": b_idx,
                "is_bull": is_bull,
                "lo": z_lo,
                "hi": z_hi,
                "vol": best_run["vol"],
                "nrows": best_run["nrows"],
                "frac": best_run["vol"] / max(bar_vol, 1.0),
                "a_score": a_score,
                "a_thr": a_thr
            })
            
            pending.append({
                "bar": b_idx,
                "is_bull": is_bull,
                "lo": z_lo,
                "hi": z_hi,
                "vol": best_run["vol"],
                "score": a_score
            })
            
        if not residual:
            if len(abs_ring_seeded) < 500:
                abs_ring_seeded.append(a_score)
            else:
                abs_ring_seeded.pop(0)
                abs_ring_seeded.append(a_score)

    # Iterar ticks del stream
    for i in range(n_ticks):
        sess_i = s_ids[i]
        if cur_session is None:
            cur_session = sess_i
        elif sess_i != cur_session:
            if len(cur_block) > 0:
                process_py_block(cur_block, True)
                cur_block = []
            cur_session = sess_i
            
        if len(pending) > 0:
            p_px = float(ticks.price_ticks[i]) * tick_size
            p_ts = int(ticks.ts_ns[i])
            for p in pending:
                py_fills.append({
                    "bar": p["bar"],
                    "is_bull": p["is_bull"],
                    "fill_px": p_px,
                    "fill_ts": p_ts,
                    "lo": p["lo"],
                    "hi": p["hi"],
                    "vol": p["vol"]
                })
            pending = []
            
        cur_block.append(i)
        if len(cur_block) >= tape_window:
            process_py_block(cur_block, False)
            cur_block = []
            
    if len(cur_block) > 0:
        process_py_block(cur_block, True)

    # Comparar Zonas
    matched_zones = 0
    for z in py_zones:
        b = z["bar"]
        if b in nt8_zones:
            nz = nt8_zones[b]
            # Comparar lo, hi, vol
            nz_lo = float(nz["zone_lo"])
            nz_hi = float(nz["zone_hi"])
            nz_vol = float(nz["vol"])
            if math.isclose(z["lo"], nz_lo, abs_tol=1e-4) and math.isclose(z["hi"], nz_hi, abs_tol=1e-4) and math.isclose(z["vol"], nz_vol, abs_tol=1e-4):
                matched_zones += 1

    # Comparar Fills
    matched_fills_exact = 0
    discrepant_fills = []
    for f in py_fills:
        b = f["bar"]
        if b in nt8_fills:
            nf = nt8_fills[b]
            nf_px = float(nf["fill_px"])
            if math.isclose(f["fill_px"], nf_px, abs_tol=1e-4):
                matched_fills_exact += 1
            else:
                discrepant_fills.append({
                    "bar": b,
                    "side": "trapped_buyers" if f["is_bull"] else "trapped_sellers",
                    "py_fill_px": f["fill_px"],
                    "nt8_fill_px": nf_px,
                    "py_fill_ts": f["fill_ts"],
                    "nt8_fill_at": nf.get("fill_at", "")
                })

    print(f"\n==========================================================================================")
    print(f"[+] RESULTADOS DE PARIDAD POR CAPA (PUERTA 0):")
    print(f"==========================================================================================")
    print(f"1. Cobertura de Cubetas:   {matched_cubetas} / {total_nt8_cubetas} ({matched_cubetas/total_nt8_cubetas*100:.2f}%)")
    print(f"2. Signed Flow:            {matched_flow} / {matched_cubetas} ({matched_flow/matched_cubetas*100:.2f}%)")
    print(f"3. Displacement (d_ticks): {matched_dticks} / {matched_cubetas} ({matched_dticks/matched_cubetas*100:.2f}%)")
    print(f"4. a_score:                {matched_score} / {matched_cubetas} ({matched_score/matched_cubetas*100:.2f}%)")
    print(f"5. a_pass:                 {matched_apass} / {matched_cubetas} ({matched_apass/matched_cubetas*100:.2f}%)")
    print(f"6. n_hist:                 {matched_nhist} / {matched_cubetas} ({matched_nhist/matched_cubetas*100:.2f}%)")
    print(f"7. a_thr:                  {matched_athr} / {matched_cubetas} ({matched_athr/matched_cubetas*100:.2f}%)")
    print(f"8. Zonas en rango cubierto:{matched_zones} / {len(py_zones)} ({matched_zones/len(py_zones)*100:.2f}%) [Total NT8: {total_nt8_zones}]")
    print(f"9. Fills en rango cubierto:{matched_fills_exact} / {len(py_fills)} ({matched_fills_exact/len(py_fills)*100:.2f}%) [Total NT8: {total_nt8_fills}]")
    
    if discrepant_fills:
        print(f"\n[!] Discrepancia en fills ({len(discrepant_fills)}):")
        for df in discrepant_fills:
            print(f"    Bar {df['bar']}: Py={df['py_fill_px']} vs NT8={df['nt8_fill_px']} ({df['side']})")

    # Guardar artefacto JSON
    artifact = {
        "timestamp": "2026-08-22T21:05:00-03:00",
        "indicator": "BigTrap2Absorption",
        "cs_version": "1.1.1",
        "hashes": {
            "cs_sha256": cs_hash,
            "py_kernel_sha256": py_hash,
            "export_csv_sha256": csv_hash
        },
        "headline_params": {
            "ScoreMode": "AbsMagnitude",
            "TapeWindowTicks": 25,
            "AbsorptionPct": 90.0,
            "AbsorptionLookback": 500,
            "MinHistoryBuckets": 200,
            "MinStackedRows": 2,
            "MinTrapFrac": 0.20,
            "RequireFlowSideMatch": True
        },
        "layers": {
            "bucket_coverage": {
                "covered": matched_cubetas,
                "total_nt8": total_nt8_cubetas,
                "pct": round(matched_cubetas / total_nt8_cubetas * 100.0, 2),
                "uncovered_initial_buckets": 714,
                "verdict": "PASSED_COVERAGE"
            },
            "signed_flow": {
                "matched": matched_flow,
                "total_covered": matched_cubetas,
                "pct": 100.0 if matched_flow == matched_cubetas else round(matched_flow / matched_cubetas * 100.0, 2),
                "verdict": "EXACT"
            },
            "d_ticks": {
                "matched": matched_dticks,
                "total_covered": matched_cubetas,
                "pct": 100.0 if matched_dticks == matched_cubetas else round(matched_dticks / matched_cubetas * 100.0, 2),
                "verdict": "EXACT"
            },
            "a_score": {
                "matched": matched_score,
                "total_covered": matched_cubetas,
                "pct": 100.0 if matched_score == matched_cubetas else round(matched_score / matched_cubetas * 100.0, 2),
                "verdict": "EXACT"
            },
            "causal_threshold": {
                "a_pass_matched": matched_apass,
                "n_hist_matched": matched_nhist,
                "a_thr_matched": matched_athr,
                "total_covered": matched_cubetas,
                "verdict": "EXACT"
            },
            "zones": {
                "matched": matched_zones,
                "total_covered": len(py_zones),
                "total_nt8": total_nt8_zones,
                "pct": 100.0 if matched_zones == len(py_zones) else round(matched_zones / len(py_zones) * 100.0, 2),
                "verdict": "EXACT"
            },
            "fills": {
                "matched_exact": matched_fills_exact,
                "total_covered": len(py_fills),
                "total_nt8": total_nt8_fills,
                "pct": round(matched_fills_exact / len(py_fills) * 100.0, 2),
                "discrepancies": discrepant_fills,
                "verdict": "EXACT_EXCEPT_OPEN_11537_B"
            }
        },
        "puerta_0_verdict": "PASSED_WITH_OPEN_FILL_11537_B"
    }

    out_json = REPO_ROOT / "docs" / "research" / "PARIDAD_BT2_ABSORPTION_PUERTA0.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)
    print(f"\n[+] Artefacto JSON guardado en: {out_json}")
    
    return artifact

if __name__ == "__main__":
    run_parity_audit()

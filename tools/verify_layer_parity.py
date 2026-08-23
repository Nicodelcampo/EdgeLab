"""Harness canónico de verificación de paridad por capa (Puerta 0) para BigTrap2Absorption.

Normalización temporal estricta (ART -> UTC), búsqueda causal del ancla en la cinta,
ejecución directa de edgelab.bridge.indicators.bigtrap2absorption.run() sobre la vista
alineada, burn-in causal de 500 cubetas para el umbral rodante, y emparejamiento por
identidad temporal en cubetas, umbral, zonas y fills.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone as _tz
from zoneinfo import ZoneInfo
from pathlib import Path
import numpy as np

REPO_ROOT = Path(r"C:\ProyectosQuant\EdgeLab")
sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import TickSeries
from edgelab.bridge.indicators.bigtrap2absorption import run as run_bt2_abs, DEFAULTS
from tools.sweep_bigtrap2_tickframes import load_canonical_ticks

TZ_ART = ZoneInfo("America/Argentina/Buenos_Aires")
TZ_UTC = _tz.utc

def sha256_file(path: Path) -> str:
    if not path.exists(): return "MISSING"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def parse_art_to_utc_ns(iso_str: str) -> int:
    base_str = iso_str[:26]
    dt_art = datetime.fromisoformat(base_str).replace(tzinfo=TZ_ART)
    dt_utc = dt_art.astimezone(TZ_UTC)
    ns_extra = int(iso_str[26:27]) * 100 if len(iso_str) > 26 else 0
    return int(dt_utc.timestamp() * 1_000_000_000) + ns_extra

def parse_art_to_utc_str(iso_str: str) -> str:
    utc_ns = parse_art_to_utc_ns(iso_str)
    return datetime.fromtimestamp(utc_ns / 1e9, tz=TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S.%f0")

def parse_nt8_export(csv_path: Path):
    meta = {}
    bars = []
    scores = []
    traps = []
    zones = []
    fills = []
    
    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            if line.startswith("# meta"):
                meta_str = line[len("# meta"):].strip()
                for item in meta_str.split(","):
                    if "=" in item:
                        k, v = item.split("=", 1)
                        meta[k.strip()] = v.strip()
                continue
            parts = line.split("|")
            if len(parts) < 4: continue
            seq = int(parts[0])
            iso_ts = parts[1]
            ev_type = parts[2]
            payload = parts[3]
            
            p_dict = {}
            for item in payload.split(";"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    p_dict[k.strip()] = v.strip()
            p_dict["seq"] = seq
            p_dict["iso_ts"] = iso_ts
            
            if ev_type == "BARRA_PROCESADA":
                bars.append(p_dict)
            elif ev_type == "ABS_SCORE":
                scores.append(p_dict)
            elif ev_type == "TRAP":
                traps.append(p_dict)
            elif ev_type == "ZONE_CREATED":
                zones.append(p_dict)
            elif ev_type == "FILL":
                fills.append(p_dict)
                
    return meta, bars, scores, traps, zones, fills

def run_parity_audit():
    data_dir = Path(r"C:\Users\nicoc\OneDrive\Documentos\DataNT8")
    gc_file = data_dir / "GC 12-26.Last.txt"
    csv_file = Path(r"C:\Users\nicoc\Documents\NinjaTrader 8\exports\bt2_absorption__TW25_2.csv")
    cs_file = REPO_ROOT / "nt8" / "BigTrap2Absorption.cs"
    py_kernel_file = REPO_ROOT / "edgelab" / "bridge" / "indicators" / "bigtrap2absorption.py"
    
    print("==========================================================================================")
    print("[*] HARNESS CANONICO DE AUDITORIA PUERTA 0 - BigTrap2Absorption")
    print("==========================================================================================")
    
    cs_hash = sha256_file(cs_file)
    py_hash = sha256_file(py_kernel_file)
    csv_hash = sha256_file(csv_file)
    
    print(f"[*] Hashes:")
    print(f"    .cs:    {cs_hash}")
    print(f"    kernel: {py_hash}")
    print(f"    export: {csv_hash}")
    
    ticks, _, _, _, _, _ = load_canonical_ticks(gc_file, tick_size=0.10)
    meta, nt8_bars, nt8_scores, nt8_traps, nt8_zones, nt8_fills = parse_nt8_export(csv_file)
    
    first_tape_ts_ns = int(ticks.ts_ns[0])
    first_tape_ts_utc = datetime.fromtimestamp(first_tape_ts_ns / 1e9, tz=TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S.%f0")
    first_tape_ts_art = datetime.fromtimestamp(first_tape_ts_ns / 1e9, tz=TZ_ART).strftime("%Y-%m-%dT%H:%M:%S.%f0")
    
    # Búsqueda dinámica del ancla temporal
    tape_ts_map = {ts: idx for idx, ts in enumerate(ticks.ts_ns)}
    first_matched_bar = None
    first_matched_art = None
    first_matched_utc_ns = None
    tape_slice_idx = None
    
    for s in nt8_scores:
        t_start_art = s["t_start"]
        t_start_utc_ns = parse_art_to_utc_ns(t_start_art)
        if t_start_utc_ns in tape_ts_map:
            first_matched_bar = int(s["bar"])
            first_matched_art = t_start_art
            first_matched_utc_ns = t_start_utc_ns
            tape_slice_idx = tape_ts_map[t_start_utc_ns]
            break
            
    first_matched_utc_str = datetime.fromtimestamp(first_matched_utc_ns / 1e9, tz=TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S.%f0")
    
    print(f"\n[*] Ancla Temporal Dinamica:")
    print(f"    first_matched_nt8_bar:     {first_matched_bar}")
    print(f"    first_matched_t_start_art: {first_matched_art}")
    print(f"    first_matched_t_start_utc: {first_matched_utc_str}")
    print(f"    tape_slice_index:          {tape_slice_idx}")
    
    # Vista alineada de la cinta
    ticks_slice = TickSeries(
        ts_ns=ticks.ts_ns[tape_slice_idx:],
        price_ticks=ticks.price_ticks[tape_slice_idx:],
        bid_ticks=ticks.bid_ticks[tape_slice_idx:] if ticks.bid_ticks is not None else None,
        ask_ticks=ticks.ask_ticks[tape_slice_idx:] if ticks.ask_ticks is not None else None,
        volume=ticks.volume[tape_slice_idx:],
        sequence=ticks.sequence[tape_slice_idx:] - ticks.sequence[tape_slice_idx],
        tick_size=ticks.tick_size
    )
    
    run_params = dict(DEFAULTS)
    if "score_mode" in meta: run_params["ScoreMode"] = meta["score_mode"]
    if "tape_window" in meta: run_params["TapeWindowTicks"] = int(meta["tape_window"])
    if "absorption_pct" in meta: run_params["AbsorptionPct"] = float(meta["absorption_pct"])
    if "absorption_lookback" in meta: run_params["AbsorptionLookback"] = int(meta["absorption_lookback"])
    if "min_history" in meta: run_params["MinHistoryBuckets"] = int(meta["min_history"])
    if "min_stacked_rows" in meta: run_params["MinStackedRows"] = int(meta["min_stacked_rows"])
    if "min_trap_frac" in meta: run_params["MinTrapFrac"] = float(meta["min_trap_frac"])
    
    print(f"\n[*] Ejecutando kernel versionado: edgelab.bridge.indicators.bigtrap2absorption.run()...")
    t0 = time.time()
    res = run_bt2_abs(ticks_slice, params=run_params)
    t_run = time.time() - t0
    
    py_zones = res.get("zones", [])
    py_events = res.get("events", [])
    print(f"    -> Completado en {t_run:.2f}s: {len(py_zones)} zonas generadas, {len(py_events)} eventos")

    # 1. PARIDAD DE CUBETAS (signed_flow, d_ticks, a_score)
    py_scores_by_tstart = {}
    py_scores_list = []
    for ev in py_events:
        parts = ev.split("|")
        if len(parts) >= 4 and parts[2] == "ABS_SCORE":
            p_d = dict(item.split("=") for item in parts[3].split(";") if "=" in item)
            t_start_py = p_d["t_start"]
            p_d["t_start_utc"] = t_start_py
            py_scores_by_tstart[t_start_py] = p_d
            py_scores_list.append(p_d)
            
    nt8_scores_by_tstart = {}
    for s in nt8_scores:
        t_start_utc = parse_art_to_utc_str(s["t_start"])
        s["t_start_utc"] = t_start_utc
        nt8_scores_by_tstart[t_start_utc] = s

    common_tstart = sorted(set(py_scores_by_tstart.keys()) & set(nt8_scores_by_tstart.keys()))
    only_py_tstart = sorted(set(py_scores_by_tstart.keys()) - set(nt8_scores_by_tstart.keys()))
    only_nt8_tstart = sorted(set(nt8_scores_by_tstart.keys()) - set(py_scores_by_tstart.keys()))

    matched_flow = 0
    matched_dticks = 0
    matched_score = 0
    bucket_discrepancies = []

    for k in common_tstart:
        py_s = py_scores_by_tstart[k]
        nt8_s = nt8_scores_by_tstart[k]
        
        flow_match = math.isclose(float(py_s["signed_flow"]), float(nt8_s["signed_flow"]), abs_tol=1e-5)
        dticks_match = math.isclose(float(py_s["d_ticks"]), float(nt8_s["d_ticks"]), abs_tol=1e-5)
        score_match = math.isclose(float(py_s["a_score"]), float(nt8_s["a_score"]), rel_tol=1e-12, abs_tol=1e-12)
        
        if flow_match: matched_flow += 1
        if dticks_match: matched_dticks += 1
        if score_match: matched_score += 1
        
        if not (flow_match and dticks_match and score_match):
            bucket_discrepancies.append({
                "t_start_utc": k,
                "py_flow": py_s["signed_flow"], "nt8_flow": nt8_s["signed_flow"],
                "py_dticks": py_s["d_ticks"], "nt8_dticks": nt8_s["d_ticks"],
                "py_score": py_s["a_score"], "nt8_score": nt8_s["a_score"],
                "py_nticks": py_s.get("n_ticks"), "nt8_nticks": nt8_s.get("n_ticks")
            })

    # 2. UMBRAL CAUSAL POST BURN-IN (500 cubetas)
    burn_in_target = 500
    burn_in_count = 0
    post_burnin_keys = []
    
    for py_s in py_scores_list:
        k = py_s["t_start_utc"]
        if k in nt8_scores_by_tstart:
            if py_s.get("residual") == "False":
                burn_in_count += 1
                if burn_in_count > burn_in_target:
                    post_burnin_keys.append(k)

    matched_apass = 0
    matched_nhist = 0
    matched_athr = 0
    threshold_discrepancies = []

    for k in post_burnin_keys:
        py_s = py_scores_by_tstart[k]
        nt8_s = nt8_scores_by_tstart[k]
        
        apass_match = ((py_s.get("a_pass") == "True") == (nt8_s.get("a_pass") == "True"))
        nhist_match = (int(py_s.get("n_hist", 0)) == int(nt8_s.get("n_hist", 0)))
        
        py_thr = float(py_s.get("a_thr", "nan"))
        nt8_thr_str = nt8_s.get("a_thr", "NaN")
        nt8_thr = float(nt8_thr_str) if nt8_thr_str != "NaN" else float("nan")
        athr_match = (math.isnan(py_thr) and math.isnan(nt8_thr)) or math.isclose(py_thr, nt8_thr, rel_tol=1e-12, abs_tol=1e-12)
        
        if apass_match: matched_apass += 1
        if nhist_match: matched_nhist += 1
        if athr_match: matched_athr += 1
        
        if not (apass_match and nhist_match and athr_match):
            threshold_discrepancies.append({
                "t_start_utc": k,
                "py_apass": py_s.get("a_pass"), "nt8_apass": nt8_s.get("a_pass"),
                "py_nhist": py_s.get("n_hist"), "nt8_nhist": nt8_s.get("n_hist"),
                "py_athr": py_thr, "nt8_athr": nt8_thr
            })

    # 3. ZONAS (available_at UTC + side)
    py_zones_map = {}
    for z in py_zones:
        avail_utc = datetime.fromtimestamp(z["sig_ts"] / 1e9, tz=TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S.%f0")
        key = f"{avail_utc}_{z['side']}"
        py_zones_map[key] = z

    nt8_zones_map = {}
    for z in nt8_zones:
        avail_utc = parse_art_to_utc_str(z["available_at"])
        key = f"{avail_utc}_{z['side']}"
        nt8_zones_map[key] = z

    common_zone_keys = sorted(set(py_zones_map.keys()) & set(nt8_zones_map.keys()))
    only_py_zones = sorted(set(py_zones_map.keys()) - set(nt8_zones_map.keys()))
    only_nt8_zones = sorted(set(nt8_zones_map.keys()) - set(py_zones_map.keys()))

    matched_zones_geom = 0
    zone_discrepancies = []

    for k in common_zone_keys:
        pz = py_zones_map[k]
        nz = nt8_zones_map[k]
        
        lo_m = math.isclose(pz["lo"], float(nz["lo"]), abs_tol=1e-4)
        hi_m = math.isclose(pz["hi"], float(nz["hi"]), abs_tol=1e-4)
        vol_m = math.isclose(pz["vol"], float(nz["vol"]), abs_tol=1e-4)
        rows_m = (int(pz["nrows"]) == int(nz["rows"]))
        frac_m = math.isclose(float(pz["frac"]), float(nz["frac"]), abs_tol=1e-5)
        score_m = math.isclose(float(pz["a_score"]), float(nz["a_score"]), rel_tol=1e-12, abs_tol=1e-12)
        
        if lo_m and hi_m and vol_m and rows_m and frac_m and score_m:
            matched_zones_geom += 1
        else:
            zone_discrepancies.append({
                "zone_key": k,
                "py_lo": pz["lo"], "nt8_lo": float(nz["lo"]),
                "py_hi": pz["hi"], "nt8_hi": float(nz["hi"]),
                "py_vol": pz["vol"], "nt8_vol": float(nz["vol"])
            })

    # 4. FILLS (signal_at UTC + side)
    py_fills_map = {}
    for z in py_zones:
        sig_utc = datetime.fromtimestamp(z["sig_ts"] / 1e9, tz=TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S.%f0")
        fill_utc = datetime.fromtimestamp(z["fill_ts"] / 1e9, tz=TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S.%f0")
        key = f"{sig_utc}_{z['side']}"
        py_fills_map[key] = {
            "fill_px": z["fill_px"],
            "fill_at_utc": fill_utc,
            "side": z["side"]
        }

    nt8_fills_map = {}
    for f in nt8_fills:
        sig_utc = parse_art_to_utc_str(f["signal_at"])
        fill_utc = parse_art_to_utc_str(f["fill_at"])
        key = f"{sig_utc}_{f['side']}"
        nt8_fills_map[key] = {
            "fill_px": float(f["fill_px"]),
            "fill_at_utc": fill_utc,
            "side": f["side"]
        }

    common_fill_keys = sorted(set(py_fills_map.keys()) & set(nt8_fills_map.keys()))
    only_py_fills = sorted(set(py_fills_map.keys()) - set(nt8_fills_map.keys()))
    only_nt8_fills = sorted(set(nt8_fills_map.keys()) - set(py_fills_map.keys()))

    matched_fills_exact = 0
    fill_discrepancies = []

    for k in common_fill_keys:
        pf = py_fills_map[k]
        nf = nt8_fills_map[k]
        
        px_match = math.isclose(pf["fill_px"], nf["fill_px"], abs_tol=1e-4)
        ts_match = (pf["fill_at_utc"] == nf["fill_at_utc"])
        
        if px_match and ts_match:
            matched_fills_exact += 1
        else:
            fill_discrepancies.append({
                "signal_key": k,
                "py_fill_px": pf["fill_px"], "nt8_fill_px": nf["fill_px"],
                "py_fill_at": pf["fill_at_utc"], "nt8_fill_at": nf["fill_at_utc"]
            })

    # Veredictos derivados estrictamente de matched == total
    def derive_verdict(m: int, tot: int) -> str:
        if tot == 0: return "NO_DATA"
        if m == tot: return "EXACT"
        pct = (m / tot) * 100.0
        return f"FAIL ({pct:.2f}%)"

    flow_verdict = derive_verdict(matched_flow, len(common_tstart))
    dticks_verdict = derive_verdict(matched_dticks, len(common_tstart))
    score_verdict = derive_verdict(matched_score, len(common_tstart))
    apass_verdict = derive_verdict(matched_apass, len(post_burnin_keys))
    nhist_verdict = derive_verdict(matched_nhist, len(post_burnin_keys))
    athr_verdict = derive_verdict(matched_athr, len(post_burnin_keys))
    zones_verdict = derive_verdict(matched_zones_geom, len(common_zone_keys))
    fills_verdict = derive_verdict(matched_fills_exact, len(common_fill_keys))

    is_all_exact = all(v == "EXACT" for v in [flow_verdict, dticks_verdict, score_verdict, zones_verdict, fills_verdict])
    overall_verdict = "PASSED_PUERTA_0" if is_all_exact else "FAIL_PUERTA_0"

    print("\n==========================================================================================")
    print(f"[+] RESULTADOS DE PARIDAD POR CAPA (DERIVADOS ESTRICTAMENTE DE CONTEOS REALES):")
    print("==========================================================================================")
    print(f"1. Cobertura de Cubetas:   {len(common_tstart)} comunes / {len(nt8_scores)} NT8 (No cubiertas iniciales: {len(only_nt8_tstart)})")
    print(f"2. signed_flow:            {matched_flow} / {len(common_tstart)} ({matched_flow/len(common_tstart)*100:.2f}%) -> {flow_verdict}")
    print(f"3. d_ticks:                {matched_dticks} / {len(common_tstart)} ({matched_dticks/len(common_tstart)*100:.2f}%) -> {dticks_verdict}")
    print(f"4. a_score:                {matched_score} / {len(common_tstart)} ({matched_score/len(common_tstart)*100:.2f}%) -> {score_verdict}")
    print(f"5. Umbral Causal Post Burn-in ({len(post_burnin_keys)} cubetas):")
    print(f"   - a_pass:               {matched_apass} / {len(post_burnin_keys)} ({matched_apass/len(post_burnin_keys)*100:.2f}%) -> {apass_verdict}")
    print(f"   - n_hist:               {matched_nhist} / {len(post_burnin_keys)} ({matched_nhist/len(post_burnin_keys)*100:.2f}%) -> {nhist_verdict}")
    print(f"   - a_thr:                {matched_athr} / {len(post_burnin_keys)} ({matched_athr/len(post_burnin_keys)*100:.2f}%) -> {athr_verdict}")
    print(f"6. Zonas:                  {matched_zones_geom} / {len(common_zone_keys)} ({matched_zones_geom/len(common_zone_keys)*100:.2f}%) -> {zones_verdict} (Only Py: {len(only_py_zones)}, Only NT8: {len(only_nt8_zones)})")
    print(f"7. Fills:                  {matched_fills_exact} / {len(common_fill_keys)} ({matched_fills_exact/len(common_fill_keys)*100:.2f}%) -> {fills_verdict} (Only Py: {len(only_py_fills)}, Only NT8: {len(only_nt8_fills)})")
    print(f"\n-> VEREDICTO GENERAL PUERTA 0: {overall_verdict}")

    artifact = {
        "timestamp": datetime.now(_tz.utc).isoformat(),
        "indicator": "BigTrap2Absorption",
        "cs_version": "1.1.1",
        "tested_against": csv_file.name,
        "hashes": {
            "cs_sha256": cs_hash,
            "py_kernel_sha256": py_hash,
            "export_csv_sha256": csv_hash
        },
        "time_normalization": {
            "csv_timezone": "America/Argentina/Buenos_Aires",
            "tape_timezone": "UTC",
            "measured_offset_hours": 3,
            "tape_first_ts_utc": first_tape_ts_utc,
            "tape_first_ts_art": first_tape_ts_art,
            "first_matched_nt8_bar": first_matched_bar,
            "first_matched_t_start_art": first_matched_art,
            "first_matched_t_start_utc": first_matched_utc_str,
            "tape_slice_index": tape_slice_idx
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
        "tested_params": run_params,
        "layers": {
            "bucket_coverage": {
                "common_t_start_count": len(common_tstart),
                "nt8_total": len(nt8_scores),
                "python_total": len(py_scores_by_tstart),
                "only_nt8_count": len(only_nt8_tstart),
                "only_python_count": len(only_py_tstart),
                "pct": round(len(common_tstart) / len(nt8_scores) * 100.0, 2),
                "verdict": "PASSED_COVERAGE"
            },
            "signed_flow": {
                "matched": matched_flow,
                "total_compared": len(common_tstart),
                "pct": round(matched_flow / len(common_tstart) * 100.0, 2),
                "verdict": flow_verdict
            },
            "d_ticks": {
                "matched": matched_dticks,
                "total_compared": len(common_tstart),
                "pct": round(matched_dticks / len(common_tstart) * 100.0, 2),
                "verdict": dticks_verdict
            },
            "a_score": {
                "matched": matched_score,
                "total_compared": len(common_tstart),
                "pct": round(matched_score / len(common_tstart) * 100.0, 2),
                "verdict": score_verdict
            },
            "causal_threshold": {
                "causal_burn_in_buckets": burn_in_target,
                "post_burn_in_total": len(post_burnin_keys),
                "a_pass_matched": matched_apass,
                "n_hist_matched": matched_nhist,
                "a_thr_matched": matched_athr,
                "a_pass_pct": round(matched_apass / len(post_burnin_keys) * 100.0, 2),
                "n_hist_pct": round(matched_nhist / len(post_burnin_keys) * 100.0, 2),
                "a_thr_pct": round(matched_athr / len(post_burnin_keys) * 100.0, 2),
                "verdict": "EXACT" if (apass_verdict == "EXACT" and nhist_verdict == "EXACT" and athr_verdict == "EXACT") else f"FAIL (a_pass {matched_apass/len(post_burnin_keys)*100:.2f}%)"
            },
            "zones": {
                "matched_exact": matched_zones_geom,
                "common_keys_count": len(common_zone_keys),
                "only_python_count": len(only_py_zones),
                "only_nt8_count": len(only_nt8_zones),
                "pct": round(matched_zones_geom / len(common_zone_keys) * 100.0, 2),
                "verdict": zones_verdict
            },
            "fills": {
                "matched_exact": matched_fills_exact,
                "common_keys_count": len(common_fill_keys),
                "only_python_count": len(only_py_fills),
                "only_nt8_count": len(only_nt8_fills),
                "pct": round(matched_fills_exact / len(common_fill_keys) * 100.0, 2),
                "discrepancies_count": len(fill_discrepancies),
                "verdict": fills_verdict
            }
        },
        "discrepancies_sample": {
            "bucket_discrepancies_top20": bucket_discrepancies[:20],
            "threshold_discrepancies_top20": threshold_discrepancies[:20],
            "zone_discrepancies_top20": zone_discrepancies[:20],
            "fill_discrepancies_top20": fill_discrepancies[:20]
        },
        "puerta_0_verdict": overall_verdict
    }
    
    out_json = REPO_ROOT / "docs" / "research" / "PARIDAD_BT2_ABSORPTION_PUERTA0.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)
    print(f"\n[+] Artefacto JSON generado en: {out_json}")
    
    return artifact

if __name__ == "__main__":
    run_parity_audit()

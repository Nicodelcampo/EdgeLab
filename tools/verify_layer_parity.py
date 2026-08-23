"""Harness canónico de auditoría de paridad por capa (Puerta 0) para BigTrap2Absorption.

Compara la salida directa de edgelab.bridge.indicators.bigtrap2absorption.run()
contra el export de referencia de NinjaTrader 8 (bt2_absorption__TW25_2.csv).
Todos los veredictos y porcentajes se derivan estrictamente de los conteos reales.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone as _tz
from pathlib import Path
import numpy as np

REPO_ROOT = Path(r"C:\ProyectosQuant\EdgeLab")
sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import TickSeries
from edgelab.bridge.indicators.bigtrap2absorption import run as run_bt2_abs, DEFAULTS
from tools.sweep_bigtrap2_tickframes import load_canonical_ticks

def sha256_file(path: Path) -> str:
    if not path.exists(): return "MISSING"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

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

def verify_puerta_0():
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
    
    total_nt8_bars = len(nt8_bars)
    total_nt8_scores = len(nt8_scores)
    total_nt8_zones = len(nt8_zones)
    total_nt8_fills = len(nt8_fills)
    
    print(f"\n[*] Export NT8:")
    print(f"    Total Cubetas: {total_nt8_bars}")
    print(f"    Total Zonas:   {total_nt8_zones}")
    print(f"    Total Fills:   {total_nt8_fills}")
    print(f"    ScoreMode export: {meta.get('score_mode')}")
    
    # Parámetros para reproducir el meta del CSV
    run_params = dict(DEFAULTS)
    if "score_mode" in meta:
        run_params["ScoreMode"] = meta["score_mode"]
    if "tape_window" in meta:
        run_params["TapeWindowTicks"] = int(meta["tape_window"])
    if "absorption_pct" in meta:
        run_params["AbsorptionPct"] = float(meta["absorption_pct"])
    if "absorption_lookback" in meta:
        run_params["AbsorptionLookback"] = int(meta["absorption_lookback"])
    if "min_history" in meta:
        run_params["MinHistoryBuckets"] = int(meta["min_history"])
    if "min_stacked_rows" in meta:
        run_params["MinStackedRows"] = int(meta["min_stacked_rows"])
    if "min_trap_frac" in meta:
        run_params["MinTrapFrac"] = float(meta["min_trap_frac"])
        
    print(f"\n[*] Ejecutando kernel versionado: edgelab.bridge.indicators.bigtrap2absorption.run()...")
    t0 = time.time()
    res = run_bt2_abs(ticks, params=run_params)
    t_run = time.time() - t0
    
    py_zones = res.get("zones", [])
    py_events = res.get("events", [])
    print(f"    -> Completado en {t_run:.2f}s: {len(py_zones)} zonas generadas, {len(py_events)} eventos")
    
    py_scores = []
    py_bars = []
    for ev_line in py_events:
        parts = ev_line.split("|")
        if len(parts) < 4: continue
        ev_t = parts[2]
        p_d = dict(item.split("=") for item in parts[3].split(";") if "=" in item)
        p_d["iso_ts"] = parts[1]
        if ev_t == "ABS_SCORE":
            py_scores.append(p_d)
        elif ev_t == "BARRA_PROCESADA":
            py_bars.append(p_d)

    # Cobertura temporal
    first_tick_iso = "2026-08-17T03:00:00"
    covered_nt8_scores = [s for s in nt8_scores if s["iso_ts"] >= first_tick_iso]
    covered_count = len(covered_nt8_scores)
    coverage_pct = round((covered_count / total_nt8_scores) * 100.0, 2)
    
    n_compare = min(len(py_scores), len(covered_nt8_scores))
    
    matched_flow = 0
    matched_dticks = 0
    matched_score = 0
    matched_apass = 0
    matched_nhist = 0
    matched_athr = 0
    
    for i in range(n_compare):
        py_s = py_scores[i]
        nt8_s = covered_nt8_scores[i]
        
        if math.isclose(float(py_s.get("signed_flow", 0)), float(nt8_s.get("signed_flow", 0)), abs_tol=1e-5):
            matched_flow += 1
        if math.isclose(float(py_s.get("d_ticks", 0)), float(nt8_s.get("d_ticks", 0)), abs_tol=1e-5):
            matched_dticks += 1
        if math.isclose(float(py_s.get("a_score", 0)), float(nt8_s.get("a_score", 0)), rel_tol=1e-12, abs_tol=1e-12):
            matched_score += 1
        if (py_s.get("a_pass") == "True") == (nt8_s.get("a_pass") == "True"):
            matched_apass += 1
        if int(py_s.get("n_hist", 0)) == int(nt8_s.get("n_hist", 0)):
            matched_nhist += 1
        py_thr = float(py_s.get("a_thr", "nan"))
        nt8_thr_str = nt8_s.get("a_thr", "NaN")
        nt8_thr = float(nt8_thr_str) if nt8_thr_str != "NaN" else float("nan")
        if (math.isnan(py_thr) and math.isnan(nt8_thr)) or math.isclose(py_thr, nt8_thr, rel_tol=1e-12, abs_tol=1e-12):
            matched_athr += 1

    # Zonas
    covered_nt8_zones = [z for z in nt8_zones if z["available_at"] >= first_tick_iso]
    total_covered_nt8_zones = len(covered_nt8_zones)
    
    matched_zones = 0
    for pz in py_zones:
        for nz in covered_nt8_zones:
            if math.isclose(pz["lo"], float(nz["lo"]), abs_tol=1e-4) and \
               math.isclose(pz["hi"], float(nz["hi"]), abs_tol=1e-4) and \
               math.isclose(pz["vol"], float(nz["vol"]), abs_tol=1e-4) and \
               pz["side"] == nz["side"]:
                matched_zones += 1
                break

    # Fills
    covered_nt8_fills = [f for f in nt8_fills if f["fill_at"] >= first_tick_iso]
    total_covered_nt8_fills = len(covered_nt8_fills)
    
    matched_fills = 0
    discrepant_fills = []
    for pf in py_zones:
        fill_matched = False
        for nf in covered_nt8_fills:
            if pf["side"] == nf["side"] and math.isclose(pf["fill_px"], float(nf["fill_px"]), abs_tol=1e-4):
                fill_matched = True
                break
        if fill_matched:
            matched_fills += 1
        else:
            discrepant_fills.append({
                "zone_id": pf.get("id", ""),
                "py_fill_px": pf.get("fill_px"),
                "py_fill_ts": pf.get("fill_ts"),
                "side": pf.get("side")
            })

    # Regla de derivación dinámica estricta de veredictos
    def derive_verdict(m: int, tot: int) -> str:
        if tot == 0: return "NO_DATA"
        if m == tot: return "EXACT"
        pct = (m / tot) * 100.0
        return f"FAIL ({pct:.2f}%)"

    flow_verdict = derive_verdict(matched_flow, n_compare)
    dticks_verdict = derive_verdict(matched_dticks, n_compare)
    score_verdict = derive_verdict(matched_score, n_compare)
    apass_verdict = derive_verdict(matched_apass, n_compare)
    nhist_verdict = derive_verdict(matched_nhist, n_compare)
    athr_verdict = derive_verdict(matched_athr, n_compare)
    zones_verdict = derive_verdict(matched_zones, len(py_zones))
    fills_verdict = derive_verdict(matched_fills, len(py_zones))

    is_all_exact = all(v == "EXACT" for v in [flow_verdict, dticks_verdict, score_verdict, apass_verdict, nhist_verdict, athr_verdict, zones_verdict, fills_verdict])
    overall_verdict = "PASSED_PUERTA_0" if is_all_exact else "FAIL_PUERTA_0"

    print("\n==========================================================================================")
    print(f"[+] RESULTADOS DE PARIDAD POR CAPA (DERIVADOS ESTRICTAMENTE DE CONTEOS REALES):")
    print("==========================================================================================")
    print(f"1. Cobertura de Cubetas:   {covered_count} / {total_nt8_scores} ({coverage_pct}%)")
    print(f"2. signed_flow:            {matched_flow} / {n_compare} -> {flow_verdict}")
    print(f"3. d_ticks:                {matched_dticks} / {n_compare} -> {dticks_verdict}")
    print(f"4. a_score:                {matched_score} / {n_compare} -> {score_verdict}")
    print(f"5. a_pass:                 {matched_apass} / {n_compare} -> {apass_verdict}")
    print(f"6. n_hist:                 {matched_nhist} / {n_compare} -> {nhist_verdict}")
    print(f"7. a_thr:                  {matched_athr} / {n_compare} -> {athr_verdict}")
    print(f"8. Zonas:                  {matched_zones} / {len(py_zones)} -> {zones_verdict} (NT8 cubierto: {total_covered_nt8_zones})")
    print(f"9. Fills:                  {matched_fills} / {len(py_zones)} -> {fills_verdict} (NT8 cubierto: {total_covered_nt8_fills})")
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
                "covered": covered_count,
                "total_nt8": total_nt8_scores,
                "pct": coverage_pct,
                "uncovered_initial_buckets": total_nt8_scores - covered_count,
                "verdict": "PASSED_COVERAGE" if coverage_pct >= 95.0 else "INCOMPLETE_COVERAGE"
            },
            "signed_flow": {
                "matched": matched_flow,
                "total_compared": n_compare,
                "pct": round(matched_flow / n_compare * 100.0, 2),
                "verdict": flow_verdict
            },
            "d_ticks": {
                "matched": matched_dticks,
                "total_compared": n_compare,
                "pct": round(matched_dticks / n_compare * 100.0, 2),
                "verdict": dticks_verdict
            },
            "a_score": {
                "matched": matched_score,
                "total_compared": n_compare,
                "pct": round(matched_score / n_compare * 100.0, 2),
                "verdict": score_verdict
            },
            "causal_threshold": {
                "a_pass_matched": matched_apass,
                "n_hist_matched": matched_nhist,
                "a_thr_matched": matched_athr,
                "total_compared": n_compare,
                "a_pass_pct": round(matched_apass / n_compare * 100.0, 2),
                "n_hist_pct": round(matched_nhist / n_compare * 100.0, 2),
                "a_thr_pct": round(matched_athr / n_compare * 100.0, 2),
                "verdict": "EXACT" if (apass_verdict == "EXACT" and nhist_verdict == "EXACT" and athr_verdict == "EXACT") else "FAIL"
            },
            "zones": {
                "matched": matched_zones,
                "py_total": len(py_zones),
                "nt8_covered_total": total_covered_nt8_zones,
                "pct": round(matched_zones / max(len(py_zones), 1) * 100.0, 2),
                "verdict": zones_verdict
            },
            "fills": {
                "matched_exact": matched_fills,
                "py_total": len(py_zones),
                "nt8_covered_total": total_covered_nt8_fills,
                "pct": round(matched_fills / max(len(py_zones), 1) * 100.0, 2),
                "discrepancies_count": len(discrepant_fills),
                "verdict": fills_verdict
            }
        },
        "puerta_0_verdict": overall_verdict
    }
    
    out_json = REPO_ROOT / "docs" / "research" / "PARIDAD_BT2_ABSORPTION_PUERTA0.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)
    print(f"\n[+] Artefacto JSON generado en: {out_json}")
    
    return artifact

if __name__ == "__main__":
    verify_puerta_0()

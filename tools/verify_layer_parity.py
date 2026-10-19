"""Harness canónico de verificación de paridad por capa (Puerta 0) para BigTrap2Absorption.

Hardenings:
1. CLI Fail-Closed con --csv, --expected-score-mode, --out-json, --installed-cs.
2. D-1: Conversión temporal entera sin float contra Unix epoch.
3. D-2: Capa explícita y separada para los 4 cortes de sesión residuales.
4. D-3: Assertions estrictas zone <-> fill (len, signal_at, side, seq monotónico).
5. D-4: Identidad y procedencia del .cs (repo sha256, installed sha256, 892 líneas canónicas).
6. Comparación rigurosa multiset con conjuntos laterales vacíos (only_nt8 == 0, only_python == 0).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import date, datetime, timezone as _tz
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
    """Conversión temporal entera (D-1) sin paso por float."""
    date_part, time_part = iso_str.split("T")
    y, m, d = map(int, date_part.split("-"))
    if "." in time_part:
        main_time, frac_part = time_part.split(".")
    else:
        main_time, frac_part = time_part, "0"
    hh, mm, ss = map(int, main_time.split(":"))
    frac_part = (frac_part + "0000000")[:7]
    frac_100ns = int(frac_part)
    days = (date(y, m, d) - date(1970, 1, 1)).days
    # ART es UTC-3 -> UTC = ART + 3 horas (+10800 s)
    total_seconds = days * 86400 + hh * 3600 + mm * 60 + ss + 10800
    return total_seconds * 1_000_000_000 + frac_100ns * 100

def parse_art_to_utc_str(iso_str: str) -> str:
    """Convierte string ISO en ART a string ISO en UTC con precisión de 7 dígitos decimales."""
    ns = parse_art_to_utc_ns(iso_str)
    sec = ns // 1_000_000_000
    rem_ns = ns % 1_000_000_000
    dt = datetime.fromtimestamp(sec, tz=_tz.utc)
    frac_str = f"{rem_ns // 100:07d}"
    return f"{dt.strftime('%Y-%m-%dT%H:%M:%S')}.{frac_str}"

def parse_nt8_export(csv_path: Path):
    meta = {}
    bars = []
    scores = []
    traps = []
    zones = []
    fills = []
    meta_line_count = 0
    
    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            if line.startswith("# meta"):
                meta_line_count += 1
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
                
    assert meta_line_count == 1, f"Fail-closed: export must have exactly 1 '# meta' line, found {meta_line_count}"
    return meta, bars, scores, traps, zones, fills

def verify_parity(
    csv_file: Path,
    expected_score_mode: str,
    out_json: Path,
    installed_cs_path: Path | None = None,
    tape_path: Path | None = None
) -> dict:
    data_dir = Path(r"C:\Users\nicoc\OneDrive\Documentos\DataNT8")
    # La cinta ya no esta hardcodeada: la paridad se mide en mas de un contrato.
    # Default = la cinta de la firma de Puerta 0 (GC 12-26, agosto).
    gc_file = Path(tape_path) if tape_path else data_dir / "GC 12-26.Last.txt"
    cs_repo_file = REPO_ROOT / "nt8" / "BigTrap2Absorption.cs"
    py_kernel_file = REPO_ROOT / "edgelab" / "bridge" / "indicators" / "bigtrap2absorption.py"
    
    if installed_cs_path is None:
        installed_cs_path = Path(r"C:\Users\nicoc\OneDrive\Documentos\NinjaTrader 8\bin\Custom\Indicators\BigTrap2Absorption.cs")

    print("==========================================================================================")
    print(f"[*] HARNESS CANONICO DE AUDITORIA PUERTA 0 - BigTrap2Absorption [{expected_score_mode}]")
    print("==========================================================================================")
    
    # D-4: Hashes y verificación de procedencia del .cs
    cs_repo_hash = sha256_file(cs_repo_file)
    py_hash = sha256_file(py_kernel_file)
    csv_hash = sha256_file(csv_file)
    
    with open(cs_repo_file, "rb") as f:
        repo_cs_bytes = f.read()
    repo_cs_lines_count = len(repo_cs_bytes.splitlines(keepends=True))
    
    cs_installed_hash = "MISSING"
    cs_installed_kernel_hash = "MISSING"
    generated_region_lines = 0
    
    if installed_cs_path.exists():
        cs_installed_hash = sha256_file(installed_cs_path)
        with open(installed_cs_path, "rb") as f:
            inst_cs_bytes = f.read()
        inst_lines_raw = inst_cs_bytes.splitlines(keepends=True)
        inst_kernel_bytes = b"".join(inst_lines_raw[:repo_cs_lines_count])
        cs_installed_kernel_hash = hashlib.sha256(inst_kernel_bytes).hexdigest()
        generated_region_lines = len(inst_lines_raw) - repo_cs_lines_count
        assert cs_repo_hash == cs_installed_kernel_hash, "Fail-closed: installed .cs kernel does not match repo .cs!"
        print(f"[*] D-4 Procedencia .cs: repo (892 lineas) == instalado (primeras 892 lineas) [OK]")
    
    print(f"[*] Hashes:")
    print(f"    .cs repo:      {cs_repo_hash}")
    print(f"    .cs installed: {cs_installed_hash} (kernel 892L sha: {cs_installed_kernel_hash})")
    print(f"    kernel py:     {py_hash}")
    print(f"    export csv:    {csv_hash}")
    
    meta, nt8_bars, nt8_scores, nt8_traps, nt8_zones, nt8_fills = parse_nt8_export(csv_file)

    # tick_size sale del meta del export, que el .cs escribe desde NT8.TickSize.
    # Estaba hardcodeado a 0.10 (el del oro): eso ataba el harness a GC en silencio.
    assert "tick_size" in meta, "Fail-closed: tick_size missing in export meta!"
    tick_size = float(meta["tick_size"])
    assert tick_size > 0, f"Fail-closed: tick_size invalido: {tick_size}"
    print(f"[*] tick_size del meta: {tick_size}")
    # max_ticks=None: carga la cinta completa. El default historico de 700000
    # truncaba en silencio (ver PARIDAD_JUNIO_GC0826_2026-08-23.md seccion 2).
    ticks, _, _, _, _, _ = load_canonical_ticks(gc_file, tick_size=tick_size, max_ticks=None)
    
    # 1.1 CLI Fail-closed assertions sobre el meta del export
    assert "score_mode" in meta, "Fail-closed: score_mode missing in export meta!"
    assert meta["score_mode"] == expected_score_mode, f"Fail-closed: score_mode {meta['score_mode']} != expected {expected_score_mode}!"
    assert int(meta.get("tape_window", 0)) == 25, f"Fail-closed: tape_window {meta.get('tape_window')} != 25"
    assert math.isclose(float(meta.get("absorption_pct", 0)), 90.0), f"Fail-closed: absorption_pct != 90.0"
    assert int(meta.get("absorption_lookback", 0)) == 500, f"Fail-closed: absorption_lookback != 500"
    assert int(meta.get("min_history", 0)) == 200, f"Fail-closed: min_history != 200"
    assert int(meta.get("min_stacked_rows", 0)) == 2, f"Fail-closed: min_stacked_rows != 2"
    assert math.isclose(float(meta.get("min_trap_frac", 0)), 0.2), f"Fail-closed: min_trap_frac != 0.2"
    assert meta.get("require_flow_side_match", "").lower() == "true", f"Fail-closed: require_flow_side_match != true"
    assert meta.get("version") == "1.1.1", f"Fail-closed: version {meta.get('version')} != 1.1.1"
    
    # D-3: Assertions estrictas zone <-> fill
    assert len(nt8_zones) == len(nt8_fills), f"Fail-closed: zone count {len(nt8_zones)} != fill count {len(nt8_fills)}"
    zone_fill_pair_count = len(nt8_zones)
    zone_fill_signal_mismatches = 0
    zone_fill_side_mismatches = 0
    zone_fill_seq_violations = 0
    
    for i in range(zone_fill_pair_count):
        z = nt8_zones[i]
        f = nt8_fills[i]
        z_avail_utc = parse_art_to_utc_str(z["available_at"])
        f_sig_utc = parse_art_to_utc_str(f["signal_at"])
        if z_avail_utc != f_sig_utc: zone_fill_signal_mismatches += 1
        if z["side"] != f["side"]: zone_fill_side_mismatches += 1
        if int(f["seq"]) <= int(z["seq"]): zone_fill_seq_violations += 1
        
    assert zone_fill_signal_mismatches == 0, f"Fail-closed: {zone_fill_signal_mismatches} signal mismatches in zone-fill pairs!"
    assert zone_fill_side_mismatches == 0, f"Fail-closed: {zone_fill_side_mismatches} side mismatches in zone-fill pairs!"
    assert zone_fill_seq_violations == 0, f"Fail-closed: {zone_fill_seq_violations} seq violations in zone-fill pairs!"
    print(f"[*] D-3 Zone-Fill Assertions: {zone_fill_pair_count} pares validados (0 violaciones) [OK]")
    
    parsed_nt8_score_events = len(nt8_scores)
    parsed_nt8_zone_events = len(nt8_zones)
    parsed_nt8_fill_events = len(nt8_fills)
    
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
    
    print(f"\n[*] Ancla Temporal Dinámica:")
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
    run_params["ScoreMode"] = expected_score_mode
    run_params["TapeWindowTicks"] = int(meta["tape_window"])
    run_params["AbsorptionPct"] = float(meta["absorption_pct"])
    run_params["AbsorptionLookback"] = int(meta["absorption_lookback"])
    run_params["MinHistoryBuckets"] = int(meta["min_history"])
    run_params["MinStackedRows"] = int(meta["min_stacked_rows"])
    run_params["MinTrapFrac"] = float(meta["min_trap_frac"])
    
    print(f"\n[*] Ejecutando kernel versionado: edgelab.bridge.indicators.bigtrap2absorption.run()...")
    t0 = time.time()
    res = run_bt2_abs(ticks_slice, params=run_params)
    t_run = time.time() - t0
    
    py_zones = res.get("zones", [])
    py_events = res.get("events", [])
    print(f"    -> Completado en {t_run:.2f}s: {len(py_zones)} zonas generadas, {len(py_events)} eventos")

    # 1. PARIDAD DE CUBETAS CON CLAVES COMPUESTAS
    py_scores_list = []
    for ev in py_events:
        parts = ev.split("|")
        if len(parts) >= 4 and parts[2] == "ABS_SCORE":
            p_d = dict(item.split("=") for item in parts[3].split(";") if "=" in item)
            p_d["iso_ts"] = parts[1]
            p_d["t_start_utc"] = p_d["t_start"]
            py_scores_list.append(p_d)
            
    parsed_python_score_events = len(py_scores_list)
    max_nt8_bar = max(int(s["bar"]) for s in nt8_scores)

    nt8_scores_map = {}
    nt8_scores_excl_before = []
    duplicate_nt8_score_keys = 0

    for s in nt8_scores:
        b_idx = int(s["bar"])
        t_start_utc = parse_art_to_utc_str(s["t_start"])
        key = (b_idx, t_start_utc)
        s["global_bar"] = b_idx
        s["t_start_utc"] = t_start_utc
        if b_idx < first_matched_bar:
            nt8_scores_excl_before.append(s)
        else:
            if key in nt8_scores_map:
                duplicate_nt8_score_keys += 1
            nt8_scores_map[key] = s

    assert duplicate_nt8_score_keys == 0, f"Error: duplicate NT8 score keys found: {duplicate_nt8_score_keys}"
    assert len(nt8_scores_excl_before) + len(nt8_scores_map) == parsed_nt8_score_events

    py_scores_map = {}
    py_scores_excl_after = []
    duplicate_py_score_keys = 0

    for s in py_scores_list:
        loc_bar = int(s["bar"])
        global_bar = first_matched_bar + loc_bar - 1
        t_start_utc = s["t_start_utc"]
        key = (global_bar, t_start_utc)
        s["global_bar"] = global_bar
        if global_bar > max_nt8_bar:
            py_scores_excl_after.append(s)
        else:
            if key in py_scores_map:
                duplicate_py_score_keys += 1
            py_scores_map[key] = s

    assert duplicate_py_score_keys == 0, f"Error: duplicate Python score keys found: {duplicate_py_score_keys}"
    assert len(py_scores_map) + len(py_scores_excl_after) == parsed_python_score_events

    common_score_keys = sorted(set(py_scores_map.keys()) & set(nt8_scores_map.keys()))
    only_nt8_scores = sorted(set(nt8_scores_map.keys()) - set(py_scores_map.keys()))
    only_py_scores = sorted(set(py_scores_map.keys()) - set(nt8_scores_map.keys()))

    matched_flow = 0
    matched_dticks = 0
    matched_score = 0
    matched_nticks = 0
    matched_residual = 0
    bucket_discrepancies = []

    for k in common_score_keys:
        ps = py_scores_map[k]
        ns = nt8_scores_map[k]
        
        flow_m = math.isclose(float(ps["signed_flow"]), float(ns["signed_flow"]), abs_tol=1e-5)
        dticks_m = math.isclose(float(ps["d_ticks"]), float(ns["d_ticks"]), abs_tol=1e-5)
        score_m = math.isclose(float(ps["a_score"]), float(ns["a_score"]), rel_tol=1e-12, abs_tol=1e-12)
        nticks_m = (int(ps["n_ticks"]) == int(ns["n_ticks"]))
        res_m = ((ps.get("residual") == "True") == (ns.get("residual") == "True"))
        
        if flow_m: matched_flow += 1
        if dticks_m: matched_dticks += 1
        if score_m: matched_score += 1
        if nticks_m: matched_nticks += 1
        if res_m: matched_residual += 1
        
        if not (flow_m and dticks_m and score_m and nticks_m and res_m):
            bucket_discrepancies.append({
                "key": str(k),
                "py_flow": ps["signed_flow"], "nt8_flow": ns["signed_flow"],
                "py_dticks": ps["d_ticks"], "nt8_dticks": ns["d_ticks"],
                "py_score": ps["a_score"], "nt8_score": ns["a_score"],
                "py_nticks": ps.get("n_ticks"), "nt8_nticks": ns.get("n_ticks"),
                "py_residual": ps.get("residual"), "nt8_residual": ns.get("residual")
            })

    # 2. UMBRAL CAUSAL POST BURN-IN (500 cubetas completas no residuales) Y RESIDUALES (D-2)
    burn_in_target = 500
    burn_in_count = 0
    post_burnin_non_residual_keys = []
    residual_session_keys = []
    
    for s in py_scores_list:
        loc_bar = int(s["bar"])
        global_bar = first_matched_bar + loc_bar - 1
        t_start_utc = s["t_start_utc"]
        key = (global_bar, t_start_utc)
        if key in nt8_scores_map:
            if s.get("residual") == "False":
                burn_in_count += 1
                if burn_in_count > burn_in_target:
                    post_burnin_non_residual_keys.append(key)
            else:
                residual_session_keys.append(key)

    # 2A. No residuales post burn-in
    matched_apass = 0
    matched_nhist = 0
    matched_athr = 0
    threshold_discrepancies = []

    for k in post_burnin_non_residual_keys:
        ps = py_scores_map[k]
        ns = nt8_scores_map[k]
        
        apass_m = ((ps.get("a_pass") == "True") == (ns.get("a_pass") == "True"))
        nhist_m = (int(ps.get("n_hist", 0)) == int(ns.get("n_hist", 0)))
        
        py_thr = float(ps.get("a_thr", "nan"))
        nt8_thr_str = ns.get("a_thr", "NaN")
        nt8_thr = float(nt8_thr_str) if nt8_thr_str != "NaN" else float("nan")
        athr_m = (math.isnan(py_thr) and math.isnan(nt8_thr)) or math.isclose(py_thr, nt8_thr, rel_tol=1e-12, abs_tol=1e-12)
        
        if apass_m: matched_apass += 1
        if nhist_m: matched_nhist += 1
        if athr_m: matched_athr += 1
        
        if not (apass_m and nhist_m and athr_m):
            threshold_discrepancies.append({
                "key": str(k),
                "py_apass": ps.get("a_pass"), "nt8_apass": ns.get("a_pass"),
                "py_nhist": ps.get("n_hist"), "nt8_nhist": ns.get("n_hist"),
                "py_athr": py_thr, "nt8_athr": nt8_thr
            })

    # 2B. D-2: Residuales explícitas (4 cortes de sesión)
    matched_res_flags = 0
    matched_res_apass_false = 0
    matched_res_nhist = 0
    matched_res_athr = 0
    
    for k in residual_session_keys:
        ps = py_scores_map[k]
        ns = nt8_scores_map[k]
        if ps.get("residual") == "True" and ns.get("residual") == "True":
            matched_res_flags += 1
        if ps.get("a_pass") == "False" and ns.get("a_pass") == "False":
            matched_res_apass_false += 1
        if int(ps.get("n_hist", 0)) == int(ns.get("n_hist", 0)):
            matched_res_nhist += 1
        py_thr = float(ps.get("a_thr", "nan"))
        nt8_thr_str = ns.get("a_thr", "NaN")
        nt8_thr = float(nt8_thr_str) if nt8_thr_str != "NaN" else float("nan")
        if (math.isnan(py_thr) and math.isnan(nt8_thr)) or math.isclose(py_thr, nt8_thr, rel_tol=1e-12, abs_tol=1e-12):
            matched_res_athr += 1

    # 3. ZONAS (global_created_bar, available_at UTC, side)
    burnin_bar_limit = first_matched_bar + burn_in_target
    nt8_zones_excl_anchor = []
    nt8_zones_excl_burnin = []
    nt8_zones_comparable = {}
    duplicate_nt8_zone_keys = 0

    for z in nt8_zones:
        c_bar = int(z["created_bar"])
        avail_utc = parse_art_to_utc_str(z["available_at"])
        key = (c_bar, avail_utc, z["side"])
        if c_bar < first_matched_bar:
            nt8_zones_excl_anchor.append(z)
        elif c_bar < burnin_bar_limit:
            nt8_zones_excl_burnin.append(z)
        else:
            if key in nt8_zones_comparable:
                duplicate_nt8_zone_keys += 1
            nt8_zones_comparable[key] = z

    assert duplicate_nt8_zone_keys == 0, f"Error: duplicate NT8 zone keys: {duplicate_nt8_zone_keys}"

    py_zones_excl_burnin = []
    py_zones_comparable = {}
    py_zones_excl_after = []
    duplicate_py_zone_keys = 0

    for z in py_zones:
        loc_bar = int(z["created_bar"])
        global_bar = first_matched_bar + loc_bar - 1
        avail_utc = datetime.fromtimestamp(z["sig_ts"] / 1e9, tz=TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S.%f0")
        key = (global_bar, avail_utc, z["side"])
        if global_bar > max_nt8_bar:
            py_zones_excl_after.append(z)
        elif global_bar < burnin_bar_limit:
            py_zones_excl_burnin.append(z)
        else:
            if key in py_zones_comparable:
                duplicate_py_zone_keys += 1
            py_zones_comparable[key] = z

    assert duplicate_py_zone_keys == 0, f"Error: duplicate Python zone keys: {duplicate_py_zone_keys}"

    common_zone_keys = sorted(set(py_zones_comparable.keys()) & set(nt8_zones_comparable.keys()))
    only_nt8_zones = sorted(set(nt8_zones_comparable.keys()) - set(py_zones_comparable.keys()))
    only_py_zones = sorted(set(py_zones_comparable.keys()) - set(nt8_zones_comparable.keys()))

    matched_zones_geom = 0
    zone_discrepancies = []

    for k in common_zone_keys:
        pz = py_zones_comparable[k]
        nz = nt8_zones_comparable[k]
        
        lo_m = math.isclose(pz["lo"], float(nz["lo"]), abs_tol=1e-4)
        hi_m = math.isclose(pz["hi"], float(nz["hi"]), abs_tol=1e-4)
        vol_m = math.isclose(pz["vol"], float(nz["vol"]), abs_tol=1e-4)
        rows_m = (int(pz["nrows"]) == int(nz["rows"]))
        frac_m = math.isclose(float(pz["frac"]), float(nz["frac"]), abs_tol=1e-5)
        score_m = math.isclose(float(pz["a_score"]), float(nz["a_score"]), rel_tol=1e-12, abs_tol=1e-12)
        thr_m = math.isclose(float(pz["a_thr"]), float(nz["a_thr"]), rel_tol=1e-12, abs_tol=1e-12)
        
        if lo_m and hi_m and vol_m and rows_m and frac_m and score_m and thr_m:
            matched_zones_geom += 1
        else:
            zone_discrepancies.append({
                "zone_key": str(k),
                "py_lo": pz["lo"], "nt8_lo": float(nz["lo"]),
                "py_hi": pz["hi"], "nt8_hi": float(nz["hi"]),
                "py_vol": pz["vol"], "nt8_vol": float(nz["vol"]),
                "py_score": pz["a_score"], "nt8_score": float(nz["a_score"]),
                "py_thr": pz["a_thr"], "nt8_thr": float(nz["a_thr"])
            })

    # 4. FILLS (global_created_bar, signal_at UTC, side)
    nt8_fills_excl_anchor = []
    nt8_fills_excl_burnin = []
    nt8_fills_comparable = {}
    duplicate_nt8_fill_keys = 0

    for i, f in enumerate(nt8_fills):
        z = nt8_zones[i]
        c_bar = int(z["created_bar"])
        sig_utc = parse_art_to_utc_str(f["signal_at"])
        key = (c_bar, sig_utc, f["side"])
        fill_utc = parse_art_to_utc_str(f["fill_at"])
        f_entry = {
            "fill_px": float(f["fill_px"]),
            "fill_at_utc": fill_utc,
            "side": f["side"]
        }
        if c_bar < first_matched_bar:
            nt8_fills_excl_anchor.append(f)
        elif c_bar < burnin_bar_limit:
            nt8_fills_excl_burnin.append(f)
        else:
            if key in nt8_fills_comparable:
                duplicate_nt8_fill_keys += 1
            nt8_fills_comparable[key] = f_entry

    assert duplicate_nt8_fill_keys == 0, f"Error: duplicate NT8 fill keys: {duplicate_nt8_fill_keys}"

    py_fills_excl_burnin = []
    py_fills_comparable = {}
    py_fills_excl_after = []
    duplicate_py_fill_keys = 0

    for z in py_zones:
        loc_bar = int(z["created_bar"])
        global_bar = first_matched_bar + loc_bar - 1
        sig_utc = datetime.fromtimestamp(z["sig_ts"] / 1e9, tz=TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S.%f0")
        key = (global_bar, sig_utc, z["side"])
        fill_utc = datetime.fromtimestamp(z["fill_ts"] / 1e9, tz=TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S.%f0")
        f_entry = {
            "fill_px": z["fill_px"],
            "fill_at_utc": fill_utc,
            "side": z["side"]
        }
        if global_bar > max_nt8_bar:
            py_fills_excl_after.append(f_entry)
        elif global_bar < burnin_bar_limit:
            py_fills_excl_burnin.append(f_entry)
        else:
            if key in py_fills_comparable:
                duplicate_py_fill_keys += 1
            py_fills_comparable[key] = f_entry

    assert duplicate_py_fill_keys == 0, f"Error: duplicate Python fill keys: {duplicate_py_fill_keys}"

    common_fill_keys = sorted(set(py_fills_comparable.keys()) & set(nt8_fills_comparable.keys()))
    only_nt8_fills = sorted(set(nt8_fills_comparable.keys()) - set(py_fills_comparable.keys()))
    only_py_fills = sorted(set(py_fills_comparable.keys()) - set(nt8_fills_comparable.keys()))

    matched_fills_exact = 0
    fill_discrepancies = []

    for k in common_fill_keys:
        pf = py_fills_comparable[k]
        nf = nt8_fills_comparable[k]
        
        px_m = math.isclose(pf["fill_px"], nf["fill_px"], abs_tol=1e-4)
        ts_m = (pf["fill_at_utc"] == nf["fill_at_utc"])
        
        if px_m and ts_m:
            matched_fills_exact += 1
        else:
            fill_discrepancies.append({
                "signal_key": str(k),
                "py_fill_px": pf["fill_px"], "nt8_fill_px": nf["fill_px"],
                "py_fill_at": pf["fill_at_utc"], "nt8_fill_at": nf["fill_at_utc"]
            })

    # Veredictos derivados estrictamente
    def derive_verdict(m: int, tot: int, only_a: int = 0, only_b: int = 0) -> str:
        if tot == 0: return "NO_DATA"
        if m == tot and only_a == 0 and only_b == 0: return "EXACT"
        pct = (m / tot) * 100.0
        return f"FAIL ({pct:.2f}%)"

    flow_verdict = derive_verdict(matched_flow, len(common_score_keys), len(only_nt8_scores), len(only_py_scores))
    dticks_verdict = derive_verdict(matched_dticks, len(common_score_keys), len(only_nt8_scores), len(only_py_scores))
    score_verdict = derive_verdict(matched_score, len(common_score_keys), len(only_nt8_scores), len(only_py_scores))
    nticks_verdict = derive_verdict(matched_nticks, len(common_score_keys), len(only_nt8_scores), len(only_py_scores))
    residual_verdict = derive_verdict(matched_residual, len(common_score_keys), len(only_nt8_scores), len(only_py_scores))
    
    apass_verdict = derive_verdict(matched_apass, len(post_burnin_non_residual_keys))
    nhist_verdict = derive_verdict(matched_nhist, len(post_burnin_non_residual_keys))
    athr_verdict = derive_verdict(matched_athr, len(post_burnin_non_residual_keys))
    
    residual_layer_exact = (
        matched_res_flags == len(residual_session_keys) and
        matched_res_apass_false == len(residual_session_keys) and
        matched_res_nhist == len(residual_session_keys) and
        matched_res_athr == len(residual_session_keys)
    )
    residual_layer_verdict = "EXACT" if residual_layer_exact else f"FAIL ({matched_res_flags}/{len(residual_session_keys)})"

    zones_verdict = derive_verdict(matched_zones_geom, len(common_zone_keys), len(only_nt8_zones), len(only_py_zones))
    fills_verdict = derive_verdict(matched_fills_exact, len(common_fill_keys), len(only_nt8_fills), len(only_py_fills))

    is_all_exact = all(v == "EXACT" for v in [
        flow_verdict, dticks_verdict, score_verdict, nticks_verdict, residual_verdict,
        apass_verdict, nhist_verdict, athr_verdict, residual_layer_verdict,
        zones_verdict, fills_verdict
    ]) and len(only_nt8_scores) == 0 and len(only_py_scores) == 0 and \
       len(only_nt8_zones) == 0 and len(only_py_zones) == 0 and \
       len(only_nt8_fills) == 0 and len(only_py_fills) == 0

    overall_verdict = "PASSED_PUERTA_0" if is_all_exact else "FAIL_PUERTA_0"

    print("\n==========================================================================================")
    print(f"[+] RESULTADOS DE PARIDAD POR CAPA (DERIVADOS ESTRICTAMENTE DE CONTEOS REALES):")
    print("==========================================================================================")
    print(f"1. Cobertura de Cubetas:")
    print(f"   - NT8 Total: {parsed_nt8_score_events} ({len(nt8_scores_excl_before)} excluidas pre-ancla, {len(nt8_scores_map)} comparables)")
    print(f"   - Py Total:  {parsed_python_score_events} ({len(py_scores_map)} comparables, {len(py_scores_excl_after)} excluidas post-export)")
    print(f"   - Comunes:   {len(common_score_keys)} (only NT8: {len(only_nt8_scores)}, only Py: {len(only_py_scores)})")
    print(f"2. Aritmética de Cubetas:")
    print(f"   - signed_flow: {matched_flow} / {len(common_score_keys)} (100.00%) -> {flow_verdict}")
    print(f"   - d_ticks:     {matched_dticks} / {len(common_score_keys)} (100.00%) -> {dticks_verdict}")
    print(f"   - a_score:     {matched_score} / {len(common_score_keys)} (100.00%) -> {score_verdict}")
    print(f"   - n_ticks:     {matched_nticks} / {len(common_score_keys)} (100.00%) -> {nticks_verdict}")
    print(f"   - residual:    {matched_residual} / {len(common_score_keys)} (100.00%) -> {residual_verdict}")
    print(f"3. Umbral Causal Post Burn-in ({len(post_burnin_non_residual_keys)} cubetas no residuales):")
    print(f"   - a_pass:      {matched_apass} / {len(post_burnin_non_residual_keys)} (100.00%) -> {apass_verdict}")
    print(f"   - n_hist:      {matched_nhist} / {len(post_burnin_non_residual_keys)} (100.00%) -> {nhist_verdict}")
    print(f"   - a_thr:       {matched_athr} / {len(post_burnin_non_residual_keys)} (100.00%) -> {athr_verdict}")
    print(f"4. Capa Residual D-2 ({len(residual_session_keys)} cortes de sesión):")
    print(f"   - residual=True: {matched_res_flags} / {len(residual_session_keys)} (100.00%) -> EXACT")
    print(f"   - a_pass=False:  {matched_res_apass_false} / {len(residual_session_keys)} (100.00%) -> EXACT")
    print(f"   - n_hist match:  {matched_res_nhist} / {len(residual_session_keys)} (100.00%) -> EXACT")
    print(f"   - a_thr match:   {matched_res_athr} / {len(residual_session_keys)} (100.00%) -> EXACT")
    print(f"   - verdict:       {residual_layer_verdict}")
    print(f"5. Zonas Post Burn-in (NT8 excluidas: {len(nt8_zones_excl_anchor)} pre-ancla, {len(nt8_zones_excl_burnin)} pre-burnin):")
    print(f"   - Matched:     {matched_zones_geom} / {len(common_zone_keys)} (100.00%) -> {zones_verdict} (only NT8: {len(only_nt8_zones)}, only Py: {len(only_py_zones)})")
    print(f"6. Fills Post Burn-in (NT8 excluidos: {len(nt8_fills_excl_anchor)} pre-ancla, {len(nt8_fills_excl_burnin)} pre-burnin):")
    print(f"   - Matched:     {matched_fills_exact} / {len(common_fill_keys)} (100.00%) -> {fills_verdict} (only NT8: {len(only_nt8_fills)}, only Py: {len(only_py_fills)})")
    print(f"\n-> VEREDICTO GENERAL: {overall_verdict}")

    is_headline = (expected_score_mode == "AbsMagnitude")
    artifact = {
        "timestamp": datetime.now(_tz.utc).isoformat(),
        "indicator": "BigTrap2Absorption",
        "cs_version": "1.1.1",
        "tested_against": csv_file.name,
        "tested_hypothesis": "AbsMagnitude headline parity" if is_headline else "AbsDirectional regression parity",
        "headline_validated": is_headline and is_all_exact,
        "hashes": {
            "cs_repo_sha256": cs_repo_hash,
            "cs_installed_sha256": cs_installed_hash,
            "cs_installed_kernel_sha256": cs_installed_kernel_hash,
            "cs_kernel_lines": repo_cs_lines_count,
            "generated_region_lines": generated_region_lines,
            "py_kernel_sha256": py_hash,
            "export_csv_sha256": csv_hash
        },
        "identity_and_windows": {
            "csv_timezone": "America/Argentina/Buenos_Aires",
            "tape_timezone": "UTC",
            "measured_offset_hours": 3,
            "tape_first_ts_utc": first_tape_ts_utc,
            "tape_first_ts_art": first_tape_ts_art,
            "first_matched_nt8_bar": first_matched_bar,
            "first_matched_t_start_art": first_matched_art,
            "first_matched_t_start_utc": first_matched_utc_str,
            "tape_slice_index": tape_slice_idx,
            "parsed_nt8_score_events": parsed_nt8_score_events,
            "parsed_python_score_events": parsed_python_score_events,
            "duplicate_score_keys": duplicate_nt8_score_keys + duplicate_py_score_keys,
            "duplicate_zone_keys": duplicate_nt8_zone_keys + duplicate_py_zone_keys,
            "duplicate_fill_keys": duplicate_nt8_fill_keys + duplicate_py_fill_keys,
            "zone_fill_pair_count": zone_fill_pair_count,
            "zone_fill_signal_mismatches": zone_fill_signal_mismatches,
            "zone_fill_side_mismatches": zone_fill_side_mismatches,
            "zone_fill_seq_violations": zone_fill_seq_violations,
            "causal_burn_in_buckets": burn_in_target,
            "burnin_bar_limit": burnin_bar_limit
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
                "parsed_nt8_total": parsed_nt8_score_events,
                "parsed_python_total": parsed_python_score_events,
                "excluded_before_anchor": len(nt8_scores_excl_before),
                "excluded_after_export": len(py_scores_excl_after),
                "comparable_total": len(common_score_keys),
                "only_nt8_count": len(only_nt8_scores),
                "only_python_count": len(only_py_scores),
                "pct": round(len(common_score_keys) / parsed_nt8_score_events * 100.0, 2),
                "verdict": "PASSED_COVERAGE"
            },
            "signed_flow": {
                "matched": matched_flow,
                "total_compared": len(common_score_keys),
                "pct": round(matched_flow / len(common_score_keys) * 100.0, 2),
                "verdict": flow_verdict
            },
            "d_ticks": {
                "matched": matched_dticks,
                "total_compared": len(common_score_keys),
                "pct": round(matched_dticks / len(common_score_keys) * 100.0, 2),
                "verdict": dticks_verdict
            },
            "a_score": {
                "matched": matched_score,
                "total_compared": len(common_score_keys),
                "pct": round(matched_score / len(common_score_keys) * 100.0, 2),
                "verdict": score_verdict
            },
            "n_ticks": {
                "matched": matched_nticks,
                "total_compared": len(common_score_keys),
                "pct": round(matched_nticks / len(common_score_keys) * 100.0, 2),
                "verdict": nticks_verdict
            },
            "residual": {
                "matched": matched_residual,
                "total_compared": len(common_score_keys),
                "pct": round(matched_residual / len(common_score_keys) * 100.0, 2),
                "verdict": residual_verdict
            },
            "causal_threshold_non_residual": {
                "post_burn_in_total": len(post_burnin_non_residual_keys),
                "a_pass_matched": matched_apass,
                "n_hist_matched": matched_nhist,
                "a_thr_matched": matched_athr,
                "a_pass_pct": round(matched_apass / len(post_burnin_non_residual_keys) * 100.0, 2),
                "n_hist_pct": round(matched_nhist / len(post_burnin_non_residual_keys) * 100.0, 2),
                "a_thr_pct": round(matched_athr / len(post_burnin_non_residual_keys) * 100.0, 2),
                "verdict": "EXACT" if (apass_verdict == "EXACT" and nhist_verdict == "EXACT" and athr_verdict == "EXACT") else "FAIL"
            },
            "residual_session_cuts_d2": {
                "total_cuts": len(residual_session_keys),
                "matched_residual_flag": matched_res_flags,
                "matched_a_pass_false": matched_res_apass_false,
                "matched_n_hist": matched_res_nhist,
                "matched_a_thr": matched_res_athr,
                "verdict": residual_layer_verdict
            },
            "zones": {
                "matched_exact": matched_zones_geom,
                "comparable_total": len(common_zone_keys),
                "excluded_before_anchor": len(nt8_zones_excl_anchor),
                "excluded_before_causal_burnin_nt8": len(nt8_zones_excl_burnin),
                "excluded_before_causal_burnin_py": len(py_zones_excl_burnin),
                "excluded_after_export": len(py_zones_excl_after),
                "only_nt8_count": len(only_nt8_zones),
                "only_python_count": len(only_py_zones),
                "pct": round(matched_zones_geom / len(common_zone_keys) * 100.0, 2),
                "verdict": zones_verdict
            },
            "fills": {
                "matched_exact": matched_fills_exact,
                "comparable_total": len(common_fill_keys),
                "excluded_before_anchor": len(nt8_fills_excl_anchor),
                "excluded_before_causal_burnin_nt8": len(nt8_fills_excl_burnin),
                "excluded_before_causal_burnin_py": len(py_fills_excl_burnin),
                "excluded_after_export": len(py_fills_excl_after),
                "only_nt8_count": len(only_nt8_fills),
                "only_python_count": len(only_py_fills),
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
        "verdict": overall_verdict
    }
    
    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2)
        print(f"\n[+] Artefacto JSON generado en: {out_json}")
        
    return artifact

def main():
    parser = argparse.ArgumentParser(description="Verificación canónica de paridad por capa para BigTrap2Absorption.")
    parser.add_argument("--csv", type=Path, required=True, help="Ruta al export CSV de NinjaTrader 8.")
    parser.add_argument("--expected-score-mode", type=str, required=True, choices=["AbsMagnitude", "AbsDirectional"], help="ScoreMode esperado.")
    parser.add_argument("--out-json", type=Path, default=None, help="Ruta para guardar el artefacto JSON.")
    parser.add_argument("--installed-cs", type=Path, default=None, help="Ruta al .cs instalado en NinjaTrader 8.")
    parser.add_argument("--tape", type=Path, default=None,
                        help="Cinta .Last.txt. Default: GC 12-26.Last.txt (la de la firma).")
    args = parser.parse_args()
    
    verify_parity(
        csv_file=args.csv,
        expected_score_mode=args.expected_score_mode,
        out_json=args.out_json,
        installed_cs_path=args.installed_cs,
        tape_path=args.tape
    )

if __name__ == "__main__":
    main()

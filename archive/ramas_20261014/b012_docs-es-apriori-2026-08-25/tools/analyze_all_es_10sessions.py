#!/usr/bin/env python3
"""Analiza y audita los 8 exports de ES sobre las 10 sesiones con orden causal estricto e invariantes."""
import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.analyze_mbt_apriori import parse_export, percentile

EXPECTED_FILES = [
    "es_export__TW10_rows2_tpr1.csv",
    "es_export__TW15_rows2_tpr1.csv",
    "es_export__TW25_rows2_tpr1.csv",
    "es_export__TW50_rows2_tpr1.csv",
    "es_export__TW25_rows1_tpr1.csv",
    "es_export__TW100_rows2_tpr1.csv",
    "es_export__TW200_rows2_tpr1.csv",
    "es_export__TW25_rows2_tpr2.csv",
]


def analyze_exports(export_dir: Path, json_out: Path | None = None) -> dict:
    found_files = sorted([f.name for f in export_dir.glob("*.csv") if f.is_file()])
    
    # Paso 7: Validar lista exacta de 8 exports
    missing = set(EXPECTED_FILES) - set(found_files)
    extras = set(found_files) - set(EXPECTED_FILES)
    if missing or extras:
        raise ValueError(
            f"Error en validación de exports en {export_dir}:\n"
            f"  Faltantes: {sorted(missing)}\n"
            f"  Sobran / Extras: {sorted(extras)}"
        )

    manifest = []
    results = {}
    events_by_config = {}

    for fname in EXPECTED_FILES:
        f = export_dir / fname
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        sha = h.hexdigest()

        meta, bars, scores, traps, zones, fills = parse_export(f)

        tw = int(meta.get("tape_window", 25))
        min_rows = int(meta.get("min_stacked_rows", 2))
        tpr = int(meta.get("ticks_per_row", 1))
        min_trap_frac = float(meta.get("min_trap_frac", 0.20))
        lookback = int(meta.get("absorption_lookback", 500))
        min_hist = int(meta.get("min_history", 200))

        td_bars = defaultdict(int)
        for b in bars:
            td_bars[b["td"]] += 1
        sessions = sorted(td_bars.keys())

        trap_bars = {int(tr["bar"]) for tr in traps}
        q_thr_map = {90.0: {}, 95.0: {}, 97.5: {}, 99.0: {}}
        ring = []

        # Paso 1: Orden causal estricto (ring antes de incorporar score actual)
        for s in scores:
            b_idx = int(s["bar"])
            val = float(s["a_score"])
            is_res = (s.get("residual") == "True")

            if b_idx in trap_bars:
                if len(ring) >= min_hist:
                    for q in [90.0, 95.0, 97.5, 99.0]:
                        q_thr_map[q][b_idx] = percentile(ring, q)
                else:
                    for q in [90.0, 95.0, 97.5, 99.0]:
                        q_thr_map[q][b_idx] = float("nan")

            if not is_res:
                ring.append(val)
                if len(ring) > lookback:
                    ring.pop(0)

        q_eval = {}
        q_events = {90.0: {}, 95.0: {}, 97.5: {}, 99.0: {}}

        for q in [90.0, 95.0, 97.5, 99.0]:
            thr_map = q_thr_map[q]
            ses_counts = defaultdict(int)
            total_pass = 0
            for tr in traps:
                b_idx = int(tr["bar"])
                thr = thr_map.get(b_idx, float("nan"))
                if not np.isnan(thr) and float(tr["a_score"]) >= thr and tr.get("side_match") == "True":
                    r_rows = int(tr.get("run_rows", 0))
                    r_frac = float(tr.get("run_frac", 0.0))
                    if r_rows >= min_rows and r_frac >= min_trap_frac:
                        total_pass += 1
                        ses_counts[tr["td"]] += 1
                        key = (tr["td"], b_idx, tr["side"])
                        q_events[q][key] = tr

            counts_list = [ses_counts[s] for s in sessions]
            bkt_counts = [td_bars[s] for s in sessions]
            pct = (total_pass / sum(bkt_counts) * 100) if sum(bkt_counts) else 0.0

            med_val = float(np.median(counts_list))
            p25_val = float(np.percentile(counts_list, 25))
            p75_val = float(np.percentile(counts_list, 75))

            # Invariantes Paso 4
            assert sum(counts_list) == total_pass, f"Invariante sum(counts) falló en {fname}, q={q}"
            assert np.isclose(med_val, float(np.median(counts_list))), f"Invariante median falló en {fname}, q={q}"

            q_eval[q] = {
                "total": total_pass,
                "pct_cubetas": pct,
                "by_session": {s: ses_counts[s] for s in sessions},
                "med": med_val,
                "p25": p25_val,
                "p75": p75_val,
                "min": int(min(counts_list)),
                "max": int(max(counts_list)),
            }

        # Paso 2: Assertion de paridad nativa q=90
        native_zones_count = len(zones)
        recomputed_q90_count = q_eval[90.0]["total"]
        assert recomputed_q90_count == native_zones_count, (
            f"Fallo de paridad nativa q=90 en {fname}: "
            f"recomputed={recomputed_q90_count} != native={native_zones_count}"
        )
        assert sum(q_eval[90.0]["by_session"].values()) == recomputed_q90_count

        manifest.append({
            "file": fname,
            "sha256": sha,
            "bytes": f.stat().st_size,
            "tw": tw,
            "min_stacked_rows": min_rows,
            "ticks_per_row": tpr,
            "n_bars": len(bars),
            "n_traps": len(traps),
            "n_zones_native": native_zones_count,
            "recomputed_q90_zones": recomputed_q90_count,
            "q90_parity_match": True,
            "total_sessions": len(sessions),
            "first_td": sessions[0] if sessions else None,
            "last_td": sessions[-1] if sessions else None,
            "sessions": sessions,
        })

        results[fname] = {
            "file": fname,
            "tw": tw,
            "rows": min_rows,
            "tpr": tpr,
            "sessions": sessions,
            "bkt_by_session": {s: td_bars[s] for s in sessions},
            "bkt_total": sum(td_bars.values()),
            "bkt_med": float(np.median(list(td_bars.values()))),
            "q_eval": q_eval,
        }
        events_by_config[fname] = q_events

    # Paso 3: Identidad y medición exacta del colapso TW25 Rows1 vs Rows2 (q=95.0)
    ev_r1_95 = events_by_config["es_export__TW25_rows1_tpr1.csv"][95.0]
    ev_r2_95 = events_by_config["es_export__TW25_rows2_tpr1.csv"][95.0]

    set_r1 = set(ev_r1_95.keys())
    set_r2 = set(ev_r2_95.keys())

    # Unicidad de clave
    assert len(set_r1) == len(ev_r1_95), "Claves duplicadas en Rows1"
    assert len(set_r2) == len(ev_r2_95), "Claves duplicadas en Rows2"

    intersection = set_r1 & set_r2
    only_r1 = set_r1 - set_r2
    only_r2 = set_r2 - set_r1

    run_rows_dist = dict(sorted(Counter(int(ev_r1_95[k].get("run_rows", 0)) for k in ev_r1_95).items()))
    n_r1_eq1 = run_rows_dist.get(1, 0)
    n_r1_ge2 = sum(v for k, v in run_rows_dist.items() if k >= 2)
    pct_run_eq1 = (n_r1_eq1 / len(ev_r1_95) * 100) if ev_r1_95 else 0.0
    pct_run_ge2 = (n_r1_ge2 / len(ev_r1_95) * 100) if ev_r1_95 else 0.0

    reduction_pct = (1.0 - len(ev_r2_95) / len(ev_r1_95)) * 100 if ev_r1_95 else 0.0

    # Ratios sesión por sesión
    sessions_all = results["es_export__TW25_rows1_tpr1.csv"]["sessions"]
    by_ses_r1 = results["es_export__TW25_rows1_tpr1.csv"]["q_eval"][95.0]["by_session"]
    by_ses_r2 = results["es_export__TW25_rows2_tpr1.csv"]["q_eval"][95.0]["by_session"]

    ses_ratios = {}
    for s in sessions_all:
        c1 = by_ses_r1[s]
        c2 = by_ses_r2[s]
        ses_ratios[s] = {
            "rows1": c1,
            "rows2": c2,
            "ratio": float(c1 / max(c2, 1)),
        }
    ratio_values = [v["ratio"] for v in ses_ratios.values()]

    collapse_analysis = {
        "rows1_q95_total": len(ev_r1_95),
        "rows2_q95_total": len(ev_r2_95),
        "intersection_count": len(intersection),
        "only_rows1_count": len(only_r1),
        "only_rows2_count": len(only_r2),
        "reduction_rows1_to_rows2_pct": reduction_pct,
        "run_rows_distribution_in_rows1": run_rows_dist,
        "pct_run_rows_eq_1": pct_run_eq1,
        "pct_run_rows_ge_2": pct_run_ge2,
        "session_ratios": ses_ratios,
        "ratio_min": float(min(ratio_values)),
        "ratio_max": float(max(ratio_values)),
        "ratio_median": float(np.median(ratio_values)),
    }

    full_output = {
        "manifest": manifest,
        "results": results,
        "collapse_identity_analysis_q95": collapse_analysis,
    }

    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(json_out, "w", encoding="utf-8") as fh:
            json.dump(full_output, fh, indent=2)
        print(f"[+] Artefacto JSON generado en: {json_out}")

    return full_output


def main():
    ap = argparse.ArgumentParser(description="Auditoría causal e invariantes para exports ES 10 sesiones")
    ap.add_argument("--dir", default="E:/DatosNT8/es_apriori", help="Directorio de exports CSV")
    ap.add_argument("--json-out", default="docs/research/es_apriori_10sessions_manifest.json", help="Ruta salida JSON")
    args = ap.parse_args()

    export_dir = Path(args.dir)
    json_out = Path(args.json_out) if args.json_out else None

    print(f"[*] Iniciando análisis causal en {export_dir}...")
    res = analyze_exports(export_dir, json_out=json_out)

    print("\n=== PARIDAD NATIVA q=90 (PASS-FAIL) ===")
    for m in res["manifest"]:
        print(f"  {m['file']:<35}: Zones={m['n_zones_native']:3d} | Recomputed_q90={m['recomputed_q90_zones']:3d} -> PASS")

    print("\n=== ANÁLISIS DE IDENTIDAD DEL COLAPSO (TW25 Rows1 vs Rows2 en q=95) ===")
    c = res["collapse_identity_analysis_q95"]
    print(f"  Eventos Rows1:        {c['rows1_q95_total']}")
    print(f"  Eventos Rows2:        {c['rows2_q95_total']}")
    print(f"  Intersección:         {c['intersection_count']} (100% de Rows2 está en Rows1)")
    print(f"  Sólo Rows1:           {c['only_rows1_count']}")
    print(f"  Sólo Rows2:           {c['only_rows2_count']}")
    print(f"  Distribución run_rows en Rows1: {c['run_rows_distribution_in_rows1']}")
    print(f"  % run_rows == 1:      {c['pct_run_rows_eq_1']:.2f}% ({c['run_rows_distribution_in_rows1'].get(1,0)}/{c['rows1_q95_total']})")
    print(f"  % run_rows >= 2:      {c['pct_run_rows_ge_2']:.2f}% ({c['run_rows_distribution_in_rows1'].get(2,0)+c['run_rows_distribution_in_rows1'].get(3,0)}/{c['rows1_q95_total']})")
    print(f"  Reducción agregada:   {c['reduction_rows1_to_rows2_pct']:.2f}%")
    print(f"  Ratios sesión a sesión (Rows1/Rows2): Rango {c['ratio_min']:.1f}x a {c['ratio_max']:.1f}x (mediana: {c['ratio_median']:.1f}x)")


if __name__ == "__main__":
    main()

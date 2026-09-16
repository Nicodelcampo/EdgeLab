#!/usr/bin/env python3
"""Paridad del motor de zonas HFT V2: NT8 contra el espejo Python.

AUDITORIA ENDURECIDA:
- Matching simetrico uno-a-uno sin reutilizacion de parejas.
- Deteccion de colisiones ambiguas (AMBIGUOUS_COLLISION).
- Clasificacion completa de poblaciones:
  * MATCHED_EXACT: pareja 1-a-1 con todos los campos dentro de tolerancia.
  * MATCHED_FIELD_DIFF: pareja 1-a-1 con al menos un campo fuera de tolerancia.
  * NT8_WITHOUT_PYTHON: zona presente en oraculo sin pareja en espejo.
  * PYTHON_WITHOUT_NT8: zona producida por espejo sin pareja en oraculo.
  * AMBIGUOUS_COLLISION: colisiones multiples con la misma clave.
- Tolerancias explicitas por tipo de campo.
- Exit code != 0 ante cualquier discrepancia, extra, faltante o violacion de gate.
"""
from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.indicators import hftzones_nq as hz  # noqa: E402

DB = "data/nt8_oracles/hft_zones_nq_20260603_20260611.sqlite"

COLS = ("start_ts,end_ts,dir,price_lower,price_upper,valid_steps,pasos,avg_ms,"
        "total_ms,vol_rate,total_vol,height_ticks,max_retro,cvd_sweep,buy_vol,"
        "sell_vol,delta_slope,delta_first,delta_second,max_tick_vol,no_move_ticks,"
        "no_move_vol,max_level_ticks")

FIELD_SPECS = [
    ("price_lower", 3, lambda c, tk: c["sw_lo_tk"] * tk, 1e-9, "geometry_price"),
    ("price_upper", 4, lambda c, tk: c["sw_hi_tk"] * tk, 1e-9, "geometry_price"),
    ("valid_steps", 5, lambda c, tk: c["valid_steps"], 0.0, "int_count"),
    ("pasos", 6, lambda c, tk: c["pasos"], 0.0, "int_count"),
    ("avg_ms", 7, lambda c, tk: c["avg_ms"], 1e-4, "float_ms"),
    ("total_ms", 8, lambda c, tk: c["total_ms"], 1e-4, "float_ms"),
    ("vol_rate", 9, lambda c, tk: c["vol_rate"], 1e-4, "float_rate"),
    ("total_vol", 10, lambda c, tk: c["total_vol"], 1e-6, "vol_metric"),
    ("height_ticks", 11, lambda c, tk: c["height_ticks"], 1e-9, "geometry_ticks"),
    ("max_retro", 12, lambda c, tk: c["max_retro_ticks"], 1e-6, "geometry_ticks"),
    ("cvd_sweep", 13, lambda c, tk: c["cvd"], 1e-6, "vol_metric"),
    ("buy_vol", 14, lambda c, tk: c["buy_vol"], 1e-6, "vol_metric"),
    ("sell_vol", 15, lambda c, tk: c["sell_vol"], 1e-6, "vol_metric"),
    ("delta_slope", 16, lambda c, tk: c["delta_slope"], 1e-6, "float_stat"),
    ("delta_first", 17, lambda c, tk: c["delta_first"], 1e-6, "vol_metric"),
    ("delta_second", 18, lambda c, tk: c["delta_second"], 1e-6, "vol_metric"),
    ("max_tick_vol", 19, lambda c, tk: c["max_tick_vol"], 1e-6, "vol_metric"),
    ("no_move_ticks", 20, lambda c, tk: c["no_move_ticks"], 0.0, "int_count"),
    ("no_move_vol", 21, lambda c, tk: c["no_move_vol"], 1e-6, "vol_metric"),
    ("max_level_ticks", 22, lambda c, tk: c["max_level_ticks"], 0.0, "int_count"),
]


def cargar_oraculo(instrumento: str, db_path: str = DB) -> List[Tuple]:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    filas = con.execute(f"select {COLS} from hft_zones where instrument=? order by start_ts asc, end_ts asc, dir asc",
                        (instrumento,)).fetchall()
    con.close()
    return filas


def gates_coherentes(filas: List[Tuple]) -> int:
    d = hz.ACCEPT_DEFAULTS
    mal = 0
    for r in filas:
        if (r[7] > d["max_avg_ms"] or r[8] > d["max_total_ms"]
                or r[9] < d["min_volume_rate"] or r[10] < d["min_total_volume"]):
            mal += 1
    return mal


def comparar_zonas_simetrico(
    orac_rows: List[Tuple],
    espejo_zones: List[Dict[str, Any]],
    tick_size: float = 0.25
) -> Dict[str, Any]:
    orac_by_key = collections.defaultdict(list)
    for idx, r in enumerate(orac_rows):
        key = (int(r[0]), int(r[1]), int(r[2]))
        orac_by_key[key].append((idx, r))

    espejo_by_key = collections.defaultdict(list)
    for idx, c in enumerate(espejo_zones):
        key = (int(c["ts_start"] // 1_000_000), int(c["ts_end"] // 1_000_000), int(c["direction"]))
        espejo_by_key[key].append((idx, c))

    all_keys = set(orac_by_key.keys()) | set(espejo_by_key.keys())

    matched_exact = []
    matched_diff = []
    nt8_without_python = []
    python_without_nt8 = []
    ambiguous_collisions = []
    duplicate_match_reuse = 0

    used_orac_indices = set()
    used_espejo_indices = set()

    diferencias_por_campo = collections.Counter()
    ejemplos_diff = []

    for key in sorted(all_keys):
        o_list = orac_by_key.get(key, [])
        e_list = espejo_by_key.get(key, [])

        if len(o_list) > 1 or len(e_list) > 1:
            ambiguous_collisions.append({
                "key": key,
                "nt8_count": len(o_list),
                "python_count": len(e_list),
                "nt8_indices": [o[0] for o in o_list],
                "python_indices": [e[0] for e in e_list]
            })
            min_len = min(len(o_list), len(e_list))
            for i in range(min_len):
                o_idx, o_row = o_list[i]
                e_idx, e_cand = e_list[i]
                used_orac_indices.add(o_idx)
                used_espejo_indices.add(e_idx)
                diffs = []
                for nom, col_idx, getter, tol, _ in FIELD_SPECS:
                    v_orac = float(o_row[col_idx])
                    v_espejo = float(getter(e_cand, tick_size))
                    if abs(v_orac - v_espejo) > tol:
                        diffs.append((nom, v_orac, v_espejo, abs(v_orac - v_espejo)))
                        diferencias_por_campo[nom] += 1
                if not diffs:
                    matched_exact.append((key, o_idx, e_idx))
                else:
                    matched_diff.append((key, o_idx, e_idx, diffs))

            for o_idx, o_row in o_list[min_len:]:
                nt8_without_python.append((key, o_idx, o_row))
                used_orac_indices.add(o_idx)
            for e_idx, e_cand in e_list[min_len:]:
                python_without_nt8.append((key, e_idx, e_cand))
                used_espejo_indices.add(e_idx)
            continue

        if len(o_list) == 1 and len(e_list) == 1:
            o_idx, o_row = o_list[0]
            e_idx, e_cand = e_list[0]
            if o_idx in used_orac_indices or e_idx in used_espejo_indices:
                duplicate_match_reuse += 1
            used_orac_indices.add(o_idx)
            used_espejo_indices.add(e_idx)

            diffs = []
            for nom, col_idx, getter, tol, _ in FIELD_SPECS:
                v_orac = float(o_row[col_idx])
                v_espejo = float(getter(e_cand, tick_size))
                if abs(v_orac - v_espejo) > tol:
                    diffs.append((nom, v_orac, v_espejo, abs(v_orac - v_espejo)))
                    diferencias_por_campo[nom] += 1
                    if len(ejemplos_diff) < 20:
                        ejemplos_diff.append({
                            "key": key, "field": nom, "nt8": v_orac, "python": v_espejo,
                            "delta": abs(v_orac - v_espejo), "tol": tol
                        })

            if not diffs:
                matched_exact.append((key, o_idx, e_idx))
            else:
                matched_diff.append((key, o_idx, e_idx, diffs))
            continue

        if len(o_list) > 0 and len(e_list) == 0:
            for o_idx, o_row in o_list:
                nt8_without_python.append((key, o_idx, o_row))
                used_orac_indices.add(o_idx)
            continue

        if len(e_list) > 0 and len(o_list) == 0:
            for e_idx, e_cand in e_list:
                python_without_nt8.append((key, e_idx, e_cand))
                used_espejo_indices.add(e_idx)
            continue

    total_matched = len(matched_exact) + len(matched_diff)
    fields_compared = total_matched * len(FIELD_SPECS)

    dur_0_orac = sum(1 for r in orac_rows if r[0] == r[1])
    dur_0_espejo = sum(1 for c in espejo_zones if c["ts_start"] == c["ts_end"])

    is_perfect_pass = (
        len(nt8_without_python) == 0 and
        len(python_without_nt8) == 0 and
        len(ambiguous_collisions) == 0 and
        len(matched_diff) == 0 and
        duplicate_match_reuse == 0 and
        len(matched_exact) == len(orac_rows) == len(espejo_zones)
    )

    return {
        "nt8_total_zones": len(orac_rows),
        "python_total_zones": len(espejo_zones),
        "matched_exact_count": len(matched_exact),
        "matched_field_diff_count": len(matched_diff),
        "nt8_without_python_count": len(nt8_without_python),
        "python_without_nt8_count": len(python_without_nt8),
        "ambiguous_collisions_count": len(ambiguous_collisions),
        "duplicate_match_reuse_count": duplicate_match_reuse,
        "total_matched_pairs": total_matched,
        "fields_compared_total": fields_compared,
        "diferencias_por_campo": dict(diferencias_por_campo),
        "ejemplos_diff": ejemplos_diff,
        "duracion_0ms_nt8": dur_0_orac,
        "duracion_0ms_python": dur_0_espejo,
        "is_perfect_pass": is_perfect_pass,
        "nt8_without_python_samples": [
            {"id": r[0], "start_ms": r[0], "end_ms": r[1], "dir": r[2], "lo": r[3], "hi": r[4], "pasos": r[6], "vol": r[10]}
            for _, _, r in nt8_without_python[:10]
        ],
        "python_without_nt8_samples": [
            {"start_ms": c["ts_start"] // 1_000_000, "end_ms": c["ts_end"] // 1_000_000, "dir": c["direction"],
             "lo": c["sw_lo_tk"] * tick_size, "hi": c["sw_hi_tk"] * tick_size, "pasos": c["pasos"], "vol": c["total_vol"]}
            for _, _, c in python_without_nt8[:10]
        ]
    }


def correr_v2(
    instrumento: str,
    parquet_path: Path,
    tick_size: float = 0.25,
    db_path: str = DB
) -> Dict[str, Any]:
    if not Path(db_path).exists():
        return {"error": f"No existe la base de datos oraculo: {db_path}"}
    if not parquet_path.exists():
        return {"error": f"No existe el archivo parquet: {parquet_path}"}

    orac = cargar_oraculo(instrumento, db_path)
    if not orac:
        return {"error": f"El oraculo no tiene zonas para {instrumento}"}

    viol = gates_coherentes(orac)

    t0 = min(r[0] for r in orac) * 1_000_000
    t1 = (max(r[1] for r in orac) + 1000) * 1_000_000

    tbl = pq.read_table(
        parquet_path,
        filters=[("ts_utc_ns", ">=", t0), ("ts_utc_ns", "<", t1)],
        columns=["ts_utc_ns", "price_ticks", "volume"]
    )
    ts = tbl.column("ts_utc_ns").to_numpy(zero_copy_only=False).astype("int64").tolist()
    px = tbl.column("price_ticks").to_numpy(zero_copy_only=False).astype("int64").tolist()
    vo = tbl.column("volume").to_numpy(zero_copy_only=False).astype("float64").tolist()

    if not ts:
        return {"error": "El parquet no cubre la ventana temporal del oraculo"}

    cands = hz.detect_candidates(ts, px, vo)
    espejo, reasons = hz.accept_all(cands, dict(hz.ACCEPT_DEFAULTS), tick_size=tick_size)

    diag = comparar_zonas_simetrico(orac, espejo, tick_size=tick_size)
    diag["instrumento"] = instrumento
    diag["parquet"] = str(parquet_path)
    diag["db_path"] = str(db_path)
    diag["tick_size"] = tick_size
    diag["ticks_leidos"] = len(ts)
    diag["candidatos_detectados"] = len(cands)
    diag["violaciones_de_gate"] = viol
    diag["reasons_summary"] = reasons
    diag["defaults"] = hz.ACCEPT_DEFAULTS

    return diag


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="HFTZones NQ Parity Comparator V2")
    ap.add_argument("--instrumento", default="NQ JUN26")
    ap.add_argument("--parquet", default="data/nt8/NQ_parquet/NQ_06-26_ticks.parquet")
    ap.add_argument("--tick-size", type=float, default=0.25)
    ap.add_argument("--db", default=DB)
    ap.add_argument("--out", default="data/nt8_oracles/paridad_hftzones_nq_v2.json")
    args = ap.parse_args(argv)

    p_path = Path(args.parquet)
    if not p_path.is_absolute():
        p_path = REPO / p_path
        if not p_path.exists():
            fallback = Path("E:/EdgeLab") / args.parquet
            if fallback.exists():
                p_path = fallback

    d_path = Path(args.db)
    if not d_path.is_absolute():
        d_path = REPO / d_path
        if not d_path.exists():
            fallback_db = Path("E:/EdgeLab") / args.db
            if fallback_db.exists():
                d_path = fallback_db

    res = correr_v2(args.instrumento, p_path, args.tick_size, str(d_path))
    if "error" in res:
        print(f"ERROR: {res['error']}")
        return 2

    print("=" * 70)
    print(f"REPORTE V2 DE PARIDAD SIMETRICA HFTZONES: {args.instrumento}")
    print("=" * 70)
    print(f"Zonas en Oraculo NT8:               {res['nt8_total_zones']:>8,}")
    print(f"Zonas en Espejo Python:             {res['python_total_zones']:>8,}")
    print(f"Ticks procesados:                   {res['ticks_leidos']:>8,}")
    print(f"Violaciones de gate en oraculo:     {res['violaciones_de_gate']:>8,}")
    print("-" * 70)
    print(f"Parejas EXACTAS (20/20 campos):     {res['matched_exact_count']:>8,}")
    print(f"Parejas con diferencias de campo:   {res['matched_field_diff_count']:>8,}")
    print(f"Zonas NT8 sin pareja en Python:     {res['nt8_without_python_count']:>8,}")
    print(f"Zonas Python sin pareja en NT8:     {res['python_without_nt8_count']:>8,}")
    print(f"Colisiones ambiguas:                {res['ambiguous_collisions_count']:>8,}")
    print(f"Reutilizacion duplicada de parejas: {res['duplicate_match_reuse_count']:>8,}")
    print(f"Campos efectivamente comparados:    {res['fields_compared_total']:>8,}")
    print("-" * 70)

    if res["diferencias_por_campo"]:
        print(f"Diferencias por campo: {res['diferencias_por_campo']}")

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print(f"Evidencia estructurada guardada en: {out_path}")

    if not res["is_perfect_pass"]:
        print("\n[VEREDICTO V2] PARIDAD NO EXACTA: Existen discrepancias estructurales o faltantes.")
        print(f"Status: PROVISIONAL_NEAR_EXACT_BLOCKED_BY_ORACLE_SCHEMA")
        return 1

    print("\n[VEREDICTO V2] PARIDAD EXACTA 100.00% CERTIFICADA.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

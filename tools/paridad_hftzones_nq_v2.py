#!/usr/bin/env python3
"""Comparador y arnés de paridad HFTZones NQ V2.

Soporta dos modos explícitos y ontológicamente separados:
1. V2_NS_EXACT_CERTIFICATION:
   - Requiere hft_ticks_v2 y hft_zones_v2 de la MISMA ejecución/replay.
   - Clave: (instrument, contract, session_id, zone_seq).
   - Reconstruye zonas en Python a partir de hft_ticks_v2.
   - Igualdad exacta en tick_seq, zone_seq, enteros y timestamps en ns (cero tolerancia sub-ms).
   - Verificación de monotonicidad, gaps, resets y hashes de source y parámetros.
   - Condición indispensable para emitir PASS_CERTIFIED.

2. V1_LEGACY_MS_DIAGNOSTIC:
   - Lee tabla hft_zones V1 con clave temporal en ms.
   - Rotulado obligatorio: DIAGNOSTIC_ONLY / NOT_ELIGIBLE_FOR_PASS_CERTIFIED.
   - Estatus permanente: PROVISIONAL_NEAR_EXACT_BLOCKED_BY_ORACLE_SCHEMA.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.indicators import hftzones_nq as hz  # noqa: E402

V1_DEFAULT_DB = "data/nt8_oracles/hft_zones_nq_20260603_20260611.sqlite"
V2_DEFAULT_DB = "data/nt8_oracles/hft_zones_nq_v2.sqlite"

EXPECTED_SOURCE_SHA256 = "841cdbcccbe54ca525e20456d38d1ece0beec5fdd7b820de980bbb01acebeb63"

def compute_parameter_manifest_sha256(params: Optional[Dict[str, Any]] = None) -> str:
    """Calcula el SHA-256 canónico del manifiesto de parámetros estructurales y de aceptación."""
    merged = dict(hz.STRUCTURAL_DEFAULTS)
    merged.update(hz.ACCEPT_DEFAULTS)
    if params:
        merged.update(params)
    canon_str = json.dumps(merged, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canon_str.encode("utf-8")).hexdigest()

EXPECTED_PARAM_SHA256 = compute_parameter_manifest_sha256()

# Schema de campos V1
V1_COLS = ("start_ts,end_ts,dir,price_lower,price_upper,valid_steps,pasos,avg_ms,"
           "total_ms,vol_rate,total_vol,height_ticks,max_retro,cvd_sweep,buy_vol,"
           "sell_vol,delta_slope,delta_first,delta_second,max_tick_vol,no_move_ticks,"
           "no_move_vol,max_level_ticks")

V1_FIELD_SPECS = [
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


# ==============================================================================
# MODO V2: NS EXACT CERTIFICATION (SHARED INPUT RECONSTRUCTION)
# ==============================================================================

def verificar_schema_v2(con: sqlite3.Connection) -> Tuple[bool, str]:
    """Verifica que existan hft_ticks_v2 y hft_zones_v2 con sus columnas requeridas."""
    cur = con.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "hft_ticks_v2" not in tables:
        return False, "Falta tabla obligatoria hft_ticks_v2 (ausencia de input ledger compartido)"
    if "hft_zones_v2" not in tables:
        return False, "Falta tabla obligatoria hft_zones_v2"

    cols_ticks = [r[1] for r in cur.execute("PRAGMA table_info(hft_ticks_v2)").fetchall()]
    req_ticks = ["instrument", "contract", "session_id", "tick_seq", "timestamp_ns", "price_ticks", "volume"]
    for c in req_ticks:
        if c not in cols_ticks:
            return False, f"Columna requerida faltante en hft_ticks_v2: {c}"

    cols_zones = [r[1] for r in cur.execute("PRAGMA table_info(hft_zones_v2)").fetchall()]
    req_zones = ["instrument", "contract", "session_id", "zone_seq", "start_tick_seq", "end_tick_seq",
                 "start_ts_ns", "end_ts_ns", "available_ts_ns", "direction", "lo_ticks", "hi_ticks",
                 "pasos", "vol", "parameter_manifest_sha256", "indicator_source_sha256"]
    for c in req_zones:
        if c not in cols_zones:
            return False, f"Columna requerida faltante en hft_zones_v2: {c}"

    return True, "OK"


def comparar_v2_exacto(
    con: sqlite3.Connection,
    instrument: str,
    tick_size: float = 0.25,
    source_sha: str = EXPECTED_SOURCE_SHA256,
    param_sha: str = EXPECTED_PARAM_SHA256
) -> Dict[str, Any]:
    """Ejecuta la certificación V2 de punta a punta reconstruyendo Python desde hft_ticks_v2."""
    valido, msg = verificar_schema_v2(con)
    if not valido:
        return {
            "mode": "V2_NS_EXACT_CERTIFICATION",
            "is_pass": False,
            "status": "FAIL_SCHEMA_INVALID",
            "error": msg,
            "total_nt8_zones": 0,
            "total_python_zones": 0,
            "matched_exact_count": 0,
            "matched_diffs_count": 0,
            "nt8_without_python_count": 0,
            "python_without_nt8_count": 0,
            "nt8_duplicates_count": 0,
            "py_duplicates_count": 0,
            "provenance_errors": [],
            "matched_diffs_samples": [],
            "nt8_without_python_samples": [],
            "python_without_nt8_samples": []
        }

    cur = con.cursor()
    zones_rows = cur.execute(
        """SELECT instrument, contract, session_id, zone_seq, start_tick_seq, end_tick_seq,
                  start_ts_ns, end_ts_ns, available_ts_ns, direction, lo_ticks, hi_ticks,
                  pasos, vol, avg_ms, total_ms, volume_rate, parameter_manifest_sha256,
                  indicator_source_sha256
           FROM hft_zones_v2
           WHERE instrument=?
           ORDER BY session_id ASC, zone_seq ASC""",
        (instrument,)
    ).fetchall()

    if not zones_rows:
        return {
            "mode": "V2_NS_EXACT_CERTIFICATION",
            "is_pass": False,
            "status": "FAIL_EMPTY_ORACLE_ZONES",
            "error": f"No se encontraron zonas en hft_zones_v2 para {instrument}",
            "total_nt8_zones": 0,
            "total_python_zones": 0,
            "matched_exact_count": 0,
            "matched_diffs_count": 0,
            "nt8_without_python_count": 0,
            "python_without_nt8_count": 0,
            "nt8_duplicates_count": 0,
            "py_duplicates_count": 0,
            "provenance_errors": [],
            "matched_diffs_samples": [],
            "nt8_without_python_samples": [],
            "python_without_nt8_samples": []
        }

    # Cargar ticks
    ticks_rows = cur.execute(
        """SELECT instrument, contract, session_id, tick_seq, timestamp_ns, price_ticks, volume
           FROM hft_ticks_v2
           WHERE instrument=?
           ORDER BY session_id ASC, tick_seq ASC""",
        (instrument,)
    ).fetchall()

    if not ticks_rows:
        return {
            "mode": "V2_NS_EXACT_CERTIFICATION",
            "is_pass": False,
            "status": "FAIL_EMPTY_INPUT_TICKS",
            "error": f"No se encontraron ticks en hft_ticks_v2 para {instrument}",
            "total_nt8_zones": len(zones_rows),
            "total_python_zones": 0,
            "matched_exact_count": 0,
            "matched_diffs_count": 0,
            "nt8_without_python_count": len(zones_rows),
            "python_without_nt8_count": 0,
            "nt8_duplicates_count": 0,
            "py_duplicates_count": 0,
            "provenance_errors": [],
            "matched_diffs_samples": [],
            "nt8_without_python_samples": [],
            "python_without_nt8_samples": []
        }

    # 1. Verificar secuencia monotónica de ticks y ausencia de gaps por sesión
    ticks_by_session = collections.defaultdict(list)
    for r in ticks_rows:
        sess = r[2]
        ticks_by_session[sess].append(r)

    tick_seq_errors = []
    for sess, t_list in ticks_by_session.items():
        expected_seq = 1
        for t in t_list:
            actual_seq = t[3]
            if actual_seq != expected_seq:
                tick_seq_errors.append(f"Session {sess}: tick_seq esperado {expected_seq}, encontrado {actual_seq}")
                break
            expected_seq += 1

    if tick_seq_errors:
        return {
            "mode": "V2_NS_EXACT_CERTIFICATION",
            "is_pass": False,
            "status": "FAIL_TICK_SEQUENCE_GAP",
            "error": "; ".join(tick_seq_errors[:5])
        }

    # 2. Reconstruir zonas en Python sesión por sesión a partir del ledger compartido
    reconstructed_zones = []
    session_reset_errors = []

    prev_close_ticks = None  # Último precio de la sesión anterior (para reproducir NT8 Closes[ds][1])
    for sess, t_list in sorted(ticks_by_session.items()):
        ts_ns = [t[4] for t in t_list]
        px_tk = [t[5] for t in t_list]
        vol = [float(t[6]) for t in t_list]

        # NT8: al procesar el primer tick de una sesión, Closes[ds][1] apunta al
        # cierre de la sesión anterior. Pasamos ese precio para que detect_candidates
        # pueda iniciar la racha en idx=0 (tick_seq=1), reproduciendo NT8 exactamente.
        cands = hz.detect_candidates(ts_ns, px_tk, vol,
                                     prev_session_close_ticks=prev_close_ticks)
        acc_zones, _ = hz.accept_all(cands, dict(hz.ACCEPT_DEFAULTS), tick_size=tick_size)

        # Actualizar para la próxima sesión
        prev_close_ticks = px_tk[-1] if px_tk else prev_close_ticks

        contract_sess = t_list[0][1]
        for z_idx, z in enumerate(acc_zones, start=1):
            reconstructed_zones.append({
                "instrument": instrument,
                "contract": contract_sess,
                "session_id": sess,
                "zone_seq": z_idx,
                "start_tick_seq": int(z["idx_start"]) + 1,
                "end_tick_seq": int(z["idx_end"]) + 1,
                "start_ts_ns": int(z["ts_start"]),
                "end_ts_ns": int(z["ts_end"]),
                "available_ts_ns": int(z["ts_avail"]),  # NT8: Times[1][0] al cierre = primer tick post-zona
                "direction": int(z["direction"]),
                "lo_ticks": int(z["sw_lo_tk"]),
                "hi_ticks": int(z["sw_hi_tk"]),
                "pasos": int(z["pasos"]),
                "vol": float(z["total_vol"]),
                "avg_ms": float(z["avg_ms"]),
                "total_ms": float(z["total_ms"]),
                "volume_rate": float(z["vol_rate"]),
            })

    # 3. Comparación simétrica uno-a-uno por clave canónica (instrument, contract, session_id, zone_seq)
    nt8_map = {}
    nt8_duplicates = 0
    for r in zones_rows:
        key = (r[0], r[1], r[2], int(r[3]))
        if key in nt8_map:
            nt8_duplicates += 1
        nt8_map[key] = r

    py_map = {}
    py_duplicates = 0
    for z in reconstructed_zones:
        key = (z["instrument"], z["contract"], z["session_id"], z["zone_seq"])
        if key in py_map:
            py_duplicates += 1
        py_map[key] = z

    all_keys = sorted(set(nt8_map.keys()) | set(py_map.keys()))

    matched_exact = []
    matched_diffs = []
    nt8_without_python = []
    python_without_nt8 = []
    provenance_errors = []

    for key in all_keys:
        in_nt8 = key in nt8_map
        in_py = key in py_map

        if in_nt8 and not in_py:
            nt8_without_python.append(key)
            continue
        if in_py and not in_nt8:
            python_without_nt8.append(key)
            continue

        r = nt8_map[key]
        z = py_map[key]

        # Verificar procedencia criptográfica
        actual_param_sha = str(r[17])
        actual_source_sha = str(r[18])
        if param_sha and actual_param_sha != param_sha:
            provenance_errors.append(f"Param SHA mismatch en {key}: {actual_param_sha} != {param_sha}")
        if source_sha and actual_source_sha != source_sha:
            provenance_errors.append(f"Source SHA mismatch en {key}: {actual_source_sha} != {source_sha}")

        # Comparar campos con CERO tolerancia para enteros y timestamps ns
        diffs = []
        if int(r[4]) != z["start_tick_seq"]:
            diffs.append(("start_tick_seq", int(r[4]), z["start_tick_seq"]))
        if int(r[5]) != z["end_tick_seq"]:
            diffs.append(("end_tick_seq", int(r[5]), z["end_tick_seq"]))
        if int(r[6]) != z["start_ts_ns"]:
            diffs.append(("start_ts_ns", int(r[6]), z["start_ts_ns"]))
        if int(r[7]) != z["end_ts_ns"]:
            diffs.append(("end_ts_ns", int(r[7]), z["end_ts_ns"]))
        if int(r[8]) != z["available_ts_ns"]:
            diffs.append(("available_ts_ns", int(r[8]), z["available_ts_ns"]))
        if int(r[9]) != z["direction"]:
            diffs.append(("direction", int(r[9]), z["direction"]))
        if int(r[10]) != z["lo_ticks"]:
            diffs.append(("lo_ticks", int(r[10]), z["lo_ticks"]))
        if int(r[11]) != z["hi_ticks"]:
            diffs.append(("hi_ticks", int(r[11]), z["hi_ticks"]))
        if int(r[12]) != z["pasos"]:
            diffs.append(("pasos", int(r[12]), z["pasos"]))
        if abs(float(r[13]) - z["vol"]) > 1e-6:
            diffs.append(("vol", float(r[13]), z["vol"]))
        if abs(float(r[14]) - z["avg_ms"]) > 1e-4:
            diffs.append(("avg_ms", float(r[14]), z["avg_ms"]))
        if abs(float(r[15]) - z["total_ms"]) > 1e-4:
            diffs.append(("total_ms", float(r[15]), z["total_ms"]))
        if abs(float(r[16]) - z["volume_rate"]) > 1e-4:
            diffs.append(("volume_rate", float(r[16]), z["volume_rate"]))

        if not diffs:
            matched_exact.append(key)
        else:
            matched_diffs.append({"key": key, "diffs": diffs})

    is_pass = (
        len(nt8_without_python) == 0 and
        len(python_without_nt8) == 0 and
        len(matched_diffs) == 0 and
        nt8_duplicates == 0 and
        py_duplicates == 0 and
        len(provenance_errors) == 0 and
        len(matched_exact) == len(zones_rows) == len(reconstructed_zones)
    )

    status = "PASS_CERTIFIED" if is_pass else "FAIL_V2_DISCREPANCY"

    return {
        "mode": "V2_NS_EXACT_CERTIFICATION",
        "instrument": instrument,
        "is_pass": is_pass,
        "status": status,
        "total_nt8_zones": len(zones_rows),
        "total_python_zones": len(reconstructed_zones),
        "matched_exact_count": len(matched_exact),
        "matched_diffs_count": len(matched_diffs),
        "nt8_without_python_count": len(nt8_without_python),
        "python_without_nt8_count": len(python_without_nt8),
        "nt8_duplicates_count": nt8_duplicates,
        "py_duplicates_count": py_duplicates,
        "provenance_errors": provenance_errors,
        "matched_diffs_samples": matched_diffs[:10],
        "nt8_without_python_samples": nt8_without_python[:10],
        "python_without_nt8_samples": python_without_nt8[:10]
    }


# ==============================================================================
# MODO V1: LEGACY MS DIAGNOSTIC (HISTORIC AUDIT ONLY)
# ==============================================================================

def correr_v1_legacy(
    instrumento: str,
    parquet_path: Path,
    tick_size: float = 0.25,
    db_path: str = V1_DEFAULT_DB
) -> Dict[str, Any]:
    """Ejecuta el cotejo legacy V1 con advertencia de que es solo diagnóstico."""
    import pyarrow.parquet as pq

    if not Path(db_path).exists():
        return {"error": f"No existe la base de datos oraculo V1: {db_path}"}
    if not parquet_path.exists():
        return {"error": f"No existe el archivo parquet: {parquet_path}"}

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    filas = con.execute(
        f"select {V1_COLS} from hft_zones where instrument=? order by start_ts asc, end_ts asc, dir asc",
        (instrumento,)
    ).fetchall()
    con.close()

    if not filas:
        return {"error": f"El oráculo V1 no tiene zonas para {instrumento}"}

    t0 = min(r[0] for r in filas) * 1_000_000
    t1 = (max(r[1] for r in filas) + 1000) * 1_000_000

    tbl = pq.read_table(
        parquet_path,
        filters=[("ts_utc_ns", ">=", t0), ("ts_utc_ns", "<", t1)],
        columns=["ts_utc_ns", "price_ticks", "volume"]
    )
    ts = tbl.column("ts_utc_ns").to_numpy(zero_copy_only=False).astype("int64").tolist()
    px = tbl.column("price_ticks").to_numpy(zero_copy_only=False).astype("int64").tolist()
    vo = tbl.column("volume").to_numpy(zero_copy_only=False).astype("float64").tolist()

    cands = hz.detect_candidates(ts, px, vo)
    espejo, reasons = hz.accept_all(cands, dict(hz.ACCEPT_DEFAULTS), tick_size=tick_size)

    # Indexar
    orac_by_key = collections.defaultdict(list)
    for idx, r in enumerate(filas):
        key = (int(r[0]), int(r[1]), int(r[2]))
        orac_by_key[key].append((idx, r))

    espejo_by_key = collections.defaultdict(list)
    for idx, c in enumerate(espejo):
        key = (int(c["ts_start"] // 1_000_000), int(c["ts_end"] // 1_000_000), int(c["direction"]))
        espejo_by_key[key].append((idx, c))

    all_keys = set(orac_by_key.keys()) | set(espejo_by_key.keys())
    matched_exact = []
    matched_diff = []
    nt8_without_python = []
    python_without_nt8 = []

    for key in sorted(all_keys):
        o_list = orac_by_key.get(key, [])
        e_list = espejo_by_key.get(key, [])

        if len(o_list) == 1 and len(e_list) == 1:
            o_row = o_list[0][1]
            e_cand = e_list[0][1]
            diffs = []
            for nom, col_idx, getter, tol, _ in V1_FIELD_SPECS:
                v_orac = float(o_row[col_idx])
                v_espejo = float(getter(e_cand, tick_size))
                if abs(v_orac - v_espejo) > tol:
                    diffs.append((nom, v_orac, v_espejo))
            if not diffs:
                matched_exact.append(key)
            else:
                matched_diff.append((key, diffs))
        elif len(o_list) > 0 and len(e_list) == 0:
            nt8_without_python.extend(o_list)
        elif len(e_list) > 0 and len(o_list) == 0:
            python_without_nt8.extend(e_list)

    total_matched = len(matched_exact) + len(matched_diff)
    fields_compared = total_matched * len(V1_FIELD_SPECS)

    return {
        "mode": "V1_LEGACY_MS_DIAGNOSTIC",
        "formal_classification": "DIAGNOSTIC_ONLY_NOT_ELIGIBLE_FOR_PASS_CERTIFIED",
        "status": "PROVISIONAL_NEAR_EXACT_BLOCKED_BY_ORACLE_SCHEMA",
        "is_perfect_pass": False,  # V1 nunca es eligible para pass
        "instrumento": instrumento,
        "nt8_total_zones": len(filas),
        "python_total_zones": len(espejo),
        "matched_exact_count": len(matched_exact),
        "matched_field_diff_count": len(matched_diff),
        "nt8_without_python_count": len(nt8_without_python),
        "python_without_nt8_count": len(python_without_nt8),
        "fields_compared_total": fields_compared,
        "explanation": "V1 utiliza clave en milisegundos e insumos de streaming capturados asimétricamente. Veredicto formal permanece PROVISIONAL."
    }


# ==============================================================================
# MAIN CLI
# ==============================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="HFTZones NQ Parity Comparator V2 Dual Mode")
    ap.add_argument("--mode", choices=["V2_NS_EXACT_CERTIFICATION", "V1_LEGACY_MS_DIAGNOSTIC"],
                    default="V1_LEGACY_MS_DIAGNOSTIC")
    ap.add_argument("--instrumento", default="NQ JUN26")
    ap.add_argument("--db", default=None)
    ap.add_argument("--parquet", default="data/nt8/NQ_parquet/NQ_06-26_ticks.parquet")
    ap.add_argument("--tick-size", type=float, default=0.25)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if args.mode == "V2_NS_EXACT_CERTIFICATION":
        db_p = args.db or V2_DEFAULT_DB
        db_path = Path(db_p)
        if not db_path.is_absolute():
            db_path = REPO / db_path
            if not db_path.exists():
                fallback = Path("E:/EdgeLab") / db_p
                if fallback.exists():
                    db_path = fallback

        if not db_path.exists():
            print(f"[V2_NS_EXACT_CERTIFICATION] Archivo DB no encontrado: {db_path}")
            print("Estado: BLOCKED_BY_MANUAL_NT8_SHARED_INPUT_EXPORT")
            print("Acción requerida: Ejecutar HFTZonesNQPureV4_V2 en NT8 para exportar hft_ticks_v2 y hft_zones_v2.")
            return 2

        con = sqlite3.connect(str(db_path))
        res = comparar_v2_exacto(con, args.instrumento, tick_size=args.tick_size)
        con.close()

        print("=" * 70)
        print("MODO V2: CERTIFICACIÓN EXACTA EN NANOSEGUNDOS (INPUT COMPARTIDO)")
        print("=" * 70)
        print(f"Status:                      {res['status']}")
        print(f"Is Pass:                     {res['is_pass']}")
        print(f"Zonas NT8 V2:                {res.get('total_nt8_zones', 0):>8,}")
        print(f"Zonas Python Reconstruidas:  {res.get('total_python_zones', 0):>8,}")
        print(f"Parejas Exactas (0ns drift): {res.get('matched_exact_count', 0):>8,}")
        print(f"Diferencias de Campo:        {res.get('matched_diffs_count', 0):>8,}")
        print(f"Faltantes NT8:               {res.get('nt8_without_python_count', 0):>8,}")
        print(f"Faltantes Python:            {res.get('python_without_nt8_count', 0):>8,}")
        print(f"Errores de Procedencia:      {len(res.get('provenance_errors', [])):>8,}")
        print("=" * 70)

        if args.out:
            out_p = Path(args.out)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=2, ensure_ascii=False)

        return 0 if res["is_pass"] else 1

    else:
        # Modo V1
        db_p = args.db or V1_DEFAULT_DB
        db_path = Path(db_p)
        if not db_path.is_absolute():
            db_path = REPO / db_path
            if not db_path.exists():
                fallback = Path("E:/EdgeLab") / db_p
                if fallback.exists():
                    db_path = fallback

        p_path = Path(args.parquet)
        if not p_path.is_absolute():
            p_path = REPO / p_path
            if not p_path.exists():
                fallback_p = Path("E:/EdgeLab") / args.parquet
                if fallback_p.exists():
                    p_path = fallback_p

        res = correr_v1_legacy(args.instrumento, p_path, tick_size=args.tick_size, db_path=str(db_path))
        if "error" in res:
            print(f"ERROR V1: {res['error']}")
            return 2

        print("=" * 70)
        print("MODO V1: DIAGNÓSTICO HISTÓRICO EN MILISEGUNDOS")
        print("AVISO: DIAGNOSTIC_ONLY / NOT_ELIGIBLE_FOR_PASS_CERTIFIED")
        print("=" * 70)
        print(f"Status Formal:               {res['status']}")
        print(f"Zonas Oráculo NT8:           {res['nt8_total_zones']:>8,}")
        print(f"Zonas Espejo Python:         {res['python_total_zones']:>8,}")
        print(f"Parejas Exactas (20 campos): {res['matched_exact_count']:>8,}")
        print(f"Zonas NT8 sin Python:        {res['nt8_without_python_count']:>8,}")
        print(f"Zonas Python sin NT8:        {res['python_without_nt8_count']:>8,}")
        print(f"Campos Comparados:           {res['fields_compared_total']:>8,}")
        print("=" * 70)
        print(f"Dictamen: {res['explanation']}")

        out_dest = args.out or "data/nt8_oracles/paridad_hftzones_nq_v2.json"
        out_p = Path(out_dest)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)

        # En V1 siempre devuelve exit code 1 porque el schema viejo impide la certificación exacta
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

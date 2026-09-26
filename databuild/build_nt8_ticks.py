"""Conversor NT8 `.Last.txt` -> Parquet canónico POR CONTRATO (gate P0, F2).

- Parsea el `.Last.txt` crudo (formato F1) de forma vectorizada.
- Infiere la timezone empíricamente (nt8_timezone) y escribe `ts_utc_ns` SOLO si
  la inferencia es unánime; si falla, NO escribe parquet (FAIL, reporte, stop).
- Auditor P0 (semilla tools/fixture_p0.py) generalizado DST-aware:
  orden, alineación exacta a tick, bid<=ask, volumen, quantum/resolución,
  halt CME 16:00-17:00 CT (America/Chicago), fragmentación >30min.
- POR CONTRATO: sin empalme, columna `contract` obligatoria. Además concatena
  todos los contratos en 6E_all_contracts.parquet (mismo schema, sin ajustar
  precios). Escritura atómica (temp -> rename), compresión zstd. Rutas vía
  edgelab.config (F0C), cero hardcode.

Uso:  python -m databuild.build_nt8_ticks            # procesa TickData/ real
      (importable: convert_file(...) para tests con fixtures sintéticos)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from edgelab.config import DATA_DIR, ensure_dir
from edgelab.data.nt8_contract import SIX_E, INSTRUMENT_SPECS, Nt8TickContract, ZB
from edgelab.data.nt8_timezone import forbidden_days, verify_offset

NS = 1_000_000_000

CANON_SCHEMA = pa.schema([
    ("ts_utc_ns", pa.int64()), ("ts_local_ns", pa.int64()), ("sequence", pa.int64()),
    ("price_ticks", pa.int64()), ("bid_ticks", pa.int64()), ("ask_ticks", pa.int64()),
    ("volume", pa.int32()), ("aggressor", pa.string()), ("tick_type", pa.string()),
    ("instrument", pa.string()), ("contract", pa.string()),
    ("source_file", pa.string()), ("source_row", pa.int64()),
])


def _sha256(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def _atomic_write_parquet(table, path):
    tmp = path + ".tmp"
    pq.write_table(table, tmp, compression="zstd")
    os.replace(tmp, path)


def parse_last_txt(path):
    """Parseo vectorizado -> arrays en ORDEN DEL ARCHIVO (sin reordenar)."""
    df = pd.read_csv(path, sep=";", header=None, names=["ts", "last", "bid", "ask", "vol"],
                     dtype={"ts": "string", "last": "float64", "bid": "float64",
                            "ask": "float64", "vol": "int64"}, engine="c")
    ts = df["ts"]
    lens = ts.str.len()
    if not ((lens == 23).all()):
        raise ValueError(f"{os.path.basename(path)}: líneas con longitud de ts != 23 (formato inesperado)")
    sec_ns = (pd.to_datetime(ts.str.slice(0, 15), format="%Y%m%d %H%M%S")
              .to_numpy().astype("datetime64[ns]").astype("int64"))
    frac = ts.str.slice(16, 23).astype("int64").to_numpy()
    ts_local_ns = sec_ns + frac * 100
    out = {
        "ts_local_ns": ts_local_ns,
        "last": df["last"].to_numpy("float64"),
        "bid": df["bid"].to_numpy("float64"),
        "ask": df["ask"].to_numpy("float64"),
        "vol": df["vol"].to_numpy("int64"),
    }
    del df
    return out


def _to_ticks(v, tick_size):
    r = np.round(v / tick_size)
    off = np.abs(r * tick_size - v)
    bad = int((off > 1e-6).sum())
    return r.astype("int64"), bad


def audit_and_convert(path, contract, out_dir, declared_tz, instrument=SIX_E):
    """Devuelve summary dict. Escribe parquet+manifest+p0_report solo si PASS."""
    fails, warns, r = [], [], {}
    a = parse_last_txt(path)
    ts_local = a["ts_local_ns"]
    r["rows"] = int(len(ts_local))

    # 1. orden temporal (sin reordenar)
    d = np.diff(ts_local)
    n_back = int((d < 0).sum())
    r["backwards_ts"] = n_back
    if n_back:
        fails.append(f"{n_back} retrocesos temporales en el orden del archivo")
    r["same_ts_pairs"] = int((d == 0).sum())

    # 2. resolución / quantum
    sub = ts_local % NS
    nz = sub[sub != 0]
    quantum = int(np.gcd.reduce(nz)) if len(nz) else 0
    r["time_quantum_ns"] = quantum
    r["quantum_ms"] = round(quantum / 1e6, 4)
    r["frac_subsecond"] = round(float((sub != 0).mean()), 4)
    r["frac_zero_ms"] = round(float((sub % 1_000_000 == 0).mean()), 4)
    r["resolution_limited"] = bool(quantum >= 1_000_000)
    if r["resolution_limited"]:
        warns.append(f"quantum {quantum/1e6:.0f} ms: resolution_limited")

    # 3. precios -> ticks (alineación exacta)
    tk = instrument.tick_size
    last_t, bad_l = _to_ticks(a["last"], tk)
    bid_t, bad_b = _to_ticks(a["bid"], tk)
    ask_t, bad_a = _to_ticks(a["ask"], tk)
    r["misaligned"] = {"last": bad_l, "bid": bad_b, "ask": bad_a}
    if bad_l or bad_b or bad_a:
        fails.append(f"precios desalineados a tick_size={tk}: {r['misaligned']}")

    # 4. bid<=ask, volumen, agresor, last fuera de spread
    n_cross = int((bid_t > ask_t).sum())
    r["bid_gt_ask"] = n_cross
    if n_cross:
        fails.append(f"{n_cross} filas con bid>ask")
    vol = a["vol"]
    r["volume_range"] = [int(vol.min()), int(vol.max())]
    if (vol <= 0).any():
        fails.append(f"{int((vol<=0).sum())} filas con volume<=0")
    aggressor = np.where(last_t == ask_t, "buy",
                         np.where(last_t == bid_t, "sell", "unclassified"))
    r["aggressor"] = {k: int((aggressor == k).sum()) for k in ("buy", "sell", "unclassified")}
    r["last_outside_spread"] = int(((last_t < bid_t) | (last_t > ask_t)).sum())

    # 5. timezone: verificación empírica del offset UTC (schedule-fit CME, DST-aware)
    vr = verify_offset(ts_local, offset_s=0)
    r["tz_verification"] = {
        "declared_tz": declared_tz, "canonical_offset_s": 0, "verified_utc": vr.verified,
        "score_utc": round(vr.score, 6), "min_offset_s": vr.min_offset_s,
        "min_score": round(vr.min_score, 6), "art_score": round(vr.art_score, 6),
        "note": vr.note, "scores_s": {str(k): round(v, 6) for k, v in sorted(vr.scores_s.items())},
    }
    ts_utc = None
    if not vr.verified:
        fails.append(f"timezone UTC no verificable: {vr.note}")
    else:
        ts_utc = ts_local  # offset 0 (UTC verificado empíricamente)
        r["range_utc"] = [datetime.fromtimestamp(int(ts_utc.min())/1e9, tz=timezone.utc).isoformat(),
                          datetime.fromtimestamp(int(ts_utc.max())/1e9, tz=timezone.utc).isoformat()]
        # 6. residual fuera de sesión al offset UTC = feriados CME no modelados (WARN, decidido)
        fdays = forbidden_days(ts_utc)
        r["out_of_session_frac"] = round(vr.score, 6)
        r["out_of_session_days"] = fdays
        if vr.score > 0.001:
            warns.append(f"{vr.score*100:.2f}% ticks fuera de sesión al offset UTC "
                         f"(probables feriados CME; días: {', '.join(d for d, _ in fdays[:6])})")
        # 7. fragmentación (>30min y <6h, no weekend)
        gaps = np.diff(np.sort(ts_utc))
        n_frag = int(((gaps > 30 * 60 * NS) & (gaps < 6 * 3600 * NS)).sum())
        r["fragments_30min_to_6h"] = n_frag
        if n_frag:
            warns.append(f"{n_frag} huecos 30min–6h (posible baja liquidez/feriado)")

    status = "FAIL" if fails else ("PASS_WITH_WARNINGS" if warns else "PASS")
    summary = {"contract": contract, "status": status, "rows": r["rows"],
               "fails": fails, "warnings": warns, "metrics": r}

    ensure_dir(out_dir)
    stem = contract.replace(" ", "_")
    with open(os.path.join(out_dir, f"{stem}_p0_report.json"), "w", encoding="utf-8") as fh:
        json.dump({"tool": "build_nt8_ticks", "generated_utc": datetime.now(timezone.utc).isoformat(),
                   **summary}, fh, indent=2, ensure_ascii=False)

    if fails:
        summary["parquet"] = None
        return summary

    n = len(ts_local)
    table = pa.table({
        "ts_utc_ns": ts_utc.astype("int64"), "ts_local_ns": ts_local.astype("int64"),
        "sequence": np.arange(n, dtype="int64"),
        "price_ticks": last_t, "bid_ticks": bid_t, "ask_ticks": ask_t,
        "volume": vol.astype("int32"), "aggressor": aggressor.astype(object),
        "tick_type": np.full(n, "trade", dtype=object),
        "instrument": np.full(n, instrument.symbol, dtype=object),
        "contract": np.full(n, contract, dtype=object),
        "source_file": np.full(n, os.path.basename(path), dtype=object),
        "source_row": np.arange(n, dtype="int64"),
    }, schema=CANON_SCHEMA)
    pq_path = os.path.join(out_dir, f"{stem}_ticks.parquet")
    _atomic_write_parquet(table, pq_path)
    manifest = {
        "schema_version": "canonical_tick_v1", "tool": "build_nt8_ticks",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": os.path.abspath(path), "source_sha256": _sha256(path),
        "instrument": instrument.symbol, "contract": contract, "rows": n,
        "tz": r["tz_verification"],
        "transformations": [
            "parseo .Last.txt (yyyyMMdd HHmmss fffffff;last;bid;ask;vol), frac 100ns",
            "ts_utc_ns = ts_local_ns (offset 0; UTC verificado por schedule-fit CME DST-aware)",
            f"precios -> ticks enteros (/{tk}), alineación exacta validada",
            "sequence/source_row = orden estable del archivo (sin dedup, sin reorden)",
            "SIN empalme ni ajuste de precios (por contrato)",
        ],
        "known_deviations": warns,
        "parquet_sha256": _sha256(pq_path),
    }
    with open(os.path.join(out_dir, f"{stem}_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    summary["parquet"] = pq_path
    return summary


def convert_file(path, contract, out_dir, declared_tz="UTC", instrument=SIX_E):
    Nt8TickContract(declared_tz=declared_tz, instrument=instrument)  # valida el contrato
    return audit_and_convert(path, contract, out_dir, declared_tz, instrument)


def _contract_of(filename):
    return os.path.splitext(os.path.basename(filename))[0].replace(".Last", "")


def main(argv=None):
    import argparse
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    
    parser = argparse.ArgumentParser(description="Conversor NT8 .Last.txt -> Parquet canónico (gate P0)")
    parser.add_argument("--instrument", "-i", default="6E", choices=list(INSTRUMENT_SPECS.keys()),
                        help="Símbolo del instrumento (6E, ZB, YM, ES, NQ). Default: 6E")
    parser.add_argument("--src-dir", "-s", default=None,
                        help="Directorio fuente con archivos .Last.txt")
    parser.add_argument("--out-dir", "-o", default=None,
                        help="Directorio destino de salida para los .parquet")
    parser.add_argument("--file", "-f", default=None,
                        help="Archivo específico .Last.txt a convertir (opcional)")
    
    args = parser.parse_args(argv)
    inst = INSTRUMENT_SPECS[args.instrument]
    
    if args.src_dir:
        src_dir = args.src_dir
    else:
        candidates = [
            os.path.join(DATA_DIR, "nt8", inst.symbol),
            os.path.join(os.path.dirname(DATA_DIR), "TickData"),
            os.path.join(DATA_DIR, "nt8"),
        ]
        src_dir = next((c for c in candidates if os.path.exists(c) and any(f.endswith(".Last.txt") for f in os.listdir(c))), candidates[0])

    out_dir = args.out_dir or os.path.join(DATA_DIR, "nt8", inst.symbol)
    
    if args.file:
        files = [os.path.basename(args.file)]
        src_dir = os.path.dirname(os.path.abspath(args.file))
    else:
        if not os.path.exists(src_dir):
            print(f"FAIL: Directorio fuente no existe: {src_dir}")
            return []
        files = sorted(f for f in os.listdir(src_dir) if f.endswith(".Last.txt") and (inst.symbol in f or args.src_dir))

    print(f"Instrumento: {inst.symbol} (tick_size={inst.tick_size}, tick_value={inst.tick_value})")
    print(f"Fuente: {src_dir} ({len(files)} archivos) -> {out_dir}")
    
    summaries = []
    for f in files:
        contract = _contract_of(f)
        print(f"\n=== {contract} ===")
        s = audit_and_convert(os.path.join(src_dir, f), contract, out_dir, "UTC", inst)
        summaries.append(s)
        tzv = s["metrics"].get("tz_verification", {})
        print(f"  status={s['status']} rows={s['rows']:,} "
              f"utc_verificado={tzv.get('verified_utc')} score_utc={tzv.get('score_utc')} "
              f"parquet={'sí' if s.get('parquet') else 'NO'}")
        for x in s["fails"]:
            print(f"  FAIL: {x}")
        for x in s["warnings"]:
            print(f"  WARN: {x}")

    ok = [s for s in summaries if s.get("parquet")]
    if ok:
        tables = [pq.read_table(s["parquet"]) for s in ok]
        all_path = os.path.join(out_dir, f"{inst.symbol}_all_contracts.parquet")
        _atomic_write_parquet(pa.concat_tables(tables), all_path)
        print(f"\n{os.path.basename(all_path)}: {sum(t.num_rows for t in tables):,} filas, {len(ok)} contratos")
    return summaries


if __name__ == "__main__":
    main()

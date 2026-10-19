#!/usr/bin/env python3
"""
fixture_p0.py — Fase A del puente NT8 → EdgeLab: selección de fixture + gate P0.

Uso:
  python fixture_p0.py --source ticks.parquet --list
  python fixture_p0.py --source ticks.parquet --out fixtures/ \
      --start "2026-06-04T00:00:00" --end "2026-06-05T00:00:00" \
      --instrument ES --contract "ES 06-26" --tick-size 0.25 --point-value 50

Qué hace:
  1. Carga el parquet fuente (schema NT8: datetime, price, bid, ask, volume).
  2. Audita el contrato de datos (gate P0): orden, alineación a tick, bid<=ask,
     volumen, resolución temporal, huecos y consistencia de timezone contra el
     patrón de halt diario de CME (21:00-22:00 UTC).
  3. Extrae el rango pedido y lo convierte al contrato canónico:
     ts_utc_ns | sequence | price_ticks | bid_ticks | ask_ticks | volume |
     tick_type | instrument | contract | source.
  4. Emite fixture_ticks.parquet + fixture_manifest.json + p0_report.json
     + reporte legible. Sale con código != 0 si el gate P0 falla.

Políticas fijas (a propósito NO configurables):
  - NUNCA deduplica ni reordena: sequence = orden estable del archivo fuente.
  - Precios a ticks enteros con validación exacta (tol 1e-6): un solo precio
    desalineado = FAIL. Sin redondeo silencioso.
  - datetime naive se declara UTC en el manifest; la heurística de halt la
    valida o refuta. FAIL si hay ticks dentro del halt diario.
"""
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

VERSION = "1.0.0"
NS_MIN = 60_000_000_000
NS_H = 3_600_000_000_000


def sha256(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def to_naive_utc_ns(ts):
    """Serie datetime (naive o tz-aware) -> int64 ns en UTC naive."""
    if getattr(ts.dtype, "tz", None) is not None:
        ts = ts.dt.tz_convert("UTC").dt.tz_localize(None)
    return ts.astype("int64").to_numpy(), ts


def fragments(sorted_ts_ns, gap_ns=30 * NS_MIN):
    """Tramos contiguos separados por huecos > gap_ns -> [(i0, i1, t0, t1)]."""
    d = np.diff(sorted_ts_ns)
    cuts = np.where(d > gap_ns)[0]
    starts = np.concatenate(([0], cuts + 1))
    ends = np.concatenate((cuts, [len(sorted_ts_ns) - 1]))
    return [(int(a), int(b), int(sorted_ts_ns[a]), int(sorted_ts_ns[b]))
            for a, b in zip(starts, ends)]


def halt_check(ts_ns):
    """En UTC real, ES no opera 21:00-22:00 UTC (halt CME, horario de verano).
    Fracción alta de ticks ahí => timestamps no-UTC o bases horarias mezcladas.
    Nota: con horario de invierno de EE.UU. el halt cae 22:00-23:00 UTC; si el
    dataset cruza cambios de DST, revisar por tramo."""
    sec_of_day = (ts_ns // 1_000_000_000) % 86_400
    in_halt = (sec_of_day >= 21 * 3600) & (sec_of_day < 22 * 3600)
    frac = float(in_halt.mean())
    days = []
    if in_halt.any():
        dd = np.unique(ts_ns[in_halt] // (86_400 * 1_000_000_000))
        days = [datetime.fromtimestamp(int(x) * 86_400, tz=timezone.utc).strftime("%Y-%m-%d")
                for x in dd[:20]]
    return frac, days


def audit(df, tick_size):
    """Gate P0 sobre un DataFrame ya recortado. -> (report, fails, warns)."""
    fails, warns = [], []
    r = {}

    ts_ns, _ = to_naive_utc_ns(df["datetime"])
    r["rows"] = int(len(df))
    r["range_utc"] = [
        datetime.fromtimestamp(int(ts_ns.min()) / 1e9, tz=timezone.utc).isoformat(),
        datetime.fromtimestamp(int(ts_ns.max()) / 1e9, tz=timezone.utc).isoformat(),
    ]

    # 1. Orden temporal (sobre el orden del archivo, sin reordenar)
    d = np.diff(ts_ns)
    n_back = int((d < 0).sum())
    r["backwards_ts"] = n_back
    if n_back:
        fails.append(f"{n_back} retrocesos temporales en el orden del archivo")

    # 2. Multiplicidad (dedup prohibido; solo se mide)
    r["same_ts_pairs"] = int((d == 0).sum())
    r["ticks_per_unique_ts"] = round(len(ts_ns) / max(1, len(np.unique(ts_ns))), 2)
    r["identical_rows"] = int(df.duplicated().sum())  # informativo: pueden ser trades reales

    # 3. Resolución temporal
    sub_s = ts_ns % 1_000_000_000
    r["frac_subsecond"] = round(float((sub_s != 0).mean()), 4)
    r["frac_sub_ms"] = round(float((ts_ns % 1_000_000 != 0).mean()), 6)
    quantum = int(np.gcd.reduce(sub_s[sub_s != 0])) if (sub_s != 0).any() else None
    r["time_quantum_ns"] = quantum
    dd = d[(d >= 0) & (d <= 1_000_000_000)]
    r["frac_zero_ms_deltas"] = round(float((dd < 1_000_000).mean()), 4) if len(dd) else None
    if r["frac_subsecond"] == 0:
        warns.append("timestamps redondeados al segundo: familia HFT no confiable (resolution_limited)")
    elif quantum and quantum >= 1_000_000:
        warns.append(f"quantum temporal de {quantum/1e6:.0f} ms: clasificación por intervalo individual limitada")

    # 4. Precios: alineación exacta al tick
    for col in ("price", "bid", "ask"):
        if col not in df.columns:
            (fails if col == "price" else warns).append(
                f"sin columna {col}" + ("" if col == "price" else ": buy/sell solo por tick rule"))
            continue
        v = df[col].to_numpy(dtype="float64")
        m = ~np.isnan(v)
        off = np.abs(np.round(v[m] / tick_size) * tick_size - v[m])
        bad = int((off > 1e-6).sum())
        r[f"{col}_misaligned"] = bad
        r[f"{col}_range"] = [float(np.nanmin(v)), float(np.nanmax(v))]
        if bad:
            fails.append(f"{col}: {bad} valores desalineados de tick_size={tick_size}")

    # 5. bid <= ask
    if "bid" in df.columns and "ask" in df.columns:
        b = df["bid"].to_numpy(dtype="float64")
        a = df["ask"].to_numpy(dtype="float64")
        both = ~np.isnan(b) & ~np.isnan(a) & (b > 0) & (a > 0)
        r["frac_with_quotes"] = round(float(both.mean()), 4)
        n_inv = int((b[both] > a[both]).sum())
        r["bid_gt_ask"] = n_inv
        if n_inv:
            fails.append(f"{n_inv} filas con bid > ask")

    # 6. Volumen
    v = df["volume"].to_numpy()
    r["volume_range"] = [int(v.min()), int(v.max())]
    if (v <= 0).any():
        fails.append(f"{int((v <= 0).sum())} filas con volume <= 0")

    # 7. Timezone contra patrón de halt CME
    frac_halt, bad_days = halt_check(ts_ns)
    r["frac_ticks_in_cme_halt"] = round(frac_halt, 5)
    r["halt_violation_days"] = bad_days
    if frac_halt > 0.001:
        fails.append(
            f"{frac_halt*100:.2f}% de ticks dentro del halt CME 21:00-22:00 UTC "
            f"(días: {', '.join(bad_days[:5])}): timestamps no-UTC o bases horarias "
            "mezcladas en el empalme. Corregir el export antes de usar.")

    # 8. Fragmentación interna del rango elegido
    frags = fragments(np.sort(ts_ns))
    r["fragments_gt_30min_gap"] = len(frags)
    if len(frags) > 1:
        warns.append(f"{len(frags)} tramos separados por huecos >30min dentro del rango elegido")

    return r, fails, warns


def listing(df):
    ts_ns, _ = to_naive_utc_ns(df["datetime"])
    s = np.sort(ts_ns)
    fmt = lambda ns: datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).strftime("%a %m-%d %H:%M:%S")
    print(f"{'#':>3} {'inicio (UTC)':<22} {'fin (UTC)':<22} {'dur_h':>6} {'ticks':>10}")
    for i, (a, b, t0, t1) in enumerate(fragments(s)):
        print(f"{i:>3} {fmt(t0):<22} {fmt(t1):<22} {(t1 - t0) / NS_H:>6.1f} {b - a + 1:>10,}")


def price_to_ticks(v, tick_size):
    out = np.round(np.asarray(v, dtype="float64") / tick_size)
    res = np.where(np.isnan(out), 0, out).astype("int64")
    res[np.isnan(np.asarray(v, dtype="float64"))] = -1  # -1 = sin dato
    return res


def main():
    ap = argparse.ArgumentParser(description="Fase A: fixture + gate P0")
    ap.add_argument("--source", required=True)
    ap.add_argument("--list", action="store_true", help="listar tramos contiguos y salir")
    ap.add_argument("--out", default="fixtures")
    ap.add_argument("--start", help="ISO, interpretado como UTC naive, inclusive")
    ap.add_argument("--end", help="ISO, interpretado como UTC naive, exclusivo")
    ap.add_argument("--instrument", default="ES")
    ap.add_argument("--contract", default="UNDECLARED",
                    help="contrato individual, ej. 'ES 06-26'; UNDECLARED queda registrado como deuda")
    ap.add_argument("--tick-size", type=float, default=0.25)
    ap.add_argument("--point-value", type=float, default=50.0)
    ap.add_argument("--fixture-id", default=None, help="identificador; default derivado de fechas")
    args = ap.parse_args()

    df = pq.read_table(args.source).to_pandas()
    missing = {"datetime", "price", "volume"} - set(df.columns)
    if missing:
        sys.exit(f"FAIL: faltan columnas obligatorias {sorted(missing)}")

    if args.list:
        listing(df)
        return

    if not (args.start and args.end):
        sys.exit("FAIL: --start y --end son obligatorios (o usar --list)")
    t0, t1 = pd.Timestamp(args.start), pd.Timestamp(args.end)
    if t0.tzinfo or t1.tzinfo:
        sys.exit("FAIL: pasar --start/--end naive (se interpretan como UTC)")

    _, ts_naive = to_naive_utc_ns(df["datetime"])
    df = df.assign(datetime=ts_naive)
    sel = df[(df["datetime"] >= t0) & (df["datetime"] < t1)].copy()
    if sel.empty:
        sys.exit("FAIL: el rango pedido no contiene ticks")

    report, fails, warns = audit(sel, args.tick_size)

    # --- conversión al contrato canónico (solo si no hay FAIL estructural) ---
    os.makedirs(args.out, exist_ok=True)
    fixture_id = args.fixture_id or f"{args.instrument}_{t0:%Y%m%d}_{t1:%Y%m%d}"
    status = "FAIL" if fails else ("PASS_WITH_WARNINGS" if warns else "PASS")

    p0 = {
        "tool": "fixture_p0.py", "version": VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": status, "fails": fails, "warnings": warns, "metrics": report,
    }
    with open(os.path.join(args.out, f"{fixture_id}_p0_report.json"), "w", encoding="utf-8") as fh:
        json.dump(p0, fh, indent=2, ensure_ascii=False)

    print(f"=== GATE P0: {status} ===")
    for f in fails:
        print(f"  FAIL: {f}")
    for w in warns:
        print(f"  WARN: {w}")
    for k, v in report.items():
        print(f"  {k}: {v}")

    if fails:
        print("\nNo se escribe fixture: gate P0 fallido. Reporte guardado.")
        sys.exit(2)

    ts_ns = sel["datetime"].astype("int64").to_numpy()
    out = pd.DataFrame({
        "ts_utc_ns": ts_ns.astype("int64"),
        "sequence": np.arange(len(sel), dtype="int64"),
        "price_ticks": price_to_ticks(sel["price"], args.tick_size),
        "volume": sel["volume"].to_numpy().astype("int32"),
        "bid_ticks": price_to_ticks(sel["bid"], args.tick_size) if "bid" in sel.columns else np.full(len(sel), -1, dtype="int64"),
        "ask_ticks": price_to_ticks(sel["ask"], args.tick_size) if "ask" in sel.columns else np.full(len(sel), -1, dtype="int64"),
    })
    out["tick_type"] = "trade"
    out["instrument"] = args.instrument
    out["contract"] = args.contract
    out["source"] = "nt8_export"

    fixture_path = os.path.join(args.out, f"{fixture_id}_ticks.parquet")
    out.to_parquet(fixture_path, index=False)

    manifest = {
        "fixture_id": fixture_id, "schema_version": "canonical_tick_v1",
        "tool": "fixture_p0.py", "version": VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": os.path.abspath(args.source),
        "source_sha256": sha256(args.source),
        "source_tz_declaration": "naive interpretado como UTC (validado por heurística de halt CME)",
        "filter": {"start_utc": str(t0), "end_utc": str(t1)},
        "instrument": args.instrument, "contract": args.contract,
        "contract_declared": args.contract != "UNDECLARED",
        "tick_size": args.tick_size, "point_value": args.point_value,
        "rows": int(len(out)),
        "transformations": [
            "recorte temporal [start, end)",
            f"price/bid/ask float32 -> ticks enteros (x{1/args.tick_size:.0f}, validado exacto)",
            "sequence = orden estable del archivo fuente (sin dedup, sin reorden)",
            "tick_type = 'trade' constante (export NT8 solo trades con quote prevaleciente)",
        ],
        "known_deviations": warns,
        "fixture_sha256": sha256(fixture_path),
    }
    with open(os.path.join(args.out, f"{fixture_id}_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    print(f"\nFixture escrito: {fixture_path} ({len(out):,} ticks)")
    print(f"Manifest y p0_report en {args.out}/")


if __name__ == "__main__":
    main()

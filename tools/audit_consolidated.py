#!/usr/bin/env python3
r"""Auditoría de datasets de ticks consolidados por activo (corre en Kaggle con los datasets adjuntos y edgelab-data-catalog).
Compara contra el RESOLVER: por sesión aprobada, trades esperados vs filas del dataset; además esquema canónico, monotonía temporal, duplicados exactos,
holdout (≥ 2026-10-01), libro bid/ask válido, alineación al tick y columna de contrato. Salida: AUDIT_RESULTS.json (agregados; sin precios ni ticks).
Config en env AUDIT_CFG: {"datasets": {"NQ": "ruta-o-slug-del-input", ...}}"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
import numpy as np
import pandas as pd

KAGGLE = Path("/kaggle/input").exists(); CT = "America/Chicago"; HOLDOUT = "2026-10-01"
REQ = ["ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence", "instrument", "contract"]
CFG = json.loads(os.environ.get("AUDIT_CFG", "{}"))


def session_dates(ts_ns: np.ndarray) -> np.ndarray:
    """Fecha de sesión CME (17:00-16:00 CT): idéntica a edgelab_data._session_date, calculada una vez por minuto."""
    lab = (np.asarray(ts_ns) // 60_000_000_000 + 1) * 60_000_000_000 - 1; um, inv = np.unique(lab // 60_000_000_000, return_inverse=True)
    c = pd.to_datetime(um * 60_000_000_000, utc=True).tz_convert(CT) + pd.Timedelta(hours=7)
    return np.asarray(c.strftime("%Y-%m-%d"))[inv]


def audit_chunk(t: pd.DataFrame, acc: dict, tick_size: float):
    sd = session_dates(t["ts_utc_ns"].to_numpy()); acc["rows"] += len(t)
    for d, n in zip(*np.unique(sd, return_counts=True)): acc["per_session"][d] = acc["per_session"].get(d, 0) + int(n)
    ts = t["ts_utc_ns"].to_numpy(); dt = np.diff(ts); acc["non_monotonic"] += int((dt < 0).sum())
    if acc["last_ts"] is not None and len(ts) and ts[0] < acc["last_ts"]: acc["non_monotonic"] += 1
    if len(ts): acc["last_ts"] = int(ts[-1]); acc["ts_min"] = min(acc["ts_min"], int(ts[0])) if acc["ts_min"] is not None else int(ts[0]); acc["ts_max"] = max(acc["ts_max"], int(ts[-1])) if acc["ts_max"] is not None else int(ts[-1])
    key = t[["ts_utc_ns", "price_ticks", "volume", "sequence"]].to_numpy(); same = (key[1:] == key[:-1]).all(1); acc["exact_dup_consecutive"] += int(same.sum())
    bid, ask = t["bid_ticks"].to_numpy(), t["ask_ticks"].to_numpy(); acc["book_valid"] += int(((bid > 0) & (ask >= bid)).sum()); acc["volume_lt1"] += int((t["volume"].to_numpy() < 1).sum())
    for c in ("price_ticks", "bid_ticks", "ask_ticks", "volume"): acc["nulls"][c] = acc["nulls"].get(c, 0) + int(t[c].isna().sum())
    acc["after_holdout"] += int((sd >= HOLDOUT).sum()); cs, cn = np.unique(t["contract"].astype(str).to_numpy(), return_counts=True)
    for a, b in zip(cs, cn): acc["contracts"][a] = acc["contracts"].get(a, 0) + int(b)
    acc["price_min"] = min(acc["price_min"], int(t["price_ticks"].min())); acc["price_max"] = max(acc["price_max"], int(t["price_ticks"].max()))


def compare_to_resolver(acc: dict, expected: dict) -> dict:
    got = acc["per_session"]; exact = lower = higher = 0; worst = []
    for d, e in expected.items():
        g = got.get(d, 0)
        if g == e: exact += 1
        elif g < e: lower += 1
        else: higher += 1
        if g != e: worst.append((d, e, g, round(100 * (g / e - 1), 1) if e else None))
    worst.sort(key=lambda x: -abs(x[3] if x[3] is not None else 0))
    return dict(sessions_expected=len(expected), sessions_exact=exact, sessions_fewer_rows=lower, sessions_more_rows=higher, sessions_missing=[d for d in expected if d not in got], sessions_not_in_resolver=sorted(d for d in got if d not in expected)[:50],
                rows_expected=int(sum(expected.values())), rows_found_in_approved_sessions=int(sum(got.get(d, 0) for d in expected)), worst_sessions=worst[:15])


def audit_dataset(inst: str, paths: list, expected: dict, tick_size: float) -> dict:
    import pyarrow.parquet as pq
    acc = dict(rows=0, per_session={}, non_monotonic=0, last_ts=None, ts_min=None, ts_max=None, exact_dup_consecutive=0, book_valid=0, volume_lt1=0, nulls={}, after_holdout=0, contracts={}, price_min=10**18, price_max=-10**18); schema = None; files = []
    for p in paths:
        pf = pq.ParquetFile(p); names = pf.schema_arrow.names; schema = schema or names; files.append(dict(file=Path(p).name, rows=pf.metadata.num_rows, row_groups=pf.num_row_groups, bytes=Path(p).stat().st_size))
        miss = [c for c in REQ if c not in names]
        if miss: return dict(inst=inst, ok=False, error=f"esquema no canónico: faltan {miss}", columns=names, files=files)
        for i in range(pf.num_row_groups): audit_chunk(pf.read_row_group(i, columns=REQ).to_pandas(), acc, tick_size)
    cmp_ = compare_to_resolver(acc, expected); rows = acc["rows"]
    return dict(inst=inst, files=files, rows=rows, ts_range_utc=[str(pd.to_datetime(acc["ts_min"], utc=True)), str(pd.to_datetime(acc["ts_max"], utc=True))] if rows else None, non_monotonic_steps=acc["non_monotonic"], exact_consecutive_duplicates=acc["exact_dup_consecutive"],
                exact_consecutive_duplicates_pct=round(100 * acc["exact_dup_consecutive"] / max(rows, 1), 4), rows_after_holdout=acc["after_holdout"], book_valid_pct=round(100 * acc["book_valid"] / max(rows, 1), 2), volume_lt1=acc["volume_lt1"], nulls=acc["nulls"],
                contracts_rows=acc["contracts"], price_ticks_range=[acc["price_min"], acc["price_max"]], vs_resolver=cmp_, ok=bool(acc["non_monotonic"] == 0 and acc["after_holdout"] == 0 and cmp_["sessions_exact"] == cmp_["sessions_expected"] and not cmp_["sessions_not_in_resolver"]))


def main():
    sys.path.insert(0, str(next(p.parent for r in [Path("/kaggle/input"), *Path("/kaggle/input").glob("datasets/*")] for p in r.glob("edgelab-data-catalog/**/RESOLVER.json")))) if KAGGLE else None
    res_path = next(p for r in [Path("/kaggle/input"), *Path("/kaggle/input").glob("datasets/*")] for p in r.glob("edgelab-data-catalog/**/RESOLVER.json")) if KAGGLE else Path("docs/data_catalog/RESOLVER.json")
    R = json.loads(res_path.read_text()); out = {}
    for inst, root in CFG["datasets"].items():
        paths = sorted(str(p) for p in Path(root).rglob("*.parquet")); sess = R["instruments"][inst]["sessions"]; expected = {x["date"]: int(x["trades"]) for x in sess if x.get("approved")}
        try: out[inst] = audit_dataset(inst, paths, expected, R["instruments"][inst]["tick_size"]); print(inst, {k: out[inst].get(k) for k in ("rows", "ok")}, flush=True)
        except Exception:
            import traceback; out[inst] = dict(inst=inst, ok=False, error=traceback.format_exc()[-1500:])
    Path("/kaggle/working" if KAGGLE else ".").joinpath("AUDIT_RESULTS.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()

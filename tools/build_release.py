#!/usr/bin/env python3
"""Arma la release líquida: UN Parquet de ticks por activo, sólo sesiones con contrato líquido elegido causalmente.

Entradas (todas ya producidas por los pases previos): escaneos (--scan), censo (--census) y decisiones por activo.
Salida (--out): data/<ACTIVO>_ticks.parquet + metadata/* + release_manifest.json + README_AGENTES.md.
Estado de la release: CANDIDATE_NOT_RESEARCH_APPROVED (la política de liquidez es una propuesta sin aprobar).

Uso: python tools/build_release.py --scan D:/.../scan2 --scan D:/.../scanP --census D:/.../census --out D:/.../release [--only ES NQ]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.data.liquid_release import plan as P  # noqa: E402
from edgelab.data.liquid_release.consolidate import Segment, SourceFile, write_asset  # noqa: E402
from edgelab.data.liquid_release.release_reader import SCHEMA, sha256_file  # noqa: E402

TICK = {"ES": 0.25, "NQ": 0.25, "MES": 0.25, "MNQ": 0.25, "YM": 1.0, "MYM": 1.0, "ZB": 0.03125, "GC": 0.1, "MGC": 0.1,
        "RTY": 0.1, "6E": 0.00005, "6B": 0.0001, "6J": 0.0000005, "MBT": 5.0}
CUTOFF_PREFIX = b"20260930 220000"
OFFSET_OK = ("UTC_VERIFIED", "INSUFFICIENT_EVIDENCE", "UTC_WITH_ANOMALIES")


def load_source_bins(scan_dirs):
    import glob
    inv, parts = [], []
    for d in scan_dirs:
        for f in glob.glob(str(Path(d) / "parts" / "*.json")):
            if not f.endswith(".error.json"):
                inv.append(json.load(open(f, encoding="utf-8")))
        for f in glob.glob(str(Path(d) / "parts" / "*.parquet")):
            parts.append(pd.read_parquet(f, columns=["source_id", "raw_date", "raw_hour", "n"]))
    inv = pd.DataFrame(inv)
    inv["group"] = inv["kind"] + "|" + inv["root"].str.split("\\").str[-1] + "|" + inv["contract"]
    bins = pd.concat(parts, ignore_index=True)
    bins = bins[bins["n"] > 0]
    return inv, bins


def build_segments(inst, dec, chosen, ann, sbins, inv, tz):
    sel = dec[dec["status"] == "SELECTED"][["trade_date", "contract"]].sort_values("trade_date")
    ch = chosen[chosen["instrument"] == inst].set_index(["contract", "trade_date"])
    sel = sel.join(ch[["group", "kind", "assurance"]], on=["contract", "trade_date"])
    assert sel["group"].notna().all(), "sesión seleccionada sin fuente adjudicada"
    sel["run"] = ((sel["contract"] != sel["contract"].shift()) | (sel["group"] != sel["group"].shift())).cumsum()
    verdict = tz.set_index("group")["verdict"].to_dict()
    offset = tz.set_index("group")["best_offset_h"].to_dict()
    invi = inv.set_index("id")
    segs, regime, prev_contract, runs = [], 0, None, []
    for _, r in sel.groupby("run", sort=True):
        contract, group, kind = r["contract"].iloc[0], r["group"].iloc[0], r["kind"].iloc[0]
        if contract != prev_contract:
            regime += 1
            prev_contract = contract
        dates = set(int(x) for x in r["trade_date"])
        a = ann[(ann["group"] == group) & ann["trade_date"].isin(dates) & (~ann["dup_copy"])]
        lookup = {int(rd) * 24 + int(rh): (int(td), bool(ib)) for rd, rh, td, ib in
                  zip(a["raw_date"], a["raw_hour"], a["trade_date"], a["in_break"])}
        keys = set(lookup)
        sb = sbins[sbins["source_id"].isin(inv.loc[inv["group"] == group, "id"])]
        sb_k = sb["raw_date"].astype(np.int64) * 24 + sb["raw_hour"]
        used = sorted(set(sb.loc[sb_k.isin(keys), "source_id"]))
        files = []
        for sid in used:
            s = invi.loc[sid]
            files.append(SourceFile(path=s["path"], source_id=-1, offset_h=int(offset[group]) if verdict.get(group) in OFFSET_OK else 0,
                                    kind=s["kind"], cutoff_prefix=CUTOFF_PREFIX if s["kind"] == "B" and str(s.get("day")) >= "20260930" else None,
                                    fmt="parquet" if s["kind"] == "P" else "text"))
            files[-1].source_key = sid
        segs.append(Segment(contract, regime, files, dates, lookup))
        runs.append(dict(contract=contract, regime_id=regime, group=group, kind=kind, assurance=r["assurance"].iloc[0],
                         first_trade_date=min(dates), last_trade_date=max(dates), sessions=len(dates), files=len(files)))
    return segs, pd.DataFrame(runs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="append", required=True)
    ap.add_argument("--census", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--policy-json", help="JSON {ACTIVO: {min_prev_volume,min_prev_ticks,max_prev_spread_p50_ticks}} aprobado por Nico")
    a = ap.parse_args()
    out, cen = Path(a.out), Path(a.census)
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "metadata").mkdir(parents=True, exist_ok=True)
    chosen = pd.read_parquet(cen / "chosen_sources.parquet")
    chosen = chosen[chosen["trade_date"] < 20261001]
    ann = pd.read_parquet(cen / "annotated_bins.parquet", columns=["group", "raw_date", "raw_hour", "trade_date", "in_break", "dup_copy", "instrument"])
    tz = pd.read_csv(cen / "tz_groups.csv")
    cal = pd.read_parquet(cen / "calendar_derived.parquet")
    inv, sbins = load_source_bins(a.scan)
    insts = sorted(chosen["instrument"].unique())
    if a.only:
        insts = [i for i in insts if i in a.only]
    for inst in insts:
        t0 = time.time()
        pol_override = None
        if a.policy_json:
            pj = json.load(open(a.policy_json, encoding="utf-8")).get(inst)
            if pj:
                pol_override = P.LiquidityPolicy(pj.get("version", "approved"), pj["min_prev_volume"], pj["min_prev_ticks"],
                                                 pj["max_prev_spread_p50_ticks"], approved_by=pj.get("approved_by"))
        pol, fr, dec = P.plan_asset(chosen, cal, inst, pol_override)
        dec.insert(0, "instrument", inst)
        segs, runs = build_segments(inst, dec, chosen, ann[ann["instrument"] == inst], sbins, inv, tz)
        runs.insert(0, "instrument", inst)
        # ids de fuente estables: índice dentro del activo
        sid_map = {}
        for sg in segs:
            for f in sg.files:
                f.source_id = sid_map.setdefault(f.source_key, len(sid_map))
        path = out / "data" / f"{inst}_ticks.parquet"
        stats, rows = write_asset(path, segs, TICK[inst], root=inst)
        sha = sha256_file(path)
        info = dict(file=f"data/{inst}_ticks.parquet", bytes=path.stat().st_size, sha256=sha, rows=int(rows),
                    sessions=int((dec["status"] == "SELECTED").sum()), first_trade_date=int(dec.loc[dec.status == "SELECTED", "trade_date"].min()),
                    last_trade_date=int(dec.loc[dec.status == "SELECTED", "trade_date"].max()), tick_size=TICK[inst],
                    status="CANDIDATE_NOT_RESEARCH_APPROVED")
        policy = dict(version=pol.version, min_prev_volume=pol.min_prev_volume, min_prev_ticks=pol.min_prev_ticks,
                      max_prev_spread_p50_ticks=pol.max_prev_spread_p50_ticks, approved_by=pol.approved_by, notes=pol.notes,
                      noncompetitive_frac=pol.noncompetitive_frac)
        invi = inv.set_index("id")
        src_rows = []
        for key, idx in sid_map.items():
            s_ = invi.loc[key]
            src_rows.append(dict(instrument=inst, source_id=idx, scan_id=key, kind=s_["kind"], contract=s_["contract"],
                                 file_name=Path(s_["path"]).name, sha256=s_.get("sha256"), bytes=int(s_["bytes"]),
                                 rows=int(s_.get("rows_ok") or 0), tz_group=s_["group"]))
        parts = out / "metadata" / "parts"
        parts.mkdir(parents=True, exist_ok=True)
        (parts / f"{inst}_asset.json").write_text(json.dumps(dict(info=info, policy=policy), indent=1), encoding="utf-8")
        dec.to_parquet(parts / f"{inst}_decisions.parquet", index=False)
        runs.to_parquet(parts / f"{inst}_runs.parquet", index=False)
        pd.DataFrame(src_rows).to_parquet(parts / f"{inst}_sources.parquet", index=False)
        print(f"{inst}: {rows:,} filas, {info['sessions']} sesiones, {path.stat().st_size / 1e9:.2f} GB, {time.time() - t0:.0f}s", flush=True)
    print("FIN", flush=True)


if __name__ == "__main__":
    main()

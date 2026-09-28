#!/usr/bin/env python3
r"""Bundles de MES 25 ticks con las zonas HFT calculadas con los parámetros LITERALES de NQ (`NQ_LITERAL_TRANSFER`), como
cuando en NT8 se aplica HFTZonesNQPureV4 sobre MES. Pedido de Nico (2026-09-24) para calibrar corredores a ojo.

- Mismas sesiones, parquet y sha256 que los bundles MES existentes (perfil escalado); ids nuevos `<id>_NQLIT`.
  Los bundles existentes no se tocan.
- Cada zona recibe `touch_events` CAUSALES: los instantes (inicio de vela, s) en que una vela de 25 ticks entra al rango
  de la zona viniendo de afuera, después de que la zona está disponible. El campo HP-007 solo cuenta los toques
  <= t_ref, así que no hay mirada al futuro. Se guardan hasta `MAX_TOUCHES` por zona (el desgaste ya satura).
- Paridad NT8 en MES: PARITY_ABSTAIN (el perfil literal es de NQ).

    .venv\Scripts\python tools\build_mes_nqlit_bundles.py --workers 3
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))
import numpy as np  # noqa: E402

import build_multiasset_25t_hft_bundles as B  # noqa: E402
from edgelab.bridge.indicators import hftzones_universal as hu  # noqa: E402

BUNDLES = REPO / "viewer" / "nt8_bridge" / "bundles"
SUFFIX = "_NQLIT"
MAX_TOUCHES = 40


def add_touch_events(bundle: dict) -> int:
    cd = bundle["bar_series"]["tick_25"]["candles"]
    t = np.array([c["time"] for c in cd], dtype=np.int64)
    lo = np.array([c["low"] for c in cd], dtype=float)
    hi = np.array([c["high"] for c in cd], dtype=float)
    n_touch = 0
    for run in bundle["runs"]:
        for z in run["zones"]:
            av = z.get("available_ts")
            if av is None:
                continue
            b, tp = min(z["bottom"], z["top"]), max(z["bottom"], z["top"])
            i0 = int(np.searchsorted(t, av, "right"))       # velas que empiezan DESPUÉS de estar disponible
            inside = (lo[i0:] <= tp) & (hi[i0:] >= b)
            if not inside.any():
                z["touch_events"] = []
                continue
            prev = np.concatenate([[True], inside[:-1]])      # la primera vela no cuenta: ahí la zona se formó
            entries = np.flatnonzero(inside & ~prev)[:MAX_TOUCHES]
            z["touch_events"] = [int(x) for x in t[i0 + entries]]
            n_touch += len(entries)
    return n_touch


def plan():
    out = []
    for f in sorted(BUNDLES.glob("MES_*_25T_HFT.manifest.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        sess = [dict(trade_date=s["trade_date"], start_utc_ns=s["start_utc_ns"], end_utc_ns=s["end_utc_ns"],
                     prev_session_close_ticks=("CARRY" if s.get("first_tick_context") == "EXPLICIT" else None))
                for s in m["sessions"]]
        out.append(dict(asset_id=m["asset_id"] + SUFFIX, instrument=m["instrument"], contract=m["contract"],
                        parquet=m["source_path"], expected_sha256=m["source_sha256"], sessions=sess, profile=hu.LITERAL,
                        parity_status="PARITY_ABSTAIN", _base=m["asset_id"]))
    return out


def _build(entry):
    base = entry.pop("_base")
    bundle, manifest = B.build_entry(entry, holdout_ns=B.DEFAULT_HOLDOUT_NS, source_sha256=entry["expected_sha256"])
    nt = add_touch_events(bundle)
    manifest["touch_events"] = dict(rule="entrada de vela 25t al rango de la zona desde afuera, despues de available_ts",
                                    max_per_zone=MAX_TOUCHES, total=nt)
    aid = manifest["asset_id"]
    B.write_json_atomic(BUNDLES / f"{aid}.json", bundle)
    B.write_json_atomic(BUNDLES / f"{aid}.manifest.json", manifest)
    return base, aid, manifest["zones"], manifest["tick25_bars"], nt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--only")
    a = ap.parse_args()
    entries = plan()
    if a.only:
        entries = [e for e in entries if re.search(a.only, e["asset_id"])]
    for e in entries:
        B.validate_entry({k: v for k, v in e.items() if k != "_base"}, B.DEFAULT_HOLDOUT_NS)
    mf = BUNDLES / "manifest.js"
    txt = mf.read_text(encoding="utf-8")
    by_id = {it["id"]: it for it in json.loads(txt[txt.index("["):txt.rindex("]") + 1])}
    extra_path = BUNDLES / "manifest_nqlit.js"          # catálogo aparte: manifest.js no se toca
    extra = {}
    if extra_path.exists():
        t2 = extra_path.read_text(encoding="utf-8")
        extra = {it["id"]: it for it in json.loads(t2[t2.index(".concat(") + 8:t2.rindex(")")])}
    with ProcessPoolExecutor(a.workers) as ex:
        for base, aid, nz, nb, nt in ex.map(_build, entries):
            print(f"{aid:40s} zonas={nz:7d} barras={nb:8d} toques={nt:8d}", flush=True)
            item = dict(by_id.get(base, {}))
            item.update(id=aid, name=(item.get("name", base) + " · NQ literal"), zones=nz, candles=nb,
                        profile=hu.LITERAL, parity_status="PARITY_ABSTAIN",
                        group=(item.get("group", "MES") + " · NQ literal"))
            extra[aid] = item
            extra_path.write_text("window.ASSET_CATALOG = (window.ASSET_CATALOG || []).concat(" +
                                  json.dumps(sorted(extra.values(), key=lambda x: x["id"]), indent=2, ensure_ascii=False) + ");\n",
                                  encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

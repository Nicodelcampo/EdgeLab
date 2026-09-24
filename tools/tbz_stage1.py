#!/usr/bin/env python3
r"""Familia TBZ, etapa E1 target-free (protocolo: docs/research/FAMILIA_TBZ_FRANJAS_BAJA_PERMANENCIA_20260924.md).

Pasos:
  bundles   por cada bundle de 25 ticks pre-holdout de MES y ES: franjas EXP (grilla completa) y huecos DWELL (L 60 y
            240), más el solapamiento con los corredores HFTGAP (density_field, dos presets) cada 30 min. Escribe
            viewer/nt8_bridge/bundles/tbz/<bundle>.json (para el visor) y artifacts/tbz/per_bundle/<bundle>.json.
  report    censo por variante (E1a) y solapamiento contra el nulo (E1b), por instrumento, con el contrato del día
            elegido por más ticks; declara particiones y registra observaciones en el ledger de la familia.

Nada mira el precio posterior a la disponibilidad de una franja.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from edgelab.research import density_field as DF  # noqa: E402
from edgelab.research.tbz_bands import dwell_bands, expansion_bands, overlap_ratio_vs_null, tick_set  # noqa: E402

BUNDLES = REPO / "viewer" / "nt8_bridge" / "bundles"
OUT_VIEW = BUNDLES / "tbz"
OUT = REPO / "artifacts" / "tbz"
LEDGER = REPO / "artifacts" / "hippocampus" / "tbz_20260924.jsonl"
PREREG = "docs/research/FAMILIA_TBZ_FRANJAS_BAJA_PERMANENCIA_20260924.md"
HOLDOUT_S = DF.HOLDOUT_NS // 1_000_000_000
EXP_GRID = [(20, 2.5), (20, 4.0), (60, 2.5), (60, 4.0)]
DWELL_L = [3600, 14400]
SNAP_GAP_S = 1800
EXP_MAX_AGE_S = 14400
RANGE_LOOKBACK_S = 14400
PRESETS = {
    "HP007_NO_TIME_DECAY": dict(model="FIELD_TRANS", kernel="KERNEL_GAUSS", sigma_ticks=1.2, vol_transform="TRANS_POWER_025",
                                use_maturation=True, use_time_decay=False, use_wear=True, saturation=True),
    "HP007_CALIBRATED": dict(model="FIELD_TRANS", kernel="KERNEL_GAUSS", sigma_ticks=1.2, vol_transform="TRANS_POWER_025",
                             use_maturation=True, use_time_decay=True, use_wear=True, saturation=True),
}
HMIN_TICKS = 16
PAIRS = [("EXP", "HFTGAP"), ("EXP", "DWELL"), ("DWELL", "HFTGAP"), ("DWELL", "EXP"), ("HFTGAP", "EXP"), ("HFTGAP", "DWELL")]


def _git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def bundle_ids():
    out = []
    for p in sorted(BUNDLES.glob("*_25T_HFT.json")):
        inst = p.stem.split("_")[0]
        if inst in ("MES", "ES"):
            out.append(p.stem)
    return out


def adapt_zone(z, i):
    """Mismo adaptador que el visor (index.html toFieldZones): t1 es muerte solo si state != ACTIVE."""
    fz = dict(id=str(z.get("id", i)), bottom=min(z["bottom"], z["top"]), top=max(z["bottom"], z["top"]), vol=z.get("vol"),
              kind=z.get("kind"), direction=z.get("direction"), source=z.get("source"), available_ts=z["available_ts"])
    if z.get("state") and str(z["state"]).upper() != "ACTIVE" and z.get("t1") is not None:
        fz["ended_ts"] = z["t1"]
    if isinstance(z.get("touch_events"), list):
        fz["touch_events"] = z["touch_events"]
    return fz


def process_bundle(bid: str) -> str:
    d = json.loads((BUNDLES / f"{bid}.json").read_text(encoding="utf-8"))
    tick = float(d["meta"]["tick_size"])
    cd = d["bar_series"]["tick_25"]["candles"]
    t = np.array([x["time"] for x in cd], dtype=np.int64)
    keep = t < HOLDOUT_S
    t = t[keep]
    o, h, l, c, v = (np.array([x[k] for x in cd], dtype=float)[keep] for k in ("open", "high", "low", "close", "volume"))
    exp = {f"W{W}_k{k}": expansion_bands(t, o, h, l, c, tick, W=W, k=k) for W, k in EXP_GRID}
    dwell = {f"L{L // 60}": dwell_bands(t, h, l, v, tick, L_s=L) for L in DWELL_L}
    zones = [adapt_zone(z, i) for i, z in enumerate(d["runs"][0]["zones"]) if z.get("available_ts") is not None]
    zav = np.array([z["available_ts"] for z in zones])
    order = np.argsort(zav, kind="stable")
    zones = [zones[i] for i in order]
    zav = zav[order]
    # solapamiento cada 30 min
    rng = np.random.default_rng(20260924)
    first_key = f"W{EXP_GRID[0][0]}_k{EXP_GRID[0][1]}"
    snaps = []
    T = (int(t[0]) // SNAP_GAP_S + 1) * SNAP_GAP_S if len(t) else 0
    d60 = {r["t"]: r for r in dwell["L60"]}
    while len(t) and T <= int(t[-1]):
        i0, i1 = np.searchsorted(t, T - RANGE_LOOKBACK_S), np.searchsorted(t, T)
        if i1 - i0 >= 50 and T - int(t[i1 - 1]) <= 600:          # solo con mercado activo
            rlo, rhi = int(np.round(l[i0:i1].min() / tick)), int(np.round(h[i0:i1].max() / tick))
            nz = int(np.searchsorted(zav, T, "right"))
            gaps = {}
            if nz > 0:
                el = zones[:nz]
                mn = min(DF.price_to_tick(z["bottom"], tick) for z in el) - 20
                mx = max(DF.price_to_tick(z["top"], tick) for z in el) + 20
                if mx - mn + 1 <= 20000:
                    for pname, cfg in PRESETS.items():
                        f = DF.compute_field(zones[:nz], T, tick, mn, mx, cfg)
                        inter = DF.detect_density_intervals(f["density"], f["price_ticks"], tick, min_low_ticks=HMIN_TICKS)
                        gaps[pname] = [(max(iv["tick_start"], rlo), min(iv["tick_end"], rhi))
                                       for iv in inter["low_density_intervals"] if iv["tick_end"] >= rlo and iv["tick_start"] <= rhi]
            dw = d60.get(T)
            sets = {"DWELL": [tuple(b) for b in dw["bands"]] if dw else []}
            snap = dict(t=int(T), range=(rlo, rhi), n_zones=nz, ratios={})
            for key, bands in exp.items():
                sets_x = dict(sets, EXP=[(b["lo_tick"], b["hi_tick"]) for b in bands if b["t_avail"] <= T < b["t_avail"] + EXP_MAX_AGE_S])
                for pname, g in gaps.items():
                    sets_x["HFTGAP"] = g
                    for a, b in PAIRS:
                        with_exp = "EXP" in (a, b)
                        if not with_exp and key != first_key:
                            continue                     # DWELL/HFTGAP no dependen de la grilla EXP: una sola vez
                        r = overlap_ratio_vs_null(sets_x[a], tick_set(sets_x[b]), rlo, rhi, rng) if sets_x[a] and sets_x[b] else None
                        if r:
                            snap["ratios"][f"{key if with_exp else 'ALL'}|{pname}|{a}>{b}"] = r
            snaps.append(snap)
        T += SNAP_GAP_S
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "per_bundle").mkdir(exist_ok=True)
    body = dict(bundle=bid, instrument=d["meta"]["instrument"], contract=d["meta"]["contract"], tick_size=tick,
                exp={k: v2 for k, v2 in exp.items()}, dwell_summary={k: dict(samples=len(v2), with_gap=sum(1 for r in v2 if r["bands"]),
                                                                            widths=[b[1] - b[0] + 1 for r in v2 for b in r["bands"]])
                                                                     for k, v2 in dwell.items()},
                snapshots=snaps)
    (OUT / "per_bundle" / f"{bid}.json").write_text(json.dumps(body), encoding="utf-8")
    # archivo para el visor: solo construcción (sin desenlaces)
    OUT_VIEW.mkdir(parents=True, exist_ok=True)
    view = dict(schema="EDGELAB_TBZ_VIEW_V1", bundle=bid, tick_size=tick, prereg=PREREG, holdout_ts=int(HOLDOUT_S),
                exp={k: [[b["t_start"], b["t_avail"], b["lo_tick"], b["hi_tick"], b["dir"]] for b in v2] for k, v2 in exp.items()},
                exp_extend_s=EXP_MAX_AGE_S,
                dwell={k: dict(t=[r["t"] for r in v2 if r["bands"]], bands=[r["bands"] for r in v2 if r["bands"]], step_s=300)
                       for k, v2 in dwell.items()})
    (OUT_VIEW / f"{bid}.json").write_text(json.dumps(view, separators=(",", ":")), encoding="utf-8")
    return f"{bid}: EXP {({k: len(x) for k, x in exp.items()})} DWELL60 gaps {body['dwell_summary']['L60']['with_gap']} snaps {len(snaps)}"


def front_dates():
    """Por instrumento y fecha, el bundle con más ticks esa fecha (manifests)."""
    best = {}
    for bid in bundle_ids():
        man = json.loads((BUNDLES / f"{bid}.manifest.json").read_text(encoding="utf-8"))
        inst = man["instrument"]
        for s in man.get("sessions", []):
            if s["start_utc_ns"] // 1_000_000_000 >= HOLDOUT_S:
                continue
            key = (inst, int(s["trade_date"]))
            if key not in best or s["ticks"] > best[key][1]:
                best[key] = (bid, s["ticks"], s["start_utc_ns"] // 1_000_000_000, s["end_utc_ns"] // 1_000_000_000)
    return best


def step_bundles(workers: int):
    ids = bundle_ids()
    with Pool(workers) as p:
        for line in p.imap_unordered(process_bundle, ids):
            print(line, flush=True)


def step_report():
    from edgelab.edge_brain.episode_logger import measurement_episode
    fd = front_dates()
    by_bundle_windows = {}
    for (inst, date), (bid, n, s0, s1) in fd.items():
        by_bundle_windows.setdefault(bid, []).append((s0, s1, inst, date))
    census, ratios = {}, {}
    for bid, wins in by_bundle_windows.items():
        body = json.loads((OUT / "per_bundle" / f"{bid}.json").read_text(encoding="utf-8"))
        inst, tick = body["instrument"], body["tick_size"]

        def owner(ts):
            for s0, s1, i2, dt in wins:
                if s0 <= ts < s1:
                    return dt
            return None
        c = census.setdefault(inst, dict(dates=set(), exp={}, dwell={}))
        for s0, s1, i2, dt in wins:
            c["dates"].add(dt)
        for k, bands in body["exp"].items():
            e = c["exp"].setdefault(k, dict(n=0, widths=[], sig=[], dur=[]))
            for b in bands:
                if owner(b["t_avail"]) is None:
                    continue
                e["n"] += 1; e["widths"].append(b["width_ticks"]); e["sig"].append(b["width_ticks"] / max(b["sigma_ticks"], 1e-9))
                e["dur"].append(b["t_ext"] - b["t_start"])
        for k, sm in body["dwell_summary"].items():
            dd = c["dwell"].setdefault(k, dict(samples=0, with_gap=0, widths=[]))
            dd["samples"] += sm["samples"]; dd["with_gap"] += sm["with_gap"]; dd["widths"] += sm["widths"]
        for sn in body["snapshots"]:
            if owner(sn["t"]) is None:
                continue
            for key, (real, null, n) in sn["ratios"].items():
                rr = ratios.setdefault(inst, {}).setdefault(key, [0.0, 0.0, 0])
                rr[0] += real; rr[1] += null; rr[2] += 1
    q = lambda x: None if not len(x) else {f"p{p}": float(np.percentile(x, p)) for p in (10, 50, 90)}
    rep = dict(schema="EDGELAB_TBZ_E1_V1", prereg=PREREG, code_commit=_git("rev-parse", "HEAD"),
               tree_dirty=bool(_git("status", "--porcelain", "--", "edgelab", "tools")), census={}, overlap={})
    for inst, c in census.items():
        nd = len(c["dates"])
        rep["census"][inst] = dict(
            sessions=nd,
            exp={k: dict(n=e["n"], per_session=e["n"] / max(nd, 1), width_ticks=q(e["widths"]), width_sigma=q(e["sig"]),
                         formation_s=q(e["dur"])) for k, e in c["exp"].items()},
            dwell={k: dict(samples=dd["samples"], share_with_gap=dd["with_gap"] / max(dd["samples"], 1), width_ticks=q(dd["widths"]))
                   for k, dd in c["dwell"].items()})
    for inst, rr in ratios.items():
        rep["overlap"][inst] = {}
        for key, (sr, sn, n) in sorted(rr.items()):
            real, null = sr / n, sn / n
            rep["overlap"][inst][key] = dict(real=real, null=null, ratio=(real / null) if null > 0 else None, snapshots=n)
    # criterio congelado: mismo objeto si real/nulo >= 1,5 en los dos instrumentos; distinto si < 1,2
    verdicts = {}
    keys = set().union(*[set(v) for v in rep["overlap"].values()]) if rep["overlap"] else set()
    for key in sorted(keys):
        rs = [rep["overlap"][i][key]["ratio"] for i in ("MES", "ES") if key in rep["overlap"].get(i, {})]
        rs = [r for r in rs if r is not None]
        if len(rs) < 2:
            verdicts[key] = "INSUFFICIENT"
        elif min(rs) >= 1.5:
            verdicts[key] = "SAME_OBJECT"
        elif max(rs) < 1.2:
            verdicts[key] = "DISTINCT"
        else:
            verdicts[key] = "PARTIAL"
    rep["verdicts"] = verdicts
    raw = json.dumps(rep, indent=1, default=float)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "e1_report.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    exp_s, conf_s = [], []
    for (inst, date) in fd:
        (exp_s if date <= 20260331 else conf_s).append(f"{inst}:{date}")
    with measurement_episode(LEDGER, "EP-TBZ-E1-20260924", goal="TBZ E1 target-free: censo y solapamiento de variantes",
                             recorded_by="tools/tbz_stage1.py report", repo=REPO, prereg_ref=PREREG) as ep:
        st = ep.store
        if "P-TBZ-EXP" not in st.partitions:
            st.record_partition("P-TBZ-EXP", "EXPLORATION", "MES y ES 25T pre-holdout hasta 2026-03-31 (mismo subyacente)", sorted(exp_s))
            st.record_partition("P-TBZ-CONF", "CONFIRMATION_RESERVED", "MES y ES 25T 2026-04-01..2026-06-30", sorted(conf_s))
        dep = [f"CODE:tbz_bands@{hashlib.sha256((REPO / 'edgelab/research/tbz_bands.py').read_bytes()).hexdigest()[:16]}",
               "DATA:viewer_bundles_25T_HFT_SCALED_FUNNEL_V1"]
        st.record_observation("OBS-TBZ-E1A-CENSUS", "censo de franjas por variante (MES, ES)", "TARGET_FREE", ["P-TBZ-EXP", "P-TBZ-CONF"],
                              {i: {"sessions": c2["sessions"], "exp_per_session": {k: e["per_session"] for k, e in c2["exp"].items()},
                                   "dwell_share_with_gap": {k: dd["share_with_gap"] for k, dd in c2["dwell"].items()}}
                               for i, c2 in rep["census"].items()}, {"note": "construcción, sin precio posterior"}, sha, depends_on=dep)
        st.record_observation("OBS-TBZ-E1B-OVERLAP", "solapamiento entre variantes contra franjas al azar", "TARGET_FREE",
                              ["P-TBZ-EXP", "P-TBZ-CONF"], {"verdicts": verdicts}, {"null": "desplazamiento al azar, 20 réplicas"},
                              sha, depends_on=dep)
    print(json.dumps(dict(verdicts=verdicts, sha=sha[:12]), indent=1))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["bundles", "report", "one"])
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--bundle")
    a = ap.parse_args(argv)
    if a.step == "bundles":
        step_bundles(a.workers)
    elif a.step == "one":
        print(process_bundle(a.bundle))
    else:
        step_report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

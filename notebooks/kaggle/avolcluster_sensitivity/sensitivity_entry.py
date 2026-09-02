#!/usr/bin/env python3
"""Sensibilidad de aVolClusterPOI a ruido de +-1 en el volumen por tick.

Mide cuanto cambian las zonas si se perturba el volumen tick a tick en +-1,
que es la magnitud del ruido real observado entre NT8 y Python
(docs/research/avolcluster_parity_full_20260902/). Da el numero con el que
decidir si conviene seguir con este indicador o pasar a uno sin footprint.

Vectorizado. Target-free. No modifica codigo de produccion.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "f1e5f5dd929d6fc23bae9b5825f02e763086c119"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT = Path("/kaggle/input")
OPERABLE_START, OPERABLE_END_EXCLUSIVE = 20260317, 20260616
TICKS_PER_BAR = 120
SEEDS = [11, 22, 33]
OUT = Path("/kaggle/working/avolcluster_sensitivity")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def checkout(commit: str) -> str:
    if len(commit) != 40:
        raise SystemExit("EXPECTED_COMMIT debe ser SHA de 40 chars")
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    if not (REPO_DIR / ".git").exists():
        # el clone anonimo puede fallar transitoriamente pidiendo credenciales;
        # se reintenta antes de abortar la corrida
        last = None
        for attempt in range(4):
            r = subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                                REPO_URL, str(REPO_DIR)], env=env)
            if r.returncode == 0:
                break
            last = r.returncode
            print("clone falló (intento", attempt + 1, "rc=", last, "), reintentando", flush=True)
            subprocess.run(["rm", "-rf", str(REPO_DIR)])
            time.sleep(5 * (attempt + 1))
        else:
            raise SystemExit(f"git clone fallo tras 4 intentos (rc={last})")
        subprocess.run(["git", "sparse-checkout", "set", "--no-cone", "edgelab/**"],
                       cwd=REPO_DIR, check=True)
    subprocess.run(["git", "fetch", "origin", commit, "--depth", "200"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "checkout", "-B", "sens", commit], cwd=REPO_DIR, check=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
    if actual != commit:
        raise SystemExit("code provenance gate failed")
    sys.path.insert(0, str(REPO_DIR))
    return actual


def zone_key(z):
    # las zonas emitidas por run() traen top/bottom en PRECIO (no lower_tick);
    # se redondea a 6 decimales para que la clave sea estable
    return (round(float(z["bottom"]), 6), round(float(z["top"]), 6), str(z.get("kind")))


def main() -> int:
    t0 = time.time()
    commit = checkout(EXPECTED_COMMIT)
    print("repo_commit=", commit, "cpu_count=", os.cpu_count(), flush=True)
    import numpy as np
    from edgelab.bridge import bars as bars_mod, ticks as ticks_mod
    from edgelab.bridge.ticks import TickSeries
    from edgelab.bridge.indicators import avolclusterpoi
    from edgelab.kaggle.sessions_cme import trade_date_ymd

    hits = sorted(KAGGLE_INPUT.rglob("NQ_06-26_ticks.parquet"))
    full = ticks_mod.load_canonical_parquet(str(hits[0]))
    days = trade_date_ymd(full.ts_ns)
    idx = np.flatnonzero((days >= OPERABLE_START) & (days < OPERABLE_END_EXCLUSIVE))

    def build(vol_arr):
        t = TickSeries(ts_ns=full.ts_ns[idx], price_ticks=full.price_ticks[idx],
                       volume=vol_arr,
                       bid_ticks=full.bid_ticks[idx] if full.bid_ticks is not None else None,
                       ask_ticks=full.ask_ticks[idx] if full.ask_ticks is not None else None,
                       sequence=full.sequence[idx], tick_size=full.tick_size,
                       instrument=full.instrument, contract=full.contract, source=full.source)
        bars = bars_mod.build_tick_bars(t, TICKS_PER_BAR)
        fp = bars_mod.build_footprints(t, bars)
        r = avolclusterpoi.run(t, bars, fp, debug_trace=True)
        return r["zones"], r["block_trace"]

    base_vol = full.volume[idx]
    print("ticks=", len(base_vol), "t=", round(time.time() - t0, 1), flush=True)
    z0, b0 = build(base_vol)
    k0 = {zone_key(z) for z in z0}
    d0 = [x["decision"] for x in b0]
    print("baseline zonas=", len(z0), "bloques=", len(b0),
          "t=", round(time.time() - t0, 1), flush=True)

    runs = []
    for s in SEEDS:
        rng = np.random.default_rng(s)
        noise = rng.integers(-1, 2, size=len(base_vol))          # -1, 0, +1
        pert = np.maximum(base_vol.astype(np.int64) + noise, 1)  # volumen minimo 1
        z1, b1 = build(pert)
        k1 = {zone_key(z) for z in z1}
        inter = len(k0 & k1)
        union = len(k0 | k1)
        dec_changed = sum(1 for a, b in zip(d0, b1) if a != b) if len(b1) == len(d0) else None
        runs.append({
            "seed": s, "n_zones_baseline": len(k0), "n_zones_perturbed": len(k1),
            "zones_identical": inter, "jaccard_zones": round(inter / union, 6) if union else 1.0,
            "zone_turnover": round(1 - (inter / union), 6) if union else 0.0,
            "n_blocks_perturbed": len(b1),
            "blocks_decision_changed": dec_changed,
            "pct_blocks_decision_changed": (round(dec_changed / len(d0), 6)
                                            if dec_changed is not None else None),
            "pct_ticks_perturbed": round(float((noise != 0).mean()), 6),
        })
        print("seed", s, "turnover_zonas=", runs[-1]["zone_turnover"],
              "bloques_cambiados=", dec_changed, "t=", round(time.time() - t0, 1), flush=True)

    tos = [r["zone_turnover"] for r in runs]
    report = {
        "schema": "avolclusterpoi_volume_noise_sensitivity_v1",
        "status": "DIAGNOSTIC_NO_CODE_CHANGED",
        "question": ("cuanto cambian las zonas si el volumen por tick se perturba en +-1, "
                     "que es la magnitud del ruido real medido contra NT8"),
        "code_commit": commit, "cpu_count": os.cpu_count(),
        "operable_interval": [OPERABLE_START, OPERABLE_END_EXCLUSIVE],
        "n_ticks": int(len(base_vol)), "seeds": SEEDS, "runs": runs,
        "zone_turnover_mean": round(sum(tos) / len(tos), 6),
        "zone_turnover_min": min(tos), "zone_turnover_max": max(tos),
        "elapsed_seconds": round(time.time() - t0, 1),
        "outcomes_accessed": False, "holdout_accessed": False, "code_modified": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "volume_noise_sensitivity_v1.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Kaggle entrypoint: SL/TP/BE EXPERIMENTAL_NON_CONFIRMATORY sobre 1 contrato
de GC + 1 de NQ (override explicito de Nico, 2026-09-01, ver
docs/research/sltp_be_experimental_gc_nq_2026-09-01.json y PENDIENTE.md P-62).

Mismo patron que notebooks/kaggle/avolclusterpoi_tracedump_runner.py: clona a
un commit fijo, carga desde /kaggle/input/, corre, escribe a /kaggle/working/.

No abre outcomes silenciosamente: outcomes_opened=True esta declarado a
proposito en la salida porque ESTA corrida SI mira TP/SL/BE -- es el motivo
explicito por el que Nico autorizo la corrida. No declara edge, no promueve.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "755dc3cb4771eb426ca8988ae1726c3abf382645"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT_ROOT = Path("/kaggle/input")

if not (REPO_DIR / ".git").exists():
    subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)], check=True)
    subprocess.run(["git", "sparse-checkout", "set", "--no-cone",
                     "edgelab/**", "tools/**"], cwd=REPO_DIR, check=True)
subprocess.run(["git", "fetch", "origin", EXPECTED_COMMIT, "--depth", "200"], cwd=REPO_DIR, check=True)
subprocess.run(["git", "checkout", "-B", "sltp_experimental", EXPECTED_COMMIT], cwd=REPO_DIR, check=True)
actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
if actual != EXPECTED_COMMIT:
    raise SystemExit("checked-out commit differs from EXPECTED_COMMIT")
print("repo_commit=", actual, flush=True)

sys.path.insert(0, str(REPO_DIR))
from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.bridge.indicators.bigtrap2absorption import run as run_bt2a  # noqa: E402
from edgelab.research.bt2a_sltp_breakeven_exitlogic import simulate_exit  # noqa: E402

sys.path.insert(0, str(REPO_DIR / "tools"))
from bt2_absorption_param_sweep import session_dates_from_ns  # noqa: E402

BT2A_DEFAULTS = dict(
    score_mode="AbsMagnitude", tape_window_ticks=25, absorption_pct=90.0,
    absorption_lookback=500, min_history_buckets=200, require_flow_side_match=True,
    imbalance_mode="Diagonal", trap_volume_source="AggressiveSide", ticks_per_row=1,
    imbalance_ratio=3.0, min_stacked_rows=2, min_trap_frac=0.2, min_trap_volume=0.0,
    min_export_volume=1.0, use_wick_filter=True, wick_zone_pct=30.0, min_delta_filter=0.0,
    invalidation="CloseThrough", max_age_bars=200, bar_ticks=25,
)

CELLS = [
    dict(key="REF_B9_H100", target_ticks=9, stop_ticks=9, trigger_ticks=None, tick_cap=100),
    dict(key="REF_B18_H100", target_ticks=18, stop_ticks=18, trigger_ticks=None, tick_cap=100),
    dict(key="ASIM_TP18_SL9_H100", target_ticks=18, stop_ticks=9, trigger_ticks=None, tick_cap=100),
    dict(key="ASIM_TP9_SL18_H100", target_ticks=9, stop_ticks=18, trigger_ticks=None, tick_cap=100),
    dict(key="BE_G9_TP18_SL18_H100", target_ticks=18, stop_ticks=18, trigger_ticks=9, tick_cap=100),
]

ASSETS = {
    "GC": dict(filename="GC_08-26_ticks.parquet", cost_model="frozen_p2b",
               base_friction_ticks=3.5, adverse_friction_ticks=5.5, tick_value_usd=10.0),
    "NQ": dict(filename="NQ_09-26_ticks.parquet", cost_model="none_validated",
               base_friction_ticks=None, adverse_friction_ticks=None, tick_value_usd=5.0),
}


def pick_one_contract_parquet(filename: str) -> Path:
    hits = list(KAGGLE_INPUT_ROOT.rglob(filename))
    if not hits:
        raise FileNotFoundError(f"{filename} not found anywhere under {KAGGLE_INPUT_ROOT}")
    return hits[0]


def run_asset(name: str, cfg: dict) -> dict:
    path = pick_one_contract_parquet(cfg["filename"])
    print(f"[*] {name}: {path.name}", flush=True)
    ticks = load_canonical_parquet(str(path))
    session_labels = session_dates_from_ns(ticks.ts_ns)

    result = run_bt2a(ticks, params=BT2A_DEFAULTS)
    zones = result["zones"]
    signals = [dict(fill_idx=int(z["fill_idx"]), direction=(1 if z["dir"] == "long" else -1)) for z in zones]
    print(f"    n_signals={len(signals)}", flush=True)

    cell_results = {}
    for cell in CELLS:
        outcomes = []
        for s in signals:
            try:
                r = simulate_exit(
                    ticks.price_ticks, ticks.ts_ns, ticks.sequence, session_labels,
                    fill_idx=s["fill_idx"], direction=s["direction"],
                    target_ticks=cell["target_ticks"], stop_ticks=cell["stop_ticks"],
                    trigger_ticks=cell["trigger_ticks"], tick_cap=cell["tick_cap"],
                )
                outcomes.append(r)
            except (ValueError, IndexError):
                continue
        scores = np.asarray([o.score_ticks for o in outcomes], dtype=np.float64)
        n = len(outcomes)
        by_outcome = {}
        for o in outcomes:
            by_outcome[o.outcome] = by_outcome.get(o.outcome, 0) + 1
        econ = None
        if cfg["cost_model"] == "frozen_p2b" and n:
            base_f, adv_f = cfg["base_friction_ticks"], cfg["adverse_friction_ticks"]
            net = np.where(scores > 0, scores - base_f, scores - adv_f)
            econ = dict(median_net_ticks=float(np.median(net)), mean_net_ticks=float(np.mean(net)),
                        median_net_usd=float(np.median(net) * cfg["tick_value_usd"]),
                        mean_net_usd=float(np.mean(net) * cfg["tick_value_usd"]))
        cell_results[cell["key"]] = dict(
            n=n, by_outcome=by_outcome,
            median_gross_ticks=float(np.median(scores)) if n else None,
            mean_gross_ticks=float(np.mean(scores)) if n else None,
            economics=econ,
        )
        print(f"    {cell['key']}: n={n} median_gross_ticks={cell_results[cell['key']]['median_gross_ticks']}", flush=True)

    return dict(asset=name, contract_file=path.name, n_ticks=len(ticks), n_signals=len(signals),
                cost_model=cfg["cost_model"], tick_value_usd=cfg["tick_value_usd"], cells=cell_results)


def main() -> int:
    out = {
        "schema": "sltp_be_experimental_gc_nq_v1",
        "status": "EXPERIMENTAL_NON_CONFIRMATORY",
        "edge_declared": False,
        "promotion_eligible": False,
        "outcomes_opened": True,
        "platform": "kaggle",
        "repo_commit": EXPECTED_COMMIT,
        "override_authorized_by": "Nico, 2026-09-01, explicito en chat -- override de DRAFT_DESIGN_ONLY_PREAUTHORIZATION (GC) y NO_DIRECTIONAL_MECHANISM (NQ); tambien override explicito del memo CME/Kaggle para esta corrida puntual",
        "scope": "1 contrato por activo (GC 08-26 / NQ 09-26, elegidos por tamano de archivo -- mas chico = mas rapido en Kaggle), 5 celdas chicas -- NO la grilla de 372+24+16 de la campana real. max_age_bars=200 (no 2000) para acotar el cuello de botella O(n_blocks x n_active_zones) de update_active_zones -- parametro de conveniencia de ESTA corrida experimental, no toca la config de campana congelada",
        "assets": {},
    }
    for name, cfg in ASSETS.items():
        out["assets"][name] = run_asset(name, cfg)

    out_dir = Path("/kaggle/working/sltp_be_experimental")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sltp_be_experimental_gc_nq_2026-09-01.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"escrito: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

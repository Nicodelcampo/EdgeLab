#!/usr/bin/env python3
"""Kaggle entrypoint: barrido de G (break-even trigger) EXPERIMENTAL_NON_CONFIRMATORY,
GC + NQ, recorte a las primeras 2 sesiones completas de cada contrato.

Responde a la pregunta de Nico "se midieron las mejores entradas con break
even?" -- la corrida previa (sltp_be_experimental_gc_nq_2026-09-01_KAGGLE.json)
solo probo UN G (=9) fijo. Este script barre G en un rango denso para ver la
forma de la curva antes de plantear la campana completa (372 celdas,
specs/bt2a_gc_exitlogic_sltp_breakeven_campaign_v1.draft.json, todavia
DRAFT_DESIGN_ONLY_PREAUTHORIZATION).

TP/SL fijos en 18/18 (mismo par que el unico punto BE ya medido, para que el
barrido de G sea comparable con ese dato). REF_B18_H100 (sin BE) se incluye
como baseline de referencia.

Recorte a 2 sesiones completas (no un tope de ticks arbitrario): usa
session_dates_from_ns para no cortar una sesion a la mitad. "Un par de dias"
pedido por Nico -- mirada rapida, no una corrida completa.

Mismo override de gobierno que la corrida anterior (Nico, 2026-09-01):
DRAFT_DESIGN_ONLY_PREAUTHORIZATION (GC), NO_DIRECTIONAL_MECHANISM (NQ),
memo CME/Kaggle. Ver PENDIENTE.md P-60/P-61.

No abre outcomes silenciosamente: outcomes_opened=True a proposito, ESTA
corrida SI mira TP/SL/BE. No declara edge, no promueve.
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
N_SESSIONS_CAP = 2

if not (REPO_DIR / ".git").exists():
    subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)], check=True)
    subprocess.run(["git", "sparse-checkout", "set", "--no-cone",
                     "edgelab/**", "tools/**"], cwd=REPO_DIR, check=True)
subprocess.run(["git", "fetch", "origin", EXPECTED_COMMIT, "--depth", "200"], cwd=REPO_DIR, check=True)
subprocess.run(["git", "checkout", "-B", "be_sweep_experimental", EXPECTED_COMMIT], cwd=REPO_DIR, check=True)
actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
if actual != EXPECTED_COMMIT:
    raise SystemExit("checked-out commit differs from EXPECTED_COMMIT")
print("repo_commit=", actual, flush=True)

sys.path.insert(0, str(REPO_DIR))
from edgelab.bridge.ticks import load_canonical_parquet, TickSeries  # noqa: E402
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
    invalidation="CloseThrough", max_age_bars=50, bar_ticks=25,
)

TP_SL_FIXED = 18  # mismo par que el punto BE ya medido (G=9/TP=18/SL=18)
G_VALUES = [3, 6, 9, 12, 15]  # 0 < trigger_ticks < target_ticks=18

CELLS = [dict(key="REF_B18_H100_noBE", target_ticks=TP_SL_FIXED, stop_ticks=TP_SL_FIXED,
              trigger_ticks=None, tick_cap=100)]
for g in G_VALUES:
    CELLS.append(dict(key=f"BE_G{g}_TP{TP_SL_FIXED}_SL{TP_SL_FIXED}_H100",
                       target_ticks=TP_SL_FIXED, stop_ticks=TP_SL_FIXED,
                       trigger_ticks=g, tick_cap=100))

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


def truncate_to_first_sessions(ticks: TickSeries, session_labels: np.ndarray, n_sessions: int):
    # ultimas n_sessions, no las primeras: contratos lejanos al vencimiento
    # tienen volumen casi nulo al principio de su vida (ver GC_08-26 en
    # 2026-02: 227 ticks en 2 sesiones, 0 senales). Las ultimas sesiones del
    # archivo estan mas cerca del corte pre-holdout, con volumen real.
    dates = sorted(set(session_labels.tolist()))[-n_sessions:]
    mask = np.isin(session_labels, dates)
    idx = np.flatnonzero(mask)
    sub = TickSeries(
        ts_ns=ticks.ts_ns[idx], price_ticks=ticks.price_ticks[idx], volume=ticks.volume[idx],
        bid_ticks=ticks.bid_ticks[idx] if ticks.bid_ticks is not None else None,
        ask_ticks=ticks.ask_ticks[idx] if ticks.ask_ticks is not None else None,
        sequence=ticks.sequence[idx], tick_size=ticks.tick_size,
        instrument=ticks.instrument, contract=ticks.contract, source=ticks.source,
    )
    return sub, dates


def run_asset(name: str, cfg: dict) -> dict:
    path = pick_one_contract_parquet(cfg["filename"])
    print(f"[*] {name}: {path.name}", flush=True)
    ticks_full = load_canonical_parquet(str(path))
    session_labels_full = session_dates_from_ns(ticks_full.ts_ns)
    ticks, session_dates_used = truncate_to_first_sessions(ticks_full, session_labels_full, N_SESSIONS_CAP)
    session_labels = session_dates_from_ns(ticks.ts_ns)
    print(f"    sesiones usadas={session_dates_used} n_ticks={len(ticks)} (de {len(ticks_full)} totales)", flush=True)

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
            trigger_ticks=cell["trigger_ticks"], n=n, by_outcome=by_outcome,
            median_gross_ticks=float(np.median(scores)) if n else None,
            mean_gross_ticks=float(np.mean(scores)) if n else None,
            economics=econ,
        )
        print(f"    {cell['key']}: n={n} mean_gross_ticks={cell_results[cell['key']]['mean_gross_ticks']}", flush=True)

    return dict(asset=name, contract_file=path.name, sessions_used=session_dates_used,
                n_ticks=len(ticks), n_ticks_full_contract=len(ticks_full), n_signals=len(signals),
                cost_model=cfg["cost_model"], tick_value_usd=cfg["tick_value_usd"], cells=cell_results)


def main() -> int:
    out = {
        "schema": "be_trigger_sweep_gc_nq_v1",
        "status": "EXPERIMENTAL_NON_CONFIRMATORY",
        "edge_declared": False,
        "promotion_eligible": False,
        "outcomes_opened": True,
        "platform": "kaggle",
        "repo_commit": EXPECTED_COMMIT,
        "override_authorized_by": "Nico, 2026-09-01, mismo override que sltp_be_experimental_gc_nq_2026-09-01_KAGGLE.json (P-60/P-61)",
        "scope": (
            f"Barrido de G (break-even trigger) en TP=SL={TP_SL_FIXED} fijo, "
            f"G in {G_VALUES}, mas baseline sin BE. Recorte a las primeras "
            f"{N_SESSIONS_CAP} sesiones completas de cada contrato (GC 08-26 / NQ 09-26) "
            "-- 'un par de dias', no la cinta completa. NO es la campana real "
            "(specs/bt2a_gc_exitlogic_sltp_breakeven_campaign_v1.draft.json, "
            "372 celdas, sigue DRAFT_DESIGN_ONLY_PREAUTHORIZATION)."
        ),
        "assets": {},
    }
    for name, cfg in ASSETS.items():
        out["assets"][name] = run_asset(name, cfg)

    out_dir = Path("/kaggle/working/be_trigger_sweep")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "be_trigger_sweep_gc_nq_2026-09-01.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"escrito: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

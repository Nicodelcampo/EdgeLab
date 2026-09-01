"""SL/TP/BE -- corrida EXPERIMENTAL_NON_CONFIRMATORY, 1 contrato de GC + 1 de NQ.

Override explicito de Nico (2026-09-01), sobre dos gates que hoy seguian
cerrados: GC (DRAFT_DESIGN_ONLY_PREAUTHORIZATION, falta suite RW/MCS) y NQ
(Gate1 dio NO_DIRECTIONAL_MECHANISM, no SUPPORTED). Un contrato por activo NO
alcanza para nada confirmatorio -- esto es una mirada rapida, no una campana.

Reusa piezas ya validadas, no reinventa:
- edgelab/bridge/indicators/bigtrap2absorption.py::run() para las senales K_ABS
  (mismo kernel que Puerta 1, ya con paridad medida).
- edgelab/research/bt2a_sltp_breakeven_exitlogic.py::simulate_exit() para la
  mecanica de salida (con su propio smoke test sintetico en verde).

Grilla CHICA (5 celdas), subconjunto representativo de
specs/bt2a_gc_exitlogic_sltp_breakeven_campaign_v1.draft.json (que define 372+24+16
celdas para la campana real -- no se corre esa grilla completa aca):
  REF   B=9,  H=100
  REF   B=18, H=100
  ASIM  TP=18/SL=9,  H=100
  ASIM  TP=9/SL=18,  H=100
  BE    G=9, TP=18, SL0=18, H=100

Economia: GC usa el modelo de costo YA CONGELADO en P2B (3.5t base / 5.5t adverso,
USER_SUPPLIED_FROZEN_ASSUMPTION_2026-08-27) -- transportarlo a NQ esta prohibido
por el propio spec. NQ se reporta SOLO en ticks brutos: no existe todavia un
modelo de friccion validado para NQ en este proyecto.

No abre holdout. No declara edge. No promueve ninguna celda.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.indicators.bigtrap2absorption import run as run_bt2a  # noqa: E402
from edgelab.research.bt2a_sltp_breakeven_exitlogic import simulate_exit  # noqa: E402
from tools.bt2_absorption_param_sweep import session_dates_from_ns, file_sha256  # noqa: E402
from tools.sweep_bigtrap2_tickframes import load_canonical_ticks  # noqa: E402

BT2A_DEFAULTS = dict(
    score_mode="AbsMagnitude", tape_window_ticks=25, absorption_pct=90.0,
    absorption_lookback=500, min_history_buckets=200, require_flow_side_match=True,
    imbalance_mode="Diagonal", trap_volume_source="AggressiveSide", ticks_per_row=1,
    imbalance_ratio=3.0, min_stacked_rows=2, min_trap_frac=0.2, min_trap_volume=0.0,
    min_export_volume=1.0, use_wick_filter=True, wick_zone_pct=30.0, min_delta_filter=0.0,
    invalidation="CloseThrough", max_age_bars=2000, bar_ticks=25,
)

CELLS = [
    dict(key="REF_B9_H100", target_ticks=9, stop_ticks=9, trigger_ticks=None, tick_cap=100),
    dict(key="REF_B18_H100", target_ticks=18, stop_ticks=18, trigger_ticks=None, tick_cap=100),
    dict(key="ASIM_TP18_SL9_H100", target_ticks=18, stop_ticks=9, trigger_ticks=None, tick_cap=100),
    dict(key="ASIM_TP9_SL18_H100", target_ticks=9, stop_ticks=18, trigger_ticks=None, tick_cap=100),
    dict(key="BE_G9_TP18_SL18_H100", target_ticks=18, stop_ticks=18, trigger_ticks=9, tick_cap=100),
]

ASSETS = {
    "GC": dict(contract="GC 04-26", tick_size=0.10, path=Path(r"E:\DatosNT8\GC 04-26.Last.txt"),
               cost_model="frozen_p2b", base_friction_ticks=3.5, adverse_friction_ticks=5.5, tick_value_usd=10.0),
    "NQ": dict(contract="NQ 09-25", tick_size=0.25, path=Path(r"D:\A  Trading\NQ 09-25.Last.txt"),
               cost_model="none_validated", base_friction_ticks=None, adverse_friction_ticks=None, tick_value_usd=5.0),
}


def run_asset(name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    path = cfg["path"]
    if not path.exists():
        raise FileNotFoundError(path)
    input_sha = file_sha256(path)
    ticks, *_ = load_canonical_ticks(path, tick_size=cfg["tick_size"], max_ticks=None)
    session_labels = session_dates_from_ns(ticks.ts_ns)

    result = run_bt2a(ticks, params=BT2A_DEFAULTS)
    zones = result["zones"]
    n_signals = len(zones)

    signals = []
    for z in zones:
        direction = 1 if z["dir"] == "long" else -1  # dir del kernel, ya resuelto (trapped_sellers->long)
        fill_idx = int(z["fill_idx"])
        signals.append(dict(fill_idx=fill_idx, direction=direction))

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
        median_ticks = float(np.median(scores)) if n else None
        mean_ticks = float(np.mean(scores)) if n else None

        econ = None
        if cfg["cost_model"] == "frozen_p2b" and n:
            base_f, adv_f = cfg["base_friction_ticks"], cfg["adverse_friction_ticks"]
            net = np.where(scores > 0, scores - base_f, scores - adv_f)
            econ = dict(
                median_net_ticks=float(np.median(net)), mean_net_ticks=float(np.mean(net)),
                median_net_usd=float(np.median(net) * cfg["tick_value_usd"]),
                mean_net_usd=float(np.mean(net) * cfg["tick_value_usd"]),
            )

        cell_results[cell["key"]] = dict(
            n=n, by_outcome=by_outcome,
            median_gross_ticks=median_ticks, mean_gross_ticks=mean_ticks,
            economics=econ,
        )

    return dict(
        asset=name, contract=cfg["contract"], input_sha256=input_sha,
        n_ticks=len(ticks), n_signals=n_signals,
        cost_model=cfg["cost_model"], tick_value_usd=cfg["tick_value_usd"],
        cells=cell_results,
    )


def main() -> int:
    out = {
        "schema": "sltp_be_experimental_gc_nq_v1",
        "status": "EXPERIMENTAL_NON_CONFIRMATORY",
        "edge_declared": False,
        "promotion_eligible": False,
        "outcomes_opened": True,
        "override_authorized_by": "Nico, 2026-09-01, explicito en chat -- override de DRAFT_DESIGN_ONLY_PREAUTHORIZATION (GC) y NO_DIRECTIONAL_MECHANISM (NQ)",
        "scope": "1 contrato por activo, 5 celdas chicas -- NO es la grilla de 372+24+16 de la campana real",
        "assets": {},
    }
    for name, cfg in ASSETS.items():
        print(f"[*] {name}: {cfg['contract']}", flush=True)
        out["assets"][name] = run_asset(name, cfg)
        print(f"    n_signals={out['assets'][name]['n_signals']}", flush=True)

    out_path = REPO_ROOT / "docs" / "research" / "sltp_be_experimental_gc_nq_2026-09-01.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"escrito: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

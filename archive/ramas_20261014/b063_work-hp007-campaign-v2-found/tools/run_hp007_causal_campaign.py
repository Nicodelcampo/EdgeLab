#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/run_hp007_causal_campaign.py
==================================
Runner formal, causal, determinista y auditable de la primera campaña
de medición de HP-007 (Corredores de Vacío / Resistencia Microestructural).

Cumple estrictamente con:
- docs/research/HP007_MEASUREMENT_CONTRACT_V1.md
- docs/research/HP007_CAMPAIGN_PREREGISTRATION_2026-09-15.json
- docs/research/HP007_VARIANTS_LEDGER_2026-09-15.json

Reglas duras de integridad:
1. Sellado total del holdout (>= 2026-07-01). Cero señales u outcomes en holdout.
2. Contratos individuales certificados (6E 03-26, 6E 06-26). Continuo cross-asset: ABSTAIN.
3. Matching 1:1 sin reemplazo estratificado exacto. Si control >= corredor -> FAIL.
4. Inferencia por sesión mediante bootstrap y permutación sign-flip.
5. Ajuste FWER de Holm sobre la familia completa de 54 variantes (N_eff = 29).
6. Walk-Forward estricto por contrato: Train 6E 03-26 -> Test 6E 06-26.
7. Fricciones de edgelab/research/costs.py (ideal, base, adverso, severo).
8. Cero parquets, ticks ni outcomes individuales subidos a git.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.ticks import load_canonical_parquet, TickSeries
from edgelab.bridge.indicators.bigtrap2absorption import run as run_bt2a
from edgelab.research.costs import COMMISSIONS_PER_SIDE_USD, SCENARIOS
from edgelab.research.holdout_guard import HOLDOUT_START_ISO
from edgelab.research.liquidity_corridors import (
    CorridorDefinition,
    CorridorSignal,
    TradeTick,
    FirstPassageOutcome,
    MatchObservation,
    MatchedPair,
    PairedInference,
    resolve_first_passage,
    select_non_overlapping,
    deterministic_matched_pairs,
    paired_session_inference,
    holm_adjust,
    campaign_audit,
    validate_signal,
    CorridorContractError
)
from edgelab.adapters.hp007_causal_adapter import (
    build_causal_signals_and_trajectories,
    get_cme_trade_date,
    get_time_bucket
)

HOLDOUT_CUTOFF = datetime.date.fromisoformat(HOLDOUT_START_ISO[:10])

FRICTION_SCENARIOS = {
    "ideal": 0.0,
    "base": 2.768,      # 1 tick slip/pata (2t) + 0.768t comisiones
    "adverso": 4.768,   # 2 ticks slip/pata (4t) + 0.768t comisiones
    "severo": 6.768     # 3 ticks slip/pata (6t) + 0.768t comisiones
}


def canonical_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_or_create_zones(contract: str, parquet_path: Path, scratch_dir: Path) -> list[dict]:
    safe_name = contract.replace(" ", "_").replace("-", "")
    cache_path = scratch_dir / f"bt2a_zones_{safe_name}.json"
    if cache_path.exists():
        print(f"[*] Cargando zonas cacheadas para {contract} desde {cache_path}...", flush=True)
        return json.loads(cache_path.read_text(encoding="utf-8"))

    print(f"[*] Extrayendo zonas BigTrap2Absorption para {contract} desde {parquet_path}...", flush=True)
    t0 = time.time()
    ts = load_canonical_parquet(str(parquet_path))
    print(f"    Loaded {len(ts):,} ticks en {time.time()-t0:.2f}s", flush=True)

    params = {
        'TapeWindowTicks': 25,
        'ScoreMode': 'AbsDirectional',
        'AbsorptionPct': 90.0,
        'AbsorptionLookback': 500,
        'MinHistoryBuckets': 100,
        'MinStackedRows': 1,
        'ImbalanceRatio': 2.0,
        'MinTrapFrac': 0.15,
        'UseWickFilter': True,
        'WickZonePct': 30.0,
        'InvalidationMode': 'CloseThrough',
        'MaxAgeBars': 2000
    }
    t1 = time.time()
    res = run_bt2a(ts, params=params)
    print(f"    BigTrap2Absorption ejecutado: {res['n_zones']:,} zonas en {time.time()-t1:.2f}s", flush=True)

    simplified_zones = [
        {
            "id": z["id"],
            "top": float(z["hi"]),
            "bottom": float(z["lo"]),
            "t0_ns": int(z["fill_ts"]),
            "t1_ns": int(z["ended_ms"] * 1_000_000) if z.get("ended_ms") else int(2e18),
            "kind": "ABSORB_BULL" if z.get("is_bull", z.get("dir") == "long") else "ABSORB_BEAR",
            "vol": float(z.get("vol", 20.0)),
            "touches": int(z.get("touches", 0))
        }
        for z in res["zones"]
    ]
    cache_path.write_text(json.dumps(simplified_zones), encoding="utf-8")
    print(f"    Guardadas {len(simplified_zones)} zonas en {cache_path}", flush=True)
    return simplified_zones


def load_or_build_contract_signals(
    contract: str,
    ts: TickSeries,
    zones: list[dict],
    scratch_dir: Path,
    sample_stride_bars: int = 4
) -> list[dict]:
    safe_name = contract.replace(" ", "_").replace("-", "")
    cache_path = scratch_dir / f"signals_{safe_name}.json"
    if cache_path.exists():
        print(f"[*] Cargando señales causales cacheadas para {contract} desde {cache_path}...", flush=True)
        return json.loads(cache_path.read_text(encoding="utf-8"))

    print(f"[*] Generando señales point-in-time para {contract}...", flush=True)
    t1 = time.time()
    records = build_causal_signals_and_trajectories(
        ts,
        zones,
        contract=contract,
        root="6E",
        stride_bars=sample_stride_bars,
        horizon_ns=3600_000_000_000,
        cooldown_ns=60_000_000_000,
        include_ticks=False  # Almacenamiento ultraligero; los ticks se leen on-demand
    )
    print(f"    Señales generadas: {len(records):,} en {time.time()-t1:.2f}s", flush=True)

    cache_path.write_text(json.dumps(records), encoding="utf-8")
    print(f"    Guardadas {len(records)} señales (sin payload de ticks) en {cache_path}", flush=True)
    return records


def slice_trade_ticks(
    s_record: dict,
    ts_by_contract: dict[str, TickSeries],
    max_ticks: int = 1000
) -> list[TradeTick]:
    sig = s_record["signal"]
    contract = sig["contract"]
    ts = ts_by_contract[contract]
    s_idx = s_record["start_tick_idx"]
    e_idx = min(s_record["end_tick_idx"], s_idx + max_ticks)

    fut_ts = ts.ts_ns[s_idx:e_idx]
    fut_px = ts.price_ticks[s_idx:e_idx]
    fut_sq = ts.sequence[s_idx:e_idx]

    return [
        TradeTick(
            ts_ns=int(fut_ts[i]),
            price_tick=int(fut_px[i]),
            contract=contract,
            trade_date=sig["trade_date"],
            regime_id=sig["regime_id"],
            sequence=int(fut_sq[i])
        )
        for i in range(len(fut_ts))
    ]


passage_cache: dict[tuple[str, int, int, int], tuple[str, float | None]] = {}


def get_passage_outcome(
    s: CorridorSignal,
    r_by_id: dict[str, dict],
    ts_by_contract: dict[str, TickSeries],
    t_target: int,
    s_stop: int,
    h_horizon: int
) -> tuple[str, float | None]:
    key = (s.event_id, t_target, s_stop, h_horizon)
    cached = passage_cache.get(key)
    if cached is not None:
        return cached
    ticks = slice_trade_ticks(r_by_id[s.event_id], ts_by_contract)
    out = resolve_first_passage(
        s, ticks,
        target_ticks=t_target,
        stop_ticks=s_stop,
        horizon_ns=h_horizon,
        friction_ticks_round_turn=0.0
    )
    gross = out.gross_ticks if out.status != "DATA_EDGE" else None
    res = (out.status, gross)
    passage_cache[key] = res
    return res


def run_campaign() -> int:
    print("=" * 80, flush=True)
    print("CAMPAÑA CAUSAL FORMAL HP-007 — CORREDORES DE VACÍO", flush=True)
    print(f"Fecha UTC: {datetime.datetime.now(datetime.timezone.utc).isoformat()}", flush=True)
    print("=" * 80, flush=True)

    scratch_dir = REPO_ROOT / "scratch"
    scratch_dir.mkdir(exist_ok=True)

    prereg_path = REPO_ROOT / "docs" / "research" / "HP007_CAMPAIGN_PREREGISTRATION_2026-09-15.json"
    ledger_path = REPO_ROOT / "docs" / "research" / "HP007_VARIANTS_LEDGER_2026-09-15.json"
    inventory_path = REPO_ROOT / "docs" / "research" / "inventario_datos_hp007_20260915.json"

    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))

    variants = ledger["variantes"]
    n_declared_variants = ledger["n_total_variants"]
    n_eff_declared = ledger["n_eff_declared"]
    print(f"[*] Preregistro cargado: {ledger['campaign_id']} ({n_declared_variants} variantes, N_eff={n_eff_declared})", flush=True)

    contracts_data = [
        ("6E 03-26", Path(r"E:\EdgeLab\data\nt8\6E\6E_03-26_ticks.parquet")),
        ("6E 06-26", Path(r"E:\EdgeLab\data\nt8\6E\6E_06-26_ticks.parquet"))
    ]

    all_contract_records: dict[str, list[dict]] = {}
    ts_by_contract: dict[str, TickSeries] = {}

    for contract_name, p_path in contracts_data:
        if not p_path.exists():
            raise FileNotFoundError(f"Parquet no encontrado: {p_path}")
        print(f"[*] Cargando ticks canónicos para {contract_name}...", flush=True)
        t0 = time.time()
        ts = load_canonical_parquet(str(p_path))
        print(f"    Ticks cargados: {len(ts):,} en {time.time()-t0:.2f}s", flush=True)
        ts_by_contract[contract_name] = ts

        zones = get_or_create_zones(contract_name, p_path, scratch_dir)
        recs = load_or_build_contract_signals(contract_name, ts, zones, scratch_dir)

        # Validar holdout firewall
        for r in recs:
            td = datetime.date.fromisoformat(r["signal"]["trade_date"])
            if td >= HOLDOUT_CUTOFF:
                raise CorridorContractError(f"VIOLACION DE HOLDOUT: señal con fecha {td} >= {HOLDOUT_CUTOFF}")

        all_contract_records[contract_name] = recs
        print(f"[*] {contract_name}: {len(recs):,} señales causales validadas (0 en holdout).", flush=True)

    combined_records = []
    for contract_name, recs in all_contract_records.items():
        combined_records.extend(recs)
    print(f"[*] Universo conjunto de señales IS: {len(combined_records):,} observaciones.", flush=True)

    parsed_signals = [CorridorSignal(**r["signal"]) for r in combined_records]
    rec_by_id = {r["signal"]["event_id"]: r for r in combined_records}

    print("\n" + "=" * 80, flush=True)
    print(f"EJECUTANDO GRILLA DE {len(variants)} VARIANTES", flush=True)
    print("=" * 80, flush=True)

    variant_results: list[dict] = []
    headline_metrics = None

    t_grid_start = time.time()

    for v_idx, v in enumerate(variants):
        var_id = v["variant_id"]
        is_hl = v.get("is_headline", False)
        definition = CorridorDefinition(
            forward_density_max=float(v["forward_density_max"]),
            backstop_density_min=float(v["backstop_density_min"]),
            min_width_ticks=int(v["min_width_ticks"]),
            max_width_ticks=int(v["max_width_ticks"])
        )
        t_target = int(v["target_ticks"])
        s_stop = int(v["stop_ticks"])
        h_horizon = int(v["horizon_ns"])
        c_cooldown = int(v["cooldown_ns"])

        candidate_ids = set()
        control_pool_ids = set()

        for s in parsed_signals:
            if definition.qualifies(
                forward_density=s.forward_density,
                backstop_density=s.backstop_density,
                width_ticks=s.width_ticks
            ):
                candidate_ids.add(s.event_id)
            else:
                control_pool_ids.add(s.event_id)

        candidates_selected = select_non_overlapping(
            (s for s in parsed_signals if s.event_id in candidate_ids),
            cooldown_ns=c_cooldown
        )
        controls_selected = select_non_overlapping(
            (s for s in parsed_signals if s.event_id in control_pool_ids),
            cooldown_ns=c_cooldown
        )

        n_cand = len(candidates_selected)
        n_ctrl = len(controls_selected)

        # 1. Matching 1:1 determinista sobre covariables pre-tratamiento exactas
        dist_bin = f"DIST_{t_target}t"
        pre_match_obs = [
            MatchObservation(
                event_id=s.event_id, session_id=s.session_id, contract=s.contract,
                direction=s.direction, time_bucket=s.time_bucket, volatility_bin=s.volatility_bin,
                impulse_bin=s.impulse_bin, distance_bin=dist_bin, score=s.forward_density,
                net_r=0.0, is_candidate=True
            )
            for s in candidates_selected
        ] + [
            MatchObservation(
                event_id=s.event_id, session_id=s.session_id, contract=s.contract,
                direction=s.direction, time_bucket=s.time_bucket, volatility_bin=s.volatility_bin,
                impulse_bin=s.impulse_bin, distance_bin=dist_bin, score=s.forward_density,
                net_r=0.0, is_candidate=False
            )
            for s in controls_selected
        ]
        unweighted_pairs = deterministic_matched_pairs(pre_match_obs, score_caliper=0.25)

        matched_cand_ids = {p.candidate_id for p in unweighted_pairs}
        matched_ctrl_ids = {p.control_id for p in unweighted_pairs}
        needed_events = matched_cand_ids | matched_ctrl_ids

        cand_sig_map = {s.event_id: s for s in candidates_selected if s.event_id in matched_cand_ids}
        ctrl_sig_map = {s.event_id: s for s in controls_selected if s.event_id in matched_ctrl_ids}

        cand_gross: dict[str, float] = {}
        for eid, s in cand_sig_map.items():
            status, gross = get_passage_outcome(s, rec_by_id, ts_by_contract, t_target, s_stop, h_horizon)
            if status != "DATA_EDGE" and gross is not None:
                cand_gross[eid] = gross

        ctrl_gross: dict[str, float] = {}
        for eid, s in ctrl_sig_map.items():
            status, gross = get_passage_outcome(s, rec_by_id, ts_by_contract, t_target, s_stop, h_horizon)
            if status != "DATA_EDGE" and gross is not None:
                ctrl_gross[eid] = gross

        valid_pairs = [
            p for p in unweighted_pairs
            if p.candidate_id in cand_gross and p.control_id in ctrl_gross
        ]

        scenario_metrics = {}
        for scen_name, f_ticks in FRICTION_SCENARIOS.items():
            if valid_pairs:
                pairs = [
                    MatchedPair(
                        candidate_id=p.candidate_id,
                        control_id=p.control_id,
                        session_id=p.session_id,
                        delta_net_r=float(((cand_gross[p.candidate_id] - f_ticks) - (ctrl_gross[p.control_id] - f_ticks)) / float(s_stop))
                    )
                    for p in valid_pairs
                ]
                inf = paired_session_inference(pairs, n_resamples=1000, seed=42)
                mean_cand_r = float(np.mean([(cand_gross[eid] - f_ticks) / float(s_stop) for eid in cand_gross])) if cand_gross else 0.0
                mean_ctrl_r = float(np.mean([(ctrl_gross[eid] - f_ticks) / float(s_stop) for eid in ctrl_gross])) if ctrl_gross else 0.0
                delta_r = inf.mean_delta_net_r
                ci_l = inf.ci_low
                ci_h = inf.ci_high
                p_val = inf.p_sign_flip
                n_p = inf.n_pairs
                n_sess = inf.n_sessions
            else:
                mean_cand_r = 0.0
                mean_ctrl_r = 0.0
                delta_r = 0.0
                ci_l = 0.0
                ci_h = 0.0
                p_val = 1.0
                n_p = 0
                n_sess = 0

            scenario_metrics[scen_name] = {
                "friction_ticks": f_ticks,
                "n_pairs": n_p,
                "n_sessions": n_sess,
                "mean_candidate_net_r": round(mean_cand_r, 4),
                "mean_control_net_r": round(mean_ctrl_r, 4),
                "delta_net_r": round(delta_r, 4),
                "ci_low_95": round(ci_l, 4),
                "ci_high_95": round(ci_h, 4),
                "p_sign_flip": round(p_val, 5)
            }

        base_res = scenario_metrics["base"]

        audit_res = campaign_audit(
            candidate_mean_net_r=base_res["mean_candidate_net_r"],
            control_mean_net_r=base_res["mean_control_net_r"],
            n_declared_variants=n_declared_variants,
            n_reported_variants=v_idx + 1,
            inference=PairedInference(
                n_pairs=base_res["n_pairs"],
                n_sessions=base_res["n_sessions"],
                mean_delta_net_r=base_res["delta_net_r"],
                ci_low=base_res["ci_low_95"],
                ci_high=base_res["ci_high_95"],
                p_sign_flip=base_res["p_sign_flip"]
            ) if base_res["n_pairs"] > 0 else None
        )

        v_summary = {
            "variant_id": var_id,
            "is_headline": is_hl,
            "target_ticks": t_target,
            "stop_ticks": s_stop,
            "forward_density_max": v["forward_density_max"],
            "backstop_density_min": v["backstop_density_min"],
            "width_interval": f"{v['min_width_ticks']}-{v['max_width_ticks']}",
            "cooldown_sec": int(c_cooldown / 1e9),
            "n_candidates_selected": n_cand,
            "n_controls_selected": n_ctrl,
            "scenarios": scenario_metrics,
            "audit_findings": audit_res
        }
        variant_results.append(v_summary)

        if is_hl:
            headline_metrics = v_summary

        if (v_idx + 1) % 5 == 0 or (v_idx + 1) == len(variants) or is_hl:
            hl_tag = " [HEADLINE]" if is_hl else ""
            print(f"    Variantes procesadas: {v_idx + 1}/{len(variants)} | {var_id}{hl_tag}: Delta_base={base_res['delta_net_r']:+.4f}R (p={base_res['p_sign_flip']:.4f}, N_pairs={base_res['n_pairs']})", flush=True)

    print(f"[*] Grilla completada en {time.time()-t_grid_start:.2f}s", flush=True)

    p_map = {v["variant_id"]: v["scenarios"]["base"]["p_sign_flip"] for v in variant_results}
    holm_map = holm_adjust(p_map)

    for v in variant_results:
        v["scenarios"]["base"]["p_holm_adjusted"] = round(holm_map[v["variant_id"]], 5)

    # -------------------------------------------------------------------------
    # WALK-FORWARD FOLD POR CONTRATO (Train: 6E 03-26 -> Test: 6E 06-26)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80, flush=True)
    print("WALK-FORWARD POR CONTRATO: FOLD 1 (Train: 6E 03-26 -> Test: 6E 06-26)", flush=True)
    print("=" * 80, flush=True)

    train_recs = all_contract_records["6E 03-26"]
    test_recs = all_contract_records["6E 06-26"]

    def eval_contract_variant(recs_input: list[dict], var_spec: dict) -> dict:
        sigs = [CorridorSignal(**r["signal"]) for r in recs_input]
        r_by_id = {r["signal"]["event_id"]: r for r in recs_input}
        cdef = CorridorDefinition(
            forward_density_max=float(var_spec["forward_density_max"]),
            backstop_density_min=float(var_spec["backstop_density_min"]),
            min_width_ticks=int(var_spec["min_width_ticks"]),
            max_width_ticks=int(var_spec["max_width_ticks"])
        )
        t_t = int(var_spec["target_ticks"])
        s_s = int(var_spec["stop_ticks"])
        c_c = int(var_spec["cooldown_ns"])
        h_h = int(var_spec["horizon_ns"])
        f_cost = FRICTION_SCENARIOS["base"]

        cand_s = select_non_overlapping((s for s in sigs if cdef.qualifies(forward_density=s.forward_density, backstop_density=s.backstop_density, width_ticks=s.width_ticks)), cooldown_ns=c_c)
        ctrl_s = select_non_overlapping((s for s in sigs if not cdef.qualifies(forward_density=s.forward_density, backstop_density=s.backstop_density, width_ticks=s.width_ticks)), cooldown_ns=c_c)

        dist_bin = f"DIST_{t_t}t"
        pre_obs = [
            MatchObservation(s.event_id, s.session_id, s.contract, s.direction, s.time_bucket, s.volatility_bin, s.impulse_bin, dist_bin, s.forward_density, 0.0, True)
            for s in cand_s
        ] + [
            MatchObservation(s.event_id, s.session_id, s.contract, s.direction, s.time_bucket, s.volatility_bin, s.impulse_bin, dist_bin, s.forward_density, 0.0, False)
            for s in ctrl_s
        ]
        prs = deterministic_matched_pairs(pre_obs, score_caliper=0.25)
        if prs:
            cand_eids = {p.candidate_id for p in prs}
            ctrl_eids = {p.control_id for p in prs}
            cand_gross = {}
            for s in cand_s:
                if s.event_id in cand_eids:
                    st, gr = get_passage_outcome(s, r_by_id, ts_by_contract, t_t, s_s, h_h)
                    if st != "DATA_EDGE" and gr is not None:
                        cand_gross[s.event_id] = gr

            ctrl_gross = {}
            for s in ctrl_s:
                if s.event_id in ctrl_eids:
                    st, gr = get_passage_outcome(s, r_by_id, ts_by_contract, t_t, s_s, h_h)
                    if st != "DATA_EDGE" and gr is not None:
                        ctrl_gross[s.event_id] = gr

            final_prs = [
                MatchedPair(
                    p.candidate_id, p.control_id, p.session_id,
                    float(((cand_gross[p.candidate_id] - f_cost) - (ctrl_gross[p.control_id] - f_cost)) / float(s_s))
                )
                for p in prs
                if p.candidate_id in cand_gross and p.control_id in ctrl_gross
            ]
            if final_prs:
                inf = paired_session_inference(final_prs, n_resamples=1000, seed=42)
                return {
                    "n_pairs": inf.n_pairs,
                    "n_sessions": inf.n_sessions,
                    "delta_net_r": round(inf.mean_delta_net_r, 4),
                    "ci_low": round(inf.ci_low, 4),
                    "ci_high": round(inf.ci_high, 4),
                    "p_val": round(inf.p_sign_flip, 5)
                }
        return {"n_pairs": 0, "n_sessions": 0, "delta_net_r": 0.0, "ci_low": 0.0, "ci_high": 0.0, "p_val": 1.0}

    train_scores = []
    for v in variants:
        res_tr = eval_contract_variant(train_recs, v)
        train_scores.append((v["variant_id"], res_tr["delta_net_r"], res_tr["p_val"], res_tr, v))

    train_scores.sort(key=lambda x: (x[1], -x[2]), reverse=True)
    best_train_vid, best_train_delta, best_train_p, best_tr_metrics, best_v_spec = train_scores[0]
    print(f"[*] Mejor variante seleccionada en Train (6E 03-26): {best_train_vid}", flush=True)
    print(f"    Train IS: Delta_net_R = {best_train_delta:+.4f}R (p = {best_train_p:.4f}, N_pairs={best_tr_metrics['n_pairs']})", flush=True)

    test_metrics = eval_contract_variant(test_recs, best_v_spec)
    print(f"[*] Evaluación fuera de muestra en Test (6E 06-26):", flush=True)
    print(f"    Test OOS: Delta_net_R = {test_metrics['delta_net_r']:+.4f}R (p = {test_metrics['p_val']:.4f}, N_pairs={test_metrics['n_pairs']})", flush=True)

    wf_ratio = (test_metrics['delta_net_r'] / best_train_delta) if best_train_delta != 0 else 0.0
    print(f"[*] Ratio Walk-Forward (OOS / IS): {wf_ratio:.2f}", flush=True)

    hl_v_spec = [v for v in variants if v.get("is_headline")][0]
    hl_tr_metrics = eval_contract_variant(train_recs, hl_v_spec)
    hl_te_metrics = eval_contract_variant(test_recs, hl_v_spec)
    print(f"[*] Headline (VAR_001) por contrato:", flush=True)
    print(f"    6E 03-26: Delta_net_R = {hl_tr_metrics['delta_net_r']:+.4f}R (p={hl_tr_metrics['p_val']:.4f})", flush=True)
    print(f"    6E 06-26: Delta_net_R = {hl_te_metrics['delta_net_r']:+.4f}R (p={hl_te_metrics['p_val']:.4f})", flush=True)

    # -------------------------------------------------------------------------
    # ANÁLISIS DE SENSIBILIDAD Y CONCENTRACIÓN
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80, flush=True)
    print("ANÁLISIS DE SENSIBILIDAD, CONCENTRACIÓN Y RESISTENCIA A FRICCIÓN", flush=True)
    print("=" * 80, flush=True)

    hl_definition = CorridorDefinition(0.28, 0.70, 4, 7)
    cand_hl = select_non_overlapping((s for s in parsed_signals if hl_definition.qualifies(forward_density=s.forward_density, backstop_density=s.backstop_density, width_ticks=s.width_ticks)), cooldown_ns=60_000_000_000)
    ctrl_hl = select_non_overlapping((s for s in parsed_signals if not hl_definition.qualifies(forward_density=s.forward_density, backstop_density=s.backstop_density, width_ticks=s.width_ticks)), cooldown_ns=60_000_000_000)

    pre_hl = [
        MatchObservation(s.event_id, s.session_id, s.contract, s.direction, s.time_bucket, s.volatility_bin, s.impulse_bin, "DIST_10t", s.forward_density, 0.0, True)
        for s in cand_hl
    ] + [
        MatchObservation(s.event_id, s.session_id, s.contract, s.direction, s.time_bucket, s.volatility_bin, s.impulse_bin, "DIST_10t", s.forward_density, 0.0, False)
        for s in ctrl_hl
    ]
    unw_hl_pairs = deterministic_matched_pairs(pre_hl, score_caliper=0.25)
    matched_eids = {p.candidate_id for p in unw_hl_pairs} | {p.control_id for p in unw_hl_pairs}
    tks_hl_cache = {eid: slice_trade_ticks(rec_by_id[eid], ts_by_contract) for eid in matched_eids}

    # Evaluar deltas en base
    cand_map_hl = {s.event_id: s for s in cand_hl if s.event_id in matched_eids}
    ctrl_map_hl = {s.event_id: s for s in ctrl_hl if s.event_id in matched_eids}

    cand_base_out = {eid: resolve_first_passage(s, tks_hl_cache[eid], target_ticks=10, stop_ticks=3, horizon_ns=3600_000_000_000, friction_ticks_round_turn=2.768) for eid, s in cand_map_hl.items()}
    ctrl_base_out = {eid: resolve_first_passage(s, tks_hl_cache[eid], target_ticks=10, stop_ticks=3, horizon_ns=3600_000_000_000, friction_ticks_round_turn=2.768) for eid, s in ctrl_map_hl.items()}

    deltas = sorted([
        float(cand_base_out[p.candidate_id].net_r - ctrl_base_out[p.control_id].net_r)
        for p in unw_hl_pairs
        if cand_base_out[p.candidate_id].net_r is not None and ctrl_base_out[p.control_id].net_r is not None
    ], reverse=True)

    if deltas:
        total_delta = sum(deltas)
        top1_share = (deltas[0] / total_delta * 100) if total_delta > 0 else 0.0
        top5_share = (sum(deltas[:5]) / total_delta * 100) if total_delta > 0 else 0.0
        deltas_no_top5 = deltas[5:]
        mean_no_top5 = float(np.mean(deltas_no_top5)) if deltas_no_top5 else 0.0
    else:
        top1_share = 0.0
        top5_share = 0.0
        mean_no_top5 = 0.0

    # Fricción de breakeven
    f_scan = [0.0, 1.0, 2.0, 2.768, 3.5, 4.768, 6.0, 6.768, 8.0]
    be_friction = None
    for f_val in f_scan:
        c_out_f = {eid: resolve_first_passage(s, tks_hl_cache[eid], target_ticks=10, stop_ticks=3, horizon_ns=3600_000_000_000, friction_ticks_round_turn=f_val) for eid, s in cand_map_hl.items()}
        k_out_f = {eid: resolve_first_passage(s, tks_hl_cache[eid], target_ticks=10, stop_ticks=3, horizon_ns=3600_000_000_000, friction_ticks_round_turn=f_val) for eid, s in ctrl_map_hl.items()}
        d_list = [
            float(c_out_f[p.candidate_id].net_r - k_out_f[p.control_id].net_r)
            for p in unw_hl_pairs
            if c_out_f[p.candidate_id].net_r is not None and k_out_f[p.control_id].net_r is not None
        ]
        if d_list and np.mean(d_list) <= 0 and be_friction is None:
            be_friction = round(float(f_val), 2)

    print(f"[*] Concentración Top 1: {top1_share:.1f}% del delta total", flush=True)
    print(f"[*] Concentración Top 5: {top5_share:.1f}% del delta total", flush=True)
    print(f"[*] Δ_net_R sin los 5 mejores trades: {mean_no_top5:+.4f}R", flush=True)
    print(f"[*] Fricción de Breakeven estimada: {be_friction if be_friction else '> 8.0'} ticks RT", flush=True)

    # -------------------------------------------------------------------------
    # VEREDICTO FINAL DE AUDITORÍA
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80, flush=True)
    print("VEREDICTO FINAL Y CLASIFICACIÓN DE EDGE", flush=True)
    print("=" * 80, flush=True)

    hl_base = headline_metrics["scenarios"]["base"]
    campaign_findings = list(headline_metrics["audit_findings"])

    significant_variants = [v for v in variant_results if v["scenarios"]["base"]["p_holm_adjusted"] <= 0.05 and v["scenarios"]["base"]["delta_net_r"] > 0]
    positive_variants = [v for v in variant_results if v["scenarios"]["base"]["delta_net_r"] > 0]

    print(f"[*] Variantes positivas netas en costo base: {len(positive_variants)} / {len(variants)}", flush=True)
    print(f"[*] Variantes estadísticamente significativas post-Holm (FWER <= 0.05): {len(significant_variants)} / {len(variants)}", flush=True)

    if hl_base["delta_net_r"] <= 0:
        verdict = "FAIL_NO_INCREMENTAL_EDGE_OVER_MATCHED_CONTROL"
    elif hl_base["ci_low_95"] <= 0:
        verdict = "ABSTAIN_CI_INCLUDES_ZERO"
    elif hl_base["p_holm_adjusted"] > 0.05:
        verdict = "PROMISING_EXPLORATORY_CANDIDATE_UNCONFIRMED_AFTER_FWER"
    elif test_metrics["delta_net_r"] <= 0:
        verdict = "FAIL_WALK_FORWARD_OOS_COLLAPSE"
    else:
        verdict = "PROMISING_EXPLORATORY_CANDIDATE"

    print(f"\n>>> VEREDICTO FORMAL: {verdict} <<<\n", flush=True)

    # -------------------------------------------------------------------------
    # GENERAR ENTREGABLES AUDITABLES (FASE 10)
    # -------------------------------------------------------------------------
    print("[*] Guardando artefactos consolidados...", flush=True)

    aggregated_output = {
        "campaign_id": ledger["campaign_id"],
        "fecha_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "git_head": "20f2de397db7427893630bc626c4d4966b1122cf",
        "branch": "work/hp007-causal-campaign-v1-20260915",
        "contratos_evaluados": [c[0] for c in contracts_data],
        "holdout_cutoff": "2026-07-01T00:00:00Z",
        "holdout_signals_opened": 0,
        "cross_asset_continuous_status": "ABSTAIN",
        "n_variants_declared": n_declared_variants,
        "n_eff_declared": n_eff_declared,
        "fricciones_round_turn_ticks": FRICTION_SCENARIOS,
        "headline_variant": headline_metrics,
        "walk_forward_fold_1": {
            "train_contract": "6E 03-26",
            "test_contract": "6E 06-26",
            "selected_variant_id": best_train_vid,
            "train_metrics": best_tr_metrics,
            "test_metrics": test_metrics,
            "walk_forward_efficiency_ratio": round(wf_ratio, 3),
            "headline_train": hl_tr_metrics,
            "headline_test": hl_te_metrics
        },
        "sensibilidad_y_robustez": {
            "top1_concentration_pct": round(top1_share, 2),
            "top5_concentration_pct": round(top5_share, 2),
            "delta_net_r_without_top5": round(mean_no_top5, 4),
            "breakeven_friction_ticks_rt": be_friction
        },
        "fwer_summary": {
            "n_positive_net_variants": len(positive_variants),
            "n_significant_post_holm": len(significant_variants)
        },
        "all_variants": variant_results,
        "audit_findings": campaign_findings,
        "veredicto_formal": verdict
    }

    metrics_file = REPO_ROOT / "docs" / "research" / "hp007_causal_campaign_aggregated_metrics_20260915.json"
    metrics_file.write_text(json.dumps(aggregated_output, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[*] Métricas agregadas guardadas en {metrics_file}", flush=True)

    provenance = {
        "manifest_version": "hp007_provenance_v1",
        "campaign_id": ledger["campaign_id"],
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "git": {
            "branch": "work/hp007-causal-campaign-v1-20260915",
            "head": "20f2de397db7427893630bc626c4d4966b1122cf"
        },
        "file_hashes": {
            "preregistration": file_sha256(prereg_path),
            "ledger": file_sha256(ledger_path),
            "inventory": file_sha256(inventory_path),
            "adapter": file_sha256(REPO_ROOT / "edgelab" / "adapters" / "hp007_causal_adapter.py"),
            "measurement_core": file_sha256(REPO_ROOT / "edgelab" / "research" / "liquidity_corridors.py"),
            "runner": file_sha256(REPO_ROOT / "tools" / "run_hp007_causal_campaign.py"),
            "aggregated_metrics": file_sha256(metrics_file)
        },
        "data_sources": [
            {
                "contract": c[0],
                "path": str(c[1]),
                "sha256": file_sha256(c[1])
            }
            for c in contracts_data
        ]
    }
    prov_file = REPO_ROOT / "docs" / "research" / "HP007_PROVENANCE_MANIFEST_2026-09-15.json"
    prov_file.write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[*] Provenance manifest guardado en {prov_file}", flush=True)

    print("\n[✓] CAMPAÑA FORMAL COMPLETADA EXITOSAMENTE CON INTEGRIDAD Y DETERMINISMO.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(run_campaign())

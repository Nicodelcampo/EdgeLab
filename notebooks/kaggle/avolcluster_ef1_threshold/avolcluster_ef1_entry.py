#!/usr/bin/env python3
"""EF1 -- sensibilidad de UN eje (`detection_percentile`) para aVolClusterPOI
sobre el intervalo operable de NQ 06-26, como DIAGNOSTICO PROVISIONAL.

Plan: specs/avolclusterpoi_ef1_plan_v1.draft.json (DRAFT_NOT_AUTHORIZED).
Autorizado por Nico 2026-09-02 como diagnostico provisional: el manifiesto de
regimen sigue sin certificar (`roll_schedule_sha256=PENDING_REGIME_CERTIFICATION`),
asi que NADA de esto puede promoverse a resultado formal.

Preguntas EF0 que responde: Q-THRESHOLD-PRESSURE y Q-ATPRICE-OFFPRICE.

Por que una sola corrida y no seis: `SessionProfile.add_block()` acumula
`best_score`, que NO depende de `detection_percentile`. La historia por bucket
es identica para toda la grilla. Entonces se reconstruye el trace UNA vez (con
reset en el borde del intervalo, igual que EF0) y los 6 niveles se recomputan
POST-HOC re-simulando el SessionProfile desde los BLOQUES -- sin recorrer
ticks ni reconstruir barras por nivel.

NO elige configuracion ganadora. Mide turnover de poblacion y estabilidad, no
ranking. No abre outcomes, retornos, MFE/MAE ni P&L.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "3a2b2abbe5e22a84bc0a1cc29863f301b47ac8ee"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT = Path("/kaggle/input")
OPERABLE_START, OPERABLE_END_EXCLUSIVE = 20260317, 20260616
TICKS_PER_BAR = 120
LEVELS = [96.0, 97.0, 97.5, 98.0, 98.5, 99.0]
BASELINE = 98.0
OUT = Path("/kaggle/working/avolcluster_ef1_threshold")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def checkout(commit: str) -> str:
    if len(commit) != 40:
        raise SystemExit("EXPECTED_COMMIT debe ser SHA de 40 chars")
    if not (REPO_DIR / ".git").exists():
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                        REPO_URL, str(REPO_DIR)], check=True)
        subprocess.run(["git", "sparse-checkout", "set", "--no-cone",
                        "edgelab/**", "specs/**"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "fetch", "origin", commit, "--depth", "200"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "checkout", "-B", "ef1_threshold", commit], cwd=REPO_DIR, check=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
    if actual != commit or subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=REPO_DIR, text=True).strip():
        raise SystemExit("code provenance gate failed")
    sys.path.insert(0, str(REPO_DIR))
    return actual


def replay(blocks, pct, SessionProfile, empirical_quantile, classify_kind, params):
    """Re-simula el SessionProfile desde los BLOQUES y reevalua la decision
    con `pct`. La historia acumulada es identica para todo pct porque solo se
    alimenta con best_score."""
    prof = SessionProfile(lookback_sessions=params["lookback_sessions"])
    min_samples = int(params["min_samples_per_bucket"])
    create_ids, off_ids, at_ids = [], [], []
    counts = {"CREATE": 0, "ABSTAIN_NO_HISTORY": 0, "ABSTAIN_NO_CLUSTER": 0,
              "ABSTAIN_BELOW_THRESHOLD": 0, "ABSTAIN_FEW_CELLS": 0}
    kind_by_block, ratios = {}, []
    current_session = None
    for b in blocks:
        sess = b.get("session_end_ns")
        if current_session is not None and sess != current_session:
            prof.commit()
        current_session = sess
        bid = f"{sess}:{b.get('block_index')}"
        bucket = b.get("bucket")
        clusters = b.get("clusters") or []
        hist = prof.history_scores(bucket)
        best = float(b.get("best_score") or 0.0)

        if b.get("decision") == "ABSTAIN_FEW_CELLS":
            counts["ABSTAIN_FEW_CELLS"] += 1
        elif len(hist) < min_samples:
            counts["ABSTAIN_NO_HISTORY"] += 1
        elif not clusters:
            counts["ABSTAIN_NO_CLUSTER"] += 1
        else:
            thr = empirical_quantile(sorted(hist), pct / 100.0)
            passing = [c for c in clusters if thr and thr > 0 and float(c["score"]) >= thr]
            if thr:
                ratios.append(best / thr if thr > 0 else 0.0)
            if not passing:
                counts["ABSTAIN_BELOW_THRESHOLD"] += 1
            else:
                counts["CREATE"] += 1
                win = max(passing, key=lambda c: float(c["score"]))
                kind, _d, _dist = classify_kind(b.get("close_tick"),
                                                int(win["lower_tick"]), int(win["upper_tick"]))
                create_ids.append(bid)
                kind_by_block[bid] = kind
                (off_ids if kind == "OFF_PRICE" else at_ids).append(bid)
        prof.add_block(bucket, best)
    prof.commit()
    return {"pct": pct, "counts": counts,
            "n_create": len(create_ids), "n_off_price": len(off_ids), "n_at_price": len(at_ids),
            "create_ids": set(create_ids), "off_ids": set(off_ids), "at_ids": set(at_ids),
            "kind_by_block": kind_by_block, "ratios": ratios}


def jaccard(a: set, b: set) -> float:
    u = len(a | b)
    return 1.0 if u == 0 else len(a & b) / u


def main() -> int:
    commit = checkout(EXPECTED_COMMIT)
    print("repo_commit=", commit, flush=True)
    import numpy as np
    from edgelab.bridge import bars as bars_mod, ticks as ticks_mod
    from edgelab.bridge.ticks import TickSeries
    from edgelab.bridge.indicators import avolclusterpoi
    from edgelab.bridge.indicators.avolclusterpoi import (
        RESEARCH_DEFAULTS, SessionProfile, classify_kind, empirical_quantile)
    from edgelab.kaggle.sessions_cme import trade_date_ymd, session_bounds_utc_ns
    from edgelab.kaggle.seal import HOLDOUT_START_YMD

    hits = sorted(KAGGLE_INPUT.rglob("NQ_06-26_ticks.parquet"))
    if len(hits) != 1:
        raise SystemExit("esperaba un parquet")
    full = ticks_mod.load_canonical_parquet(str(hits[0]))
    holdout_ns, _ = session_bounds_utc_ns(HOLDOUT_START_YMD)
    if int(full.ts_ns.max()) >= holdout_ns:
        raise SystemExit("el parquet alcanza el holdout")
    days = trade_date_ymd(full.ts_ns)
    idx = np.flatnonzero((days >= OPERABLE_START) & (days < OPERABLE_END_EXCLUSIVE))
    ticks = TickSeries(
        ts_ns=full.ts_ns[idx], price_ticks=full.price_ticks[idx], volume=full.volume[idx],
        bid_ticks=full.bid_ticks[idx] if full.bid_ticks is not None else None,
        ask_ticks=full.ask_ticks[idx] if full.ask_ticks is not None else None,
        sequence=full.sequence[idx], tick_size=full.tick_size, instrument=full.instrument,
        contract=full.contract, source=full.source)
    bars = bars_mod.build_tick_bars(ticks, TICKS_PER_BAR)
    fp = bars_mod.build_footprints(ticks, bars)
    base = avolclusterpoi.run(ticks, bars, fp, debug_trace=True)
    blocks = base["block_trace"]
    print(f"blocks={len(blocks):,} zones_baseline={len(base['zones']):,}", flush=True)

    params = dict(RESEARCH_DEFAULTS)
    runs = [replay(blocks, p, SessionProfile, empirical_quantile, classify_kind, params)
            for p in LEVELS]
    for r in runs:
        print(f"  pct={r['pct']:<5} create={r['n_create']:<5} off={r['n_off_price']:<5} "
              f"at={r['n_at_price']:<5} below={r['counts']['ABSTAIN_BELOW_THRESHOLD']}", flush=True)

    # control: el replay al baseline debe reproducir el trace real
    base_run = next(r for r in runs if r["pct"] == BASELINE)
    real_create = sum(1 for b in blocks if b.get("decision") == "CREATE")
    control = {"replay_create_at_baseline": base_run["n_create"], "trace_create": real_create,
               "match": base_run["n_create"] == real_create}
    print("control replay==trace:", control, flush=True)

    turnover = []
    for a, b in zip(runs, runs[1:]):
        moved = sum(1 for k in (a["kind_by_block"].keys() & b["kind_by_block"].keys())
                    if a["kind_by_block"][k] != b["kind_by_block"][k])
        turnover.append({
            "from_pct": a["pct"], "to_pct": b["pct"],
            "jaccard_create": round(jaccard(a["create_ids"], b["create_ids"]), 6),
            "jaccard_off_price": round(jaccard(a["off_ids"], b["off_ids"]), 6),
            "turnover_create": round(1 - jaccard(a["create_ids"], b["create_ids"]), 6),
            "blocks_reclassified_at_off": moved,
            "delta_create": b["n_create"] - a["n_create"]})
    for t in turnover:
        print(f"  {t['from_pct']}->{t['to_pct']}: turnover={t['turnover_create']:.3f} "
              f"dCREATE={t['delta_create']:+d} reclasificados={t['blocks_reclassified_at_off']}", flush=True)

    # regla de parada declarada en el plan
    mid = [t for t in turnover if (t["from_pct"], t["to_pct"]) in {(97.5, 98.0), (98.0, 98.5)}]
    worst = max((t["turnover_create"] for t in mid), default=0.0)
    fragile = worst > 0.50

    report = {
        "schema": "avolclusterpoi_ef1_threshold_v1",
        "status": "PROVISIONAL_DIAGNOSTIC_REGIME_NOT_CERTIFIED",
        "plan": "specs/avolclusterpoi_ef1_plan_v1.draft.json",
        "authorized_by": "Nico 2026-09-02, explicito, como diagnostico provisional",
        "roll_schedule_sha256": "PENDING_REGIME_CERTIFICATION",
        "questions": ["Q-THRESHOLD-PRESSURE", "Q-ATPRICE-OFFPRICE"],
        "axis": "detection_percentile", "levels": LEVELS, "baseline": BASELINE,
        "code_commit": commit, "n_blocks": len(blocks),
        "replay_control": control,
        "per_level": [{k: v for k, v in r.items()
                       if k not in ("create_ids", "off_ids", "at_ids", "kind_by_block", "ratios")}
                      for r in runs],
        "neighbor_turnover": turnover,
        "stopping_rule": {
            "rule": "turnover de CREATE entre 97.5 y 98.5 > 50% => fragilidad estructural, detener",
            "worst_mid_turnover": round(worst, 6), "triggered": fragile},
        "winner_selected": False, "outcomes_accessed": False, "holdout_accessed": False,
        "promotion_eligible": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ef1_threshold_report_v1.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "sha256_manifest.json").write_text(json.dumps(
        {p.name: sha256(p) for p in sorted(OUT.iterdir()) if p.is_file()}, indent=2), encoding="utf-8")
    with zipfile.ZipFile(Path("/kaggle/working/avolcluster_ef1_threshold.zip"), "w",
                         zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(OUT.iterdir()):
            zf.write(p, p.relative_to(OUT.parent))
    print(json.dumps({"status": report["status"], "worst_mid_turnover": round(worst, 6),
                      "stopping_rule_triggered": fragile}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

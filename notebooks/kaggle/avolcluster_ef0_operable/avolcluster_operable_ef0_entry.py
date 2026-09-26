#!/usr/bin/env python3
"""Reconstruye el trace de aVolClusterPOI SOLO sobre el intervalo operable de
NQ 06-26 con reset total de estado, y corre EF0 sobre ese trace.

Por que reconstruir en vez de filtrar el trace existente: el trace previo
(avolclusterpoi-tracedump-full-nq0626) recorrio las 72 sesiones del archivo,
de las cuales 3 son pre-roll (pertenecen a NQ 03-26) y 3 post-roll (NQ 09-26).
Filtrar sus bloques a posteriori NO deshace que la historia del indicador
(SessionProfile, buckets) se acumulo cruzando el roll -- violaria
`state_boundary = RESET_AT_CONTRACT_ROLL` del contrato de regimen.

El reset se logra recortando los TICKS antes de construir barras y correr el
indicador: barras, footprints y SessionProfile arrancan limpios en el borde
del intervalo.

Intervalo operable: [20260317, 20260616) -- 66 sesiones. Derivado del scan v2
(`docs/research/nq_contract_regime_v2_20260902/`) y del analisis de
sensibilidad P-68, que mostro que las 4 fechas de roll son identicas a 6
decimales con y sin feriados. **El manifiesto de regimen NO esta certificado**
(falta evidencia de completitud aprobada y Juneteenth 2026-06-19 sin
adjudicar), asi que la salida se rotula REGIME_NOT_CERTIFIED.

Target-free: no lee ni calcula outcomes, retornos, MFE/MAE ni P&L. EF0 rechaza
por contrato cualquier campo de esa familia.

Kaggle 'script' kernels no exponen archivos hermanos ni aceptan argv: este
archivo es autocontenido.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "b48675abea13e557de3f08ebafb826d554b8eaad"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT = Path("/kaggle/input")
CONTRACT = "NQ 06-26"
OPERABLE_START = 20260317          # inclusive
OPERABLE_END_EXCLUSIVE = 20260616  # exclusive
TICKS_PER_BAR = 120                # misma resolucion que el trace previo
OUT = Path("/kaggle/working/avolcluster_operable_ef0")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def checkout(commit: str) -> str:
    if len(commit) != 40:
        raise SystemExit("EXPECTED_COMMIT debe ser un SHA completo de 40 chars")
    if not (REPO_DIR / ".git").exists():
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                        REPO_URL, str(REPO_DIR)], check=True)
        subprocess.run(["git", "sparse-checkout", "set", "--no-cone",
                        "edgelab/**", "specs/**"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "fetch", "origin", commit, "--depth", "200"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "checkout", "-B", "ef0_operable", commit], cwd=REPO_DIR, check=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_DIR, text=True).strip()
    if actual != commit or dirty:
        raise SystemExit("code provenance gate failed")
    sys.path.insert(0, str(REPO_DIR))
    return actual


def main() -> int:
    commit = checkout(EXPECTED_COMMIT)
    print("repo_commit=", commit, flush=True)

    import numpy as np
    from edgelab.bridge import bars as bars_mod, ticks as ticks_mod
    from edgelab.bridge.ticks import TickSeries
    from edgelab.bridge.indicators import avolclusterpoi
    from edgelab.kaggle.sessions_cme import trade_date_ymd
    from edgelab.kaggle.seal import HOLDOUT_START_YMD
    from edgelab.kaggle.sessions_cme import session_bounds_utc_ns
    from edgelab.research.avolclusterpoi_funnel import (
        build_profile, build_question_cards, canonical_sha256, validate_trace)

    hits = sorted(KAGGLE_INPUT.rglob("NQ_06-26_ticks.parquet"))
    if len(hits) != 1:
        raise SystemExit(f"esperaba un parquet, encontre {len(hits)}")
    parquet = hits[0]
    full = ticks_mod.load_canonical_parquet(str(parquet))
    holdout_ns, _ = session_bounds_utc_ns(HOLDOUT_START_YMD)
    if int(full.ts_ns.max()) >= holdout_ns:
        raise SystemExit("el parquet alcanza el holdout")

    days = trade_date_ymd(full.ts_ns)
    mask = (days >= OPERABLE_START) & (days < OPERABLE_END_EXCLUSIVE)
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        raise SystemExit("el recorte operable quedo vacio")
    # RESET: los ticks se recortan ANTES de barras/footprints/indicador
    ticks = TickSeries(
        ts_ns=full.ts_ns[idx], price_ticks=full.price_ticks[idx], volume=full.volume[idx],
        bid_ticks=full.bid_ticks[idx] if full.bid_ticks is not None else None,
        ask_ticks=full.ask_ticks[idx] if full.ask_ticks is not None else None,
        sequence=full.sequence[idx], tick_size=full.tick_size,
        instrument=full.instrument, contract=full.contract, source=full.source)
    sessions_kept = sorted({int(x) for x in days[idx]})
    print(f"ticks {len(full.ts_ns):,} -> {len(ticks.ts_ns):,} | sesiones {len(sessions_kept)}"
          f" [{sessions_kept[0]}..{sessions_kept[-1]}]", flush=True)

    bars = bars_mod.build_tick_bars(ticks, TICKS_PER_BAR)
    footprints = bars_mod.build_footprints(ticks, bars)
    result = avolclusterpoi.run(ticks, bars, footprints, debug_trace=True)
    blocks, zones = result["block_trace"], result["zones"]
    print(f"bars={len(bars.close_t):,} blocks={len(blocks):,} zones={len(zones):,}", flush=True)

    summary = {
        # el gate de EF0 exige este valor exacto; el recorte operable se declara
        # en los campos de abajo, no alterando el scope
        "scope": "target_free_preholdout",
        "restriction": "operable_interval_only_state_reset_at_roll",
        "repo_commit": commit,
        "parquet": parquet.name,
        "contract": CONTRACT,
        "operable_interval": [OPERABLE_START, OPERABLE_END_EXCLUSIVE],
        "interval_source": "scan v2 + sensibilidad P-68; manifiesto NO certificado",
        "regime_certified": False,
        "state_boundary": "RESET_AT_CONTRACT_ROLL",
        "reset_method": "ticks recortados antes de barras/footprints/indicador",
        "ticks_per_bar": TICKS_PER_BAR,
        "n_sessions": len(sessions_kept),
        "n_ticks": len(ticks.ts_ns),
        "n_bars": len(bars.close_t),
        "n_blocks": len(blocks),
        "n_zones": len(zones),
        "decision_counts": {d: sum(1 for b in blocks if b["decision"] == d)
                            for d in sorted({b["decision"] for b in blocks})},
    }

    # EF0: integridad + perfil + tarjetas de preguntas (no autoejecutan EF1)
    integrity = validate_trace(summary, blocks, zones, commit, len(blocks), len(zones))
    profile = build_profile(summary, blocks, zones, result.get("params", {}))
    cards = build_question_cards(profile)
    status = {
        "execution_status": "COMPLETE",
        "scientific_status": "EF0_COMPLETE_REGIME_NOT_CERTIFIED",
        "regime_certified": False,
        "outcomes_accessed": False,
        "holdout_accessed": False,
        "auto_execute_ef1": False,
        "code_commit": commit,
        "trace_sha256": canonical_sha256({"summary": summary, "blocks": blocks, "zones": zones}),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    files = {"summary.json": summary, "all_blocks.json": blocks, "zones.json": zones,
             "ef0_integrity.json": integrity, "ef0_profile.json": profile,
             "ef0_question_cards.json": cards, "ef0_status.json": status}
    for name, payload in files.items():
        (OUT / name).write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
                                encoding="utf-8")
    (OUT / "sha256_manifest.json").write_text(json.dumps(
        {n: {"bytes": (OUT / n).stat().st_size, "sha256": sha256(OUT / n)} for n in files},
        indent=2), encoding="utf-8")
    archive = Path("/kaggle/working/avolcluster_operable_ef0.zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(OUT.iterdir()):
            zf.write(p, p.relative_to(OUT.parent))

    raw_cards = cards.get("cards", cards) if isinstance(cards, dict) else cards
    ids = [c.get("question_id") for c in raw_cards if isinstance(c, dict)]
    print(json.dumps({**status, "n_blocks": len(blocks), "n_zones": len(zones),
                      "n_create_candidates": integrity.get("n_create_candidates"),
                      "n_zones_off_price": integrity.get("n_zones_off_price"),
                      "n_at_price_candidates": integrity.get("n_at_price_candidates"),
                      "n_question_cards": len(raw_cards), "question_cards": ids},
                     indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

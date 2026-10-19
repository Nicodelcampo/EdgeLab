#!/usr/bin/env python3
"""Ingesta retroactiva al Hipocampo durable: hipótesis de research ya cerradas o falsadas.

Cada entrada traduce un acta existente del repo (no un recuerdo) a un `Counterexample`
contra el claim que refutó, más una `LessonCandidate` con la regla operativa que deja. El
objetivo es que el cerebro recuerde qué ya murió, con qué alcance y bajo qué condición se
reabre -- para no gastar presupuesto de hipótesis repitiendo búsquedas saturadas.

Reglas:
- Ledger SEPARADO del génesis de CYCLE-001 (cuyo tip hash está pineado): no se toca aquél.
- Todo queda `PROPOSED` / `LOW` / sin evidence_record_ids: techo LESSON_CANDIDATE, sin
  autopromoción (NO_SELF_APPROVAL).
- `outcomes_inspected=False`: este episodio de ingesta NO abre outcomes; sólo registra
  veredictos ya documentados. El alcance de cada muerte se copia del acta, no se amplía
  ("Toda muerte tiene alcance preciso", CLAUDE.md).
- Determinista: timestamps fijos, orden fijo -> mismo tip hash en cada build.

    .venv\\Scripts\\python tools\\build_research_history_ledger.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edgelab.edge_brain.hippocampus import AnalysisEpisode, Counterexample, LessonCandidate  # noqa: E402
from edgelab.edge_brain.hippocampus_store import DurableHippocampus, LedgerIntegrityError  # noqa: E402

LEDGER = ROOT / "artifacts" / "hippocampus" / "research_history_ledger.jsonl"
EPISODE_ID = "EPISODE-RESEARCH-HISTORY-INGEST-001"
TS = "2026-09-22T00:00:00Z"

# (id, claim refutado, contexto/alcance, comportamiento observado, por qué viola, evidencia,
#  lección operativa, condición de reapertura)
ENTRIES = [
    ("BIGTRAP2-SR", "BIGTRAP2-AS-SUPPORT-RESISTANCE",
     "BigTrap2 zones as support/resistance, 6E",
     "~96% of zones are broken, invariant to all 12 indicator parameters",
     "EFFECT_ABSENT: breakage rate does not depend on the parameters that define the zone",
     "doc:CLAUDE.md#estado-vigente",
     "A zone that breaks ~96% of the time regardless of its parameters is not a barrier; do not re-sweep its parameters.",
     "NEW_OBSERVABLE"),
    ("BIGTRAP2-MAGNET", "BIGTRAP2-AS-ZONE-MAGNET",
     "BigTrap2 zone attraction/revisit, 6E, 201 sessions, 15.947 zones (F2.7-F2.10)",
     "race vs mirror real but survives d>=6; zone-free control with same geometry gives ~same effect; "
     "BigTrap2 kernel K0 ~= matched non-creator N0; zone residual +0.026 with MDE 0.034",
     "EFFECT_NOT_ZONE_SPECIFIC: a generic extreme candle explains the asymmetry, not the zone",
     "doc:docs/research/F27_F210_CIERRE_Y_HERRAMIENTAS_2026-08-13.md@cb62c3a3",
     "Always run a zone-free control with identical geometry before attributing an effect to a zone.",
     "NEW_DATASET"),
    ("HFTZONES-ES", "HFTZONES-ES-EDGE",
     "HFTZones on ES, five measurements",
     "no positive measurement; equivalence reached in 1 of 3 volatility terciles; low/high underpowered "
     "(MDE 14.5 and 9.6 vs margin 7.91)",
     "UNDERPOWERED_NULL: SIN EFECTO DETECTADO, NO CERRADA -- limit is sample size, not analysis",
     "doc:docs/research/HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md@47f91168",
     "A null without published MDE does not distinguish absence of effect from lack of power; "
     "more analysis on the same N cannot close it.",
     "NEW_DATASET"),
    ("YM-BT2A", "YM-BT2A-DENSITY-EDGE",
     "YM BT2A density lineage, YM_DISCOVERY_PRE2026, price/bid/ask/volume only",
     "6 campaigns, 26.856 policies adjudicated, 0 survivors",
     "SATURATED_STOP: search space exhausted on current observables",
     "config:config/edge_brain/ym_bt2a_research_saturation_20260921.json@bac8a41",
     "Do not rescue a saturated lineage with new thresholds, narratives, directional reinterpretations "
     "or exit grids on rejected entries.",
     "NEW_DATASET|NEW_OBSERVABLE|NEW_EXECUTION_CONTRACT"),
    ("HP008-UNCONDITIONAL", "HP008-UNCONDITIONAL-REVERSION",
     "HP-008 HFT climax + EMA reversion, NQ 25t, blind entry at t0",
     "blind entry loses -1.62 pt; micro-scalping dies to CME friction (PF 0.75-0.88); only a rotational-day "
     "subset with vacuum corridors survives",
     "NET_NEGATIVE_AFTER_COSTS: unconditional version falsified; conditional subset not yet replicated OOS",
     "doc:docs/research/INFORME_FALSACION_ABSORCION_HFT_EMA_2026-09-17.md@965f54d",
     "A conditional survivor found after the unconditional version failed is a hypothesis, not a result, "
     "until replicated out of sample under preregistration.",
     "PREREGISTERED_OOS_REPLICATION"),
    ("TOUCH-ONLY-POPULATION", "BIGTRAP2-CORPUS-POPULATION-COMPLETE",
     "entire BigTrap2 corpus measured only the touch entry family",
     "a premise inside a conditional became an axiom; zone-as-state framework existed 13 days unused",
     "DESIGN_BIAS: population chosen without enumerating alternatives",
     "doc:docs/SESGO_DE_DISENO_2026-08-10_EL_TOQUE_COMO_UNICA_ENTRADA.md@f3d5c7bd",
     "Enumerate creation/approach/first touch/nth touch/invalidation/expiry/confluence/state before "
     "freezing a population.",
     "NEW_POPULATION_WITH_ENUMERATED_EVENT_SPACE"),
    ("G2-MCPT", "G2-MCPT-MEASURES-EDGE",
     "original G2 MCPT gate",
     "it measured temporal concentration, favouring decaying edges and penalising stable ones",
     "MEASUREMENT_INVALID: the test did not measure what its contract claimed",
     "doc:docs/incidents/AMENDMENT_G2-A1_2026-08-10.md@62ac28cd",
     "Validate what a statistical gate actually measures against its contract before trusting its verdicts.",
     "AMENDED_GATE"),
    # --- 2026-09-23 (agregadas por append; el prefijo anterior queda anclado en ANCHORS.json) ---
    ("L2-DIR-GC", "L2-BOOK-ADDS-DIRECTIONAL-INFO-30-300S",
     "GC 08-26 pre-holdout 2026-05-27..06-30, NT8 MBP-10, ridge M0 (trades) vs M1 (+9 book features), "
     "L in {0,250,500} ms, preregistered at aa080a1",
     "DeltaIC(M1-M0) did not reject in 6 Bonferroni tests; 30 s directional significantly negative "
     "(-0.024); 60 s informative null (CI [-0.014, 0.011], MDE 0.011); identical at L=0",
     "the order book added no information on the mid at 30-300 s beyond trade flow, independent of latency",
     "doc:docs/research/L2_FASE2_RESULTADOS_20260923.md@2d9add9",
     "Book information in GC lives below ~1 s; at retail-reachable horizons it adds nothing over trade flow.",
     "the same preregistration on another instrument or period, or L2 as signal filter (M3) or execution (M4)"),
    ("L2-BOOTSTRAP-OVERLAP", "EXPECTED_BOOTSTRAP_OVERLAP-ROOT-CAUSE",
     "L2 session boundaries, GC 08-26/12-26 reconverted 2026-09-22",
     "the -4..-8 s cross-day overlap disappears once NT8 sub-second fields (100 ns ticks) are divided by 10",
     "a published root cause and its 30 s tolerance were artifacts of a unit bug (sub-second x10)",
     "doc:docs/research/L2_VISOR_RESOLUCION_20260923.md@e3028da",
     "Before explaining an anomaly, compare against an independent conversion of the same raw data.",
     "overlap evidence in data converted with the fixed parser"),
    ("L2-SPOOF-DETECTOR", "SPOOF-HEURISTIC-DETECTS-SPOOFING",
     "GC 08-26 pre-holdout, 29 sessions, trade-time-shift null",
     "real/null = 0.79 [0.73, 0.84], 0/29 sessions above null",
     "the detector measures fleeting large quotes, not spoofing: 79% of flags survive without the trade link",
     "doc:docs/research/L2_FASE0_RESULTADOS_20260923.md@f0dc78e",
     "Name a detector by what its null shows it measures, never by an unobservable intention.",
     "order-level (MBO) data and a null specific to intent"),
]


def _records(path: Path) -> list[bytes]:
    return [ln for ln in path.read_bytes().split(b"\n") if ln.strip()] if path.exists() else []


def build(path: Path = LEDGER) -> str:
    """APPEND-ONLY: genera el ledger completo en un temporal y, si ya existe uno, exige que lo existente sea
    PREFIJO exacto de lo generado; solo agrega lo que falta. Nunca borra ni reescribe historia (antes hacia
    unlink + regeneracion, y el tip anclado se editaba en el mismo commit)."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "gen.jsonl"
        store = DurableHippocampus(tmp)
        store.register_episode(AnalysisEpisode(
            episode_id=EPISODE_ID,
            goal="Retroactively ingest documented closures/falsifications as counterexamples + lesson "
                 "candidates; no outcomes opened, no promotion",
            created_at_utc=TS, updated_at_utc=TS, status="COMPLETED_UNADJUDICATED",
            recorded_by="research-history-ingest", outcomes_inspected=False))
        for key, claim, context, observed, why, evidence, lesson, reopen in ENTRIES:
            store.record_counterexample(Counterexample(
                counterexample_id=f"CX-RH-{key}", target_claim_or_rule_id=claim, context=context,
                observed_behavior=observed, why_it_violates=why, evidence_ref=evidence,
                status="CONFIRMED", recorded_at_utc=TS))
            store.record_lesson(LessonCandidate(
                lesson_id=f"LESSON-RH-{key}", episode_id=EPISODE_ID,
                statement=f"{lesson} Reopen only with: {reopen}.",
                scope="RESEARCH", confidence="LOW", status="PROPOSED",
                evidence_record_ids=[], created_at_utc=TS))
        generated = _records(tmp)
    existing = _records(path)
    if generated[:len(existing)] != existing:
        raise LedgerIntegrityError(f"{path}: existing ledger is not a prefix of the generated one; "
                                   "refusing to rewrite history (append-only)")
    path.parent.mkdir(parents=True, exist_ok=True)
    if len(generated) > len(existing):
        with path.open("ab") as fh:
            fh.write(b"".join(ln + b"\n" for ln in generated[len(existing):]))
    return DurableHippocampus(path).verify()


if __name__ == "__main__":
    print(build())

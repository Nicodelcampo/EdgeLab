"""Propuestas 2-6 (2026-09-23): append-only entre commits, cascada de invalidacion, campanas con presupuesto
(STOP ejecutable + contabilidad de pruebas) y registro automatico de episodios."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edgelab.edge_brain.episode_logger import measurement_episode  # noqa: E402
from edgelab.edge_brain.hippocampus_store import (CampaignBudgetError, DurableHippocampus,  # noqa: E402
                                                  LedgerIntegrityError, verify_anchors)
from tools import build_research_history_ledger as B  # noqa: E402

HIPPO = ROOT / "artifacts" / "hippocampus"
ANCHORS = json.loads((HIPPO / "ANCHORS.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("ledger", [k for k in ANCHORS if not k.startswith("_")])
def test_every_historical_anchor_still_holds(ledger):
    verify_anchors(HIPPO / ledger, ANCHORS[ledger])


def test_rewritten_history_breaks_the_anchor(tmp_path):
    p = tmp_path / "l.jsonl"
    B.build(p)
    anchors = ANCHORS["research_history_ledger.jsonl"]
    verify_anchors(p, anchors)
    p.write_bytes(b"".join(ln + b"\n" for ln in p.read_bytes().split(b"\n")[:10] if ln))   # trunca
    with pytest.raises(LedgerIntegrityError, match="no longer holds"):
        verify_anchors(p, anchors)


def test_builder_appends_only_and_refuses_to_rewrite(tmp_path):
    p = tmp_path / "l.jsonl"
    tip = B.build(p)
    assert B.build(p) == tip                         # idempotente: no reescribe
    lines = p.read_bytes().split(b"\n")
    other = tmp_path / "x.jsonl"
    DurableHippocampus(other).record_invalidation("ART-X", "STALE_BY_DEPENDENCY")
    p.write_bytes(other.read_bytes())                # historia distinta
    with pytest.raises(LedgerIntegrityError, match="not a prefix"):
        B.build(p)
    assert lines


def test_cascade_invalidation_today_case(tmp_path):
    """Caso real 2026-09-23: el bug x10 invalido parquets, y con ellos una causa raiz publicada y su tolerancia."""
    s = DurableHippocampus(tmp_path / "l.jsonl")
    s.record_dependency("CLAIM:EXPECTED_BOOTSTRAP_OVERLAP", "DATA:l2_parquet_GC_12-26@x10", "MEASURED_BY")
    s.record_dependency("CODE:validator_overlap_tolerance", "CLAIM:EXPECTED_BOOTSTRAP_OVERLAP", "DEPENDS_ON")
    s.record_dependency("DOC:fase0_costs", "DATA:l2_parquet_GC_12-26@x10", "SUPPORTED_BY")
    st = s.invalidate_with_cascade("DATA:l2_parquet_GC_12-26@x10")
    assert st["DATA:l2_parquet_GC_12-26@x10"] == "INVALIDATED_BY_MEASUREMENT_ERROR"
    assert st["CLAIM:EXPECTED_BOOTSTRAP_OVERLAP"] == "STALE_BY_DEPENDENCY"
    assert st["CODE:validator_overlap_tolerance"] == "STALE_BY_DEPENDENCY"
    assert st["DOC:fase0_costs"] == "REQUIRES_REAUDIT"
    r = DurableHippocampus(tmp_path / "l.jsonl")          # persiste tras reabrir
    assert r.invalidations["CODE:validator_overlap_tolerance"] == "STALE_BY_DEPENDENCY"
    with pytest.raises(Exception):
        r.reuse_artifact("CLAIM:EXPECTED_BOOTSTRAP_OVERLAP")


def test_campaign_budget_is_the_executable_stop_rule(tmp_path):
    s = DurableHippocampus(tmp_path / "l.jsonl")
    with pytest.raises(CampaignBudgetError, match="no approved campaign"):
        s.record_trial("C-1", "T-1", "h", "v", "ic", "0.01")
    with pytest.raises(ValueError, match="human"):
        s.record_campaign("C-1", "L2", "agent:claude", "agent:claude", 2, "prereg@x", "GC pre-holdout")
    with pytest.raises(CampaignBudgetError, match="spec confirmed"):
        s.record_campaign("C-1", "L2", "human:Nico", "agent:claude", 2, "prereg@aa080a1", "GC 08-26 pre-holdout")
    s.record_spec_confirmation("SPEC-1", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "human:Nico", "agent:claude")
    s.record_campaign("C-1", "L2", "human:Nico", "agent:claude", 2, "prereg@aa080a1", "GC 08-26 pre-holdout", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    s.record_trial("C-1", "T-1", "h1", "30s", "dIC", "-0.024")
    s.record_trial("C-1", "T-2", "h1", "60s", "dIC", "-0.003")
    with pytest.raises(CampaignBudgetError, match="exhausted"):
        s.record_trial("C-1", "T-3", "h1", "300s", "dIC", "?")
    assert s.trials_by_family() == {"L2": 2}
    assert DurableHippocampus(tmp_path / "l.jsonl").trials_by_family() == {"L2": 2}


def test_forged_trial_over_budget_is_rejected_on_replay(tmp_path):
    from edgelab.edge_brain import hippocampus_store as m
    p = tmp_path / "l.jsonl"
    s = DurableHippocampus(p)
    s.record_spec_confirmation("SPEC-1", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "human:Nico", "agent:claude")
    s.record_campaign("C-1", "L2", "human:Nico", "agent:claude", 1, "prereg@x", "scope", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    s.record_trial("C-1", "T-1", "h", "v", "m", "r")
    row = dict(campaign_id="C-1", trial_id="T-2", hypothesis="h", variant="v", metric="m", result="r")
    rec = {"schema": m.LEDGER_SCHEMA, "type": "trial_recorded", "prev_hash": s.tip_hash, "payload": row}
    rec["hash"] = m._record_hash("trial_recorded", row, s.tip_hash)
    with p.open("ab") as fh:
        fh.write((json.dumps(rec, sort_keys=True) + "\n").encode())
    with pytest.raises(LedgerIntegrityError, match="outside an approved budget"):
        DurableHippocampus(p)


def test_measurement_episode_logs_success_and_failure(tmp_path):
    led = tmp_path / "l.jsonl"
    inp = tmp_path / "in.txt"; inp.write_text("x", encoding="utf-8")
    with measurement_episode(led, "EP-1", goal="g", recorded_by="tools/x.py", inputs={"in": inp},
                             prereg_ref="p@1", repo=ROOT) as ep:
        ep.note("result", "null")
    with pytest.raises(RuntimeError):
        with measurement_episode(led, "EP-2", goal="g", recorded_by="tools/x.py", repo=ROOT):
            raise RuntimeError("boom")
    s = DurableHippocampus(led)
    e1, e2 = s.memory.reconstruct_episode("EP-1"), s.memory.reconstruct_episode("EP-2")
    assert e1["successes"] and not e1["failures"]
    assert e2["failures"] and not e2["successes"]


def test_spec_confirmation_must_be_human_and_full_hash(tmp_path):
    s = DurableHippocampus(tmp_path / "l.jsonl")
    with pytest.raises(ValueError, match="human"):
        s.record_spec_confirmation("SPEC-1", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "agent:claude", "agent:claude")
    with pytest.raises(ValueError, match="sha256"):
        s.record_spec_confirmation("SPEC-1", "27a450b05bd9", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "human:Nico", "agent:claude")
    s.record_spec_confirmation("SPEC-1", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "human:Nico", "agent:claude")
    assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in DurableHippocampus(tmp_path / "l.jsonl").specs


def test_legacy_campaign_without_spec_still_replays():
    """Las 5 campanas del 2026-09-23 (anteriores a la regla) siguen reproduciendose."""
    s = DurableHippocampus(HIPPO / "campaign_ticks_multi_20260923.jsonl")
    assert len(s.campaigns) == 5 and len(s.trials) == 100


def test_atlas_exploration_cannot_be_confirmed_on_the_same_data(tmp_path):
    s = DurableHippocampus(tmp_path / "l.jsonl")
    s.record_partition("P-EXP", "EXPLORATION", "primeras 15", ["d1", "d2"])
    s.record_partition("P-CONF", "CONFIRMATION_RESERVED", "ultimas 15", ["d3", "d4"])
    with pytest.raises(ValueError, match="overlaps"):
        s.record_partition("P-X", "FUTURE", "pisa", ["d2", "d9"])
    with pytest.raises(ValueError, match="EXPLORATION"):          # mirar retornos en la reserva: prohibido
        s.record_observation("O-0", "abs", "RESPONSE_PROFILE", ["P-CONF"], {}, {}, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    s.record_observation("O-1", "abs", "RESPONSE_PROFILE", ["P-EXP"], {"x": 1}, {"ci_half_width": 0.2}, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                         depends_on=["CODE:AbsorptionTracker@causal"])
    s.record_spec_confirmation("SPEC-1", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "human:Nico", "agent:claude")
    with pytest.raises(CampaignBudgetError, match="EXPLORATION"):
        s.record_campaign("C-1", "ABS", "human:Nico", "agent:claude", 4, "p@1", "GC", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", ("O-1",), "P-EXP")
    s.record_campaign("C-1", "ABS", "human:Nico", "agent:claude", 4, "p@1", "GC", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", ("O-1",), "P-CONF")
    st = s.invalidate_with_cascade("CODE:AbsorptionTracker@causal")                  # el detector cambia -> STALE
    assert st["OBS:O-1"] == "STALE_BY_DEPENDENCY"
    r = DurableHippocampus(tmp_path / "l.jsonl")
    assert set(r.partitions) == {"P-EXP", "P-CONF"} and r.observations["O-1"]["status"] == "DESCRIPTIVE"


def test_observation_can_never_carry_a_verdict(tmp_path):
    from edgelab.edge_brain import hippocampus_store as m
    p = tmp_path / "l.jsonl"
    s = DurableHippocampus(p)
    s.record_partition("P-EXP", "EXPLORATION", "x", ["d1"])
    row = dict(observation_id="O-9", phenomenon="abs", kind="TARGET_FREE", partitions=["P-EXP"], metrics={},
               resolution={}, artifact_sha256="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", status="PROMOTED")
    rec = {"schema": m.LEDGER_SCHEMA, "type": "observation_recorded", "prev_hash": s.tip_hash, "payload": row}
    rec["hash"] = m._record_hash("observation_recorded", row, s.tip_hash)
    with p.open("ab") as fh:
        fh.write((json.dumps(rec, sort_keys=True) + "\n").encode())
    with pytest.raises(LedgerIntegrityError, match="DESCRIPTIVE"):
        DurableHippocampus(p)

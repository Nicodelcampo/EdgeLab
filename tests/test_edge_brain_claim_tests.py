"""Cierre del ciclo literatura -> Kaggle -> hipocampo: contrastes de hallazgos SSRN, adjudicacion humana, cascada."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from edgelab.edge_brain.hippocampus import AnalysisEpisode, SuccessEvent
from edgelab.edge_brain.hippocampus_store import CampaignBudgetError, DurableHippocampus, LedgerIntegrityError
from edgelab.edge_brain.literature_planner import assess

CLAIM, SRC = "CLAIM-SSRN-FINDING-0439", "SRC-SSRN-0174"
EXE = dict(code_commit="a" * 40, output_sha256="b" * 64, kaggle_dataset="nicolasbuttaro/edgelab-data-catalog",
           kaggle_kernel="nicolasbuttaro/edgelab-litcheck-ssrn-20261009")


class TestClaimTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "brain.jsonl"
        self.store = DurableHippocampus(self.path)
        self.store.register_episode(AnalysisEpisode(episode_id="EP-K", goal="contrastar 0439", created_at_utc="t"))
        self.store.record_success(SuccessEvent(success_id="OK-K", episode_id="EP-K", step_id="S1",
                                               description="corrida Kaggle completa"))
        self.store.record_partition("PART-EXP", "EXPLORATION", "ES pre-holdout", ["ES:20260105", "ES:20260106"])
        self.store.record_partition("PART-RES", "CONFIRMATION_RESERVED", "ES reservado", ["ES:20260107"])
        self.store.record_observation("OBS-1", "volumen en marcas horarias", "TARGET_FREE", ["PART-EXP"],
                                      metrics={"excess_hour": 0.12}, resolution={"bin_s": 30}, artifact_sha256="c" * 64,
                                      design="NO_CONTROL")

    def tearDown(self):
        self._tmp.cleanup()

    def row(self, **kw):
        r = dict(test_id="CT-1", claim_id=CLAIM, source_id=SRC, verdict="CONSISTENT_EXPLORATORY", platform="KAGGLE",
                 holdout_touched=False, episode_id="EP-K", observation_ids=["OBS-1"], execution=dict(EXE),
                 recorded_by="agent:notion-ai", rationale="exceso de volumen en :00 y :30")
        r.update(kw)
        return r

    def test_exploratory_test_enters_proposed_and_waits_for_human(self):
        self.store.record_claim_test(self.row())
        self.assertEqual(self.store.claim_tests["CT-1"]["status"], "PROPOSED")
        self.assertEqual(self.store.claim_status(CLAIM), "TESTED_PENDING_ADJUDICATION")
        with self.assertRaises(ValueError):                     # el agente no se auto-adjudica
            self.store.adjudicate_claim_test("CT-1", "ACCEPTED", "agent:notion-ai", "agent:notion-ai")
        with self.assertRaises(ValueError):                     # humano, pero el mismo que registro
            self.store.adjudicate_claim_test("CT-1", "ACCEPTED", "human:nico", "human:nico")
        self.store.adjudicate_claim_test("CT-1", "ACCEPTED", "human:nico", "agent:notion-ai")
        self.assertEqual(self.store.claim_status(CLAIM), "CONSISTENT_EXPLORATORY_IN_EDGELAB")
        reopened = DurableHippocampus(self.path)                 # el replay reconstruye todo
        self.assertEqual(reopened.claim_status(CLAIM), "CONSISTENT_EXPLORATORY_IN_EDGELAB")

    def test_fail_closed_rules(self):
        bad = [dict(status="ACCEPTED"), dict(holdout_touched=True), dict(platform="LOCAL"),
               dict(observation_ids=[]), dict(observation_ids=["OBS-404"]), dict(episode_id="EP-404"),
               dict(execution=dict(EXE, code_commit="abc")), dict(execution=dict(EXE, output_sha256="")),
               dict(claim_id="CLAIM-X"), dict(verdict="PROMOTED")]
        for i, kw in enumerate(bad):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                self.store.record_claim_test(self.row(test_id=f"CT-B{i}", **kw))
        # REPRODUCED/REFUTED exigen trials de una campana aprobada: una observacion exploratoria no alcanza
        with self.assertRaises(ValueError):
            self.store.record_claim_test(self.row(test_id="CT-R", verdict="REPRODUCED"))

    def test_exploratory_cannot_use_reserved_partition(self):
        self.store.record_observation("OBS-R", "x", "TARGET_FREE", ["PART-RES"], metrics={}, resolution={},
                                      artifact_sha256="d" * 64, design="NO_CONTROL")
        with self.assertRaises(ValueError):
            self.store.record_claim_test(self.row(observation_ids=["OBS-R"]))

    def test_confirmatory_refuted_cascades_to_citing_artifacts(self):
        self.store.record_spec_confirmation("SPEC-1", "e" * 64, "f" * 64, "human:nico", "agent:notion-ai")
        with self.assertRaises(CampaignBudgetError):
            self.store.record_campaign("CAMP-1", "LITCHECK", "human:nico", "agent:notion-ai", 1, "prereg.md",
                                       "ES", spec_sha256="0" * 64)
        self.store.record_campaign("CAMP-1", "LITCHECK", "human:nico", "agent:notion-ai", 1, "prereg.md", "ES",
                                   spec_sha256="e" * 64)
        self.store.record_trial("CAMP-1", "TR-1", "H1", "base", "excess", "-0.01")
        with self.assertRaises(CampaignBudgetError):            # presupuesto agotado
            self.store.record_trial("CAMP-1", "TR-2", "H1", "alt", "excess", "0.2")
        self.store.record_dependency("HYP-USES-0439", CLAIM, "SUPPORTED_BY")
        self.store.record_claim_test(self.row(test_id="CT-C", verdict="REFUTED", trial_ids=["TR-1"], observation_ids=[]))
        self.store.adjudicate_claim_test("CT-C", "ACCEPTED", "human:nico", "agent:notion-ai")
        self.assertEqual(self.store.claim_status(CLAIM), "REFUTED_IN_EDGELAB")
        self.assertEqual(self.store.invalidations.get("HYP-USES-0439"), "REQUIRES_REAUDIT")
        # un contraste exploratorio posterior no pisa al confirmatorio
        self.store.record_claim_test(self.row(test_id="CT-E2"))
        self.store.adjudicate_claim_test("CT-E2", "ACCEPTED", "human:nico", "agent:notion-ai")
        self.assertEqual(self.store.claim_status(CLAIM), "REFUTED_IN_EDGELAB")

    def test_tampered_claim_test_breaks_replay(self):
        self.store.record_claim_test(self.row())
        lines = self.path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            rec = json.loads(line)
            if rec["type"] == "literature_claim_tested":
                rec["payload"]["holdout_touched"] = True
                lines[i] = json.dumps(rec)
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaises(LedgerIntegrityError):
            DurableHippocampus(self.path)


class TestPlannerHeuristics(unittest.TestCase):
    def test_blockers_and_transfer(self):
        a = assess("afirmacion: el volumen sube al acercarse a horas en punto | mercado: US equities | magnitud: 15.7%")
        self.assertEqual(a["blockers"], [])
        self.assertTrue(a["measurable"] and a["quantitative"])
        b = assess("afirmacion: la profundidad del libro en varios niveles predice | mercado: E-mini S&P 500 futures")
        self.assertIn("L2_DEPTH", b["blockers"])
        self.assertEqual(b["transfer"], 1.0)
        c = assess("afirmacion: el modelo LSTM alcanza 81% de acierto | mercado: Bitcoin")
        self.assertTrue(c["model_specific"])
        self.assertEqual(c["transfer"], 0.35)


if __name__ == "__main__":
    unittest.main()

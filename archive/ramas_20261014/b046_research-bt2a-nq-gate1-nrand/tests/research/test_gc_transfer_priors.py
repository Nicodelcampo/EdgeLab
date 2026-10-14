"""Tests for the GC transfer prior derivation. Target-free w.r.t. NQ."""
import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TOOL = os.path.join(ROOT, "tools", "derive_gc_transfer_priors.py")
RESEARCH = os.path.join(ROOT, "docs", "research")

spec = importlib.util.spec_from_file_location("dgtp", TOOL)
dgtp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dgtp)


class TestGcTransferPriors(unittest.TestCase):
    def test_reconstruction_matches_published_contrast(self):
        m = dgtp.derive(RESEARCH)
        self.assertTrue(m["reconstruction_matches_published_contrast"])
        self.assertEqual(m["n_sessions"], m["published_contrast"]["n_sessions"])

    def test_sd_is_positive_and_below_popoviciu_session_bound(self):
        m = dgtp.derive(RESEARCH)
        sd = m["sd_paired_session_contrast_ticks"]
        self.assertGreater(sd, 0.0)
        # A session mean cannot be as disperse as the single-event bound.
        self.assertLess(sd, 60.0)

    def test_all_source_files_are_hash_bound(self):
        m = dgtp.derive(RESEARCH)
        self.assertGreaterEqual(len(m["source_files_sha256"]), 6)
        for name, digest in m["source_files_sha256"].items():
            self.assertEqual(len(digest), 64, name)

    def test_power_is_monotone_in_alpha(self):
        table = dgtp.power_table(11.5, 234, 1.0)
        bonf = [r for r in table if r["alpha"] < 0.05][0]
        single = [r for r in table if r["alpha"] == 0.05][0]
        self.assertGreater(bonf["required_sessions_at_mde"],
                           single["required_sessions_at_mde"])
        self.assertGreater(bonf["mde_resolvable_at_available"],
                           single["mde_resolvable_at_available"])

    def test_firewall_rejects_nq_outcome_shaped_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "BT2A_NQ_GATE1_MFE_MAE_RESULT.json"), "w").close()
            with self.assertRaises(SystemExit):
                dgtp.assert_nq_firewall(d)

    def test_emitted_payload_is_self_consistent(self):
        m = dgtp.derive(RESEARCH)
        payload = {"a": 1, "measured": m}
        digest = dgtp.canonical_sha256(payload)
        self.assertEqual(digest, dgtp.canonical_sha256(payload))
        self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    unittest.main()

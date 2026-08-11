from __future__ import annotations
import hashlib
import unittest
from pathlib import Path
from tools.prepare_nt8_candidate import MARKER, load_artifact, prepare_source
REPO = Path(__file__).resolve().parents[2]
ARTIFACT = REPO / "incoming/nt8/aVolClusterPOI/v0.4/aVolClusterPOI.raw.manifest.json"
RAW_SHA = "3420519de9b4a1456f812040b62af419b0c323486281424a84aaaab126100c98"
PREPARED_SHA = "33028abd28b706191b5a455e47989252e0ff33035fa75bc23e1dc0f6ec94ec1c"

class PrepareTests(unittest.TestCase):
    def test_raw_hash(self):
        self.assertEqual(hashlib.sha256(load_artifact(ARTIFACT, gzip_base64=True)).hexdigest(), RAW_SHA)
    def test_candidate_is_deterministic(self):
        raw = load_artifact(ARTIFACT, gzip_base64=True)
        result = prepare_source(raw, expected_sha256=RAW_SHA, class_name="aVolClusterPOI")
        self.assertEqual(hashlib.sha256(result).hexdigest(), PREPARED_SHA)
    def test_crlf_and_generated_tail(self):
        raw = load_artifact(ARTIFACT, gzip_base64=True)
        data = prepare_source(raw, expected_sha256=RAW_SHA, class_name="aVolClusterPOI")
        self.assertEqual(data.count(b"\n") - data.count(b"\r\n"), 0)
        text = data.decode("utf-8")
        self.assertNotIn(MARKER, text)
        self.assertEqual(text.count("class aVolClusterPOI : Indicator"), 1)
    def test_wrong_hash_fails(self):
        with self.assertRaises(ValueError):
            prepare_source(load_artifact(ARTIFACT, gzip_base64=True), expected_sha256="0"*64, class_name="aVolClusterPOI")
if __name__ == "__main__":
    unittest.main()

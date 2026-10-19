import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("catalog", ROOT / "tools/edgelab_catalog.py")
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "config/component_registry.json").read_text())
    def test_registry(self):
        self.assertEqual(catalog.validate(self.data, ROOT), [])
    def test_duplicate(self):
        self.data["modules"].append(copy.deepcopy(self.data["modules"][0]))
        self.assertTrue(catalog.validate(self.data, ROOT))
    def test_missing_local(self):
        self.data["modules"][0]["paths"] = ["not-present/navigation"]
        self.assertTrue(catalog.validate(self.data, ROOT))
    def test_remote_paths_not_required_locally(self):
        m = self.data["modules"][0]; m["location"] = "other_branch"; m["paths"] = ["not-present/navigation"]
        self.assertEqual(catalog.validate(self.data, ROOT), [])
    def test_escape(self):
        for path in ("../../outside", "/outside"):
            self.data["modules"][0]["paths"] = [path]
            self.assertTrue(catalog.validate(self.data, ROOT))
    def test_bad_category(self):
        self.data["modules"][0]["category"] = "CERTIFIED_EDGE"
        self.assertTrue(catalog.validate(self.data, ROOT))
    def test_unknown_module_fails(self):
        p = subprocess.run([sys.executable, str(ROOT / "tools/edgelab_catalog.py"), "show", "missing"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
    def test_check_outside_repo(self):
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run([sys.executable, str(ROOT / "tools/edgelab_catalog.py"), "check", "--json"], cwd=d, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout)
        result = json.loads(p.stdout)
        self.assertFalse(result["research_authorized"])
        self.assertFalse(result["data_read"])
        self.assertFalse(result["runtime_tested"])
    def test_markdown_ids_match_registry(self):
        text = (ROOT / "docs/COMPONENTS.md").read_text()
        for m in self.data["modules"]:
            self.assertIn("| `" + m["id"] + "` |", text)
    def test_bad_fields(self):
        self.data["modules"][0]["inputs"] = "ticks"
        self.assertTrue(catalog.validate(self.data, ROOT))
    def test_missing_required(self):
        del self.data["modules"][0]["limitations"]
        self.assertTrue(catalog.validate(self.data, ROOT))

if __name__ == "__main__":
    unittest.main()

"""CYCLE-001 Agent D independent causal smoke for PR #48.

Synthetic pre-holdout only. No outcomes, validation, or holdout access.
Run directly: python tests/qa/test_cycle001_viewer_causal_smoke.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from edgelab.bridge import viewer_export as ve

INDEX = ROOT / "viewer" / "nt8_bridge" / "index.html"


class Cycle001ViewerCausalSmoke(unittest.TestCase):
    def test_tick_legacy_abstains_instead_of_inheriting_display_timeframe(self):
        zone = {
            "top": 10.0,
            "bottom": 9.0,
            "kind": "BULL",
            "created_ms": 1_780_000_003_000,
        }
        out = ve._zone_json(
            zone,
            "python",
            1_780_000_100_000,
            None,
            display_bar_key="time_5m",
            formation_spec=None,
        )
        self.assertEqual(out["available_origin"], "UNAVAILABLE")
        self.assertIsNone(out["available_ts"])
        self.assertIsNone(out["formation_spec"])
        self.assertEqual(out["display_bar_key"], "time_5m")

    def test_renderer_has_one_strict_duration_helper_and_no_300_second_default(self):
        html = INDEX.read_text(encoding="utf-8")
        self.assertEqual(html.count("function parseBarDurationSec("), 1)
        self.assertNotIn("var barDurationSec", html)
        self.assertNotRegex(html, r"(?:duration|Duration)[^\n=]*=\s*300\b")
        self.assertGreaterEqual(html.count("parseBarDurationSec(bspec)"), 2)

    def test_duration_helper_executes_in_real_chromium(self):
        node = shutil.which("node")
        chromium = shutil.which("chromium") or shutil.which("chromium-browser")
        if not node or not chromium:
            self.skipTest("optional Node/Chromium browser smoke dependencies unavailable")
        has_playwright = subprocess.run(
            [node, "-e", "require.resolve('playwright')"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
        if not has_playwright:
            self.skipTest("optional Node Playwright dependency unavailable")
        html = INDEX.read_text(encoding="utf-8")
        match = re.search(
            r"function parseBarDurationSec\(barKey\) \{.*?\n  \}",
            html,
            flags=re.S,
        )
        self.assertIsNotNone(match)
        helper = match.group(0)
        script = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const browser = await chromium.launch({{headless:true, executablePath:{json.dumps(chromium)}, args:['--no-sandbox']}});
  const page = await browser.newPage();
  await page.setContent(`<script>${{{helper!r}}}</script>`);
  const got = await page.evaluate(() => [
    parseBarDurationSec('time_5m'),
    parseBarDurationSec('time_1h'),
    parseBarDurationSec('tick_25'),
    parseBarDurationSec('time_5'),
    parseBarDurationSec('time_0m')
  ]);
  await browser.close();
  if (JSON.stringify(got) !== JSON.stringify([300,3600,null,null,null])) {{
    throw new Error('unexpected duration contract: ' + JSON.stringify(got));
  }}
}})().catch(e => {{ console.error(e); process.exit(1); }});
"""
        subprocess.run([node, "-e", script], cwd=ROOT, check=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)

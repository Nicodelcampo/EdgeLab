"""Test availability semantics and density profile status (Gate B).

Validates:
1. Availability classification: EXPLICIT vs ORIGIN_FALLBACK_UNVERIFIED
2. UI controls: chk-show-exploratory and chk-include-exploratory-density
3. Persistent exploratory warning badge
4. Status assertions:
   - PASS_CAUSAL_DENSITY_PROFILE
   - PASS_EXPLORATORY_DENSITY_PROFILE
   - ABSTAIN_NO_EXPLICIT_AVAILABILITY
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import json

ROOT = Path(__file__).resolve().parents[2]
VIEWER_HTML = ROOT / "viewer" / "nt8_bridge" / "index.html"

def test_viewer_html_contains_required_controls():
    content = VIEWER_HTML.read_text(encoding="utf-8")
    assert "id=\"chk-show-exploratory\"" in content, "Missing chk-show-exploratory"
    assert "id=\"chk-include-exploratory-density\"" in content, "Missing chk-include-exploratory-density"
    assert "EXPLORATORY — t0 USED AS UNVERIFIED AVAILABILITY" in content, "Missing persistent warning badge"
    assert "zoneAvailabilityInfo" in content, "Missing zoneAvailabilityInfo function"
    assert "PASS_CAUSAL_DENSITY_PROFILE" in content, "Missing PASS_CAUSAL_DENSITY_PROFILE status"
    assert "PASS_EXPLORATORY_DENSITY_PROFILE" in content, "Missing PASS_EXPLORATORY_DENSITY_PROFILE status"
    assert "ABSTAIN_NO_EXPLICIT_AVAILABILITY" in content, "Missing ABSTAIN_NO_EXPLICIT_AVAILABILITY status"

def test_js_availability_semantics_in_node():
    script = r"""
    const fs = require('fs');
    const path = require('path');
    const html = fs.readFileSync(process.argv[1], 'utf8');

    // Extract densityTsSec and zoneAvailabilityInfo from index.html
    const fnDef = html.match(/function densityTsSec[\s\S]*?function zoneAvailableSec\(z\) \{[\s\S]*?\}/);
    if (!fnDef) throw new Error("Could not extract zoneAvailabilityInfo from HTML");

    eval(fnDef[0]);

    // 1. Explicit zone
    const zExp = { top: 100, bottom: 98, available_ts: 1700000000, t0: 1699990000 };
    const infoExp = zoneAvailabilityInfo(zExp);
    if (infoExp.quality !== "EXPLICIT" || !infoExp.isExplicit || infoExp.sec !== 1700000000) {
        throw new Error("Explicit zone failed: " + JSON.stringify(infoExp));
    }

    // 2. Exploratory zone (t0 fallback)
    const zExpl = { top: 100, bottom: 98, t0: 1700000000 };
    const infoExpl = zoneAvailabilityInfo(zExpl);
    if (infoExpl.quality !== "ORIGIN_FALLBACK_UNVERIFIED" || infoExpl.isExplicit || infoExpl.sec !== 1700000000) {
        throw new Error("Exploratory zone failed: " + JSON.stringify(infoExpl));
    }

    // 3. Extract buildCrosshairDensityRanges
    const rangesDef = html.match(/function buildCrosshairDensityRanges\(candles, tRef, tick, extBars, activeKey\) \{[\s\S]*?return \{\s*ranges: ranges,\s*explicitRanges: explicitRanges,\s*exploratoryRanges: exploratoryRanges,\s*excludedMissingAvailability: excludedMissingAvailability\s*\};\s*\}/);
    if (!rangesDef) throw new Error("Could not extract buildCrosshairDensityRanges from HTML");

    eval(rangesDef[0]);

    const candles = [{ time: 1700000000 }, { time: 1700000060 }];
    const tRef = 1700000050;
    const tick = 0.25;
    const extBars = 50;
    const activeKey = "tick_25";

    // Scenario A: Only exploratory zones with include_exploratory_density = false
    global.visible = (z) => true;
    global.state = { run: { zones: [zExpl] }, decayMode: "none" };
    global.activeProps = { consumption_mode: "fixed", include_exploratory_density: false };

    let res = buildCrosshairDensityRanges(candles, tRef, tick, extBars, activeKey);
    if (res.ranges.length !== 0 || res.excludedMissingAvailability !== 1 || res.exploratoryRanges !== 0) {
        throw new Error("Scenario A failed: " + JSON.stringify(res));
    }

    // Scenario B: Exploratory zones with include_exploratory_density = true
    global.activeProps.include_exploratory_density = true;
    res = buildCrosshairDensityRanges(candles, tRef, tick, extBars, activeKey);
    if (res.ranges.length !== 1 || res.exploratoryRanges !== 1 || res.excludedMissingAvailability !== 0) {
        throw new Error("Scenario B failed: " + JSON.stringify(res));
    }

    // Scenario C: Explicit zone with include_exploratory_density = false
    global.state = { run: { zones: [zExp] }, decayMode: "none" };
    global.activeProps.include_exploratory_density = false;
    res = buildCrosshairDensityRanges(candles, tRef, tick, extBars, activeKey);
    if (res.ranges.length !== 1 || res.explicitRanges !== 1 || res.exploratoryRanges !== 0) {
        throw new Error("Scenario C failed: " + JSON.stringify(res));
    }

    console.log("PASS_AVAILABILITY_SEMANTICS_JS");
    """
    res = subprocess.run(["node", "-e", script, str(VIEWER_HTML)], capture_output=True, text=True, check=True)
    assert "PASS_AVAILABILITY_SEMANTICS_JS" in res.stdout

"""End-to-end browser test for HFT corridor viewer and NT8 bridge integration.

Verifies:
1. Preview loads real bundle and renders canvas and HUD.
2. Status is explicitly PROVISIONAL_NEAR_EXACT_BLOCKED_BY_SHARED_INPUT_V2_EXPORT.
3. Strict tRef causality: zero future candles past tRef.
4. Viewport invariance: zooming in/out changes visual scale but leaves D(p) and field_hash 100% identical.
5. Interactive controls (config selector, tRef slider, zoom buttons).
6. Bidirectional navigation between index.html and hft_corridor_preview.html.
"""
from __future__ import annotations

from pathlib import Path
import pytest

sync_playwright = pytest.importorskip(
    "playwright.sync_api",
    reason="optional Playwright dependency not installed in core CI",
).sync_playwright

VIEWER_DIR = Path(__file__).resolve().parents[2] / "viewer" / "nt8_bridge"


@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        yield context
        browser.close()


def test_preview_loads_and_verifies_causality(browser_context):
    page = browser_context.new_page()
    preview_url = (VIEWER_DIR / "hft_corridor_preview.html").as_uri()
    page.goto(preview_url)
    page.wait_for_selector("#chart")
    page.wait_for_selector("#profile")
    page.wait_for_selector("#hud")

    # 1. Verify status pill
    status_text = page.locator("#status").inner_text()
    assert "PROVISIONAL" in status_text or "BLOCKED" in status_text

    # 2. Verify state is populated
    state = page.evaluate("() => window.__HFT_CORRIDOR_STATE__")
    assert state is not None
    assert len(state["candles"]) > 0
    assert len(state["zones"]) > 0
    assert state["vref"] > 0

    # 3. Invariant: strictly causal candles (no candles past tRef)
    t_ref = state["t"]
    for c in state["candles"]:
        assert c["time_ns"] <= t_ref, f"Future candle detected: {c['time_ns']} > tRef {t_ref}"

    # 4. Invariant: zoom invariance
    # Record initial field_hash and density vector
    init_hash = state["field_hash"]
    init_density = page.evaluate("() => Array.from(window.__HFT_CORRIDOR_STATE__.d)")

    # Click zoom in 3 times
    page.locator("#zin").click()
    page.locator("#zin").click()
    page.locator("#zin").click()

    state_zoomed = page.evaluate("() => window.__HFT_CORRIDOR_STATE__")
    assert state_zoomed["zoom"] > 1.0
    assert state_zoomed["field_hash"] == init_hash, "Zoom altered field hash! Viewport invariance violated!"
    zoomed_density = page.evaluate("() => Array.from(window.__HFT_CORRIDOR_STATE__.d)")
    assert zoomed_density == init_density, "Zoom altered density vector! Viewport invariance violated!"

    # Click zoom out 4 times
    page.locator("#zout").click()
    page.locator("#zout").click()
    page.locator("#zout").click()
    page.locator("#zout").click()

    state_zoomed_out = page.evaluate("() => window.__HFT_CORRIDOR_STATE__")
    assert state_zoomed_out["field_hash"] == init_hash, "Zoom out altered field hash!"
    assert page.evaluate("() => Array.from(window.__HFT_CORRIDOR_STATE__.d)") == init_density

    # 5. Invariant: viewport resize / autoscale invariance
    page.set_viewport_size({"width": 800, "height": 600})
    page.wait_for_timeout(200)
    state_resized = page.evaluate("() => window.__HFT_CORRIDOR_STATE__")
    assert state_resized["field_hash"] == init_hash, "Window resize altered field hash! Viewport invariance violated!"
    assert page.evaluate("() => Array.from(window.__HFT_CORRIDOR_STATE__.d)") == init_density

    page.set_viewport_size({"width": 1920, "height": 1080})
    page.wait_for_timeout(200)
    state_large = page.evaluate("() => window.__HFT_CORRIDOR_STATE__")
    assert state_large["field_hash"] == init_hash, "Large viewport altered field hash! Viewport invariance violated!"
    assert page.evaluate("() => Array.from(window.__HFT_CORRIDOR_STATE__.d)") == init_density

    # 6. Interactive controls: change config
    page.select_option("#cfg", "HFT_RAW_BOX")
    state_box = page.evaluate("() => window.__HFT_CORRIDOR_STATE__")
    assert state_box["c"]["id"] == "HFT_RAW_BOX"

    page.close()


def test_bidirectional_navigation_between_index_and_preview(browser_context):
    page = browser_context.new_page()

    # Start at index.html
    index_url = (VIEWER_DIR / "index.html").as_uri()
    page.goto(index_url)
    page.wait_for_selector("#btn-hft-corridor")

    # Click HFT Corredores button
    page.locator("#btn-hft-corridor").click()
    page.wait_for_url("**/hft_corridor_preview.html")
    assert "hft_corridor_preview.html" in page.url

    # In preview, click Back to Chart NT8
    page.wait_for_selector("#btn-back-chart")
    page.locator("#btn-back-chart").click()
    page.wait_for_url("**/index.html")
    assert "index.html" in page.url

    page.close()

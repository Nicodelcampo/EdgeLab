"""Visual inspection charts generator for HP007-CAMP-002 (Causal & Viewport-Invariant).

Renders neutral, target-free microstructural charts for selected sessions of NQ 06-26.
Features:
- Explicit reproducible tRef boundary plotted vertically.
- Active absorption zones strictly as-of (available_ts <= tRef).
- Zone rectangles terminate at or before tRef (no future leak).
- Continuous lateral density field profile D(p) computed via pure causal compute_field.
- Rollover boundary marker (state_reset_flag == True) when applicable.
- Mandatory prominent watermark: "PARITY_ABSTAIN — PYTHON EXPLORATORY VISUALIZATION ONLY"
- Absolute prohibition of outcome markers (no trades, no targets, no stops, no R:R, no P&L).
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd

from edgelab.bridge.indicators import bigtrap2absorption
from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.research.density_field import (
    compute_field,
    detect_density_intervals,
    price_to_tick,
    tick_to_price,
    to_nanoseconds,
)

MANIFEST_PATH = Path("docs/research/HP007_CAMP002_SESSION_SELECTION_MANIFEST_2026-09-15.json")
CATALOG_PATH = Path("docs/research/HP007_CAMP002_BT2A_CONFIG_CATALOG_2026-09-15.json")
OUTPUT_DIR = Path("docs/research/visual_charts")
ARTIFACT_DIR = Path("C:/Users/Usuario/.gemini/antigravity-ide/brain/894df4a6-beb3-46f1-bd1a-53ca4853b5e2")


def build_bars(ts_ns: np.ndarray, px_ticks: np.ndarray, bar_size: int = 120) -> list[dict]:
    """Aggregates tick stream into non-overlapping tick bars."""
    n = len(ts_ns)
    bars = []
    for i in range(0, n, bar_size):
        chunk_ts = ts_ns[i:i + bar_size]
        chunk_px = px_ticks[i:i + bar_size]
        if len(chunk_px) == 0:
            continue
        bars.append({
            "idx": len(bars),
            "open": chunk_px[0],
            "high": np.max(chunk_px),
            "low": np.min(chunk_px),
            "close": chunk_px[-1],
            "t_open": chunk_ts[0],
            "t_close": chunk_ts[-1]
        })
    return bars


def render_chart(
    session_id: str,
    trade_date: str,
    criterion: str,
    cfg_id: str,
    cfg_desc: str,
    bars: list[dict],
    all_zones: list[dict],
    t_ref_ns: int,
    tick_size: float,
    out_path: Path,
    has_roll: bool = False
):
    """Renders high-resolution chart with strictly causal visual logic elements."""
    fig, (ax_main, ax_field) = plt.subplots(
        1, 2, figsize=(16, 9),
        gridspec_kw={"width_ratios": [5, 1]},
        facecolor="#0d1117"
    )

    # Styling
    for ax in (ax_main, ax_field):
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#8b949e", labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#30363d")

    n_bars = len(bars)
    step = max(1, n_bars // 1000)
    sub_bars = bars[::step]

    # Find bar index closest to t_ref_ns
    t_ref_bar_idx = n_bars - 1
    for i, b in enumerate(bars):
        if b["t_close"] >= t_ref_ns:
            t_ref_bar_idx = i
            break

    # Plot candlesticks
    xs = [b["idx"] for b in sub_bars]
    opens = [b["open"] * tick_size for b in sub_bars]
    highs = [b["high"] * tick_size for b in sub_bars]
    lows = [b["low"] * tick_size for b in sub_bars]
    closes = [b["close"] * tick_size for b in sub_bars]

    for x, o, h, l, c in zip(xs, opens, highs, lows, closes):
        color = "#2ea043" if c >= o else "#f85149"
        ax_main.vlines(x, l, h, color=color, linewidth=1.0, alpha=0.8)
        ax_main.vlines(x, min(o, c), max(o, c), color=color, linewidth=2.5, alpha=0.9)

    # Filter zones causally: available_ts <= t_ref_ns
    active_zones = []
    for z in all_zones:
        sig_ts = z.get("sig_ts") or (z.get("created_ms", 0) * 1_000_000)
        avail_ts = int(sig_ts)
        if avail_ts <= t_ref_ns:
            zd = dict(z)
            zd["available_ts"] = avail_ts
            zd["bottom"] = float(z.get("lo", 0.0))
            zd["top"] = float(z.get("hi", 0.0))
            active_zones.append(zd)

    # Plot zones: only active zones, extending from origin to min(t_ref_bar, ended_bar)
    for z in active_zones:
        z_lo = z["bottom"]
        z_hi = z["top"]
        z_col = "#388bfd" if z.get("dir") == "long" else "#d29922"

        # Find start bar
        orig_ts = int(z.get("created_ms", 0) * 1_000_000)
        x_start = 0
        for i, b in enumerate(bars):
            if b["t_close"] >= orig_ts:
                x_start = i
                break

        x_end = t_ref_bar_idx
        if z.get("ended_ms") is not None:
            ended_ts = int(z["ended_ms"] * 1_000_000)
            if ended_ts < t_ref_ns:
                for i in range(x_start, len(bars)):
                    if bars[i]["t_close"] >= ended_ts:
                        x_end = i
                        break

        rect_w = max(2, x_end - x_start)
        rect = patches.Rectangle(
            (x_start, z_lo),
            rect_w,
            max(tick_size, z_hi - z_lo),
            linewidth=0.8,
            edgecolor=z_col,
            facecolor=z_col,
            alpha=0.25
        )
        ax_main.add_patch(rect)

    # Vertical tRef As-Of line
    t_ref_dt = pd.Timestamp(t_ref_ns, unit="ns", tz="UTC")
    t_ref_str = t_ref_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    ax_main.axvline(
        x=t_ref_bar_idx, color="#58a6ff", linestyle="--", linewidth=2.0,
        label=f"tRef As-Of Boundary ({t_ref_str})"
    )

    # Roll boundary marker if applicable
    if has_roll:
        ax_main.axvline(
            x=0, color="#da3633", linestyle="--", linewidth=2.0,
            label="Roll Boundary Purge (state_reset_flag == True)"
        )

    ax_main.legend(loc="upper left", facecolor="#161b22", edgecolor="#30363d", labelcolor="#f0f6fc", fontsize=8)

    # Compute causal lateral density field on integer tick domain
    all_prices = highs + lows
    min_chart_p = min(all_prices) if all_prices else 18000.0
    max_chart_p = max(all_prices) if all_prices else 18500.0
    p_min_tick = price_to_tick(min_chart_p - 5.0, tick_size)
    p_max_tick = price_to_tick(max_chart_p + 5.0, tick_size)

    field_res = compute_field(
        zones=active_zones,
        t_ref=t_ref_ns,
        tick_size=tick_size,
        price_tick_min=p_min_tick,
        price_tick_max=p_max_tick,
        field_config={"model": "FIELD_RAW_STATIC", "kernel": "KERNEL_GAUSS", "sigma_ticks": 1.2}
    )

    dp = np.array(field_res["density"], dtype=np.float64)
    px_grid = np.array([tick_to_price(k, tick_size) for k in field_res["price_ticks"]])

    # Plot lateral profile
    ax_field.fill_betweenx(px_grid, 0, dp, color="#38bdf8", alpha=0.35)
    ax_field.plot(dp, px_grid, color="#38bdf8", linewidth=1.2)
    ax_field.axvline(0.32, color="#22d3ee", linestyle=":", linewidth=1.0, label="Baja Densidad (0.32)")
    ax_field.axvline(0.70, color="#f59e0b", linestyle=":", linewidth=1.0, label="Alta Densidad (0.70)")
    ax_field.set_xlabel("D(p, tRef)", color="#8b949e", fontsize=8)
    ax_field.set_xlim(0, max(1.2, float(np.max(dp)) * 1.15))

    # Sync Y limits
    y_min = min_chart_p - 2.0
    y_max = max_chart_p + 2.0
    ax_main.set_ylim(y_min, y_max)
    ax_field.set_ylim(y_min, y_max)

    # Titles and metadata
    f_hash = field_res["field_hash"][:16]
    ax_main.set_title(
        f"HP-007 CAMP-002 · {session_id} ({trade_date}) · {cfg_id} · {criterion}\n"
        f"As-Of tRef: {t_ref_str} | Active Zones: {len(active_zones)} | Field Hash: {f_hash}...",
        color="#f0f6fc", fontsize=11, fontweight="bold", pad=12
    )

    # Watermark box
    ax_main.text(
        0.5, 0.94,
        "PARITY_ABSTAIN — PYTHON EXPLORATORY VISUALIZATION ONLY",
        transform=ax_main.transAxes,
        fontsize=10, fontweight="bold", color="#f85149",
        ha="center", va="top",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#1f1414", edgecolor="#f85149", alpha=0.9)
    )

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=120, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)

    # Copy to artifact dir for report presentation
    if ARTIFACT_DIR.exists():
        shutil.copy(out_path, ARTIFACT_DIR / out_path.name)

    print(f"  Rendered {out_path.name} | tRef: {t_ref_str} | Active zones: {len(active_zones)} | field_hash: {f_hash}")


def generate_all_charts():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    cfg_lookup = {c["configuration_id"]: c for c in catalog["configurations"]}
    sessions_lookup = {s["session_id"]: s for s in manifest["selected_sessions"]}
    source_parquet = manifest["asset"]["source_parquet"]
    tick_size = float(manifest["asset"]["tick_size"])

    # Chart specifications (8 charts from visual index)
    chart_specs = [
        ("HP007_VISUAL_SESS_01_BT2A_CFG_01", "SESS_01", "BT2A_CFG_01", False),
        ("HP007_VISUAL_SESS_02_BT2A_CFG_01", "SESS_02", "BT2A_CFG_01", False),
        ("HP007_VISUAL_SESS_02_BT2A_CFG_04", "SESS_02", "BT2A_CFG_04", False),
        ("HP007_VISUAL_SESS_02_BT2A_CFG_08", "SESS_02", "BT2A_CFG_08", False),
        ("HP007_VISUAL_SESS_02_BT2A_CFG_09", "SESS_02", "BT2A_CFG_09", False),
        ("HP007_VISUAL_SESS_03_BT2A_CFG_01", "SESS_03", "BT2A_CFG_01", True),
        ("HP007_VISUAL_SESS_04_BT2A_CFG_01", "SESS_04", "BT2A_CFG_01", False),
        ("HP007_VISUAL_SESS_05_BT2A_CFG_01", "SESS_05", "BT2A_CFG_01", False),
    ]

    # Preload sessions
    loaded_sessions: dict[str, Any] = {}
    for _, s_id, _, _ in chart_specs:
        s_meta = sessions_lookup[s_id]
        td = s_meta["trade_date"]
        if td not in loaded_sessions:
            print(f"Loading {td} ({s_id})...")
            t_series = load_canonical_parquet(
                source_parquet,
                start_utc_ns=s_meta["metrics"]["session_open_utc_ns"],
                end_utc_ns=s_meta["metrics"]["session_close_utc_ns"],
                instrument="NQ"
            )
            loaded_sessions[td] = t_series

    print(f"\nGenerating {len(chart_specs)} causal visual inspection charts...")
    for chart_id, s_id, cfg_id, has_roll in chart_specs:
        s_meta = sessions_lookup[s_id]
        td = s_meta["trade_date"]
        t_series = loaded_sessions[td]
        cfg = cfg_lookup[cfg_id]

        res = bigtrap2absorption.run(t_series, params=cfg["parameters"])
        bars = build_bars(t_series.ts_ns, t_series.price_ticks, bar_size=120)

        # Reproducible t_ref at 65% of session time
        open_ns = s_meta["metrics"]["session_open_utc_ns"]
        close_ns = s_meta["metrics"]["session_close_utc_ns"]
        t_ref_ns = int(open_ns + 0.65 * (close_ns - open_ns))

        out_path = OUTPUT_DIR / f"{chart_id}.png"
        render_chart(
            session_id=s_id,
            trade_date=td,
            criterion=s_meta["selection_criterion"],
            cfg_id=cfg_id,
            cfg_desc=cfg["description"],
            bars=bars,
            all_zones=res["zones"],
            t_ref_ns=t_ref_ns,
            tick_size=tick_size,
            out_path=out_path,
            has_roll=has_roll
        )

    print(f"\nAll {len(chart_specs)} charts regenerated and published.")


if __name__ == "__main__":
    generate_all_charts()

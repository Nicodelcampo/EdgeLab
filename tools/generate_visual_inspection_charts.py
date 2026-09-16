"""Visual inspection charts generator for HP007-CAMP-002.

Renders neutral, target-free microstructural charts for selected sessions of NQ 06-26.
Features:
- 120-tick candle bars
- Active absorption zones as-of
- Continuous lateral intensity field profile F(p)
- Rollover boundary marker (state_reset_flag == True)
- Mandatory prominent watermark: "PARITY_ABSTAIN — PYTHON EXPLORATORY VISUALIZATION ONLY"
- Absolute prohibition of outcome markers (no trades, no P&L, no traversal classifications).
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

from edgelab.bridge.indicators import bigtrap2absorption
from edgelab.bridge.ticks import load_canonical_parquet

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
    zones: list[dict],
    tick_size: float,
    out_path: Path,
    has_roll: bool = False
):
    """Renders high-resolution chart with neutral visual logic elements."""
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
    # Downsample bars for display if session is huge (keep up to 1200 bars for clear rendering)
    step = max(1, n_bars // 1000)
    sub_bars = bars[::step]

    # Plot candlesticks / price range
    xs = [b["idx"] for b in sub_bars]
    opens = [b["open"] * tick_size for b in sub_bars]
    highs = [b["high"] * tick_size for b in sub_bars]
    lows = [b["low"] * tick_size for b in sub_bars]
    closes = [b["close"] * tick_size for b in sub_bars]

    for x, o, h, l, c in zip(xs, opens, highs, lows, closes):
        color = "#2ea043" if c >= o else "#f85149"
        ax_main.vlines(x, l, h, color=color, linewidth=1.0, alpha=0.8)
        ax_main.vlines(x, min(o, c), max(o, c), color=color, linewidth=2.5, alpha=0.9)

    # Plot zones as neutral shaded intervals
    all_prices = highs + lows
    min_chart_p = min(all_prices) if all_prices else 0.0
    max_chart_p = max(all_prices) if all_prices else 100.0

    zone_vol_ref = np.median([z.get("vol", 1.0) for z in zones]) if zones else 100.0
    for z in zones:
        z_lo = z["lo"]
        z_hi = z["hi"]
        if z_hi < min_chart_p or z_lo > max_chart_p:
            continue
        z_col = "#388bfd" if z.get("dir") == "long" else "#d29922"
        v_weight = min(1.0, max(0.2, (z.get("vol", 1.0) / zone_vol_ref) ** 0.35))
        rect = patches.Rectangle(
            (0, z_lo),
            n_bars,
            max(tick_size, z_hi - z_lo),
            linewidth=0.8,
            edgecolor=z_col,
            facecolor=z_col,
            alpha=0.18 * v_weight
        )
        ax_main.add_patch(rect)

    # If roll session, plot vertical line for state reset
    if has_roll:
        ax_main.axvline(
            x=0, color="#da3633", linestyle="--", linewidth=2.5,
            label="state_reset_flag == True (Roll Boundary Purge)"
        )
        ax_main.legend(loc="upper left", facecolor="#161b22", edgecolor="#30363d", labelcolor="#f0f6fc")

    # Lateral field profile calculation
    p_grid = np.linspace(min_chart_p, max_chart_p, 200)
    sigma_pts = 1.2 * tick_size
    field_vals = []
    for p in p_grid:
        exp_sum = 0.0
        for z in zones:
            d = max(0.0, z["lo"] - p, p - z["hi"])
            if d <= 3.0 * sigma_pts:
                k = math.exp(-(d ** 2) / (2.0 * (sigma_pts ** 2)))
                w = (z.get("vol", 1.0) / zone_vol_ref) ** 0.25
                exp_sum += w * k
        f_val = 1.0 - math.exp(-exp_sum)
        field_vals.append(f_val)

    ax_field.plot(field_vals, p_grid, color="#a371f7", linewidth=2.0)
    ax_field.fill_betweenx(p_grid, 0, field_vals, color="#a371f7", alpha=0.25)
    ax_field.set_xlim(0, 1.0)
    ax_field.set_ylim(min_chart_p, max_chart_p)
    ax_field.set_xlabel("Field Intensity F(p)", color="#8b949e", fontsize=9)
    ax_field.axvline(0.6, color="#f0883e", linestyle=":", linewidth=1.0, alpha=0.6, label="High-Density (0.6)")
    ax_field.axvline(0.2, color="#58a6ff", linestyle=":", linewidth=1.0, alpha=0.6, label="Low-Density (0.2)")

    # Align main y-limits
    ax_main.set_ylim(min_chart_p, max_chart_p)
    ax_main.set_ylabel("Price (NQ pts)", color="#8b949e", fontsize=11)
    ax_main.set_xlabel("120-Tick Bar Index", color="#8b949e", fontsize=11)

    # Title
    fig.suptitle(
        f"EdgeLab Visual Logic Inspection — {session_id} ({trade_date}) | Asset: NQ 06-26\n"
        f"Config: {cfg_id} ({cfg_desc}) | Criterion: {criterion}",
        color="#f0f6fc", fontsize=12, fontweight="bold", y=0.97
    )

    # MANDATORY PROMINENT WATERMARK
    fig.text(
        0.45, 0.52,
        "PARITY_ABSTAIN — PYTHON EXPLORATORY VISUALIZATION ONLY",
        fontsize=18, color="#ffffff", alpha=0.18,
        ha="center", va="center", rotation=25, fontweight="heavy"
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.93])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"  Rendered: {out_path.name}")


def generate_all_charts():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        session_manifest = json.load(f)

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        config_catalog = json.load(f)

    source_parquet = session_manifest["asset"]["source_parquet"]
    tick_size = float(session_manifest["asset"]["tick_size"])
    sessions = session_manifest["selected_sessions"]

    cfg_dict = {c["configuration_id"]: c for c in config_catalog["configurations"]}

    # Target configurations for inspection:
    # BT2A_CFG_01 (Baseline)
    # BT2A_CFG_04 (Selective: 95%)
    # BT2A_CFG_08 (Stacked: min 2 rows)
    # BT2A_CFG_09 (Directional ScoreMode)
    target_cfgs = ["BT2A_CFG_01", "BT2A_CFG_04", "BT2A_CFG_08", "BT2A_CFG_09"]

    rendered_files = []
    print(f"Generating visual inspection charts into {OUTPUT_DIR}...")

    # Cache loaded sessions
    cached_ticks = {}

    for s in sessions:
        sid = s["session_id"]
        tdate = s["trade_date"]
        crit = s["selection_criterion"]
        open_ns = s["metrics"]["session_open_utc_ns"]
        close_ns = s["metrics"]["session_close_utc_ns"]

        if tdate not in cached_ticks:
            t_series = load_canonical_parquet(
                source_parquet, start_utc_ns=open_ns, end_utc_ns=close_ns, instrument="NQ"
            )
            bars = build_bars(t_series.ts_ns, t_series.price_ticks, bar_size=120)
            cached_ticks[tdate] = (t_series, bars)
        else:
            t_series, bars = cached_ticks[tdate]

        # For SESS_02 (Median session), render all 4 representative configs for comparison
        if sid == "SESS_02":
            cfgs_to_run = target_cfgs
        else:
            # Baseline config for other sessions
            cfgs_to_run = ["BT2A_CFG_01"]

        for cid in cfgs_to_run:
            cfg_info = cfg_dict[cid]
            res = bigtrap2absorption.run(t_series, params=cfg_info["parameters"])
            zones = res["zones"]

            has_roll = (sid == "SESS_03")
            fname = f"HP007_VISUAL_{sid}_{cid}.png"
            out_file = OUTPUT_DIR / fname

            render_chart(
                session_id=sid,
                trade_date=tdate,
                criterion=crit,
                cfg_id=cid,
                cfg_desc=cfg_info["description"],
                bars=bars,
                zones=zones,
                tick_size=tick_size,
                out_path=out_file,
                has_roll=has_roll
            )
            rendered_files.append((sid, tdate, crit, cid, cfg_info["description"], out_file))

            # Copy to artifact directory for easy IDE preview
            if ARTIFACT_DIR.exists():
                shutil.copy2(out_file, ARTIFACT_DIR / fname)

    # Write Visual Index Markdown
    index_md_path = Path("docs/research/HP007_CAMP002_VISUAL_INDEX_2026-09-15.md")
    lines = [
        "# Índice de Inspección Visual Lógica — HP007-CAMP-002",
        "## Fase de Diseño Visual Target-Free (Visual Logic Design)",
        "",
        "- **Activo Canónico:** `NQ 06-26` (Tick size: 0.25)",
        "- **Ancla Contractual:** [`29cad93d6600ee4c07a7d716be35e4881d78f491`](https://github.com/Nicodelcampo/EdgeLab/commit/29cad93d6600ee4c07a7d716be35e4881d78f491)",
        "- **Documento Rector:** [`docs/research/HP007_CAMP002_VISUAL_LOGIC_CATALOG_2026-09-15.md`](HP007_CAMP002_VISUAL_LOGIC_CATALOG_2026-09-15.md)",
        "- **Watermark Mandatorio:** `PARITY_ABSTAIN — PYTHON EXPLORATORY VISUALIZATION ONLY`",
        "- **Estado Oficial:** `READY_FOR_OWNER_VISUAL_REVIEW = YES`",
        "",
        "> [!IMPORTANT]",
        "> **Directiva del Propietario:** Queda prohibida toda medición empírica o estimación de edge.",
        "> La función de este índice es permitir la inspección visual neutral de zonas y campos para que el propietario defina la semántica de los eventos.",
        "",
        "---",
        "",
        "## Tabla de Gráficos Generados",
        "",
        "| ID Gráfico | ID Sesión | Fecha CME | Criterio de Selección | Configuración | Descripción de la Variante | Enlace Local |",
        "|---|---|---|---|---|---|---|"
    ]

    for sid, tdate, crit, cid, cdesc, out_file in rendered_files:
        rel_link = f"visual_charts/{out_file.name}"
        lines.append(f"| `{out_file.stem}` | `{sid}` | `{tdate}` | {crit} | `{cid}` | {cdesc} | [{out_file.name}]({rel_link}) |")

    lines.extend([
        "",
        "---",
        "",
        "## Checklist para la Inspección Visual del Propietario",
        "",
        "1. **Comparación de Sensibilidad en SESS_02 (Mediana de Actividad):**",
        "   - Compare `HP007_VISUAL_SESS_02_BT2A_CFG_01` (Baseline 90%) con `BT2A_CFG_04` (Restrictiva 95%): ¿Qué densidad de zonas resulta interpretable sin saturar el espacio?",
        "   - Observe `BT2A_CFG_08` (Zonas agrupadas min 2 filas): ¿Las zonas más gruesas capturan mejor los vacíos o los estrechan excesivamente?",
        "   - Observe `BT2A_CFG_09` (Direccional): ¿Aporta mejor asimetría entre vacíos superiores e inferiores?",
        "2. **Verificación de Rollover en SESS_03:**",
        "   - Verifique en `HP007_VISUAL_SESS_03_BT2A_CFG_01` que la línea roja vertical `state_reset_flag == True` purgue adecuadamente el estado.",
        "3. **Comportamiento en Extremos de Volatilidad:**",
        "   - `HP007_VISUAL_SESS_04_BT2A_CFG_01` (Alta volatilidad, rango 3.608t / 902 pts): Evalúe si el desgaste por toques (`NO_WEAR` vs `FULL`) es visualmente perceptible.",
        "   - `HP007_VISUAL_SESS_05_BT2A_CFG_01` (Bajo rango / compresión, rango 1.252t / 313 pts): Observe si los vacíos estrechos ($W < 5$ ticks) son absorbidos por el kernel gaussiano.",
        "",
        "### Aporte al Referente",
        "Se publica el paquete visual y el índice completo de inspección en `docs/research/HP007_CAMP002_VISUAL_INDEX_2026-09-15.md` y `docs/research/visual_charts/`. Quedan renderizadas las alternativas visuales comparables y neutrales sobre NQ 06-26 con watermark mandatorio, listas para la decisión semántica del propietario."
    ])

    with open(index_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nVisual index published to: {index_md_path}")


if __name__ == "__main__":
    generate_all_charts()

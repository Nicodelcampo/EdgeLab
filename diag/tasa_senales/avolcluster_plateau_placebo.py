"""aVolClusterPOI -- meseta (eje B) + placebo, protocolo target-free.

docs/research/AVOLCLUSTER_POI_RESOLUTION_PROTOCOL_2026-08-26.md #3.2/#3.3/#3.4.
Corre sobre el bar-type ganador del eje A (ticks, docs/research/avolcluster_bar_type_decision.json),
sobre TODO el split S (133 sesiones, specs/avolclusterpoi_resolution_split_v1.json).

Alcance declarado de ESTA corrida (no silent caps -- ver "Aporte al referente"):
- Grilla real: 5 tamanos de bloque {40,50,60,70,80}t a (percentile=98, multiplier=2.0)
  + 4 combinaciones de (percentile, multiplier) a tamano de bloque fijo 60t
  ({95,99}x{2.0} y {98}x{1.5,2.5}). 9 configs distintas (60t/98/2.0 es el punto
  compartido). NO es el producto cartesiano completo 5x3x3=45 -- esa grilla
  completa queda para una segunda pasada si esta primera no cierra la pregunta.
- Placebo (permutacion de volumen intra-bloque, K=50) SOLO en la config ganadora
  del eje A (60t/98/2.0) -- correrlo en las 9 configs es otra orden de magnitud
  de computo y no hace falta para responder "es meseta o es pico" (eso lo
  contesta la grilla real sola).
- Metrica de aislamiento medida en CREACION solamente: este kernel de
  investigacion (edgelab/bridge/indicators/avolclusterpoi.py) no implementa
  invalidacion/touches/expiracion (a diferencia del .cs) -- no hay lifecycle
  que medir mas alla de la creacion con el codigo que existe hoy. Consistente
  con el objeto declarado en #3.0 (creacion).

Target-free puro: cells = volumen por nivel de precio (SIN clasificar bid/ask,
detect_block no lo usa). No abre outcomes, no toca holdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.bars import build_tick_bars, BarSeries  # noqa: E402
from edgelab.bridge.ticks import TickSeries  # noqa: E402
from edgelab.bridge.indicators.avolclusterpoi import (  # noqa: E402
    SessionProfile, detect_block, session_relative_bucket, RESEARCH_DEFAULTS,
)
from tools.bt2_absorption_param_sweep import session_dates_from_ns  # noqa: E402
from tools.sweep_bigtrap2_tickframes import load_canonical_ticks  # noqa: E402
from diag.tasa_senales.avolcluster_bar_type_paso0 import load_split, assign_contract  # noqa: E402

DATA_DIR = Path(r"E:\DatosNT8")
TICK_SIZE_GC = 0.10
WINDOW_BARS = 10
PLACEBO_K = 50
PLACEBO_SEED = 20260826  # sin reusar semilla de ninguna otra campana


def slice_session(ticks: TickSeries, mask: np.ndarray) -> TickSeries:
    return TickSeries(
        ts_ns=ticks.ts_ns[mask], price_ticks=ticks.price_ticks[mask], volume=ticks.volume[mask],
        bid_ticks=ticks.bid_ticks[mask] if ticks.bid_ticks is not None else None,
        ask_ticks=ticks.ask_ticks[mask] if ticks.ask_ticks is not None else None,
        sequence=ticks.sequence[mask], tick_size=ticks.tick_size,
        instrument=ticks.instrument, contract=ticks.contract, source=ticks.source,
    )


def block_cells_and_meta(sess_ticks: TickSeries, bars: BarSeries, window_bars: int = WINDOW_BARS):
    """cells por bloque de `window_bars` barras (bloque parcial final descartado),
    vectorizado con pandas groupby (evita el loop por-tick de build_footprints,
    que no hace falta: cells no distingue bid/ask, solo volumen por precio)."""
    n_bars = len(bars)
    n_full = n_bars // window_bars
    if n_full == 0:
        return {}, np.asarray([], dtype=np.int64), np.asarray([], dtype=np.int64)
    n_bars_used = n_full * window_bars
    tick_mask = bars.tick_bar_idx < n_bars_used
    block_of_tick = bars.tick_bar_idx[tick_mask] // window_bars
    df = pd.DataFrame({
        "block": block_of_tick,
        "price": sess_ticks.price_ticks[tick_mask],
        "vol": sess_ticks.volume[tick_mask],
    })
    grouped = df.groupby(["block", "price"], sort=False)["vol"].sum()
    cells_by_block: dict[int, dict[int, float]] = {}
    for (blk, price), v in grouped.items():
        cells_by_block.setdefault(int(blk), {})[int(price)] = float(v)
    last_bar_of_block = np.arange(window_bars - 1, n_bars_used, window_bars)
    close_tick_by_block = bars.close_t[last_bar_of_block]
    block_end_ns_by_block = bars.end_ns[last_bar_of_block]
    return cells_by_block, close_tick_by_block, block_end_ns_by_block


def permute_cells(cells: dict[int, float], rng: np.random.Generator) -> dict[int, float]:
    """Placebo: baraja que tick recibe cada porcion de volumen, preservando EXACTO
    el conjunto de ticks activos y el multiset de volumenes -- destruye solo la
    contiguidad espacial del volumen, protocolo #3.3."""
    if len(cells) < 2:
        return dict(cells)
    prices = list(cells.keys())
    vols = list(cells.values())
    shuffled_vols = rng.permutation(vols)
    return {p: float(v) for p, v in zip(prices, shuffled_vols)}


def zone_metrics(zones_off_price: list[dict[str, Any]]) -> dict[str, Any]:
    """Metricas 1 y 3 de #3.4 (espesor, aislamiento en creacion) sobre las zonas
    OFF_PRICE de una config. AT_PRICE no tiene lower/upper de zona (ocupacion,
    no nivel) -- se cuenta aparte, no se mezcla en espesor/aislamiento."""
    if not zones_off_price:
        return {"n_zonas": 0, "espesor_mediana": None, "espesor_p25": None, "espesor_p75": None,
                "aislamiento_ticks_mediana": None}
    anchos = np.asarray([z["upper_tick"] - z["lower_tick"] + 1 for z in zones_off_price], dtype=np.float64)
    by_session: dict[str, list[int]] = {}
    for z in zones_off_price:
        by_session.setdefault(z["trade_date"], []).append(z["centro_tick"])
    gaps = []
    for _d, centros in by_session.items():
        centros_sorted = sorted(centros)
        if len(centros_sorted) >= 2:
            gaps.extend(np.diff(centros_sorted).tolist())
    return {
        "n_zonas": len(zones_off_price),
        "espesor_mediana": float(np.median(anchos)),
        "espesor_p25": float(np.quantile(anchos, 0.25)),
        "espesor_p75": float(np.quantile(anchos, 0.75)),
        "aislamiento_ticks_mediana": float(np.median(gaps)) if gaps else None,
    }


def run_config(ticks_by_contract: dict[str, TickSeries], sessions_by_contract: dict[str, list[str]],
               *, ticks_per_bar: int, percentile: float, multiplier: float,
               placebo_k: int = 0) -> dict[str, Any]:
    params = dict(RESEARCH_DEFAULTS)
    params["detection_percentile"] = float(percentile)
    params["median_multiplier"] = float(multiplier)

    zones_off_price: list[dict[str, Any]] = []
    n_at_price = 0
    n_blocks_total = 0
    n_sessions_procesadas = 0
    placebo_pass_real = 0
    placebo_pass_fake = 0
    placebo_evaluados = 0
    rng = np.random.default_rng(PLACEBO_SEED) if placebo_k else None

    for contract, dates in sorted(sessions_by_contract.items()):
        ticks = ticks_by_contract[contract]
        session_labels = session_dates_from_ns(ticks.ts_ns)
        profile = SessionProfile(lookback_sessions=RESEARCH_DEFAULTS["lookback_sessions"])
        for d in sorted(dates):
            mask = session_labels == d
            n = int(mask.sum())
            if n == 0:
                raise RuntimeError(f"{contract} {d}: 0 ticks -- sesion esperada por S, ausente en la cinta")
            sess_ticks = slice_session(ticks, mask)
            session_begin_ns = int(sess_ticks.ts_ns[0])
            bars = build_tick_bars(sess_ticks, ticks_per_bar=ticks_per_bar)
            cells_by_block, close_by_block, end_ns_by_block = block_cells_and_meta(sess_ticks, bars)
            n_sessions_procesadas += 1
            for blk in sorted(cells_by_block):
                cells = cells_by_block[blk]
                close_tick = int(close_by_block[blk])
                bucket = session_relative_bucket(int(end_ns_by_block[blk]), session_begin_ns,
                                                  RESEARCH_DEFAULTS["time_bucket_minutes"])
                hist = profile.history_scores(bucket)
                out = detect_block(cells, hist, params=params, close_tick=close_tick)
                profile.add_block(bucket, out["best_score"])
                n_blocks_total += 1
                for z in out["zones"]:
                    if z["kind"] == "OFF_PRICE":
                        zones_off_price.append({
                            "trade_date": d, "contract": contract,
                            "lower_tick": z["lower_tick"], "upper_tick": z["upper_tick"],
                            "centro_tick": (z["lower_tick"] + z["upper_tick"]) // 2,
                        })
                    else:
                        n_at_price += 1
                if placebo_k and len(cells) >= 2:
                    real_pass = bool(out["zones"])
                    fake_pass_count = 0
                    for _ in range(placebo_k):
                        fake_cells = permute_cells(cells, rng)
                        fake_out = detect_block(fake_cells, hist, params=params, close_tick=close_tick)
                        if fake_out["zones"]:
                            fake_pass_count += 1
                    placebo_evaluados += 1
                    placebo_pass_real += int(real_pass)
                    placebo_pass_fake += fake_pass_count / float(placebo_k)
            profile.commit()

    metrics = zone_metrics(zones_off_price)
    metrics["n_at_price"] = n_at_price
    metrics["n_blocks_evaluados"] = n_blocks_total
    metrics["n_sesiones"] = n_sessions_procesadas
    metrics["frecuencia_normalizada_x100bloques"] = (
        100.0 * metrics["n_zonas"] / n_blocks_total if n_blocks_total else None)
    metrics["frecuencia_cruda_por_sesion"] = (
        metrics["n_zonas"] / n_sessions_procesadas if n_sessions_procesadas else None)

    result: dict[str, Any] = {
        "ticks_per_bar": ticks_per_bar, "detection_percentile": percentile, "median_multiplier": multiplier,
        "metrics": metrics,
    }
    if placebo_k:
        result["placebo"] = {
            "k": placebo_k,
            "n_bloques_evaluados": placebo_evaluados,
            "tasa_pass_real": placebo_pass_real / placebo_evaluados if placebo_evaluados else None,
            "tasa_pass_placebo": placebo_pass_fake / placebo_evaluados if placebo_evaluados else None,
        }
    return result


def plateau_check(landscape: list[dict[str, Any]], baseline_key: str, axis: str,
                   metric_keys: tuple[str, ...], tol_rel: float = 0.15) -> dict[str, Any]:
    base = next(r for r in landscape if r["_key"] == baseline_key)
    out = {}
    for r in landscape:
        if r["_key"] == baseline_key or r.get("_axis") != axis:
            continue
        ok = True
        detalle = {}
        for k in metric_keys:
            bv, rv = base["metrics"].get(k), r["metrics"].get(k)
            if bv is None or rv is None or bv == 0:
                ok = False
                detalle[k] = "no_comparable"
                continue
            rel = abs(rv - bv) / abs(bv)
            detalle[k] = round(rel, 4)
            if rel > tol_rel:
                ok = False
        out[r["_key"]] = {"dentro_de_meseta": ok, "detalle_variacion_relativa": detalle}
    return out


def main() -> int:
    split = load_split()
    S = split["S"]
    sessions_by_contract: dict[str, list[str]] = {}
    for d in S:
        sessions_by_contract.setdefault(assign_contract(split, d), []).append(d)

    ticks_by_contract: dict[str, TickSeries] = {}
    for contract in sorted(sessions_by_contract):
        path = DATA_DIR / f"{contract}.Last.txt"
        ticks, *_ = load_canonical_ticks(path, tick_size=TICK_SIZE_GC, max_ticks=None)
        ticks_by_contract[contract] = ticks

    grid_block = [40, 50, 60, 70, 80]
    grid_pm = [(95.0, 2.0), (99.0, 2.0), (98.0, 1.5), (98.0, 2.5)]

    landscape = []
    for n in grid_block:
        r = run_config(ticks_by_contract, sessions_by_contract, ticks_per_bar=n,
                        percentile=98.0, multiplier=2.0, placebo_k=(PLACEBO_K if n == 60 else 0))
        r["_key"] = f"{n}t_98p_2.0m"
        r["_axis"] = "block_size"
        landscape.append(r)
        print(f"[grid] {r['_key']}: n_zonas={r['metrics']['n_zonas']} "
              f"espesor_p50={r['metrics']['espesor_mediana']}", flush=True)

    for pct, mult in grid_pm:
        r = run_config(ticks_by_contract, sessions_by_contract, ticks_per_bar=60,
                        percentile=pct, multiplier=mult, placebo_k=0)
        r["_key"] = f"60t_{pct}p_{mult}m"
        r["_axis"] = "percentile_multiplier"
        landscape.append(r)
        print(f"[grid] {r['_key']}: n_zonas={r['metrics']['n_zonas']} "
              f"espesor_p50={r['metrics']['espesor_mediana']}", flush=True)

    baseline_key = "60t_98p_2.0m"
    meseta_block = plateau_check(landscape, baseline_key, "block_size",
                                  ("espesor_mediana", "frecuencia_normalizada_x100bloques",
                                   "aislamiento_ticks_mediana"))
    meseta_pm = plateau_check(landscape, baseline_key, "percentile_multiplier",
                               ("espesor_mediana", "frecuencia_normalizada_x100bloques",
                                "aislamiento_ticks_mediana"))

    result = {
        "schema": "avolcluster_plateau_placebo_v1",
        "target_free": True,
        "outcomes_opened": False,
        "holdout_accessed": False,
        "split_path": "specs/avolclusterpoi_resolution_split_v1.json",
        "universo": "S completo (133 sesiones)",
        "window_bars": WINDOW_BARS,
        "baseline": baseline_key,
        "grilla_declarada": {
            "block_size_at_98p_2.0m": grid_block,
            "percentile_multiplier_at_60t": grid_pm,
            "alcance": "NO es el producto cartesiano completo 5x3x3 -- ver docstring del script",
        },
        "landscape": landscape,
        "meseta_eje_block_size": meseta_block,
        "meseta_eje_percentile_multiplier": meseta_pm,
    }
    out_path = REPO_ROOT / "docs" / "research" / "avolcluster_plateau_placebo.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps({"meseta_eje_block_size": meseta_block, "meseta_eje_percentile_multiplier": meseta_pm,
                       "placebo": next(r["placebo"] for r in landscape if r["_key"] == baseline_key)},
                      indent=2, ensure_ascii=False))
    print(f"escrito: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

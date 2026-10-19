"""aVolClusterPOI -- decision del eje A (bar-type), protocolo target-free.

docs/research/AVOLCLUSTER_POI_RESOLUTION_PROTOCOL_2026-08-26.md #3.1: decide
tiempo (1m/3m/5m) vs. ticks ANTES de explorar tamano de bloque (#3.2), sobre la
serie de volumen total del bloque de WINDOW_BARS=10 barras -- el mismo bloque
que usa el indicador real (SessionProfile, WindowBars default). NO usa el score
del kernel (seria circular: el score ya depende de la resolucion elegida).

Candidatos de ticks derivados de docs/research/avolcluster_bar_type_paso0.json
(mediana de ticks/minuto * {1,3,5}, redondeado a multiplo de 5) -- nunca
elegidos a mano.

Target-free puro. Mismas 19 sesiones de paso0 (misma submuestra de S). No abre
outcomes, no toca holdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.bars import build_time_bars, build_tick_bars, BarSeries  # noqa: E402
from edgelab.bridge.ticks import TickSeries  # noqa: E402
from tools.bt2_absorption_param_sweep import session_dates_from_ns  # noqa: E402
from tools.sweep_bigtrap2_tickframes import load_canonical_ticks  # noqa: E402
from diag.tasa_senales.avolcluster_bar_type_paso0 import (  # noqa: E402
    load_split, sample_S, assign_contract,
)

DATA_DIR = Path(r"E:\DatosNT8")
TICK_SIZE_GC = 0.10
WINDOW_BARS = 10  # WindowBars default del indicador (RESEARCH_DEFAULTS)
PASO0_PATH = REPO_ROOT / "docs" / "research" / "avolcluster_bar_type_paso0.json"
MIN_BLOCKS_PARA_ESTADISTICO = 6  # umbral para poder partir en tercios con >=2 c/u


def slice_session(ticks: TickSeries, mask: np.ndarray) -> TickSeries:
    return TickSeries(
        ts_ns=ticks.ts_ns[mask],
        price_ticks=ticks.price_ticks[mask],
        volume=ticks.volume[mask],
        bid_ticks=ticks.bid_ticks[mask] if ticks.bid_ticks is not None else None,
        ask_ticks=ticks.ask_ticks[mask] if ticks.ask_ticks is not None else None,
        sequence=ticks.sequence[mask],
        tick_size=ticks.tick_size,
        instrument=ticks.instrument,
        contract=ticks.contract,
        source=ticks.source,
    )


def block_volumes(bars: BarSeries, window_bars: int = WINDOW_BARS) -> np.ndarray:
    """Volumen total por bloque de `window_bars` barras consecutivas.

    El bloque parcial del final se DESCARTA (mismo contrato que el .cs, ver
    docs/research/AVOLCLUSTER_POI_PROTOCOL_2026-08-13.md #3: "El bloque parcial
    del final de sesion se descarta").
    """
    n = len(bars.volume)
    n_full = n // window_bars
    if n_full == 0:
        return np.asarray([], dtype=np.float64)
    return bars.volume[: n_full * window_bars].reshape(n_full, window_bars).sum(axis=1)


def autocorr_lag1(v: np.ndarray) -> float | None:
    if v.size < 3 or np.std(v[:-1]) == 0 or np.std(v[1:]) == 0:
        return None
    return float(np.corrcoef(v[:-1], v[1:])[0, 1])


def homoscedasticity_ratio(v: np.ndarray) -> float | None:
    """Razon de varianza entre el primer y el ultimo tercio de la serie.

    Mas cerca de 1.0 = mas homocedastico (la dispersion no cambia con la hora).
    """
    n = v.size
    if n < MIN_BLOCKS_PARA_ESTADISTICO:
        return None
    third = n // 3
    first, last = v[:third], v[n - third:]
    var_first, var_last = np.var(first), np.var(last)
    if var_last == 0:
        return None
    return float(var_first / var_last)


def tick_candidates_from_paso0() -> list[int]:
    paso0 = json.loads(PASO0_PATH.read_text(encoding="utf-8"))
    p50 = paso0["agregado"]["ticks_por_min_p50"]
    raw = [p50 * 1, p50 * 3, p50 * 5]
    return [int(round(x / 5.0)) * 5 for x in raw]


def bartype_candidates() -> list[tuple[str, int]]:
    ticks_n = tick_candidates_from_paso0()
    return [("time", 1), ("time", 3), ("time", 5),
            ("tick", ticks_n[0]), ("tick", ticks_n[1]), ("tick", ticks_n[2])]


def label(kind: str, param: int) -> str:
    return f"{param}m" if kind == "time" else f"{param}t"


def main() -> int:
    split = load_split()
    sample = sample_S(split)
    candidates = bartype_candidates()

    by_contract: dict[str, list[str]] = {}
    for d in sample:
        by_contract.setdefault(assign_contract(split, d), []).append(d)

    per_candidate: dict[str, list[dict[str, Any]]] = {label(k, p): [] for k, p in candidates}

    for contract, dates in sorted(by_contract.items()):
        path = DATA_DIR / f"{contract}.Last.txt"
        ticks, *_ = load_canonical_ticks(path, tick_size=TICK_SIZE_GC, max_ticks=None)
        session_labels = session_dates_from_ns(ticks.ts_ns)
        for d in dates:
            mask = session_labels == d
            sess_ticks = slice_session(ticks, mask)
            for kind, param in candidates:
                bars = (build_time_bars(sess_ticks, minutes=param) if kind == "time"
                        else build_tick_bars(sess_ticks, ticks_per_bar=param))
                v = block_volumes(bars)
                per_candidate[label(kind, param)].append({
                    "trade_date": d, "contract": contract,
                    "n_bars": int(len(bars)), "n_blocks": int(v.size),
                    "autocorr_lag1": autocorr_lag1(v),
                    "homoscedasticity_ratio": homoscedasticity_ratio(v),
                })

    landscape = {}
    for lbl, rows in per_candidate.items():
        autocorrs = [r["autocorr_lag1"] for r in rows if r["autocorr_lag1"] is not None]
        homos = [r["homoscedasticity_ratio"] for r in rows if r["homoscedasticity_ratio"] is not None]
        n_blocks = np.asarray([r["n_blocks"] for r in rows], dtype=np.float64)
        cv_blocks = float(np.std(n_blocks) / np.mean(n_blocks)) if np.mean(n_blocks) > 0 else None
        landscape[lbl] = {
            "n_sesiones": len(rows),
            "n_sesiones_con_autocorr": len(autocorrs),
            "n_sesiones_con_homoscedasticidad": len(homos),
            "autocorr_lag1_mediana": float(np.median(autocorrs)) if autocorrs else None,
            "autocorr_lag1_abs_mediana": float(np.median(np.abs(autocorrs))) if autocorrs else None,
            "homoscedasticity_ratio_mediana": float(np.median(homos)) if homos else None,
            "cv_blocks_por_sesion": cv_blocks,
            "n_blocks_mediana": float(np.median(n_blocks)),
        }

    # Cascada declarada antes de mirar el landscape (protocolo #3.1/#3.6 adaptado):
    # 1) exigir cobertura estadistica minima (>=15/19 sesiones con ambos estadisticos)
    # 2) entre los que pasan, menor |autocorrelacion lag-1| mediana (menos redundancia)
    # 3) desempate: homoscedasticity_ratio mas cercano a 1.0
    MIN_COBERTURA = 15
    elegibles = {lbl: s for lbl, s in landscape.items()
                 if s["n_sesiones_con_autocorr"] >= MIN_COBERTURA
                 and s["n_sesiones_con_homoscedasticidad"] >= MIN_COBERTURA}
    if elegibles:
        ganador = min(
            elegibles.items(),
            key=lambda kv: (kv[1]["autocorr_lag1_abs_mediana"], abs(kv[1]["homoscedasticity_ratio_mediana"] - 1.0)),
        )[0]
    else:
        ganador = None

    result = {
        "schema": "avolcluster_bar_type_decision_v1",
        "target_free": True,
        "outcomes_opened": False,
        "holdout_accessed": False,
        "window_bars": WINDOW_BARS,
        "min_bloques_para_homoscedasticidad": MIN_BLOCKS_PARA_ESTADISTICO,
        "min_cobertura_sesiones": MIN_COBERTURA,
        "candidatos": [label(k, p) for k, p in candidates],
        "ticks_derivados_de_paso0": tick_candidates_from_paso0(),
        "landscape": landscape,
        "detalle_por_sesion": per_candidate,
        "cascada": {
            "paso_1": "cobertura estadistica >= 15/19 sesiones con autocorrelacion Y homoscedasticidad definidas",
            "paso_2": "menor mediana de |autocorrelacion lag-1| entre los elegibles",
            "paso_3_desempate": "homoscedasticity_ratio mas cercano a 1.0",
        },
        "ganador_eje_A": ganador,
    }
    out_path = REPO_ROOT / "docs" / "research" / "avolcluster_bar_type_decision.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps({"landscape": landscape, "ganador_eje_A": ganador}, indent=2, ensure_ascii=False))
    print(f"escrito: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""aVolClusterPOI -- paso 0 del eje A (bar-type), protocolo target-free.

Mide la distribucion empirica de ticks/minuto por sesion sobre una submuestra
deterministica de S (docs/research/AVOLCLUSTER_POI_RESOLUTION_PROTOCOL_2026-08-26.md
#3.1, #4). Sirve para dos cosas, ninguna es todavia la decision de bar-type:

1. Insumo del criterio estadistico de #3.1 (autocorrelacion/homocedasticidad),
   que corre en avolcluster_bar_type_decision.py sobre estas mismas sesiones.
2. Derivar candidatos de tamano de barra en ticks para el eje B (#3.2), en vez
   de elegirlos a mano.

Target-free puro: no calcula MFE/MAE/P&L/retornos/hit-rate. No abre outcomes.
No toca el holdout (universo = specs/avolclusterpoi_resolution_split_v1.json#S,
todo <= 2026-06-30).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.bt2_absorption_param_sweep import session_dates_from_ns  # noqa: E402
from tools.sweep_bigtrap2_tickframes import load_canonical_ticks  # noqa: E402

SPLIT_PATH = REPO_ROOT / "specs" / "avolclusterpoi_resolution_split_v1.json"
DATA_DIR = Path(r"E:\DatosNT8")
TICK_SIZE_GC = 0.10
STRIDE = 7  # paso 0 explicito: cada STRIDE-esima sesion de S, ordenada por fecha


def load_split() -> dict[str, Any]:
    return json.loads(SPLIT_PATH.read_text(encoding="utf-8"))


def sample_S(split: dict[str, Any], stride: int = STRIDE) -> list[str]:
    """Submuestra deterministica de S: cada `stride`-esima sesion, ordenada.

    Determinista, sin semilla, no gameable -- mismo espiritu que la regla de
    particion del split (i % 8 == 7). NO es un muestreo aleatorio.
    """
    s_sorted = sorted(split["S"])
    return s_sorted[::stride]


def assign_contract(split: dict[str, Any], trade_date: str) -> str:
    """Contrato asignado a una sesion. El split no guarda la asignacion inversa
    (solo listas S/C), asi que se reconstruye desde la cadena front-month."""
    chain = json.loads((REPO_ROOT / "docs" / "research" / "CADENA_FRONTMONTH_GC.json").read_text(encoding="utf-8"))
    return chain["asignacion"][trade_date]


def minute_bucket_counts(ts_ns: np.ndarray) -> np.ndarray:
    """Ticks por bucket de 1 minuto de reloj (UTC). Vectorizado, sin pandas.

    Devuelve el conteo por CADA minuto que tuvo >=1 tick (minutos sin ticks no
    entran al array -- una sesion tranquila no infla el denominador con ceros
    artificiales; el numero de minutos ACTIVOS se reporta aparte).
    """
    if ts_ns.size == 0:
        return np.asarray([], dtype=np.int64)
    minute_id = ts_ns // 60_000_000_000
    _, counts = np.unique(minute_id, return_counts=True)
    return counts


def session_stats(counts: np.ndarray, n_ticks_total: int) -> dict[str, Any]:
    if counts.size == 0:
        return {"n_active_minutes": 0, "n_ticks": 0, "ticks_per_min_p10": None,
                "ticks_per_min_p50": None, "ticks_per_min_p90": None, "ticks_per_min_mean": None}
    return {
        "n_active_minutes": int(counts.size),
        "n_ticks": int(n_ticks_total),
        "ticks_per_min_p10": float(np.quantile(counts, 0.10)),
        "ticks_per_min_p50": float(np.quantile(counts, 0.50)),
        "ticks_per_min_p90": float(np.quantile(counts, 0.90)),
        "ticks_per_min_mean": float(np.mean(counts)),
    }


def main() -> int:
    split = load_split()
    assert split["schema"] == "avolclusterpoi_resolution_split_v1"
    assert split["status"] == "FROZEN_BEFORE_METRICS"
    sample = sample_S(split)
    by_contract: dict[str, list[str]] = {}
    for d in sample:
        by_contract.setdefault(assign_contract(split, d), []).append(d)

    per_session: list[dict[str, Any]] = []
    all_counts: list[np.ndarray] = []

    for contract, dates in sorted(by_contract.items()):
        path = DATA_DIR / f"{contract}.Last.txt"
        if not path.exists():
            raise FileNotFoundError(path)
        ticks, *_ = load_canonical_ticks(path, tick_size=TICK_SIZE_GC, max_ticks=None)
        session_labels = session_dates_from_ns(ticks.ts_ns)
        for d in dates:
            mask = session_labels == d
            n = int(mask.sum())
            if n == 0:
                raise RuntimeError(f"{contract} {d}: 0 ticks en la cinta -- sesion esperada por el split, ausente en la cinta")
            counts = minute_bucket_counts(ticks.ts_ns[mask])
            stats = session_stats(counts, n)
            stats["trade_date"] = d
            stats["contract"] = contract
            per_session.append(stats)
            all_counts.append(counts)

    agg = np.concatenate(all_counts) if all_counts else np.asarray([], dtype=np.int64)
    result = {
        "schema": "avolcluster_bar_type_paso0_v1",
        "target_free": True,
        "outcomes_opened": False,
        "holdout_accessed": False,
        "split_path": str(SPLIT_PATH.relative_to(REPO_ROOT)),
        "stride": STRIDE,
        "n_sesiones_muestreadas": len(sample),
        "sesiones_muestreadas": sample,
        "balance_por_contrato": {c: len(v) for c, v in sorted(by_contract.items())},
        "por_sesion": per_session,
        "agregado": {
            "n_sesiones": len(per_session),
            "n_ticks_total": int(sum(s["n_ticks"] for s in per_session)),
            "ticks_por_min_p10": float(np.quantile(agg, 0.10)) if agg.size else None,
            "ticks_por_min_p25": float(np.quantile(agg, 0.25)) if agg.size else None,
            "ticks_por_min_p50": float(np.quantile(agg, 0.50)) if agg.size else None,
            "ticks_por_min_p75": float(np.quantile(agg, 0.75)) if agg.size else None,
            "ticks_por_min_p90": float(np.quantile(agg, 0.90)) if agg.size else None,
            "ticks_por_min_mean": float(np.mean(agg)) if agg.size else None,
        },
    }
    out_path = REPO_ROOT / "docs" / "research" / "avolcluster_bar_type_paso0.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps(result["agregado"], indent=2, ensure_ascii=False))
    print(f"escrito: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

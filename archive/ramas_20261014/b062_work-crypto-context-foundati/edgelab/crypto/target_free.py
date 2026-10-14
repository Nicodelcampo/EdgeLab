"""Preregistro y censos target-free para el piloto crypto de BigTrap2.

Este módulo prepara la investigación antes de recibir parquets u oráculos. No
acepta retornos, P&L, etiquetas ni columnas de respuesta. La unidad de volumen
no tiene default: debe declararse y se somete a una sensibilidad preregistrada.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from edgelab.bridge.ticks import TickSeries

TARGET_FREE_SPEC_SCHEMA = "edgelab.crypto.bt2_target_free/1.0.0"
TARGET_FREE_CENSUS_SCHEMA = "edgelab.crypto.bt2_target_free_census/1.0.0"


def _positive_decimal(value: str | float | Decimal, name: str) -> Decimal:
    try:
        out = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} no es decimal: {value!r}") from exc
    if not out.is_finite() or out <= 0:
        raise ValueError(f"{name} debe ser finito y > 0: {value!r}")
    return out


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


@dataclass(frozen=True)
class UnitSensitivityPoint:
    symbol: str
    reference_unit_base: str
    multiplier: str
    quantity_unit_base: str
    config_id: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def build_unit_sensitivity_plan(
    symbol: str,
    reference_unit_base: str | float | Decimal,
    multipliers: Iterable[str | float | Decimal],
) -> tuple[UnitSensitivityPoint, ...]:
    """Construye una grilla determinista; referencia y multiplicadores son obligatorios."""
    normalized_symbol = str(symbol).strip().upper()
    if not normalized_symbol:
        raise ValueError("symbol vacío")
    reference = _positive_decimal(reference_unit_base, "reference_unit_base")
    parsed = tuple(_positive_decimal(x, "multiplier") for x in multipliers)
    if not parsed:
        raise ValueError("multipliers vacío")
    if len(set(parsed)) != len(parsed):
        raise ValueError("multipliers contiene duplicados")
    if Decimal("1") not in parsed:
        raise ValueError("multipliers debe incluir 1 para identificar la referencia")

    points: list[UnitSensitivityPoint] = []
    for multiplier in parsed:
        unit = reference * multiplier
        payload = {
            "symbol": normalized_symbol,
            "reference_unit_base": _canonical_decimal(reference),
            "multiplier": _canonical_decimal(multiplier),
            "quantity_unit_base": _canonical_decimal(unit),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        config_id = "crypto-unit-" + sha256(canonical.encode("utf-8")).hexdigest()[:12]
        points.append(UnitSensitivityPoint(config_id=config_id, **payload))
    return tuple(points)


def load_target_free_spec(path: str | Path) -> dict[str, Any]:
    """Carga el preregistro y falla cerrado si se abrió una variable de respuesta."""
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    if spec.get("schema") != TARGET_FREE_SPEC_SCHEMA:
        raise ValueError(f"schema inesperado: {spec.get('schema')!r}")
    if spec.get("status") != "FROZEN_PENDING_INPUTS":
        raise ValueError("el preregistro debe estar FROZEN_PENDING_INPUTS")

    firewall = spec.get("firewall")
    expected_firewall = {
        "outcomes_accessed": False,
        "returns_accessed": False,
        "pnl_accessed": False,
        "holdout_accessed": False,
        "response_columns": [],
    }
    if firewall != expected_firewall:
        raise ValueError("firewall target-free inválido o incompleto")

    quantity = spec.get("quantity_unit") or {}
    if quantity.get("reference_required") is not True:
        raise ValueError("quantity_unit.reference_required debe ser true")
    if "default_reference_unit_base" in quantity:
        raise ValueError("la unidad de volumen no puede tener default")
    multipliers = quantity.get("sensitivity_multipliers")
    parsed = tuple(_positive_decimal(x, "sensitivity_multiplier") for x in multipliers or [])
    if not parsed or len(set(parsed)) != len(parsed) or Decimal("1") not in parsed:
        raise ValueError("sensitivity_multipliers debe ser no vacío, único e incluir 1")

    stages = spec.get("stages") or []
    symbols = [str(stage.get("symbol", "")).strip().upper() for stage in stages]
    if not symbols or any(not symbol for symbol in symbols) or len(set(symbols)) != len(symbols):
        raise ValueError("stages debe declarar símbolos únicos y no vacíos")
    if [int(stage.get("order", -1)) for stage in stages] != list(range(1, len(stages) + 1)):
        raise ValueError("stages.order debe ser consecutivo desde 1")
    return spec


def target_free_census(ticks: TickSeries) -> dict[str, Any]:
    """Resume integridad, actividad y geometría sin tocar ninguna respuesta futura."""
    n = len(ticks)
    if n == 0:
        raise ValueError("TickSeries vacío")
    arrays = {
        "ts_ns": np.asarray(ticks.ts_ns, dtype=np.int64),
        "price_ticks": np.asarray(ticks.price_ticks, dtype=np.int64),
        "volume": np.asarray(ticks.volume, dtype=np.float64),
        "sequence": np.asarray(ticks.sequence, dtype=np.int64),
    }
    if ticks.bid_ticks is None or ticks.ask_ticks is None:
        raise ValueError("el censo crypto requiere bid_ticks y ask_ticks")
    arrays["bid_ticks"] = np.asarray(ticks.bid_ticks, dtype=np.int64)
    arrays["ask_ticks"] = np.asarray(ticks.ask_ticks, dtype=np.int64)
    if any(len(values) != n for values in arrays.values()):
        raise ValueError("TickSeries tiene longitudes inconsistentes")
    if not np.isfinite(arrays["volume"]).all() or np.any(arrays["volume"] <= 0):
        raise ValueError("volume debe ser finito y > 0")

    ts = arrays["ts_ns"]
    sequence = arrays["sequence"]
    if np.any(np.diff(ts) < 0):
        raise ValueError("ts_ns no es monótono")
    identity = np.rec.fromarrays([ts, sequence], names="ts,sequence")
    if len(np.unique(identity)) != n:
        raise ValueError("identidad (ts_ns, sequence) duplicada")
    order = np.lexsort((sequence, ts))
    if not np.array_equal(order, np.arange(n, dtype=np.int64)):
        raise ValueError("orden causal debe ser (ts_ns, sequence)")

    spread = arrays["ask_ticks"] - arrays["bid_ticks"]
    if np.any(spread < 0):
        raise ValueError("book cruzado: ask_ticks < bid_ticks")
    duration_ns = int(ts[-1] - ts[0])
    volume_q = np.quantile(arrays["volume"], [0.5, 0.9, 0.99])
    spread_q = np.quantile(spread.astype(np.float64), [0.5, 0.9, 0.99])

    return {
        "schema": TARGET_FREE_CENSUS_SCHEMA,
        "target_free": True,
        "outcomes_opened": False,
        "instrument": str(ticks.instrument),
        "contract": str(ticks.contract),
        "n_ticks": n,
        "first_ts_ns": int(ts[0]),
        "last_ts_ns": int(ts[-1]),
        "duration_ns": duration_ns,
        "same_timestamp_adjacent_pairs": int(np.sum(np.diff(ts) == 0)),
        "tick_rate_per_second": (float(n * 1_000_000_000 / duration_ns) if duration_ns > 0 else None),
        "locked_book_pct": float(np.mean(spread == 0)),
        "spread_ticks_p50": float(spread_q[0]),
        "spread_ticks_p90": float(spread_q[1]),
        "spread_ticks_p99": float(spread_q[2]),
        "volume_units_p50": float(volume_q[0]),
        "volume_units_p90": float(volume_q[1]),
        "volume_units_p99": float(volume_q[2]),
    }

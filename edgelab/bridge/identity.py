"""Identidades canónicas, content-addressed e independientes de rutas (F6.1)."""
from __future__ import annotations

import hashlib
import json
import os

ENGINE_VERSION = "1"
DATASET_SCHEMA_VERSION = "canonical_tick_v1"
OBSERVATION_SCHEMA_VERSION = "1"
EVENT_SCHEMA_VERSION = "1"
ZONE_SCHEMA_VERSION = "1"
ID_LEN = 16

_BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
_COMMON_DEPS = ("common.py", "bars.py")
_KERNEL_FILE = {
    "Gaps2": "gaps2.py",
    "VolTicksPOC2": "voltickspoc2.py",
    "BigTrap2": "bigtrap2.py",
    "BigTrap2Absorption": "bigtrap2absorption_adapter.py",
    "HFTZones2": "hftzones2.py",
    "aVolCellPOI2": "avolcellpoi2.py",
    "AACloseOpenDiffs": "aacloseopendiffs.py",
}
_KERNEL_DEPS = {
    "Gaps2": _COMMON_DEPS,
    "VolTicksPOC2": _COMMON_DEPS,
    "BigTrap2": _COMMON_DEPS,
    "BigTrap2Absorption": _COMMON_DEPS + (
        "sessions.py", "indicators/bigtrap2absorption.py"
    ),
    "HFTZones2": _COMMON_DEPS + ("sessions.py",),
    "aVolCellPOI2": _COMMON_DEPS + ("sessions.py",),
    "AACloseOpenDiffs": _COMMON_DEPS,
}


def canonical_json(obj) -> str:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )


def _hash(obj, n: int = ID_LEN) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()[:n]


def sha256_bytes(*blobs: bytes) -> str:
    h = hashlib.sha256()
    for blob in blobs:
        h.update(blob)
    return h.hexdigest()


def content_sha256_of_ticks(ticks) -> str:
    h = hashlib.sha256()
    for name in ("ts_ns", "price_ticks", "volume", "sequence"):
        h.update(name.encode())
        h.update(getattr(ticks, name).tobytes())
    for name in ("bid_ticks", "ask_ticks"):
        arr = getattr(ticks, name)
        h.update(name.encode())
        h.update(b"\x00" if arr is None else arr.tobytes())
    return h.hexdigest()


def dataset_id(ticks, *, tz_interpretation: str, source_sha256=None,
               schema_version: str = DATASET_SCHEMA_VERSION) -> str:
    n = len(ticks)
    body = {
        "instrument": ticks.instrument,
        "contract": ticks.contract,
        "tick_size": float(ticks.tick_size),
        "schema_version": schema_version,
        "row_count": int(n),
        "ts_min_ns": int(ticks.ts_ns[0]) if n else None,
        "ts_max_ns": int(ticks.ts_ns[-1]) if n else None,
        "tz_interpretation": tz_interpretation,
        "content_sha256": content_sha256_of_ticks(ticks),
        "source_sha256": source_sha256,
    }
    return _hash(body)


def _read_bridge_file(name: str) -> bytes:
    if os.path.isabs(name):
        path = name
    elif name.startswith("indicators/"):
        path = os.path.join(_BRIDGE_DIR, name)
    elif name in _KERNEL_FILE.values():
        path = os.path.join(_BRIDGE_DIR, "indicators", name)
    else:
        path = os.path.join(_BRIDGE_DIR, name)
    with open(path, "rb") as fh:
        return fh.read()


def kernel_sources(indicator: str) -> dict:
    if indicator not in _KERNEL_FILE:
        raise KeyError(f"indicador desconocido: {indicator}")
    kernel_file = _KERNEL_FILE[indicator]
    out = {kernel_file: _read_bridge_file(kernel_file)}
    for dep in _KERNEL_DEPS[indicator]:
        out[dep] = _read_bridge_file(dep)
    return out


def kernel_id(indicator: str, sources: dict | None = None) -> str:
    sources = kernel_sources(indicator) if sources is None else sources
    body = {
        "indicator": indicator,
        "sources": {name: sha256_bytes(data) for name, data in sources.items()},
        "observation_schema_version": OBSERVATION_SCHEMA_VERSION,
        "event_schema_version": EVENT_SCHEMA_VERSION,
        "zone_schema_version": ZONE_SCHEMA_VERSION,
    }
    return _hash(body)


def _kernel_module(indicator: str):
    from .indicators import REGISTRY
    if indicator not in REGISTRY:
        raise KeyError(f"indicador desconocido: {indicator}")
    return REGISTRY[indicator]


def _coerce(value, ptype: str):
    if ptype == "int":
        return int(value)
    if ptype == "float":
        return float(value)
    if ptype == "bool":
        return bool(value)
    return str(value)


ANALYTIC_CLASSES = ("recompute", "lifecycle", "offline", "instrument")


def canonicalize_params(indicator: str, params: dict) -> dict:
    mod = _kernel_module(indicator)
    spec = mod.PARAM_SPEC
    defaults = mod.DEFAULTS
    unknown = set(params) - set(spec)
    if unknown:
        raise KeyError(f"{indicator}: parámetros inexistentes {sorted(unknown)}")
    for key in params:
        cls = spec[key].get("class")
        if cls not in ANALYTIC_CLASSES:
            raise ValueError(
                f"{indicator}: '{key}' es class={cls}; no entra a una "
                "configuración analítica (identidad)"
            )
    out = {}
    for key, meta in spec.items():
        if meta.get("class") not in ANALYTIC_CLASSES:
            continue
        value = params[key] if key in params else defaults.get(key, meta.get("default"))
        out[key] = _coerce(value, meta.get("type", "str"))
    return out


def config_id(indicator: str, params: dict, bar_key: str, chart_tz: str,
              kernel_id_value: str) -> str:
    return _hash({
        "indicator": indicator,
        "params": canonicalize_params(indicator, params),
        "bar_key": bar_key,
        "chart_tz": chart_tz,
        "kernel_id": kernel_id_value,
    })


def _typed_ok(value, ptype: str):
    if ptype == "int":
        if isinstance(value, bool):
            return False, None
        if isinstance(value, int):
            return True, int(value)
        if isinstance(value, float):
            return ((True, int(value)) if value == int(value) else (False, None))
        if isinstance(value, str):
            try:
                return True, int(value)
            except ValueError:
                return False, None
        return False, None
    if ptype == "float":
        if isinstance(value, bool):
            return False, None
        if isinstance(value, (int, float)):
            return True, float(value)
        if isinstance(value, str):
            try:
                return True, float(value)
            except ValueError:
                return False, None
        return False, None
    if ptype == "bool":
        if isinstance(value, bool):
            return True, value
        if value in (0, 1):
            return True, bool(value)
        return False, None
    return True, str(value)


def validate_params(indicator: str, params: dict) -> list:
    mod = _kernel_module(indicator)
    spec = mod.PARAM_SPEC
    errors = []
    coerced = {}
    for key, value in params.items():
        if key not in spec:
            errors.append(f"'{key}': parámetro inexistente en {indicator}")
            continue
        meta = spec[key]
        cls = meta.get("class")
        if cls not in ANALYTIC_CLASSES:
            reason = meta.get("reason", "")
            errors.append(
                f"'{key}': class={cls} no optimizable" +
                (f" ({reason})" if reason else "")
            )
            continue
        ptype = meta.get("type", "str")
        ok, cv = _typed_ok(value, ptype)
        if not ok:
            errors.append(
                f"'{key}': tipo inválido (esperado {ptype}, dado {value!r})"
            )
            continue
        coerced[key] = cv
        choices = meta.get("choices")
        if choices is not None and cv not in choices:
            errors.append(f"'{key}': '{cv}' no está en choices {choices}")
        if "min" in meta and cv < meta["min"]:
            errors.append(f"'{key}': {cv} < min {meta['min']}")
        if "max" in meta and cv > meta["max"]:
            errors.append(f"'{key}': {cv} > max {meta['max']}")
    for key, meta in spec.items():
        floor_key = meta.get("requires_covered_by")
        if floor_key is None or key not in coerced:
            continue
        floor_val = coerced.get(floor_key, mod.DEFAULTS.get(floor_key))
        if floor_val is not None and coerced[key] < floor_val:
            errors.append(
                f"'{key}'={coerced[key]}: filtro offline no cubierto por "
                f"'{floor_key}'={floor_val}"
            )
    return errors


def run_id(dataset_id_value: str, config_id_value: str, start_utc, end_utc,
           engine_version: str = ENGINE_VERSION) -> str:
    return _hash({
        "dataset_id": dataset_id_value,
        "config_id": config_id_value,
        "start_utc": start_utc,
        "end_utc": end_utc,
        "engine_version": engine_version,
    })


def zone_key(run_id_value: str, zone_id, created_event_seq, created_ms,
             lower_tick, upper_tick, side) -> str:
    return _hash({
        "run_id": run_id_value,
        "zone_id": str(zone_id),
        "created_event_seq": int(created_event_seq),
        "created_ms": int(created_ms),
        "lower_tick": int(lower_tick),
        "upper_tick": int(upper_tick),
        "side": str(side),
    }, n=24)

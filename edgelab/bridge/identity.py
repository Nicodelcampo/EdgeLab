"""Identidades canónicas e inmutables del bridge (F6.1).

Nada del store se sostiene sin identidades estables y content-addressed. Una
RUTA no es identidad: la ruta puede existir mañana con otro contenido. Acá todo
se deriva de contenido + semántica, no de nombres de archivo.

Jerarquía:
  dataset_id  = f(instrument, contract, tick_size, schema, row_count, rango UTC,
                  interpretación de tz, sha256 del CONTENIDO, sha256 de la fuente)
  kernel_id   = f(indicator, sha256 del archivo del kernel, sha256 de sus
                  dependencias semánticas (common/bars/sessions), versiones de
                  schema de observations/events/zones)
  config_id   = f(params con TODOS los defaults materializados y tipados,
                  bar_spec, chart_tz, kernel_id)  — {"min_gap_ticks":5} y la
                  versión con todos los defaults explícitos dan el MISMO id
  run_id      = f(dataset_id, config_id, rango UTC, engine_version)
  zone_key    = f(run_id, zone_id interno, created_event_seq, created_ms,
                  lower_tick, upper_tick, side)  — global; dos configs o dos
                  indicadores jamás colisionan.

Regla de determinismo: los mismos inputs SIEMPRE dan el mismo id, entre
procesos y máquinas (sin `Date`/`random`/orden de dict/rutas absolutas).
"""
from __future__ import annotations

import hashlib
import json
import os

# --- Versiones de schema (bump manual si cambia el formato de un artefacto) ---
ENGINE_VERSION = "1"
DATASET_SCHEMA_VERSION = "canonical_tick_v1"   # coincide con el manifest F2
OBSERVATION_SCHEMA_VERSION = "1"
EVENT_SCHEMA_VERSION = "1"
ZONE_SCHEMA_VERSION = "1"

ID_LEN = 16   # 64 bits en hex: sin colisiones a escala real del store

_BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))

# Dependencias semánticas por kernel: cambiar el bar builder (bars.py) o el
# calendario (sessions.py) cambia el kernel_id de TODOS los que dependen de él.
_COMMON_DEPS = ("common.py", "bars.py")        # helpers + bar builder + footprint
_KERNEL_FILE = {
    "Gaps2": "gaps2.py",
    "VolTicksPOC2": "voltickspoc2.py",
    "BigTrap2": "bigtrap2.py",
    "HFTZones2": "hftzones2.py",
    "aVolCellPOI2": "avolcellpoi2.py",
}
_KERNEL_DEPS = {
    "Gaps2": _COMMON_DEPS,
    "VolTicksPOC2": _COMMON_DEPS,
    "BigTrap2": _COMMON_DEPS,
    "HFTZones2": _COMMON_DEPS + ("sessions.py",),
    "aVolCellPOI2": _COMMON_DEPS + ("sessions.py",),
}


# --------------------------------------------------------------------------- #
# Serialización canónica
# --------------------------------------------------------------------------- #
def canonical_json(obj) -> str:
    """JSON determinista: claves ordenadas, sin espacios, floats vía el repr
    canónico de Python (json ya lo hace: 3.0->'3.0', 5.0->'5.0')."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def _hash(obj, n: int = ID_LEN) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()[:n]


def sha256_bytes(*blobs: bytes) -> str:
    h = hashlib.sha256()
    for b in blobs:
        h.update(b)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# dataset_id
# --------------------------------------------------------------------------- #
def content_sha256_of_ticks(ticks) -> str:
    """sha256 del CONTENIDO de la serie (arrays crudos), no de la ruta.
    Incluye quotes; None -> se marca ausente para no confundir con vacío."""
    h = hashlib.sha256()
    for name in ("ts_ns", "price_ticks", "volume", "sequence"):
        arr = getattr(ticks, name)
        h.update(name.encode())
        h.update(arr.tobytes())
    for name in ("bid_ticks", "ask_ticks"):
        arr = getattr(ticks, name)
        h.update(name.encode())
        h.update(b"\x00" if arr is None else arr.tobytes())
    return h.hexdigest()


def dataset_id(ticks, *, tz_interpretation: str, source_sha256=None,
               schema_version: str = DATASET_SCHEMA_VERSION) -> str:
    """Identidad de un dataset = slice canónico exacto de ticks."""
    n = len(ticks)
    body = dict(
        instrument=ticks.instrument, contract=ticks.contract,
        tick_size=float(ticks.tick_size), schema_version=schema_version,
        row_count=int(n),
        ts_min_ns=int(ticks.ts_ns[0]) if n else None,
        ts_max_ns=int(ticks.ts_ns[-1]) if n else None,
        tz_interpretation=tz_interpretation,
        content_sha256=content_sha256_of_ticks(ticks),
        source_sha256=source_sha256)
    return _hash(body)


# --------------------------------------------------------------------------- #
# kernel_id
# --------------------------------------------------------------------------- #
def _read_bridge_file(name: str) -> bytes:
    path = name if os.path.isabs(name) else os.path.join(_BRIDGE_DIR, name)
    if name.startswith("indicators/") or name in _KERNEL_FILE.values():
        # los kernels viven en el subpaquete indicators/
        base = name if name.startswith("indicators/") else os.path.join("indicators", name)
        path = os.path.join(_BRIDGE_DIR, base)
    with open(path, "rb") as fh:
        return fh.read()


def kernel_sources(indicator: str) -> dict:
    """{nombre: bytes} del kernel + sus dependencias semánticas. Base de la
    identidad de código; permite inyectar contenido mutado en tests."""
    if indicator not in _KERNEL_FILE:
        raise KeyError(f"indicador desconocido: {indicator}")
    out = {}
    kf = _KERNEL_FILE[indicator]
    out[kf] = _read_bridge_file(os.path.join("indicators", kf))
    for dep in _KERNEL_DEPS[indicator]:
        out[dep] = _read_bridge_file(dep)
    return out


def kernel_id(indicator: str, sources: dict | None = None) -> str:
    """Identidad del código del kernel. `sources` (nombre->bytes) permite
    testear que mutar cualquier dependencia cambia el id."""
    if sources is None:
        sources = kernel_sources(indicator)
    shas = {name: sha256_bytes(data) for name, data in sources.items()}
    body = dict(
        indicator=indicator, sources=shas,
        observation_schema_version=OBSERVATION_SCHEMA_VERSION,
        event_schema_version=EVENT_SCHEMA_VERSION,
        zone_schema_version=ZONE_SCHEMA_VERSION)
    return _hash(body)


# --------------------------------------------------------------------------- #
# config_id
# --------------------------------------------------------------------------- #
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


# Clases de parámetro que participan de la IDENTIDAD (afectan el cómputo o su
# proyección analítica). visual/forbidden jamás entran a config_id.
ANALYTIC_CLASSES = ("recompute", "lifecycle", "offline", "instrument")


def canonicalize_params(indicator: str, params: dict) -> dict:
    """Materializa TODOS los defaults analíticos y tipa cada valor según
    PARAM_SPEC. {"min_gap_ticks":5} -> dict completo con min_gap_ticks=5 (==
    default) -> idéntico al dict con todos los defaults explícitos. Rechaza
    claves inexistentes o de clase visual/forbidden (no son analíticas)."""
    mod = _kernel_module(indicator)
    spec = getattr(mod, "PARAM_SPEC")
    defaults = getattr(mod, "DEFAULTS")
    unknown = set(params) - set(spec)
    if unknown:
        raise KeyError(f"{indicator}: parámetros inexistentes {sorted(unknown)}")
    for key in params:
        cls = spec[key].get("class")
        if cls not in ANALYTIC_CLASSES:
            raise ValueError(f"{indicator}: '{key}' es class={cls}; no entra a "
                             f"una configuración analítica (identidad)")
    out = {}
    for key, meta in spec.items():
        if meta.get("class") not in ANALYTIC_CLASSES:
            continue
        ptype = meta.get("type", "str")
        if key in params:
            out[key] = _coerce(params[key], ptype)
        else:
            out[key] = _coerce(defaults[key], ptype) if key in defaults else meta.get("default")
    return out


def config_id(indicator: str, params: dict, bar_key: str, chart_tz: str,
              kernel_id_value: str) -> str:
    body = dict(
        indicator=indicator, params=canonicalize_params(indicator, params),
        bar_key=bar_key, chart_tz=chart_tz, kernel_id=kernel_id_value)
    return _hash(body)


def _typed_ok(value, ptype: str):
    """(ok, coerced|None). Rechaza tipos incompatibles sin coerción silenciosa
    con pérdida (p.ej. 3.5 para un int)."""
    if ptype == "int":
        if isinstance(value, bool):
            return False, None
        if isinstance(value, int):
            return True, int(value)
        if isinstance(value, float):
            return (True, int(value)) if value == int(value) else (False, None)
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
    return (True, str(value))   # str


def validate_params(indicator: str, params: dict) -> list:
    """Valida un param set contra PARAM_SPEC. Devuelve lista de errores (vacía =
    válido). Rechaza los 5 casos: inexistente, tipo incorrecto, fuera de rango/
    choice, clase visual/forbidden en grilla analítica, y filtro offline cuyo
    piso de export no cubre el valor pedido (requires_covered_by)."""
    mod = _kernel_module(indicator)
    spec = getattr(mod, "PARAM_SPEC")
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
            errors.append(f"'{key}': class={cls} no optimizable"
                          + (f" ({reason})" if reason else ""))
            continue
        ptype = meta.get("type", "str")
        ok, cv = _typed_ok(value, ptype)
        if not ok:
            errors.append(f"'{key}': tipo inválido (esperado {ptype}, dado {value!r})")
            continue
        coerced[key] = cv
        choices = meta.get("choices")
        if choices is not None and cv not in choices:
            errors.append(f"'{key}': '{cv}' no está en choices {choices}")
        if "min" in meta and cv < meta["min"]:
            errors.append(f"'{key}': {cv} < min {meta['min']}")
        if "max" in meta and cv > meta["max"]:
            errors.append(f"'{key}': {cv} > max {meta['max']}")
    # cobertura de filtros offline por el piso de export del mismo param set
    for key, meta in spec.items():
        floor_key = meta.get("requires_covered_by")
        if floor_key is None or key not in coerced:
            continue
        floor_val = coerced.get(floor_key)
        if floor_val is None:
            defaults = getattr(mod, "DEFAULTS")
            floor_val = defaults.get(floor_key)
        if floor_val is not None and coerced[key] < floor_val:
            errors.append(
                f"'{key}'={coerced[key]}: filtro offline no cubierto por el piso "
                f"de export '{floor_key}'={floor_val} (exige {key} >= {floor_key})")
    return errors


# --------------------------------------------------------------------------- #
# run_id / zone_key
# --------------------------------------------------------------------------- #
def run_id(dataset_id_value: str, config_id_value: str, start_utc, end_utc,
           engine_version: str = ENGINE_VERSION) -> str:
    body = dict(dataset_id=dataset_id_value, config_id=config_id_value,
                start_utc=start_utc, end_utc=end_utc, engine_version=engine_version)
    return _hash(body)


def zone_key(run_id_value: str, zone_id, created_event_seq, created_ms,
             lower_tick, upper_tick, side) -> str:
    """Clave global de zona: incluye run_id, así que dos configs o dos
    indicadores jamás colisionan aunque compartan geometría."""
    body = dict(run_id=run_id_value, zone_id=str(zone_id),
                created_event_seq=int(created_event_seq),
                created_ms=int(created_ms), lower_tick=int(lower_tick),
                upper_tick=int(upper_tick), side=str(side))
    return _hash(body, n=24)

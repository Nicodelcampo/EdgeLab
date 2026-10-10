"""Reader streaming + auditor P0 del formato NT8 `.Last.txt`.

Parseo por línea a registros tipados con precios en TICKS ENTEROS. Reglas P0:
- FAIL (Nt8ContractError): estructura ≠ 5 campos, timestamp mal formado /
  fracción ≠ 7 díg, precio no alineado a tick, quote cruzada (ask<bid),
  volumen<=0, timestamp no monotónico.
- CONTADO (no falla): last fuera de [bid,ask]; ts duplicados.
- WARN: resolución limitada / quantum inconsistente (mezcla de grillas).

NO convierte a UTC (eso es F2, con verificación empírica de timezone).
`ts_local_ns` es el wall-clock LOCAL declarado, como int64 ns.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from functools import reduce
from math import gcd
from typing import Iterable

import numpy as np


class Nt8ContractError(ValueError):
    """Violación dura del contrato P0."""


@dataclass(frozen=True)
class Nt8Tick:
    ts_local_ns: int          # wall-clock LOCAL (declared_tz), int64 ns
    last_ticks: int
    bid_ticks: int
    ask_ticks: int
    volume: int
    aggressor: str            # "buy" | "sell" | "unclassified"
    frac_units: int           # sub-segundo en unidades de 100 ns
    last_outside: bool
    line: int


@dataclass
class Nt8QualityReport:
    n: int
    contract: str
    first_ts_ns: int
    last_ts_ns: int
    n_duplicate_ts: int
    quantum_units: int        # grilla temporal efectiva (100-ns units); 0 si no medible
    quantum_ms: float
    resolution_limited: bool
    inconsistent_resolution: bool
    frac_zero_count: int
    aggressor: dict
    last_outside_spread: int
    warnings: list = field(default_factory=list)


def _to_ticks(price_str: str, tick_size: float, tol: float, line: int, name: str) -> int:
    px = float(price_str)
    q = px / tick_size
    r = round(q)
    if abs(q - r) > tol * max(abs(r), 1.0):
        raise Nt8ContractError(f"línea {line}: {name}={price_str} no alineado a tick_size {tick_size}")
    return int(r)


def parse_line(line: str, contract, i: int = 0) -> Nt8Tick:
    parts = line.split(contract.field_sep)
    if len(parts) != len(contract.columns):
        raise Nt8ContractError(f"línea {i}: esperados {len(contract.columns)} campos, hay {len(parts)}")
    ts_tok, last_s, bid_s, ask_s, vol_s = parts
    toks = ts_tok.split()
    if len(toks) != 3:
        raise Nt8ContractError(f"línea {i}: timestamp mal formado: {ts_tok!r}")
    d, hms, frac = toks
    if len(d) != 8 or len(hms) != 6 or len(frac) != contract.frac_digits or not (d + hms + frac).isdigit():
        raise Nt8ContractError(
            f"línea {i}: ts inválido (esperado {contract.ts_format}): {ts_tok!r}")
    frac_units = int(frac)
    try:
        iso = f"{d[0:4]}-{d[4:6]}-{d[6:8]}T{hms[0:2]}:{hms[2:4]}:{hms[4:6]}"
        base_ns = int(np.datetime64(iso, "ns").astype(np.int64))
    except Exception as e:  # fecha/hora fuera de rango
        raise Nt8ContractError(f"línea {i}: fecha/hora inválida {ts_tok!r}: {e}")
    ts_ns = base_ns + frac_units * contract.frac_unit_ns

    try:
        vol = int(vol_s)
    except ValueError:
        raise Nt8ContractError(f"línea {i}: volumen no entero: {vol_s!r}")
    if vol <= 0:
        raise Nt8ContractError(f"línea {i}: volumen<=0 ({vol})")

    tk, tol = contract.instrument.tick_size, contract.price_align_tol
    last_t = _to_ticks(last_s, tk, tol, i, "last")
    bid_t = _to_ticks(bid_s, tk, tol, i, "bid")
    ask_t = _to_ticks(ask_s, tk, tol, i, "ask")
    if ask_t < bid_t:
        raise Nt8ContractError(f"línea {i}: quote cruzada ask<bid ({ask_s}<{bid_s})")

    if last_t == ask_t:
        aggr = "buy"
    elif last_t == bid_t:
        aggr = "sell"
    else:
        aggr = "unclassified"
    last_outside = not (bid_t <= last_t <= ask_t)
    return Nt8Tick(ts_ns, last_t, bid_t, ask_t, vol, aggr, frac_units, last_outside, i)


def iter_records(lines: Iterable[str], contract) -> Iterable[Nt8Tick]:
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        yield parse_line(s, contract, i)


def _resolution(fracs):
    nz = [f for f in fracs if f > 0]
    if not nz:
        return 0, False, False
    quantum = reduce(gcd, nz)
    cnt = Counter(nz)
    top = [v for v, _ in cnt.most_common(2)]
    bulk = reduce(gcd, top) if top else quantum
    inconsistent = bool(quantum > 0 and bulk > 0 and quantum < bulk)
    return quantum, quantum > 1, inconsistent


def audit(lines: Iterable[str], contract):
    """Consume el stream, valida P0 y devuelve (records, Nt8QualityReport)."""
    recs, fracs = [], []
    last_ts = None
    ndup = zero = outside = 0
    agg = {"buy": 0, "sell": 0, "unclassified": 0}
    for r in iter_records(lines, contract):
        if last_ts is not None:
            if r.ts_local_ns < last_ts:
                raise Nt8ContractError(f"línea {r.line}: timestamp no monotónico")
            if r.ts_local_ns == last_ts:
                ndup += 1
        last_ts = r.ts_local_ns
        recs.append(r)
        if r.frac_units == 0:
            zero += 1
        else:
            fracs.append(r.frac_units)
        outside += int(r.last_outside)
        agg[r.aggressor] += 1

    quantum, res_lim, inconsistent = _resolution(fracs)
    warnings = []
    if inconsistent:
        warnings.append(f"quantum inconsistente: grilla fina {quantum * contract.frac_unit_ns / 1e6:.4f}ms "
                        f"mezclada con una grilla más gruesa (mezcla de resoluciones)")
    return recs, Nt8QualityReport(
        n=len(recs), contract=contract.instrument.symbol,
        first_ts_ns=recs[0].ts_local_ns if recs else 0,
        last_ts_ns=recs[-1].ts_local_ns if recs else 0,
        n_duplicate_ts=ndup,
        quantum_units=quantum, quantum_ms=quantum * contract.frac_unit_ns / 1e6,
        resolution_limited=res_lim, inconsistent_resolution=inconsistent,
        frac_zero_count=zero, aggressor=agg, last_outside_spread=outside, warnings=warnings)

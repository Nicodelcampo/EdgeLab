"""Construye el `contract_regime_manifest_v1` (edgelab/data/contract_regime.py)
para el root NQ a partir de volumen diario real por contrato.

Separa deliberadamente la parte cara (leer 5 parquets de ticks y agregar
volumen por trade_date) de la parte barata y testeable (armar `contracts`,
`daily_volumes` y `calendar_trade_dates` en el formato que exige
`build_contract_regime`). Esta última es la que este modulo prueba con
fixtures sinteticos -- la primera corre en Kaggle, aparte, con autorizacion
explicita.

`complete_session=True` se asigna a TODO trade_date con al menos un tick
observado dentro de la cobertura declarada del contrato -- no hay todavia una
auditoria mas fina de integridad de sesion (ej. conteo esperado de ticks).
Es una simplificacion deliberada y declarada, no oculta: un trade_date sin
ticks queda simplemente ausente de `daily_volumes`, y `build_contract_regime`
ya trata eso como "SOURCE_INCOMPLETE" -- vuelve inelegible el dia siguiente,
no elige otro contrato en silencio.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_CONTRACT_RE = re.compile(r"^(?P<root>[A-Z0-9]+)[ _](?P<mm>\d{2})-(?P<yy>\d{2})$")


def parse_contract_label(label: str) -> dict[str, Any]:
    """'NQ 09-25' o 'NQ_09-25' -> {root, contract, expiry_ordinal}."""
    m = _CONTRACT_RE.match(label.strip())
    if not m:
        raise ValueError(f"contract label no reconocido: {label!r}")
    root = m.group("root")
    mm = int(m.group("mm"))
    yy = int(m.group("yy"))
    if not (1 <= mm <= 12):
        raise ValueError(f"mes invalido en {label!r}")
    year = 2000 + yy
    return {"root": root, "contract": f"{root} {mm:02d}-{yy:02d}",
            "expiry_ordinal": year * 100 + mm}


def contract_metadata_from_daily(
    contract_label: str, trade_dates_with_volume: Sequence[int],
) -> dict[str, Any]:
    """Deriva first/last_trade_date de las fechas realmente observadas."""
    if not trade_dates_with_volume:
        raise ValueError(f"{contract_label}: sin trade_dates observadas")
    parsed = parse_contract_label(contract_label)
    parsed["first_trade_date"] = int(min(trade_dates_with_volume))
    parsed["last_trade_date"] = int(max(trade_dates_with_volume))
    return parsed


def daily_volume_rows_from_aggregate(
    root: str, contract: str, volume_by_trade_date: Mapping[int, float],
) -> list[dict[str, Any]]:
    """volume_by_trade_date: {YYYYMMDD: volumen_sumado_del_dia}.

    Cada trade_date presente en el mapping se declara complete_session=True
    (ver docstring del modulo). Un trade_date ausente del mapping NO genera
    fila -- queda ausente, y build_contract_regime lo trata como cobertura
    incompleta en vez de elegir otro contrato en silencio.
    """
    rows = []
    for trade_date, volume in sorted(volume_by_trade_date.items()):
        rows.append({
            "root": root, "contract": contract, "trade_date": int(trade_date),
            "volume": float(volume), "complete_session": True,
        })
    return rows


def build_nq_manifest_inputs(
    per_contract_volume: Mapping[str, Mapping[int, float]],
    source_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Empaqueta `contracts`, `daily_volumes`, `calendar_trade_dates`,
    `source_identity` listos para `build_contract_regime(**esto)`.

    per_contract_volume: {"NQ 03-26": {20260202: 12345.0, ...}, "NQ 06-26": {...}, ...}
    """
    if not per_contract_volume:
        raise ValueError("per_contract_volume vacio")
    contracts = []
    daily_volumes = []
    all_dates: set[int] = set()
    for label, by_date in per_contract_volume.items():
        meta = contract_metadata_from_daily(label, list(by_date.keys()))
        contracts.append(meta)
        rows = daily_volume_rows_from_aggregate(meta["root"], meta["contract"], by_date)
        daily_volumes.extend(rows)
        all_dates.update(by_date.keys())
    calendar_trade_dates = sorted(all_dates)
    return {
        "contracts": contracts,
        "daily_volumes": daily_volumes,
        "calendar_trade_dates": calendar_trade_dates,
        "source_identity": dict(source_identity),
    }

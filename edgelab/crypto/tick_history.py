"""tickSize vigente por simbolo y fecha, desde anuncios oficiales de Binance.

Resuelve el bloqueante #1 del contrato causal: `exchangeInfo` sólo expone el
valor VIGENTE, y el tick cambia. Medido: SOLUSDT paso de 0.001 a 0.01 el
2024-10-14, asi que usar el vigente sobre datos de 2024-03 da 85% de precios
"fuera de tick" que no son ninguna anomalia.

Falla cerrado por diseno: un simbolo o una fecha sin cobertura documentada NO
cae al valor vigente. Devolver el vigente ante la duda es exactamente el defecto
que este modulo existe para impedir.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

_SPEC = Path(__file__).resolve().parents[2] / "specs" / "binance_tick_size_history.json"


class TickHistoryUnavailable(LookupError):
    """No hay metadata historica documentada para ese simbolo/fecha."""


def load_history(path: str | Path | None = None) -> dict[str, Any]:
    return json.loads(Path(path or _SPEC).read_text(encoding="utf-8"))


def tick_size_on(symbol: str, date_utc: str, *, history: dict | None = None) -> tuple[Decimal, dict]:
    """tickSize vigente para `symbol` en `date_utc` (YYYY-MM-DD).

    Devuelve `(tick, procedencia)`. Levanta `TickHistoryUnavailable` si el
    simbolo no esta cubierto o si no hay anuncio que permita datar el valor.
    """
    h = history or load_history()
    sym = h["symbols"].get(symbol.upper())
    if sym is None:
        raise TickHistoryUnavailable(
            f"{symbol}: sin metadata historica documentada. No se cae al valor vigente.")
    changes = sorted(sym.get("changes", []), key=lambda c: c["effective_utc"])
    if not changes:
        raise TickHistoryUnavailable(
            f"{symbol}: no se encontro ningun anuncio de cambio de tick. "
            "Ausencia de evidencia no es evidencia de ausencia: declarar el valor "
            "explicitamente o aprobar un contrato OBSERVED_PRICE_GRID.")
    for c in changes:
        if date_utc < c["effective_utc"][:10]:
            return Decimal(c["tick_before"]), {
                "value": c["tick_before"], "basis": "anterior al cambio",
                "effective_utc": c["effective_utc"], "source_url": c["source_url"],
                "status": "OFFICIAL_ANNOUNCEMENT"}
    last = changes[-1]
    return Decimal(last["tick_after"]), {
        "value": last["tick_after"], "basis": "posterior al ultimo cambio conocido",
        "effective_utc": last["effective_utc"], "source_url": last["source_url"],
        "status": "OFFICIAL_ANNOUNCEMENT"}

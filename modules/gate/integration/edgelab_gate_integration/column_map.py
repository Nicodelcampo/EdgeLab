"""
Mapeo de columnas export EdgeLab / NT8 → schema GATE v1.

Basado en commits foundation/f0b (BigTrap2 v1.1 context keys) y oráculos HFT.
Acepta alias; normaliza a: event_id, t0, session_id, symbol, ancho_ticks.
"""

from __future__ import annotations

import pandas as pd

# alias → canonical GATE event column
EVENT_ALIASES: dict[str, tuple[str, ...]] = {
    "event_id": (
        "event_id",
        "EventId",
        "trap_id",
        "zone_id",
        "id",
        "uid",
    ),
    "t0": (
        "t0",
        "t_start",
        "T0",
        "bucket_start",
        "zone_start",
        "StartTime",
        "time_start",
        "ts_start",
        "fill_time",  # last resort: fill as decision time if only fill exported
    ),
    "session_id": (
        "session_id",
        "trade_date",
        "TradeDate",
        "TradingDay",
        "session",
        "Session",
        "dia",
    ),
    "symbol": (
        "symbol",
        "Symbol",
        "instrument",
        "Instrument",
    ),
    "ancho_ticks": (
        "ancho_ticks",
        "width_ticks",
        "WidthTicks",
        "zone_width_ticks",
        "ticks_width",
        "ancho",
    ),
}

BAR_TIME_ALIASES = ("time", "timestamp", "ts", "datetime", "bar_time", "Time")


def _first_present(df: pd.DataFrame, names: tuple[str, ...]) -> str | None:
    for n in names:
        if n in df.columns:
            return n
    # case-insensitive
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None


def normalize_events(raw: pd.DataFrame, default_symbol: str = "ES") -> pd.DataFrame:
    """
    Convierte un export EdgeLab heterogéneo al schema mínimo de eventos GATE.
    Fail-closed: lanza si faltan event_id o t0 o session_id.
    """
    mapping = {}
    missing = []
    for canon, aliases in EVENT_ALIASES.items():
        col = _first_present(raw, aliases)
        if col is None:
            if canon == "symbol":
                continue
            if canon == "ancho_ticks":
                continue  # optional for labeling; required for Paso 2 corr
            missing.append(canon)
        else:
            mapping[canon] = col

    if missing:
        raise ValueError(
            "EdgeLab export missing required columns (after alias map): "
            + ", ".join(missing)
            + f". Present: {list(raw.columns)}"
        )

    out = pd.DataFrame()
    out["event_id"] = raw[mapping["event_id"]].astype(str)
    out["t0"] = pd.to_datetime(raw[mapping["t0"]], utc=True, errors="coerce")
    out["session_id"] = raw[mapping["session_id"]].astype(str)
    if "symbol" in mapping:
        out["symbol"] = raw[mapping["symbol"]].astype(str)
    else:
        out["symbol"] = default_symbol
    if "ancho_ticks" in mapping:
        out["ancho_ticks"] = pd.to_numeric(raw[mapping["ancho_ticks"]], errors="coerce")

    if out["event_id"].duplicated().any():
        # make unique preserving order
        out["event_id"] = out["event_id"] + "_" + out.groupby("event_id").cumcount().astype(str)

    if out["t0"].isna().any():
        n = int(out["t0"].isna().sum())
        raise ValueError(f"{n} events have unparseable t0")

    return out


def normalize_bar_time(bars: pd.DataFrame) -> pd.DataFrame:
    col = _first_present(bars, BAR_TIME_ALIASES)
    if col is None:
        raise ValueError(f"bars missing time column; have {list(bars.columns)}")
    out = bars.copy()
    if col != "time":
        out = out.rename(columns={col: "time"})
    out["time"] = pd.to_datetime(out["time"], utc=True, errors="coerce")
    return out.sort_values("time").reset_index(drop=True)

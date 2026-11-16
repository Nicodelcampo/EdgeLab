"""CLI para ejecutar los Expert Advisors de QuantLab MT5 traducidos sobre datos pre-holdout."""
from __future__ import annotations

import argparse
from typing import Dict, Optional

import pandas as pd

try:
    from .contracts import QlbBasketConfig, SessionOpenMomentumConfig
    from .indicators import load_ohlc_data
    from .qlb_k_xauusd_basket import correr_qlb_basket, correr_slot_qlb
    from .session_open_momentum import correr_session_open_momentum
except ImportError:  # pragma: no cover
    from contracts import QlbBasketConfig, SessionOpenMomentumConfig
    from indicators import load_ohlc_data
    from qlb_k_xauusd_basket import correr_qlb_basket, correr_slot_qlb
    from session_open_momentum import correr_session_open_momentum


def correr_modulo_quantlab(
    tag: str,
    df_ohlc: pd.DataFrame,
    instrument: str = "XAUUSD",
) -> pd.DataFrame:
    """Despacha por nombre (`SOM`, `QLB_S0`, `QLB_S1`, `QLB_S2`, `QLB_BASKET`)."""
    key = tag.strip().upper()
    if key == "SOM":
        return correr_session_open_momentum(df_ohlc, instrument=instrument)
    if key == "QLB_S0":
        return correr_slot_qlb(df_ohlc, slot_id=0, instrument=instrument)
    if key == "QLB_S1":
        return correr_slot_qlb(df_ohlc, slot_id=1, instrument=instrument)
    if key == "QLB_S2":
        return correr_slot_qlb(df_ohlc, slot_id=2, instrument=instrument)
    if key == "QLB_BASKET":
        return correr_qlb_basket(df_ohlc, instrument=instrument)
    raise KeyError(f"Modulo desconocido: {tag!r}")


def correr_todos_quantlab(
    df_ohlc: pd.DataFrame,
    instrument: str = "XAUUSD",
    som_config: Optional[SessionOpenMomentumConfig] = None,
    qlb_config: Optional[QlbBasketConfig] = None,
) -> Dict[str, object]:
    """Ejecuta SOM y los 3 slots de QLB generando resumen consolidado y tablas por modulo."""
    por_modulo = {
        "SOM": correr_session_open_momentum(df_ohlc, config=som_config, instrument=instrument),
        "QLB_S0": correr_slot_qlb(df_ohlc, slot_id=0, config=qlb_config, instrument=instrument),
        "QLB_S1": correr_slot_qlb(df_ohlc, slot_id=1, config=qlb_config, instrument=instrument),
        "QLB_S2": correr_slot_qlb(df_ohlc, slot_id=2, config=qlb_config, instrument=instrument),
        "QLB_BASKET": correr_qlb_basket(df_ohlc, config=qlb_config, instrument=instrument),
    }
    rows = []
    for tag, df in por_modulo.items():
        n = len(df)
        wins = int((df["pnl_usd"] > 0).sum()) if n else 0
        net = float(df["pnl_usd"].sum()) if n else 0.0
        rows.append({
            "module": tag,
            "trades": n,
            "win_rate_pct": round(wins / n * 100.0, 1) if n else 0.0,
            "net_pnl_usd": round(net, 2),
        })
    return {"resumen_df": pd.DataFrame(rows), "por_modulo": por_modulo}


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Ejecutar EAs QuantLab MT5 traducidos a Python.")
    ap.add_argument("--data", required=True, help="Ruta a CSV/Parquet/JSON OHLCV pre-holdout.")
    ap.add_argument("--instrument", default="XAUUSD", help="EURUSD, XAUUSD, USATECH, USA500.")
    ap.add_argument("--module", default="ALL", help="SOM, QLB_S0, QLB_S1, QLB_S2, QLB_BASKET, o ALL.")
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default="2026-10-01")
    args = ap.parse_args(argv)

    df = load_ohlc_data(args.data, start=args.start, end=args.end)
    if args.module.upper() == "ALL":
        res = correr_todos_quantlab(df, instrument=args.instrument)
        print(res["resumen_df"].to_string(index=False))
    else:
        out = correr_modulo_quantlab(args.module, df, instrument=args.instrument)
        print(f"{args.module}: {len(out)} trades | Net USD: {out['pnl_usd'].sum():,.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

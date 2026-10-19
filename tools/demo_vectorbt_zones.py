#!/usr/bin/env python3
"""Demo end-to-end (F8): estrategia vectorbt que combina zonas de 2+ indicadores
del store, materializadas as-of, SIN importar ningún módulo de kernel.

El punto de la fábrica de features: EdgeLab consume `store` + `features`
(coordenadas verificadas) y arma señales; jamás ejecuta indicadores. Este archivo
importa `edgelab.bridge.features` y NADA de `edgelab.bridge.indicators`.

Uso (requiere el extra research-vectorbt):
  python tools/demo_vectorbt_zones.py --store runs/nt8_bridge/store \
      --contract "6E 09-25" --a Gaps2 --b BigTrap2
(la serie de precios se reconstruye del parquet fuente de la partición).
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from edgelab.bridge import features  # noqa: E402  (NO se importa ningún kernel)


def build_signals(store_root, contract, index_ms, price, a="Gaps2", b="BigTrap2",
                  a_bar_key="time_1", b_bar_key="time_1"):
    """Devuelve (entries, exits) booleanos alineados a index_ms combinando las
    zonas de dos indicadores del store. Regla demo (no optimizada):
      entrada = precio dentro de una zona de A y ≥1 zona activa de B;
      salida  = precio fuera de toda zona de A.
    Todo point-in-time (materialize_features no mira el futuro)."""
    za = features.get_zones_df(store_root, indicator=a, contract=contract, bar_key=a_bar_key)
    zb = features.get_zones_df(store_root, indicator=b, contract=contract, bar_key=b_bar_key)
    fa = features.materialize_features(za, index_ms, price=price,
                                       features=("inside_zone",))
    fb = features.materialize_features(zb, index_ms, price=price,
                                       features=("active_zone_count",))
    entries = fa["inside_zone"].to_numpy() & (fb["active_zone_count"].to_numpy() > 0)
    exits = ~fa["inside_zone"].to_numpy()
    return entries, exits, za, zb


def run_demo(store_root, contract, index_ms, price, a="Gaps2", b="BigTrap2",
             a_bar_key="time_1", b_bar_key="time_1"):
    """Corre una Portfolio de vectorbt con la señal combinada. Devuelve el
    portfolio. Importa vectorbt de forma perezosa (extra opcional)."""
    import vectorbt as vbt
    entries, exits, za, zb = build_signals(store_root, contract, index_ms, price,
                                           a, b, a_bar_key, b_bar_key)
    import pandas as pd
    close = pd.Series(np.asarray(price, dtype=float),
                      index=pd.to_datetime(np.asarray(index_ms), unit="ms"))
    pf = vbt.Portfolio.from_signals(close, entries, exits, freq="1min")
    return pf


def main(argv=None):
    ap = argparse.ArgumentParser(description="Demo vectorbt sobre zonas del store")
    ap.add_argument("--store", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--a", default="Gaps2")
    ap.add_argument("--b", default="BigTrap2")
    ap.add_argument("--bar-key", default="time_1")
    args = ap.parse_args(argv)

    # reconstruir la serie de precios del parquet fuente de una partición
    from edgelab.bridge import store, bars as bars_mod, ticks as ticks_mod
    import json
    from datetime import datetime, timezone
    parts = store.get_partitions(args.store, contract=args.contract, bar_key=args.bar_key)
    if not parts:
        print("sin particiones para", args.contract, args.bar_key)
        return 2
    man = json.loads(parts[0]["manifest_json"])
    src = man["source"]

    def iso_ns(s):
        return None if not s else int(datetime.fromisoformat(s.replace("Z", "")).replace(
            tzinfo=timezone.utc).timestamp() * 1e9)
    tk = ticks_mod.load_canonical_parquet(src["path"], contract=args.contract,
                                          start_utc_ns=iso_ns(src.get("range_start_utc")),
                                          end_utc_ns=iso_ns(src.get("range_end_utc")))
    kind, _, val = args.bar_key.partition("_")
    bars = (bars_mod.build_time_bars(tk, int(val)) if kind == "time"
            else bars_mod.build_tick_bars(tk, int(val)))
    index_ms = (bars.end_ns // 1_000_000).astype(np.int64)
    price = bars.close_t.astype(float) * tk.tick_size
    pf = run_demo(args.store, args.contract, index_ms, price, args.a, args.b, args.bar_key, args.bar_key)
    print("== demo vectorbt ==")
    print(pf.stats())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

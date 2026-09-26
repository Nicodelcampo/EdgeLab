#!/usr/bin/env python3
"""Inventario TARGET-FREE de BigTrap2 sobre los folds de desarrollo (time:1).

**No toca retornos ni P&L.** Cuenta zonas, mide geometría, ciclo de vida y
toques — lo mismo que se hizo con Gaps2 para calibrar E1, pero esta vez ANTES de
escribir el manifiesto, para no repetir el error de extrapolar desde un día.

No habilita ninguna campaña por sí solo: BigTrap2 sigue sin `parity_exact`
promovido (gate FAIL por el diff de borde) y sin manifiesto sellado.

Uso: python tools/bigtrap2_inventory.py
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from edgelab.bridge import bars as bars_mod, ticks as ticks_mod   # noqa: E402
from edgelab.bridge.indicators import bigtrap2                    # noqa: E402
from edgelab.research.camp001 import FOLDS                        # noqa: E402
from edgelab.research.holdout_guard import check_holdout          # noqa: E402

OUT = os.path.join(REPO, "runs", "nt8_bridge", "bigtrap2_inventory")


def _iso_ns(s):
    return int(dt.datetime.fromisoformat(s).replace(
        tzinfo=dt.timezone.utc).timestamp() * 1e9)


def main():
    os.makedirs(OUT, exist_ok=True)
    res = []
    for key, contract, s, e in FOLDS:
        t0 = time.time()
        check_holdout(s, e, purpose="development", caller="bigtrap2_inventory")
        tk = ticks_mod.load_canonical_parquet(
            os.path.join(REPO, "data", "nt8", "6E", key + "_ticks.parquet"),
            contract=contract, start_utc_ns=_iso_ns(s), end_utc_ns=_iso_ns(e))
        bars = bars_mod.build_time_bars(tk, 1)
        fps = bars_mod.build_footprints(tk, bars)
        r = bigtrap2.run(tk, bars, fps, params=None, chart_tz="UTC")
        zs = r["zones"]
        days = {dt.datetime.fromtimestamp(z["created_ms"] / 1000,
                                          tz=dt.timezone.utc).date() for z in zs}
        size = [round((z["top"] - z["bottom"]) / tk.tick_size) for z in zs]
        touch = [z["touches"] for z in zs]
        life = [(z["ended_ms"] - z["created_ms"]) / 60000.0
                for z in zs if z["ended_ms"] is not None]
        rec = dict(
            fold=key, contract=contract, n_ticks=len(tk), n_bars=len(bars),
            n_zones=len(zs), n_events=len(r["csv_lines"]), n_days=len(days),
            zones_per_day=round(len(zs) / max(1, len(days)), 1),
            bull=sum(1 for z in zs if z["kind"] == "trapped_buyers"),
            bear=sum(1 for z in zs if z["kind"] == "trapped_sellers"),
            size_ticks=dict(sorted(collections.Counter(size).items())[:12]),
            size_ge=({n: sum(1 for x in size if x >= n) for n in (1, 2, 3, 5, 8)}),
            touches=dict(sorted(collections.Counter(touch).items())[:8]),
            zonas_tocadas=sum(1 for t in touch if t > 0),
            vida_min_mediana=round(sorted(life)[len(life) // 2], 1) if life else None,
            end_reason=dict(collections.Counter(
                z["end_reason"] for z in zs).most_common()),
            elapsed_sec=round(time.time() - t0, 1))
        res.append(rec)
        print(json.dumps(rec, ensure_ascii=False))
        sys.stdout.flush()
    with open(os.path.join(OUT, "inventory.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)
    tot = sum(r["n_zones"] for r in res)
    print("\nTOTAL zonas BigTrap2 time:1 en desarrollo: %d" % tot)
    print("salida: %s" % os.path.join(OUT, "inventory.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

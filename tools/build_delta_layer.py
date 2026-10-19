#!/usr/bin/env python3
r"""Capa de delta por vela (volumen agresor comprador y vendedor) para un bundle de 25 ticks del visor.

    .venv\Scripts\python tools\build_delta_layer.py --asset NQ_03-26_202601_25T_HFT

Reconstruye las velas de cada sesión del manifiesto con la misma función del bundle
(`build_tick_bars(..., 25, reiniciar_por_sesion=True)`), verifica que tiempos y cierres coincidan con las velas del
bundle y suma el volumen por lado del agresor (`aggressor` de research-v2). Salida:
`viewer/nt8_bridge/bundles/delta/<asset>.json` con `buy` y `sell` alineados al índice de vela.

**Validez del agresor:** NQ 99 % (válido); ES 80 % (NO usar, P-93); YM y MYM sin verificar. El script se niega a
construir la capa para activos no validados, salvo con `--allow-unvalidated` (queda marcado en la salida).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pyarrow.compute as pc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from edgelab.bridge.bars import build_tick_bars  # noqa: E402
from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402

BUNDLES = REPO / "viewer" / "nt8_bridge" / "bundles"
VALIDATED = {"NQ": "99% (artifacts/aggressor_validation.json, P-93)"}
EXP_END = 20260331


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", required=True)
    ap.add_argument("--allow-unvalidated", action="store_true")
    a = ap.parse_args(argv)
    m = json.loads((BUNDLES / f"{a.asset}.manifest.json").read_text(encoding="utf-8"))
    inst = m["instrument"]
    if inst not in VALIDATED and not a.allow_unvalidated:
        raise SystemExit(f"agresor de {inst} no validado: no se construye (ver P-93)")
    if any(int(s["trade_date"]) > EXP_END for s in m["sessions"]):
        raise SystemExit("el bundle tiene sesiones fuera de exploración")
    b = json.loads((BUNDLES / f"{a.asset}.json").read_text(encoding="utf-8"))
    cd = b["bar_series"][next(iter(b["bar_series"]))]["candles"]
    t_b = np.array([c["time"] for c in cd], np.int64); c_b = np.array([c["close"] for c in cd])
    del b, cd
    buy, sell, times, closes = [], [], [], []
    path = m["source_path"]
    for s in m["sessions"]:
        start, end = int(s["start_utc_ns"]), int(s["end_utc_ns"])
        tk = load_canonical_parquet(path, contract=m["contract"], instrument=inst, start_utc_ns=start, end_utc_ns=end)
        tb = pq.read_table(path, columns=["ts_utc_ns", "price_ticks", "aggressor", "contract"],
                           filters=[("ts_utc_ns", ">=", start), ("ts_utc_ns", "<", end)])
        tb = tb.filter(pc.equal(tb["contract"], m["contract"]))
        ts = tb["ts_utc_ns"].to_numpy(); px = tb["price_ticks"].to_numpy()
        ag = np.array(tb["aggressor"].to_pylist(), dtype=object)
        if len(ts) != len(tk) or not np.array_equal(ts, tk.ts_ns) or not np.array_equal(px, tk.price_ticks):
            raise SystemExit(f"{s['trade_date']}: las filas del agresor no coinciden con el loader (orden o filtro distinto)")
        bars = build_tick_bars(tk, 25, reiniciar_por_sesion=True)
        idx = bars.tick_bar_idx
        v = tk.volume.astype(float)
        nb = len(bars.end_ns)
        buy.append(np.bincount(idx, weights=v * (ag == "buy"), minlength=nb))
        sell.append(np.bincount(idx, weights=v * (ag == "sell"), minlength=nb))
        times.append(bars.end_ns // 1_000_000_000); closes.append(bars.close_t * tk.tick_size)
        print(s["trade_date"], "velas", nb, "sin lado", int(((ag != "buy") & (ag != "sell")).sum()), flush=True)
    buy, sell = np.concatenate(buy), np.concatenate(sell)
    times, closes = np.concatenate(times), np.concatenate(closes)
    if len(times) != len(t_b) or not np.array_equal(times, t_b) or not np.allclose(closes, c_b):
        raise SystemExit("las velas reconstruidas no coinciden con las del bundle: no se escribe la capa")
    out = BUNDLES / "delta" / f"{a.asset}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(asset=a.asset, instrument=inst, aggressor_validity=VALIDATED.get(inst, "NO VALIDADO"),
                                   n=int(len(times)), buy=[round(float(x), 1) for x in buy], sell=[round(float(x), 1) for x in sell]),
                              separators=(",", ":")), encoding="utf-8")
    print("OK", out, len(times), "velas; alineación con el bundle verificada")


if __name__ == "__main__":
    main()

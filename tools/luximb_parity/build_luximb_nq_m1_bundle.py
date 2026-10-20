"""Bundle del visor: NQ (un contrato, sin merge ni back-adjust) en velas M1 + zonas LUX-IMB (OG + VI).

Target-free: geometria de velas y zonas, sin desenlaces ni retornos.
- Velas: ticks del release v4, convencion validada en la paridad del 2026-10-20 (un tick en HH:MM:00.000 abre la
  vela nueva). En el visor la vela se marca con su hora de APERTURA (NT8 la marca con el cierre).
- Zonas: `parity_luximb.detect` (paridad 1507/1507 contra NT8). Viven Extend=500 minutos desde el cierre de la
  vela que las crea, no se borran por mitigacion (igual que el indicador).
- Rechaza cualquier tick >= 2026-10-01 (holdout).

Uso: python tools/luximb_parity/build_luximb_nq_m1_bundle.py <ticks_parquet> <contrato "NQ 09-26"> <td_desde> <td_hasta> <bundles_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parity_luximb as P  # noqa: E402

HOLDOUT_MS = int(pd.Timestamp("2026-10-01", tz="UTC").value // 1_000_000)
EXTEND_MIN = 500
COLORS = {"bull": "#2157f3", "bear": "#ff1100"}


def main():
    ticks, contract, d0, d1, out_dir = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), Path(sys.argv[5])
    pf = pq.ParquetFile(ticks)
    md = pf.metadata
    ci = {md.row_group(0).column(i).path_in_schema: i for i in range(md.row_group(0).num_columns)}
    parts = []
    for rg in range(md.num_row_groups):          # por row group: no se carga el archivo entero
        g = md.row_group(rg)
        td, ct = g.column(ci["trade_date"]).statistics, g.column(ci["contract"]).statistics
        if td.max < d0 or td.min > d1 or str(ct.min) > contract or str(ct.max) < contract:
            continue
        tb = pf.read_row_group(rg, columns=["ts_utc_ns", "price_ticks", "volume", "contract", "trade_date"]).to_pandas()
        tb = tb[(tb.contract == contract) & (tb.trade_date >= d0) & (tb.trade_date <= d1)]
        if len(tb):
            parts.append(tb[["ts_utc_ns", "price_ticks", "volume"]])
    tk = pd.concat(parts).sort_values("ts_utc_ns", kind="stable")
    if int(tk.ts_utc_ns.max()) // 1_000_000 >= HOLDOUT_MS:
        raise SystemExit("ticks del holdout en la ventana pedida")
    b = P.bars_from_ticks(tk.ts_utc_ns.to_numpy(), tk.price_ticks.to_numpy().astype(float) * P.TICK,
                          tk.volume.to_numpy().astype(float), boundary_to_previous=False)
    t_close = b.t.to_numpy() // 1000                  # segundos, cierre (convencion NT8)
    t_open = t_close - 60
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    det = P.detect(o, h, l, c)
    zones = []
    for n, (i, ty, d, tp, bt) in enumerate(det):
        zones.append({"id": f"LUX_{ty}_{n}", "source": "luxalgo", "kind": f"{ty} {'BULL' if d == 'bull' else 'BEAR'}",
                      "top": float(tp), "bottom": float(bt), "t0": int(t_open[i - 1]), "t1": int(t_close[i] + EXTEND_MIN * 60),
                      "available_ts": int(t_close[i]), "state": "ACTIVE", "color": COLORS[d], "label": ty,
                      "height_ticks": round((tp - bt) / P.TICK, 2)})
    candles = [{"time": int(t_open[k]), "open": o[k], "high": h[k], "low": l[k], "close": c[k], "volume": float(b.volume[k])}
               for k in range(len(b))]
    aid = f"NQ_{contract.split(' ')[1]}_M1_LUXIMB"
    meta = dict(id=aid, name=f"{contract} · M1 · LUX-IMB (OG+VI) · {d0}-{d1}", instrument="NQ", contract=contract,
                tick_size=P.TICK, precision=2, chart_tz="UTC", n_candles=len(candles), n_zones=len(zones), rolls=[],
                kind="M1_LUX_IMB", outcome_firewall="ENFORCED", holdout_boundary_ms=HOLDOUT_MS,
                fuente_ticks=ticks, ventana_trade_date=[d0, d1], sin_back_adjust=True,
                velas="marca = apertura; tick en HH:MM:00.000 abre vela nueva", extend_min=EXTEND_MIN)
    bundle = {"meta": meta,
              "bar_series": {"time_1m": {"kind": "time_1m", "name": "1 Minuto (desde ticks)", "param": 1, "candles": candles}},
              "runs": [{"id": "lux_imb_og_vi", "name": "Imbalance MTF [LuxAlgo] (OG + VI · Python, paridad NT8 1507/1507)",
                        "indicator": "ImbalanceDetectorLuxAlgoMTF", "bar_key": "time_1m", "zones": zones, "has_oracle": False,
                        "parity": {"status": "PARITY_PASS", "gate": "PARITY_PASS",
                                   "ref": "docs/research/luximb_parity_20261020/PARIDAD_LUXIMB_NQ1226_20261020.md"}}]}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{aid}.json").write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
    mf = out_dir / "manifest.js"
    cat = []
    if mf.exists():
        txt = mf.read_text(encoding="utf-8")
        cat = json.loads(txt[txt.index("["):txt.rindex("]") + 1])
    cat = [e for e in cat if e.get("id") != aid]
    cat.insert(0, dict(id=aid, name=meta["name"], group="NQ (LUX-IMB M1)", instrument="NQ", contract=contract, tick_size=P.TICK,
                       precision=2, candles=len(candles), zones=len(zones), rolls=0, parity_status="PARITY_PASS", kind="M1_LUX_IMB"))
    mf.write_text("window.ASSET_CATALOG = " + json.dumps(cat, indent=2, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(json.dumps({"bundle": aid, "velas": len(candles), "zonas": len(zones),
                      "desde": str(pd.to_datetime(t_open[0], unit="s")), "hasta": str(pd.to_datetime(t_close[-1], unit="s"))}))


if __name__ == "__main__":
    main()

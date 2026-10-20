"""Bundle del visor para FX de Dukascopy (JForex: timestamp UTC, bid, ask, last=mid): velas M1 y 25t + zonas LUX-IMB.

Misma logica que `build_luximb_nq_m1_bundle.py` (detector con paridad NT8, zona nace al cierre de su vela, vida 500 min).
Diferencias por ser FX: precio = mid (`last`); sin volumen real (volume = cantidad de ticks); 25t = 25 actualizaciones
de cotizacion (no operaciones); tick_size 0.00001. Target-free.

Uso: python tools/luximb_parity/build_luximb_fx_bundle.py <ticks.parquet> <SIMBOLO> <desde YYYY-MM-DD> <hasta YYYY-MM-DD> <bundles_dir>
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

EXTEND_MIN = 500
TICK = 0.00001
COLORS = {"bull": "#2157f3", "bear": "#ff1100"}


def main():
    path, sym, d0, d1, out_dir = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], Path(sys.argv[5])
    t0 = pd.Timestamp(d0, tz="UTC"); t1 = pd.Timestamp(d1, tz="UTC") + pd.Timedelta(days=1)
    pf = pq.ParquetFile(path); parts = []
    for rg in range(pf.num_row_groups):                  # por row group
        st = pf.metadata.row_group(rg).column(0).statistics
        if pd.Timestamp(st.max).tz_localize("UTC") < t0 or pd.Timestamp(st.min).tz_localize("UTC") >= t1:
            continue
        tb = pf.read_row_group(rg, columns=["timestamp", "last"]).to_pandas()
        ts = tb.timestamp.dt.tz_localize("UTC")
        tb = tb[(ts >= t0) & (ts < t1)]
        if len(tb): parts.append(tb)
    tk = pd.concat(parts).sort_values("timestamp", kind="stable")
    ts_ns = tk.timestamp.astype("datetime64[ns]").astype("int64").to_numpy()
    px = np.round(tk["last"].to_numpy() / TICK) * TICK                     # mid redondeado a 0.00001
    vol = np.ones(len(px))
    b = P.bars_from_ticks(ts_ns, px, vol, boundary_to_previous=False)
    t_close = b.t.to_numpy() // 1000; t_open = t_close - 60
    o, h, l, c = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    zones = []
    for n, (i, ty, d, tp, bt) in enumerate(P.detect(o, h, l, c)):
        zones.append({"id": f"LUX_{ty}_{n}", "source": "luxalgo", "kind": f"{ty} {'BULL' if d == 'bull' else 'BEAR'}",
                      "top": float(tp), "bottom": float(bt), "t0": int(t_close[i]), "t1": int(t_close[i] + EXTEND_MIN * 60),
                      "available_ts": int(t_close[i]), "state": "ACTIVE", "color": COLORS[d], "label": ty,
                      "height_ticks": round((tp - bt) / TICK, 2)})
    candles = [{"time": int(t_open[k]), "open": round(o[k], 5), "high": round(h[k], 5), "low": round(l[k], 5), "close": round(c[k], 5),
                "volume": float(b.volume[k])} for k in range(len(b))]
    brk = np.r_[True, np.diff(ts_ns) > 1_800 * 10**9]; seg = np.cumsum(brk) - 1
    pos = np.arange(len(ts_ns)) - np.flatnonzero(brk)[seg]
    gid = np.cumsum(np.r_[True, (seg[1:] != seg[:-1]) | (pos[1:] // 25 != pos[:-1] // 25)]) - 1
    st_ = np.flatnonzero(np.r_[True, gid[1:] != gid[:-1]]); en = np.r_[st_[1:], len(ts_ns)]
    c25 = [{"time": int(ts_ns[a] // 10**9), "open": round(px[a], 5), "high": round(float(px[a:e].max()), 5), "low": round(float(px[a:e].min()), 5),
            "close": round(px[e - 1], 5), "volume": float(e - a)} for a, e in zip(st_, en)]
    aid = f"{sym}_DUKAS_M1_LUXIMB"
    meta = dict(id=aid, name=f"{sym} Dukascopy · M1/25t · LUX-IMB (OG+VI) · {d0}..{d1}", instrument=sym, contract=f"{sym} (Dukascopy mid)",
                tick_size=TICK, precision=5, chart_tz="UTC", n_candles=len(candles), n_zones=len(zones), rolls=[], kind="M1_LUX_IMB",
                fuente_ticks=path, precio="mid (last)", volumen="cantidad de ticks", velas="marca = apertura", extend_min=EXTEND_MIN)
    bundle = {"meta": meta,
              "bar_series": {"time_1m": {"kind": "time_1m", "name": "1 Minuto (desde ticks)", "param": 1, "candles": candles},
                             "tick_25": {"kind": "tick_25", "name": "25 Tick (25 cotizaciones)", "param": 25, "candles": c25}},
              "runs": [{"id": "lux_imb_og_vi", "name": "Imbalance MTF [LuxAlgo] (OG + VI · Python; paridad medida en NQ, no en FX)",
                        "indicator": "ImbalanceDetectorLuxAlgoMTF", "bar_key": "time_1m", "zones": zones, "has_oracle": False,
                        "parity": {"status": "PARITY_ABSTAIN", "gate": "PARITY_ABSTAIN"}}]}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{aid}.json").write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
    mf = out_dir / "manifest.js"; txt = mf.read_text(encoding="utf-8"); cat = json.loads(txt[txt.index("["):txt.rindex("]") + 1])
    cat = [e for e in cat if e.get("id") != aid]
    cat.insert(0, dict(id=aid, name=meta["name"], group=f"{sym} (LUX-IMB M1)", instrument=sym, contract=meta["contract"], tick_size=TICK,
                       precision=5, candles=len(candles), zones=len(zones), rolls=0, parity_status="PARITY_ABSTAIN", kind="M1_LUX_IMB"))
    mf.write_text("window.ASSET_CATALOG = " + json.dumps(cat, indent=2, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(json.dumps({"bundle": aid, "ticks": len(px), "velas_m1": len(candles), "velas_25t": len(c25), "zonas": len(zones)}))


if __name__ == "__main__":
    main()

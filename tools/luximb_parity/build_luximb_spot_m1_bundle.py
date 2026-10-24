"""Bundle del visor con velas M1 de Dukascopy (spot/CFD, p. ej. USATECH ~ NQ) + zonas LUX-IMB (OG+VI). Target-free.

Igual que `build_luximb_fx_bundle.py` (detector `parity_luximb.detect`, la zona nace al CIERRE de su vela, vida 500 min),
pero parte del M1 ya agregado del dataset (`USATECHIDXUSD_m1.parquet`: time_utc_ns = inicio de vela, bid_/ask_ OHLC).
Precio = mid (bid+ask)/2. Se descartan las velas de relleno (planas y sin volumen cotizado: mercado cerrado).
Es un CFD, no el futuro: horario, spread y volumen distintos; sirve para mirar/agregar potencia a pruebas de información.

Uso: python tools/luximb_parity/build_luximb_spot_m1_bundle.py <m1.parquet> <SIMBOLO> <desde> <hasta> <bundles_dir> [tick=0.01]
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
COLORS = {"bull": "#2157f3", "bear": "#ff1100"}


def main():
    path, sym, d0, d1, out_dir = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], Path(sys.argv[5])
    tick = float(sys.argv[6]) if len(sys.argv) > 6 else 0.01
    a_ns = pd.Timestamp(d0, tz="UTC").value; b_ns = (pd.Timestamp(d1, tz="UTC") + pd.Timedelta(days=1)).value
    b_ns = min(b_ns, 1_790_805_600_000_000_000)                         # nunca entra al holdout (apertura 2026-09-30 22:00 UTC, HOLDOUT-A4)
    pf = pq.ParquetFile(path); parts = []
    for rg in range(pf.num_row_groups):                                   # por row group: no se carga el archivo entero
        st = pf.metadata.row_group(rg).column(0).statistics
        if st.max < a_ns or st.min >= b_ns: continue
        t = pf.read_row_group(rg).to_pandas(); parts.append(t[(t.time_utc_ns >= a_ns) & (t.time_utc_ns < b_ns)])
    d = pd.concat(parts).sort_values("time_utc_ns", kind="stable")
    mid = {k: (d[f"bid_{k}"].to_numpy() + d[f"ask_{k}"].to_numpy()) / 2 for k in ("open", "high", "low", "close")}
    vol = (d.bid_vol.to_numpy() + d.ask_vol.to_numpy()).astype(float)
    relleno = (vol == 0) & (mid["high"] == mid["low"])
    keep = ~relleno
    o, h, l, c = (np.round(mid[k][keep] / tick) * tick for k in ("open", "high", "low", "close"))
    t_open = d.time_utc_ns.to_numpy()[keep] // 10**9; t_close = t_open + 60; v = vol[keep]
    zones = []
    for n, (i, ty, dr, tp, bt) in enumerate(P.detect(o, h, l, c)):
        zones.append({"id": f"LUX_{ty}_{n}", "source": "luxalgo", "kind": f"{ty} {'BULL' if dr == 'bull' else 'BEAR'}",
                      "top": float(tp), "bottom": float(bt), "t0": int(t_close[i]), "t1": int(t_close[i] + EXTEND_MIN * 60),
                      "available_ts": int(t_close[i]), "state": "ACTIVE", "color": COLORS[dr], "label": ty,
                      "height_ticks": round((tp - bt) / tick, 2)})
    candles = [{"time": int(t_open[k]), "open": round(float(o[k]), 3), "high": round(float(h[k]), 3), "low": round(float(l[k]), 3),
                "close": round(float(c[k]), 3), "volume": round(float(v[k]), 4)} for k in range(len(o))]
    aid = f"{sym}_DUKAS_SPOT_M1_LUXIMB"
    meta = dict(id=aid, name=f"{sym} Dukascopy (CFD, no CME) · M1 · LUX-IMB (OG+VI) · {d0}..{d1}", instrument=sym,
                contract=f"{sym} (Dukascopy mid)", tick_size=tick, precision=2, chart_tz="UTC", n_candles=len(candles), n_zones=len(zones),
                rolls=[], kind="M1_LUX_IMB", fuente=Path(path).name, precio="mid (bid+ask)/2", volumen="liquidez cotizada (no trades)",
                velas="marca = apertura", extend_min=EXTEND_MIN, velas_relleno_descartadas=int(relleno.sum()))
    bundle = {"meta": meta, "bar_series": {"time_1m": {"kind": "time_1m", "name": "1 Minuto (Dukascopy)", "param": 1, "candles": candles}},
              "runs": [{"id": "lux_imb_og_vi", "name": "Imbalance MTF [LuxAlgo] (OG + VI · Python; paridad medida en NQ CME, no en este CFD)",
                        "indicator": "ImbalanceDetectorLuxAlgoMTF", "bar_key": "time_1m", "zones": zones, "has_oracle": False,
                        "parity": {"status": "PARITY_ABSTAIN", "gate": "PARITY_ABSTAIN"}}]}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{aid}.json").write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
    mf = out_dir / "manifest.js"; txt = mf.read_text(encoding="utf-8"); cat = json.loads(txt[txt.index("["):txt.rindex("]") + 1])
    cat = [e for e in cat if e.get("id") != aid]
    cat.insert(0, dict(id=aid, name=meta["name"], group=f"{sym} (LUX-IMB M1, CFD)", instrument=sym, contract=meta["contract"], tick_size=tick,
                       precision=2, candles=len(candles), zones=len(zones), rolls=0, parity_status="PARITY_ABSTAIN", kind="M1_LUX_IMB"))
    mf.write_text("window.ASSET_CATALOG = " + json.dumps(cat, indent=2, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(json.dumps({"bundle": aid, "velas_m1": len(candles), "relleno_descartado": int(relleno.sum()), "zonas": len(zones),
                      "og": sum(z["label"] == "OG" for z in zones), "vi": sum(z["label"] == "VI" for z in zones)}))


if __name__ == "__main__":
    main()

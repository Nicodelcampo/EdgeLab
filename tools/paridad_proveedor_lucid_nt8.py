#!/usr/bin/env python3
r"""Paridad de proveedor Lucid (research-v2) ↔ NinjaTrader (solape jul-2025 → jun-2026), sesión por sesión. Target-free.

Por cada trade date presente en los dos catálogos (mismo instrumento):
- contrato elegido por cada catálogo;
- ticks y volumen totales (razón NT8 / Lucid);
- por minuto: cantidad de trades, volumen, máximo, mínimo y último precio (en ticks) — correlación del volumen por
  minuto, fracción de minutos con máximo/mínimo/cierre idénticos, diferencia máxima;
- velas de 25t: cantidad y fracción de cierres idénticos (alineados por índice dentro de la sesión);
- bid/ask: fracción de ticks con cotización válida en cada proveedor.
Criterio de lectura (a fijar con el auditor, entrada 053/054): no se decide acá.

    .venv\Scripts\python tools\paridad_proveedor_lucid_nt8.py ES [--max N]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
import tbzx_iter2 as T2  # noqa: E402

OUT = REPO / "artifacts" / "paridad_proveedor"


def minute_table(tk):
    ts = tk.ts_ns.astype(np.int64); px = tk.price_ticks.astype(np.int64); v = tk.volume.astype(float)
    m = ts // 60_000_000_000
    df = pd.DataFrame(dict(m=m, px=px, v=v))
    g = df.groupby("m")
    return pd.DataFrame(dict(n=g.size(), vol=g.v.sum(), hi=g.px.max(), lo=g.px.min(), last=g.px.last()))


def bars25_close(tk):
    px = tk.price_ticks.astype(np.int64); n = len(px)
    return px[np.minimum(np.arange((n + 24) // 25) * 25 + 24, n - 1)]


def quote_ok(tk):
    if tk.bid_ticks is None or tk.ask_ticks is None:
        return None
    b = tk.bid_ticks.astype(float); a = tk.ask_ticks.astype(float)
    return float(((b > 0) & (a > 0) & (a >= b)).mean())


def main():
    inst = sys.argv[1]
    mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else None
    lucid = {s["trade_date"]: s for s in T2.canonical_sessions(inst) if s["trade_date"] <= "20260630" and "nt8_ext" not in s["path"]}
    cat = json.loads((REPO / "docs" / "research" / "contract_regimes" / f"{inst}_nt8_overlap_sessions_catalog.json").read_text(encoding="utf-8"))
    nt8 = {s["trade_date"]: s for s in cat["sessions"]}
    common = sorted(set(lucid) & set(nt8))[: mx or None]
    rows = []
    for d in common:
        a, b = lucid[d], nt8[d]
        r = dict(trade_date=d, contrato_lucid=a["contract"], contrato_nt8=b["contract"], mismo_contrato=a["contract"] == b["contract"])
        try:
            ta = load_canonical_parquet(a["path"], contract=a["contract"], start_utc_ns=a["start"], end_utc_ns=a["end"])
            tb = load_canonical_parquet(b["path"], contract=b["contract"], start_utc_ns=int(b["start"]), end_utc_ns=int(b["end"]))
        except Exception as e:  # noqa: BLE001
            r["error"] = str(e)[:200]; rows.append(r); continue
        ma, mb = minute_table(ta), minute_table(tb)
        j = ma.join(mb, lsuffix="_l", rsuffix="_n", how="inner")
        ca, cb = bars25_close(ta), bars25_close(tb)
        k = min(len(ca), len(cb))
        r.update(ticks_l=len(ta), ticks_n=len(tb), razon_ticks=len(tb) / max(len(ta), 1),
                 vol_l=float(ta.volume.sum()), vol_n=float(tb.volume.sum()), razon_vol=float(tb.volume.sum() / max(ta.volume.sum(), 1)),
                 minutos_comunes=int(len(j)), minutos_solo_lucid=int(len(ma) - len(j)), minutos_solo_nt8=int(len(mb) - len(j)),
                 corr_vol_minuto=float(np.corrcoef(j.vol_l, j.vol_n)[0, 1]) if len(j) > 2 else None,
                 min_hi_igual=float((j.hi_l == j.hi_n).mean()), min_lo_igual=float((j.lo_l == j.lo_n).mean()),
                 min_cierre_igual=float((j.last_l == j.last_n).mean()),
                 max_dif_hi_lo_ticks=int(max((j.hi_l - j.hi_n).abs().max(), (j.lo_l - j.lo_n).abs().max())) if len(j) else None,
                 velas25_l=len(ca), velas25_n=len(cb), velas25_cierre_igual=float((ca[:k] == cb[:k]).mean()) if k else None,
                 cotiz_validas_l=quote_ok(ta), cotiz_validas_n=quote_ok(tb))
        rows.append(r)
        print(d, r.get("razon_ticks"), r.get("min_hi_igual"), r.get("velas25_cierre_igual"), flush=True)
        del ta, tb
    D = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    D.to_csv(OUT / f"paridad_{inst}.csv", index=False)
    ok = D.dropna(subset=["razon_ticks"]) if "razon_ticks" in D else D
    resumen = dict(instrumento=inst, sesiones_comunes=len(common), con_error=int(D.get("error", pd.Series(dtype=str)).notna().sum()),
                   mismo_contrato=float(D.mismo_contrato.mean()) if len(D) else None,
                   razon_ticks_mediana=float(ok.razon_ticks.median()) if len(ok) else None,
                   razon_vol_mediana=float(ok.razon_vol.median()) if len(ok) else None,
                   min_hi_igual_mediana=float(ok.min_hi_igual.median()) if len(ok) else None,
                   min_cierre_igual_mediana=float(ok.min_cierre_igual.median()) if len(ok) else None,
                   corr_vol_minuto_mediana=float(ok.corr_vol_minuto.median()) if len(ok) else None,
                   velas25_cierre_igual_mediana=float(ok.velas25_cierre_igual.median()) if len(ok) else None,
                   outcomes_accessed=False)
    (OUT / f"paridad_{inst}_resumen.json").write_text(json.dumps(resumen, indent=1), encoding="utf-8")
    print(json.dumps(resumen, indent=1))


if __name__ == "__main__":
    main()

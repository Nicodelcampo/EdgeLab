"""Paridad NT8 -> Python del ImbalanceDetectorLuxAlgoMTF (OG/VI sobre velas M1), en tres capas.

A) detector Python sobre las velas M1 EXPORTADAS por NT8  vs  zonas exportadas por NT8   (logica del detector)
B) velas M1 construidas desde ticks de NT8 (.Last)        vs  velas M1 exportadas por NT8 (construccion de barras)
C) detector Python sobre las velas construidas desde ticks vs  zonas exportadas por NT8    (paridad de punta a punta)

Uso: python tools/luximb_parity/parity_luximb.py <prefijo_export_sin__zones.csv> <ticks_parquet> <out.json>
Sin outcomes ni retornos: solo geometria de zonas y barras.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

TICK = 0.25


def read_nt8(path):
    lines = [ln for ln in open(path, encoding="utf-8") if not ln.startswith("#")]
    header, rows = lines[0].strip().split(","), lines[1:]
    ok = [r for r in rows if r.endswith("\n") and r.count(",") == len(header) - 1]   # descarta una ultima linea truncada
    from io import StringIO
    df = pd.read_csv(StringIO(lines[0] + "".join(ok)))
    return df, len(rows) - len(ok)


def detect(o, h, l, c, show_og=True, show_vi=True):
    """Replica de OnBarUpdate (serie M1, OnBarClose): CurrentBar < 3 -> return. Sin filtros de ancho (UseWidth=False)."""
    out = []
    for i in range(3, len(c)):
        O0, H0, L0, C0, O1, H1, L1, C1 = o[i], h[i], l[i], c[i], o[i - 1], h[i - 1], l[i - 1], c[i - 1]
        bull_top, bull_btm = min(C0, O0), max(C1, O1)
        bear_top, bear_btm = min(C1, O1), max(C0, O0)
        bull_vi = show_vi and O0 > C1 and H1 > L0 and C0 > C1 and O0 > O1 and H1 < bull_top
        bear_vi = show_vi and O0 < C1 and L1 < H0 and C0 < C1 and O0 < O1 and L1 > bear_btm
        bull_og = show_og and L0 > H1
        bear_og = show_og and H0 < L1
        if bull_vi: out.append((i, "VI", "bull", bull_top, bull_btm))
        if bear_vi: out.append((i, "VI", "bear", bear_top, bear_btm))
        if bull_og: out.append((i, "OG", "bull", bull_top, bull_btm))
        if bear_og: out.append((i, "OG", "bear", bear_top, bear_btm))
    return out


def bars_from_ticks(ts_ns, px, vol, boundary_to_previous=True):
    """Velas de 1 minuto con marca de CIERRE (convencion NT8). boundary_to_previous: un tick en HH:MM:00.000 cierra la vela HH:MM."""
    ms = ts_ns // 1_000_000
    if boundary_to_previous:
        close_ms = ((ms + 59_999) // 60_000) * 60_000
    else:
        close_ms = (ms // 60_000 + 1) * 60_000
    df = pd.DataFrame({"t": close_ms, "p": px, "v": vol})
    g = df.groupby("t", sort=True)
    b = pd.DataFrame({"open": g.p.first(), "high": g.p.max(), "low": g.p.min(), "close": g.p.last(), "volume": g.v.sum()}).reset_index()
    return b


def compare_zones(nt, py_list, key_time):
    """nt: DataFrame de zonas NT8; py_list: [(ts_ms, type, dir, top, btm)]. Clave = (ts_ms, type, dir); compara top/bottom."""
    k_nt = {(int(r.ts_utc_ms), r.type, r.dir): (float(r.top), float(r.bottom)) for r in nt.itertuples()}
    k_py = {(int(t), ty, d): (tp, bt) for (t, ty, d, tp, bt) in py_list}
    both = set(k_nt) & set(k_py)
    geo_ok = sum(1 for k in both if abs(k_nt[k][0] - k_py[k][0]) < 1e-9 and abs(k_nt[k][1] - k_py[k][1]) < 1e-9)
    only_nt = sorted(set(k_nt) - set(k_py))
    only_py = sorted(set(k_py) - set(k_nt))
    return dict(nt8=len(k_nt), python=len(k_py), comunes=len(both), comunes_misma_geometria=geo_ok,
                solo_nt8=len(only_nt), solo_python=len(only_py),
                paridad_exacta_pct=round(100.0 * geo_ok / max(len(k_nt), 1), 3),
                ejemplos_solo_nt8=[list(map(str, k)) for k in only_nt[:5]], ejemplos_solo_python=[list(map(str, k)) for k in only_py[:5]])


def main():
    pref, ticks_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    zones, trunc_z = read_nt8(pref + "_zones.csv")
    bars, trunc_b = read_nt8(pref + "_m1bars.csv")
    res = {"export": pref, "lineas_truncadas": {"zones": trunc_z, "m1bars": trunc_b}}

    # --- A: detector sobre las velas de NT8 ---
    o, h, l, c = (bars[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    det = detect(o, h, l, c)
    t_ms = bars.ts_utc_ms.to_numpy()
    zA = [(t_ms[i], ty, d, tp, bt) for (i, ty, d, tp, bt) in det]
    # NT8 escribe zonas hasta la ultima vela completa: recortar Python al mismo rango
    tmax = zones.ts_utc_ms.max()
    zA = [z for z in zA if z[0] <= tmax]
    res["A_detector_sobre_velas_NT8"] = compare_zones(zones, zA, "ts_utc_ms")

    # --- B: velas desde ticks ---
    t0, t1 = int(bars.ts_utc_ms.min()) - 60_000, int(bars.ts_utc_ms.max())
    pf = pq.ParquetFile(ticks_path)
    parts = []
    for rg in range(pf.num_row_groups):
        tb = pf.read_row_group(rg, columns=["ts_utc_ns", "price_ticks", "volume"])
        ts = tb["ts_utc_ns"].to_numpy()
        m = (ts // 1_000_000 > t0) & (ts // 1_000_000 <= t1)
        if m.any():
            parts.append((ts[m], tb["price_ticks"].to_numpy()[m], tb["volume"].to_numpy()[m]))
    ts = np.concatenate([p[0] for p in parts]); px = np.concatenate([p[1] for p in parts]).astype(float) * TICK
    vol = np.concatenate([p[2] for p in parts]).astype(float)
    o_ = np.argsort(ts, kind="stable"); ts, px, vol = ts[o_], px[o_], vol[o_]
    nt_b = bars.set_index("ts_utc_ms")
    best = None
    for conv in (True, False):
        tb = bars_from_ticks(ts, px, vol, conv).set_index("t")
        common = nt_b.index.intersection(tb.index)
        eq = {k: float(np.mean(np.isclose(nt_b.loc[common, k].to_numpy(float), tb.loc[common, k].to_numpy(float)))) for k in ("open", "high", "low", "close", "volume")}
        allohlc = float(np.mean(np.all([np.isclose(nt_b.loc[common, k].to_numpy(float), tb.loc[common, k].to_numpy(float)) for k in ("open", "high", "low", "close")], axis=0)))
        r = dict(convencion="tick_en_borde_cierra_vela_anterior" if conv else "tick_en_borde_abre_vela_nueva", velas_nt8=len(nt_b), velas_ticks=len(tb),
                 comunes=len(common), solo_nt8=int(len(nt_b.index.difference(tb.index))), solo_ticks=int(len(tb.index.difference(nt_b.index))),
                 igualdad_por_campo=eq, igualdad_ohlc_completa=round(allohlc, 5))
        res.setdefault("B_velas_desde_ticks", []).append(r)
        if best is None or allohlc > best[0]:
            best = (allohlc, conv, tb)

    # --- C: detector sobre velas desde ticks (mejor convencion) ---
    tb = best[2].reset_index()
    tb = tb[(tb.t >= bars.ts_utc_ms.min()) & (tb.t <= bars.ts_utc_ms.max())].reset_index(drop=True)
    detC = detect(tb.open.to_numpy(float), tb.high.to_numpy(float), tb.low.to_numpy(float), tb.close.to_numpy(float))
    zC = [(int(tb.t[i]), ty, d, tp, bt) for (i, ty, d, tp, bt) in detC if tb.t[i] <= tmax]
    res["C_punta_a_punta"] = compare_zones(zones, zC, "ts_utc_ms")
    res["C_convencion_usada"] = "tick_en_borde_cierra_vela_anterior" if best[1] else "tick_en_borde_abre_vela_nueva"
    json.dump(res, open(out_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

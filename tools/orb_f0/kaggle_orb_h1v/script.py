# -*- coding: utf-8 -*-
"""ORB Fase 0A (SIN retornos): integridad, geometria del rango de apertura, ocurrencia de ruptura,
costo de un stop de ruptura y marginales de filtros. Manifiesto: docs/research/ORB_FASE0_MANIFIESTO_20261017.md (seccion 3).
ES y NQ por separado. RTH 09:30 ET. Descubrimiento 2025-07-18..2026-03-31 y ventana limpia 2026-07-16..2026-09-30.
No calcula ningun P&L ni extension post-ruptura (eso es 0B)."""
from __future__ import annotations

import json
import math
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ET = ZoneInfo("America/New_York")
TICK = 0.25
HOLDOUT_TRADE_DATE = 20261001
HOLDOUT_UTC_NS = 1790812800000000000
WINDOWS = {"DISC": (20250718, 20260331), "CLEAN": (20260716, 20260930)}
OR_MINS = (5, 15, 30, 60)
PRIMARY_W = 15
NS_MIN = 60_000_000_000
COST_RT_TICKS = 2.5          # el de strategies/orb.py, para la razon costo/ancho
MAX_GAP_NS = 60 * 1_000_000_000


def locate_parquet(asset: str) -> Path:
    root = Path("/kaggle/input")
    for mpath in root.rglob("release_manifest.json"):
        try:
            man = json.loads(mpath.read_text(encoding="utf-8"))
            info = man.get("assets", {}).get(asset)
            if info and "file" in info and (mpath.parent / info["file"]).exists():
                return mpath.parent / info["file"]
        except Exception:
            pass
    for name in (asset + ".parquet", asset + "_ticks.parquet"):
        for cand in root.rglob(name):
            return cand
    raise FileNotFoundError(asset)


def iter_sessions(pfile: Path):
    pf = pq.ParquetFile(pfile)
    names = [pf.metadata.row_group(0).column(i).path_in_schema for i in range(pf.metadata.row_group(0).num_columns)]
    ci = {n: i for i, n in enumerate(names)}
    need = ["ts_utc_ns", "price_ticks", "bid_ticks", "ask_ticks", "volume", "outside_regular"]
    for c in need:
        assert c in ci, "falta %s en %s" % (c, names)
    td_col, c_col, sel_col = ci["trade_date"], ci.get("contract", -1), ci.get("session_selected", -1)
    rg_by_td = defaultdict(list)
    for rg in range(pf.num_row_groups):
        st = pf.metadata.row_group(rg).column(td_col).statistics
        if st is not None and st.has_min_max and int(st.min) >= HOLDOUT_TRADE_DATE:
            continue
        key = int(st.min) if (st is not None and st.has_min_max and st.min == st.max) else -1
        rg_by_td[key].append(rg)
    lo_all = min(v[0] for v in WINDOWS.values())
    hi_all = max(v[1] for v in WINDOWS.values())
    # se cargan tambien las sesiones previas para ATR/volumen/gap causales
    for td in sorted(k for k in rg_by_td if lo_all <= k <= hi_all):
        rows_by_c, rgs_by_c = defaultdict(int), defaultdict(list)
        for rg in rg_by_td[td]:
            md = pf.metadata.row_group(rg)
            if sel_col >= 0:
                ss = md.column(sel_col).statistics
                if ss is not None and ss.has_min_max and ss.max is False:
                    continue
            sc = md.column(c_col).statistics if c_col >= 0 else None
            cn = str(sc.min) if (sc is not None and sc.has_min_max) else "PRIM"
            rows_by_c[cn] += md.num_rows
            rgs_by_c[cn].append(rg)
        if not rows_by_c:
            continue
        prim = max(rows_by_c.items(), key=lambda x: x[1])[0]
        t = pq.ParquetFile(pfile).read_row_groups(rgs_by_c[prim], columns=need)
        ts = t["ts_utc_ns"].to_numpy().astype(np.int64)
        if len(ts) < 1000:
            continue
        cols = {c: t[c].to_numpy() for c in need[1:]}
        if (np.diff(ts) < 0).any():
            o = np.argsort(ts, kind="mergesort")
            ts = ts[o]
            cols = {k: v[o] for k, v in cols.items()}
        m = ts < HOLDOUT_UTC_NS
        if not m.all():
            ts = ts[m]
            cols = {k: v[m] for k, v in cols.items()}
        yield td, prim, ts, cols["price_ticks"].astype(np.int64), cols["bid_ticks"].astype(np.int64), \
            cols["ask_ticks"].astype(np.int64), cols["volume"].astype(np.float64), cols["outside_regular"].astype(np.int8)


def open_ns_for(td: int) -> int:
    """09:30 ET del trade_date (la sesion Globex del trade_date empieza el dia anterior a las 18:00 ET)."""
    o = datetime(td // 10000, (td // 100) % 100, td % 100, 9, 30, tzinfo=ET)
    return int(o.timestamp()) * 1_000_000_000


def session_core(td, ts, px, bid, ask, vol, outreg):
    """Devuelve (record, descarte). record = dict con lo necesario para la Fase 0A (camino 1: ticks)."""
    # `outside_regular` NO sirve como bandera RTH en este release (diagnostico 2026-10-17: vale 0 en todo el
    # dia Globex 18:00-17:00 ET). RTH se define por RELOJ: 09:30 a 16:00 ET del trade_date.
    open_ns = open_ns_for(int(td))
    close_ns = open_ns + 390 * NS_MIN
    sel = (ts >= open_ns) & (ts <= close_ns)
    if sel.sum() < 500:
        return None, "sin_rth"
    ts, px, bid, ask, vol = ts[sel], px[sel], bid[sel], ask[sel], vol[sel]
    if not (open_ns <= ts[0] <= open_ns + 300 * 1_000_000_000):
        return None, "primer_print_fuera_de_0930_0935"
    t1030 = open_ns + 60 * NS_MIN
    w = ts < t1030
    if w.sum() < 100:
        return None, "pocos_prints_en_la_primera_hora"
    if (np.diff(ts[w]) > MAX_GAP_NS).any():
        return None, "hueco_mayor_60s_0930_1030"
    rec = {"td": td, "open_ns": open_ns, "open_px": int(px[0]), "rth_hi": int(px.max()), "rth_lo": int(px.min()),
           "rth_close": int(px[-1]), "early_close": bool(((ts >= open_ns + 330 * NS_MIN) & (ts < open_ns + 375 * NS_MIN)).sum() < 100), "n_ticks": int(len(ts))}
    h1130, h1545 = open_ns + 120 * NS_MIN, open_ns + 375 * NS_MIN
    rec["windows"] = {}
    for W in OR_MINS:
        tw = open_ns + W * NS_MIN
        inw = ts < tw
        if inw.sum() < 20:
            continue
        hi, lo = int(px[inw].max()), int(px[inw].min())
        post = ~inw
        pts, ppx, pbid, pask = ts[post], px[post], bid[post], ask[post]
        up = np.flatnonzero(ppx > hi)
        dn = np.flatnonzero(ppx < lo)
        iu = int(up[0]) if len(up) else -1
        idn = int(dn[0]) if len(dn) else -1

        def first_break_info():
            cands = [(pts[i], s, i) for s, i in (("up", iu), ("down", idn)) if i >= 0]
            if not cands:
                return None
            t, s, i = min(cands)
            return t, s, i
        fb = first_break_info()
        d = {"hi": hi, "lo": lo, "width": hi - lo, "vol_or": float(vol[inw].sum()), "close_px": int(px[inw][-1])}
        for tag, tmax in (("1130", h1130), ("1545", h1545)):
            u_ok = iu >= 0 and pts[iu] <= tmax
            d_ok = idn >= 0 and pts[idn] <= tmax
            d["break_up_" + tag], d["break_dn_" + tag], d["break_both_" + tag], d["break_none_" + tag] = \
                bool(u_ok), bool(d_ok), bool(u_ok and d_ok), bool(not u_ok and not d_ok)
        if fb is not None and fb[0] <= h1545:
            t, side, i = fb
            d["first_side"] = side
            d["t_break_min"] = float((t - tw) / NS_MIN)
            sp = int(pask[i] - pbid[i]) if (pask[i] > 0 and pbid[i] > 0 and pask[i] >= pbid[i]) else -1
            trig = (hi + 1) if side == "up" else (lo - 1)
            slip = (int(pask[i]) - trig) if side == "up" else (trig - int(pbid[i]))
            d["spread_at_break"] = sp
            d["slip_proxy_ticks"] = int(slip) if sp >= 0 else None
            other_t = pts[idn] if side == "up" else pts[iu]
            other_i = idn if side == "up" else iu
            d["whipsaw_1130"] = bool(other_i >= 0 and other_t <= h1130 and t <= h1130)
        rec["windows"][W] = d
    # primera vela de 5 minutos (direccion) y spread 09:45-10:30 por tramo de 5 min
    f5 = ts < open_ns + 5 * NS_MIN
    rec["first5_dir"] = int(np.sign(px[f5][-1] - px[0])) if f5.any() else 0
    sp_rows = (ts >= open_ns + 15 * NS_MIN) & (ts < t1030) & (bid > 0) & (ask >= bid)
    sp = (ask - bid)[sp_rows]
    bucket = ((ts[sp_rows] - open_ns) // (5 * NS_MIN)).astype(int)
    rec["spread_by_bucket"] = {int(b): sp[bucket == b][::10].tolist()[:2000] for b in np.unique(bucket)}
    # camino 2 independiente: barras de 1 minuto con groupby (pandas) -> ancho y minuto de la primera ruptura
    m = ((ts - open_ns) // NS_MIN).astype(np.int64)
    g = pd.DataFrame({"m": m, "p": px}).groupby("m")["p"].agg(["max", "min"])
    chk = {}
    for W in OR_MINS:
        if W not in rec["windows"]:
            continue
        gw = g[g.index < W]
        hi2, lo2 = int(gw["max"].max()), int(gw["min"].min())
        gp = g[g.index >= W]
        mu = gp.index[gp["max"] > hi2]
        md = gp.index[gp["min"] < lo2]
        first_up2 = int(mu[0]) if len(mu) else -1
        first_dn2 = int(md[0]) if len(md) else -1
        d = rec["windows"][W]
        ok_w = (hi2 == d["hi"]) and (lo2 == d["lo"])
        # minuto (desde la apertura) del primer cruce segun ticks, por lado
        pts_all = ts[ts >= open_ns + W * NS_MIN]
        ppx_all = px[ts >= open_ns + W * NS_MIN]
        u1 = np.flatnonzero(ppx_all > d["hi"])
        d1 = np.flatnonzero(ppx_all < d["lo"])
        mu1 = int((pts_all[u1[0]] - open_ns) // NS_MIN) if len(u1) else -1
        md1 = int((pts_all[d1[0]] - open_ns) // NS_MIN) if len(d1) else -1
        chk[W] = bool(ok_w and mu1 == first_up2 and md1 == first_dn2)
    rec["second_path_agrees"] = chk
    return rec, None


def quantiles(a, qs=(5, 25, 50, 75, 95)):
    a = np.asarray([x for x in a if x is not None and not (isinstance(x, float) and math.isnan(x))], dtype=float)
    return [float(np.percentile(a, q)) for q in qs] if len(a) else []


def summarize_asset(records, discards, window_name):
    lo, hi = WINDOWS[window_name]
    R = [r for r in records if lo <= r["td"] <= hi]
    out = {"window": [lo, hi], "n_sessions_valid": len(R), "discards": dict(discards.get(window_name, {})),
           "n_early_close": int(sum(1 for r in R if r["early_close"])),
           "second_path_all_agree": all(all(r["second_path_agrees"].values()) for r in R) if R else None,
           "second_path_disagreements": int(sum(1 for r in R for v in r["second_path_agrees"].values() if not v))}
    gw = {}
    for W in OR_MINS:
        D = [(r, r["windows"][W]) for r in R if W in r["windows"]]
        if not D:
            continue
        widths = [d["width"] for _, d in D]
        atr_w = [d["width"] / r["atr14"] for r, d in D if r.get("atr14")]
        pct_w = [d["width"] * TICK / (r["open_px"] * TICK) * 100.0 for r, d in D]
        e = {"n": len(D), "width_ticks_q": quantiles(widths), "width_over_ATR14_q": quantiles(atr_w),
             "width_pct_of_price_q": quantiles(pct_w),
             "cost_over_width_median": float(np.median([COST_RT_TICKS / max(w, 1) for w in widths])),
             "cost_over_width_gt25pct_frac": float(np.mean([COST_RT_TICKS / max(w, 1) > 0.25 for w in widths]))}
        for tag in ("1130", "1545"):
            e["P_break_up_" + tag] = float(np.mean([d["break_up_" + tag] for _, d in D]))
            e["P_break_dn_" + tag] = float(np.mean([d["break_dn_" + tag] for _, d in D]))
            e["P_both_" + tag] = float(np.mean([d["break_both_" + tag] for _, d in D]))
            e["P_none_" + tag] = float(np.mean([d["break_none_" + tag] for _, d in D]))
        fb = [d for _, d in D if "t_break_min" in d]
        e["n_with_break_1545"] = len(fb)
        e["t_break_min_q"] = quantiles([d["t_break_min"] for d in fb])
        e["first_side_up_frac"] = float(np.mean([d["first_side"] == "up" for d in fb])) if fb else None
        e["whipsaw_1130_frac_among_breaks"] = float(np.mean([d.get("whipsaw_1130", False) for d in fb])) if fb else None
        e["spread_at_break_q"] = quantiles([d["spread_at_break"] for d in fb if d.get("spread_at_break", -1) >= 0])
        e["slip_proxy_ticks_q"] = quantiles([d["slip_proxy_ticks"] for d in fb if d.get("slip_proxy_ticks") is not None])
        gw[str(W)] = e
    out["by_window_minutes"] = gw
    # marginales de filtros para la ventana primaria (solo sesiones con ruptura hasta 15:45)
    Dp = [(r, r["windows"][PRIMARY_W]) for r in R if PRIMARY_W in r["windows"] and "t_break_min" in r["windows"][PRIMARY_W]]
    marg = {"n_with_break": len(Dp)}

    def terc(name, vals):
        v = np.asarray([x for x in vals if x is not None and not math.isnan(x)], dtype=float)
        if len(v) < 30:
            marg[name] = {"n": int(len(v))}
            return
        c1, c2 = np.percentile(v, [33.33, 66.67])
        marg[name] = {"n": int(len(v)), "cut_33_67": [float(c1), float(c2)],
                      "n_per_tercile": [int((v <= c1).sum()), int(((v > c1) & (v <= c2)).sum()), int((v > c2).sum())],
                      "q": quantiles(v)}
    terc("rel_volume_or_vs_20prior", [r.get("relvol15") for r, d in Dp])
    terc("or_width_over_ATR14", [d["width"] / r["atr14"] if r.get("atr14") else None for r, d in Dp])
    terc("abs_gap_over_ATR14", [abs(r["gap_ticks"]) / r["atr14"] if (r.get("atr14") and r.get("gap_ticks") is not None) else None for r, d in Dp])
    marg["first5_dir_counts"] = {"up": int(sum(1 for r, d in Dp if r["first5_dir"] > 0)),
                                "down": int(sum(1 for r, d in Dp if r["first5_dir"] < 0)),
                                "flat": int(sum(1 for r, d in Dp if r["first5_dir"] == 0))}
    out["filter_marginals_W15"] = marg
    # spread por tramo de 5 minutos entre 09:45 y 10:30
    sp_b = defaultdict(list)
    for r in R:
        for b, v in r["spread_by_bucket"].items():
            sp_b[b].extend(v)
    out["spread_ticks_by_5min_bucket_from_0945"] = {str(b): quantiles(v) for b, v in sorted(sp_b.items())}
    return out


def add_causal_features(records_sorted):
    """ATR14 diario, volumen relativo del rango de 15 min y gap, todos con sesiones PREVIAS."""
    tr_hist, vol_hist, prev_close = [], [], None
    for r in records_sorted:
        if prev_close is not None:
            r["gap_ticks"] = r["open_px"] - prev_close
        else:
            r["gap_ticks"] = None
        r["atr14"] = float(np.mean(tr_hist[-14:])) if len(tr_hist) >= 14 else None
        v15 = r["windows"].get(PRIMARY_W, {}).get("vol_or")
        r["relvol15"] = (v15 / float(np.median(vol_hist[-20:]))) if (v15 is not None and len(vol_hist) >= 20 and np.median(vol_hist[-20:]) > 0) else None
        trange = r["rth_hi"] - r["rth_lo"]
        if prev_close is not None:
            trange = max(r["rth_hi"], prev_close) - min(r["rth_lo"], prev_close)
        tr_hist.append(float(trange))
        if v15 is not None:
            vol_hist.append(float(v15))
        prev_close = r["rth_close"]


def run_asset(asset):
    t0 = time.time()
    pfile = locate_parquet(asset)
    records, discards = [], defaultdict(lambda: defaultdict(int))
    for td, prim, ts, px, bid, ask, vol, outreg in iter_sessions(pfile):
        rec, why = session_core(td, ts, px, bid, ask, vol, outreg)
        wn = next((n for n, (a, b) in WINDOWS.items() if a <= td <= b), "WARMUP")
        if rec is None:
            discards[wn][why] += 1
            continue
        rec["contract"] = prim
        records.append(rec)
        if len(records) % 40 == 0:
            print(asset, "sesiones validas", len(records), "t=%.0fs" % (time.time() - t0), flush=True)
    records.sort(key=lambda r: r["td"])
    add_causal_features(records)
    res = {w: summarize_asset(records, discards, w) for w in WINDOWS}
    res["n_sessions_loaded_valid_total"] = len(records)
    res["warmup_discards"] = dict(discards.get("WARMUP", {}))
    flags = {}
    for w in WINDOWS:
        s = res[w]
        e = s["by_window_minutes"].get(str(PRIMARY_W), {})
        flags[w] = {"N_with_break_ge_150": bool(e.get("n_with_break_1545", 0) >= 150),
                    "N_with_break": e.get("n_with_break_1545"),
                    "cost_over_width_median_le_10pct": bool(e.get("cost_over_width_median", 1) <= 0.10),
                    "cost_over_width_median": e.get("cost_over_width_median"),
                    "integrity_second_path_agrees": s["second_path_all_agree"],
                    "discard_fraction": (sum(s["discards"].values()) / max(1, sum(s["discards"].values()) + s["n_sessions_valid"]))}
    res["preliminary_flags_vs_manifest_sec5"] = flags
    res["MDE_grid_R_80pct_2p5onesided"] = {
        w: {str(sd): float(2.8 * sd / math.sqrt(max(1, flags[w]["N_with_break"] or 1))) for sd in (0.5, 1.0, 1.5, 2.0)}
        for w in WINDOWS}
    res["FINAL_GATE"] = "PENDIENTE_0B (el MDE necesita la SD de la extension, que mide 0B)"
    res["per_session"] = [{"td": r["td"], "contract": r["contract"], "w15_width": r["windows"].get(15, {}).get("width"),
                           "w5_width": r["windows"].get(5, {}).get("width"), "w15_first_side": r["windows"].get(15, {}).get("first_side"),
                           "w15_t_break_min": r["windows"].get(15, {}).get("t_break_min")} for r in records]
    res["elapsed_seconds"] = round(time.time() - t0, 1)
    return res


def main():
    out_dir = Path(os.environ.get("STUDY_OUT", "/kaggle/working"))
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"spec_id": "EXP-ORB-F0A-V1", "manifest": "ORB_FASE0_MANIFIESTO_20261017.md",
               "windows": WINDOWS, "holdout_touched": False, "returns_computed": False}
    for asset in ("ES", "NQ"):
        try:
            summary[asset] = run_asset(asset)
        except Exception as e:  # se declara, no se oculta
            summary[asset] = {"ERROR": repr(e)[:500]}
            print("ORB_F0A_ERROR", asset, repr(e)[:500], flush=True)
    print("=== EXP_ORB_F0A_SUMMARY_START ===", flush=True)
    txt = json.dumps(summary, indent=1, default=float)
    print(txt[:200000], flush=True)
    print("=== EXP_ORB_F0A_SUMMARY_END ===", flush=True)
    (out_dir / "EXP_ORB_F0A_RESULTS.json").write_text(txt, encoding="utf-8")



# ======================================================================================
# ORB Fase 0B (descriptiva, toca precios posteriores a la ruptura; manifiesto seccion 4).
# E_t = signo(ruptura) x (P_t - nivel_roto) / ancho_del_rango, sin stop ni objetivo. Una celda primaria:
# rango de 15 min, ruptura por toque (primer print fuera del rango), E a 11:30 y a 15:45 ET.
# Nulo (A2): permutacion de signos entre dias conservando el desplazamiento de cada dia. Sin grilla de decision.
# ======================================================================================
NULL_REPS = 2000
HORIZONS = {"1130": 120, "1545": 375}           # minutos desde 09:30


def price_at(ts, px, t):
    """A2: ultimo print ESTRICTAMENTE anterior al reloj t (causal; coincide con el camino por minutos)."""
    i = int(np.searchsorted(ts, t, side="left")) - 1
    return int(px[i]) if i >= 0 else None


def price_at_incl(ts, px, t):
    """Diagnostico A2: convencion anterior (print en t incluido)."""
    i = int(np.searchsorted(ts, t, side="right")) - 1
    return int(px[i]) if i >= 0 else None


def session_ext(td, ts, px):
    open_ns = open_ns_for(int(td))
    sel = (ts >= open_ns) & (ts <= open_ns + 390 * NS_MIN)
    if sel.sum() < 500:
        return None, "sin_rth"
    ts, px = ts[sel], px[sel]
    if not (open_ns <= ts[0] <= open_ns + 300 * 1_000_000_000):
        return None, "primer_print_fuera_de_0930_0935"
    w = ts < open_ns + 60 * NS_MIN
    if (np.diff(ts[w]) > MAX_GAP_NS).any():
        return None, "hueco_mayor_60s_0930_1030"
    if ((ts >= open_ns + 330 * NS_MIN) & (ts < open_ns + 375 * NS_MIN)).sum() < 100:
        return None, "cierre_temprano"
    out = {"td": td}
    # camino 2 (independiente): ultimo precio por minuto (groupby) para P_t
    m = ((ts - open_ns) // NS_MIN).astype(np.int64)
    last_by_min = pd.DataFrame({"m": m, "p": px}).groupby("m")["p"].last()
    for W in OR_MINS:
        tw = open_ns + W * NS_MIN
        inw = ts < tw
        if inw.sum() < 20:
            continue
        hi, lo = int(px[inw].max()), int(px[inw].min())
        width = hi - lo
        if width <= 0:
            continue
        post = ts >= tw
        pts, ppx = ts[post], px[post]
        up, dn = np.flatnonzero(ppx > hi), np.flatnonzero(ppx < lo)
        iu = int(up[0]) if len(up) else -1
        idn = int(dn[0]) if len(dn) else -1
        d = {"width": width, "hi": hi, "lo": lo}
        for tag, mins in HORIZONS.items():
            t = open_ns + mins * NS_MIN
            P = price_at(ts, px, t)
            d["P_" + tag] = P
            P2 = int(last_by_min[last_by_min.index <= mins - 1].iloc[-1]) if (last_by_min.index <= mins - 1).any() else None
            d["P2_" + tag] = P2
            d["Pincl_" + tag] = price_at_incl(ts, px, t)
            d["n_at_t_" + tag] = int((ts == t).sum())
            # contrafactuales con el mismo camino: largo desde hi y corto desde lo
            d["Eup_" + tag] = (P - hi) / width
            d["Edn_" + tag] = (lo - P) / width
        cands = [(pts[i], s, i) for s, i in (("up", iu), ("down", idn)) if i >= 0]
        if cands:
            t_b, side, i_b = min(cands)
            d["side"] = side
            d["entry_px"] = int(ppx[i_b])
            d["t_break_min"] = float((t_b - tw) / NS_MIN)
            for tag, mins in HORIZONS.items():
                if t_b <= open_ns + mins * NS_MIN:
                    sgn = 1.0 if side == "up" else -1.0
                    lvl = hi if side == "up" else lo
                    P = d["P_" + tag]
                    d["E_" + tag] = sgn * (P - lvl) / width
                    d["Eentry_" + tag] = sgn * (P - d["entry_px"]) / width
                    d["Eabs_" + tag] = abs(P - lvl) / width
                    d["s_" + tag] = sgn
                    d["D_" + tag] = (P - lvl) / width
        out[W] = d
    return out, None


def ci_mean(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), float("nan"), float("nan"), n
    mu, sd = float(x.mean()), float(x.std(ddof=1))
    se = sd / math.sqrt(n)
    return mu, se, mu - 1.96 * se, mu + 1.96 * se, n


def summarize_ext(R, W, tag, rng):
    rows = [r[W] for r in R if W in r and ("E_" + tag) in r[W]]
    if not rows:
        return {}
    E = np.array([d["E_" + tag] for d in rows])
    Ee = np.array([d["Eentry_" + tag] for d in rows])
    Ea = np.array([d["Eabs_" + tag] for d in rows])
    mu, se, lo, hi, n = ci_mean(E)
    # A2 - nulo de deriva (manifiesto secc. 4): se PERMUTAN los signos de ruptura entre los dias, conservando el
    # desplazamiento D_i = (P_t - nivel_roto_i)/ancho_i de cada dia (y por tanto la deriva del periodo).
    sg = np.array([d["s_" + tag] for d in rows])
    D = np.array([d["D_" + tag] for d in rows])
    null_means = np.array([float((sg[rng.permutation(len(sg))] * D).mean()) for _ in range(NULL_REPS)])
    p_null = float((1 + np.sum(null_means >= mu)) / (NULL_REPS + 1.0))
    p_two = float((1 + np.sum(np.abs(null_means - null_means.mean()) >= abs(mu - null_means.mean()))) / (NULL_REPS + 1.0))
    eup = np.array([d["Eup_" + tag] for d in rows])
    edn = np.array([d["Edn_" + tag] for d in rows])
    # SD de la extension firmada (insumo del MDE)
    return {"n_days": int(n), "mean_E": mu, "se": se, "ci95": [lo, hi], "sd": float(E.std(ddof=1)),
            "quantiles_E_5_25_50_75_95": [float(np.percentile(E, q)) for q in (5, 25, 50, 75, 95)],
            "mean_E_from_entry_print": float(Ee.mean()), "mean_abs_extension": float(Ea.mean()),
            "frac_E_positive": float((E > 0).mean()),
            "mean_E_long_from_hi_all_days": float(eup.mean()), "mean_E_short_from_lo_all_days": float(edn.mean()),
            "null_sign_permutation": {"mean": float(null_means.mean()), "p975": float(np.percentile(null_means, 97.5)),
                                 "p_value_one_sided": p_null, "p_value_two_sided": p_two},
            "MDE_80pct_2p5onesided_R": float(2.8 * E.std(ddof=1) / math.sqrt(n)),
            "second_path_price_disagreements": int(sum(1 for d in rows if d["P_" + tag] != d["P2_" + tag])),
            "diag_incl_convention_price_differs_from_strict": int(sum(1 for d in rows if d["P_" + tag] != d["Pincl_" + tag])),
            "diag_days_with_print_exactly_at_t": int(sum(1 for d in rows if d["n_at_t_" + tag] > 0))}


def run_asset_b(asset):
    t0 = time.time()
    pfile = locate_parquet(asset)
    recs, disc = [], defaultdict(lambda: defaultdict(int))
    for td, prim, ts, px, bid, ask, vol, outreg in iter_sessions(pfile):
        wn = next((n for n, (a, b) in WINDOWS.items() if a <= td <= b), None)
        if wn is None:
            continue
        r, why = session_ext(td, ts, px)
        if r is None:
            disc[wn][why] += 1
            continue
        r["win"] = wn
        recs.append(r)
    rng = np.random.default_rng(20261017)
    out = {"discards": {k: dict(v) for k, v in disc.items()}}
    for wn in WINDOWS:
        R = [r for r in recs if r["win"] == wn]
        o = {"n_sessions_valid": len(R)}
        for W in OR_MINS:
            for tag in HORIZONS:
                o["W%d_%s" % (W, tag)] = summarize_ext(R, W, tag, rng)
        out[wn] = o
    # veredicto automatico (manifiesto secc. 5) sobre la celda primaria: 15 min, E al cierre 15:45, DISC
    p = out["DISC"]["W%d_1545" % PRIMARY_W]
    cl = out["CLEAN"]["W%d_1545" % PRIMARY_W]
    verdict = "ABSTENCION"
    if p:
        mde_ok = p["MDE_80pct_2p5onesided_R"] <= 0.30
        n_ok = p["n_days"] >= 150
        within = (p["ci95"][0] >= -0.10) and (p["ci95"][1] <= 0.10)
        if p["n_days"] < 100 or (within and p["null_sign_permutation"]["p_value_one_sided"] > 0.10):
            verdict = "NO_GO"
        elif n_ok and mde_ok:
            verdict = "GO_FASE1"
        out["gate_inputs"] = {"n_ok_ge_150": n_ok, "MDE_ok_le_0.30R": mde_ok, "ci95_within_pm0.10R": within,
                              "p_null": p["null_sign_permutation"]["p_value_one_sided"]}
    out["VERDICT_PRIMARY_GATE_0B"] = verdict
    out["clean_window_primary_cell_descriptive"] = cl
    out["elapsed_seconds"] = round(time.time() - t0, 1)
    return out


def main_b():
    out_dir = Path(os.environ.get("STUDY_OUT", "/kaggle/working"))
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"spec_id": "EXP-ORB-F0B-V2-A2", "manifest": "ORB_FASE0_MANIFIESTO_20261017.md (secc. 4 y 5)",
               "windows": WINDOWS, "holdout_touched": False,
               "definition": "E_t = sign(break) * (P_t - broken_level) / OR_width; sin stop ni objetivo; nulo = permutacion de signos entre dias (A2)"}
    for asset in ("ES", "NQ"):
        try:
            summary[asset] = run_asset_b(asset)
        except Exception as e:
            summary[asset] = {"ERROR": repr(e)[:500]}
            print("ORB_F0B_ERROR", asset, repr(e)[:500], flush=True)
    txt = json.dumps(summary, indent=1, default=float)
    print("=== EXP_ORB_F0B_SUMMARY_START ===", flush=True)
    print(txt[:180000], flush=True)
    print("=== EXP_ORB_F0B_SUMMARY_END ===", flush=True)
    (out_dir / "EXP_ORB_F0B_RESULTS.json").write_text(txt, encoding="utf-8")




# ======================================================================================
# ORB H1 - Nivel V (factibilidad, DESCRIPTIVO, sin compuerta ni alfa; manifiesto H1 enmienda A1).
# Futuros ES/NQ (trades con volumen). Se concatena tras orb_f0a_kernel + orb_f0b_tail (sin sus main).
# V1: volumen relativo del rango de 15 min (OR15 vol / mediana de los 20 previos); favorable > 1.
# V2: conductividad del "por donde": densidad de volumen/tick del perfil RTH previo en el corredor de un ancho
#     por delante del nivel roto / densidad media del perfil previo; favorable < 1.
# ======================================================================================
PERM_REPS_V = 2000


def rth_profile(ts, px, vol, o):
    sel = (ts >= o) & (ts <= o + 390 * NS_MIN)
    if sel.sum() < 500:
        return None
    p, v = px[sel], vol[sel]
    pmin = int(p.min())
    arr = np.bincount((p - pmin).astype(np.int64), weights=v)
    return pmin, arr


def corridor_ratio(prof, lvl, width, side):
    pmin, arr = prof
    if side == "up":
        lo_t, hi_t = lvl + 1, lvl + width
    else:
        lo_t, hi_t = lvl - width, lvl - 1
    a, b = lo_t - pmin, hi_t - pmin
    a2, b2 = max(a, 0), min(b, len(arr) - 1)
    vol_in = float(arr[a2:b2 + 1].sum()) if b2 >= a2 else 0.0
    dens = vol_in / max(width, 1)
    ref = float(arr.sum()) / len(arr)
    return dens / ref if ref > 0 else None


def v_test(E, fav, rng):
    n = len(E)
    if fav.sum() < 8 or (~fav).sum() < 8:
        return {"n": int(n), "n_fav": int(fav.sum()), "n_unfav": int((~fav).sum()), "undefined": True}
    a, b = E[fav], E[~fav]
    d = float(a.mean() - b.mean())
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    nm = np.empty(PERM_REPS_V)
    for k in range(PERM_REPS_V):
        pm = rng.permutation(fav)
        nm[k] = E[pm].mean() - E[~pm].mean()
    return {"n": int(n), "n_fav": int(fav.sum()), "n_unfav": int((~fav).sum()), "mean_fav": float(a.mean()), "mean_unfav": float(b.mean()),
            "sd_fav": float(a.std(ddof=1)), "sd_unfav": float(b.std(ddof=1)), "D": d, "D_se": se, "D_ci95": [d - 1.96 * se, d + 1.96 * se],
            "MDE_D_80pct": 2.8 * se, "p_one_sided_DESCRIPTIVE": float((1 + np.sum(nm >= d)) / (PERM_REPS_V + 1.0))}


def run_asset_v(asset):
    t0 = time.time()
    pfile = locate_parquet(asset)
    prev_prof, or15_hist, rows = None, [], []
    for td, prim, ts, px, bid, ask, vol, outreg in iter_sessions(pfile):
        o = open_ns_for(int(td))
        wn = next((n for n, (a, b) in WINDOWS.items() if a <= td <= b), None)
        r, why = session_ext(td, ts, px)
        if r is not None and wn is not None and PRIMARY_W in r and "E_1545" in r[PRIMARY_W] and prev_prof is not None and len(or15_hist) >= 20:
            d = r[PRIMARY_W]
            side, lvl = d["side"], (d["hi"] if d["side"] == "up" else d["lo"])
            rel = float(vol[(ts >= o) & (ts < o + 15 * NS_MIN)].sum()) / float(np.median(or15_hist[-20:]))
            ratio = corridor_ratio(prev_prof, int(lvl), int(d["width"]), side)
            rows.append({"win": wn, "E": d["E_1545"], "relvol": rel, "ratio": ratio})
        pr = rth_profile(ts, px, vol, o)
        if pr is not None:
            prev_prof = pr
            or15_hist.append(float(vol[(ts >= o) & (ts < o + 15 * NS_MIN)].sum()))
    rng = np.random.default_rng(20261017)
    out = {"n_rows": len(rows)}
    for wn in WINDOWS:
        R = [r for r in rows if r["win"] == wn]
        if not R:
            continue
        E = np.array([r["E"] for r in R])
        rel = np.array([r["relvol"] for r in R])
        rt = np.array([np.nan if r["ratio"] is None else r["ratio"] for r in R])
        ok2 = ~np.isnan(rt)
        out[wn] = {"n_days": len(R), "base_mean_E": float(E.mean()), "base_sd": float(E.std(ddof=1)),
                   "V1_relvol_gt_1": v_test(E, rel > 1.0, rng),
                   "V2_corridor_density_lt_1": v_test(E[ok2], (rt < 1.0)[ok2], rng),
                   "relvol_quantiles": [float(np.percentile(rel, q)) for q in (5, 25, 50, 75, 95)],
                   "ratio_quantiles": [float(np.nanpercentile(rt, q)) for q in (5, 25, 50, 75, 95)],
                   "corr_relvol_vs_log_ratio": float(np.corrcoef(np.log(rel[ok2]), np.log(rt[ok2] + 1e-6))[0, 1])}
    out["elapsed_s"] = round(time.time() - t0, 1)
    return out


def main_v():
    out_dir = Path(os.environ.get("STUDY_OUT", "/kaggle/working"))
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"spec_id": "EXP-ORB-H1-V-V1", "manifest": "ORB_CFD_H1_HERRAMIENTAS_MANIFIESTO_20261017.md (enmienda A1, nivel V)",
               "windows": WINDOWS, "holdout_touched": False, "nature": "factibilidad descriptiva, sin compuerta ni alfa"}
    for asset in ("ES", "NQ"):
        try:
            summary[asset] = run_asset_v(asset)
        except Exception as e:
            import traceback
            summary[asset] = {"ERROR": repr(e)[:500], "tb": traceback.format_exc()[-1500:]}
            print("ERR", asset, repr(e)[:500], flush=True)
    txt = json.dumps(summary, indent=1, default=float)
    (out_dir / "EXP_ORB_H1_V_RESULTS.json").write_text(txt, encoding="utf-8")
    print("=== H1V_START ===\n" + txt[:150000] + "\n=== H1V_END ===", flush=True)


if __name__ == "__main__":
    main_v()

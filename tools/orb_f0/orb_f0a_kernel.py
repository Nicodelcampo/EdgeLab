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


def open_ns_for(ts_first_rth: int) -> int:
    d = datetime.fromtimestamp(ts_first_rth / 1e9, ET)
    o = datetime(d.year, d.month, d.day, 9, 30, tzinfo=ET)
    return int(o.timestamp()) * 1_000_000_000


def session_core(td, ts, px, bid, ask, vol, outreg):
    """Devuelve (record, descarte). record = dict con lo necesario para la Fase 0A (camino 1: ticks)."""
    rth_idx = np.flatnonzero(outreg == 0)
    if len(rth_idx) < 500:
        return None, "sin_rth"
    i0 = rth_idx[0]
    open_ns = open_ns_for(int(ts[i0]))
    if not (open_ns <= ts[i0] <= open_ns + 300 * 1_000_000_000):
        return None, "primer_print_fuera_de_0930_0935"
    sel = ts >= open_ns
    ts, px, bid, ask, vol, outreg = ts[sel], px[sel], bid[sel], ask[sel], vol[sel], outreg[sel]
    keep = outreg == 0
    ts, px, bid, ask, vol = ts[keep], px[keep], bid[keep], ask[keep], vol[keep]
    t1030 = open_ns + 60 * NS_MIN
    w = ts < t1030
    if w.sum() < 100:
        return None, "pocos_prints_en_la_primera_hora"
    if (np.diff(ts[w]) > MAX_GAP_NS).any():
        return None, "hueco_mayor_60s_0930_1030"
    rec = {"td": td, "open_ns": open_ns, "open_px": int(px[0]), "rth_hi": int(px.max()), "rth_lo": int(px.min()),
           "rth_close": int(px[-1]), "early_close": bool(ts[-1] < open_ns + 330 * NS_MIN), "n_ticks": int(len(ts))}
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


if __name__ == "__main__":
    main()

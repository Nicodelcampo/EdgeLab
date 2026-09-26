#!/usr/bin/env python3
r"""Capa TBZ-E2 para el visor unificado: TODA la lógica medida, sobre el gráfico continuo de 25 ticks.

    .venv\Scripts\python tools\build_tbz_e2_layer.py --asset ES_03-26_202601_25T_HFT

Por cada sesión del bundle (sólo exploración, <= 2026-03-31) escribe
`viewer/nt8_bridge/bundles/tbze2/<asset>/<fecha>.json` con:
- franjas (rápidas y tramos N2, las cuatro configuraciones): ventana de detección, vela de disparo, umbral k·σ, A→B,
  extremo, confirmación, descriptores y perfil de volumen izquierdo (as-of el inicio);
- eventos E0–E3 del censo, con sus descriptores;
- operaciones de los tres modos (hacia A→A, hacia A→HVN, hacia B→B) re-simuladas con la MISMA función de la
  medición (`tbz_e2.simulate`), más la hora de salida para dibujarlas (se verifica igualdad con la medición);
- EMA20/EMA50/SMA200 de 1 min y VWAP de sesión.

Muestra desenlaces: por eso sólo acepta la partición de exploración ya medida (P-TBZ-EXP). Abr–jun queda cerrado.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import tbz_e2 as TB  # noqa: E402
from edgelab.bridge.bars import build_tick_bars  # noqa: E402
from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.research.tbz_bands import causal_sigma, expansion_bands  # noqa: E402

NS = TB.NS
SPEC = REPO / "docs" / "specs" / "SPEC_TBZ_E2_V1_20260925.json"
OUTDIR = TB.BUNDLES / "tbze2"


def r3(x):
    return None if x is None or not np.isfinite(x) else round(float(x), 3)


def sim_with_exit(ts, px, bid, ask, t_ev, tdir, stop, target, end_ns, comm):
    """Igual que `tbz_e2.simulate` pero devuelve también los instantes de entrada y salida."""
    i = int(np.searchsorted(ts, t_ev + TB.LAT_NS))
    if i >= len(ts):
        return None
    j1 = max(int(np.searchsorted(ts, min(int(ts[i]) + TB.TMAX_S * NS, end_ns))), i + 1)
    seg = px[i:j1]
    hs, ht = (seg <= stop, seg >= target + 1) if tdir == 1 else (seg >= stop, seg <= target - 1)
    ks = int(np.argmax(hs)) if hs.any() else 10**12
    kt = int(np.argmax(ht)) if ht.any() else 10**12
    k = j1 - 1 - i if ks == kt == 10**12 else min(ks, kt)
    ref = TB.simulate(ts, px, bid, ask, t_ev, tdir, stop, target, end_ns, comm)
    return ref, int(ts[i]), int(ts[i + k])


def minute_lines(ts, px, vol):
    m_end, c = TB.minute_closes(ts, px)
    e20, e50 = TB.ema(c, 20), TB.ema(c, 50)
    s200 = pd.Series(c).rolling(200).mean().to_numpy()
    m = ts // (60 * NS); last = np.flatnonzero(np.r_[m[1:] != m[:-1], True])
    vw = np.cumsum(px * vol)[last] / np.maximum(np.cumsum(vol)[last], 1)
    return dict(t=[int(t // NS) for t in m_end], ema20=[r3(v) for v in e20], ema50=[r3(v) for v in e50],
                sma200=[r3(v) for v in s200], vwap=[r3(v) for v in vw])


def session_layer(m, s, cen_dir):
    td = str(s["trade_date"])
    E = pd.read_parquet(cen_dir / f"{td}.parquet")
    Bd = pd.read_parquet(cen_dir / f"{td}_bands.parquet")
    if str(E["contract"].iloc[0]) != m["contract"]:
        return None, "CENSO_DE_OTRO_CONTRATO"
    start, end = int(s["start_utc_ns"]), int(s["end_utc_ns"])
    tk = load_canonical_parquet(m["source_path"], contract=m["contract"], start_utc_ns=start, end_utc_ns=end)
    ts, px, vol = tk.ts_ns.astype(np.int64), tk.price_ticks.astype(np.int64), tk.volume.astype(float)
    bid, ask = tk.bid_ticks.astype(np.int64), tk.ask_ticks.astype(np.int64)
    if int(ts[-1]) >= TB.HOLDOUT_NS:
        raise ValueError("holdout decodificado")
    bars = build_tick_bars(tk, 25, reiniciar_por_sesion=True)
    tsec = (bars.end_ns // NS).astype(np.int64)
    o, h, l, c = (bars.open_t * bars.tick_size, bars.high_t * bars.tick_size, bars.low_t * bars.tick_size,
                  bars.close_t * bars.tick_size)
    zz = TB.zigzag(bars)
    sig20 = causal_sigma(bars.close_t.astype(np.int64), 20, 3000)
    raw = {}
    for W, k in TB.GRID:
        cfg = f"W{W}_k{k}"
        fast = expansion_bands(tsec, o, h, l, c, bars.tick_size, W=W, k=k, r=TB.R_END)
        for bi, b in enumerate(fast):
            raw[f"rapida:{cfg}:{bi}"] = (W, k, b)
        for bi, z in enumerate(TB.nonexp_null(zz, fast)):
            raw[f"tramo_N2:{cfg}:{bi}"] = (None, None, z)
    bands, bidx, vp_cache = [], {}, {}
    for r in Bd.to_dict("records"):
        W, k, b = raw[r["band"]]
        t_start, t_avail = int(bars.start_ns[b["i_start"]]), int(bars.end_ns[b["i_avail"]])
        assert (int(b["a_tick"]), int(b["b_tick"]), t_start, t_avail) == (r["A"], r["B"], r["t_start"], r["t_avail"]), r["band"]
        row = dict(id=r["band"], kind=r["kind"], cfg=r["cfg"], dir=int(r["dir"]), A=int(r["A"]), B=int(r["B"]), W=int(r["W"]),
                   t_start=t_start / NS, t_ext=int(bars.end_ns[b["i_ext"]]) / NS, t_avail=t_avail / NS,
                   W_sigma=r3(r["W_sigma"]), dur_s=r3(r["dur_s"]), speed_tps=r3(r["speed_tps"]), efficiency=r3(r["efficiency"]),
                   vol_total=r3(r["vol_total"]), vol_rel=r3(r["vol_rel"]), max_pullback_inside=r3(r["max_pullback_inside"]),
                   lvn_frac_inside=r3(r["lvn_frac_inside"]), n_lvn_inside=int(r["n_lvn_inside"]), phase=r["phase"],
                   dir_vs_trend30=r3(r["dir_vs_trend30"]))
        if r["kind"] == "rapida":
            it = int(b["i_trigger"])
            row.update(W_bars=W, k=k, sigma=r3(b["sigma_ticks"]), thr=r3(max(k * b["sigma_ticks"], 4)),
                       t_win0=int(bars.start_ns[max(it - W, 0)]) / NS, t_trigger=int(bars.end_ns[it]) / NS,
                       trig_close=int(bars.close_t[it]))
        else:
            row.update(sigma=r3(sig20[b["i_avail"]]))
        if t_start not in vp_cache:                              # el perfil depende sólo del inicio (as-of)
            vp = TB.left_profile(ts, px, vol, t_start)
            vp_cache[t_start] = None if vp is None else dict(
                lo=float(vp[0][0] - TB.VP_BIN / 2), bin=TB.VP_BIN, v=[round(float(x), 1) for x in vp[1]],
                hvn=[float(x) for x in vp[2]], lvn=[int(i) for i in np.flatnonzero(vp[3])], poc=float(vp[4]))
        row["vp_key"] = str(t_start)
        bidx[r["band"]] = len(bands)
        bands.append(row)
    events, n_chk = [], 0
    for e in E.itertuples(index=False):
        tr = {}
        for mode in TB.MODES:
            tdir, stop, target = TB.trade_plan(e, mode)
            out = sim_with_exit(ts, px, bid, ask, int(e.t_event), tdir, stop, target, end, TB.COMM[m["instrument"]])
            if out is None or out[0] is None:
                continue
            (entry, ex, pnl, why, x0), t_in, t_out = out
            risk = max(abs(stop - entry), 1)
            s_eff = max(tdir * (x0 - stop), 0); r_eff = max(tdir * ((target + tdir) - x0), 0)
            tr[mode] = dict(tdir=tdir, t_in=t_in / NS, entry=entry, x0=x0, stop=int(stop), target=int(target), t_out=t_out / NS,
                            exit=ex, why=why, pnl=r3(pnl), R=r3(pnl / risk), p0=r3(s_eff / (s_eff + r_eff)) if s_eff + r_eff else None)
            n_chk += 1
        events.append(dict(b=bidx[e.band], ev=e.event, t=int(e.t_event) / NS, p=int(e.p_event), depth=r3(e.depth), age_s=r3(e.age_s),
                           ext_beyond_B=r3(e.ext_beyond_B), n_prior_touches_B=int(e.n_prior_touches_B), vol_between=r3(e.vol_between),
                           approach_speed=r3(e.approach_speed), approach_vol_rel=r3(e.approach_vol_rel), skate_len=r3(e.skate_len),
                           tp_hvn_dist=r3(e.tp_hvn_dist), lvn_at_event=r3(e.lvn_at_event), poc_left_dist=r3(e.poc_left_dist),
                           ema20_align=r3(e.ema20_align), ema50_align=r3(e.ema50_align), sma200_align=r3(e.sma200_align),
                           vwap_align=r3(e.vwap_align), phase=e.phase, tr=tr))
    # control cruzado: los desenlaces tienen que ser los de la medición guardada
    xp = TB.OUT / "explore" / m["instrument"] / f"{td}.parquet"
    mism = None
    if xp.exists():
        X = pd.read_parquet(xp)
        got = {(bands[ev["b"]]["id"], ev["ev"], md): (t["entry"], t["exit"], t["why"]) for ev in events for md, t in ev["tr"].items()}
        mism = int(sum(got.get((r.band, r.event, r.mode)) != (r.entry, r.exit, r.why) for r in X.itertuples(index=False)))
    return dict(trade_date=td, contract=m["contract"], tick_size=float(bars.tick_size), start=start / NS, end=end / NS,
                event_window_s=TB.EVENT_WIN_S, lat_s=TB.LAT_NS / NS, tmax_s=TB.TMAX_S, comm_ticks=TB.COMM[m["instrument"]],
                r_end=TB.R_END, bands=bands, events=events, vp={str(k): v for k, v in vp_cache.items()},
                lines=minute_lines(ts, px, vol), check=dict(trades=n_chk, mismatches_vs_explore=mism)), "OK"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", required=True)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args(argv)
    m = json.loads((TB.BUNDLES / f"{a.asset}.manifest.json").read_text(encoding="utf-8"))
    cen_dir = TB.OUT / "census" / m["instrument"]
    fuera = [str(s["trade_date"]) for s in m["sessions"] if str(s["trade_date"]) > TB.EXP_END]
    if fuera:                                                    # antes de crear nada: el bundle entero queda afuera
        raise SystemExit(f"{fuera[0]} está fuera de exploración (> {TB.EXP_END}): la capa muestra desenlaces, no se construye.")
    od = OUTDIR / a.asset
    od.mkdir(parents=True, exist_ok=True)
    idx = []
    for s in m["sessions"]:
        td = str(s["trade_date"])
        if a.only and td not in a.only:
            continue
        if not (cen_dir / f"{td}.parquet").exists():
            print(td, "SIN_CENSO"); continue
        lay, st = session_layer(m, s, cen_dir)
        print(td, st, "" if lay is None else f"franjas={len(lay['bands'])} eventos={len(lay['events'])} {lay['check']}", flush=True)
        if lay is None:
            continue
        (od / f"{td}.json").write_text(json.dumps(lay, separators=(",", ":")), encoding="utf-8")
        idx.append(dict(trade_date=td, start=lay["start"], end=lay["end"], bands=len(lay["bands"]), events=len(lay["events"]),
                        mismatches=lay["check"]["mismatches_vs_explore"]))
    old = json.loads((od / "index.json").read_text(encoding="utf-8")) if (od / "index.json").exists() else {}
    have = {x["trade_date"]: x for x in old.get("sessions", [])}
    have.update({x["trade_date"]: x for x in idx})
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    (od / "index.json").write_text(json.dumps(dict(asset=a.asset, spec_id=spec["spec_id"], partition="P-TBZ-EXP",
                                                   code_commit=TB._git("rev-parse", "HEAD"), dirty=bool(TB._git("status", "--porcelain")),
                                                   sessions=sorted(have.values(), key=lambda x: x["trade_date"])), indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

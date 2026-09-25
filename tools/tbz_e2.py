#!/usr/bin/env python3
r"""TBZ-E2: la expansión como área de patinaje. Diseño y enmiendas: docs/research/TBZ_E2_PARAMETRIZACION_HOLISTICA_20260924.md
(§7, iteración 1). Registro de parámetros: docs/specs/TBZ_E2_PARAM_REGISTRY.json. OK de Nico: "OK censo TBZ y OK
manifiestos TBZ-E2 y TREND-MICRO".

Pasos:
  census   E2a, target-free: por sesión (ES primario; MES apoyo) detecta las franjas rápidas (grilla de 4) y las lentas
           (nulo N2, ventana ×6), calcula los descriptores G2 a G5 y los eventos E0 a E3 con su estado hasta el
           instante del evento. Nada mira el precio posterior a un evento. Escribe artifacts/tbz_e2/census/<inst>/<fecha>.parquet
  summary  resumen del censo: franjas y eventos por sesión, distribuciones, correlaciones (redundancia)

El agresor de ES no pasó la validación (P-93): acá no se usa ningún descriptor de agresor.
Lectura por sesión (filtro por row group). Como máximo 2 procesos (hubo dos cuelgues de la PC).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from edgelab.bridge.bars import build_tick_bars  # noqa: E402
from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.research.tbz_bands import causal_sigma, expansion_bands  # noqa: E402

BUNDLES = REPO / "viewer" / "nt8_bridge" / "bundles"
OUT = REPO / "artifacts" / "tbz_e2"
DOC = "docs/research/TBZ_E2_PARAMETRIZACION_HOLISTICA_20260924.md"
HOLDOUT_NS = 1_782_864_000 * 1_000_000_000          # 2026-07-01T00:00Z (frontera dura; los bundles ya la cumplen)
GRID = [(20, 2.5), (20, 4.0), (60, 2.5), (60, 4.0)]  # G1 primaria (la de E1)
R_END = 0.3                                           # retr_end por defecto
EVENT_WIN_S = 240 * 60
VP_LOOKBACK_S = 4 * 3600
VP_BIN = 2
VP_SMOOTH = 3
HVN_PROM = 1.0
LVN_Q = 0.25
ET = ZoneInfo("America/New_York")
NS = 1_000_000_000


def _git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def sessions(inst):
    """trade_date -> sesión del contrato con más ticks (regla de E1), desde los manifiestos de los bundles."""
    best = {}
    for f in sorted(glob.glob(str(BUNDLES / f"{inst}_[0-9]*_25T_HFT.manifest.json"))):
        m = json.loads(Path(f).read_text(encoding="utf-8"))
        for s in m["sessions"]:
            if int(s["end_utc_ns"]) > HOLDOUT_NS:
                continue
            td = str(s["trade_date"])
            cand = dict(trade_date=td, path=m["source_path"], contract=m["contract"], start=int(s["start_utc_ns"]),
                        end=int(s["end_utc_ns"]), ticks=int(s.get("ticks", 0)))
            if td not in best or cand["ticks"] > best[td]["ticks"]:
                best[td] = cand
    return [best[k] for k in sorted(best)]


def phase_et(ns):
    t = pd.Timestamp(int(ns), tz="UTC").tz_convert(ET)
    h = t.hour + t.minute / 60
    if 9.5 <= h < 10.5:
        return "apertura_RTH"
    if 10.5 <= h < 15.0:
        return "RTH"
    if 15.0 <= h < 17.0:
        return "cierre"
    if 3.0 <= h < 9.5:
        return "Europa"
    return "Asia"


def minute_closes(ts, px):
    """Cierres de 1 minuto (último trade de cada minuto) -> (fin del minuto en ns, cierre)."""
    m = ts // (60 * NS)
    last = np.r_[m[1:] != m[:-1], True]
    return (m[last] + 1) * 60 * NS, px[last].astype(float)


def ema(x, n):
    a = 2 / (n + 1)
    out = np.empty_like(x)
    acc = x[0]
    for i, v in enumerate(x):
        acc = a * v + (1 - a) * acc
        out[i] = acc
    return out


def left_profile(ts, px, vol, t_end_ns):
    """Perfil de volumen en [t_end - 4 h, t_end): bins de 2 ticks, suavizado 3. Devuelve (centros, perfil, hvn, lvn, poc)."""
    a, b = np.searchsorted(ts, t_end_ns - VP_LOOKBACK_S * NS), np.searchsorted(ts, t_end_ns)
    if b - a < 200:
        return None
    p, v = px[a:b], vol[a:b]
    lo = p.min() // VP_BIN * VP_BIN
    idx = (p - lo) // VP_BIN
    prof = np.bincount(idx, weights=v)
    if VP_SMOOTH > 1 and len(prof) >= VP_SMOOTH:
        prof = np.convolve(prof, np.ones(VP_SMOOTH) / VP_SMOOTH, mode="same")
    centers = lo + np.arange(len(prof)) * VP_BIN + VP_BIN / 2
    sd = prof.std() if prof.std() > 0 else 1.0
    hvn = [centers[i] for i in range(1, len(prof) - 1)
           if prof[i] >= prof[i - 1] and prof[i] >= prof[i + 1] and prof[i] - np.median(prof) >= HVN_PROM * sd]
    med = np.median(prof[prof > 0]) if (prof > 0).any() else 0
    lvn_mask = prof < LVN_Q * med
    return centers, prof, np.asarray(hvn), lvn_mask, float(centers[int(np.argmax(prof))])


def band_rows(kind, cfg, bands, bars, ts, px, vol, ctx):
    """Descriptores G2 por franja y eventos E0–E3 con G3/G4/G5 hasta el instante del evento."""
    tick = bars.tick_size
    C = bars.close_t.astype(float)
    Hh, Ll = bars.high_t, bars.low_t
    rows_b, rows_e = [], []
    for bi, b in enumerate(bands):
        d, A, B, W = b["dir"], b["a_tick"], b["b_tick"], max(b["width_ticks"], 1)
        i0, ie, ia = b["i_start"], b["i_ext"], b["i_avail"]
        t0_ns, text_ns, tav_ns = int(bars.start_ns[i0]), int(bars.end_ns[ie]), int(bars.end_ns[ia])
        dur = max((text_ns - t0_ns) / NS, 1e-3)
        path = np.abs(np.diff(C[i0:ie + 1])).sum()
        eff = abs(C[ie] - C[i0]) / path if path > 0 else np.nan
        a, e = np.searchsorted(ts, t0_ns), np.searchsorted(ts, text_ns, "right")
        v_exp = float(vol[a:e].sum())
        pa = np.searchsorted(ts, t0_ns - 3600 * NS)
        v_rate_prior = vol[pa:a].sum() / max((t0_ns - ts[pa]) / NS, 1) if a > pa else np.nan
        vol_rel = (v_exp / dur) / v_rate_prior if v_rate_prior and v_rate_prior > 0 else np.nan
        if d == 1:
            run = np.maximum.accumulate(Hh[i0:ie + 1]); pull = (run - Ll[i0:ie + 1]).max() / W
        else:
            run = np.minimum.accumulate(Ll[i0:ie + 1]); pull = (Hh[i0:ie + 1] - run).max() / W
        lo, hi = b["lo_tick"], b["hi_tick"]
        pe, ve = px[a:e], vol[a:e]
        inside = (pe >= lo) & (pe <= hi)
        dw = np.bincount(pe[inside] - lo, weights=ve[inside], minlength=hi - lo + 1) if inside.any() else np.zeros(hi - lo + 1)
        med = np.median(dw[dw > 0]) if (dw > 0).any() else 0
        low = dw < LVN_Q * med
        n_lvn = int(((np.diff(np.r_[0, low.astype(int), 0]) == 1)).sum())
        tr_a = np.searchsorted(ts, t0_ns - 1800 * NS)
        trend30 = float(d * np.sign(px[max(a - 1, 0)] - px[tr_a])) if a > tr_a else 0.0
        bid = f"{kind}:{cfg}:{bi}"
        rows_b.append(dict(band=bid, kind=kind, cfg=cfg, dir=d, A=A, B=B, W=W, W_sigma=W / b["sigma_ticks"] if b["sigma_ticks"] else np.nan,
                           dur_s=dur, speed_tps=W / dur, efficiency=eff, vol_total=v_exp, vol_rel=vol_rel,
                           max_pullback_inside=pull, lvn_frac_inside=float(low.mean()), n_lvn_inside=n_lvn,
                           phase=phase_et(tav_ns), dir_vs_trend30=trend30, t_start=t0_ns, t_avail=tav_ns))
        # ---- eventos (sólo hasta el instante del evento)
        s0 = np.searchsorted(ts, tav_ns, "right")
        s1 = np.searchsorted(ts, min(tav_ns + EVENT_WIN_S * NS, ctx["end"]))
        seg = px[s0:s1]
        if len(seg) == 0:
            continue
        depth = ((B - seg) if d == 1 else (seg - B)) / W          # 0 en B, 1 en A; negativo = más allá de B
        beyond = ((seg - B) if d == 1 else (B - seg)) >= 2       # más allá de B por >= 2 ticks
        at_B = (np.abs(seg - B) <= 1) & (depth >= 0)
        passed_A = depth >= 1

        def first(mask, start=0):
            if start >= len(mask):
                return -1
            k = np.argmax(mask[start:])
            return start + int(k) if mask[start + k] else -1

        evs = [("E0", -1)]
        kA = first(passed_A)
        kB = first(beyond)
        k1 = first(depth >= 0.5)
        if k1 >= 0 and (kB < 0 or k1 < kB) and (kA < 0 or k1 <= kA):
            evs.append(("E1", k1))
        if kB >= 0 and (kA < 0 or kB < kA):
            k2 = first(depth >= R_END, kB)
            if k2 >= 0:
                evs.append(("E2", k2))
        kT = first(at_B)
        if kT >= 0 and (kB < 0 or kT < kB) and (kA < 0 or kT < kA):
            k3 = first(depth >= R_END, kT)
            if k3 >= 0 and (kB < 0 or k3 < kB):
                evs.append(("E3", k3))
        for et, k in evs:
            if et == "E0":
                t_ev, p_ev, j = tav_ns, int(px[max(s0 - 1, 0)]), max(s0 - 1, 0)
            else:
                j = s0 + k
                t_ev, p_ev = int(ts[j]), int(px[j])
            pre = seg[:max(k, 0)] if et != "E0" else seg[:0]
            ext_beyond = float(((pre - B) if d == 1 else (B - pre)).max()) if len(pre) else 0.0
            ext_beyond = max(ext_beyond, 0.0)
            n_touch = int((np.diff(np.r_[0, at_B[:max(k, 0)].astype(int)]) == 1).sum()) if et != "E0" else 0
            a60 = np.searchsorted(ts, t_ev - 60 * NS)
            appr_speed = abs(p_ev - px[a60]) / 60.0
            v60 = vol[a60:j + 1].sum()
            a3600 = np.searchsorted(ts, t_ev - 3600 * NS)
            v_rate = vol[a3600:j + 1].sum() / 60.0 if j + 1 > a3600 else np.nan
            appr_vol_rel = v60 / v_rate if v_rate and v_rate > 0 else np.nan
            # medias de 1 minuto y VWAP de sesión hasta el evento
            mi = np.searchsorted(ctx["m_end"], t_ev, "right") - 1
            ema20 = ctx["ema20"][mi] if mi >= 0 else np.nan
            ema50 = ctx["ema50"][mi] if mi >= 49 else np.nan
            sma200 = ctx["sma200"][mi] if mi >= 199 else np.nan
            vwap = ctx["cum_pv"][j] / ctx["cum_v"][j] if ctx["cum_v"][j] > 0 else np.nan
            tdirA = -d                                              # patinaje hacia A
            vp = left_profile(ts, px, vol, t0_ns)
            tp_hvn, lvn_at, poc = np.nan, np.nan, np.nan
            if vp is not None:
                centers, prof, hvn, lvn_mask, poc = vp
                between = hvn[(hvn - p_ev) * tdirA > 0]
                between = between[((between - A) * tdirA) <= 0] if len(between) else between
                if len(between):
                    tp_hvn = float(np.min(np.abs(between - p_ev)))
                ci = int(np.clip((p_ev - (centers[0] - VP_BIN / 2)) // VP_BIN, 0, len(centers) - 1))
                lvn_at = float(lvn_mask[ci])
            rows_e.append(dict(band=bid, kind=kind, cfg=cfg, event=et, dir=d, A=A, B=B, W=W, t_event=t_ev, p_event=p_ev,
                               depth=float(((B - p_ev) if d == 1 else (p_ev - B)) / W), age_s=(t_ev - tav_ns) / NS,
                               ext_beyond_B=ext_beyond, n_prior_touches_B=n_touch,
                               vol_between=float(vol[s0:j + 1].sum()) if et != "E0" else 0.0,
                               approach_speed=appr_speed, approach_vol_rel=appr_vol_rel,
                               skate_len=float(abs(p_ev - A)), tp_hvn_dist=tp_hvn, lvn_at_event=lvn_at,
                               poc_left_dist=(float((poc - p_ev) * tdirA) if np.isfinite(poc) else np.nan),
                               ema20_align=float(tdirA * (p_ev - ema20)) if np.isfinite(ema20) else np.nan,
                               ema50_align=float(tdirA * (p_ev - ema50)) if np.isfinite(ema50) else np.nan,
                               sma200_align=float(tdirA * (p_ev - sma200)) if np.isfinite(sma200) else np.nan,
                               vwap_align=float(tdirA * (p_ev - vwap)) if np.isfinite(vwap) else np.nan,
                               phase=phase_et(t_ev)))
    return rows_b, rows_e


def zigzag(bars, r=R_END, min_net=4):
    """Tramos A->B con la MISMA regla de fin que TBZ-EXP (retroceso >= max(2, r*tramo)) pero sin la condición de
    arranque (k*sigma, eficiencia): todos los tramos del precio, rápidos o lentos."""
    H, L = bars.high_t.astype(np.int64), bars.low_t.astype(np.int64)
    n = len(H)
    out = []
    d = 0
    hi_i, hi_p, lo_i, lo_p = 0, int(H[0]), 0, int(L[0])
    piv_i = piv_p = ext_i = ext_p = 0
    for j in range(1, n):
        if d == 0:
            if H[j] > hi_p:
                hi_i, hi_p = j, int(H[j])
            if L[j] < lo_p:
                lo_i, lo_p = j, int(L[j])
            if hi_p - lo_p >= min_net:
                if hi_i > lo_i:
                    d, piv_i, piv_p, ext_i, ext_p = 1, lo_i, lo_p, hi_i, hi_p
                else:
                    d, piv_i, piv_p, ext_i, ext_p = -1, hi_i, hi_p, lo_i, lo_p
            continue
        if d == 1:
            if H[j] > ext_p:
                ext_i, ext_p = j, int(H[j])
            retr = ext_p - int(L[j])
        else:
            if L[j] < ext_p:
                ext_i, ext_p = j, int(L[j])
            retr = int(H[j]) - ext_p
        tot = abs(ext_p - piv_p)
        if tot >= min_net and retr >= max(2, r * tot):
            out.append(dict(dir=d, a_tick=piv_p, b_tick=ext_p, lo_tick=min(piv_p, ext_p), hi_tick=max(piv_p, ext_p),
                            width_ticks=tot, sigma_ticks=np.nan, i_start=piv_i, i_ext=ext_i, i_avail=j))
            piv_i, piv_p, d = ext_i, ext_p, -d
            ext_i, ext_p = j, (int(L[j]) if d == -1 else int(H[j]))
    return out


def nonexp_null(zz, fast):
    """N2 (iteración 1b, 24/09): tramos del zigzag que NO terminan donde termina una franja TBZ (mismo B a <= 1 tick y
    t_avail a <= 3 velas). Mismo ancho mínimo y la misma regla de vuelta; el emparejamiento por ancho se hace en el
    reporte (pesos por bin de ancho de las franjas TBZ). Contesta si importa que haya sido una expansión TBZ."""
    ends = [(f["b_tick"], f["i_avail"]) for f in fast]
    out = []
    for z in zz:
        if any(abs(z["b_tick"] - bb) <= 1 and abs(z["i_avail"] - ia) <= 3 for bb, ia in ends):
            continue
        out.append(z)
    return out


def census_session(args):
    inst, s = args
    out = OUT / "census" / inst / f"{s['trade_date']}.parquet"
    tk = load_canonical_parquet(s["path"], contract=s["contract"], start_utc_ns=s["start"], end_utc_ns=s["end"])
    if int(tk.ts_ns[-1]) >= HOLDOUT_NS:
        raise ValueError("holdout decodificado")
    ts, px, vol = tk.ts_ns.astype(np.int64), tk.price_ticks.astype(np.int64), tk.volume.astype(float)
    if len(ts) < 5000 or bool((np.diff(ts) < 0).any()):
        return inst, s["trade_date"], dict(skip="POCA_ACTIVIDAD_O_NO_MONOTONO")
    bars = build_tick_bars(tk, 25, reiniciar_por_sesion=True)
    tsec = (bars.end_ns // NS).astype(np.int64)
    o, h, l, c = (bars.open_t * bars.tick_size, bars.high_t * bars.tick_size, bars.low_t * bars.tick_size,
                  bars.close_t * bars.tick_size)
    m_end, m_close = minute_closes(ts, px)
    sma = pd.Series(m_close).rolling(200).mean().to_numpy()
    ctx = dict(end=s["end"], m_end=m_end, ema20=ema(m_close, 20), ema50=ema(m_close, 50), sma200=sma,
               cum_pv=np.cumsum(px * vol), cum_v=np.cumsum(vol))
    RB, RE = [], []
    zz = zigzag(bars)
    sig20 = causal_sigma(bars.close_t.astype(np.int64), 20, 3000)
    for z in zz:
        z["sigma_ticks"] = float(sig20[z["i_avail"]]) if np.isfinite(sig20[z["i_avail"]]) else np.nan
    for W, k in GRID:
        cfg = f"W{W}_k{k}"
        fast = expansion_bands(tsec, o, h, l, c, bars.tick_size, W=W, k=k, r=R_END)
        slow = nonexp_null(zz, fast)
        for kind, bb in (("rapida", fast), ("tramo_N2", slow)):
            rb, re = band_rows(kind, cfg, bb, bars, ts, px, vol, ctx)
            RB += rb; RE += re
    out.parent.mkdir(parents=True, exist_ok=True)
    B = pd.DataFrame(RB); E = pd.DataFrame(RE)
    for df in (B, E):
        df.insert(0, "session", s["trade_date"]); df.insert(1, "contract", s["contract"])
    tmp = out.with_suffix(".partial")
    E.to_parquet(tmp, index=False); tmp.replace(out)
    B.to_parquet(out.with_name(f"{s['trade_date']}_bands.parquet"), index=False)
    return inst, s["trade_date"], dict(bands=len(B), events=len(E), ticks=int(len(ts)))


def step_census(inst, workers, only=None):
    ss = sessions(inst)
    if only:
        ss = [s for s in ss if s["trade_date"] in only]
    todo = [(inst, s) for s in ss if not (OUT / "census" / inst / f"{s['trade_date']}.parquet").exists()]
    log = OUT / f"census_log_{inst}.jsonl"
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(workers) as ex:
        futs = [ex.submit(census_session, t) for t in todo]
        for fu in as_completed(futs):
            i, d, info = fu.result()
            with open(log, "a", encoding="utf-8") as f:
                f.write(json.dumps(dict(inst=i, session=d, **info)) + "\n")
            print(i, d, info, flush=True)


def step_summary(inst):
    files = sorted((OUT / "census" / inst).glob("*_bands.parquet"))
    B = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    E = pd.concat([pd.read_parquet(str(f).replace("_bands", "")) for f in files], ignore_index=True)
    ns = B.session.nunique()
    summ = dict(sessions=int(ns))
    summ["franjas_por_sesion"] = (B.groupby(["kind", "cfg"]).size() / ns).round(1).to_dict()
    summ["eventos_por_sesion"] = (E.groupby(["kind", "cfg", "event"]).size() / ns).round(1).to_dict()
    desc_b = ["W", "W_sigma", "dur_s", "speed_tps", "efficiency", "vol_rel", "max_pullback_inside", "lvn_frac_inside", "n_lvn_inside"]
    desc_e = ["depth", "age_s", "ext_beyond_B", "n_prior_touches_B", "approach_speed", "approach_vol_rel", "skate_len",
              "tp_hvn_dist", "lvn_at_event", "ema20_align", "ema50_align", "sma200_align", "vwap_align"]
    summ["cuantiles_franjas"] = {c: B[B.kind == "rapida"][c].quantile([.05, .25, .5, .75, .95]).round(3).tolist() for c in desc_b}
    summ["cuantiles_eventos"] = {c: E[E.kind == "rapida"][c].quantile([.05, .25, .5, .75, .95]).round(3).tolist() for c in desc_e}
    summ["hvn_disponible"] = float(E[E.kind == "rapida"].tp_hvn_dist.notna().mean())
    corr = E[E.kind == "rapida"][desc_e].corr(method="spearman").round(2)
    summ["pares_redundantes_|rho|>=0.7"] = [(a, b, float(corr.loc[a, b])) for i, a in enumerate(desc_e) for b in desc_e[i + 1:]
                                            if abs(corr.loc[a, b]) >= 0.7]
    cb = B[B.kind == "rapida"][desc_b].corr(method="spearman").round(2)
    summ["pares_redundantes_franjas_|rho|>=0.7"] = [(a, b, float(cb.loc[a, b])) for i, a in enumerate(desc_b) for b in desc_b[i + 1:]
                                                     if abs(cb.loc[a, b]) >= 0.7]
    summ["n2_vs_tbz"] = {k: B[B.kind == k][["W", "speed_tps", "dur_s"]].quantile([.25, .5, .75]).round(2).to_dict() for k in ("rapida", "tramo_N2")}
    body = dict(schema="EDGELAB_TBZ_E2A_CENSUS_V1", doc=DOC, inst=inst, code_commit=_git("rev-parse", "HEAD"),
                tree_dirty=bool(_git("status", "--porcelain", "--", "tools", "edgelab")), summary=summ)
    raw = json.dumps(body, indent=1, default=str)
    (OUT / f"census_summary_{inst}.json").write_text(raw, encoding="utf-8")
    print(json.dumps(summ, indent=1, default=str)[:6000])
    return hashlib.sha256(raw.encode()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["census", "summary"])
    ap.add_argument("--inst", default="ES")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args(argv)
    if a.step == "census":
        step_census(a.inst, a.workers, a.only)
    else:
        step_summary(a.inst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

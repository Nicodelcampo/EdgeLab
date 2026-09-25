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
LEDGER_TBZ = REPO / "artifacts" / "hippocampus" / "tbz_20260924.jsonl"
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
    summ["franjas_por_sesion"] = {"|".join(k): v for k, v in (B.groupby(["kind", "cfg"]).size() / ns).round(1).to_dict().items()}
    summ["eventos_por_sesion"] = {"|".join(k): v for k, v in (E.groupby(["kind", "cfg", "event"]).size() / ns).round(1).to_dict().items()}
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
    summ["n2_vs_tbz"] = {k: {c: B[B.kind == k][c].quantile([.25, .5, .75]).round(2).tolist() for c in ("W", "speed_tps", "dur_s")} for k in ("rapida", "tramo_N2")}
    body = dict(schema="EDGELAB_TBZ_E2A_CENSUS_V1", doc=DOC, inst=inst, code_commit=_git("rev-parse", "HEAD"),
                tree_dirty=bool(_git("status", "--porcelain", "--", "tools", "edgelab")), summary=summ)
    raw = json.dumps(body, indent=1, default=str)
    (OUT / f"census_summary_{inst}.json").write_text(raw, encoding="utf-8")
    print(json.dumps(summ, indent=1, default=str)[:6000])
    return hashlib.sha256(raw.encode()).hexdigest()


# ============================================================== E2b: resultados (sólo P-TBZ-EXP; OK de Nico) =====
EXP_END = "20260331"
LAT_NS = 250_000_000
TMAX_S = 1800
COMM = {"ES": 0.2, "MES": 0.68}
PHANTOM_TRIES = 8
MODES = ("hacia_A_A", "hacia_A_HVN", "hacia_B_B")


def load_session_arrays(s):
    tk = load_canonical_parquet(s["path"], contract=s["contract"], start_utc_ns=s["start"], end_utc_ns=s["end"])
    return (tk.ts_ns.astype(np.int64), tk.price_ticks.astype(np.int64), tk.bid_ticks.astype(np.int64),
            tk.ask_ticks.astype(np.int64))


def simulate(ts, px, bid, ask, t_ev, tdir, stop, target, end_ns, comm):
    """Entrada agresiva en el primer trade >= t_ev + 250 ms (ask para comprar, bid para vender). Stop: primer trade
    que lo toca, al precio de ese trade. Target: se llena sólo si el precio lo atraviesa por 1 tick. Tiempo máximo:
    1.800 s, a mercado. Devuelve (entrada, salida, pnl_neto_ticks, motivo) o None si no hay trade para entrar."""
    i = int(np.searchsorted(ts, t_ev + LAT_NS))
    if i >= len(ts):
        return None
    entry = int(ask[i] if tdir == 1 else bid[i])
    j1 = int(np.searchsorted(ts, min(int(ts[i]) + TMAX_S * NS, end_ns)))
    j1 = max(j1, i + 1)
    seg = px[i:j1]
    if tdir == 1:
        hs, ht = seg <= stop, seg >= target + 1
    else:
        hs, ht = seg >= stop, seg <= target - 1
    ks = int(np.argmax(hs)) if hs.any() else 10**12
    kt = int(np.argmax(ht)) if ht.any() else 10**12
    if ks == kt == 10**12:
        k = j1 - 1
        ex, why = int(bid[k] if tdir == 1 else ask[k]), "tiempo"
    elif ks <= kt:
        ex, why = int(seg[ks]), "stop"
    else:
        ex, why = int(target), "target"
    return entry, ex, tdir * (ex - entry) - 2 * comm, why, int(px[i])


def trade_plan(e, mode):
    """(tdir, stop, target) de un evento. hacia_A: contra la expansión, stop en B + 0,25W, target A o HVN.
    hacia_B: a favor, target B, stop simétrico (1R)."""
    d, A, B, W, p = int(e.dir), int(e.A), int(e.B), int(e.W), int(e.p_event)
    if mode.startswith("hacia_A"):
        tdir = -d
        stop = B + d * int(np.ceil(0.25 * W))
        target = A
        if mode.endswith("HVN") and np.isfinite(e.tp_hvn_dist) and e.tp_hvn_dist > 0:
            target = int(round(p + tdir * e.tp_hvn_dist))
    else:
        tdir = d
        target = B
        stop = p - tdir * max(abs(B - p), 1)
    return tdir, stop, target


def explore_session(args):
    inst, s = args
    cen = OUT / "census" / inst / f"{s['trade_date']}.parquet"
    out = OUT / "explore" / inst / f"{s['trade_date']}.parquet"
    if not cen.exists():
        return inst, s["trade_date"], dict(skip="SIN_CENSO")
    E = pd.read_parquet(cen)
    ts, px, bid, ask = load_session_arrays(s)
    if bool((np.diff(ts) < 0).any()):
        return inst, s["trade_date"], dict(skip="NO_MONOTONO")
    rows = []
    for e in E.itertuples(index=False):
        for mode in MODES:
            tdir, stop, target = trade_plan(e, mode)
            r = simulate(ts, px, bid, ask, int(e.t_event), tdir, stop, target, s["end"], COMM[inst])
            if r is None:
                continue
            entry, ex, pnl, why, x0 = r
            risk = max(abs(stop - entry), 1)
            rew = max(abs(target - entry), 1)
            # N1 con las MISMAS convenciones que la simulación (iteración 1c): camino de precios de trade desde el
            # último trade al entrar; el stop se toca, el target hay que atravesarlo por 1 tick.
            s_eff = max(tdir * (x0 - stop), 0)
            r_eff = max(tdir * ((target + tdir) - x0), 0)
            p0 = s_eff / (s_eff + r_eff) if (s_eff + r_eff) > 0 else np.nan
            rows.append(dict(band=e.band, kind=e.kind, cfg=e.cfg, event=e.event, mode=mode, tdir=tdir, W=int(e.W),
                             t_event=int(e.t_event), entry=entry, exit=ex, pnl=pnl, R=pnl / risk, why=why, risk=risk,
                             reward=rew, p0=p0, x0=x0, hit=int(why == "target")))
    D = pd.DataFrame(rows)
    D.insert(0, "session", s["trade_date"])
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".partial")
    D.to_parquet(tmp, index=False)
    tmp.replace(out)
    return inst, s["trade_date"], dict(trades=len(D))


def tod_et_s(ns):
    t = pd.Timestamp(int(ns), tz="UTC").tz_convert(ET)
    return t.hour * 3600 + t.minute * 60 + t.second


def phantom_assign(inst, ss):
    """N3: para cada trade de una franja rápida hacia A, otra sesión de exploración al azar y un instante a la misma
    hora ET ±5 min, con la misma dirección y el mismo stop y target en ticks relativos a la entrada."""
    rng = np.random.default_rng(20260924)
    by_date = {s["trade_date"]: s for s in ss}
    dates = sorted(by_date)
    Q = []
    for d in dates:
        f = OUT / "explore" / inst / f"{d}.parquet"
        if not f.exists():
            continue
        D = pd.read_parquet(f, columns=["band", "kind", "cfg", "event", "mode", "tdir", "t_event", "risk", "reward"])
        D = D[(D.kind == "rapida") & D["mode"].str.startswith("hacia_A")]
        for r in D.itertuples(index=False):
            tod = tod_et_s(r.t_event) + int(rng.integers(-300, 301))
            for _ in range(PHANTOM_TRIES):
                o = dates[int(rng.integers(0, len(dates)))]
                if o == d:
                    continue
                so = by_date[o]
                base = pd.Timestamp(int(so["end"]), tz="UTC").tz_convert(ET).normalize()
                cand = base + pd.Timedelta(seconds=int(tod))
                if cand.tz_convert("UTC").value >= so["end"]:
                    cand -= pd.Timedelta(days=1)
                tn = int(cand.tz_convert("UTC").value)
                if so["start"] + 600 * NS <= tn <= so["end"] - (TMAX_S + 60) * NS:
                    Q.append(dict(src=d, band=r.band, cfg=r.cfg, event=r.event, mode=r.mode, tdir=int(r.tdir), host=o,
                                  t=tn, risk=int(r.risk), reward=int(r.reward)))
                    break
    return pd.DataFrame(Q)


def phantom_session(args):
    inst, s, Qh = args
    ts, px, bid, ask = load_session_arrays(s)
    res = []
    for q in Qh.itertuples(index=False):
        i = int(np.searchsorted(ts, q.t + LAT_NS))
        if i >= len(ts):
            continue
        entry = int(ask[i] if q.tdir == 1 else bid[i])
        stop, target = entry - q.tdir * q.risk, entry + q.tdir * q.reward
        r = simulate(ts, px, bid, ask, q.t, q.tdir, stop, target, s["end"], COMM[inst])
        if r is None:
            continue
        res.append(dict(src=q.src, band=q.band, cfg=q.cfg, event=q.event, mode=q.mode, host=q.host, pnl=r[2],
                        hit=int(r[3] == "target"), R=r[2] / max(q.risk, 1)))
    return inst, s["trade_date"], pd.DataFrame(res)


def step_explore(inst, workers):
    ss = [s for s in sessions(inst) if s["trade_date"] <= EXP_END]
    todo = [(inst, s) for s in ss if not (OUT / "explore" / inst / f"{s['trade_date']}.parquet").exists()]
    with ProcessPoolExecutor(workers) as ex:
        for fu in as_completed([ex.submit(explore_session, t) for t in todo]):
            i, d, info = fu.result()
            print(i, d, info, flush=True)
    Q = phantom_assign(inst, ss)
    Q.to_parquet(OUT / f"explore_N3_queries_{inst}.parquet", index=False)
    by = {s["trade_date"]: s for s in ss}
    parts = []
    with ProcessPoolExecutor(workers) as ex:
        futs = [ex.submit(phantom_session, (inst, by[h], g)) for h, g in Q.groupby("host")]
        for fu in as_completed(futs):
            i, d, df = fu.result()
            parts.append(df)
            print("N3", i, d, len(df), flush=True)
    pd.concat(parts, ignore_index=True).to_parquet(OUT / f"explore_N3_{inst}.parquet", index=False)


# ------------------------------------------------------------------------------------------------ reporte E2b
WBINS = [4, 8, 16, 32, 10**9]
SEED, N_BOOT, FDR_Q = 20260924, 2000, 0.10
TREE_FEATS = ["W", "W_sigma", "dur_s", "speed_tps", "efficiency", "vol_rel", "max_pullback_inside", "lvn_frac_inside",
              "depth", "age_s", "ext_beyond_B", "n_prior_touches_B", "approach_speed", "approach_vol_rel", "skate_len",
              "tp_hvn_dist", "lvn_at_event", "ema20_align", "ema50_align", "sma200_align", "vwap_align", "k", "Wbars", "ev"]


def _boot_mean(df, col, sessions_idx, n_s, W):
    S = np.zeros(n_s); N = np.zeros(n_s)
    np.add.at(S, sessions_idx, df[col].to_numpy(float)); np.add.at(N, sessions_idx, 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        b = (W @ S) / (W @ N)
    pt = S.sum() / N.sum() if N.sum() else np.nan
    b = b[np.isfinite(b)]
    return pt, (float(np.percentile(b, 2.5)) if len(b) else np.nan), (float(np.percentile(b, 97.5)) if len(b) else np.nan), \
        (float(b.std()) if len(b) else np.nan), S, N


def _bh(p, q):
    p = np.asarray(p, float); m = len(p); o = np.argsort(p)
    ok = np.zeros(m, bool); k = np.flatnonzero(p[o] <= q * np.arange(1, m + 1) / m)
    if len(k):
        ok[o[:k.max() + 1]] = True
    return ok


def _wbin(w):
    return np.digitize(w, WBINS[1:-1])


def step_report(inst):
    from math import erfc, sqrt
    from edgelab.edge_brain.control_guard import audit_event_controls
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus import LessonCandidate
    files = sorted((OUT / "explore" / inst).glob("*.parquet"))
    D = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    D = D[D.session <= EXP_END]
    P = pd.read_parquet(OUT / f"explore_N3_{inst}.parquet")
    Qn = pd.read_parquet(OUT / f"explore_N3_queries_{inst}.parquet")
    sess = sorted(D.session.unique()); n_s = len(sess); si = {d: i for i, d in enumerate(sess)}
    rng = np.random.default_rng(SEED)
    W = np.stack([np.bincount(rng.integers(0, n_s, n_s), minlength=n_s) for _ in range(N_BOOT)]).astype(float)
    D["si"] = D.session.map(si)
    D["wb"] = _wbin(D.W.to_numpy())
    D["month"] = D.session.str.slice(0, 6)
    P = P.rename(columns={"src": "session", "pnl": "pnl_n3", "hit": "hit_n3", "R": "R_n3"})
    cells, fams = [], {"primaria_hacia_A": ["hacia_A_A", "hacia_A_HVN"], "secundaria_hacia_B": ["hacia_B_B"]}
    for fam, modes in fams.items():
        for mode in modes:
            for cfg in sorted(D.cfg.unique()):
                for ev in ("E0", "E1", "E2", "E3"):
                    T_ = D[(D.kind == "rapida") & (D["mode"] == mode) & (D.cfg == cfg) & (D.event == ev)]
                    N2 = D[(D.kind == "tramo_N2") & (D["mode"] == mode) & (D.cfg == cfg) & (D.event == ev)]
                    if len(T_) < 30:
                        cells.append(dict(fam=fam, mode=mode, cfg=cfg, event=ev, n=int(len(T_)), status="SIN_MUESTRA"))
                        continue
                    pt, lo, hi, sd, S, N = _boot_mean(T_, "pnl", T_.si.to_numpy(), n_s, W)
                    hp, hlo, hhi, _, Sh, Nh = _boot_mean(T_, "hit", T_.si.to_numpy(), n_s, W)
                    T2 = T_.assign(ex=T_.hit - T_.p0)
                    ep, elo, ehi, _, _, _ = _boot_mean(T2, "ex", T2.si.to_numpy(), n_s, W)
                    # N2 emparejado por ancho: diferencia de tasa de acierto y de pnl, con pesos por bin de la celda TBZ
                    wts = T_.wb.value_counts(normalize=True)
                    def n2_stat(col):
                        Sb = np.zeros((len(WBINS) - 1, n_s)); Nb = np.zeros((len(WBINS) - 1, n_s))
                        np.add.at(Sb, (N2.wb.to_numpy(), N2.si.to_numpy()), N2[col].to_numpy(float))
                        np.add.at(Nb, (N2.wb.to_numpy(), N2.si.to_numpy()), 1)
                        with np.errstate(invalid="ignore", divide="ignore"):
                            bb = (Sb @ W.T) / (Nb @ W.T)
                            pt_ = (Sb.sum(1) / Nb.sum(1))
                        ww = np.array([wts.get(k, 0.0) for k in range(len(WBINS) - 1)])
                        okb = np.isfinite(pt_) & (ww > 0)
                        if not okb.any():
                            return np.nan, np.full(N_BOOT, np.nan)
                        wn = ww[okb] / ww[okb].sum()
                        return float((pt_[okb] * wn).sum()), (bb[okb] * wn[:, None]).sum(0)
                    n2_hit, n2_hit_b = n2_stat("hit")
                    n2_pnl, n2_pnl_b = n2_stat("pnl")
                    with np.errstate(invalid="ignore", divide="ignore"):
                        tb_hit_b = (W @ Sh) / (W @ Nh); tb_pnl_b = (W @ S) / (W @ N)
                    dh = tb_hit_b - n2_hit_b; dp = tb_pnl_b - n2_pnl_b
                    # N3 pareado
                    M = T_.merge(P[["session", "band", "event", "mode", "pnl_n3", "hit_n3"]],
                                 on=["session", "band", "event", "mode"], how="inner") \
                        if mode.startswith("hacia_A") else pd.DataFrame()
                    if len(M) >= 30:
                        M = M.assign(dp3=M.pnl - M.pnl_n3, dh3=M.hit - M.hit_n3)
                        d3p, d3lo, d3hi, _, _, _ = _boot_mean(M, "dp3", M.si.to_numpy(), n_s, W)
                        h3p, h3lo, h3hi, _, _, _ = _boot_mean(M, "dh3", M.si.to_numpy(), n_s, W)
                        n3 = dict(n=int(len(M)), pnl_n3=float(M.pnl_n3.mean()), hit_n3=float(M.hit_n3.mean()),
                                  dif_pnl=[d3p, d3lo, d3hi], dif_hit=[h3p, h3lo, h3hi])
                    else:
                        n3 = None
                    mpos = float((T_.groupby("month").pnl.mean() > 0).mean())
                    p = erfc(abs(pt / sd) / sqrt(2)) if sd and sd > 0 else 1.0
                    cells.append(dict(fam=fam, mode=mode, cfg=cfg, event=ev, n=int(len(T_)), sesiones=int(T_.session.nunique()),
                                      pnl=[pt, lo, hi], p=p, R_medio=float(T_.R.mean()), hit=[hp, hlo, hhi], p0_N1=float(T_.p0.mean()),
                                      exceso_hit_N1=[ep, elo, ehi],
                                      N2=dict(n=int(len(N2)), hit=n2_hit, pnl=n2_pnl,
                                              dif_hit=[float(np.nanmean(dh)) if np.isfinite(dh).any() else np.nan,
                                                       float(np.nanpercentile(dh, 2.5)) if np.isfinite(dh).any() else np.nan,
                                                       float(np.nanpercentile(dh, 97.5)) if np.isfinite(dh).any() else np.nan],
                                              dif_pnl=[float(np.nanmean(dp)) if np.isfinite(dp).any() else np.nan,
                                                       float(np.nanpercentile(dp, 2.5)) if np.isfinite(dp).any() else np.nan,
                                                       float(np.nanpercentile(dp, 97.5)) if np.isfinite(dp).any() else np.nan]),
                                      N3=n3, meses_positivos=mpos,
                                      salidas=T_.why.value_counts(normalize=True).round(3).to_dict(), status="OK"))
    # FDR por familia + regla de sugerencia (§7 I8)
    sug = []
    for fam in fams:
        cc = [c for c in cells if c["fam"] == fam and c["status"] == "OK"]
        ok = _bh([c["p"] for c in cc], FDR_Q)
        for c, o in zip(cc, ok):
            c["fdr"] = bool(o)
            n3ok = c["N3"] is not None and c["N3"]["dif_hit"][1] > 0 if fam.startswith("primaria") else True
            c["sugerencia"] = bool(o and c["pnl"][1] > 0 and c["exceso_hit_N1"][1] > 0 and
                                   np.isfinite(c["N2"]["dif_hit"][1]) and c["N2"]["dif_hit"][1] > 0 and n3ok and
                                   c["meses_positivos"] >= 0.55)
            if c["sugerencia"]:
                sug.append(c)
    top = sorted(sug, key=lambda c: -c["pnl"][1])[:3]
    # árbol honesto sobre R neto (franjas rápidas, hacia A con target A), rasgos del censo
    tree = _honest_tree(inst, D, sess)
    # guardia de controles para N3 (controles de otra sesión)
    q = Qn.merge(D[["session", "band", "event", "mode", "t_event"]].rename(columns={"session": "src"}),
                 on=["src", "band", "event", "mode"], how="inner")
    audit = audit_event_controls(q.t_event.to_numpy(), q.t.to_numpy(), TMAX_S, same_session=(q.src == q.host).to_numpy())
    body = dict(schema="EDGELAB_TBZ_E2B_V1", doc=DOC, inst=inst, code_commit=_git("rev-parse", "HEAD"),
                tree_dirty=bool(_git("status", "--porcelain", "--", "tools", "edgelab")), sesiones=n_s,
                celdas=cells, sugerencias_top=top, arbol=tree, control_audit_N3=audit)
    raw = json.dumps(body, indent=1, default=float)
    (OUT / f"report_E2b_{inst}.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    LED = LEDGER_TBZ
    with measurement_episode(LED, f"EP-TBZ-E2B-{inst}-20260924", goal="TBZ-E2b: patinaje en la franja, 32+16 celdas y 3 nulos",
                             recorded_by="tools/tbz_e2.py report", repo=REPO, prereg_ref=DOC) as ep:
        ep.store.record_observation(f"OBS-TBZ-E2B-{inst}", "expansión como área de patinaje (E2b)", "RESPONSE_PROFILE",
                                    ["P-TBZ-EXP"], {f"{c['mode']}|{c['cfg']}|{c['event']}": c.get("pnl") for c in cells},
                                    {"sessions": n_s}, sha, design="EVENT_VS_CONTROL", control_audit=audit)
        for i, c in enumerate(top):
            ep.store.record_lesson(LessonCandidate(
                lesson_id=f"SUG-TBZ-E2B-{inst}-{i + 1}", episode_id=f"EP-TBZ-E2B-{inst}-20260924",
                statement=(f"{inst} {c['mode']} {c['cfg']} {c['event']}: pnl {c['pnl'][0]:.2f} t (IC {c['pnl'][1]:.2f}..{c['pnl'][2]:.2f}), "
                           f"hit {c['hit'][0]:.3f} vs N1 {c['p0_N1']:.3f}. Confirmar SOLO en P-TBZ-CONF con spec y campaña."),
                confidence="LOW", status="PROPOSED", scope="SUGGESTED_ANALYSIS"))
    print(json.dumps(dict(sesiones=n_s, celdas_ok=sum(c["status"] == "OK" for c in cells),
                          fdr=sum(c.get("fdr", False) for c in cells), sugerencias=len(sug), sha=sha[:12])))


def _honest_tree(inst, D, sess):
    """Árbol honesto (profundidad <= 3, hojas >= 15 sesiones) sobre el R neto de franjas rápidas hacia A (target A).
    La mitad de las sesiones arma los cortes y la otra estima. Sirve para sugerir, no para probar."""
    rng = np.random.default_rng(SEED)
    perm = list(rng.permutation(sess)); half = len(perm) // 2
    grow_s, est_s = set(perm[:half]), set(perm[half:])
    frames = []
    for d in sess:
        f = OUT / "census" / inst / f"{d}.parquet"
        fb = OUT / "census" / inst / f"{d}_bands.parquet"
        if f.exists() and fb.exists():
            e = pd.read_parquet(f); b = pd.read_parquet(fb)
            e = e[e.kind == "rapida"].merge(b[["band", "W_sigma", "dur_s", "speed_tps", "efficiency", "vol_rel",
                                               "max_pullback_inside", "lvn_frac_inside"]], on="band", how="left")
            e["session"] = d
            frames.append(e)
    C = pd.concat(frames, ignore_index=True)
    X = D[(D.kind == "rapida") & (D["mode"] == "hacia_A_A")][["session", "band", "event", "R"]]
    E = X.merge(C, on=["session", "band", "event"], how="inner")
    E["k"] = E.cfg.str.extract(r"k([\d.]+)").astype(float)
    E["Wbars"] = E.cfg.str.extract(r"W(\d+)").astype(float)
    E["ev"] = E.event.str.slice(1).astype(float)
    E = E.rename(columns={"R": "tau"})
    def grow(G, depth, path=()):
        node = dict(path=list(path), n=int(len(G)), sess=int(G.session.nunique()), mean=float(G.tau.mean()) if len(G) else None)
        if depth == 0:
            return [node]
        best = None; tot = G.tau.sum()
        for f in TREE_FEATS:
            x = G[f].astype(float)
            if x.isna().all():
                continue
            for c in np.unique(np.nanpercentile(x, np.arange(10, 100, 10))):
                L = x <= c
                if G.session[L].nunique() < 15 or G.session[~L & x.notna()].nunique() < 15:
                    continue
                nl, nr = int(L.sum()), int((~L).sum())
                sl = G.tau[L].sum()
                gain = sl ** 2 / nl + (tot - sl) ** 2 / nr - tot ** 2 / len(G)
                if best is None or gain > best[0]:
                    best = (gain, f, float(c))
        if best is None:
            return [node]
        _, f, c = best
        L = G[f].astype(float) <= c
        return grow(G[L], depth - 1, path + ((f, "<=", c),)) + grow(G[~L], depth - 1, path + ((f, ">", c),))
    leaves = grow(E[E.session.isin(grow_s)], 3)
    out = []
    Ee = E[E.session.isin(est_s)]
    for lf in leaves:
        m = pd.Series(True, index=Ee.index)
        for f, op, c in lf["path"]:
            x = Ee[f].astype(float)
            m &= (x <= c) if op == "<=" else (x > c)
        sub = Ee[m]
        g = sub.groupby("session").tau.agg(["sum", "count"])
        ci = None
        if len(g) >= 5:
            r = np.random.default_rng(SEED); idx = r.integers(0, len(g), (N_BOOT, len(g)))
            b = g["sum"].to_numpy()[idx].sum(1) / g["count"].to_numpy()[idx].sum(1)
            ci = [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]
        out.append(dict(path=lf["path"], grow_mean_R=lf["mean"], grow_n=lf["n"], est_mean_R=float(sub.tau.mean()) if len(sub) else None,
                        est_ci=ci, est_n=int(len(sub)), est_sess=int(sub.session.nunique())))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["census", "summary", "explore", "report"])
    ap.add_argument("--inst", default="ES")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args(argv)
    if a.step == "census":
        step_census(a.inst, a.workers, a.only)
    elif a.step == "summary":
        step_summary(a.inst)
    elif a.step == "explore":
        step_explore(a.inst, a.workers)
    else:
        step_report(a.inst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
r"""VIO-1 — zonas VIOLETA (lógica de aVolClusterPOI v0.5) aplicadas a las zonas de aVolZonePOI2 (paridad NT8 verificada, config 25T) en MGC 25 ticks.
Pregunta: cuando el precio, después de alejarse de una zona violeta, vuelve a una distancia D de ella, ¿tiene más probabilidad de llegar a la zona (TP de `a` ticks hacia la zona) que de alejarse otros `b` ticks (SL)?
¿Hay una distancia y una configuración TP/SL con esperanza NETA positiva? Pre-registro: docs/research/autopilot/drafts/VIO-1.md (configuración textual en VIO_CFG).
Salida STUDY_RESULTS.json (formato del autopilot) + agregados por sesión para el análisis posterior. Sin holdout."""
from __future__ import annotations
import dataclasses, gc, json, os, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

KAGGLE = Path("/kaggle/input").exists()
if KAGGLE:
    _roots = [Path("/kaggle/input"), *Path("/kaggle/input").glob("datasets/*")]
    os.environ["EDGELAB_DATA_ROOTS"] = os.pathsep.join(str(r) for r in _roots)
    sys.path.insert(0, str(next(p.parent for r in _roots for p in r.glob("edgelab-data-catalog/**/edgelab_data.py"))))
    sys.path.insert(0, str(next(p.parent.parent for r in _roots for p in r.glob("edgelab-code-zones/**/edgelab/__init__.py"))))
    OUT = Path("/kaggle/working")
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docs/data_catalog")); sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    OUT = Path(os.environ.get("VIO_OUT", "/tmp/vio_out"))
OUT.mkdir(parents=True, exist_ok=True); os.environ.setdefault("EDGELAB_ALLOW_MISSING", "1")
from edgelab.bridge import bars as B, ticks as T                                    # noqa: E402
from edgelab.bridge.indicators.avolzonepoi2 import run as zones_run                 # noqa: E402
from edgelab.research import violet_zones as VZ                                      # noqa: E402

CFG = json.loads(os.environ.get("VIO_CFG", "{}"))
INST = CFG.get("inst", "MGC"); SPEC = int(CFG.get("bar_ticks", 25)); TICK_USD = float(CFG.get("tick_usd", 1.0)); COST_TICKS = float(CFG.get("cost_ticks", 6.8))
ZPARAMS = CFG.get("zone_params", {"ob_away_heights": 6.0, "ob_max_inside_pct": 4.0, "racimo_min": 6, "racimo_bars": 500, "racimo_altura_ticks": 30})   # config 25T con paridad verificada
VPARAMS = CFG.get("violet_params", {})                                               # vacío = valores por defecto del .cs (40, 2,0, 30, 20, 0,35)
DS = CFG.get("D", [10, 16, 20, 30, 40, 60]); SEED = int(CFG.get("seed", 20261018)); NPERM = int(os.environ.get("VIO_NPERM", CFG.get("nperm", 10000)))
DESDE, HASTA = CFG.get("desde", "2025-07-01"), CFG.get("hasta", "2026-09-30"); SPLIT = float(CFG.get("split", 0.6)); CT = "America/Chicago"
END_NS = pd.Timestamp("2026-09-30 22:00", tz="UTC").value


def configs(D):                                   # (a = ticks hacia la zona, b = ticks alejándose): a ∈ {D/2, D}, b ∈ {D/2, D, 2D}
    return [(a, b) for a in (D // 2, D) for b in (D // 2, D, 2 * D)]


def ct_minute_of_day(ts_ns):
    ts = np.asarray(ts_ns, dtype=np.int64); um, inv = np.unique(ts // 60_000_000_000, return_inverse=True)
    c = pd.to_datetime(um * 60_000_000_000, utc=True).tz_convert(CT); return np.asarray(c.hour * 60 + c.minute)[inv]


def session_end_vec(end_ns):
    end = np.asarray(end_ns, dtype=np.int64)
    d0 = pd.Timestamp(int(end.min()), tz="UTC").tz_convert(CT).normalize() - pd.Timedelta(days=1); d1 = pd.Timestamp(int(end.max()), tz="UTC").tz_convert(CT).normalize() + pd.Timedelta(days=8)
    days = pd.date_range(d0.tz_localize(None), d1.tz_localize(None), freq="D"); days = days[days.weekday < 5]
    closes = np.sort((days + pd.Timedelta(hours=16)).tz_localize(CT).tz_convert("UTC").asi8); return closes[np.searchsorted(closes, end, side="right")]


def process_ticks(tk, dates, label=""):
    """ticks (ya cargados) → zonas AVZP2 → violeta → eventos; devuelve (DataFrame de eventos, contadores)."""
    t0 = time.time(); mod = ct_minute_of_day(tk.ts_ns); keep = np.asarray(~((mod >= 960) & (mod < 1020)))                  # sin la pausa CME 16:00-17:00 CT
    tk = dataclasses.replace(tk, **{f: (getattr(tk, f)[keep] if getattr(tk, f) is not None else None) for f in ("ts_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence")}); del mod, keep
    bars = B.build_tick_bars(tk, SPEC); fp = B.build_total_footprint_csr_nt8(tk, bars); n = len(bars.close_t); end = np.asarray(bars.end_ns, dtype=np.int64); send = session_end_vec(end)
    r = zones_run(bars, fp, send, ZPARAMS); zones = r["zones"]; vio = VZ.violet(zones, bars, fp, VPARAMS)
    us, uinv = np.unique(send, return_inverse=True); sdate = np.asarray(pd.to_datetime(us, utc=True).tz_convert(CT).strftime("%Y-%m-%d"))[uinv]
    last_of_session = np.searchsorted(send, send, side="right") - 1; bar_start = np.searchsorted(np.asarray(bars.tick_bar_idx), np.arange(n + 1)); price = np.asarray(tk.price_ticks, dtype=np.int64); cl = np.asarray(bars.close_t, dtype=np.int64)
    rows = []
    for i in np.flatnonzero(vio.departed):
        d = int(vio.decision_bar[i])
        if dates is not None and sdate[d] not in dates: continue
        for (D, a, b, res, pnl, j) in VZ.zone_events(zones[i], int(vio.direction[i]), d, price, bar_start, last_of_session, cl, DS, configs):
            rows.append((int(vio.purple[i]), sdate[d], D, a, b, res, pnl, zones[i]["high_tick"] - zones[i]["low_tick"] + 1, float(vio.ratio[i])))
    cnt = dict(label=label, bars=int(n), zones=len(zones), dir0=int((vio.direction == 0).sum()), departed=int(vio.departed.sum()), purple=int(vio.purple.sum()), ticks=int(len(price)), seconds=round(time.time() - t0))
    print(cnt, flush=True); del bars, fp, r, tk; gc.collect()
    return pd.DataFrame(rows, columns=["purple", "session", "D", "a", "b", "res", "pnl", "width", "ratio"]), cnt


def contract_rows(c, sess):
    rows = sess[sess.contract == c]; ds, fl = rows.groupby(["dataset", "file"]).size().idxmax()
    first = pd.Timestamp(rows.date.min()).tz_localize(CT) - pd.Timedelta(days=45); last = pd.Timestamp(rows.date.max()).tz_localize(CT) + pd.Timedelta(hours=16)
    return ds, fl, int(first.value), int(min(last.value, END_NS)), set(rows.date)


def aggregate(ev):
    g = ev.groupby(["purple", "D", "a", "b", "session"]).agg(n=("pnl", "size"), sum_pnl=("pnl", "sum"), n_tp=("res", lambda x: int((x == 1).sum())), n_sl=("res", lambda x: int((x == -1).sum())), n_to=("res", lambda x: int((x == 0).sum()))).reset_index()
    return g


def analyze(ag, rng):
    """Descubrimiento (60 % inicial de sesiones) con nulo de MÁXIMO por cambio de signo por sesión (conjunto en las 36 configuraciones) y réplica de las 3 mejores en el 40 % final."""
    pu = ag[ag.purple == 1]; ses = sorted(pu.session.unique()); k = int(len(ses) * SPLIT); s0, s1 = set(ses[:k]), set(ses[k:]); cfgs = sorted(set(zip(pu.D, pu.a, pu.b)))
    def mat(sub, sset):
        S = sorted(sset); idx = {s: i for i, s in enumerate(S)}; M = np.zeros((len(S), len(cfgs))); N = np.zeros((len(S), len(cfgs)))
        ci = {c: j for j, c in enumerate(cfgs)}
        for r in sub[sub.session.isin(sset)].itertuples(): M[idx[r.session], ci[(r.D, r.a, r.b)]] = r.sum_pnl; N[idx[r.session], ci[(r.D, r.a, r.b)]] = r.n
        return M, N, S
    M0, N0, S0 = mat(pu, s0); M1, N1, S1 = mat(pu, s1); out, ps, rows, desc = [], [], [], []
    ok0 = N0.sum(0) >= 100
    mean0 = np.where(N0.sum(0) > 0, M0.sum(0) / np.maximum(N0.sum(0), 1), 0.0)
    nul = np.empty((NPERM, len(cfgs)))
    for i in range(NPERM): nul[i] = (M0 * rng.choice([-1.0, 1.0], len(S0))[:, None]).sum(0) / np.maximum(N0.sum(0), 1)           # H0: esperanza bruta 0 (martingala), sesiones como clusters
    sd = nul.std(0) + 1e-12; z0 = np.where(ok0, mean0 / sd, -np.inf); zn = np.where(ok0, nul / sd, -np.inf).max(1); zmax = float(z0.max())
    p_max = float((1 + np.sum(zn >= zmax)) / (1 + NPERM)); top = np.argsort(-z0)[:3]
    r = dict(test="vio/max_disc", n_sessions_disc=len(S0), n_cfg=int(ok0.sum()), max_z=zmax, null_q95=float(np.quantile(zn, 0.95)), p=p_max, evaluable=True, disc=f"{S0[0]}..{S0[-1]}")
    out.append(r); ps.append(p_max); rows.append(r); print(r, flush=True)
    for j in top:
        D, a, bb = cfgs[j]; n1 = N1[:, j].sum()
        if n1 < 50: out.append(dict(test=f"vio/rep/{D}_{a}_{bb}", evaluable=False, n_rep=float(n1))); continue
        m1 = M1[:, j].sum() / n1; nl = np.array([(M1[:, j] * rng.choice([-1.0, 1.0], len(S1))).sum() / n1 for _ in range(NPERM)]); praw = float((1 + np.sum(nl >= m1)) / (1 + NPERM))
        net = m1 - COST_TICKS
        r2 = dict(test=f"vio/rep/{D}_{a}_{bb}", cfg=dict(D=D, a=a, b=bb), n_events_rep=float(n1), mean_gross_ticks_rep=float(m1), mean_net_ticks_rep=float(net), mean_gross_ticks_disc=float(mean0[j]), p_gross_raw=praw, p=praw if net > 0 else 1.0,
                  evaluable=True, rep=f"{S1[0]}..{S1[-1]}")
        out.append(r2); ps.append(r2["p"]); rows.append(r2); print(r2, flush=True)
    tab = []
    for (g, name) in ((1, "violeta"), (0, "alejada_no_violeta")):
        sub = ag[ag.purple == g]
        for (D, a, bb), x in sub.groupby(["D", "a", "b"]):
            n = x.n.sum(); tab.append(dict(group=name, D=int(D), a=int(a), b=int(bb), n=int(n), p_tp=float(x.n_tp.sum() / n), p_sl=float(x.n_sl.sum() / n), p_to=float(x.n_to.sum() / n), p_tp_breakeven=float(bb / (a + bb)),
                                           mean_gross=float(x.sum_pnl.sum() / n), mean_gross_D0=float(x[x.session.isin(s0)].sum_pnl.sum() / max(1, x[x.session.isin(s0)].n.sum())), mean_gross_D1=float(x[x.session.isin(s1)].sum_pnl.sum() / max(1, x[x.session.isin(s1)].n.sum())),
                                           events_per_session=float(n / max(1, x.session.nunique()))))
    return out, ps, rows, tab


def main():
    t0 = time.time(); rng = np.random.default_rng(SEED); import edgelab_data as ed
    ed.check_inputs((INST, DESDE, HASTA))                                  # verifica el manifiesto de lanzamiento (versiones y bytes) y que haya fuente para cada sesión aprobada
    sess = ed.sessions(INST, DESDE, HASTA); print("sesiones aprobadas", len(sess), "contratos", sorted(sess.contract.unique()), flush=True); parts, cnts = [], []
    for c in sorted(sess.contract.unique(), key=lambda x: (x[-2:], x[-5:-3])):
        ds, fl, a, b, dates = contract_rows(c, sess); tk = T.load_canonical_parquet(str(ed._path(ds, fl)), start_utc_ns=a, end_utc_ns=b); ev, cnt = process_ticks(tk, dates, c); parts.append(ev); cnts.append(cnt); del tk; gc.collect()
    ev = pd.concat(parts, ignore_index=True); ag = aggregate(ev); ag.to_parquet(OUT / "vio1_aggregates.parquet")
    out, ps, rows, tab = analyze(ag, rng); m = int(CFG.get("n_planned", len(ps))); o = np.argsort(ps); mx = 0.0
    for rank, i in enumerate(o): mx = max(mx, min(1.0, (m - rank) * ps[i])); rows[i]["p_holm_%d" % m] = mx
    (OUT / "STUDY_RESULTS.json").write_text(json.dumps(dict(campaign="VIO-1", cfg=CFG, nperm=NPERM, results_flat=out, descriptive=dict(table=tab, contracts=cnts), n_planned=m, seconds=round(time.time() - t0)), indent=1, default=float))
    print("listo en %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()

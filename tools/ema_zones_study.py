#!/usr/bin/env python3
r"""Descriptivo (NO es una prueba de hipótesis): ¿cómo se comporta el detector de zonas EMA-estables en la HISTORIA de NQ (25 ticks, EMA 200, sesiones aprobadas hasta 2026-09-30)?
Por configuración candidata: fracción de barras marcadas, zonas por sesión, duración, distancia precio-EMA en puntos, y deriva posterior a favor de la tendencia (ticks) a 50/100/200 barras
comparada con la de una regla trivial (solo pendiente de la EMA). Sin P&L ni costos. Las capturas del usuario son posteriores al holdout y NO se usan aquí.
Config en env EMAZ_CFG: {"inst","desde","hasta","ema_n","bar_ticks","configs":{nombre:{M,K,f,er,dmin,cv,hold}}}"""
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
    OUT = Path(os.environ.get("EMAZ_OUT", "/tmp/emaz_out"))
OUT.mkdir(parents=True, exist_ok=True); os.environ.setdefault("EDGELAB_ALLOW_MISSING", "1")
from edgelab.bridge import bars as B, ticks as T      # noqa: E402
from edgelab.research import ema_zones as Z            # noqa: E402
from edgelab.research import ema_zone_desc as ZD       # noqa: E402

CFG = json.loads(os.environ.get("EMAZ_CFG", "{}")); INST = CFG.get("inst", "NQ"); DESDE, HASTA = CFG.get("desde", "2025-07-01"), CFG.get("hasta", "2026-09-30")
EMA_N = int(CFG.get("ema_n", 200)); SPEC = int(CFG.get("bar_ticks", 25)); CONFIGS = CFG["configs"]; CT = "America/Chicago"; END_NS = pd.Timestamp("2026-09-30 22:00", tz="UTC").value
HZ = (50, 100, 200)


def ct_minute_of_day(ts):
    c = pd.to_datetime(np.asarray(ts), utc=True).tz_convert(CT); return (c.hour * 60 + c.minute).to_numpy()


def contract_rows(c, sess):
    rows = sess[sess.contract == c]; ds, fl = rows.groupby(["dataset", "file"]).size().idxmax()
    first = pd.Timestamp(rows.date.min()).tz_localize(CT) - pd.Timedelta(days=3); last = pd.Timestamp(rows.date.max()).tz_localize(CT) + pd.Timedelta(hours=16)
    return ds, fl, int(first.value), int(min(last.value, END_NS)), set(rows.date)


def session_date_of(end_ns):
    um, inv = np.unique(np.asarray(end_ns) // 60_000_000_000, return_inverse=True)
    c = pd.to_datetime(um * 60_000_000_000, utc=True).tz_convert(CT) + pd.Timedelta(hours=7)
    return np.asarray(c.strftime("%Y-%m-%d"))[inv]


def runs(st):
    """(inicio, fin, dir) de cada racha de estado != 0 constante."""
    ch = np.flatnonzero(np.r_[True, st[1:] != st[:-1], True]); return [(int(a), int(b - 1), int(st[a])) for a, b in zip(ch[:-1], ch[1:]) if st[a] != 0]


def process(tk, dates, label):
    mod = ct_minute_of_day(tk.ts_ns); keep = np.asarray(~((mod >= 960) & (mod < 1020)))
    tk = dataclasses.replace(tk, **{f: (getattr(tk, f)[keep] if getattr(tk, f) is not None else None) for f in ("ts_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence")})
    bars = B.build_tick_bars(tk, SPEC); c, h, l = (np.asarray(x, float) for x in (bars.close_t, bars.high_t, bars.low_t)); sd = session_date_of(bars.end_ns); inset = np.isin(sd, list(dates)); n = len(c)
    P = Z.precompute(c, h, l, ema_n=EMA_N, atr_n=100); PCACHE = {}; tick = float(tk.tick_size); rows = []
    slope = np.sign(np.r_[np.zeros(100), P["e"][100:] - P["e"][:-100]])
    if CFG.get("desc"):                                                          # estadística descriptiva por zona (sin hipótesis sobre el precio)
        name, kw = next(iter(CONFIGS.items())); kw = dict(kw); M = kw["M"]; ex = {k: kw.pop(k) for k in ("max_far_cv", "max_near_cv", "extend", "anchors", "atr_mult_break", "max_dist_atr", "atr_mult_tol", "vmax", "min_extent_atr", "max_mean_dist_atr", "min_zone") if k in kw}; en = kw.pop("ema_n", EMA_N)
        PP = P if en == EMA_N else Z.precompute(c, h, l, ema_n=en, atr_n=100); st = np.where(inset, Z.state(PP, **kw), 0); sim = Z.simulate_zones(PP, h, l, st, M, tick=tick, **{**CFG.get("sim_params", {}), **ex})
        ct = pd.to_datetime(np.asarray(bars.end_ns), utc=True).tz_convert(CT); out = ZD.zone_rows(sim, c, h, l, PP["e"], PP["atr"], np.asarray(bars.end_ns), np.asarray(bars.volume, float), sd, ct.hour.to_numpy(), ct.minute.to_numpy(), tick, label, inset)
        print(label, "zonas", len(out), flush=True); del P; gc.collect(); return out
    for name, kw in CONFIGS.items():
        if CFG.get("sim"):                                                      # réplica del indicador con tangente: zonas confirmadas
            kw = dict(kw); M = kw["M"]; ex = {k: kw.pop(k) for k in ("max_far_cv", "max_near_cv", "extend", "anchors", "atr_mult_break", "max_dist_atr", "atr_mult_tol", "vmax", "min_extent_atr", "max_mean_dist_atr", "min_zone") if k in kw}; en = kw.pop("ema_n", EMA_N); PP = PCACHE[en] if en in PCACHE else PCACHE.setdefault(en, P if en == EMA_N else Z.precompute(c, h, l, ema_n=en, atr_n=100)); st = Z.state(PP, **kw); st = np.where(inset, st, 0); sim = Z.simulate_zones(PP, h, l, st, M, tick=tick, **{**CFG.get("sim_params", {}), **ex}); cf = [z for z in sim if z["confirmed"] and inset[z["detect"]]]; fw = {}
            for H in HZ:
                v = [z["dir"] * (c[min(z["confirm_bar"] + H, n - 1)] - c[z["confirm_bar"]]) for z in cf]; fw[str(H)] = (float(np.sum(v)), len(v))
            rows.append(dict(config=name, contract=label, sessions=len(dates), raw_runs=int(sum(1 for z in sim if inset[z["detect"]])), confirmed=len(cf), length=[z["length"] for z in cf], move_pts=[z["move_pts"] for z in cf], touches=[z["touches"] for z in cf],
                             delay=[z["delay"] for z in cf], dirs=[z["dir"] for z in cf], broken=int(sum(1 for z in cf if "broken_at" in z)), fwd=fw)); continue
        st = Z.state(P, **kw); st = np.where(inset, st, 0); rs = [r for r in runs(st)]
        fwd = {}
        for H in HZ:
            ok = np.zeros(n, bool); ok[: n - H] = True; f = np.zeros(n); f[: n - H] = c[H:] - c[:-H]; sel = (st != 0) & ok & inset; base = (slope != 0) & ok & inset & (st == 0)
            fwd[H] = (float(np.sum(st[sel] * f[sel])), int(sel.sum()), float(np.sum(slope[base] * f[base])), int(base.sum()))
        gap = np.abs(P["g"]) * tick; rows.append(dict(config=name, contract=label, bars=int(inset.sum()), flagged=int(((st != 0) & inset).sum()), runs=len(rs), dur=[b - a + 1 for a, b, d in rs], gap_pts_median=[float(np.median(gap[a:b + 1]) ) for a, b, d in rs], disp_pts=[float(abs(c[b] - c[a]) * tick) for a, b, d in rs], dirs=[d for a, b, d in rs],
                                                         sessions=len(dates), fwd={str(k): v for k, v in fwd.items()}, tick=tick))
    print(label, "barras", int(inset.sum()), {r["config"]: r.get("runs", r.get("confirmed")) for r in rows[-len(CONFIGS):]}, flush=True); del P; gc.collect(); return rows


def summarize_sim(rows):
    out = {}
    for name in CONFIGS:
        R = [r for r in rows if r["config"] == name]; ses = sum(r["sessions"] for r in R); q = lambda a: dict(p10=float(np.percentile(a, 10)), median=float(np.median(a)), p90=float(np.percentile(a, 90))) if len(a) else None
        L = np.array([x for r in R for x in r["length"]]); mv = np.array([x for r in R for x in r["move_pts"]]); tc = np.array([x for r in R for x in r["touches"]]); dl = np.array([x for r in R for x in r["delay"]]); dirs = [d for r in R for d in r["dirs"]]
        out[name] = dict(params=CONFIGS[name], raw_runs=int(sum(r["raw_runs"] for r in R)), confirmed=int(len(L)), confirmed_per_session=round(len(L) / max(1, ses), 2), confirmed_up=int(sum(1 for d in dirs if d > 0)), confirmed_down=int(sum(1 for d in dirs if d < 0)),
                         length_bars=q(L), move_points=q(mv), touches=q(tc), confirm_delay_bars=q(dl), broken_share=round(sum(r["broken"] for r in R) / max(1, len(L)), 3),
                         forward_drift_ticks_after_confirmation={H: dict(mean=float(sum(r["fwd"][H][0] for r in R) / max(1, sum(r["fwd"][H][1] for r in R))), n=int(sum(r["fwd"][H][1] for r in R))) for H in map(str, HZ)})
    return out


def summarize(rows):
    if CFG.get("desc"): return ZD.summarize(rows, k=int(CFG.get("k", 4)))
    if CFG.get("sim"): return summarize_sim(rows)
    out = {}
    for name in CONFIGS:
        R = [r for r in rows if r["config"] == name]; bars = sum(r["bars"] for r in R); ses = sum(r["sessions"] for r in R); dur = np.array([d for r in R for d in r["dur"]]); gap = np.array([g for r in R for g in r["gap_pts_median"]]); disp = np.array([g for r in R for g in r["disp_pts"]]); long_ = dur >= 150; n_up = sum(1 for r in R for d in r["dirs"] if d > 0)
        per = {str(H): dict(zone_mean_ticks=float(sum(r["fwd"][str(H)][0] for r in R) / max(1, sum(r["fwd"][str(H)][1] for r in R))), zone_bars=int(sum(r["fwd"][str(H)][1] for r in R)),
                           slope_rule_mean_ticks=float(sum(r["fwd"][str(H)][2] for r in R) / max(1, sum(r["fwd"][str(H)][3] for r in R))), slope_rule_bars=int(sum(r["fwd"][str(H)][3] for r in R))) for H in HZ}
        out[name] = dict(params=CONFIGS[name], flagged_pct=round(100 * sum(r["flagged"] for r in R) / max(1, bars), 2), zones=int(len(dur)), zones_per_session=round(len(dur) / max(1, ses), 2), zones_up=int(n_up), zones_down=int(len(dur) - n_up),
                         duration_bars=dict(p10=float(np.percentile(dur, 10)), median=float(np.median(dur)), p90=float(np.percentile(dur, 90))) if len(dur) else None,
                         long150=dict(zones_per_session=round(int(long_.sum()) / max(1, ses), 2), bars_pct=round(100 * float(dur[long_].sum()) / max(1, bars), 2)), disp_points=dict(p10=float(np.percentile(disp, 10)), median=float(np.median(disp)), p90=float(np.percentile(disp, 90))) if len(disp) else None,
                         gap_points=dict(p10=float(np.percentile(gap, 10)), median=float(np.median(gap)), p90=float(np.percentile(gap, 90))) if len(gap) else None, forward_drift_ticks_with_trend=per)
    return out


def main():
    import edgelab_data as ed
    t0 = time.time(); ed.check_inputs((INST, DESDE, HASTA)); sess = ed.sessions(INST, DESDE, HASTA); print("sesiones", len(sess), flush=True); rows, errors = [], []
    for c in sorted(sess.contract.unique(), key=lambda x: (x[-2:], x[-5:-3])):
        try:
            ds, fl, a, b, dates = contract_rows(c, sess); tk = T.load_canonical_parquet(str(ed._path(ds, fl)), start_utc_ns=a, end_utc_ns=b); rows += process(tk, dates, c); del tk; gc.collect()
        except Exception:
            import traceback; errors.append(dict(contract=c, tb=traceback.format_exc()[-2500:])); print("ERROR", c, errors[-1]["tb"], flush=True)
    if not rows: (OUT / "ERROR.json").write_text(json.dumps(dict(errors=errors), indent=1)); return
    if CFG.get("desc"): pd.DataFrame(rows).to_csv(OUT / "zones_table_PRIVADA.csv", index=False)               # tabla por zona: privada, no se publica
    (OUT / "STUDY_RESULTS.json").write_text(json.dumps(dict(campaign="EMAZ-D1" if CFG.get("desc") else "EMAZ-1", note="descriptivo, no es una prueba de hipótesis; sin P&L", cfg=CFG, summary=summarize(rows), errors=errors, seconds=round(time.time() - t0)), indent=1)); print("listo", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()

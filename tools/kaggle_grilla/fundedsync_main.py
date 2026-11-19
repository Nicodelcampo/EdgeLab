"""Kernel: los 15 módulos de FUNDEDSYNCSTACK (valores de fábrica, 1 contrato) sobre M1 del Nasdaq 2012 → 2026-09 con costos de NQ y el
nulo intradía de m1_intradia (pre-registro docs/research/fundedsyncstack_20261115/PREREGISTRO_CADENA.md). Lo arma tools/fundedsync_cadena.py."""
import glob, json, os, time
import numpy as np, pandas as pd
M = __import__("m1_intradia"); from edgelab.research import fundedsyncstack as F
t0 = time.time(); ent = os.environ.get("ENTRADA", "/kaggle/input"); FR = float(os.environ.get("FRICCION", "1.5455")); REPS = int(os.environ.get("REPS", "20"))
D = M.leer_m1(glob.glob(ent + "/**/NQ_M1_dukas-M1-*.csv", recursive=True)[0])
D = D[(D.index >= "2012-01-20") & (D.index < "2026-09-30")]


def a_utc(D):
    t = D.index.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC"); ok = ~t.isna()
    return pd.DataFrame(dict(t=t[ok], o=D.o.values[ok], h=D.h.values[ok], l=D.l.values[ok], c=D.c.values[ok], v=(D.v.values if "v" in D else np.ones(len(D)))[ok]))   # el nulo no trae volumen


def _orb_t(D):
    mm = D.index.hour * 60 + D.index.minute; orb = D[(mm >= 570) & (mm < 585)]; dd = orb.index.normalize()
    return ((orb.h.groupby(dd).max() - orb.l.groupby(dd).min()) * 1.25).clip(2.0, 100.0)


def operaciones(D):
    ms = F.build_multi_series(F.load_m1_data(a_utc(D), end=os.environ.get("FIN", "2026-10-01")), tz_input="UTC"); out = {}   # holdout: FIN posterior
    for k in F.MODULOS:
        try: x = F.correr_modulo(k, ms)
        except Exception as ex: print("ERROR", k, str(ex)[:200], flush=True); out[k] = None; continue
        if not len(x): out[k] = pd.DataFrame(columns=["dia", "neto", "riesgo", "side"]); continue
        tt = pd.to_datetime(x.entry_time_utc, utc=True).dt.tz_convert("America/New_York")
        rg_k = (pd.to_numeric(x.entry_price, errors="coerce") - pd.to_numeric(x.stop_price, errors="coerce")).abs().astype(float).values
        if k == "T":       # auditoría 2026-11-16: stop_price es el stop ACTIVO al salir; el riesgo inicial de T = clip(rango 09:30–09:45 × 1,25, 2, 100)
            rg_k = _orb_t(D).reindex(tt.dt.tz_localize(None).dt.normalize()).to_numpy(float)
        out[k] = pd.DataFrame(dict(dia=tt.dt.tz_localize(None).dt.normalize(), t=((tt - pd.Timestamp(0, tz="UTC")) // pd.Timedelta("1s")).values, side=x.side.values,
                                   neto=pd.to_numeric(x.pnl_pts, errors="coerce").values - FR,
                                   riesgo=rg_k,
                                   salida=x.exit_name.values,
                                   mae_pts=(pd.to_numeric(x.mae_usd, errors="coerce") * (pd.to_numeric(x.pnl_pts, errors="coerce") / pd.to_numeric(x.pnl_usd, errors="coerce")).replace([np.inf, -np.inf], np.nan).median()).values))
    return out


ZBANDA = [(a, b, e) for (a, b) in ((10, 30), (15, 20), (30, 10)) for e in (35.0, 45.0, 55.0)]   # Z-banda (regimen_forward_20261119/PREREGISTRO_ZBANDA.md)


def operaciones_zbanda(D):
    """Las 9 configuraciones de severidad moderada de Z (misma conversión que `operaciones`); modulo = ZB_<cubeta>_<ema>_<eficiencia>."""
    ms = F.build_multi_series(F.load_m1_data(a_utc(D), end=os.environ.get("FIN", "2026-10-01")), tz_input="UTC"); out = {}
    for bk, em, ef in ZBANDA:
        x = F.correr_modulo("Z", ms, bucket_minutes=bk, ema_period=em, min_efficiency_pct=ef); k = f"ZB_{bk}_{em}_{ef:g}"
        if not len(x): out[k] = pd.DataFrame(columns=["dia", "neto", "riesgo", "side"]); continue
        tt = pd.to_datetime(x.entry_time_utc, utc=True).dt.tz_convert("America/New_York")
        out[k] = pd.DataFrame(dict(dia=tt.dt.tz_localize(None).dt.normalize(), t=((tt - pd.Timestamp(0, tz="UTC")) // pd.Timedelta("1s")).values, side=x.side.values,
                                   neto=pd.to_numeric(x.pnl_pts, errors="coerce").values - FR, riesgo=np.nan, salida=x.exit_name.values,
                                   mae_pts=(pd.to_numeric(x.mae_usd, errors="coerce") * (pd.to_numeric(x.pnl_pts, errors="coerce") / pd.to_numeric(x.pnl_usd, errors="coerce")).replace([np.inf, -np.inf], np.nan).median()).values))
    return out


def t_ses(df):
    if df is None or len(df) < 3: return None
    s = df.groupby("dia").neto.sum(); return float(s.mean() / s.std(ddof=1) * np.sqrt(len(s))) if s.std(ddof=1) > 0 else None


def resumen(ops):
    R = {}
    for k, df in ops.items():
        if df is None: R[k] = None; continue
        R[k] = {}
        for nom, a, b in M.PERIODOS:
            x = df[(df.dia >= a) & (df.dia <= b)]
            rg = pd.to_numeric(x.riesgo, errors="coerce").astype(float); con = x[np.isfinite(rg) & (rg > 0)]
            R[k][nom] = dict(n=int(len(x)), neto_pts=float(x.neto.mean()) if len(x) else None, t_ses=t_ses(x),
                             R=float((con.neto / rg[con.index]).mean()) if len(con) else None, n_con_stop=int(len(con)),
                             ganadoras=float((x.neto > 0).mean()) if len(x) else None)
    return R


if os.environ.get("SELLADO") == "1":                                    # apertura única (ACTA_HOLDOUT.md): desarrollo + USATECH sellado a M1
    from edgelab.research import fuentes_ticks as FT
    acta = os.path.abspath("ACTA_HOLDOUT.json"); json.dump(json.loads(os.environ["ACTA_JSON"]), open(acta, "w"))
    raiz = os.path.dirname(glob.glob(ent + "/**/SELLADO.txt", recursive=True)[0])
    T = pd.concat(list(FT.bloques_spot_sellado("USATECHIDXUSD", 20261001, int(os.environ.get("HASTA", "20261113")), raiz)), ignore_index=True)
    tt = pd.to_datetime(T.ts_ns.to_numpy(), utc=True).tz_convert("America/New_York").tz_localize(None)
    S = pd.DataFrame(dict(px=T.px.to_numpy(float), vol=T.vol.to_numpy(float)), index=tt).sort_index()
    B = S.px.resample("1min").ohlc().join(S.vol.resample("1min").sum()).dropna(subset=["open"])
    H = pd.DataFrame(dict(o=B.open, h=B.high, l=B.low, c=B.close, v=B.vol), index=B.index)
    D = pd.concat([D[D.index < H.index.min()], H]); print(f"holdout: {len(H)} velas M1 sellladas", flush=True)
    F.MODULOS = {k: F.MODULOS[k] for k in ("T", "Z", "R")}
    ops = operaciones(D)
    if os.environ.get("FW_ZBANDA") == "1": ops.update(operaciones_zbanda(D))
    ops = {k: v[v.dia >= os.environ.get("FW_DESDE", "2026-10-01")] for k, v in ops.items() if v is not None}
    mm = D.index.hour * 60 + D.index.minute; RR = D[(mm >= 570) & (mm < 960)]; dd = RR.index.normalize()
    atr20 = (RR.h.groupby(dd).max() - RR.l.groupby(dd).min()).rolling(20).mean().shift(1)          # stop de catástrofe (PREREGISTRO_TANDA2 L2)
    ses = (D.index + pd.Timedelta(hours=6)).normalize()                                           # sesión CME (18:00 NY → día siguiente)
    atr20_ses = (D.h.groupby(ses).max() - D.l.groupby(ses).min()).rolling(20).mean().shift(1)      # = tools/m1_largo.py::atr20 (R y Z validados)
    ops = {k: v.assign(atr20=atr20.reindex(v.dia).values, atr20_ses=atr20_ses.reindex(v.dia).values) for k, v in ops.items()}
    pd.concat([v.assign(modulo=k) for k, v in ops.items()]).to_csv("FUNDEDSYNC_HOLDOUT_OPS.csv", index=False)
    json.dump({k: dict(n=int(len(v)), neto_pts=float(v.neto.mean()) if len(v) else None, ee=float(v.neto.std(ddof=1) / np.sqrt(len(v))) if len(v) > 1 else None)
               for k, v in ops.items()}, open("RESULTADO_HOLDOUT.json", "w"), indent=1); print("listo holdout"); raise SystemExit(0)
real = operaciones(D); Rr = resumen(real); print(f"[{time.time() - t0:6.0f}s] real listo", flush=True)
pd.concat([v.assign(modulo=k) for k, v in real.items() if v is not None and len(v)]).to_csv("FUNDEDSYNC_OPS.csv.gz", index=False)
nulo = []
for s in range(REPS):
    Rs = resumen(operaciones(M.sintetica_m1(D, 5000 + s)))
    nulo.append(max((v["OOS"]["t_ses"] for v in Rs.values() if v and v["OOS"]["t_ses"] is not None), default=float("nan")))   # tramo principal: 2020–2023
    print(f"[{time.time() - t0:6.0f}s] nulo {s} tmax {nulo[-1]:.2f}", flush=True)
json.dump(dict(modulos=Rr, nulo_tmax_oos=nulo, umbral_p95=float(np.nanpercentile(nulo, 95)) if nulo else None, friccion_pts=FR,
               segundos=round(time.time() - t0)), open("RESULTADO.json", "w"), indent=1, default=float)
print("listo")

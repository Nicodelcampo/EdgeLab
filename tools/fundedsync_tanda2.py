#!/usr/bin/env python3
"""FundedSync tanda 2 (pre-registro docs/research/fundedsyncstack_20261115/PREREGISTRO_TANDA2.md).

  python tools/fundedsync_tanda2.py salidas  <carpeta M1>   # L1: salida al cierre vs técnica (S, A20, W, N) en S&P, Dow, Russell (+ Nasdaq aparte)
  python tools/fundedsync_tanda2.py tendencia <carpeta M1>  # L3 + L4: días de tendencia (E0) y volatilidad rugosa / Hurst
  python tools/fundedsync_tanda2.py knn <carpeta M1>        # L4bis: capa KNN sombra sobre PREAPERTURA-NQ y CVGAP-ES-C
  python tools/fundedsync_tanda2.py catastrofe <carpeta M1> # L2: Z y R con stop de catástrofe 0,5 × ATR20 (desarrollo, descriptivo)
<carpeta M1>: los CSV de `edgelab-sqx-m1` (NQ_M1_dukas.csv, SP_M1_dukas.csv, DJ_M1_dukas.csv, USSC2000IDXUSD.csv).
Salida: docs/research/fundedsyncstack_20261115/tanda2/*.json. Reusa m1_intradia.leer_m1 y el paquete fundedsyncstack.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.research import m1_intradia as M  # noqa: E402

OUT = ROOT / "docs/research/fundedsyncstack_20261115/tanda2"
INST = {"NQ_M1_dukas": ("NQ", 1.5455), "SP_M1_dukas": ("ES", 0.8877), "DJ_M1_dukas": ("YM", 5.052), "USSC2000IDXUSD": ("RTY", 0.4436)}
PRUEBA = ("SP_M1_dukas", "DJ_M1_dukas", "USSC2000IDXUSD")
VARIANTES = {"S": dict(exit_on_st_flip=False, use_hard_stop=True), "A20": dict(exit_on_st_flip=False), "W": dict(exit_on_vwap_cross=False),
             "N": dict(use_failed_breakout_exit=False)}
TRAMOS = (("2012-2019", "2012-01-01", "2019-12-31"), ("2020-2023", "2020-01-01", "2023-12-31"), ("2024-2026", "2024-01-01", "2026-09-29"))


def leer(carpeta, sim):
    D = M.leer_m1(Path(carpeta) / f"{sim}.csv"); return D[(D.index >= "2012-01-20") & (D.index < "2026-09-30")]


def a_utc(D):
    t = D.index.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC"); ok = ~t.isna()
    return pd.DataFrame(dict(t=t[ok], o=D.o.values[ok], h=D.h.values[ok], l=D.l.values[ok], c=D.c.values[ok], v=D.v.values[ok]))


def diario(D):
    m = D.index.hour * 60 + D.index.minute; R = D[(m >= 570) & (m < 960)]; d = R.index.normalize()
    day = pd.DataFrame(dict(o=R.o.groupby(d).first(), h=R.h.groupby(d).max(), l=R.l.groupby(d).min(), c=R.c.groupby(d).last()))
    day["atr20"] = (day.h - day.l).rolling(20).mean().shift(1); return day


def _ops(x, fr):
    if not len(x): return pd.DataFrame(columns=["dia", "neto"])
    tt = pd.to_datetime(x.entry_time_utc, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    return pd.DataFrame(dict(dia=tt.dt.normalize(), neto=pd.to_numeric(x.pnl_pts, errors="coerce").values - fr,
                             mae=pd.to_numeric(x.get("mae_usd", np.nan), errors="coerce").values, salida=x.exit_name.astype(str).str.replace(r"_\d+$", "", regex=True).values))


def _boot_media(v, seed=7, B=10000):
    v = np.asarray(v, float); i = np.random.default_rng(seed).integers(0, len(v), (B, len(v))); m = v[i].mean(1)
    return float((1 + (m <= 0).sum()) / (B + 1))


def _bh(ps, q=0.10):
    ps = np.asarray(ps); o = np.argsort(ps); k = 0
    for j, idx in enumerate(o, 1):
        if ps[idx] <= q * j / len(ps): k = j
    nom = np.zeros(len(ps), bool); nom[o[:k]] = True; return nom.tolist()


def salidas(carpeta):
    from edgelab.research import fundedsyncstack as F
    res, dif = {}, {k: [] for k in VARIANTES}
    for sim, (fut, fr) in INST.items():
        D = leer(carpeta, sim); day = diario(D); ms = F.build_multi_series(F.load_m1_data(a_utc(D), end="2026-10-01"), tz_input="UTC"); res[sim] = {}
        for k, kw in VARIANTES.items():
            a = _ops(F.correr_modulo(k, ms), fr); b = _ops(F.correr_modulo(k, ms, **kw), fr)
            sa, sb = a.groupby("dia").neto.sum(), b.groupby("dia").neto.sum(); dias = sa.index.union(sb.index)
            d = (sb.reindex(dias, fill_value=0) - sa.reindex(dias, fill_value=0)) / day.atr20.reindex(dias)
            d = d[np.isfinite(d)]
            if sim in PRUEBA: dif[k].append(d.values)
            res[sim][k] = dict(original=dict(n=len(a), neto=float(a.neto.mean()) if len(a) else None, peor_dia=float(sa.min()) if len(sa) else None),
                               variante=dict(n=len(b), neto=float(b.neto.mean()) if len(b) else None, peor_dia=float(sb.min()) if len(sb) else None),
                               dif_dia_atr=float(d.mean()) if len(d) else None, p_dif=_boot_media(d.values) if len(d) > 5 else None,
                               por_tramo={n: dict(original=float(a[(a.dia >= x) & (a.dia <= y)].neto.sum()), variante=float(b[(b.dia >= x) & (b.dia <= y)].neto.sum())) for n, x, y in TRAMOS},
                               salidas_variante=b.salida.value_counts().to_dict())
            print(sim, k, "orig", round(res[sim][k]["original"]["neto"] or 0, 2), "var", round(res[sim][k]["variante"]["neto"] or 0, 2), "p", res[sim][k]["p_dif"], flush=True)
    pooled = {k: dict(dif_dia_atr=float(np.concatenate(v).mean()), p=_boot_media(np.concatenate(v)), mejor_en=sum(res[s][k]["dif_dia_atr"] > 0 for s in PRUEBA)) for k, v in dif.items()}
    bh = _bh([pooled[k]["p"] for k in VARIANTES])
    for k, b in zip(VARIANTES, bh): pooled[k].update(bh=b, confirmada=bool(b and pooled[k]["mejor_en"] >= 2))
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "L1_SALIDAS.json").write_text(json.dumps(dict(por_indice=res, prueba_SP_DJ_RTY=pooled), indent=1, default=float))
    print(json.dumps(pooled, indent=1))


# ---------------------------------------------------------------- L4: volatilidad rugosa / Hurst
def hurst_variograma(lv, lags=range(1, 51)):
    lv = np.asarray(lv, float); lv = lv[np.isfinite(lv)]
    m = [np.mean((lv[k:] - lv[:-k]) ** 2) for k in lags]
    return float(np.polyfit(np.log(list(lags)), np.log(m), 1)[0] / 2)


def hurst_rs(x, tamanos=(10, 20, 40, 80, 160, 250)):
    x = np.asarray(x, float); x = x[np.isfinite(x)]; rs = []
    for n in tamanos:
        v = []
        for i in range(0, len(x) - n + 1, n):
            s = x[i:i + n]; z = np.cumsum(s - s.mean()); sd = s.std()
            if sd > 0: v.append((z.max() - z.min()) / sd)
        rs.append(np.mean(v))
    return float(np.polyfit(np.log(tamanos), np.log(rs), 1)[0])


def _ols(X, y):
    X = np.c_[np.ones(len(X)), X]; b, *_ = np.linalg.lstsq(X, y, rcond=None); return b


def pronosticos(lv: pd.Series, H: float, desde="2016-01-01") -> pd.DataFrame:
    """Pronóstico de la log-volatilidad (log rango) de cada día con información hasta el día previo; re-ajuste anual expansivo."""
    x = lv.values; n = len(x); K = 250
    w = np.array([1.0 / ((k + 1.0) * k ** (H + 0.5)) for k in range(1, K + 1)]); w = w / w.sum()       # núcleo rugoso (GJR 2014), normalizado
    feats = {"rw": np.r_[np.nan, x[:-1]]}
    s = pd.Series(x); feats["m5"] = s.shift(1).rolling(5).mean().values; feats["m22"] = s.shift(1).rolling(22).mean().values
    rug = np.full(n, np.nan)
    for t in range(K + 1, n): rug[t] = np.dot(w, x[t - 1::-1][:K])
    feats["rug"] = rug
    F = pd.DataFrame(feats, index=lv.index); F["y"] = x; out = pd.DataFrame(index=lv.index)
    for col in ("ar1", "har", "rugoso"): out[col] = np.nan
    out["rw"] = F.rw
    for anio in sorted({d.year for d in lv.index if d >= pd.Timestamp(desde)}):
        tr = F[(F.index < pd.Timestamp(f"{anio}-01-01"))].dropna(); te = F[(F.index.year == anio)].dropna()
        if len(tr) < 300 or not len(te): continue
        b = _ols(tr[["rw"]].values, tr.y.values); out.loc[te.index, "ar1"] = b[0] + te[["rw"]].values @ b[1:]
        b = _ols(tr[["rw", "m5", "m22"]].values, tr.y.values); out.loc[te.index, "har"] = b[0] + te[["rw", "m5", "m22"]].values @ b[1:]
        b = _ols(tr[["rug"]].values, tr.y.values); out.loc[te.index, "rugoso"] = b[0] + te[["rug"]].values @ b[1:]
    out["y"] = F.y; return out


def _auc(score, y):
    s = pd.Series(score).rank().values; y = np.asarray(y, bool); n1, n0 = y.sum(), (~y).sum()
    return float((s[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else None


def _logit(X, y, it=50):
    X = np.c_[np.ones(len(X)), X]; b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p) + 1e-9
        b = b + np.linalg.solve((X.T * W) @ X + 1e-6 * np.eye(len(b)), X.T @ (y - p))
    return b


def tabla_dia(D, nombre):
    m = D.index.hour * 60 + D.index.minute; dd = D.index.normalize()
    R = D[(m >= 570) & (m < 960)]; dR = R.index.normalize()
    day = pd.DataFrame(dict(o=R.o.groupby(dR).first(), h=R.h.groupby(dR).max(), l=R.l.groupby(dR).min(), c=R.c.groupby(dR).last()))
    P1 = D[(m >= 570) & (m < 630)]; d1 = P1.index.normalize()
    P2 = D[(m >= 630) & (m < 960)]; d2 = P2.index.normalize()
    day["h1"], day["l1"], day["p1030"], day["v1"] = P1.h.groupby(d1).max(), P1.l.groupby(d1).min(), P1.c.groupby(d1).last(), P1.v.groupby(d1).sum()
    day["h2"], day["l2"] = P2.h.groupby(d2).max(), P2.l.groupby(d2).min()
    day = day.dropna(); rango = day.h - day.l; day["atr20"] = rango.rolling(20).mean().shift(1)
    day["E1"] = (day.c - day.o).abs() >= 0.8 * rango
    day["E2"] = (day.c - day.p1030).abs() >= 0.6 * (day.h2 - day.l2)
    day["r1"] = (day.h1 - day.l1) / day.atr20
    day["ef1"] = (day.p1030 - day.o).abs() / (day.h1 - day.l1)
    day["vrel"] = day.v1 / day.v1.rolling(20).mean().shift(1)
    day["gap_al"] = (np.sign(day.o - day.c.shift(1)) == np.sign(day.p1030 - day.o)).astype(float)
    N = D[(m >= 18 * 60) | (m < 570)]; sn = (N.index + pd.Timedelta(hours=6)).normalize()
    noche = ((N.h.groupby(sn).max() - N.l.groupby(sn).min()).reindex(day.index)) / day.c.shift(1)
    day["noche"] = noche.rolling(251, min_periods=120).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True)
    day["vol20"] = rango.rolling(20).mean().shift(1).rolling(251, min_periods=120).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True)
    lv = np.log(rango.clip(lower=1e-9)); H = hurst_variograma(lv[lv.index < "2016-01-01"])
    pr = pronosticos(lv, H); day["pron_har"] = np.exp(pr.har) / day.atr20; day["pron_rug"] = np.exp(pr.rugoso) / day.atr20
    return day, lv, pr


PRED = ("r1", "ef1", "vrel", "gap_al", "noche", "vol20", "pron_har", "pron_rug")
CORTES = (("A", "2012-01-01", "2019-12-31"), ("B", "2020-01-01", "2023-12-31"), ("C", "2024-01-01", "2026-09-29"))


def tendencia(carpeta):
    OUT.mkdir(parents=True, exist_ok=True); res = {"L3": {}, "L4": {}}
    for sim in INST:
        D = leer(carpeta, sim); day, lv, pr = tabla_dia(D, sim)
        # L4: Hurst y pronósticos
        r = np.log(day.c / day.c.shift(1))
        res["L4"][sim] = dict(H_logvol={n: hurst_variograma(lv[(lv.index >= x) & (lv.index <= y)]) for n, x, y in TRAMOS},
                              H_logvol_lag5a50=hurst_variograma(lv, range(5, 51)), H_precio_RS=hurst_rs(r.values[1:]),
                              mse_relativo_rw={c: float(((pr[c] - pr.y) ** 2).mean() / ((pr.rw - pr.y) ** 2)[pr[c].notna()].mean()) for c in ("ar1", "har", "rugoso")},
                              ar1_logvol=float(np.corrcoef(lv.values[1:], lv.values[:-1])[0, 1]))
        res["L3"][sim] = {}
        for et in ("E1", "E2"):
            fila = {"tasa": {n: float(day[(day.index >= x) & (day.index <= y)][et].mean()) for n, x, y in CORTES}}
            A_ = day[(day.index >= "2012-01-01") & (day.index <= "2019-12-31")].dropna(subset=list(PRED))
            for p in PRED:
                sgn = 1.0 if (_auc(A_[p].values, A_[et].values) or 0.5) >= 0.5 else -1.0
                fila[p] = {n: _auc(sgn * day[(day.index >= x) & (day.index <= y)].dropna(subset=[p])[p].values,
                                   day[(day.index >= x) & (day.index <= y)].dropna(subset=[p])[et].values) for n, x, y in CORTES}
            mu, sd = A_[list(PRED)].mean(), A_[list(PRED)].std(); b = _logit(((A_[list(PRED)] - mu) / sd).values, A_[et].values.astype(float))
            comb = {}
            for n, x, y in CORTES:
                T = day[(day.index >= x) & (day.index <= y)].dropna(subset=list(PRED)); z = np.c_[np.ones(len(T)), ((T[list(PRED)] - mu) / sd).values] @ b
                comb[n] = _auc(z, T[et].values)
            fila["combinado"] = comb; res["L3"][sim][et] = fila
        print(sim, "H logvol", {k: round(v, 3) for k, v in res["L4"][sim]["H_logvol"].items()}, "MSE/rw", {k: round(v, 3) for k, v in res["L4"][sim]["mse_relativo_rw"].items()}, flush=True)
        for et in ("E1", "E2"): print("   ", et, {p: res["L3"][sim][et][p]["B"] and round(res["L3"][sim][et][p]["B"], 3) for p in PRED + ("combinado",)}, flush=True)
    sirve = {}
    for et in ("E1", "E2"):
        for p in PRED + ("combinado",):
            ok = sum(1 for s in INST if (res["L3"][s][et][p]["B"] or 0) >= 0.60 and (res["L3"][s][et][p]["C"] or 0) >= 0.60)
            sirve[f"{et}:{p}"] = dict(indices_ok=ok, sirve=ok >= 3)
    res["L3_lectura"] = sirve
    (OUT / "L3_L4_TENDENCIA_RUGOSA.json").write_text(json.dumps(res, indent=1, default=float)); print(json.dumps(sirve, indent=1))


PRED12 = ("ef_m", "r_m", "z_vwap", "v_m", "pron_rug", "frac_rec")


def mediodia(carpeta):
    """Enmienda 1: ¿la tarde continúa la mañana? Predictores conocidos a las 12:00 (AUC en A/B/C, 4 índices)."""
    res = {}
    for sim in INST:
        D = leer(carpeta, sim); m = D.index.hour * 60 + D.index.minute
        day, lv, pr = tabla_dia(D, sim)
        Mn = D[(m >= 570) & (m < 720)]; dm = Mn.index.normalize(); Tn = D[(m >= 720) & (m < 960)]; dt_ = Tn.index.normalize()
        pv = (Mn.h + Mn.l + Mn.c) / 3
        g = pd.DataFrame(dict(o=Mn.o.groupby(dm).first(), p12=Mn.c.groupby(dm).last(), hm=Mn.h.groupby(dm).max(), lm=Mn.l.groupby(dm).min(),
                              vm=Mn.v.groupby(dm).sum(), vw=(pv * Mn.v).groupby(dm).sum() / Mn.v.groupby(dm).sum().replace(0, np.nan),
                              sd=pv.groupby(dm).std(), c=Tn.c.groupby(dt_).last(), hit=Tn.h.groupby(dt_).max(), lot=Tn.l.groupby(dt_).min())).dropna()
        g = g.join(day[["atr20", "pron_rug"]], how="inner")
        mov_m = g.p12 - g.o; mov_t = g.c - g.p12
        g["E3"] = (np.sign(mov_t) == np.sign(mov_m)) & ((mov_t.abs() / (g.hit - g.lot)) >= 0.5)
        g["ef_m"] = mov_m.abs() / (g.hm - g.lm); g["r_m"] = (g.hm - g.lm) / g.atr20
        g["z_vwap"] = np.sign(mov_m) * (g.p12 - g.vw) / g.sd.replace(0, np.nan)
        g["v_m"] = g.vm / g.vm.rolling(20).mean().shift(1); g["frac_rec"] = (g.hm - g.lm) / (g.pron_rug * g.atr20)
        fila = {"tasa": {n: float(g[(g.index >= x) & (g.index <= y)].E3.mean()) for n, x, y in CORTES}}
        A_ = g[(g.index >= "2012-01-01") & (g.index <= "2019-12-31")].dropna(subset=list(PRED12))
        usados = [p for p in PRED12 if g[p].notna().sum() > 200]
        for p in usados:
            sgn = 1.0 if (_auc(A_[p].values, A_.E3.values) or 0.5) >= 0.5 else -1.0
            fila[p] = {n: _auc(sgn * T[p].values, T.E3.values) for n, x, y in CORTES for T in [g[(g.index >= x) & (g.index <= y)].dropna(subset=[p])]}
        if len(A_) > 200:
            mu, sd = A_[usados].mean(), A_[usados].std(); b = _logit(((A_[usados] - mu) / sd).values, A_.E3.values.astype(float))
            fila["combinado"] = {n: _auc(np.c_[np.ones(len(T)), ((T[usados] - mu) / sd).values] @ b, T.E3.values)
                                 for n, x, y in CORTES for T in [g[(g.index >= x) & (g.index <= y)].dropna(subset=usados)]}
        res[sim] = fila; print(sim, {p: fila[p]["B"] and round(fila[p]["B"], 3) for p in fila if p != "tasa"}, flush=True)
    sirve = {p: sum(1 for s in res if p in res[s] and (res[s][p]["B"] or 0) >= 0.60 and (res[s][p]["C"] or 0) >= 0.60) for p in PRED12 + ("combinado",)}
    (OUT / "L3_MEDIODIA.json").write_text(json.dumps(dict(por_indice=res, indices_ok=sirve), indent=1, default=float)); print(sirve)


# ---------------------------------------------------------------- L4bis: capa KNN sombra
REGLAS_KNN = {"PREAPERTURA-NQ": ("NQ_M1_dukas", "docs/research/cartera_20261116/ops/PREAPERTURA-NQ__{t}.json", False),
              "CVGAP-ES-C": ("SP_M1_dukas", "docs/research/canasta_7_20261030/desarrollo_en_r/CVGAP-ES-C__{t}.json", False)}
RASGOS = ("r5", "r15", "r30", "r60", "rango15", "ubic15", "dvwap", "ret_ap", "minuto", "lado")


def rasgos(D, ops):
    """Rasgos en la entrada con barras cerradas ANTES del minuto de la señal (causal)."""
    idx = D.index; c = D.c.values; h = D.h.values; l = D.l.values; v = D.v.values; m = idx.hour * 60 + idx.minute
    dia = idx.normalize(); pv = (D.h + D.l + D.c).values / 3
    ses = pd.Series(np.where(m >= 18 * 60, 1, 0)).values
    filas = []
    for _, o in ops.iterrows():
        te = pd.Timestamp(o.t, unit="s", tz="UTC").tz_convert("America/New_York").tz_localize(None)
        j = idx.searchsorted(te) - 1
        if j < 61: filas.append([np.nan] * len(RASGOS)); continue
        p = c[j]; f = lambda k: (p / c[j - k] - 1) * 1e4
        h15, l15 = h[j - 14:j + 1].max(), l[j - 14:j + 1].min()
        d0 = idx.searchsorted(te.normalize() + pd.Timedelta(minutes=570)) if te.hour * 60 + te.minute >= 570 else idx.searchsorted(te.normalize() - pd.Timedelta(hours=6))
        d0 = min(d0, j); vw = np.sum(pv[d0:j + 1] * v[d0:j + 1]) / max(np.sum(v[d0:j + 1]), 1e-9)
        filas.append([f(5), f(15), f(30), f(60), (h15 - l15) / p * 1e4, (p - l15) / (h15 - l15) if h15 > l15 else 0.5, (p / vw - 1) * 1e4,
                      (p / c[d0] - 1) * 1e4, te.hour * 60 + te.minute, float(o.side)])
    return pd.DataFrame(filas, columns=RASGOS, index=ops.index)


def knn(carpeta):
    OUT.mkdir(parents=True, exist_ok=True); res = {}
    for regla, (sim, ruta, en_R) in REGLAS_KNN.items():
        D = M.leer_m1(Path(carpeta) / f"{sim}.csv"); partes = []
        for t in ("desc", "rep"):
            o = json.loads((ROOT / ruta.format(t=t)).read_text())["operaciones"]
            df = pd.DataFrame(dict(ses=o["ses"], t=o["t"], neto=o["neto"], riesgo=o["riesgo"], tramo=t))
            df["side"] = np.sign(np.asarray(o.get("lado", [1] * len(df)), float)) if "lado" in o else 1.0
            partes.append(df)
        ops = pd.concat(partes, ignore_index=True).sort_values("t").reset_index(drop=True)
        ops["R"] = ops.neto if en_R else ops.neto / ops.riesgo
        X = rasgos(D, ops); ops = ops.join(X).dropna(subset=list(RASGOS)).reset_index(drop=True)
        tq = pd.to_datetime(ops.t, unit="s").dt.to_period("Q"); toma = np.full(len(ops), np.nan)
        for q in sorted(tq.unique()):
            tr = ops[tq < q]; te = ops.index[tq == q]
            if len(tr) < 40: continue
            mu, sd = tr[list(RASGOS)].mean(), tr[list(RASGOS)].std().replace(0, 1)
            A_ = ((tr[list(RASGOS)] - mu) / sd).values; y = (tr.R > 0).values
            for i in te:
                z = ((ops.loc[i, list(RASGOS)] - mu) / sd).values.astype(float); d = np.sqrt(((A_ - z) ** 2).sum(1))
                toma[i] = float(y[np.argsort(d)[:15]].mean() >= 0.5)
        ops["toma"] = toma; rep = ops[(ops.tramo == "rep") & ops.toma.notna()]
        tk, sk = rep[rep.toma == 1], rep[rep.toma == 0]
        dias = np.unique(rep.ses); pos = {d: i for i, d in enumerate(dias)}; B = 10000; rng = np.random.default_rng(11)
        st, nt, ss, ns = (np.zeros(len(dias)) for _ in range(4))
        np.add.at(st, [pos[d] for d in tk.ses], tk.R.values); np.add.at(nt, [pos[d] for d in tk.ses], 1)
        np.add.at(ss, [pos[d] for d in sk.ses], sk.R.values); np.add.at(ns, [pos[d] for d in sk.ses], 1)
        i = rng.integers(0, len(dias), (B, len(dias))); dif = st[i].sum(1) / np.maximum(nt[i].sum(1), 1) - ss[i].sum(1) / np.maximum(ns[i].sum(1), 1)
        res[regla] = dict(rep_n=int(len(rep)), rep_R_todas=float(rep.R.mean()), rep_n_tomadas=int(len(tk)), rep_R_tomadas=float(tk.R.mean()) if len(tk) else None,
                          rep_R_salteadas=float(sk.R.mean()) if len(sk) else None, p_tomadas_mejor=float((1 + (dif <= 0).sum()) / (B + 1)),
                          desc_n_evaluadas=int(ops[(ops.tramo == "desc") & ops.toma.notna()].shape[0]),
                          desc_R_tomadas=float(ops[(ops.tramo == "desc") & (ops.toma == 1)].R.mean()), desc_R_todas=float(ops[(ops.tramo == "desc") & ops.toma.notna()].R.mean()))
        print(regla, res[regla], flush=True)
    bh = _bh([res[r]["p_tomadas_mejor"] for r in res])
    for r, b in zip(res, bh): res[r]["bh"] = b
    (OUT / "L4bis_KNN.json").write_text(json.dumps(res, indent=1, default=float))


# ---------------------------------------------------------------- L2: stop de catástrofe para Z y R (desarrollo, descriptivo)
def catastrofe(carpeta):
    from edgelab.research import fundedsyncstack as F
    D = leer(carpeta, "NQ_M1_dukas"); day = diario(D); ms = F.build_multi_series(F.load_m1_data(a_utc(D), end="2026-10-01"), tz_input="UTC"); res = {}
    for k in ("Z", "R", "T"):
        x = F.correr_modulo(k, ms); o = _ops(x, 1.5455)
        pts_por_usd = (pd.to_numeric(x.pnl_pts, errors="coerce") / pd.to_numeric(x.pnl_usd, errors="coerce")).replace([np.inf, -np.inf], np.nan).median()
        o["mae_pts"] = o.mae * pts_por_usd; o["stop"] = 0.5 * day.atr20.reindex(o.dia).values
        o["neto_cat"] = np.where((k != "T") & (o.mae_pts >= o.stop), -o.stop - 1.5455, o.neto)
        res[k] = {n: dict(n=int(len(g)), neto=float(g.neto.mean()), neto_con_stop=float(g.neto_cat.mean()), peor=float(g.neto.min()), peor_con_stop=float(g.neto_cat.min()),
                          cortadas=int(((g.mae_pts >= g.stop) & (k != "T")).sum()))
                  for n, x0, y0 in TRAMOS for g in [o[(o.dia >= x0) & (o.dia <= y0)]]}
        print(k, res[k], flush=True)
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "L2_CATASTROFE.json").write_text(json.dumps(res, indent=1, default=float))


# ---------------------------------------------------------------- Tanda 3 (PREREGISTRO_TANDA3.md)
FUENTE_EJEC = {"NQ": "NQ_M1_dukas", "ES": "SP_M1_dukas", "YM": "DJ_M1_dukas"}


def tamano_vol(carpeta):
    """V1: t diario en USD con micros fijos vs micros escalados por la volatilidad pronosticada (rugosa), en reglas fuera de la cartera v2."""
    sys.path.insert(0, str(ROOT / "tools"))
    from cartera_nov import universo, DIR as CDIR
    from cartera_nov_analisis import _ops, MICRO
    from edgelab import costos as C
    sel = set(json.loads((CDIR / "SELECCION.json").read_text())["futuros"]); F = {}
    for ej, sim in FUENTE_EJEC.items():
        day, lv, pr = tabla_dia(leer(carpeta, sim), sim); f = np.exp(pr.rugoso)
        F[ej] = pd.DataFrame(dict(F=f, med=f.rolling(250, min_periods=60).median().shift(1)))
    res = {}
    for r in universo():
        sp = r["spec"]; ej = sp.get("ejecucion") or sp["sensor"]
        if r["cid"] in sel or ej not in FUENTE_EJEC: continue
        o = [x for x in (_ops(r["cid"], "desc"), _ops(r["cid"], "rep")) if x is not None]
        if not o: continue
        ses = np.r_[o[0]["ses"], o[1]["ses"]] if len(o) > 1 else o[0]["ses"]; R = np.r_[o[0]["R"], o[1]["R"]] if len(o) > 1 else o[0]["R"]
        rg = np.r_[o[0]["riesgo"], o[1]["riesgo"]] if len(o) > 1 else o[0]["riesgo"]
        m = MICRO[ej]; usd_pt = C.tick_value_usd(m) / C.tick_size(m); n_fix = max(1, round(200.0 / (np.median(rg) * usd_pt)))
        dias = pd.to_datetime(pd.Series(ses).astype(str)); FF = F[ej].reindex(dias.values)
        esc = (FF.med / FF.F).values; ok = np.isfinite(esc)
        n_vol = np.maximum(1, np.round(n_fix * esc[ok])); usd = R * rg * usd_pt
        df = pd.DataFrame(dict(ses=ses[ok], fijo=usd[ok] * n_fix, vol=usd[ok] * n_vol))
        dd = df.groupby("ses")[["fijo", "vol"]].sum()
        if len(dd) < 20: continue
        t = {k: float(dd[k].mean() / dd[k].std(ddof=1) * np.sqrt(len(dd))) for k in ("fijo", "vol")}
        def dmax(x): e = np.cumsum(x / np.abs(x).mean()); return float((e - np.maximum.accumulate(np.r_[0, e])[1:]).min())
        res[r["cid"]] = dict(ejec=ej, dias=int(len(dd)), t_fijo=t["fijo"], t_vol=t["vol"], dt=t["vol"] - t["fijo"], dd_fijo=dmax(dd.fijo.values), dd_vol=dmax(dd.vol.values),
                             usd_dia_fijo=float(dd.fijo.mean()), usd_dia_vol=float(dd.vol.mean()))
        print(r["cid"], {k: round(v, 2) if isinstance(v, float) else v for k, v in res[r["cid"]].items()}, flush=True)
    from math import comb
    pos = sum(v["dt"] > 0 for v in res.values()); n = len(res)
    p = sum(comb(n, k) for k in range(pos, n + 1)) / 2 ** n if n else None
    out = dict(reglas=res, n=n, dt_positivo=pos, frac=pos / n if n else None, p_signo=p, pasa=bool(n and pos / n >= 0.6 and p < 0.05))
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "T3_V1_TAMANO_VOL.json").write_text(json.dumps(out, indent=1, default=float))
    print({k: out[k] for k in ("n", "dt_positivo", "frac", "p_signo", "pasa")})


def cubos_salida(_=None):
    """V2: R medio por ejecución (1R / 2R / SALIDA al cierre) a igual entrada y stop, en los cubos de PREAPERTURA y RANGO0100."""
    from edgelab.research import regimen_offline as RO
    EJ = {0: ("MID", "1R"), 1: ("MID", "2R"), 2: ("MID", "SALIDA"), 3: ("OPUESTO", "1R"), 4: ("OPUESTO", "2R"), 5: ("OPUESTO", "SALIDA")}
    res = {}
    for nom in ("PREAPERTURA-NQ-R", "PREAPERTURA-ES-R", "PREAPERTURA-YM-R", "RANGO0100-NQ-R", "RANGO0100-ES-R", "RANGO0100-GC-R"):
        d = json.loads((ROOT / f"data/cubos/{nom}.json").read_text()); c = RO.decodificar(d.get("cubo", d), nom); j = c.idx.shape[1] - 1; res[nom] = {}
        for tr, (a, b) in {"DESC": (20250801, 20260331), "REP": (20260401, 20260930)}.items():
            mm = (c.ses >= a) & (c.ses <= b)
            res[nom][tr] = {f"{EJ[e][0]}|{EJ[e][1]}": dict(n=int(((c.idx[:, j] == e) & mm).sum()), R=float(c.net[(c.idx[:, j] == e) & mm].mean())) for e in EJ}
    gana = {nom: sum(1 for tr in v for st in ("MID", "OPUESTO") if v[tr][f"{st}|SALIDA"]["R"] > max(v[tr][f"{st}|1R"]["R"], v[tr][f"{st}|2R"]["R"])) for nom, v in res.items()}
    (OUT / "T3_V2_CUBOS_SALIDA.json").write_text(json.dumps(dict(cubos=res, salida_gana_de_4=gana), indent=1, default=float)); print(gana)


if __name__ == "__main__":
    globals()[sys.argv[1]](*(sys.argv[2:] or [None]))

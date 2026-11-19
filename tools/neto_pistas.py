#!/usr/bin/env python3
"""NETO-PISTAS: R (AtrPhase) y Z (ZetaTrend) en R con los controles de T, y esquemas de tamaño para Franklin y SOM
(pre-registro docs/research/neto_pistas_20261119/PREREGISTRO.md).

Reusa `fundedsyncstack.correr_modulo`, el kernel de `tools/m1_largo.py` (`cargar`, `_kernel_fs`, `atr20`), la fricción canónica,
`g2.pbo_cscv`, `g2.parameter_sensitivity` y las operaciones versionadas de Franklin y SOM (`docs/research/m1_largo_20261117/`).

  python tools/neto_pistas.py rz_grilla      # R (81) y Z (27) variantes en NQ y ES → data/neto_pistas (reanudable) + RZ_OPS.csv.gz
  python tools/neto_pistas.py rz_prefijo     # prueba de causalidad por prefijo de la fábrica (corte 2015-06-30)
  python tools/neto_pistas.py rz_decidir     # k del stop de catástrofe, meseta, PBO, quiebre → RZ_RESULTADO.json
  python tools/neto_pistas.py tamano         # esquemas S0–S4 en Franklin y SOM → TAMANO_RESULTADO.json + TAMANO_CURVAS.csv.gz
"""
import itertools, json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/neto_pistas_20261119"; PRE = "docs/research/neto_pistas_20261119/PREREGISTRO.md"
PARCIAL = ROOT / "data/neto_pistas"; M1L = ROOT / "docs/research/m1_largo_20261117"
FIN = "2026-09-29"; KS = (0.25, 0.5, 0.75, 1.0)
GRILLAS = {"R": dict(ema_period=[14, 21, 30], umbral=[80.0, 100.0, 120.0], vwap_atr_mult=[2.0, 2.5, 3.0], entry_end_min_et=[630, 660, 720]),
           "Z": dict(bucket_minutes=[10, 15, 30], ema_period=[10, 20, 30], min_efficiency_pct=[35.0, 45.0, 55.0]),
           "A20": dict(st_period=[5, 7, 10], st_mult=[1.5, 2.0, 2.5], absorb_vol_mult=[2.0, 2.5, 3.0], hard_stop_atr_mult=[1.0, 1.5, 2.0])}
FABRICA = {"R": (21, 100.0, 2.5, 660), "Z": (15, 20, 45.0), "A20": (7, 2.0, 2.5, 1.5)}
MODS = ("R", "Z", "A20")


def _cfg(mod, v):
    d = dict(zip(GRILLAS[mod], v))
    if mod == "R": u = d.pop("umbral"); d.update(upper_threshold=u, lower_threshold=-u)
    return d


def _nombre(mod, v):
    return mod + "_" + "_".join(f"{x:g}" for x in v)


def _ops(F, mod, ms, D, cfg):
    from m1_largo import atr20, _sesion
    x = F.correr_modulo(mod, ms, **cfg)
    if not len(x): return pd.DataFrame(columns=["ses", "t", "side", "pnl_pts", "mae_pts", "atr20"])
    tt = pd.to_datetime(x.entry_time_utc, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    pp = pd.to_numeric(x.pnl_pts, errors="coerce"); pu = pd.to_numeric(x.pnl_usd, errors="coerce")
    pv = float((pu / pp).replace([np.inf, -np.inf], np.nan).dropna().median())            # usd por punto de la posición
    ses = _sesion(pd.DatetimeIndex(tt)); a = atr20(D)                                      # ATR20 de las 20 sesiones PREVIAS (shift(1))
    rg = (pd.to_numeric(x.entry_price, errors="coerce") - pd.to_numeric(x.stop_price, errors="coerce")).abs()   # A20: stop duro fijo al entrar
    return pd.DataFrame(dict(ses=ses, t=tt.values, side=x.side.values, pnl_pts=pp.values, riesgo=rg.values,
                             mae_pts=(pd.to_numeric(x.mae_usd, errors="coerce").abs() / pv).values, atr20=a.reindex(ses).to_numpy(float)))


def _ms(inst, hasta=None):
    from datos import ruta
    from m1_largo import cargar, _kernel_fs
    from edgelab.research import fundedsyncstack as F
    D = cargar(inst, ruta("M1NT8")); D = D[D.index >= "2008-01-01"]
    if hasta: D = D[D.index < hasta]
    return F, D, F.build_multi_series(F.load_m1_data(_kernel_fs(0.0)["a_utc"](D), end="2026-10-01"), tz_input="UTC")


def rz_grilla():
    from registro_global import exigir_contada
    exigir_contada(PRE); PARCIAL.mkdir(parents=True, exist_ok=True)
    for inst in ("NQ", "ES"):
        F, D, ms = _ms(inst)
        for mod in MODS:
            for v in itertools.product(*GRILLAS[mod].values()):
                f = PARCIAL / f"{inst}_{_nombre(mod, v)}.csv"
                if f.exists(): continue
                o = _ops(F, mod, ms, D, _cfg(mod, v)); o["inst"], o["modulo"], o["variante"] = inst, mod, _nombre(mod, v)
                o.to_csv(f, index=False); print(inst, _nombre(mod, v), len(o), flush=True)
    G = pd.concat([pd.read_csv(f) for f in sorted(PARCIAL.glob("*.csv"))]); G.to_csv(DIR / "RZ_OPS.csv.gz", index=False)


def rz_prefijo():
    out = {}
    for mod in MODS:
        F, D, ms = _ms("NQ"); full = _ops(F, mod, ms, D, _cfg(mod, FABRICA[mod]))
        F, Dc, msc = _ms("NQ", hasta="2015-07-01"); cut = _ops(F, mod, msc, Dc, _cfg(mod, FABRICA[mod]))
        a = full[pd.to_datetime(full.t) < "2015-06-30"].reset_index(drop=True); b = cut[pd.to_datetime(cut.t) < "2015-06-30"].reset_index(drop=True)
        igual = len(a) == len(b) and bool((a.t.astype(str) == b.t.astype(str)).all() and (a.side == b.side).all() and np.allclose(a.pnl_pts, b.pnl_pts))
        out[mod] = dict(n_completa=int(len(a)), n_cortada=int(len(b)), identicas=igual)
    (DIR / "RZ_PREFIJO.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))


def _supf(r, perm=300, seed=1, meses=None):
    def g(x):
        c = np.cumsum(x); N = len(x); best = (0.0, None)
        for k in range(int(.15 * N), int(.85 * N)):
            m1, m2 = c[k - 1] / k, (c[-1] - c[k - 1]) / (N - k); v = k * (m1 - x.mean()) ** 2 + (N - k) * (m2 - x.mean()) ** 2
            if v > best[0]: best = (v, k)
        return best
    v, k = g(r); bl = [r[meses == m] for m in pd.unique(meses)]; rng = np.random.default_rng(seed)
    nul = [g(np.concatenate([bl[i] for i in rng.permutation(len(bl))]))[0] for _ in range(perm)]
    return k, (1 + sum(x >= v for x in nul)) / (perm + 1)


def _r_neto(G, k, fr):
    if k is None:                                                     # A20: su propio stop duro
        return (G.pnl_pts - fr) / G.riesgo, G.pnl_pts / G.riesgo
    s = k * G.atr20; res = np.where(G.mae_pts >= s, -s, G.pnl_pts)
    return (res - fr) / s, (res) / s


def rz_decidir():
    from edgelab.research import g2
    from edgelab.research.embudo_runners import friccion
    G = pd.read_csv(DIR / "RZ_OPS.csv.gz", parse_dates=["ses", "t"]); G = G[(G.ses <= FIN) & ((G.modulo == "A20") | (np.isfinite(G.atr20) & (G.atr20 > 0)))]
    out = {}
    for mod in MODS:
        ks = (None,) if mod == "A20" else KS
        nombres = [_nombre(mod, v) for v in itertools.product(*GRILLAS[mod].values())]; fab = _nombre(mod, FABRICA[mod])
        porinst = {}
        for inst in ("NQ", "ES"):
            g = G[(G.modulo == mod) & (G.inst == inst)].copy(); fr = float(friccion(inst)[0])
            if mod == "A20": g = g[np.isfinite(g.riesgo) & (g.riesgo > 0)]
            porinst[inst] = {k: g.assign(R=_r_neto(g, k, fr)[0], Rb=_r_neto(g, k, fr)[1]) for k in ks}
        med = {k: float(porinst["NQ"][k].groupby("variante").R.mean().reindex(nombres).median()) for k in ks}
        k_el = max(ks, key=lambda k: med[k] if med[k] == med[k] else -9); W = porinst["NQ"][k_el]
        f_ = W[W.variante == fab].sort_values("t"); kq, pq = _supf(f_.R.to_numpy(), meses=f_.ses.dt.to_period("M").to_numpy())
        quiebre = str(f_.ses.iloc[kq].date())
        rv = W.groupby("variante").R.mean().reindex(nombres); rf = float(rv[fab])
        M = W.assign(mes=W.ses.dt.to_period("M")).pivot_table(index="mes", columns="variante", values="R", aggfunc="sum").reindex(columns=nombres).fillna(0.0)
        pbo = g2.pbo_cscv(M.to_numpy().tolist(), s=16)[0]
        vec = []
        for i, b in enumerate(FABRICA[mod]):
            vals = list(GRILLAS[mod].values())[i]; j = vals.index(b)
            for jj in (j - 1, j + 1):
                if 0 <= jj < len(vals): v = list(FABRICA[mod]); v[i] = vals[jj]; vec.append(_nombre(mod, tuple(v)))
        mv, pv_, nv = g2.parameter_sensitivity(rv.to_dict(), fab, vec)
        frac = float((rv > 0).mean()); mediana = float(rv.median())
        meseta = frac >= 0.70 and mediana >= 0.5 * rf and (mv or 0) > 0
        ver = "SOBREAJUSTE_PROBABLE" if (pbo > 0.5 or frac < 0.5) else ("REGIMEN_ROBUSTO" if (meseta and pbo < 0.3) else "INTERMEDIO")
        anio = f_.groupby(f_.ses.dt.year).R.mean()
        out[mod] = dict(k_elegido=k_el, mediana_grilla_por_k={str(k): v for k, v in med.items()}, R_fabrica=rf, Rb_fabrica=float(W[W.variante == fab].Rb.mean()),
                        frac_variantes_positivas=frac, mediana_grilla=mediana, vecinos=dict(mediana=mv, positivos=pv_, n=nv), pbo=float(pbo),
                        meseta=bool(meseta), veredicto=ver, quiebre_fabrica=quiebre, p_quiebre=pq,
                        R_fabrica_antes=float(f_[f_.ses < quiebre].R.mean()), R_fabrica_despues=float(f_[f_.ses >= quiebre].R.mean()),
                        anios_positivos=f"{int((anio > 0).sum())}/{len(anio)}", R_fabrica_por_anio=anio.round(3).to_dict(),
                        n_fabrica=int(len(f_)), ops_por_mes=float(len(f_) / max(f_.ses.dt.to_period("M").nunique(), 1)),
                        ES_fabrica_por_k={str(k): float(porinst["ES"][k].query("variante == @fab").R.mean()) for k in ks})
    (DIR / "RZ_RESULTADO.json").write_text(json.dumps(out, indent=1, default=str))
    for m, v in out.items(): print(m, {x: v[x] for x in ("k_elegido", "R_fabrica", "Rb_fabrica", "frac_variantes_positivas", "mediana_grilla", "vecinos", "pbo", "veredicto", "quiebre_fabrica", "p_quiebre", "R_fabrica_antes", "R_fabrica_despues", "anios_positivos", "ops_por_mes")})


ESQUEMAS = {"S0": ("riesgo", False), "S1": ("fijo", False), "S2": ("raiz", False), "S3": ("riesgo", True), "S4": ("raiz", True)}


def _peso(r, tipo):
    return {"riesgo": 1.0 / r, "fijo": np.ones(len(r)), "raiz": 1.0 / np.sqrt(r)}[tipo]


def _medir(g, tipo, salta, B=300, seed=3):
    g = g[g.fricR <= 0.08] if salta else g
    w = _peso(g.riesgo.to_numpy(float), tipo); den = (w * g.riesgo).sum()
    net, bru = float((w * g.neto).sum() / den), float((w * g.bruto).sum() / den)
    ses = g.fecha.to_numpy(); u, inv = np.unique(ses, return_inverse=True)
    a = np.bincount(inv, w * g.neto); b = np.bincount(inv, w * g.riesgo); rng = np.random.default_rng(seed)
    bs = [a[i].sum() / b[i].sum() for i in (rng.integers(0, len(u), len(u)) for _ in range(B))]
    return dict(n=int(len(g)), neto=net, bruto=bru, se_neto=float(np.std(bs, ddof=1)))


def tamano():
    from registro_global import exigir_contada
    exigir_contada(PRE)
    def cargar(pref, insts, filt=None):
        x = pd.concat([pd.read_csv(M1L / f"{pref}_OPS_{i}.csv.gz").assign(inst=i) for i in insts])
        x = x[filt(x)] if filt else x; return x[x.riesgo > 0]
    som = lambda d: d.celda == "sin_finde"
    casos = {"FRANKLIN": (cargar("FRANKLIN", ["NQ", "ES"]), cargar("FRANKLIN", ["EMD", "RTY"])),
             "SOM": (cargar("SOM", ["NQ", "ES", "YM"], som), cargar("SOM", ["EMD", "RTY"], som))}
    out, curvas = {}, []
    for fam, (eleg, conf) in casos.items():
        r = {e: dict(eleccion=_medir(eleg, *p), confirmacion=_medir(conf, *p),
                     antes_2020=_medir(eleg[eleg.fecha < 20200101], *p)) for e, p in ESQUEMAS.items()}
        mejor = max([e for e in ESQUEMAS if e != "S0"], key=lambda e: r[e]["eleccion"]["neto"])
        d = r[mejor]["confirmacion"]["neto"] - r["S0"]["confirmacion"]["neto"]; se = np.hypot(r[mejor]["confirmacion"]["se_neto"], r["S0"]["confirmacion"]["se_neto"])
        real = d > 0 and d > se and r[mejor]["antes_2020"]["neto"] >= r["S0"]["antes_2020"]["neto"]
        out[fam] = dict(esquemas=r, mejor=mejor, confirmacion_dif=d, confirmacion_se=se, mejora_real=bool(real))
        for e, (tipo, salta) in ESQUEMAS.items():
            g = (eleg[eleg.fricR <= 0.08] if salta else eleg).sort_values("fecha"); w = _peso(g.riesgo.to_numpy(float), tipo); u = (w * g.riesgo).mean()
            curvas.append(pd.DataFrame(dict(familia=fam, esquema=e, fecha=g.fecha.values, neto=(w * g.neto / u).values, bruto=(w * g.bruto / u).values)))
    (DIR / "TAMANO_RESULTADO.json").write_text(json.dumps(out, indent=1, default=float)); pd.concat(curvas).to_csv(DIR / "TAMANO_CURVAS.csv.gz", index=False)
    for fam, v in out.items():
        print(fam, "mejor", v["mejor"], "mejora_real", v["mejora_real"], "dif conf %.3f se %.3f" % (v["confirmacion_dif"], v["confirmacion_se"]))
        for e, x in v["esquemas"].items(): print("  ", e, {k: {kk: round(vv, 3) for kk, vv in x[k].items() if kk != "n"} for k in x})


def a20_regimen():
    """A20-REGIMEN (docs/research/a20_regimen_20261119/PREREGISTRO.md): procedimiento de T en la ventana desde el quiebre 2017-11-10."""
    from registro_global import exigir_contada
    from edgelab.research import g2
    from edgelab.research.embudo_runners import friccion
    exigir_contada("docs/research/a20_regimen_20261119/PREREGISTRO.md")
    G = pd.read_csv(DIR / "RZ_OPS.csv.gz", parse_dates=["ses", "t"]); G = G[(G.modulo == "A20") & (G.riesgo > 0) & (G.ses <= FIN)]
    nombres = [_nombre("A20", v) for v in itertools.product(*GRILLAS["A20"].values())]; fab = _nombre("A20", FABRICA["A20"])
    def r_inst(inst, a, b):
        g = G[(G.inst == inst) & (G.ses >= a) & (G.ses <= b)].copy(); g["R"] = (g.pnl_pts - float(friccion(inst)[0])) / g.riesgo; return g
    W = r_inst("NQ", "2017-11-10", FIN); rv = W.groupby("variante").R.mean().reindex(nombres)
    M = W.assign(mes=W.ses.dt.to_period("M")).pivot_table(index="mes", columns="variante", values="R", aggfunc="sum").reindex(columns=nombres).fillna(0.0)
    pbo = g2.pbo_cscv(M.to_numpy().tolist(), s=16)[0]
    vec = []
    for i, b in enumerate(FABRICA["A20"]):
        vals = list(GRILLAS["A20"].values())[i]; j = vals.index(b)
        for jj in (j - 1, j + 1):
            if 0 <= jj < len(vals): v = list(FABRICA["A20"]); v[i] = vals[jj]; vec.append(_nombre("A20", tuple(v)))
    mv, pv, nv = g2.parameter_sensitivity(rv.to_dict(), fab, vec)
    frac, med, rf = float((rv > 0).mean()), float(rv.median()), float(rv[fab])
    m1 = float((r_inst("NQ", "2017-11-10", "2021-12-31").groupby("variante").R.mean() > 0).mean())
    m2 = float((r_inst("NQ", "2022-01-01", FIN).groupby("variante").R.mean() > 0).mean())
    es = float(r_inst("ES", "2017-11-10", FIN).query("variante == @fab").R.mean())
    meseta = frac >= 0.70 and med >= 0.5 * rf and (mv or 0) > 0
    ver = "SOBREAJUSTE_PROBABLE" if (pbo > 0.5 or frac < 0.5) else ("REGIMEN_ROBUSTO" if (meseta and pbo < 0.3) else "INTERMEDIO")
    if ver == "REGIMEN_ROBUSTO" and not (m1 >= 0.70 and m2 >= 0.70 and es > 0): ver = "INTERMEDIO"
    out = dict(R_fabrica=rf, frac_positivas=frac, mediana=med, vecinos=dict(mediana=mv, positivos=pv, n=nv), pbo=float(pbo),
               mitad1_frac_positivas=m1, mitad2_frac_positivas=m2, ES_fabrica=es, veredicto=ver, n_fabrica=int((W.variante == fab).sum()))
    (ROOT / "docs/research/a20_regimen_20261119/RESULTADO.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps(out, default=float))


if __name__ == "__main__":
    {"rz_grilla": rz_grilla, "rz_prefijo": rz_prefijo, "rz_decidir": rz_decidir, "tamano": tamano, "a20_regimen": a20_regimen}[sys.argv[1]]()

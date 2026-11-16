#!/usr/bin/env python3
"""Mejora de SOM (docs/research/mejora_estrategias_20261116/CRITERIOS_Y_PLAN.md §5): 14 variantes de una perilla, elección en años pares por
t del R mensual, confirmación en años impares contra la base (bootstrap por mes, BH), acuerdo ES/YM y ventana reciente.

  python tools/mejora_som.py <carpeta M1>   # -> docs/research/mejora_estrategias_20261116/SOM_MEJORAS.json
Reusa quantlab_mt5 (motor y cargador), estrategias_scrapeadas (sesgo Franklin), fundedsync_mecanismos.contexto (noche), m1_intradia.leer_m1.
"""
import json, sys
from dataclasses import replace
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "docs/research/mejora_estrategias_20261116"
FUENTES = {"NQ": ("NQ_M1_dukas", "USATECH"), "ES": ("SP_M1_dukas", "USA500"), "YM": ("DJ_M1_dukas", "USA500")}
NB = 20000

VARIANTES = {                     # nombre: (categoría, cambios de configuración, filtro de contexto)
    "base": ("base", {}, None),
    "rotar": ("frecuencia", dict(rotar=True), None),
    "trail_desde_0": ("salida", dict(trail_start_r=0.0), None),
    "trail_desde_1R": ("salida", dict(trail_start_r=1.0), None),
    "trail_ema60": ("salida", dict(trail_ema=60), None),
    "trail_ema240": ("salida", dict(trail_ema=240), None),
    "stop_6atr": ("stop", dict(sl_atr_mult=6.0), None),
    "stop_10atr": ("stop", dict(sl_atr_mult=10.0), None),
    "ema6": ("senal", dict(fast_ema=6), None),
    "ema24": ("senal", dict(fast_ema=24), None),
    "entrada_1000": ("entrada", dict(open_ny="16:55"), None),
    "franklin_no_en_contra": ("contexto", {}, "franklin"),
    "noche_no_baja": ("contexto", {}, "noche"),
    "sin_gap_grande": ("contexto", {}, "gap"),
    "cierre_diario": ("riesgo", dict(close_eod=True), None),
}


def contextos(carpeta, arch):
    """Por fecha NY: sesgo Franklin al cierre de la vela 09:34 (entrada 09:35), tercil de noche y |gap| / ATR20 (todo causal)."""
    import reels_20261116 as RR, fundedsync_mecanismos as FM
    from edgelab.research import estrategias_scrapeadas as X, m1_intradia as M
    ctx = RR.ctx_de_csv(Path(carpeta) / f"{arch}.csv"); vw, lh, ll = X._sesgo_franklin(ctx); m, f, _ = X._hora(ctx, "America/New_York"); c = ctx["c"]
    k = m == 574; s = np.where((c > lh) & (c > vw), 1, np.where((c < ll) & (c < vw), -1, 0))
    sesgo = dict(zip(f[k].tolist(), s[k].tolist()))
    V = FM.contexto(Path(carpeta) / f"{arch}.csv"); noche = {int(d.strftime("%Y%m%d")): v for d, v in V.noche.items()}
    D = M.leer_m1(Path(carpeta) / f"{arch}.csv"); mm = D.index.hour * 60 + D.index.minute; R = D[(mm >= 570) & (mm < 960)]; d = R.index.normalize()
    day = pd.DataFrame(dict(o=R.o.groupby(d).first(), h=R.h.groupby(d).max(), l=R.l.groupby(d).min(), c=R.c.groupby(d).last()))
    gap = ((day.o - day.c.shift(1)).abs() / (day.h - day.l).rolling(20).mean().shift(1))
    return sesgo, noche, {int(k_.strftime("%Y%m%d")): v for k_, v in gap.items()}


def _permitir(tipo, ctxs):
    if tipo is None: return None
    sesgo, noche, gap = ctxs
    fecha = lambda ts: int((pd.Timestamp(ts, unit="ns") - pd.Timedelta(hours=7)).strftime("%Y%m%d"))        # hora del servidor → fecha NY
    if tipo == "franklin": return lambda ts, s: sesgo.get(fecha(ts), 0) != -s
    if tipo == "noche": return lambda ts, s: noche.get(fecha(ts)) in ("medio", "alto")
    if tipo == "gap": return lambda ts, s: (lambda g: g is not None and np.isfinite(g) and g < 0.5)(gap.get(fecha(ts)))
    raise ValueError(tipo)


def correr(df, spec, fr, nombre, ctxs, extra=None):
    from edgelab.research.quantlab_mt5 import correr_session_open_momentum
    from edgelab.research.quantlab_mt5.contracts import SessionOpenMomentumConfig
    partes = [VARIANTES[n] for n in ([nombre] if extra is None else [nombre, extra])]
    cambios = {"close_weekend": True}; filtros = []
    for _, cf, fl in partes: cambios.update(cf); filtros += [fl] if fl else []
    ps = [_permitir(t, ctxs) for t in filtros]
    perm = (lambda ts, s: all(p(ts, s) for p in ps)) if ps else None
    T = correr_session_open_momentum(df, config=replace(SessionOpenMomentumConfig(), **cambios), instrument=spec, permitir=perm)
    t = pd.to_datetime(T.entry_time_utc, unit="ns") - pd.Timedelta(hours=7)
    g = pd.DataFrame(dict(fecha=t.dt.strftime("%Y%m%d").astype(int).values, mes=t.dt.to_period("M").astype(str).values, anio=t.dt.year.values,
                          riesgo=(T.entry_price - T.stop_price).abs().values, bruto=T.pnl_pts.values.astype(float)))
    g = g[g.riesgo > 0]; g["R"] = (g.bruto - fr) / g.riesgo; g["fricR"] = fr / g.riesgo; return g


def _mensual(g, meses):
    return g.groupby("mes").R.sum().reindex(meses, fill_value=0.0)


def metricas(g, meses):
    x = _mensual(g, meses); yr = g.groupby("anio").R.sum(); ac = x.cumsum()
    return dict(n=int(len(g)), R_op=float(g.R.mean()) if len(g) else None, R_mes=float(x.mean()), t_mes=float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))) if x.std(ddof=1) > 0 else 0.0,
                ops_mes=float(len(g) / len(meses)), anios_pos=int((yr > 0).sum()), anios=int(len(yr)), peor_anio=float(yr.min()) if len(yr) else None,
                dd_R=float((ac - ac.cummax()).min()), fric_med=float(g.fricR.median()) if len(g) else None)


def _p_dif(a, b, seed=7):
    d = (a - b).to_numpy(); i = np.random.default_rng(seed).integers(0, len(d), (NB, len(d))); m = d[i].mean(1)
    return float(d.mean()), float((1 + (m <= 0).sum()) / (NB + 1))


def main(carpeta):
    from edgelab.research.quantlab_mt5 import load_ohlc_data
    from edgelab.research.embudo_runners import friccion
    from fundedsync_tanda2 import _bh
    res = dict(plan="docs/research/mejora_estrategias_20261116/CRITERIOS_Y_PLAN.md", variantes={})
    arch, spec = FUENTES["NQ"]; df = load_ohlc_data(Path(carpeta) / f"{arch}.csv", start="2012-01-20"); fr = friccion("NQ")[0]; ctxs = contextos(carpeta, arch)
    G = {n: correr(df, spec, fr, n, ctxs) for n in VARIANTES}
    todos = sorted(set().union(*[set(g.mes) for g in G.values()]))
    par = [m for m in todos if int(m[:4]) % 2 == 0]; impar = [m for m in todos if int(m[:4]) % 2 == 1]; rec = [m for m in todos if "2025-08" <= m <= "2026-09"]
    for n, g in G.items():
        res["variantes"][n] = dict(categoria=VARIANTES[n][0], E=metricas(g[g.anio % 2 == 0], par), C=metricas(g[g.anio % 2 == 1], impar),
                                   reciente=metricas(g[g.mes.isin(rec)], rec), total=metricas(g, todos))
        e = res["variantes"][n]["E"]; print(n, "E t_mes", round(e["t_mes"], 2), "R_mes", round(e["R_mes"], 3), "ops/mes", round(e["ops_mes"], 1), "años+", e["anios_pos"], "fric", round(e["fric_med"], 3), flush=True)
    b = res["variantes"]["base"]["E"]
    eleg = [n for n, v in res["variantes"].items() if n not in ("base", "cierre_diario") and v["E"]["fric_med"] <= 0.08 and v["E"]["anios_pos"] >= b["anios_pos"]]
    top = sorted(eleg, key=lambda n: -res["variantes"][n]["E"]["t_mes"])[:3]
    fin = [(n, None) for n in top]
    if len(top) >= 2 and VARIANTES[top[0]][0] != VARIANTES[top[1]][0]:
        fin.append((top[0], top[1])); g = correr(df, spec, fr, top[0], ctxs, top[1]); G[f"{top[0]}+{top[1]}"] = g
        res["variantes"][f"{top[0]}+{top[1]}"] = dict(categoria="combinacion", E=metricas(g[g.anio % 2 == 0], par), C=metricas(g[g.anio % 2 == 1], impar),
                                                       reciente=metricas(g[g.mes.isin(rec)], rec), total=metricas(g, todos))
    nombres = [a if b_ is None else f"{a}+{b_}" for a, b_ in fin]
    base_C = _mensual(G["base"][G["base"].anio % 2 == 1], impar); conf = {}
    for n in nombres:
        dif, p = _p_dif(_mensual(G[n][G[n].anio % 2 == 1], impar), base_C); conf[n] = dict(dif_R_mes=dif, p=p, R_mes_C=res["variantes"][n]["C"]["R_mes"])
    bh = _bh([conf[n]["p"] for n in nombres]) if nombres else []
    for n, bb in zip(nombres, bh): conf[n].update(bh=bool(bb), confirma=bool(bb and conf[n]["dif_R_mes"] > 0 and conf[n]["R_mes_C"] > 0))
    gan = max((n for n in nombres if conf[n]["confirma"]), key=lambda n: res["variantes"][n]["E"]["t_mes"], default=None)
    res.update(elegibles=eleg, finalistas=nombres, confirmacion=conf, ganadora=gan)
    acuerdo = {}                                                                    # ES / YM: base y finalistas (descriptivo)
    for inst in ("ES", "YM"):
        a2, s2 = FUENTES[inst]; d2 = load_ohlc_data(Path(carpeta) / f"{a2}.csv", start="2012-01-20"); f2 = friccion(inst)[0]; c2 = contextos(carpeta, a2)
        acuerdo[inst] = {}
        for n in ["base"] + nombres:
            p_ = n.split("+"); g = correr(d2, s2, f2, p_[0], c2, p_[1] if len(p_) > 1 else None); ms = sorted(set(g.mes))
            acuerdo[inst][n] = metricas(g, ms)
    res["acuerdo_ES_YM"] = acuerdo
    if gan:
        G[gan].to_csv(OUT / "SOM_GANADORA_OPS.csv.gz", index=False)
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "SOM_MEJORAS.json").write_text(json.dumps(res, indent=1, default=float))
    print("finalistas", nombres); print(json.dumps(conf, indent=1)); print("ganadora", gan)
    print({i: {n: (round(v["R_mes"], 3), round(v["t_mes"], 2)) for n, v in a.items()} for i, a in acuerdo.items()})


if __name__ == "__main__":
    main(sys.argv[1])

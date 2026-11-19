#!/usr/bin/env python3
"""Tanda 4 (pre-registro docs/research/cartera_20261116/PREREGISTRO_TANDA4.md).

  python tools/cartera_tanda4.py c1                 # re-elegibilidad con el filtro de fricción -> cartera_20261116/v3/SELECCION.json
  python tools/cartera_tanda4.py c2c5 <carpeta M1>  # cartera (v2/v3) + T+Z+R y freno diario: correlación, t, DD y prop 50K -> TANDA4_C2C5.json
  python tools/cartera_tanda4.py c4 <carpeta M1>    # noche movida como contexto para PREAPERTURA-NQ/ES, T y Z -> TANDA4_C4.json
Reusa cartera_nov_analisis (selección), mejoras_cartera (v2: A1, A2, M1, M3), fundedsync_tanda2 (stop de catástrofe), estimar_propfirm.sim.
"""
import importlib.util, json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import cartera_nov_analisis as A  # noqa: E402
from cartera_nov import DIR, universo  # noqa: E402

FRENO_USD, USD_R = 500.0, 200.0
DEV = ("2025-08-05", "2026-09-29")


def c1():
    """Selección §5 con M1 aplicado antes a todas las reglas (operaciones con fricción/riesgo > 0,08 fuera)."""
    from edgelab.research.embudo_runners import friccion
    U = {r["cid"]: r["spec"] for r in universo()}; orig = A._ops
    def _ops_m1(cid, tramo):
        o = orig(cid, tramo)
        if o is None: return None
        fr = friccion(U[cid].get("ejecucion") or U[cid]["sensor"])[0]; k = (fr / o["riesgo"]) <= 0.08
        return {a: b[k] for a, b in o.items()}
    A._ops = _ops_m1; A.DIR = DIR / "v3"; A.DIR.mkdir(exist_ok=True)
    try: A.seleccion()
    finally: A._ops = orig; A.DIR = DIR


def _ep():
    spec = importlib.util.spec_from_file_location("ep", ROOT / "docs/research/canasta_7_20261030/estimar_propfirm.py"); ep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ep); return ep


def ops_cartera(S):
    """Operaciones en USD de la cartera con la v2 (A1, A2, M1, M3), con su hora de entrada (para el freno)."""
    from edgelab import costos as C
    from mejoras_cartera import marcar, PESO, MICRO
    from perdidas_concentradas import clasificar
    U = {r["cid"]: r for r in universo()}; filas = []
    for c in S:
        sp = U[c]["spec"]; ej = sp.get("ejecucion") or sp["sensor"]; m = MICRO[ej]; usd_pt = C.tick_value_usd(m) / C.tick_size(m)
        dfr = C.friccion_rt_puntos(m, criterio="max") - C.friccion_rt_puntos(m, criterio="min")
        todas = marcar(clasificar(c, sp)); rmed = np.median([x["riesgo"] for x in todas if x["tramo"] != "hold"])
        n = max(1, round(USD_R * PESO.get(c, 1.0) / (rmed * usd_pt)))
        for x in todas:
            if x["tramo"] == "hold" or x["m1"]: continue
            filas.append(dict(ses=x["ses"], t=x["t"], usd=(x["R"] + dfr / x["riesgo"]) * x["riesgo"] * usd_pt * n, regla=c))
    return pd.DataFrame(filas)


def ops_tzr(carpeta, minimo=False, modulos=("T", "Z", "R")):
    """T, Z, R de fábrica en MNQ (micros fijos ≈ 200 USD de riesgo mediano; Z y R con stop de catástrofe 0,5 × ATR20 vía MAE)."""
    from edgelab.research import fundedsyncstack as F
    import fundedsync_tanda2 as T2
    D = T2.leer(carpeta, "NQ_M1_dukas"); day = T2.diario(D); ms = F.build_multi_series(F.load_m1_data(T2.a_utc(D), end="2026-10-01"), tz_input="UTC"); filas = []
    for k in modulos:
        x = F.correr_modulo(k, ms); o = T2._ops(x, 1.5455)
        o["t"] = ((pd.to_datetime(x.entry_time_utc, utc=True) - pd.Timestamp(0, tz="UTC")) // pd.Timedelta("1s")).values
        ppu = (pd.to_numeric(x.pnl_pts, errors="coerce") / pd.to_numeric(x.pnl_usd, errors="coerce")).replace([np.inf, -np.inf], np.nan).median()
        o["mae_pts"] = o.mae * ppu; o["stop"] = 0.5 * day.atr20.reindex(o.dia).values
        if k == "T":
            riesgo = (pd.to_numeric(x.entry_price, errors="coerce") - pd.to_numeric(x.stop_price, errors="coerce")).abs().values; rmed = np.nanmedian(riesgo[riesgo >= 4])
        else:
            o["neto"] = np.where(o.mae_pts >= o.stop, -o.stop - 1.5455, o.neto); rmed = np.nanmedian(o.stop)
        n = 1 if minimo else max(1, round(USD_R / (rmed * 2.0)))
        o = o[(o.dia >= DEV[0]) & (o.dia <= DEV[1])]
        filas += [dict(ses=int(d.strftime("%Y%m%d")), t=t, usd=v * 2.0 * n, regla=k) for d, t, v in zip(o.dia, o.t, o.neto)]
    return pd.DataFrame(filas)


def _diario(df, freno):
    out = {}
    for s, g in df.sort_values("t").groupby("ses"):
        ac = 0.0
        for u in g.usd:
            if freno and ac <= -FRENO_USD: break
            ac += u
        out[int(s)] = ac
    return out


def c2c5(carpeta):
    ep = _ep(); sesiones = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(*DEV)]
    v2 = json.loads((DIR / "SELECCION.json").read_text())["futuros"]
    v3f = DIR / "v3/SELECCION.json"; v3 = json.loads(v3f.read_text())["futuros"] if v3f.exists() else v2
    contr = json.loads((DIR / "PROP.json").read_text())["factor_contraccion"]
    tzr = ops_tzr(carpeta); base = {"v2": ops_cartera(v2), "v3": ops_cartera(v3)}
    res = dict(v2=v2, v3=v3, versiones={})
    serie = lambda df, fr: np.array([_diario(df, fr).get(s, 0.0) for s in sesiones])
    x_tzr = serie(tzr, False); x_v2 = serie(base["v2"], False)
    res["correlacion_v2_tzr"] = float(np.corrcoef(x_v2, x_tzr)[0, 1])
    for nom, df in (("v2", base["v2"]), ("v2+TZR", pd.concat([base["v2"], tzr])), ("v3", base["v3"]), ("v3+TZR", pd.concat([base["v3"], tzr])), ("TZR", tzr)):
        for fr in (False, True):
            x = serie(df, fr); r = dict(res_dev=ep.res(x))
            for k, mu in (("media_dev", x.mean()), ("media_contraida", x.mean() * contr), ("azar_0", 0.0)):
                p, q = ep.sim(x, ep.CUENTAS["50K"], mu=mu); r[k] = dict(pasa=float(p), quema=float(q))
            res["versiones"][nom + (" +freno" if fr else "")] = r
            print(nom + (" +freno" if fr else ""), r["res_dev"], {k: r[k] for k in ("media_contraida", "azar_0")}, flush=True)
    (DIR / "TANDA4_C2C5.json").write_text(json.dumps(res, indent=1, default=float))


def c4(carpeta):
    import fundedsync_mecanismos as FM
    VN = FM.contexto(Path(carpeta) / "NQ_M1_dukas.csv"); VE = FM.contexto(Path(carpeta) / "SP_M1_dukas.csv"); res = {}
    fs = pd.read_csv(ROOT / "docs/research/fundedsyncstack_20261115/cadena/FUNDEDSYNC_OPS.csv.gz", parse_dates=["dia"])
    casos = {}
    for k in ("T", "Z"):
        g = fs[fs.modulo == k]; casos[k] = (g.dia, g.neto.values, VN, ("2020-01-01", "2023-12-31"), ("2024-01-01", "2026-09-29"))
    for c, V in (("PREAPERTURA-NQ", VN), ("PREAPERTURA-ES", VE)):
        oo = [A._ops(c, t) for t in ("desc", "rep")]
        dia = pd.to_datetime(pd.Series(np.r_[oo[0]["ses"], oo[1]["ses"]]).astype(str)); casos[c] = (dia, np.r_[oo[0]["R"], oo[1]["R"]], V, ("2025-08-01", "2026-03-31"), ("2026-04-01", "2026-09-30"))
    for k, (dia, y, V, a, b) in casos.items():
        n = V.noche.reindex(dia.values).values; dfx = pd.DataFrame(dict(dia=dia.values, y=y, alta=n == "alto")).dropna()
        r = {}
        for nom, (x0, x1) in (("A", a), ("B", b)):
            g = dfx[(dfx.dia >= x0) & (dfx.dia <= x1)]; c1_, c0 = g[g.alta], g[~g.alta]
            s = FM._boot(c1_.y.values, c1_.dia.values, c0.y.values, c0.dia.values, 5) if len(c1_) >= 5 and len(c0) >= 5 else {}
            r[nom] = dict(n_alta=int(len(c1_)), media_alta=float(c1_.y.mean()) if len(c1_) else None, n_resto=int(len(c0)), media_resto=float(c0.y.mean()) if len(c0) else None, **s)
        res[k] = r; print(k, {n: (v["n_alta"], v["media_alta"] and round(v["media_alta"], 3), v["media_resto"] and round(v["media_resto"], 3), v.get("p_dif") and round(v["p_dif"], 3)) for n, v in r.items()}, flush=True)
    ks = [k for k in res if "p_dif" in res[k]["B"]]; bh = FM._bh([res[k]["B"]["p_dif"] for k in ks])
    for k, b in zip(ks, bh): res[k]["pasa"] = bool(b and res[k]["A"].get("dif", 0) > 0 and res[k]["B"]["dif"] > 0)
    (DIR / "TANDA4_C4.json").write_text(json.dumps(res, indent=1, default=float)); print({k: res[k].get("pasa") for k in res})


def t5a(carpeta):
    """PREREGISTRO_TANDA5 T5a: v2/v3 + T+Z+R a 1 MNQ por regla (y v2 + T sola a 1 MNQ) en la prop 50K."""
    ep = _ep(); sesiones = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(*DEV)]
    v2 = json.loads((DIR / "SELECCION.json").read_text())["futuros"]; v3 = json.loads((DIR / "v3/SELECCION.json").read_text())["futuros"]
    contr = json.loads((DIR / "PROP.json").read_text())["factor_contraccion"]
    tzr = ops_tzr(carpeta, minimo=True); b2, b3 = ops_cartera(v2), ops_cartera(v3); res = dict(versiones={})
    serie = lambda df: np.array([_diario(df, False).get(s, 0.0) for s in sesiones])
    for nom, df in (("v2", b2), ("v3", b3), ("v2+TZRmin", pd.concat([b2, tzr])), ("v3+TZRmin", pd.concat([b3, tzr])),
                    ("v2+Tmin", pd.concat([b2, tzr[tzr.regla == "T"]])), ("v3+Tmin", pd.concat([b3, tzr[tzr.regla == "T"]])), ("TZRmin", tzr)):
        x = serie(df); r = dict(res_dev=ep.res(x))
        for k, mu in (("media_dev", x.mean()), ("media_contraida", x.mean() * contr), ("azar_0", 0.0)):
            p, q = ep.sim(x, ep.CUENTAS["50K"], mu=mu); r[k] = dict(pasa=float(p), quema=float(q))
        res["versiones"][nom] = r; print(nom, r["res_dev"], {k: r[k] for k in ("media_contraida", "azar_0")}, flush=True)
    for nom in ("v2+TZRmin", "v3+TZRmin", "v2+Tmin", "v3+Tmin"):
        r = res["versiones"][nom]; solo = res["versiones"][nom.split("+")[0]]
        r["entra_forward"] = bool(r["media_contraida"]["quema"] <= 0.10 and r["media_contraida"]["pasa"] >= solo["media_contraida"]["pasa"])
    (DIR / "TANDA5_T5A.json").write_text(json.dumps(res, indent=1, default=float)); print({k: v.get("entra_forward") for k, v in res["versiones"].items()})


def operativa_v3():
    """CARTERA_V3_OPERATIVA.json con el formato de la v2 (A1, A2, M1, M3) para el forward."""
    from edgelab import costos as C
    from mejoras_cartera import marcar, PESO, MICRO, UMBRAL_FRICCION
    from perdidas_concentradas import clasificar
    v2 = json.loads((DIR / "CARTERA_V2_OPERATIVA.json").read_text(encoding="utf-8")); U = {r["cid"]: r for r in universo()}; reglas = []
    for c in json.loads((DIR / "v3/SELECCION.json").read_text())["futuros"]:
        sp = U[c]["spec"]; ej = sp.get("ejecucion") or sp["sensor"]; m = MICRO[ej]; usd_pt = C.tick_value_usd(m) / C.tick_size(m)
        todas = marcar(clasificar(c, sp)); dev = [x for x in todas if x["tramo"] != "hold"]; rmed = float(np.median([x["riesgo"] for x in dev]))
        n = max(1, round(USD_R * PESO.get(c, 1.0) / (rmed * usd_pt))); fr = C.friccion_rt_puntos(ej, criterio="max")
        reglas.append(dict(regla=c, senal=sp["sensor"], ejecuta=m, micros=n, riesgo_mediano_pts=rmed, usd_riesgo_mediano=round(rmed * usd_pt * n),
                           peso=PESO.get(c, 1.0), no_operar_si_stop_menor_a_pts=round(fr / UMBRAL_FRICCION, 2), friccion_canonica_pts=round(fr, 3),
                           friccion_micro_min_pts=round(C.friccion_rt_puntos(m, criterio="min"), 3), pct_ops_salteadas_dev=round(float(np.mean([x["m1"] for x in dev])), 2)))
    out = dict(v2, version="v3", base="v3/SELECCION.json (selección §5 con M1 antes de elegir; PREREGISTRO_TANDA4 C1)", reglas=reglas)
    (DIR / "CARTERA_V3_OPERATIVA.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8"); print(json.dumps(reglas, indent=1))


if __name__ == "__main__":
    {"t5a": lambda: t5a(sys.argv[2]), "operativa_v3": lambda: operativa_v3(), "c1": lambda: c1(), "c2c5": lambda: c2c5(sys.argv[2]), "c4": lambda: c4(sys.argv[2])}[sys.argv[1]]()

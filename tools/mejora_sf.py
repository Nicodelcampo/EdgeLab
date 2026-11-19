#!/usr/bin/env python3
"""MEJORA-SF: filtros causales con mecanismo para SOM y Franklin, DESC → REP con K49 (pre-registro docs/research/mejora_sf_20261119/PREREGISTRO.md).

Reusa `quantlab_mt5_medir.ops_som`, las operaciones versionadas de Franklin (`docs/research/m1_largo_20261117/FRANKLIN_OPS_*`),
`m1_largo.cargar`/`_sesion`/`atr20`, `holdout.a5_bloque`, `a5.diferencia`, `a5.bh`, `holdout_ventanas.plan_potencia`, `libro_lord` y el VIX
de `cboe_volatility_daily.parquet`.

  python tools/mejora_sf.py tabla     # operaciones con lado y estados causales (sin desenlaces nuevos) → TABLA.csv.gz
  python tools/mejora_sf.py desc      # 9 contrastes en DESC, BH q 0,10 → DESC.json (commitear antes de rep)
  python tools/mejora_sf.py rep       # nominadas con potencia en días ≥ 0,8, una vez con LORD++ → REP.json
  python tools/mejora_sf.py conf      # Franklin M3/M6 en YM+EMD+RTY (PREREGISTRO_CONF.md): potencia primero, después la prueba → CONF.json
"""
import json, sys
from dataclasses import replace
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/mejora_sf_20261119"; PRE = "docs/research/mejora_sf_20261119/PREREGISTRO.md"
M1L = ROOT / "docs/research/m1_largo_20261117"; FIN = 20250731
PRUEBAS = [("SOM", m) for m in ("M2", "M3", "M6", "M8")] + [("FRANKLIN", m) for m in ("M1", "M2", "M3", "M6", "M8")]
FAM = {"SOM": "SOM", "FRANKLIN": "FRANKLIN"}


def _estados(inst, D):
    from m1_largo import _sesion, atr20
    ses = _sesion(D.index); c = D.c.groupby(ses).last(); a = atr20(D)                     # atr20 ya es de las 20 sesiones previas
    pct = a.rolling(250, min_periods=120).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
    tend = np.sign(c.shift(1) - c.shift(61))
    return pd.DataFrame(dict(atr_pct=pct, tend=tend))


def tabla():
    from registro_global import exigir_contada
    from datos import ruta
    from m1_largo import cargar
    from edgelab.research.quantlab_mt5.contracts import SessionOpenMomentumConfig
    from edgelab.research.m1_intradia import SERVIDOR_MENOS_NY
    from edgelab.research.embudo_runners import friccion
    from edgelab.holdout import a5_bloque
    from quantlab_mt5_medir import ops_som, FUENTES
    exigir_contada(PRE)
    V = pd.read_parquet(Path(ruta("M1NT8")) / "cboe_volatility_daily.parquet"); V.index = pd.to_datetime(V.index).normalize()
    partes = []
    for inst in ("NQ", "ES", "YM"):
        D = cargar(inst, ruta("M1NT8")); E = _estados(inst, D)
        srv = (D.index + pd.Timedelta(hours=SERVIDOR_MENOS_NY)).tz_localize("UTC")
        df = pd.DataFrame(dict(time=srv, ts_ns=srv.asi8, open=D.o.to_numpy(), high=D.h.to_numpy(), low=D.l.to_numpy(), close=D.c.to_numpy(), volume=D.v.to_numpy()))
        s = ops_som(df, replace(SessionOpenMomentumConfig(), close_weekend=True), FUENTES.get(inst, (None, "USA500"))[1], friccion(inst)[0]).assign(estrategia="SOM")
        s["lado"] = [1 if (str(x).lower() in ("1", "long", "buy") or x == 1) else -1 for x in s.lado]
        lst = [s]
        if inst in ("NQ", "ES"):
            f = pd.read_csv(M1L / f"FRANKLIN_OPS_{inst}.csv.gz").assign(estrategia="FRANKLIN"); lst.append(f[["fecha", "lado", "riesgo", "bruto", "neto", "R", "Rb", "fricR", "estrategia"]])
        for g in lst:
            g = g[g.riesgo > 0].copy(); g["inst"] = inst; d = pd.to_datetime(g.fecha.astype(str))
            g["atr_pct"] = E.atr_pct.reindex(d).to_numpy(); g["tend"] = E.tend.reindex(d).to_numpy()
            g["vix_ivp"] = V.vix_ivp_252_prev_close.reindex(d).to_numpy()
            partes.append(g[["fecha", "inst", "estrategia", "lado", "riesgo", "bruto", "neto", "R", "Rb", "fricR", "atr_pct", "tend", "vix_ivp"]])
        print(inst, flush=True)
    T = pd.concat(partes, ignore_index=True)
    som = T[T.estrategia == "SOM"][["fecha", "inst", "lado"]].drop_duplicates(["fecha", "inst"], keep="first").rename(columns={"lado": "lado_som"})
    T = T.merge(som, on=["fecha", "inst"], how="left")
    T["bloque"] = [a5_bloque(int(x)) for x in T.fecha]
    T = T[(T.fecha <= FIN) & T.bloque.isin(["DESC", "REP"])]           # holdout y embargo de A5: ni se guardan
    T.to_csv(DIR / "TABLA.csv.gz", index=False); print(T.groupby(["estrategia", "bloque"]).size().to_dict())


def _dentro(T, m):
    if m == "M1": return (T.lado_som == T.lado)
    if m == "M2": return T.fricR <= 0.08
    if m == "M3": return T.atr_pct >= 2 / 3
    if m == "M6": return T.vix_ivp >= 200 / 3                            # percentil 0–100 en el parquet
    if m == "M8": return (T.tend * T.lado) > 0


def _contraste(T, est, m, bloque):
    from edgelab.research import a5 as A5
    g = T[(T.estrategia == est) & (T.bloque == bloque)]
    if m in ("M3", "M6", "M8"): g = g[g[{"M3": "atr_pct", "M6": "vix_ivp", "M8": "tend"}[m]].notna()]
    a = _dentro(g, m).fillna(False).to_numpy(bool)
    d, se, p = A5.diferencia(g.fecha.to_numpy()[a], g.R.to_numpy()[a], g.fecha.to_numpy()[~a], g.R.to_numpy()[~a])
    return dict(dif=d, se=se, p=p, n_dentro=int(a.sum()), n_fuera=int((~a).sum()), R_dentro=float(g.R[a].mean()), R_fuera=float(g.R[~a].mean()),
                R_base=float(g.R.mean()), frac_dentro=float(a.mean())), g, a


def desc():
    from edgelab.research.a5 import bh
    T = pd.read_csv(DIR / "TABLA.csv.gz"); res = {}
    for est, m in PRUEBAS: res[f"{est}|{m}"] = _contraste(T, est, m, "DESC")[0]
    k = list(res); rech = bh([res[x]["p"] for x in k], 0.10)
    for x, r in zip(k, rech): res[x]["bh"] = bool(r)
    out = dict(preregistro=PRE, resultados=res, nominadas=[x for x in k if res[x]["bh"] and res[x]["dif"] > 0])
    (DIR / "DESC.json").write_text(json.dumps(out, indent=1, default=float))
    for x in k: print(x, {y: round(res[x][y], 3) if isinstance(res[x][y], float) else res[x][y] for y in ("dif", "p", "R_dentro", "R_fuera", "R_base", "frac_dentro", "bh")})
    print("nominadas", out["nominadas"])


def rep():
    from a5_campana import _commiteado
    from edgelab.research import holdout_ventanas as HV
    from edgelab.funnel.libro_lord import LibroLord
    if not _commiteado(DIR / "DESC.json"): raise SystemExit("DESC.json sin commitear")
    T = pd.read_csv(DIR / "TABLA.csv.gz"); nom = json.loads((DIR / "DESC.json").read_text())["nominadas"]; out = {}
    for x in nom:
        est, m = x.split("|"); fam = FAM[est]
        r, g, a = _contraste(T, est, m, "DESC")
        dd = pd.DataFrame(dict(f=g.fecha.to_numpy(), R=g.R.to_numpy(), a=a))
        ins, fue = dd[dd.a].groupby("f").R.mean(), dd[~dd.a].groupby("f").R.mean(); q = len(ins) / (len(ins) + len(fue))
        sd = float(np.sqrt(ins.var(ddof=1) / q + fue.var(ddof=1) / (1 - q)))
        n_rep = int(T[(T.estrategia == est) & (T.bloque == "REP")].fecha.nunique())      # sólo cuenta sesiones, no lee desenlaces
        plan = HV.plan_potencia("fijo", 0.5 * r["dif"], sd, n=n_rep, alfa=LibroLord().nivel(fam), fuente_efecto="mitad del contraste de DESC (K49)")
        out[x] = dict(plan=plan, sd_dia=sd, n_dias_rep=n_rep)
    con = [x for x in nom if (out[x]["plan"].get("potencia") or 0) >= 0.8]
    for x in con:
        est, m = x.split("|"); r = _contraste(T, est, m, "REP")[0]
        dec = LibroLord().probar(FAM[est], f"REP_MEJORA_SF_{est}_{m}", [(x, r["p"])])
        out[x].update(rep=r, lord=dec, confirmada=bool(dec.get("rechazo") if isinstance(dec, dict) else False) and r["R_dentro"] > 0)
    for x in nom:
        if x not in con: out[x]["estado"] = "SIN_POTENCIA_PREVIA"
    (DIR / "REP.json").write_text(json.dumps(out, indent=1, default=float))
    for x, v in out.items(): print(x, v.get("estado", ""), "potencia", round(v["plan"].get("potencia") or 0, 3), v.get("rep", {}).get("dif"), v.get("confirmada"))


def _plan(T, est, m, n_dias, fam):
    from edgelab.research import holdout_ventanas as HV
    from edgelab.funnel.libro_lord import LibroLord
    r, g, a = _contraste(T, est, m, "DESC")
    dd = pd.DataFrame(dict(f=g.fecha.to_numpy(), R=g.R.to_numpy(), a=a))
    ins, fue = dd[dd.a].groupby("f").R.mean(), dd[~dd.a].groupby("f").R.mean(); q = len(ins) / (len(ins) + len(fue))
    sd = float(np.sqrt(ins.var(ddof=1) / q + fue.var(ddof=1) / (1 - q)))
    return HV.plan_potencia("fijo", 0.5 * r["dif"], sd, n=n_dias, alfa=LibroLord().nivel(fam), fuente_efecto="mitad del contraste de DESC (K49)")


def conf():
    from registro_global import exigir_contada
    from datos import ruta
    from m1_largo import cargar
    from edgelab.holdout import a5_bloque
    from edgelab.funnel.libro_lord import LibroLord
    exigir_contada("docs/research/mejora_sf_20261119/PREREGISTRO_CONF.md")
    V = pd.read_parquet(Path(ruta("M1NT8")) / "cboe_volatility_daily.parquet"); V.index = pd.to_datetime(V.index).normalize()
    partes = []
    for inst in ("YM", "EMD", "RTY"):
        D = cargar(inst, ruta("M1NT8")); E = _estados(inst, D)
        g = pd.read_csv(M1L / f"FRANKLIN_OPS_{inst}.csv.gz"); g = g[g.riesgo > 0].copy(); d = pd.to_datetime(g.fecha.astype(str))
        g["atr_pct"] = E.atr_pct.reindex(d).to_numpy(); g["vix_ivp"] = V.vix_ivp_252_prev_close.reindex(d).to_numpy()
        g["inst"], g["estrategia"] = inst, "FRANKLIN"; partes.append(g[["fecha", "inst", "estrategia", "lado", "R", "fricR", "atr_pct", "vix_ivp"]])
    C = pd.concat(partes, ignore_index=True); C["bloque"] = [a5_bloque(int(x)) for x in C.fecha]
    C = C[(C.fecha <= FIN) & C.bloque.isin(["DESC", "REP"])].copy(); C["bloque_orig"] = C.bloque; C["bloque"] = "CONF"
    T = pd.read_csv(DIR / "TABLA.csv.gz")
    n_dias = int(C.fecha.nunique())                                            # sólo cuenta sesiones: no lee desenlaces
    planes = {m: _plan(T, "FRANKLIN", m, n_dias, "FRANKLIN") for m in ("M3", "M6")}
    out = dict(preregistro="docs/research/mejora_sf_20261119/PREREGISTRO_CONF.md", n_dias=n_dias, planes=planes)
    con = [m for m in planes if (planes[m].get("potencia") or 0) >= 0.8]
    for m in planes:
        if m not in con: out[f"FRANKLIN|{m}"] = dict(estado="SIN_POTENCIA_PREVIA")
    if con:
        res = {m: _contraste(C, "FRANKLIN", m, "CONF")[0] for m in con}
        sin_emd = {m: _contraste(C[C.inst != "EMD"], "FRANKLIN", m, "CONF")[0] for m in con}
        dec = LibroLord().probar("FRANKLIN", "CONF_MEJORA_SF_YM_EMD_RTY", [(f"FRANKLIN|{m}", res[m]["p"]) for m in con])
        for m in con:
            rech = f"FRANKLIN|{m}" in (dec.get("confirmadas") or [])
            out[f"FRANKLIN|{m}"] = dict(conf=res[m], sin_emd=sin_emd[m], rechazo=rech)
        out["lord"] = dec
    (DIR / "CONF.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: (v if k != "planes" else {m: v[m].get("potencia") for m in v}) for k, v in out.items() if k != "lord"}, default=float)[:1500])
    print("LORD", json.dumps(out.get("lord"), default=float)[:600])


if __name__ == "__main__":
    {"tabla": tabla, "desc": desc, "rep": rep, "conf": conf}[sys.argv[1]]()

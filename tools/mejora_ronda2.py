#!/usr/bin/env python3
"""Mejora ronda 2 (docs/research/mejora_estrategias_20261116/CRITERIOS_Y_PLAN.md §15): tamaño por regla (fijo / R constante / raíz) en SOM,
T y Franklin, y pesos de la cartera SOM + T + Franklin. Elección en años pares, confirmación en impares.

  python tools/mejora_ronda2.py <carpeta M1>   # -> docs/research/mejora_estrategias_20261116/RONDA2.json
Reusa las operaciones de SOM (RESULTADO_SOM), fundedsyncstack (T), estrategias_scrapeadas.franklin, reels_20261116.ctx_de_csv y fundedsync_tanda2._bh.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "docs/research/mejora_estrategias_20261116"; NB = 20000
USD_PT = {"NQ": 2.0, "ES": 5.0}; FR = {"NQ": 1.5455, "ES": 0.8877}


def operaciones(carpeta):
    """Por regla: fecha, neto en USD por micro y riesgo en USD por micro (operaciones de desarrollo hasta 2026-09-29)."""
    from edgelab.research import fundedsyncstack as F, estrategias_scrapeadas as X
    import fundedsync_tanda2 as T2, reels_20261116 as RR
    S = pd.read_csv(ROOT / "docs/research/quantlab_mt5_eas_20261116/SOM_OPS_NQ_sin_finde.csv.gz")
    ops = {"SOM": pd.DataFrame(dict(fecha=S.fecha, usd=(S.bruto - FR["NQ"]) * 2.0, riesgo=S.riesgo * 2.0))}
    D = T2.leer(carpeta, "NQ_M1_dukas"); ms = F.build_multi_series(F.load_m1_data(T2.a_utc(D), end="2026-10-01"), tz_input="UTC")
    x = F.correr_modulo("T", ms); o = T2._ops(x, FR["NQ"])
    # Riesgo INICIAL de T: el motor devuelve el stop activo al salir (movido a la entrada al activarse el stop administrado), no el inicial.
    # submit_entry fija stop = clip(rango 09:30–09:45 × 1,25, 2, 100) pts (FtmConfig): se reconstruye del M1 (2026-11-16).
    mm = D.index.hour * 60 + D.index.minute; orb = D[(mm >= 570) & (mm < 585)]; dd = orb.index.normalize()
    rango = (orb.h.groupby(dd).max() - orb.l.groupby(dd).min()); r0 = (rango * 1.25).clip(2.0, 100.0)
    ops["T"] = pd.DataFrame(dict(fecha=o.dia.dt.strftime("%Y%m%d").astype(int).values, usd=o.neto.values * 2.0, riesgo=r0.reindex(o.dia).to_numpy(float) * 2.0))
    fr = []
    for inst, arch in (("NQ", "NQ_M1_dukas"), ("ES", "SP_M1_dukas")):
        R = X.franklin(RR.ctx_de_csv(Path(carpeta) / f"{arch}.csv")); R = R[R.celda.map(tuple) == ("cierre",)]
        fr.append(pd.DataFrame(dict(fecha=R.fecha, usd=(R.bruto - FR[inst]) * USD_PT[inst], riesgo=R.riesgo * USD_PT[inst])))
    ops["FRANKLIN"] = pd.concat(fr, ignore_index=True)
    for k, g in ops.items():
        g["mes"] = pd.to_datetime(g.fecha.astype(str)).dt.to_period("M").astype(str); g["anio"] = g.fecha // 10000
        ops[k] = g[(g.riesgo > 0) & (g.fecha <= 20260929)].reset_index(drop=True)
    return ops


def pesos(g, modo, ref):
    """Contratos por operación: fijo 1; R_const ∝ 1/riesgo; raiz ∝ 1/√riesgo; escalados para que el riesgo medio en años pares = el de fijo."""
    if modo == "fijo": return np.ones(len(g))
    w = 1 / g.riesgo.to_numpy() if modo == "R_const" else 1 / np.sqrt(g.riesgo.to_numpy())
    e = (g.anio % 2 == 0).to_numpy(); return w * ref / np.mean(w[e] * g.riesgo.to_numpy()[e])


def mensual(g, w, meses):
    return pd.Series(g.usd.to_numpy() * w).groupby(g.mes.to_numpy()).sum().reindex(meses, fill_value=0.0)


def met(x, anios):
    ac = x.cumsum(); yr = x.groupby([m[:4] for m in x.index]).sum()
    return dict(t_mes=float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))) if x.std(ddof=1) > 0 else 0.0, usd_mes=float(x.mean()),
                anios_pos=int((yr > 0).sum()), anios=int(len(yr)), dd=float((ac - ac.cummax()).min()))


def main(carpeta):
    from fundedsync_tanda2 import _bh
    ops = operaciones(carpeta); res = dict(plan="docs/research/mejora_estrategias_20261116/CRITERIOS_Y_PLAN.md §15", tamano={}, pesos={})
    meses = sorted(set().union(*[set(g.mes) for g in ops.values()])); meses = [m for m in meses if "2012-02" <= m <= "2026-09"]
    par = [m for m in meses if int(m[:4]) % 2 == 0]; impar = [m for m in meses if int(m[:4]) % 2 == 1]
    series, pr = {}, []
    for k, g in ops.items():
        ref = float(g.riesgo[g.anio % 2 == 0].mean()); res["tamano"][k] = {}
        for modo in ("fijo", "R_const", "raiz"):
            x = mensual(g, pesos(g, modo, ref), meses); series[(k, modo)] = x
            res["tamano"][k][modo] = dict(E=met(x[par], par), C=met(x[impar], impar), riesgo_medio_usd=ref)
        for modo in ("R_const", "raiz"):                                      # diferencia normalizada por el desvío en pares
            a = series[(k, modo)] / series[(k, modo)][par].std(); b = series[(k, "fijo")] / series[(k, "fijo")][par].std()
            d = (a - b)[impar].to_numpy(); i = np.random.default_rng(7).integers(0, len(d), (NB, len(d))); m = d[i].mean(1)
            p = float((1 + (m <= 0).sum()) / (NB + 1)); pr.append(((k, modo), p))
            res["tamano"][k][modo]["dif_norm_C"] = float(d.mean()); res["tamano"][k][modo]["p"] = p
    for ((k, modo), p), b in zip(pr, _bh([p for _, p in pr])):
        v = res["tamano"][k][modo]; f = res["tamano"][k]["fijo"]
        v["confirma"] = bool(b and v["C"]["t_mes"] > f["C"]["t_mes"] and v["C"]["anios_pos"] >= f["C"]["anios_pos"])
    gana = {k: next((m for m in ("R_const", "raiz") if res["tamano"][k][m]["confirma"] and res["tamano"][k][m]["E"]["t_mes"] >= max(res["tamano"][k][x]["E"]["t_mes"] for x in ("R_const", "raiz") if res["tamano"][k][x]["confirma"])), "fijo") for k in ops}
    res["tamano_elegido"] = gana
    base = {k: series[(k, gana[k])] for k in ops}
    rm = {k: res["tamano"][k][gana[k]]["riesgo_medio_usd"] for k in ops}
    sd = {k: base[k][par].std() for k in ops}
    for modo, w in (("igual_contrato", {k: 1.0 for k in ops}), ("igual_riesgo", {k: np.mean(list(rm.values())) / rm[k] for k in ops}),
                    ("paridad_vol", {k: np.mean(list(sd.values())) / sd[k] for k in ops})):
        x = sum(base[k] * w[k] for k in ops); res["pesos"][modo] = dict(pesos={k: float(v) for k, v in w.items()}, E=met(x[par], par), C=met(x[impar], impar),
                                                                         reciente=met(x[[m for m in meses if m >= "2025-08"]], None))
    res["correlacion_mensual"] = pd.DataFrame(base).corr().round(3).to_dict()
    res["solas"] = {k: dict(E=met(base[k][par], par), C=met(base[k][impar], impar)) for k in ops}
    (OUT / "RONDA2.json").write_text(json.dumps(res, indent=1, default=float))
    for k in ops:
        print(k, {m: (round(v["E"]["t_mes"], 2), round(v["C"]["t_mes"], 2), v["C"]["anios_pos"], round(v.get("p", float("nan")), 3), v.get("confirma")) for m, v in res["tamano"][k].items()})
    print("tamaño elegido", gana)
    for m, v in res["pesos"].items(): print(m, {k: round(x, 2) for k, x in v["pesos"].items()}, "E t", round(v["E"]["t_mes"], 2), "C t", round(v["C"]["t_mes"], 2), "C usd/mes", round(v["C"]["usd_mes"]), "C dd", round(v["C"]["dd"]), "años+", v["C"]["anios_pos"], "/", v["C"]["anios"])
    print("solas", {k: (round(v["E"]["t_mes"], 2), round(v["C"]["t_mes"], 2)) for k, v in res["solas"].items()}); print(res["correlacion_mensual"])


if __name__ == "__main__":
    main(sys.argv[1])

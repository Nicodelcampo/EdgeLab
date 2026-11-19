#!/usr/bin/env python3
"""Las canastas vigentes (cartera v2, v3, B y v2+B) en LucidFlex 25K con sus 4 configuraciones oficiales y variantes de tamaño y de retiro.
Pedido de Nico (2026-11-17): «simulá Lucid con las canastas, distintas variantes». Descriptivo (no elige reglas ni toca el holdout).

Series: USD por sesión de desarrollo. v2/v3: `tools/cartera_nov_analisis._usd_diario` (micros enteros a `usd_R` por operación, DESC+REP,
2025-08 → 2026-09, sesiones sin operaciones = 0). B: T+Z+R a 1 MNQ por regla desde `fundedsyncstack_20261115/cadena/FUNDEDSYNC_OPS.csv.gz`
(2020-01 → 2026-09; SIN el stop de catástrofe de Z y R porque el desarrollo no trae ATR20/MAE: colas más pesadas que la regla operativa).
Cuenta: reglas oficiales (ver docs/research/propfirm_lucidflex_20261117/RESULTADO.md): objetivo $1.250, piso EOD a $1.000 que sube con el
mejor cierre y se fija en +$100 (al superar +$1.100 o al primer retiro), consistencia 40/50 % (mayor día / beneficio al llegar al objetivo;
si no, se sigue), DLL $600 blando (aprox.: la pérdida del día se corta en −$600), retiro con 5 días ≥ $100 y neto del ciclo > 0, 50 % del
beneficio total hasta $1.000, mínimo $500, 90 %, hasta 5 retiros. Bootstrap por bloques de 5 sesiones recentrado a la media declarada.
  python tools/lucid_canastas.py      # -> docs/research/propfirm_lucidflex_20261117/CANASTAS_LUCID.json
  python tools/lucid_canastas.py senales   # SOM + Franklin + T en MNQ por riesgo -> CANASTA_SENALES_LUCID.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from numba import njit

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "docs/research/propfirm_lucidflex_20261117"
CONFIG = {"DLL600|40%": (600.0, 0.4, 45.50), "DLL600|50%": (600.0, 0.5, 55.30), "sinDLL|40%": (0.0, 0.4, 60.20), "sinDLL|50%": (0.0, 0.5, 70.00)}


@njit(cache=False)
def _sim(x, mu, N, seed, dll, cons, pol_max, max_dias):
    np.random.seed(seed); y = x - x.mean() + mu; L = len(y)
    cob = np.zeros(N); pasa = np.zeros(N); pagos = np.zeros(N); de = np.zeros(N); df = np.zeros(N)
    for k in range(N):
        pos = np.random.randint(L); paso = 0
        bal = 0.0; piso = -1000.0; maxc = 0.0; mayor = 0.0; d = 0; ok = False
        while d < max_dias:                                          # evaluación
            if paso % 5 == 0: pos = np.random.randint(L)
            p = y[(pos + paso % 5) % L]; paso += 1
            if dll > 0 and p < -dll: p = -dll
            bal += p; d += 1; mayor = max(mayor, p)
            if bal <= piso: break
            maxc = max(maxc, bal); piso = min(max(piso, maxc - 1000.0), 100.0)
            if bal >= 1250.0 and mayor / bal <= cons: ok = True; break
        de[k] = d
        if not ok: continue
        pasa[k] = 1.0; bal = 0.0; piso = -1000.0; maxc = 0.0; c0 = 0.0; dok = 0; f = 0; npg = 0; tot = 0.0
        while f < max_dias and npg < 5:                               # fondeada
            if paso % 5 == 0: pos = np.random.randint(L)
            p = y[(pos + paso % 5) % L]; paso += 1
            if dll > 0 and p < -dll: p = -dll
            bal += p; f += 1
            if p >= 100.0: dok += 1
            if bal <= piso: break
            maxc = max(maxc, bal)
            if piso < 100.0: piso = 100.0 if maxc > 1100.0 else max(piso, maxc - 1000.0)
            monto = min(1000.0, 0.5 * bal)
            if dok >= 5 and bal > c0 and monto >= 500.0 and (monto >= 1000.0 or not pol_max):
                tot += 0.9 * monto; bal -= monto; npg += 1; piso = 100.0; c0 = bal; dok = 0
        cob[k] = tot; pagos[k] = npg; df[k] = f
    return cob, pasa, pagos, de, df


def serie_v(version, usd_R):
    import cartera_nov_analisis as CA
    S = json.loads((ROOT / ("docs/research/cartera_20261116/SELECCION.json" if version == "v2" else "docs/research/cartera_20261116/v3/SELECCION.json")).read_text())["futuros"]
    d, salt, tot = CA._usd_diario(S, ("desc", "rep"), usd_R)
    con = sorted({int(s) for c in S for t in ("desc", "rep") for s in (CA._ops(c, t) or {"ses": []})["ses"]})
    ses = [int(x.strftime("%Y%m%d")) for x in pd.bdate_range(str(max(con[0], 20250805)), str(min(con[-1], 20260929)))]
    return pd.Series([d.get(s, 0.0) for s in ses], index=ses), dict(reglas=S, saltadas=f"{salt}/{tot}")


def serie_b(micros=1, desde=20200101, modulos=("T", "Z", "R")):
    o = pd.read_csv(ROOT / "docs/research/fundedsyncstack_20261115/cadena/FUNDEDSYNC_OPS.csv.gz", usecols=["dia", "neto", "modulo"])
    o = o[o.modulo.isin(list(modulos))]; o["ses"] = pd.to_datetime(o.dia).dt.strftime("%Y%m%d").astype(int); o = o[(o.ses >= desde) & (o.ses <= 20260929)]
    d = (o.neto * 2.0 * micros).groupby(o.ses).sum()
    ses = [int(x.strftime("%Y%m%d")) for x in pd.bdate_range(str(desde), "2026-09-29")]
    return pd.Series([d.get(s, 0.0) for s in ses], index=ses), dict(reglas=list(modulos), micros=micros)


def serie_senales(usd_riesgo=150.0, reglas=("SOM", "FRANKLIN", "T"), desde=20200101, hasta=20250731, tope_micros=20, contrato="MNQ"):
    """Canasta de señales estables (SOM sin_finde, Franklin, T) en MNQ con tamaño por riesgo (2026-11-18, «edges para prop firms»):
    micros = piso(usd_riesgo / (riesgo en puntos × 2 USD)), entre 1 y `tope_micros`; P&L = micros × (bruto en puntos × 2 − fricción
    canónica de MNQ en USD). Operaciones del M1 de NT8 ya medidas (docs/research/m1_largo_20261117/); descriptivo, no elige reglas."""
    from edgelab.research.embudo_runners import friccion
    mult = {"MNQ": 2.0, "NQ": 20.0}[contrato]       # contrato de ejecución (2026-11-19: minis); tope_micros = tope de contratos de ese tipo
    D = ROOT / "docs/research/m1_largo_20261117"; fr_usd = float(friccion(contrato)[0]) * mult; fr_nq = float(friccion("NQ")[0]); partes = []
    if "SOM" in reglas:
        o = pd.read_csv(D / "SOM_OPS_NQ.csv.gz"); o = o[o.celda == "sin_finde"]; partes.append(o[["dia", "bruto", "riesgo"]])
    if "SOMEOD" in reglas:   # SOM que cierra a las 15:55 de NY (celda «eod»): la única que respeta el «plano a las 16:45» de Lucid (2026-11-19)
        o = pd.read_csv(D / "SOM_OPS_NQ.csv.gz"); o = o[o.celda == "eod"]; partes.append(o[["dia", "bruto", "riesgo"]])
    if "FRANKLIN" in reglas:
        partes.append(pd.read_csv(D / "FRANKLIN_OPS_NQ.csv.gz")[["dia", "bruto", "riesgo"]])
    if "T" in reglas:
        o = pd.read_csv(D / "FS_OPS_T2008_NQ.csv.gz"); o = o[o.riesgo > 0]; o["bruto"] = o.neto + fr_nq; partes.append(o[["dia", "bruto", "riesgo"]])
    if "R" in reglas:        # R AtrPhase de fábrica con stop de catástrofe 0,25 × ATR20 previo aplicado con el MAE (NETO-PISTAS; pnl_pts es bruto)
        o = pd.read_csv(ROOT / "docs/research/neto_pistas_20261119/RZ_OPS.csv.gz"); o = o[(o.modulo == "R") & (o.inst == "NQ") & (o.variante == "R_21_100_2.5_660")]
        rg = 0.25 * o.atr20; o = o.assign(dia=o.ses, riesgo=rg, bruto=np.where(o.mae_pts >= rg, -rg, o.pnl_pts)); partes.append(o[["dia", "bruto", "riesgo"]])
    if "ZB" in reglas:       # Z-banda (9 configuraciones de severidad moderada, promedio diario; regimen_forward_20261119/PREREGISTRO_ZBANDA.md)
        o = pd.read_csv(ROOT / "docs/research/neto_pistas_20261119/RZ_OPS.csv.gz")
        banda = [f"Z_{a}_{b}_{e}" for (a, b) in ((10, 30), (15, 20), (30, 10)) for e in (35, 45, 55)]
        o = o[(o.modulo == "Z") & (o.inst == "NQ") & o.variante.isin(banda)]; rg = 0.25 * o.atr20
        o = o.assign(bruto=np.where(o.mae_pts >= rg, -rg, o.pnl_pts), riesgo=rg).groupby("ses")[["bruto", "riesgo"]].mean().reset_index().rename(columns={"ses": "dia"})
        partes.append(o[["dia", "bruto", "riesgo"]])
    o = pd.concat(partes, ignore_index=True); o["ses"] = pd.to_datetime(o.dia).dt.strftime("%Y%m%d").astype(int)
    o = o[(o.ses >= desde) & (o.ses <= hasta)]
    mic = np.clip(np.floor(usd_riesgo / (o.riesgo * mult)), 1, tope_micros)
    d = (mic * (o.bruto * mult - fr_usd)).groupby(o.ses).sum()
    ses = [int(x.strftime("%Y%m%d")) for x in pd.bdate_range(str(desde), str(hasta))]
    return pd.Series([d.get(s, 0.0) for s in ses], index=ses), dict(reglas=list(reglas), usd_riesgo=usd_riesgo, micros_medio=float(mic.mean()),
        contrato=contrato, riesgo_usd_real_p10_50_90=[float(np.quantile(mic * o.riesgo * mult, q)) for q in (0.1, 0.5, 0.9)] if len(o) else None,
        ops=int(len(o)))


def serie_orb5(usd_riesgo=100.0, desde=20200101, hasta=20250731, tope_micros=20, fric_max=0.08):
    """ORB de 5 min (ORB-A5 O1) en MNQ, sólo el subconjunto operable declarado (fricción de micro ≤ 0,08 R) y sólo sesiones DESC/REP de A5
    (los meses HOLDOUT siguen sellados). Devuelve la serie diaria y las sesiones disponibles (para recortar otras series igual)."""
    from edgelab.research.embudo_runners import friccion
    from edgelab.holdout import a5_bloque
    O = pd.read_csv(ROOT / "docs/research/orb_a5_20261118/OPS_DESC_REP.csv.gz"); e = "P_obj_stop_fin"
    O = O[O.O1.astype(bool) & (O.inst == "NQ") & O[f"r_{e}"].notna() & (O[f"k_{e}"] > 0) & (O.ses >= desde) & (O.ses <= hasta)]
    fr_pts = float(friccion("MNQ")[0]); O = O[fr_pts / O[f"k_{e}"] <= fric_max]
    mic = np.clip(np.floor(usd_riesgo / (O[f"k_{e}"] * 2.0)), 1, tope_micros)
    d = (mic * (O[f"r_{e}"] * O[f"k_{e}"] * 2.0 - fr_pts * 2.0)).groupby(O.ses).sum()
    ses = [s for s in (int(x.strftime("%Y%m%d")) for x in pd.bdate_range(str(desde), str(hasta))) if a5_bloque(s) in ("DESC", "REP")]
    return pd.Series([d.get(s, 0.0) for s in ses], index=ses), dict(regla="ORB5 O1 NQ→MNQ operable", usd_riesgo=usd_riesgo, ops=int(len(O)))


def senales():
    res = dict(nota="Canasta de señales estables en MNQ con tamaño por riesgo; contracción declarada 0,5 (efecto 2020–2025 elegido después de "
                    "ver el salto de T; SOM y Franklin con bruto estable desde 2006)", canastas={})
    for usd in (100, 150, 250):
        for reglas in (("SOM", "FRANKLIN", "T"), ("SOM", "FRANKLIN"), ("T",), ("R",), ("T", "R")):
            x, info = serie_senales(usd, reglas); r = evaluar(x.to_numpy(), 0.5); r.update(info)
            nom = f"{'+'.join(reglas)}|usd{usd}"; res["canastas"][nom] = r; _imprimir(nom, r)
    xo, info_o = serie_orb5(100.0); xt, _ = serie_senales(100.0, ("T",)); xt = xt.reindex(xo.index).fillna(0.0)    # mismas sesiones (DESC/REP)
    res["correlacion_T_ORB5"] = float(np.corrcoef(xo, xt)[0, 1])
    for nom, x in (("ORB5|usd100|DESC+REP", xo), ("T|usd100|DESC+REP", xt), ("T+ORB5|usd100|DESC+REP", xo + xt)):
        r = evaluar(x.to_numpy(), 0.5); r.update(info_o if "ORB5" in nom else {}); res["canastas"][nom] = r; _imprimir(nom, r)
    print("correlación diaria T vs ORB5:", round(res["correlacion_T_ORB5"], 3))
    (OUT / "CANASTA_SENALES_LUCID.json").write_text(json.dumps(res, indent=1, default=float))


def evaluar(x, contr, N=20000, max_dias=250):
    out = dict(sesiones=len(x), usd_sesion_media=float(x.mean()), usd_sesion_sd=float(x.std(ddof=1)), peor_dia=float(x.min()),
               t=float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))), variantes={})
    for nom, (dll, cons, precio) in CONFIG.items():
        for mu_nom, mu in (("dev", x.mean()), ("contraida", x.mean() * contr), ("cero", 0.0)):
            for pol in ("max", "min"):
                cob, pas, pg, de, df = _sim(np.asarray(x, np.float64), float(mu), N, 7, dll, cons, pol == "max", max_dias)
                dias = de + df
                out["variantes"][f"{nom}|{mu_nom}|{pol}"] = dict(precio=precio, pasa=float(pas.mean()), cobra=float((pg > 0).mean()), retiros=float(pg.mean()),
                    cobrado=float(cob.mean()), ev=float(cob.mean() - precio), p_ganar=float((cob > precio).mean()), dias_eval=float(de.mean()),
                    dias_fondeada=float(df[pas > 0].mean()) if pas.any() else 0.0, dias_total=float(dias.mean()),
                    ev_por_mes=float((cob.mean() - precio) / max(dias.mean(), 1) * 21), quema_eval=float(1 - pas.mean()))
    return out


def main():
    BAT = json.loads((ROOT / "docs/research/cartera_20261116/BATERIA.json").read_text())["reglas"]; B = {b["cid"]: b for b in BAT}
    res = dict(reglas_lucid="docs/research/propfirm_lucidflex_20261117/RESULTADO.md", canastas={})
    for version in ("v2", "v3"):
        S = json.loads((ROOT / ("docs/research/cartera_20261116/SELECCION.json" if version == "v2" else "docs/research/cartera_20261116/v3/SELECCION.json")).read_text())["futuros"]
        contr = float(np.mean([B[c]["R_contraido"] / max(B[c]["dev"]["R_op"], 1e-9) for c in S if c in B]))
        for usd in (100, 200, 300):
            x, info = serie_v(version, usd); r = evaluar(x.to_numpy(), contr); r.update(info, factor_contraccion=contr)
            res["canastas"][f"{version}|usd{usd}"] = r; _imprimir(f"{version}|usd{usd}", r)
    for mic in (1, 2):
        x, info = serie_b(mic); r = evaluar(x.to_numpy(), 0.5); r.update(info, factor_contraccion=0.5, nota="contracción declarada 0,5 (no hay batería)")
        res["canastas"][f"B|{mic}MNQ"] = r; _imprimir(f"B|{mic}MNQ", r)
    for mods in (("T",), ("Z",), ("R",), ("T", "Z"), ("T", "R"), ("Z", "R")):                    # B por componentes (Nico: «¿probaste T+Z+R?»)
        x, info = serie_b(1, modulos=mods); r = evaluar(x.to_numpy(), 0.5); r.update(info, factor_contraccion=0.5)
        res["canastas"][f"B[{'+'.join(mods)}]|1MNQ"] = r; _imprimir(f"B[{'+'.join(mods)}]|1MNQ", r)
    for desde, nom in ((20250805, "B|1MNQ|desde-2025-08"),):                                      # mismo tramo que la v2
        x, info = serie_b(1, desde=desde); r = evaluar(x.to_numpy(), 0.5); r.update(info, factor_contraccion=0.5); res["canastas"][nom] = r; _imprimir(nom, r)
    xv, _ = serie_v("v2", 200); xb, _ = serie_b(1, 20250805); ix = xv.index.intersection(xb.index)
    xc = xv.reindex(ix) + xb.reindex(ix); r = evaluar(xc.to_numpy(), 0.5)
    r.update(correlacion=float(np.corrcoef(xv.reindex(ix), xb.reindex(ix))[0, 1]), nota="v2 a 200 USD + B a 1 MNQ, sesiones comunes 2025-08 → 2026-09")
    res["canastas"]["v2+B"] = r; _imprimir("v2+B", r)
    (OUT / "CANASTAS_LUCID.json").write_text(json.dumps(res, indent=1, default=float))


def _imprimir(nom, r):
    v = r["variantes"]
    print(nom, f"ses {r['sesiones']} media {r['usd_sesion_media']:.0f} sd {r['usd_sesion_sd']:.0f} t {r['t']:.2f}", flush=True)
    for k in ("DLL600|50%|dev|max", "DLL600|50%|contraida|max", "DLL600|50%|cero|max", "sinDLL|50%|contraida|max", "DLL600|40%|contraida|min"):
        e = v[k]; print("   ", k, {q: round(e[q], 3) for q in ("pasa", "cobra", "retiros", "ev", "ev_por_mes", "dias_total")}, flush=True)


if __name__ == "__main__":
    senales() if sys.argv[1:] == ["senales"] else main()

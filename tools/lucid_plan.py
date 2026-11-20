#!/usr/bin/env python3
"""LUCID-PLAN: qué conviene hacer en LucidFlex para ganar más, con el piso y el DLL simulados DENTRO del día, y la reproducción del plan
elegido sobre el holdout ya abierto de FUNDEDSYNC (2026-10-01 → 2026-11-13). Pedido de Nico (2026-11-19): «simulá bien para determinar qué
es lo que más me conviene hacer para ganar la mayor cantidad de dinero posible. Luego simulá esa estrategia como si la hubiera hecho en
challenges a partir del holdout».

Qué agrega a `tools/lucid_guia.py` (que reutiliza: TAMANOS, precio):
  - día con P&L de cierre Y mínimo intradía: cada operación aporta su excursión adversa (MAE, topeada por el stop) después del P&L ya
    realizado ese día (orden por hora de entrada); la fricción se cuenta entera en el mínimo. El piso se rompe si el saldo + el mínimo
    del día lo toca; el DLL cierra el día en −DLL si el mínimo lo toca (las operaciones siguientes de ese día no ocurren).
  - contratos fijos por regla (micros, o minis si son múltiplos de 10, con la fricción de NQ), con el tope de Lucid para el peor caso de
    todas las reglas abiertas a la vez; Z-banda como 1 micro por configuración (9) por unidad.
  - política de retiro (máximo o en cuanto se pueda), consistencia 40/50 %, DLL sí/no, evaluaciones simultáneas.
  - media contraída por operación (cada operación pierde una constante en USD hasta que la media diaria es la fracción declarada).
Criterio de elección (declarado antes de correr, en PLAN.md): máximo neto medio a 12 meses de la cartera con la media contraída a la mitad,
entre los planes con P(neto 12 m > 0) ≥ 0,8 bajo esa media; se reportan también la media de desarrollo y la media cero.
  python tools/lucid_plan.py elegir     # -> docs/research/lucid_plan_20261119/PLANES.json
  python tools/lucid_plan.py holdout    # -> HOLDOUT_REPLAY.json (sólo ops del holdout YA publicadas: no abre nada nuevo)
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from numba import njit

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "docs/research/lucid_plan_20261119"
from lucid_guia import TAMANOS, precio  # noqa: E402

BANDA = [f"Z_{a}_{b}_{e}" for (a, b) in ((10, 30), (15, 20), (30, 10)) for e in (35, 45, 55)]
DESDE, HASTA = "2020-01-01", "2026-09-30"


def _fr():
    from edgelab.research.embudo_runners import friccion
    return float(friccion("NQ")[0]), float(friccion("MNQ")[0])


def ops_desarrollo():
    """Una fila por operación: ses, hora (NY), regla (T, R, Z_* de la banda), bruto y MAE en puntos de NQ (MAE ≥ 0, topeado por el stop)."""
    frn, _ = _fr(); D = ROOT / "docs/research"
    t = pd.read_csv(D / "m1_largo_20261117/FS_OPS_T2008_NQ.csv.gz"); t = t[t.riesgo > 0]
    t = pd.DataFrame(dict(ses=pd.to_datetime(t.dia), hora=pd.to_datetime(t.t, unit="s", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None),
                          regla="T", bruto=t.neto + frn, mae=np.minimum(t.mae_pts.abs(), t.riesgo)))
    o = pd.read_csv(D / "neto_pistas_20261119/RZ_OPS.csv.gz"); o = o[(o.inst == "NQ") & ((o.variante == "R_21_100_2.5_660") | o.variante.isin(BANDA))]
    rg = 0.25 * o.atr20; o = o[rg > 0]; rg = 0.25 * o.atr20
    z = pd.DataFrame(dict(ses=pd.to_datetime(o.ses), hora=pd.to_datetime(o.t), regla=np.where(o.modulo == "R", "R", o.variante),
                          bruto=np.where(o.mae_pts >= rg, -rg, o.pnl_pts), mae=np.minimum(o.mae_pts.abs(), rg)))
    x = pd.concat([t, z], ignore_index=True)
    return x[(x.ses >= DESDE) & (x.ses <= HASTA)].sort_values(["ses", "hora"]).reset_index(drop=True)


def contratos(canasta, s):
    """Micros por operación de cada regla para la unidad s; Z-banda = s//9 micros por configuración (sólo si s ≥ 9)."""
    c = {"T": s}
    if "R" in canasta: c["R"] = s
    if "ZB" in canasta: c.update({b: s // 9 for b in BANDA})
    return {k: v for k, v in c.items() if v > 0}


def max_simultaneo(canasta, s):
    return s + (s if "R" in canasta else 0) + (9 * (s // 9) if "ZB" in canasta else 0)


def dias(x, cont, fraccion, desde=DESDE, hasta=HASTA):
    """P&L de cierre y mínimo intradía por sesión hábil (USD) para los contratos dados; `fraccion` contrae la media por operación."""
    frn, frm = _fr(); x = x[x.regla.isin(cont)].copy(); n = x.regla.map(cont).astype(float)
    mini = (n >= 10) & (n % 10 == 0)
    usd = np.where(mini, n / 10 * (x.bruto * 20 - frn * 20), n * (x.bruto * 2 - frm * 2))
    adv = np.where(mini, n / 10 * (x.mae * 20 + frn * 20), n * (x.mae * 2 + frm * 2))
    ses = pd.bdate_range(desde, hasta)
    if len(x) and fraccion != 1.0:
        tot = usd.sum() / len(ses); usd = usd - (1 - fraccion) * tot * len(ses) / len(x)
    x["usd"] = usd; x["adv"] = adv
    x["antes"] = x.groupby("ses").usd.cumsum() - x.usd
    x["lo"] = x.antes - x.adv
    g = x.groupby("ses").agg(p=("usd", "sum"), lo=("lo", "min"))
    g = g.reindex(ses, fill_value=0.0); lo = np.minimum(np.minimum(g.lo.to_numpy(), 0.0), g.p.to_numpy())
    return g.p.to_numpy(np.float64), lo.astype(np.float64)


@njit(cache=False)
def _dia(p, lo, dll):
    if dll > 0 and lo <= -dll: return -dll, -dll
    return p, lo


@njit(cache=False)
def _cartera(P, LO, N, seed, H, objetivo, mll, dll, dia_min, tope, cons, pr, max_eval, pol_max):
    """Igual que lucid_guia._cartera pero con el mínimo intradía (piso y DLL) y política de retiro. Devuelve caja a 12 m y 24 m."""
    np.random.seed(seed); L = len(P); S = 10
    caja = np.zeros(N); caja12 = np.zeros(N); cmin = np.zeros(N); live = np.full(N, -1.0); comp = np.zeros(N); fond = np.zeros(N); ret = np.zeros(N)
    for k in range(N):
        est = np.zeros(S, np.int64); bal = np.zeros(S); piso = np.zeros(S); maxc = np.zeros(S); mayor = np.zeros(S)
        dok = np.zeros(S, np.int64); c0 = np.zeros(S); npg = np.zeros(S, np.int64)
        pos = np.random.randint(L); c = 0.0; mn = 0.0
        for d in range(H):
            if d % 5 == 0: pos = np.random.randint(L)
            j = (pos + d % 5) % L; p, lo = _dia(P[j], LO[j], dll)
            vivo = False
            for i in range(S):
                if est[i] == 1:
                    if bal[i] + lo <= piso[i]: est[i] = 0; continue
                    bal[i] += p; mayor[i] = max(mayor[i], p)
                    maxc[i] = max(maxc[i], bal[i]); piso[i] = min(max(piso[i], maxc[i] - mll), 100.0)
                    if bal[i] >= objetivo and mayor[i] / bal[i] <= cons: est[i] = 2
                elif est[i] == 3:
                    if bal[i] + lo <= piso[i]: est[i] = 0; continue
                    bal[i] += p
                    if p >= dia_min: dok[i] += 1
                    maxc[i] = max(maxc[i], bal[i])
                    if piso[i] < 100.0: piso[i] = 100.0 if maxc[i] > mll + 100.0 else max(piso[i], maxc[i] - mll)
                    monto = min(tope, 0.5 * bal[i])
                    if dok[i] >= 5 and bal[i] > c0[i] and monto >= 500.0 and (monto >= tope or not pol_max):
                        c += 0.9 * monto; ret[k] += 1; bal[i] -= monto; npg[i] += 1; piso[i] = 100.0; c0[i] = bal[i]; dok[i] = 0
                        if npg[i] >= 5: vivo = True
            if vivo:
                for i in range(S):
                    if est[i] == 1 and bal[i] - piso[i] >= 0.5 * mll: c += pr
                live[k] = d
                if d < 252: caja12[k] = c
                break
            nf = 0; ne = 0
            for i in range(S):
                if est[i] == 3: nf += 1
            for i in range(S):
                if est[i] == 2 and nf < 5:
                    est[i] = 3; nf += 1; fond[k] += 1; bal[i] = 0.0; piso[i] = -mll; maxc[i] = 0.0; dok[i] = 0; c0[i] = 0.0; npg[i] = 0
            for i in range(S):
                if est[i] == 1 or est[i] == 2: ne += 1
            for i in range(S):
                if ne >= max_eval or ne + nf >= 10: break
                if est[i] == 0:
                    est[i] = 1; bal[i] = 0.0; piso[i] = -mll; maxc[i] = 0.0; mayor[i] = 0.0; c -= pr; comp[k] += 1; ne += 1
                    break
            mn = min(mn, c)
            if d == 251: caja12[k] = c
        caja[k] = c; cmin[k] = mn
    return caja12, caja, cmin, live, comp, fond, ret


def _q(a, qs=(0.1, 0.5, 0.9)):
    return [round(float(np.quantile(a, q)), 0) for q in qs]


def evaluar_plan(x, tam, canasta, s, dll_on, cons, pol_max, max_eval, fraccion, N=2000, H=504, seed=11):
    r = TAMANOS[tam]; P, LO = dias(x, contratos(canasta, s), fraccion); pr = precio(tam, dll_on, cons)
    c12, c24, mn, live, comp, fond, ret = _cartera(P, LO, N, seed, H, r["objetivo"], r["mll"], r["dll"] if dll_on else 0.0, r["dia_min"], r["tope"],
                                                  cons, pr, max_eval, pol_max)
    viv = live >= 0
    return dict(neto12_medio=float(c12.mean()), neto12_p10_50_90=_q(c12), p_neto12_pos=float((c12 > 0).mean()), neto24_medio=float(c24.mean()),
                neto24_p10_50_90=_q(c24), caja_min_p50_p10=[float(np.median(mn)), float(np.quantile(mn, 0.1))], p_live_24m=float(viv.mean()),
                meses_live_p50=float(np.median(live[viv]) / 21) if viv.any() else None, evals=float(comp.mean()), fondeadas=float(fond.mean()),
                retiros=float(ret.mean()), precio=pr, usd_dia=float(P.mean()), peor_minimo=float(LO.min()))


def grilla():
    for tam, r in TAMANOS.items():
        for canasta in ("T", "T+R", "T+R+ZB"):
            for s in (1, 2, 3, 5, 7, 9, 10, 15, 18, 20, 27, 30, 40, 50):
                if max_simultaneo(canasta, s) > r["micros"] or ("ZB" in canasta and s < 9): continue
                for dll_on in (True, False):
                    for cons in (0.4, 0.5):
                        for pol_max in (True, False):
                            yield tam, canasta, s, dll_on, cons, pol_max


def elegir():
    OUT.mkdir(parents=True, exist_ok=True); x = ops_desarrollo(); res = dict(etapa1={}, etapa2={})
    for tam, canasta, s, dll_on, cons, pol_max in grilla():                 # etapa 1: 3 evaluaciones a la vez, 1.000 calendarios
        k = f"{tam}|{canasta}|s{s}|{'DLL' if dll_on else 'sinDLL'}|{int(cons * 100)}%|{'max' if pol_max else 'min'}"
        res["etapa1"][k] = evaluar_plan(x, tam, canasta, s, dll_on, cons, pol_max, 3, 0.5, N=1000)
        print(k, round(res["etapa1"][k]["neto12_medio"]), flush=True)
    top = sorted(res["etapa1"], key=lambda k: -res["etapa1"][k]["neto12_medio"])[:25]
    for k in top:                                                            # etapa 2: evaluaciones a la vez y tres medias
        tam, canasta, s, dl, co, pol = k.split("|")
        for me in (1, 3, 5, 10):
            for fr_nom, fr in (("contraida", 0.5), ("dev", 1.0), ("cero", 0.0)):
                kk = f"{k}|eval{me}|{fr_nom}"
                res["etapa2"][kk] = evaluar_plan(x, tam, canasta, int(s[1:]), dl == "DLL", int(co[:-1]) / 100, pol == "max", me, fr, N=3000)
        print("etapa2", k, flush=True)
    ok = {k: v for k, v in res["etapa2"].items() if k.endswith("|contraida") and v["p_neto12_pos"] >= 0.8}
    res["elegido"] = max(ok, key=lambda k: ok[k]["neto12_medio"]) if ok else None
    (OUT / "PLANES.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print("ELEGIDO", res["elegido"], res["etapa2"].get(res["elegido"]))


def holdout():
    """Reproduce el plan elegido sobre las operaciones del holdout de FUNDEDSYNC ya publicadas el 2026-11-16 (USATECH sellado, costos de NQ;
    T con la misma regla; R y Z de fábrica SIN stop y sin MAE: no son las reglas del plan). Una trayectoria, sin bootstrap."""
    out = dict(nota="El criterio pre-registrado (P(neto 12 m > 0) ≥ 0,8) no lo cumplió ningún plan (máximo 0,7997); se reproducen los dos "
               "planes fijados antes de mirar: A = mayor neto medio a 12 m, B = mayor P(neto 12 m > 0).", planes={})
    for etiqueta, plan in (("A", "150K|T+R+ZB|s9|DLL|50%|max|eval10|contraida"), ("B", "50K|T+R|s5|DLL|50%|min|eval10|contraida")):
        out["planes"][etiqueta] = _holdout_plan(plan)
    (OUT / "HOLDOUT_REPLAY.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    for e, v in out["planes"].items():
        print(e, v["plan"], {k: (w["caja_final"], w["comprado"], w["cobrado"], [(c["estado"], c.get("pasó"), c.get("fin"), c["retiros"]) for c in w["cuentas"]]) for k, w in v["escenarios"].items()})


def _holdout_plan(plan):
    tam, canasta, s, dl, co, pol, me, _ = plan.split("|")
    s = int(s[1:]); r = TAMANOS[tam]; dll = r["dll"] if dl == "DLL" else 0.0; cons = int(co[:-1]) / 100; me = int(me[4:]); pr = precio(tam, dl == "DLL", cons)
    frn, frm = _fr()
    o = pd.read_csv(ROOT / "docs/research/fundedsyncstack_20261115/cadena/FUNDEDSYNC_HOLDOUT_OPS.csv")
    o["ses"] = pd.to_datetime(o.dia); o["bruto"] = o.neto + frn; ses = pd.bdate_range("2026-10-01", "2026-11-13")
    res = dict(plan=plan, sesiones=len(ses), escenarios={})
    for nom, reglas, mae_gan in (("T_mae_cero", ("T",), 0.0), ("T_mae_riesgo", ("T",), 1.0),
                                 ("T+R+Z_sin_stop_mae_cero", ("T", "R", "Z"), 0.0)):
        if nom.startswith("T+") and canasta == "T": continue
        x = o[o.modulo.isin(reglas)].copy(); n = x.modulo.map({"T": s, "R": s, "Z": max(s // 9, 1) * 9 if "ZB" in canasta else 0}).astype(float)
        x = x[n > 0]; n = n[n > 0]; mini = (n >= 10) & (n % 10 == 0)
        usd = np.where(mini, n / 10 * (x.bruto * 20 - frn * 20), n * (x.bruto * 2 - frm * 2))
        mae = np.where(x.neto < 0, -x.neto + 0.0, mae_gan * x.riesgo.fillna(0.0))     # perdedoras: su pérdida; ganadoras: 0 o el riesgo entero
        adv = np.where(mini, n / 10 * (np.maximum(mae - frn, 0) * 20 + frn * 20), n * (np.maximum(mae - frn, 0) * 2 + frm * 2))
        x["usd"] = usd; x["adv"] = adv; x = x.sort_values(["ses", "t"]); x["lo"] = x.groupby("ses").usd.cumsum() - x.usd - x.adv
        g = x.groupby("ses").agg(p=("usd", "sum"), lo=("lo", "min")).reindex(ses, fill_value=0.0)
        P = g.p.to_numpy(np.float64); LO = np.minimum(np.minimum(g.lo.to_numpy(), 0), P).astype(np.float64)
        res["escenarios"][nom] = _replay(P, LO, ses, r, dll, cons, pr, me, pol == "max")
    return res


def _replay(P, LO, ses, r, dll, cons, pr, max_eval, pol_max):
    """Calendario real: el día 1 se compran evaluaciones (1 por día) hasta el máximo; mismas reglas que _cartera. Bitácora por cuenta."""
    cuentas = []; caja = 0.0; diario = []
    for d, fecha in enumerate(ses):
        p, lo = (-dll, -dll) if dll > 0 and LO[d] <= -dll else (P[d], LO[d])
        for a in cuentas:
            if a["estado"] not in ("eval", "fondeada"): continue
            if a["bal"] + lo <= a["piso"]: a["estado"] = "quemada_" + a["estado"]; a["fin"] = str(fecha.date()); continue
            a["bal"] += p; a["mayor"] = max(a["mayor"], p); a["maxc"] = max(a["maxc"], a["bal"])
            if a["estado"] == "eval":
                a["piso"] = min(max(a["piso"], a["maxc"] - r["mll"]), 100.0)
                if a["bal"] >= r["objetivo"] and a["mayor"] / a["bal"] <= cons:
                    a["estado"] = "aprobada"; a["pasó"] = str(fecha.date())
            else:
                if p >= r["dia_min"]: a["dok"] += 1
                if a["piso"] < 100: a["piso"] = 100.0 if a["maxc"] > r["mll"] + 100 else max(a["piso"], a["maxc"] - r["mll"])
                m = min(r["tope"], 0.5 * a["bal"])
                if a["dok"] >= 5 and a["bal"] > a["c0"] and m >= 500 and (m >= r["tope"] or not pol_max):
                    caja += 0.9 * m; a["retiros"].append((str(fecha.date()), round(0.9 * m, 2))); a["bal"] -= m; a["piso"] = 100.0; a["c0"] = a["bal"]; a["dok"] = 0
        nf = sum(a["estado"] == "fondeada" for a in cuentas)
        for a in cuentas:                                     # máximo 5 fondeadas: la aprobada espera lugar (como en _cartera)
            if a["estado"] == "aprobada" and nf < 5:
                a["estado"] = "fondeada"; a["fondeada_desde"] = str(fecha.date()); a.update(bal=0.0, piso=-r["mll"], maxc=0.0, dok=0, c0=0.0); nf += 1
        ne = sum(a["estado"] in ("eval", "aprobada") for a in cuentas)
        if ne < max_eval and ne + nf < 10:
            cuentas.append(dict(id=len(cuentas) + 1, compra=str(fecha.date()), estado="eval", bal=0.0, piso=-r["mll"], maxc=0.0, mayor=0.0, retiros=[], dok=0, c0=0.0))
            caja -= pr
        diario.append(dict(fecha=str(fecha.date()), usd_dia=round(float(P[d]), 2), minimo=round(float(LO[d]), 2), caja=round(caja, 2)))
    return dict(caja_final=round(caja, 2), comprado=round(pr * len(cuentas), 2), cobrado=round(sum(m for a in cuentas for _, m in a["retiros"]), 2),
                cuentas=[{k: (round(v, 2) if isinstance(v, float) else v) for k, v in a.items()} for a in cuentas], diario=diario)


if __name__ == "__main__":
    {"elegir": elegir, "holdout": holdout}[sys.argv[1]]()

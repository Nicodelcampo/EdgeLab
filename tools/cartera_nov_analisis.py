#!/usr/bin/env python3
"""Análisis de la cartera del período nuevo (pre-registro docs/research/cartera_20261116/PREREGISTRO.md).

  python tools/cartera_nov_analisis.py seleccion     # batería §4 + selección §5 con sesiones <= 2026-10-30 -> BATERIA.json, SELECCION.json
  python tools/cartera_nov_analisis.py noviembre     # §6, sólo si SELECCION.json está commiteado y sin cambios -> NOVIEMBRE.json
  python tools/cartera_nov_analisis.py prop          # §8 simulación de la evaluación 50K -> PROP.json

Datos: tools/cartera_nov.py (ops/<cid>__{desc,rep,hold}.json) y canasta_7_20261030/desarrollo_en_r (desarrollo ya medido).
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from cartera_nov import DIR, OPS, DEV_PREVIO, universo  # noqa: E402

CORTE_OCT, NOV0 = 20261030, 20261102
FAMILIAS = ("CVGAP", "U1-ZONAS", "U1-RACIMOS", "U1-", "DRC", "TORI", "CONF", "PREAPERTURA")
FUTUROS = {"NQ", "ES", "YM", "GC", "MNQ", "MES", "MYM", "MGC"}


def familia(cid):
    return next(f for f in FAMILIAS if cid.startswith(f))


def _ops(cid, tramo):
    f = (DEV_PREVIO / f"{cid}__{tramo}.json") if tramo != "hold" and (DEV_PREVIO / f"{cid}__{tramo}.json").exists() else OPS / f"{cid}__{tramo}.json"
    if not f.exists(): return None
    o = json.loads(f.read_text()).get("operaciones") or {}
    ses = np.array(o.get("ses", []), int); neto = np.array(o.get("neto", []), float)
    rg = np.array([np.nan if x is None else x for x in o.get("riesgo", [np.nan] * len(neto))], float)
    ok = np.isfinite(neto) & np.isfinite(rg) & (rg > 0)
    en_R = _en_R(cid)                                  # campañas con "estadistico": "R": el motor ya devuelve el neto en R (etapas.py)
    return dict(ses=ses[ok], R=neto[ok] if en_R else neto[ok] / rg[ok], riesgo=rg[ok])


_ESTAD = {}


def _en_R(cid):
    if not _ESTAD: _ESTAD.update({r["cid"]: r["spec"].get("estadistico") == "R" for r in universo()})
    return _ESTAD.get(cid, False)


def _validas_hold(sp):
    """Sesiones válidas del holdout: no excluidas en edgelab/holdout.py (las incompletas de octubre están declaradas ahí)."""
    from edgelab.holdout import sesion_excluida
    insts = {x[3:] if x.startswith("DK:") else x for x in (sp["sensor"], sp.get("ejecucion") or sp["sensor"])}
    return lambda s: not any(sesion_excluida(i, s) for i in insts)


def _sesion(ses, R):
    if not len(R): return np.array([]), np.array([])
    u, inv = np.unique(ses, return_inverse=True); return u, np.bincount(inv, weights=R)


def _boot_ic(ses, R, B=4000, seed=7):
    u, x = _sesion(ses, R); n = np.bincount(np.unique(ses, return_inverse=True)[1]) if len(R) else np.array([])
    if len(u) < 3: return [None, None]
    rng = np.random.default_rng(seed); i = rng.integers(0, len(u), (B, len(u)))
    m = x[i].sum(1) / n[i].sum(1); return [float(np.quantile(m, .05)), float(np.quantile(m, .95))]


def _t_ses(ses, R):
    u, x = _sesion(ses, R)
    return float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else None


def metricas(cid, sp):
    from edgelab.research.embudo_runners import friccion
    d = {t: _ops(cid, t) for t in ("desc", "rep", "hold")}
    if d["desc"] is None or d["rep"] is None or d["hold"] is None: return None
    ok = _validas_hold(sp); h = d["hold"]; m = np.array([ok(s) for s in h["ses"]], bool) if len(h["ses"]) else np.zeros(0, bool)
    h = {k: v[m] for k, v in h.items()}
    octb = h["ses"] <= CORTE_OCT; nov = h["ses"] >= NOV0
    dev = {k: np.r_[d["desc"][k], d["rep"][k]] for k in ("ses", "R", "riesgo")}
    fr_pts = friccion(sp.get("ejecucion") or sp["sensor"])[0]; frR = fr_pts / dev["riesgo"]
    mes = dev["ses"] // 100; meses = {mm: dev["R"][mes == mm].sum() for mm in np.unique(mes)}
    srt = np.sort(dev["R"]); eq = np.cumsum(dev["R"][np.argsort(dev["ses"], kind="stable")])
    racha = mx = 0
    for r in dev["R"][np.argsort(dev["ses"], kind="stable")]: racha = racha + 1 if r <= 0 else 0; mx = max(mx, racha)
    def tr(x): return dict(n=int(len(x["R"])), R_op=float(x["R"].mean()) if len(x["R"]) else None, R_total=float(x["R"].sum()),
                           ic90=_boot_ic(x["ses"], x["R"]), t_ses=_t_ses(x["ses"], x["R"]))
    ho = {k: v[octb] for k, v in h.items()}; hn = {k: v[nov] for k, v in h.items()}
    dias = (int(str(dev["ses"].max())[:4]) * 12 + int(str(dev["ses"].max())[4:6])) - (int(str(dev["ses"].min())[:4]) * 12 + int(str(dev["ses"].min())[4:6])) + 1
    return dict(cid=cid, familia=familia(cid), sensor=sp["sensor"], ejecucion=sp.get("ejecucion") or sp["sensor"],
                futuro=(sp.get("ejecucion") or sp["sensor"]) in FUTUROS, desc=tr(d["desc"]), rep=tr(d["rep"]), dev=tr(dev), oct=tr(ho),
                _nov=tr(hn), nov_disponible=bool((sp.get("ejecucion") or sp["sensor"]) in {"NQ", "ES", "YM"} and sp["sensor"] in {"NQ", "ES", "YM"}),
                friccion_R=float(np.nanmean(frR)), R_dev_fric15=float((dev["R"] - 0.5 * frR).mean()), R_dev_fric20=float((dev["R"] - frR).mean()),
                sin_top5=float(srt[:-5].sum()) if len(srt) > 5 else None, meses_pos=float(np.mean([v > 0 for v in meses.values()])),
                meses_dev={str(k): float(v) for k, v in meses.items()}, pct_oct_en_meses_dev=float(np.mean([v < ho["R"].sum() for v in meses.values()])),
                dd_R=float((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()) if len(eq) else 0.0, racha_perdedora=int(mx),
                ops_mes=float(len(dev["R"]) / max(dias, 1)), _dev_diario=dict(zip(*[a.tolist() for a in _sesion(dev["ses"], dev["R"])])),
                **micros(sp.get("ejecucion") or sp["sensor"], dev["R"], dev["riesgo"], fr_pts))


MICRO = {"NQ": "MNQ", "ES": "MES", "YM": "MYM", "GC": "MGC"}


def micros(ejec, R, riesgo, fr_mini):
    """Ejecutabilidad en una prop de 50K (descriptivo, no elige): R si se opera en micros (fricción canónica del micro, comisión máxima y
    mínima entre las firmas que admiten algoritmos) y qué parte de las operaciones se puede dimensionar con micros enteros a 100 USD por R."""
    from edgelab import costos as C
    m = MICRO.get(ejec)
    if not m: return {}
    usd_pt = C.tick_value_usd(m) / C.tick_size(m)
    out = {f"R_dev_micro_{c}": float((R - (C.friccion_rt_puntos(m, criterio=c) - fr_mini) / riesgo).mean()) for c in ("max", "min")}
    out["R_dev_mini_min"] = float((R - (C.friccion_rt_puntos(ejec, criterio="min") - fr_mini) / riesgo).mean())
    n = np.floor(100.0 / (riesgo * usd_pt))
    out.update(micro=m, riesgo_usd_por_micro_mediana=float(np.median(riesgo * usd_pt)), frac_dimensionable_100usd=float((n >= 1).mean()))
    return out


def contraer(B):
    """James-Stein hacia 0: m_i * tau2 / (tau2 + se_i^2), tau2 = max(0, var(m) - mean(se^2)) entre reglas."""
    m = np.array([b["dev"]["R_op"] for b in B]); n = np.array([b["dev"]["n"] for b in B])
    sd = np.array([np.std(list(b["_dev_diario"].values()), ddof=1) / max(np.sqrt(b["dev"]["n"] / max(len(b["_dev_diario"]), 1)), 1e-9) for b in B])
    se2 = (sd ** 2) / n; tau2 = max(0.0, float(np.var(m, ddof=1) - se2.mean()))
    for b, mi, s in zip(B, m, se2): b["R_contraido"] = float(mi * tau2 / (tau2 + s)) if tau2 > 0 else 0.0
    return tau2


def _corr(a, b):
    ks = sorted(set(a) | set(b)); x = np.array([a.get(k, 0.0) for k in ks]); y = np.array([b.get(k, 0.0) for k in ks])
    return float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else 0.0


def elegibles(B):
    for b in B:
        o = b["oct"]; e = dict(E1=b["dev"]["n"] >= 40 and (b["desc"]["R_op"] or 0) > 0 and (b["rep"]["R_op"] or 0) > 0, E2=b["friccion_R"] <= 0.08,
                                E3=(b["sin_top5"] or 0) > 0, E4=b["meses_pos"] >= 0.55, E5=o["n"] < 3 or o["t_ses"] is None or o["t_ses"] >= -1.64, E6=b["futuro"])
        b["criterios"] = e; b["elegible"] = all(v for k, v in e.items() if k != "E6")
    return B


def armar(B, futuro=True):
    cand = sorted([b for b in B if b["elegible"] and b["futuro"] == futuro], key=lambda b: -b["R_contraido"]); sel = []
    for b in cand:
        if len(sel) >= 10: break
        if sum(s["familia"] == b["familia"] for s in sel) >= 2: b["descarte"] = "ya hay 2 de su familia"; continue
        c = max([_corr(b["_dev_diario"], s["_dev_diario"]) for s in sel], default=0.0)
        if c > 0.5: b["descarte"] = f"correlación {c:.2f} con una elegida"; continue
        sel.append(b)
    return [s["cid"] for s in sel]


def seleccion():
    U = universo(); B, falta = [], []
    for r in U:
        m = metricas(r["cid"], r["spec"])
        (B.append(m) if m else falta.append(r["cid"]))
    if falta: print("faltan datos de:", falta)
    tau2 = contraer(B); elegibles(B)
    S = dict(regla="PREREGISTRO.md §5", corte=CORTE_OCT, tau2=tau2, futuros=armar(B, True), cfd=armar(B, False), sin_datos=falta)
    pub = [{k: v for k, v in b.items() if not k.startswith("_")} for b in B]
    (DIR / "BATERIA.json").write_text(json.dumps(dict(reglas=pub, tau2=tau2), indent=1, default=float))
    (DIR / "SELECCION.json").write_text(json.dumps(S, indent=1)); print(json.dumps(S, indent=1))
    corr = {a["cid"]: {b["cid"]: round(_corr(a["_dev_diario"], b["_dev_diario"]), 2) for b in B} for a in B}
    (DIR / "CORRELACION_DEV.json").write_text(json.dumps(corr, indent=1))


def _commiteado(p):
    r = subprocess.run(["git", "status", "--porcelain", str(p)], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    c = subprocess.run(["git", "log", "-1", "--format=%H", "--", str(p)], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return bool(c) and not r


def _serie_hold(cids, desde, hasta):
    """R por sesión válida de la cartera en [desde, hasta]: suma de R de las elegidas (0 si no operan)."""
    U = {r["cid"]: r for r in universo()}; dias, por = set(), {}
    for c in cids:
        h = _ops(c, "hold"); ok = _validas_hold(U[c]["spec"])
        for s, x in zip(h["ses"], h["R"]):
            if desde <= s <= hasta and ok(s): por[s] = por.get(s, 0.0) + x
        dias |= {int(s) for s in h["ses"] if desde <= s <= hasta}
    return por


def noviembre():
    S = DIR / "SELECCION.json"
    if not _commiteado(S): raise SystemExit("SELECCION.json no está commiteado (o tiene cambios): §5 exige commitearlo antes de mirar noviembre")
    sel = json.loads(S.read_text())["futuros"]
    from edgelab.holdout import sesion_excluida
    U = {r["cid"]: r for r in universo()}
    nov_ses = sorted({int(s) for c in sel for s in _ops(c, "hold")["ses"] if s >= NOV0} |
                     {d for d in (20261102, 20261103, 20261104, 20261105, 20261106, 20261109, 20261110, 20261111, 20261112, 20261113)})
    nov_ses = [d for d in nov_ses if not any(sesion_excluida(i, d) for i in ("NQ", "ES", "YM"))]
    p_nov = _serie_hold(sel, NOV0, 20261113); x = np.array([p_nov.get(d, 0.0) for d in nov_ses])
    oct_ses = sorted({int(s) for c in sel for s in _ops(c, "hold")["ses"] if s <= CORTE_OCT})
    p_all = _serie_hold(sel, 20261001, 20261113); y = np.array([p_all.get(d, 0.0) for d in sorted(set(oct_ses) | set(nov_ses))])
    rng = np.random.default_rng(20261116)
    def prueba(v):
        if len(v) < 2: return dict(n_ses=int(len(v)))
        Z = (rng.choice((-1.0, 1.0), size=(20000, len(v))) * v).mean(1)
        return dict(n_ses=int(len(v)), media_R_sesion=float(v.mean()), R_total=float(v.sum()), t=float(v.mean() / v.std(ddof=1) * np.sqrt(len(v))) if v.std(ddof=1) > 0 else None,
                    p_signo=float((1 + (Z >= v.mean()).sum()) / 20001))
    pn, pa = prueba(x), prueba(y)
    color = "ROJO" if (pa.get("t") is not None and pa["t"] < -1.64) else ("VERDE" if pn.get("media_R_sesion", 0) > 0 and pa.get("media_R_sesion", 0) > 0 else "AMARILLO")
    por_regla = {}
    for c in json.loads(S.read_text())["futuros"] + json.loads(S.read_text())["cfd"] + [r["cid"] for r in universo()]:
        if c in por_regla: continue
        h = _ops(c, "hold")
        if h is None: continue
        ok = _validas_hold(U[c]["spec"]); m = np.array([ok(s) and s >= NOV0 for s in h["ses"]], bool) if len(h["ses"]) else np.zeros(0, bool)
        por_regla[c] = dict(n=int(m.sum()), R_total=float(h["R"][m].sum()), R_op=float(h["R"][m].mean()) if m.any() else None)
    out = dict(seleccion=sel, sesiones_nov=nov_ses, noviembre=pn, holdout_completo=pa, lectura=color, por_regla_nov=por_regla,
               e_procesos=e_procesos(sel))
    (DIR / "NOVIEMBRE.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps({k: out[k] for k in ("noviembre", "holdout_completo", "lectura")}, indent=1))


def e_procesos(cids):
    """e-proceso por regla sobre TODO el holdout (oct + nov), H0: E[R] <= 0; cotas declaradas: R en [-3, 12] por operación."""
    from edgelab.funnel.secuencial import EProceso
    U = {r["cid"]: r for r in universo()}; out = {}
    for c in cids:
        h = _ops(c, "hold"); ok = _validas_hold(U[c]["spec"]); E = EProceso(mu0=0.0, piso=-3.0, techo=12.0)
        viol, n = False, 0
        for s, x in sorted(zip(h["ses"], h["R"])):
            if not ok(s): continue
            if not -3.0 <= x <= 12.0: viol = True; break
            E.agregar(float(x)); n += 1
        out[c] = dict(n=n, e=float(E.e_valor), limite_violado=viol)
    return out


def _usd_diario(cids, tramos, usd_R, desde=0, hasta=99999999):
    """USD por sesión con micros enteros: n = max(1, round(usd_R / riesgo de 1 micro)); se salta la operación si 1 micro arriesga más
    de 2 × usd_R (no se puede dimensionar). P&L = R × riesgo realizado (n micros)."""
    from edgelab import costos as C
    U = {r["cid"]: r for r in universo()}; d, salt, tot = {}, 0, 0
    for c in cids:
        sp = U[c]["spec"]; m = MICRO[sp.get("ejecucion") or sp["sensor"]]; usd_pt = C.tick_value_usd(m) / C.tick_size(m)
        ok = _validas_hold(sp)
        for t in tramos:
            o = _ops(c, t)
            for s, x, rg in zip(o["ses"], o["R"], o["riesgo"]):
                if not desde <= s <= hasta or (t == "hold" and not ok(s)): continue
                tot += 1; r1 = rg * usd_pt
                if r1 > 2 * usd_R: salt += 1; continue
                n = max(1, round(usd_R / r1)); d[int(s)] = d.get(int(s), 0.0) + x * n * r1
    return d, salt, tot


def prop():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ep", ROOT / "docs/research/canasta_7_20261030/estimar_propfirm.py"); ep = importlib.util.module_from_spec(spec); spec.loader.exec_module(ep)
    S = json.loads((DIR / "SELECCION.json").read_text())["futuros"]; B = {b["cid"]: b for b in json.loads((DIR / "BATERIA.json").read_text())["reglas"]}
    import pandas as pd
    con = sorted({int(s) for c in S for t in ("desc", "rep") for s in _ops(c, t)["ses"]})
    ses = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(str(max(con[0], 20250805)), str(con[-1]))]   # todas las sesiones (0 si no opera)
    contr = sum(B[c]["R_contraido"] / max(B[c]["dev"]["R_op"], 1e-9) for c in S) / len(S)       # factor medio de contracción
    out = dict(seleccion=S, sesiones_dev=len(ses), sesiones_con_ops=len(con), factor_contraccion=float(contr), por_usd_R={})
    c50 = ep.CUENTAS["50K"]
    for usd in (100, 200, 300, 400):
        d, salt, tot = _usd_diario(S, ("desc", "rep"), usd)
        x = np.array([d.get(s, 0.0) for s in ses])
        r = dict(usd_sesion_media=float(x.mean()), usd_sesion_sd=float(x.std(ddof=1)), saltadas=f"{salt}/{tot}", res=ep.res(x))
        for k, mu in (("media_dev", x.mean()), ("media_contraida", x.mean() * contr), ("azar_0", 0.0)):
            pasa, quema = ep.sim(x, c50, mu=mu); r[k] = dict(pasa=float(pasa), quema=float(quema))
        out["por_usd_R"][usd] = r
    (DIR / "PROP.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"seleccion": seleccion, "noviembre": noviembre, "prop": prop}[sys.argv[1]]()

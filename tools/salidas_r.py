#!/usr/bin/env python3
"""Políticas de salida y filtros comunes en R (docs/research/programa_r_20261103/PREREGISTRO_SALIDAS_Y_FILTROS.md), evaluados OFFLINE
sobre las trayectorias (etapa TRAYECTORIAS). Motor por vela, conservador: si en una vela se alcanzan stop y salida favorable, gana el
stop; salidas por tiempo al cierre; un stop más corto re-denomina el R con el riesgo nuevo. Elige en DESC (cota inferior del IC90
de la diferencia emparejada contra la base, bootstrap por sesiones) y prueba una vez en réplica.
  python tools/salidas_r.py analizar
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
D = ROOT / "docs/research/programa_r_20261103"


def politicas() -> dict:
    P = {"base": {}}
    for n in (15, 30, 60, 120): P[f"tiempo{n}"] = dict(tiempo=n)
    for t in (0.5, 1, 1.5, 2, 3): P[f"objetivo{t}"] = dict(objetivo=t)
    for b in (0.5, 1): P[f"be{b}"] = dict(be=b)
    for a, d in ((1, 0.5), (1, 1), (2, 1)): P[f"trail{a}-{d}"] = dict(trail=(a, d))
    for s in (0.5, 0.75): P[f"stop{s}"] = dict(stop=s)
    for t in (1, 1.5, 2): P[f"objetivo{t}+be0.5"] = dict(objetivo=t, be=0.5)
    for n in (30, 60): P[f"tiempo{n}+be1"] = dict(tiempo=n, be=1)
    P["trail1-0.5+tiempo120"] = dict(trail=(1, 0.5), tiempo=120)
    for t in (1, 2):
        for s in (0.5, 0.75): P[f"objetivo{t}+stop{s}"] = dict(objetivo=t, stop=s)
    for n in (30, 60): P[f"tiempo{n}+objetivo1.5"] = dict(tiempo=n, objetivo=1.5)
    return P


def simular(tr: dict, pol: dict) -> float:
    """R neto de una operación bajo la política (unidades del riesgo efectivo)."""
    f, a, c = (np.asarray(tr[k], float) for k in ("f", "a", "c"))
    s = float(pol.get("stop", 1.0)); stop = -s; obj = float(pol.get("objetivo", tr["objetivo_R"])); n = len(c)
    fin = min(n, int(pol.get("tiempo", n))); be = pol.get("be"); tr_ = pol.get("trail"); mfe = -np.inf; salida = None
    for j in range(fin):
        if a[j] <= stop: salida = stop; break                      # conservador: el stop primero
        if f[j] >= obj: salida = obj; break
        mfe = max(mfe, f[j])
        if be is not None and mfe >= be: stop = max(stop, 0.0)
        if tr_ is not None and mfe >= tr_[0]: stop = max(stop, mfe - tr_[1])
    if salida is None: salida = c[fin - 1]
    return float(salida / s - tr["friccion_R"] / s)


def cargar(tramo: str) -> list:
    T = []
    for f in sorted((D / "trayectorias").glob(f"*__{tramo}.json")):
        for t in (json.loads(f.read_text()).get("trayectorias") or []): T.append(dict(t, regla=f.name.split("__")[0]))
    return T


def franja(t_s: float) -> str:
    h = (t_s % 86400) / 3600
    return "asia" if (h >= 22 or h < 7) else ("europa" if h < 13.5 else "eeuu")


def _boot_dif(dif, ses, B=4000, seed=20261103):
    import pandas as pd
    g = pd.DataFrame(dict(d=dif, s=ses)).groupby("s").d.agg(["sum", "count"]); k = len(g)
    i = np.random.default_rng(seed).integers(0, k, (B, k)); m = g["sum"].to_numpy()[i].sum(1) / g["count"].to_numpy()[i].sum(1)
    return float(np.percentile(m, 5)), float(np.percentile(m, 95)), float((m <= 0).mean())


def evaluar(T, P):
    ses = np.array([t["ses"] for t in T]); base = np.array([simular(t, {}) for t in T]); out = {}
    for k, p in P.items():
        x = np.array([simular(t, p) for t in T]); d = x - base; lo, hi, pv = _boot_dif(d, ses)
        por = {}
        for r in sorted({t["regla"] for t in T}):
            m = np.array([t["regla"] == r for t in T]); por[r] = dict(n=int(m.sum()), R=float(x[m].mean()), dif=float(d[m].mean()))
        out[k] = dict(n=len(x), R=float(x.mean()), dif=float(d.mean()), ic90_dif=[lo, hi], p=pv, por_regla=por)
    return out, base


def filtros(T, base):
    ses = np.array([t["ses"] for t in T]); out = {}
    fr = np.array([franja(t["t"]) for t in T]); lado = np.array([t["lado"] for t in T])
    for nombre, m in [(f"sin_{z}", fr != z) for z in ("asia", "europa", "eeuu")] + [("solo_compras", lado == 1), ("solo_ventas", lado == -1)]:
        d = np.where(m, base, 0.0) - base                             # excluir = no operar (R 0)
        lo, hi, pv = _boot_dif(-np.where(m, 0.0, base), ses)          # mejora = −(R de lo excluido)
        out[nombre] = dict(n_quedan=int(m.sum()), R_quedan=float(base[m].mean()) if m.any() else None, R_excluidas=float(base[~m].mean()) if (~m).any() else None,
                           mejora_media=float(-np.where(m, 0.0, base).mean()), ic90=[lo, hi], p=pv)
    return out


def analizar():
    P = politicas(); res = {}
    Td = cargar("desc"); ev, base = evaluar(Td, P); fi = filtros(Td, base)
    mejor = max((k for k in ev if k != "base"), key=lambda k: ev[k]["ic90_dif"][0])
    mejor_f = max(fi, key=lambda k: fi[k]["ic90"][0])
    res["desc"] = dict(n=len(Td), politicas=ev, filtros=fi, elegida=mejor, filtro_elegido=mejor_f)
    Tr = cargar("rep")
    if Tr:
        evr, baser = evaluar(Tr, {"base": {}, mejor: P[mejor]}); fir = filtros(Tr, baser)
        p1, p2 = evr[mejor]["p"], fir[mejor_f]["p"]; ps = sorted([p1, p2])
        holm = {mejor: min(1, p1 * (2 if p1 == ps[0] else 1)), mejor_f: min(1, p2 * (2 if p2 == ps[0] else 1))}
        res["rep"] = dict(n=len(Tr), politica=evr[mejor], filtro=fir[mejor_f], holm=holm,
                          confirmada_politica=bool(evr[mejor]["dif"] > 0 and holm[mejor] < 0.05),
                          confirmado_filtro=bool(fir[mejor_f]["mejora_media"] > 0 and holm[mejor_f] < 0.05))
    (D / "SALIDAS_RESULTADO.json").write_text(json.dumps(res, indent=1, default=float)); return res


if __name__ == "__main__":
    r = analizar(); print("politicas", len(politicas()) - 1, "| DESC n", r["desc"]["n"], "| elegida", r["desc"]["elegida"], "| filtro", r["desc"]["filtro_elegido"])

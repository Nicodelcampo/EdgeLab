"""Kernel de Kaggle: gestión del tamaño de carteras en cuentas LucidFlex (pre-registro
docs/research/cartera_nt8_20261125/PREREGISTRO_MULTIACTIVO_Y_GESTION.md, Parte B). Lo arma y lanza tools/kaggle_cartera_gestion.py.

Entrada: MATRIZ_DIARIA_1MICRO.csv.gz (P&L diario por estrategia a 1 micro, costos canónicos, motor EdgeLabCartera en modo broker).
Bootstrap por bloques de 10 sesiones del vector diario conjunto; reglas oficiales de LucidFlex (EOD trailing, piso que se fija,
consistencia en evaluación, pérdida diaria, retiros); políticas: asignación (EQ, INV_VOL, HRP), contratos base k, tamaño dinámico
(fijo, colchón Grossman–Zhou, escalón al fijarse el piso, escalón con colchón alto), freno diario de la cuenta, tope diario en
evaluación. Tres medias (desarrollo, contraída 0,5, cero) y tres muestras (todo, 2019-07→2023-12, 2024-01→2026-09).
Además, el rescate de la 25K desde su estado actual con subconjuntos de la cartera.
"""
import glob
import itertools
import json
import os
import time

import numpy as np
import pandas as pd
from numba import njit

T0 = time.time()
def _leer(nombre):
    f = [x for x in sorted(glob.glob(f"/kaggle/input/**/{nombre}*", recursive=True)) if os.path.isfile(x)
         and os.path.basename(x).split(".")[0] == nombre] or sorted(glob.glob(nombre + "*"))
    print("entrada:", f[0], flush=True)
    return pd.read_csv(f[0], index_col=0, parse_dates=True)


# iteracion 2 (auditoria): resultado de cierre y MINIMO INTRADIA por sesion CME (el piso de Lucid y los frenos actuan dentro del
# dia). El minimo de la cartera se toma como la suma de minimos por estrategia (cota conservadora); C2_VZ (de varios dias) usa
# min(cierre, 0). Se publica tambien la simulacion solo con cierres (optimista) para comparar.
C1 = _leer("MATRIZ_DIARIA_CIERRE_1MICRO"); N1 = _leer("MATRIZ_DIARIA_MIN_1MICRO"); OLD = _leer("MATRIZ_DIARIA_1MICRO")
for c in ("C2VZ_NQ", "C2VZ_ES"):
    C1[c] = OLD[c].reindex(C1.index).fillna(0.0); N1[c] = np.minimum(C1[c], 0.0)
M = C1; MN = N1
BASE = ["T_NQ", "R_NQ", "Z_NQ", "V_NQ", "RQ5_NQ", "FR_NQ", "RQ5_ES", "ES5N_ES"]
INTER = BASE + ["C2VZ_NQ", "C2VZ_ES"]
N_PATHS = int(os.environ.get("N_PATHS", "20000"))
OUT = "/kaggle/working" if os.path.isdir("/kaggle/working") else "."

# precio, objetivo, MLL, umbral del piso fijo, DLL de la cuenta, retiro max, dia min, tope micros, consistencia evaluacion
CUENTAS = {"25K": (45.5, 1250.0, 1000.0, 1100.0, 600.0, 1000.0, 100.0, 20, 0.4),
           "50K": (95.2, 3000.0, 2000.0, 2100.0, 1200.0, 2000.0, 150.0, 40, 0.4),
           "150K": (214.25, 9000.0, 4500.0, 4600.0, 2700.0, 3000.0, 250.0, 100, 0.4)}


# ----------------------------------------------------------------------------------------------- asignacion causal trimestral
def hrp_pesos(ret: pd.DataFrame) -> np.ndarray:
    try:                                       # scipy existe en Kaggle; no está en el entorno local de CLAUDE.md
        from scipy.cluster.hierarchy import linkage, leaves_list
        from scipy.spatial.distance import squareform
    except ImportError:
        raise SystemExit("HRP necesita scipy (correr en Kaggle)")
    c = ret.corr().fillna(0).to_numpy(copy=True); np.fill_diagonal(c, 1.0)
    v = ret.var().to_numpy(copy=True); v[v <= 0] = np.nanmean(v[v > 0]) if (v > 0).any() else 1.0
    d = np.sqrt(np.clip(0.5 * (1 - c), 0, 1)); np.fill_diagonal(d, 0)
    orden = leaves_list(linkage(squareform(d, checks=False), "single"))
    w = np.ones(len(v)); grupos = [list(orden)]
    cov = ret.cov().to_numpy(copy=True)
    while grupos:
        g = grupos.pop()
        if len(g) <= 1: continue
        a, b = g[: len(g) // 2], g[len(g) // 2:]
        def var_cl(ix):
            cc = cov[np.ix_(ix, ix)]; iv = 1 / np.clip(np.diag(cc), 1e-9, None); iv /= iv.sum()
            return float(iv @ cc @ iv)
        va, vb = var_cl(a), var_cl(b); al = 1 - va / (va + vb)
        w[a] *= al; w[b] *= 1 - al
        grupos += [a, b]
    return w


def contratos_diarios(cols, alloc: str, k: int) -> np.ndarray:
    X = M[cols]; n = np.ones((len(X), len(cols)))
    trims = pd.date_range(X.index[0], X.index[-1], freq="QS")
    for t0 in trims:
        hist = X[(X.index < t0) & (X.index >= t0 - pd.DateOffset(months=12))]
        sel = (X.index >= t0) & (X.index < t0 + pd.DateOffset(months=3))
        if alloc == "EQ" or len(hist) < 120:
            w = np.ones(len(cols))
        elif alloc == "INV_VOL":
            sd = hist.std().values; w = 1 / np.where(sd > 0, sd, np.nan); w = np.nan_to_num(w / np.nanmean(w), nan=1.0)
        else:
            w = hrp_pesos(hist); w = w / w.mean()
        w = np.clip(w, 0.25, 2.0)
        n[sel] = np.maximum(1, np.round(k * w))
    return n


# ----------------------------------------------------------------------------------------------- simulacion de la cuenta
@njit(cache=True)
def sim(y, ymin, intr, nsum, N, seed, precio, obj, mll, lock, dll, cap, dmin, tope, cons, dyn, guard, capdia, bal0, maxc0, piso0, solo_eval, max_dias):
    np.random.seed(seed); L = len(y)
    pasa = np.zeros(N); pagos = np.zeros(N); cob = np.zeros(N); dias = np.zeros(N); quiebra = np.zeros(N)
    for k in range(N):
        pos = np.random.randint(L); paso = 0
        bal = bal0; piso = piso0; maxc = maxc0; mayor = 0.0; ganado = 0.0; d = 0; ok = False
        while d < max_dias:
            if paso % 10 == 0: pos = np.random.randint(L)
            j = (pos + paso % 10) % L; paso += 1
            colchon = bal - piso
            m = 1.0
            if dyn == 1: m = max(1.0, np.floor(colchon / (0.5 * mll)))
            elif dyn == 3: m = 2.0 if colchon >= 0.75 * mll else 1.0
            mmax = max(1.0, np.floor(tope / max(nsum, 1.0)))
            if m > mmax: m = mmax
            p = y[j] * m; pm = min(ymin[j] * m, p, 0.0)
            lim = 0.0
            if guard > 0: lim = guard
            if dll > 0 and (lim == 0.0 or dll < lim): lim = dll
            if intr == 1:
                if lim > 0 and pm <= -lim: p = -lim; pm = -lim
            else:
                if lim > 0 and p < -lim: p = -lim
                pm = min(p, 0.0)
            if capdia > 0 and p > capdia: p = capdia
            if bal + pm <= piso: quiebra[k] = 1.0; break
            bal += p; d += 1
            if p > mayor: mayor = p
            if bal > maxc: maxc = bal
            piso = min(max(piso, maxc - mll), 100.0)
            ganancia = bal                      # relativo al saldo inicial de la cuenta
            if ganancia >= obj and mayor <= cons * ganancia: ok = True; break
        dias[k] = d
        if not ok: continue
        pasa[k] = 1.0
        if solo_eval: continue
        bal = 0.0; piso = -mll; maxc = 0.0; c0 = 0.0; dok = 0; f = 0; npg = 0; tot = 0.0; fijo = False
        while f < max_dias and npg < 5:
            if paso % 10 == 0: pos = np.random.randint(L)
            j = (pos + paso % 10) % L; paso += 1
            colchon = bal - piso
            m = 1.0
            if dyn == 1: m = max(1.0, np.floor(colchon / (0.5 * mll)))
            elif dyn == 2: m = 2.0 if fijo else 1.0
            elif dyn == 3: m = 2.0 if colchon >= 0.75 * mll else 1.0
            mmax = max(1.0, np.floor(tope / max(nsum, 1.0)))
            if m > mmax: m = mmax
            p = y[j] * m; pm = min(ymin[j] * m, p, 0.0)
            lim = 0.0
            if guard > 0: lim = guard
            if dll > 0 and (lim == 0.0 or dll < lim): lim = dll
            if intr == 1:
                if lim > 0 and pm <= -lim: p = -lim; pm = -lim
            else:
                if lim > 0 and p < -lim: p = -lim
                pm = min(p, 0.0)
            if bal + pm <= piso: break
            bal += p; f += 1
            if p >= dmin: dok += 1
            if bal > maxc: maxc = bal
            if piso < 100.0:
                if maxc > lock: piso = 100.0; fijo = True
                else: piso = max(piso, maxc - mll)
            monto = min(cap, 0.5 * bal)
            if dok >= 5 and bal > c0 and monto >= 500.0:
                tot += 0.9 * monto; bal -= monto; npg += 1; piso = 100.0; fijo = True; c0 = bal; dok = 0
        cob[k] = tot; pagos[k] = npg; dias[k] += f
    return pasa, pagos, cob, dias, quiebra


MUESTRAS = {"todo": (M.index[0], M.index[-1]), "H1": (pd.Timestamp("2019-07-01"), pd.Timestamp("2023-12-31")),
            "H2": (pd.Timestamp("2024-01-01"), M.index[-1])}


def correr(serie: np.ndarray, smin: np.ndarray, idx, nsum, cta, dyn, guard_usd, capdia_on, extra=None):
    precio, obj, mll, lock, dll, cap, dmin, tope, cons = CUENTAS[cta]
    out = {}
    for mn, (a, b) in MUESTRAS.items():
        sel = (idx >= a) & (idx <= b); x = serie[sel]; xm = smin[sel]
        for mu_nom, f in (("dev", 1.0), ("contraida", 0.5), ("cero", 0.0)):
          for intr in (1, 0):
            if mn != "todo" and (mu_nom != "contraida" or intr == 0): continue
            sh = (f - 1.0) * x.mean(); y = x + sh; ym = xm + sh
            bal0, maxc0, piso0, solo = (0.0, 0.0, -mll, False) if extra is None else extra
            pa, pg, cb, di, qb = sim(y, ym, intr, nsum, N_PATHS, 7, precio, obj, mll, lock, dll, cap, dmin, tope, cons, dyn,
                                     guard_usd, (cons * obj - 1) if capdia_on else 0.0,
                                     bal0, maxc0, piso0, solo, 250)
            out[f"{mn}|{mu_nom}" + ("" if intr == 1 else "|cierre")] = dict(pasa=float(pa.mean()), cobra=float((pg > 0).mean()), retiros=float(pg.mean()),
                                         ev=float(cb.mean() - precio), p_ganar=float((cb > precio).mean()), dias=float(di.mean()),
                                         quiebra=float(qb.mean()))
    return out


res = {"n_paths": N_PATHS, "cuentas": CUENTAS, "gestion": {}, "rescate": {}}
idx = M.index
for comp_nom, cols in (("INTRADIA8", BASE), ("INTERDIA10", INTER)):
    for alloc in ("EQ", "INV_VOL", "HRP"):
        for kk in (1, 2, 3, 4):
            n = contratos_diarios(cols, alloc, kk)
            serie = (M[cols].values * n).sum(axis=1)
            smin = (MN[cols].values * n).sum(axis=1)
            nsum = float(n[-1].sum())
            for cta in CUENTAS:
                if comp_nom == "INTERDIA10" and cta != "150K": continue
                if n.sum(axis=1).max() > CUENTAS[cta][7]: continue
                for dyn in (0, 1, 2, 3):
                    for gfrac in (0.0, 0.5):
                        for capd in (False, True):
                            key = f"{comp_nom}|{cta}|{alloc}|k{kk}|dyn{dyn}|freno{gfrac}|tope{int(capd)}"
                            res["gestion"][key] = correr(serie, smin, idx, nsum, cta, dyn, gfrac * CUENTAS[cta][2], capd)
            print(comp_nom, alloc, kk, round(time.time() - T0), "s", flush=True)

# rescate de la 25K: saldo 24.270 (rel -730), mejor cierre 25.000 (rel 0), piso 24.000 (rel -1000); solo evaluacion
for r in (1, 2, len(BASE)):
    for comb in itertools.combinations(BASE, r):
        if r == len(BASE) and comb != tuple(BASE): continue
        serie = M[list(comb)].values.sum(axis=1); smin = MN[list(comb)].values.sum(axis=1)
        for guard in (0.0, 120.0, 250.0):
            for capd in (False, True):
                key = f"{'+'.join(comb)}|freno{int(guard)}|tope{int(capd)}"
                res["rescate"][key] = correr(serie, smin, idx, float(len(comb)), "25K", 0, guard, capd,
                                             extra=(-730.0, 0.0, -1000.0, True))
print("rescate listo", round(time.time() - T0), "s", flush=True)
json.dump(res, open(os.path.join(OUT, "RESULTADOS_GESTION.json"), "w"), indent=0)
print("FIN", round(time.time() - T0), "s")

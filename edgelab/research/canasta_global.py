"""CANASTA-GLOBAL (2026-11-08, regla global de Nico, docs/DECISIONES_20261108.md): canasta de reglas estables, poco correlacionadas
y de varios activos elegida entre TODAS las celdas de los 106 cubos, con el nulo que repite la selección completa.
Pre-registro: docs/research/canasta_global_20261108/PREREGISTRO.md. Mismo criterio que `tools/canasta_orb.py`, en flujo.

Por cubo (uno por vez): matriz diaria por bloque (sesiones del bloque × celdas con >= MIN_OPS operaciones en la ventana) y, para las
B+1 series de signos (fila 0 = observado), sumas por bloque con un producto matricial. Una celda es estable si su media es > 0 en al
menos 4 de los 5 bloques y su t diario (sobre todas las sesiones de la ventana, 0 los días sin operar) es > 1. Se guardan las
TOP_POR_CUBO estables de mayor t de cada réplica y, en una segunda pasada, sus series diarias. Después, por réplica: orden por t,
correlación < 0,3 con las ya elegidas, como máximo 3 por cubo, hasta 10, al menos 3 instrumentos; estadístico = t de la canasta.
"""
from __future__ import annotations

import numpy as np

from edgelab.research import grilla_masiva as GM

VENTANA = (20250805, 20260930)
N_BLOQUES, MIN_POS, T_MIN, CORR_MAX, MAX_REGLAS, MAX_POR_CUBO, MIN_INST, TOP_POR_CUBO, MIN_OPS = 5, 4, 1.0, 0.3, 10, 3, 3, 20, 30


def _dia_cubo(cubo, dias):
    """Iterador (posición global del día, R por celda evaluable) y el índice de celdas evaluables (>= MIN_OPS en la ventana)."""
    m = (cubo.ses >= VENTANA[0]) & (cubo.ses <= VENTANA[1])
    idx = [cubo.idx[m, j] for j in range(cubo.idx.shape[1])]; ses = cubo.ses[m]; net = cubo.net[m]
    _, _, Ct = GM.tensor(cubo.perillas, idx, net); ev = np.flatnonzero(Ct.ravel() >= MIN_OPS)
    orden = np.argsort(ses, kind="stable"); so = ses[orden]; u = np.unique(so)
    cortes = np.searchsorted(so, u, side="left").tolist() + [len(so)]; pos = np.searchsorted(dias, u)

    def it():
        for q in range(len(u)):
            o = orden[cortes[q]:cortes[q + 1]]
            Sd, _, _ = GM.tensor(cubo.perillas, [ix[o] for ix in idx], net[o]); yield int(pos[q]), Sd.ravel()[ev]
    return it, ev


def candidatos_cubo(cubo, dias, G):
    """Por réplica b: índices (en ev) de las TOP_POR_CUBO estables de mayor t y sus t. G: (B+1, D) signos por día global."""
    it, ev = _dia_cubo(cubo, dias); D = len(dias); E = len(ev); Bp = G.shape[0]
    if E == 0: return ev, [np.zeros(0, np.int64)] * Bp, [np.zeros(0)] * Bp
    bloque = np.minimum((np.arange(D) * N_BLOQUES) // D, N_BLOQUES - 1)
    sumb = np.zeros((N_BLOQUES, Bp, E), np.float32); sq = np.zeros(E)
    filas, buf = [], []
    def vaciar():
        if not filas: return
        P = np.array(filas); S = np.stack(buf).astype(np.float32)
        for k in np.unique(bloque[P]):
            m = bloque[P] == k; sumb[k] += G[:, P[m]].astype(np.float32) @ S[m]
        sq[:] += (S.astype(np.float64) ** 2).sum(0); filas.clear(); buf.clear()
    for p, x in it():
        filas.append(p); buf.append(x)
        if len(filas) >= 40: vaciar()
    vaciar()
    tot = sumb.sum(0)                                                     # (B+1, E)
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = tot / D; var = (sq[None, :] - D * mu ** 2) / (D - 1); t = mu / np.sqrt(var / D)
    estable = ((sumb > 0).sum(0) >= MIN_POS) & (t > T_MIN) & np.isfinite(t)
    top, tt = [], []
    for b in range(Bp):
        j = np.flatnonzero(estable[b])
        j = j[np.argsort(-t[b, j])][:TOP_POR_CUBO]; top.append(j); tt.append(t[b, j])
    return ev, top, tt


def series_cubo(cubo, dias, columnas):
    """Series diarias (D × len(columnas)) sin signo de las celdas pedidas (índices en ev)."""
    it, ev = _dia_cubo(cubo, dias); X = np.zeros((len(dias), len(columnas)), np.float32)
    if len(columnas):
        for p, x in it(): X[p] = x[columnas]
    return X


def elegir(cands, series, G_b):
    """cands: lista de (t, cubo, instrumento, clave); series: clave -> serie sin signo; G_b: signos (D,). Devuelve (elegidas, t)."""
    el, por_cubo, Xs = [], {}, []
    for t, cu, inst, k in sorted(cands, key=lambda c: -c[0]):
        if por_cubo.get(cu, 0) >= MAX_POR_CUBO: continue
        x = series[k] * G_b
        if any(abs(np.corrcoef(x, y)[0, 1]) >= CORR_MAX if np.std(x) > 0 and np.std(y) > 0 else False for y in Xs): continue
        el.append((cu, inst, k)); Xs.append(x); por_cubo[cu] = por_cubo.get(cu, 0) + 1
        if len(el) == MAX_REGLAS: break
    if len({i for _, i, _ in el}) < MIN_INST: return [], 0.0
    c = np.mean(Xs, axis=0); s = c.std(ddof=1)
    return el, float(c.mean() / (s / np.sqrt(len(c)))) if s > 0 else 0.0


def signos(dias, B, seed=20261108):
    rng = np.random.default_rng(seed); G = np.ones((B + 1, len(dias))); G[1:] = rng.choice([-1.0, 1.0], size=(B, len(dias)))
    return G


def procesar(fuentes, dias, B=200, seed=20261108, log=None):
    """Una tanda de cubos (2026-11-08: en paralelo, una tanda por kernel). Devuelve lo necesario para combinar: candidatas por
    réplica y series diarias sin signo de su unión. Los días y la semilla deben ser los mismos en todas las tandas."""
    G = signos(dias, B, seed); out = []
    for n, (nombre, inst, f) in enumerate(fuentes):
        cubo = f(); ev, top, tt = candidatos_cubo(cubo, dias, G)
        union = np.unique(np.concatenate(top)) if any(len(x) for x in top) else np.zeros(0, np.int64)
        out.append(dict(nombre=nombre, instrumento=inst, ev=ev[union] if len(union) else np.zeros(0, np.int64), union=union,
                        series=series_cubo(cubo, dias, union), top=[np.searchsorted(union, x) for x in top], tt=tt,
                        perillas=[q.nombre for q in cubo.perillas]))
        if log: log(f"cubo {n + 1}/{len(fuentes)} {nombre} evaluables {len(ev)} candidatas obs {len(top[0])}")
        del cubo
    return out


def combinar(partes, dias, B=200, seed=20261108, completo=True):
    """Selección global sobre las tandas disponibles. Con `completo=False` (tandas parciales) informa la canasta observada sin p."""
    G = signos(dias, B, seed); por_rep = [[] for _ in range(B + 1)]; series = {}; meta = {}
    for c in partes:
        for i in range(len(c["union"])): series[(c["nombre"], i)] = c["series"][:, i].astype(float)
        meta[c["nombre"]] = c
        for b in range(B + 1): por_rep[b] += [(float(tv), c["nombre"], c["instrumento"], (c["nombre"], int(j))) for j, tv in zip(c["top"][b], c["tt"][b])]
    obs, t_obs = elegir(por_rep[0], series, G[0])
    if completo:
        nul = [elegir(por_rep[b], series, G[b])[1] for b in range(1, B + 1)]
        p = float((1 + sum(x >= t_obs for x in nul)) / (B + 1)) if obs else 1.0; q = np.quantile(nul, [.5, .9, .95]).tolist()
    else: p, q = None, None
    reglas = []
    for cu, inst, (nm, j) in obs:
        x = series[(nm, j)]
        reglas.append(dict(cubo=nm, instrumento=inst, celda_plana=int(meta[nm]["ev"][j]), perillas=meta[nm]["perillas"], media_diaria=float(x.mean()),
                           medias_bloques=[float(b.mean()) for b in np.array_split(x, N_BLOQUES)]))
    c = np.mean([series[k] for _, _, k in obs], axis=0) if obs else np.zeros(len(dias))
    return dict(reglas=reglas, t_canasta=t_obs, p_seleccion=p, B=B, sesiones=len(dias), cubos=len(partes), completo=completo,
                media_diaria_canasta=float(c.mean()), medias_bloques_canasta=[float(b.mean()) for b in np.array_split(c, N_BLOQUES)],
                nulo_q50_q90_q95=q, serie_canasta=[float(v) for v in c], dias=[int(d) for d in dias])


def dias_de(fuentes):
    d = set()
    for _, _, f in fuentes:
        s = f().ses; d |= set(s[(s >= VENTANA[0]) & (s <= VENTANA[1])].tolist())
    return np.array(sorted(d))


def correr(fuentes, B=200, seed=20261108, log=None):
    """Todo en un proceso (tests y corridas chicas)."""
    dias = dias_de(fuentes)
    return combinar(procesar(fuentes, dias, B, seed, log), dias, B, seed)

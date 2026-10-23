"""Núcleo genérico para experimentos de GRILLA MASIVA (millones de variantes) con el embudo de EdgeLab. Reutilizable.

Idea: cada operación simulada se calcula UNA vez. Cada perilla que sólo FILTRA operaciones se discretiza en niveles ordinales;
las perillas que cambian la ejecución (entrada, salida, objetivo...) son dimensiones de agrupamiento. Con sumas acumuladas
sobre un tensor salen las estadísticas de TODAS las celdas sin recorrer las operaciones por cada combinación:
costo ~ O(operaciones + celdas), no O(operaciones × celdas).

Modos de perilla (cómo se acumula su dimensión):
  "grupo"     dimensión de agrupamiento: cada nivel es una celda distinta (sin acumular)
  "ge"        umbral mínimo: la celda de nivel i toma niveles >= i  (p. ej. alejamiento >= 1, 2, 4, 8)
  "le"        umbral máximo: niveles <= i                          (p. ej. comercio <= 0, 1, 3, cualquiera)
  "eq_any"    cada nivel por separado + un nivel extra "cualquiera"
  "extremos"  primer nivel, último nivel y "cualquiera"             (p. ej. tercio bajo / alto / cualquiera)
Uso:
    P = [Perilla("N", 3, "grupo"), Perilla("A/H", 4, "ge"), Perilla("comercio", 4, "le"), Perilla("p_vol", 3, "eq_any")]
    S, Q, C = tensor(P, [ni, ai, ci, pi], net)       # índices de nivel por operación (-1 = fuera)
    st = estadisticas(S, Q, C); nom = criba(st, q=0.10)
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

import numpy as np

_N = NormalDist()


@dataclass(frozen=True)
class Perilla:
    nombre: str
    niveles: int
    modo: str = "grupo"

    def tamano_celdas(self) -> int:
        return {"grupo": self.niveles, "ge": self.niveles, "le": self.niveles, "eq_any": self.niveles + 1, "extremos": 3}[self.modo]


def tensor(perillas, indices, valores, pesos=None):
    """Suma, suma de cuadrados y conteo por celda (forma = tamano_celdas de cada perilla). Índices < 0 o NaN quedan fuera.
    `pesos` (opcional, por operación) pondera las tres sumas: lo usa el remuestreo por sesiones de `romano_wolf`."""
    v = np.asarray(valores, float); ok = np.isfinite(v)
    for p, ix in zip(perillas, indices):
        ok &= (np.asarray(ix) >= 0) & (np.asarray(ix) < p.niveles)
    shp = tuple(p.niveles for p in perillas)
    flat = np.ravel_multi_index(tuple(np.asarray(ix)[ok] for ix in indices), shp)
    out = []; pw = None if pesos is None else np.asarray(pesos, float)[ok]
    for w in (v[ok], v[ok] ** 2, None):
        if pw is not None: w = pw if w is None else w * pw
        X = np.bincount(flat, weights=w, minlength=int(np.prod(shp))).astype(float).reshape(shp)
        for ax, p in enumerate(perillas):
            X = acumular(X, ax, p.modo)
        out.append(X)
    return out


def acumular(X, ax, modo):
    if modo == "grupo": return X
    if modo == "ge": return np.flip(np.cumsum(np.flip(X, ax), ax), ax)
    if modo == "le": return np.cumsum(X, ax)
    if modo == "eq_any": return np.concatenate([X, X.sum(ax, keepdims=True)], ax)
    if modo == "extremos":
        n = X.shape[ax]
        return np.concatenate([np.take(X, [0], ax), np.take(X, [n - 1], ax), X.sum(ax, keepdims=True)], ax)
    raise ValueError(modo)


def mascara(perillas, indices, celda):
    """Qué operaciones pertenecen a una celda (para la inferencia cara sobre sobrevivientes)."""
    m = np.ones(len(indices[0]), bool)
    for p, ix, c in zip(perillas, indices, celda):
        ix = np.asarray(ix)
        if p.modo == "grupo": m &= ix == c
        elif p.modo == "ge": m &= ix >= c
        elif p.modo == "le": m &= ix <= c
        elif p.modo == "eq_any": m &= (ix == c) if c < p.niveles else (ix >= 0)
        elif p.modo == "extremos": m &= (ix == (0 if c == 0 else p.niveles - 1)) if c < 2 else (ix >= 0)
    return m


def estadisticas(S, Q, C, min_n=30):
    """Media, t (varianza por operación) y p unilateral (media > 0). Celdas con < min_n operaciones: p = 1 (se cuentan igual)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = S / C; var = (Q - C * mu ** 2) / (C - 1); t = mu / np.sqrt(var / C)
    ev = (C >= min_n) & np.isfinite(t)
    p = np.ones(C.shape); p[ev] = 1 - np.vectorize(_N.cdf)(t[ev])
    return dict(media=mu, t=t, p=p, n=C, evaluable=ev)


def criba(st, q=0.10, metodo="storey", tope=1000):
    """Tamiz FDR sobre TODAS las celdas (las no evaluables cuentan con p = 1). Devuelve las nominadas, ordenadas por t."""
    from edgelab.funnel.escalera import tamiz_fdr
    tz = tamiz_fdr(st["p"].ravel(), q, metodo); nom = np.array(tz["nominadas"], int)
    nom = nom[np.argsort(-st["t"].ravel()[nom])][:tope] if len(nom) else nom
    return dict(nominadas=[tuple(int(v) for v in np.unravel_index(f, st["n"].shape)) for f in nom], pi0=tz["pi0"], q=q,
                evaluables=int(st["evaluable"].sum()), celdas=int(st["n"].size), recortadas_por_tope=max(0, len(tz["nominadas"]) - tope))


def vecinos(celda, perillas, ejes_ordinales):
    """Celdas a ±1 nivel en cada perilla ordinal (para la meseta)."""
    out = []
    for ax in ejes_ordinales:
        lim = perillas[ax].tamano_celdas() - (1 if perillas[ax].modo in ("eq_any", "extremos") else 0)
        for d in (-1, 1):
            v = list(celda); v[ax] += d
            if 0 <= v[ax] < lim: out.append(tuple(v))
    return out


def meseta(st, celda, perillas, ejes_ordinales, min_n=30):
    """Regla fija del embudo: >= 2/3 de los vecinos positivos y mediana de vecinos >= 50 % de la celda."""
    v = [st["media"][x] for x in vecinos(celda, perillas, ejes_ordinales) if st["n"][x] >= min_n]
    ok = bool(v and np.mean(np.array(v) > 0) >= 2 / 3 and np.median(v) >= 0.5 * st["media"][celda])
    return dict(meseta=ok, vecinos=len(v), fraccion_positivos=float(np.mean(np.array(v) > 0)) if v else None)


def resumen_nulo(st, perillas, q=0.10, referencia=None, potencia=0.8):
    """Lo que publica toda grilla, nomine o no (regla «todo nulo publica su MDE»). Por celda evaluable, con el error estándar
    por operación: MDE del tamiz (nivel q/m, lo que haría falta para ser nominada entre m celdas) y MDE de confirmación (5 %).
    Agregado por nivel de cada perilla (mínimo y mediana), cuántas celdas detectarían `referencia` (p. ej. 1x la fricción),
    y la distribución de t en los dos canales (cola positiva y negativa: un efecto bidireccional no se pierde en el promedio)."""
    from edgelab.funnel.escalera import ALFA_CONFIRMACION
    ev = st["evaluable"]; m = int(st["n"].size)
    with np.errstate(invalid="ignore", divide="ignore"):
        se = np.abs(st["media"] / st["t"])
    zp = _N.inv_cdf(potencia); z_tamiz = _N.inv_cdf(1 - q / m); z_conf = _N.inv_cdf(1 - ALFA_CONFIRMACION)
    mde_t, mde_c = (z_tamiz + zp) * se, (z_conf + zp) * se
    out = dict(celdas=m, evaluables=int(ev.sum()), z_tamiz=round(z_tamiz, 3), z_confirmacion=round(z_conf, 3), potencia=potencia)
    if not ev.any(): return out
    tv = st["t"][ev]
    out["t"] = dict(max=float(tv.max()), min=float(tv.min()), **{f"q{int(k * 1000):03d}": float(np.quantile(tv, k)) for k in (0.001, 0.01, 0.5, 0.99, 0.999)},
                    sobre_z_tamiz=int((tv > z_tamiz).sum()), bajo_menos_z_tamiz=int((tv < -z_tamiz).sum()))
    out["mde_tamiz"] = dict(min=float(np.nanmin(mde_t[ev])), mediana=float(np.nanmedian(mde_t[ev])))
    out["mde_confirmacion"] = dict(min=float(np.nanmin(mde_c[ev])), mediana=float(np.nanmedian(mde_c[ev])))
    if referencia is not None:
        out["referencia"] = float(referencia)
        out["detectarian_referencia"] = dict(tamiz=int((mde_t[ev] <= referencia).sum()), confirmacion=int((mde_c[ev] <= referencia).sum()))
    por = {}
    for ax, p in enumerate(perillas):
        filas = []
        for v in range(st["n"].shape[ax]):
            sl = [slice(None)] * st["n"].ndim; sl[ax] = v; e = ev[tuple(sl)]
            if not e.any(): filas.append(dict(nivel=v, evaluables=0)); continue
            mt = mde_t[tuple(sl)][e]
            filas.append(dict(nivel=v, evaluables=int(e.sum()), mde_tamiz_min=float(np.nanmin(mt)), mde_tamiz_mediana=float(np.nanmedian(mt)),
                              t_max=float(st["t"][tuple(sl)][e].max()), t_min=float(st["t"][tuple(sl)][e].min())))
        por[p.nombre] = filas
    out["por_perilla"] = por
    return out


def romano_wolf(perillas, indices, valores, sesiones, st, B=200, alfa=0.10, seed=0, pasos=5):
    """Umbral de máximo t MEDIDO en los datos (Romano y Wolf 2005, step-down), con remuestreo de SESIONES enteras.
    Respeta la correlación real entre celdas anidadas (que el tamiz FDR trata como independientes) y la dependencia dentro de
    la sesión (que la t por operación ignora). Sólo celdas evaluables cuentan. t_j = media_j / sd_bootstrap_j; nula:
    max_j (media*_j - media_j) / sd_j. Controla la tasa de al menos un falso positivo (FWER) en `alfa`."""
    ev = st["evaluable"].ravel(); n_ev = int(ev.sum()); m0 = st["media"].ravel()[ev].astype(np.float32)
    out = dict(B=B, alfa=alfa, evaluables=n_ev, seed=seed)
    if not n_ev: return dict(out, t=np.full(st["n"].shape, np.nan), umbral=np.inf, rechazadas=[])
    us, inv = np.unique(np.asarray(sesiones), return_inverse=True); rng = np.random.default_rng(seed)
    M = np.empty((B, n_ev), np.float32)
    for b in range(B):
        w = rng.multinomial(len(us), np.full(len(us), 1 / len(us)))[inv]
        S, _, C = tensor(perillas, indices, valores, pesos=w)
        with np.errstate(invalid="ignore", divide="ignore"): M[b] = (S.ravel() / C.ravel())[ev]
    sd = np.nanstd(M, 0); sd[~(sd > 0)] = np.nan
    t = m0 / sd; M -= m0; M /= sd                                  # M pasa a ser la desviación estandarizada (en el lugar: memoria)
    activos = np.isfinite(t); rech = np.zeros(n_ev, bool); umbrales = []
    for _ in range(pasos):
        mx = np.nanmax(np.where(activos, M, -np.inf), axis=1); c = float(np.quantile(mx, 1 - alfa)); umbrales.append(c)
        nuevo = activos & (t > c)
        if not nuevo.any(): break
        rech |= nuevo; activos &= ~nuevo
    mx0 = np.nanmax(np.where(np.isfinite(t), M, -np.inf), axis=1)
    T = np.full(st["n"].size, np.nan); T[np.flatnonzero(ev)] = t; T = T.reshape(st["n"].shape)
    cel = [tuple(int(v) for v in np.unravel_index(f, st["n"].shape)) for f in np.flatnonzero(ev)[rech]]
    tmax = float(np.nanmax(t))
    return dict(out, t=T, umbral=umbrales[0], umbrales=umbrales, rechazadas=cel, t_max=tmax,
                p_rw_del_maximo=float(np.mean(mx0 >= tmax)), nula_max_q=dict(q50=float(np.quantile(mx0, .5)), q90=float(np.quantile(mx0, .9)), q95=float(np.quantile(mx0, .95))))


def pistas(st, t, k=60, min_dif=2, min_n=30):
    """Las k mejores celdas por t (la de romano_wolf: agrupada por sesión) con media > 0, DISTINTAS entre sí: cada una difiere
    de todas las elegidas en >= `min_dif` perillas (si no, serían la misma estrategia con otro nombre). Son pistas para réplica,
    no hallazgos: lo que es azar muere en la réplica."""
    tt = np.asarray(t).ravel(); ok = np.isfinite(tt) & (st["media"].ravel() > 0) & (st["n"].ravel() >= min_n)
    elegidas = []
    for f in np.flatnonzero(ok)[np.argsort(-tt[ok])]:
        c = np.array(np.unravel_index(f, st["n"].shape))
        if all(int((c != e).sum()) >= min_dif for e in elegidas): elegidas.append(c)
        if len(elegidas) >= k: break
    return [tuple(int(v) for v in c) for c in elegidas]

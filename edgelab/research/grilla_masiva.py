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


def tensor(perillas, indices, valores):
    """Suma, suma de cuadrados y conteo por celda (forma = tamano_celdas de cada perilla). Índices < 0 o NaN quedan fuera."""
    v = np.asarray(valores, float); ok = np.isfinite(v)
    for p, ix in zip(perillas, indices):
        ok &= (np.asarray(ix) >= 0) & (np.asarray(ix) < p.niveles)
    shp = tuple(p.niveles for p in perillas)
    flat = np.ravel_multi_index(tuple(np.asarray(ix)[ok] for ix in indices), shp)
    out = []
    for w in (v[ok], v[ok] ** 2, None):
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

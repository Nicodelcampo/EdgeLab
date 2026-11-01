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

import math
import os

import numpy as np

try:
    from numba import njit, prange
except ImportError:                                    # sin numba: misma lógica en Python (lenta, sólo para tests mínimos)
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]
    prange = range

_N = NormalDist()
_MODOS = {"grupo": 0, "ge": 1, "le": 2, "eq_any": 3, "extremos": 4}
# Memoria máxima para guardar la matriz bootstrap estandarizada (B x celdas evaluables, float32) entre los pasos del step-down.
# Si no entra, se recalcula por bloques en cada paso (mismo resultado, más tiempo, memoria acotada).
RW_MEMORIA_BYTES = int(float(os.environ.get("EDGELAB_RW_MEMORIA_GB", "2")) * 2**30)
RW_BLOQUE_BYTES = int(float(os.environ.get("EDGELAB_RW_BLOQUE_MB", "1024")) * 2**20)


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
    p = np.ones(C.shape)
    if ev.any(): p[ev] = _cola_superior(t[ev])                              # sin evaluables: todo p = 1 (no revienta)
    return dict(media=mu, t=t, p=p, n=C, evaluable=ev)


def criba(st, q=0.10, metodo="storey", tope=1000, m_sobre="evaluables"):
    """Tamiz FDR. Devuelve las nominadas, ordenadas por t, y los q-valores de TODAS las celdas (las no evaluables con q = 1).
    m = celdas EVALUABLES (2026-10-24, falsos negativos; filtrado independiente, Bourgon, Gentleman y Huber 2010): el filtro
    «n >= min_n» depende sólo del conteo de operaciones, no del signo ni del tamaño del P&L, así que bajo la nula no cambia la
    distribución de los p que pasan y puede salir del tamiz. Antes las no evaluables entraban con p = 1: inflaban m (y π0 de
    Storey) sin poder rechazar nunca; en AREAS-EXP-1 v1.4 eran 2/3 de las celdas (995.328 contra 315.654 evaluables).
    `m_sobre="celdas"` reproduce la regla anterior. Se publican las dos cuentas (`m`, `evaluables`, `celdas`)."""
    from edgelab.funnel.escalera import tamiz_fdr
    ev = st["evaluable"].ravel(); pf = st["p"].ravel()
    if m_sobre == "celdas": idx = np.arange(pf.size)
    elif m_sobre == "evaluables": idx = np.flatnonzero(ev)
    else: raise ValueError("m_sobre: evaluables | celdas")
    qv = np.ones(pf.size)
    if len(idx):
        tz = tamiz_fdr(pf[idx], q, metodo); qv[idx] = np.asarray(tz["q_valores"]); pi0 = tz["pi0"]
    else: pi0 = 1.0
    nom = np.flatnonzero(qv <= q); n_nom = len(nom)
    nom = nom[np.argsort(-st["t"].ravel()[nom])][:tope] if n_nom else nom
    return dict(nominadas=[tuple(int(v) for v in np.unravel_index(f, st["n"].shape)) for f in nom], pi0=pi0, q=q, m=int(len(idx)), m_sobre=m_sobre,
                evaluables=int(ev.sum()), celdas=int(st["n"].size), n_nominadas=int(n_nom), recortadas_por_tope=max(0, n_nom - tope),
                q_valores=qv.reshape(st["n"].shape))   # completo (sin tope): para marcar la nominación de cada pista


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
    ev = st["evaluable"]; m = max(int(ev.sum()), 1)                  # m del tamiz = evaluables (filtrado independiente, ver `criba`)
    with np.errstate(invalid="ignore", divide="ignore"):
        se = np.abs(st["media"] / st["t"])
    zp = _N.inv_cdf(potencia); z_tamiz = _N.inv_cdf(1 - q / m); z_conf = _N.inv_cdf(1 - ALFA_CONFIRMACION)
    mde_t, mde_c = (z_tamiz + zp) * se, (z_conf + zp) * se
    out = dict(celdas=int(st["n"].size), evaluables=int(ev.sum()), m_tamiz=m, z_tamiz=round(z_tamiz, 3), z_confirmacion=round(z_conf, 3), potencia=potencia)
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


def romano_wolf(perillas, indices, valores, sesiones, st, B=1000, alfa=0.10, seed=0, pasos=5):
    """Umbral de máximo t MEDIDO en los datos (Romano y Wolf 2005, step-down), con remuestreo de SESIONES enteras.
    Respeta la correlación real entre celdas anidadas (que el tamiz FDR trata como independientes) y la dependencia dentro de
    la sesión (que la t por operación ignora). Sólo celdas evaluables cuentan. t_j = media_j / sd_bootstrap_j; nula:
    max_j (media*_j - media_j) / sd_j. Controla la tasa de al menos un falso positivo (FWER) en `alfa`."""
    ev = st["evaluable"].ravel(); n_ev = int(ev.sum()); m0 = st["media"].ravel()[ev].astype(np.float32)
    out = dict(B=B, alfa=alfa, evaluables=n_ev, seed=seed)
    if not n_ev: return dict(out, t=np.full(st["n"].shape, np.nan), umbral=np.inf, umbrales=[], rechazadas=[], t_max=float("nan"),
                             p_rw_del_maximo=float("nan"), nula_max_q={})
    us, inv = np.unique(np.asarray(sesiones), return_inverse=True); rng = np.random.default_rng(seed)
    W = np.stack([rng.multinomial(len(us), np.full(len(us), 1 / len(us))) for _ in range(B)]).astype(np.float64)   # mismo orden de sorteo
    bs = _Bootstrap(perillas, indices, valores, inv, len(us), ev, W)
    sd = np.empty(n_ev, np.float32)
    for a, b, Mb in bs.bloques(): sd[a:b] = np.nanstd(Mb, 0)
    sd[~(sd > 0)] = np.nan; t = m0 / sd
    bs.estandarizar(m0, sd)                                        # desde acá cada bloque es la desviación estandarizada
    activos = np.isfinite(t); rech = np.zeros(n_ev, bool); umbrales = []
    for _ in range(pasos):
        mx = bs.maximo(activos); c = float(np.quantile(mx, 1 - alfa)); umbrales.append(c)
        nuevo = activos & (t > c)
        if not nuevo.any(): break
        rech |= nuevo; activos &= ~nuevo
    mx0 = bs.maximo(np.isfinite(t))
    T = np.full(st["n"].size, np.nan); T[np.flatnonzero(ev)] = t; T = T.reshape(st["n"].shape)
    cel = [tuple(int(v) for v in np.unravel_index(f, st["n"].shape)) for f in np.flatnonzero(ev)[rech]]
    tmax = float(np.nanmax(t))
    return dict(out, t=T, umbral=umbrales[0], umbrales=umbrales, rechazadas=cel, t_max=tmax,
                p_rw_del_maximo=float((1 + np.sum(mx0 >= tmax)) / (B + 1)),   # (k+1)/(B+1): nunca 0 (decisión 2026-10-24)
                nula_max_q=dict(q50=float(np.quantile(mx0, .5)), q90=float(np.quantile(mx0, .9)), q95=float(np.quantile(mx0, .95))))



def criba_maxt(perillas, indices, valores, sesiones, st, B=1000, alfa=0.10, seed=20261030):
    """Criba con error familiar bajo dependencia: Westfall-Young maxT por inversión de signo de SESIONES enteras.
    T_j = suma_s x_sj / raíz(suma_s x_sj²), con x_sj el P&L de la celda j en la sesión s: el denominador no depende de los signos,
    así que la nula es exacta si cada sesión es simétrica en signo, sin aproximación normal y sin importar la correlación entre
    celdas (el mismo signo se aplica a todas las celdas de la sesión) ni dentro de la sesión.
    Distinto de `romano_wolf`, que usa media / sd bootstrap sin reestudentizar cada réplica: medido en el control nulo de CVGAP-NQ
    rechazó en 3 de 3 semillas (18, 12 y 465 celdas), sobre todo celdas de ~30 sesiones.
    Nominadas: T_j estrictamente sobre el umbral, lo que implica p_ajustado = (1 + #{max* >= T_j}) / (B + 1) <= alfa."""
    ev = st["evaluable"].ravel(); n_ev = int(ev.sum()); shp = st["n"].shape
    out = dict(metodo="maxt_signos_sesion", B=B, alfa=alfa, seed=seed, evaluables=n_ev)
    if not n_ev: return dict(out, t=np.full(shp, np.nan), p_ajustado=np.ones(shp), umbral=np.inf, t_max=float("nan"), p_del_maximo=float("nan"),
                             nula_max_q={}, nominadas=[], n_nominadas=0)
    us, inv = np.unique(np.asarray(sesiones), return_inverse=True)
    W = np.random.default_rng(seed).choice((-1.0, 1.0), size=(B, len(us)))
    bs = _Bootstrap(perillas, indices, valores, inv, len(us), ev, W)
    T = np.full(n_ev, np.nan); mx = np.full(B, -np.inf)
    for a in range(0, n_ev, bs.ancho):
        b = min(n_ev, a + bs.ancho); ES = bs._sumas(a, b)[0]; d = np.sqrt((ES ** 2).sum(0))
        with np.errstate(invalid="ignore", divide="ignore"):
            T[a:b] = ES.sum(0) / d; R = (W @ ES) / d
        mx = np.maximum(mx, np.where(np.isfinite(R), R, -np.inf).max(1))
    orden = np.sort(mx); k = int(math.floor(alfa * (B + 1)))                   # el k-ésimo máximo: nadie sobre él tiene p_ajustado > alfa
    umbral = float(orden[B - k]) if k >= 1 else np.inf
    ok = np.isfinite(T); p_aj = np.ones(n_ev)
    p_aj[ok] = (1 + B - np.searchsorted(orden, T[ok], side="left")) / (B + 1)
    nom = np.flatnonzero(ok & (T > umbral)); nom = nom[np.argsort(-T[nom], kind="stable")]
    TT = np.full(st["n"].size, np.nan); PP = np.ones(st["n"].size); TT[np.flatnonzero(ev)] = T; PP[np.flatnonzero(ev)] = p_aj
    return dict(out, t=TT.reshape(shp), p_ajustado=PP.reshape(shp), umbral=umbral, t_max=float(np.nanmax(T)) if ok.any() else float("nan"),
                p_del_maximo=float(p_aj.min()), nula_max_q=dict(q50=float(np.quantile(mx, .5)), q90=float(np.quantile(mx, .9)), q95=float(np.quantile(mx, .95))),
                nominadas=[tuple(int(v) for v in np.unravel_index(f, shp)) for f in np.flatnonzero(ev)[nom]], n_nominadas=int(len(nom)))


# ------------------------------------------------------------------ bootstrap por sesiones sin recorrer el tensor denso B veces
# Antes: B llamadas a `tensor` (bincount + acumulación de TODAS las celdas, vacías incluidas) => O(B x celdas x perillas).
# Ahora: (1) se agregan las operaciones por (sesión, celda cruda); (2) cada par se expande una sola vez a las celdas EVALUABLES
# que lo contienen (misma regla que `mascara`), dando E_S y E_C de forma sesiones x evaluables; (3) cada réplica bootstrap es
# un producto matricial: medias* = (W @ E_S) / (W @ E_C). Mismo sorteo, mismas celdas, mismo resultado (oráculo:
# `_medias_bootstrap_denso`, test `test_romano_wolf_igual_al_denso`). Por bloques de columnas: memoria acotada.

@njit(cache=False, parallel=True)
def _expandir(ses_ini, lv, sv, cv, fmin, fmax, niveles, modos, strides, evmap, lo, hi, flo, fhi, ES, EC):
    """Pares ordenados por sesión (`ses_ini`: inicio de cada sesión): en paralelo por sesión, cada hilo escribe sólo su fila.
    Un par cuyo rango de celdas [fmin, fmax] no toca el bloque [flo, fhi] se salta sin expandir."""
    A = lv.shape[1]
    mx = 2
    for a in range(A): mx = max(mx, niveles[a] + 1)
    for s in prange(len(ses_ini) - 1):
        buf = np.empty((A, mx), np.int64); lens = np.empty(A, np.int64); pos = np.zeros(A, np.int64)
        _expandir_sesion(s, ses_ini[s], ses_ini[s + 1], lv, sv, cv, fmin, fmax, niveles, modos, strides, evmap, lo, hi, flo, fhi,
                         ES, EC, buf, lens, pos)


@njit(cache=False)
def _expandir_sesion(s, p0, p1, lv, sv, cv, fmin, fmax, niveles, modos, strides, evmap, lo, hi, flo, fhi, ES, EC, buf, lens, pos):
    A = lv.shape[1]
    for p in range(p0, p1):
        if fmax[p] < flo or fmin[p] > fhi: continue
        for a in range(A):
            l = lv[p, a]; n = niveles[a]; m = modos[a]; k = 0
            if m == 0:
                buf[a, 0] = l; k = 1
            elif m == 1:                                            # ge: la celda c toma niveles >= c  ->  c <= l
                for c in range(l + 1): buf[a, k] = c; k += 1
            elif m == 2:                                            # le: niveles <= c  ->  c >= l
                for c in range(l, n): buf[a, k] = c; k += 1
            elif m == 3:                                            # eq_any: su nivel y «cualquiera»
                buf[a, 0] = l; buf[a, 1] = n; k = 2
            else:                                                   # extremos: 0 = primero, 1 = último, 2 = cualquiera
                if l == 0: buf[a, k] = 0; k += 1
                if l == n - 1: buf[a, k] = 1; k += 1
                buf[a, k] = 2; k += 1
            lens[a] = k; pos[a] = 0
        while True:
            f = 0
            for a in range(A): f += buf[a, pos[a]] * strides[a]
            e = evmap[f]
            if e >= lo and e < hi:
                ES[s, e - lo] += sv[p]; EC[s, e - lo] += cv[p]
            a = A - 1
            while a >= 0:
                pos[a] += 1
                if pos[a] < lens[a]: break
                pos[a] = 0; a -= 1
            if a < 0: break


def _rango_celdas(lv, niveles, modos):
    """Celda mínima y máxima (por eje) que contiene a cada nivel crudo, según el modo (misma regla que `mascara`)."""
    n = niveles[None, :]; m = modos[None, :]
    cmin = np.select([m == 0, m == 1, m == 2, m == 3], [lv, 0, lv, lv], np.where(lv == 0, 0, np.where(lv == n - 1, 1, 2)))
    cmax = np.select([m == 0, m == 1, m == 2, m == 3], [lv, lv, n - 1, n], 2)
    return cmin.astype(np.int64), cmax.astype(np.int64)


class _Bootstrap:
    """Medias bootstrap de las celdas evaluables por bloques de columnas (ver arriba)."""

    def __init__(self, perillas, indices, valores, ses_inv, n_ses, ev, W, bloque_bytes=None, memoria_bytes=None):
        v = np.asarray(valores, float); ok = np.isfinite(v)
        for p, ix in zip(perillas, indices): ok &= (np.asarray(ix) >= 0) & (np.asarray(ix) < p.niveles)
        shp_raw = tuple(p.niveles for p in perillas); shp = tuple(p.tamano_celdas() for p in perillas)
        flat = np.ravel_multi_index(tuple(np.asarray(ix)[ok] for ix in indices), shp_raw)
        clave = np.asarray(ses_inv)[ok].astype(np.int64) * int(np.prod(shp_raw)) + flat
        u, j = np.unique(clave, return_inverse=True)                 # pares (sesión, celda cruda)
        self.sv = np.bincount(j, weights=v[ok], minlength=len(u)); self.cv = np.bincount(j, minlength=len(u)).astype(float)
        ses_p = (u // int(np.prod(shp_raw))).astype(np.int64)             # u ordenado => pares ordenados por sesión
        self.ses_ini = np.searchsorted(ses_p, np.arange(int(n_ses) + 1)).astype(np.int64)
        self.lv = np.stack(np.unravel_index(u % int(np.prod(shp_raw)), shp_raw), 1).astype(np.int64) if len(u) else np.zeros((0, len(shp)), np.int64)
        self.niveles = np.array([p.niveles for p in perillas], np.int64); self.modos = np.array([_MODOS[p.modo] for p in perillas], np.int64)
        self.strides = (np.array([int(np.prod(shp[a + 1:])) for a in range(len(shp))], np.int64))
        cmin, cmax = _rango_celdas(self.lv, self.niveles, self.modos)
        self.fmin, self.fmax = cmin @ self.strides, cmax @ self.strides     # rango de celdas planas que puede tocar cada par
        self.evflat = np.flatnonzero(ev)
        self.n_ev = int(ev.sum()); self.evmap = np.full(ev.size, -1, np.int32 if self.n_ev < 2**31 else np.int64); self.evmap[self.evflat] = np.arange(self.n_ev)
        self.W, self.n_ses = W, int(n_ses); B = W.shape[0]
        bb = bloque_bytes or RW_BLOQUE_BYTES; mem = memoria_bytes or RW_MEMORIA_BYTES
        self.ancho = max(1, min(self.n_ev, bb // (16 * max(self.n_ses, 1) + 8 * B)))
        self.guardar = B * self.n_ev * 4 <= mem; self._cache = {}; self._std = None

    def _sumas(self, a, b):
        ES = np.zeros((self.n_ses, b - a)); EC = np.zeros((self.n_ses, b - a))
        _expandir(self.ses_ini, self.lv, self.sv, self.cv, self.fmin, self.fmax, self.niveles, self.modos, self.strides, self.evmap, a, b,
                  int(self.evflat[a]), int(self.evflat[b - 1]), ES, EC)
        return ES, EC

    def _medias(self, a, b):
        ES, EC = self._sumas(a, b)
        with np.errstate(invalid="ignore", divide="ignore"): return ((self.W @ ES) / (self.W @ EC)).astype(np.float32)

    def bloque(self, a, b):
        if (a, b) in self._cache: return self._cache[(a, b)]
        M = self._medias(a, b)
        if self._std is not None: m0, sd = self._std; M -= m0[a:b]; M /= sd[a:b]
        if self.guardar: self._cache[(a, b)] = M
        return M

    def bloques(self):
        for a in range(0, self.n_ev, self.ancho):
            b = min(self.n_ev, a + self.ancho); yield a, b, self.bloque(a, b)

    def estandarizar(self, m0, sd):
        self._std = (m0, sd)
        for (a, b), M in self._cache.items(): M -= m0[a:b]; M /= sd[a:b]

    def maximo(self, activos):
        """max_j sobre las celdas activas de cada réplica (NaN se ignora; sin activas: -inf), sin copiar la matriz entera."""
        out = np.full(self.W.shape[0], -np.inf, np.float32)
        for a, b, M in self.bloques():
            act = activos[a:b]
            if not act.any(): continue
            with np.errstate(invalid="ignore"): out = np.fmax(out, np.nanmax(np.where(act, M, -np.inf), axis=1))
        return out


def _medias_bootstrap_denso(perillas, indices, valores, ses_inv, ev, W):
    """Oráculo (la implementación anterior): un tensor completo por réplica."""
    M = np.empty((W.shape[0], int(ev.sum())), np.float32)
    for b in range(W.shape[0]):
        S, _, C = tensor(perillas, indices, valores, pesos=W[b][ses_inv])
        with np.errstate(invalid="ignore", divide="ignore"): M[b] = (S.ravel() / C.ravel())[ev]
    return M


@njit(cache=False)
def _cola_superior_nb(t):
    out = np.empty(len(t))
    for i in range(len(t)): out[i] = 1.0 - 0.5 * (1.0 + math.erf(t[i] / math.sqrt(2.0)))     # = 1 - NormalDist().cdf(t) (fórmula de 3.13)
    return out


def _cola_superior(t):
    """1 - Phi(t) vectorizado (antes: np.vectorize de NormalDist.cdf, una llamada Python por celda). Difiere a lo sumo en 1 ulp
    (libm vs CPython; NormalDist mismo cambia de fórmula entre versiones de Python): ningún corte del tamiz depende de eso."""
    return _cola_superior_nb(np.ascontiguousarray(t, dtype=np.float64))

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

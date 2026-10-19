# -*- coding: utf-8 -*-
"""Bootstrap estacionario (Politis–Romano) con largo de bloque automático (Politis–White).

Origen: F-MET 3/3 del proceso FABLE. Fuentes extraídas y verificadas:
Politis & Romano 1994 (*The Stationary Bootstrap*, JASA); Politis & White 2004
(selección automática del largo de bloque), con la corrección de
Patton–Politis–White 2009.

## Qué problema del arnés resuelve

El bootstrap de bloques de día usa hoy un largo **fijo por convención** (bloque
= 1 día). Si hay dependencia multi-día — y los clusters de volatilidad son
exactamente eso — un bloque de 1 día sub-cubre: los intervalos salen más
angostos de lo que corresponde y un resultado parece más significativo de lo que
es.

Politis–White estima el largo óptimo **desde los datos**, y el bootstrap
estacionario (bloques de largo geométrico) es más robusto a mala especificación
del largo que el bloque fijo.

Nota de rehabilitación: la crítica de ineficiencia de Lahiri (1999) fue refutada
— Nordman (2009) halló un error de cálculo. El estacionario queda como
alternativa legítima al bloque móvil.

## Regla de uso (decidida el 2026-07-27, y es la parte que importa)

**El método de inferencia de un estudio se congela en su pre-registro, ANTES de
correrlo.** Adoptar este módulo no autoriza a re-hacer intervalos ya publicados
ni a elegir, después de ver los números, cuál de los dos métodos conviene.
Elegir el método viendo el intervalo es búsqueda de especificación con otro
nombre.

El bloque fijo **no se borra**: queda como `metodo="fijo"` para comparar.
"""
from __future__ import annotations

import numpy as np

__all__ = ["autocorrelaciones", "largo_de_bloque_optimo", "bootstrap_estacionario",
           "bootstrap_bloque_fijo"]


def autocorrelaciones(x, max_lag):
    """R(k) para k = 0..max_lag, normalizadas por R(0)."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    u = x - x.mean()
    r0 = float((u * u).sum())
    if r0 <= 0:
        return np.zeros(max_lag + 1)
    out = np.empty(max_lag + 1)
    out[0] = 1.0
    for k in range(1, max_lag + 1):
        out[k] = float((u[k:] * u[:-k]).sum()) / r0
    return out


def _flat_top(k, M):
    """Ventana flat-top de Politis–Romano: 1 hasta M/2, baja lineal hasta M."""
    a = np.abs(k) / float(M)
    w = np.ones_like(a, dtype=np.float64)
    med = (a > 0.5) & (a <= 1.0)
    w[med] = 2.0 * (1.0 - a[med])
    w[a > 1.0] = 0.0
    return w


def largo_de_bloque_optimo(x, c=2.0, K_N=None):
    """b_opt de Politis–White para el bootstrap ESTACIONARIO.

    Receta (del paper, sin adornos):
      1. m = menor lag tal que |R(k)| < c*sqrt(log10(N)/N) para K_N lags
         consecutivos a partir de m.
      2. M = 2m.
      3. G   = suma_{|k|<=M} w(k) * |k| * R(k)
         D_SB = 2 * ( suma_{|k|<=M} w(k) * R(k) )^2
      4. b = ( 2*G^2 / D_SB )^(1/3) * N^(1/3), acotado a [1, N/3].
    """
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    if n < 8:
        return 1
    K_N = K_N or max(5, int(np.ceil(np.sqrt(np.log10(n)))))
    max_lag = min(n - 2, int(np.ceil(np.sqrt(n))) + K_N + 20)
    R = autocorrelaciones(x, max_lag)
    umbral = c * np.sqrt(np.log10(n) / n)

    m = 0
    for k in range(1, max_lag - K_N + 1):
        if np.all(np.abs(R[k:k + K_N]) < umbral):
            m = k - 1
            break
    else:
        m = max_lag // 2
    M = max(2 * m, 2)
    M = min(M, max_lag)

    k = np.arange(-M, M + 1)
    w = _flat_top(k, M)
    Rk = R[np.abs(k)]
    G = float((w * np.abs(k) * Rk).sum())
    s = float((w * Rk).sum())
    D = 2.0 * s * s
    if D <= 0 or not np.isfinite(G):
        return 1
    b = (2.0 * G * G / D) ** (1.0 / 3.0) * n ** (1.0 / 3.0)
    if not np.isfinite(b):
        return 1
    return int(max(1, min(np.ceil(b), n // 3 if n >= 3 else 1)))


def bootstrap_estacionario(x, estadistico=np.mean, reps=10000, b=None,
                           seed=20260727, alpha=0.05):
    """Bloques de largo GEOMÉTRICO con media b, arranque uniforme, wrap circular.

    El wrap circular es lo que hace al remuestreo estacionario: sin él, las
    observaciones del final tendrían menos probabilidad de aparecer que las del
    medio y el estimador quedaría sesgado hacia el centro de la muestra.
    """
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    if n < 3:
        return None
    b = b or largo_de_bloque_optimo(x)
    p = 1.0 / max(b, 1)
    rng = np.random.default_rng(seed)

    # Formulación de BERNOULLI, equivalente exacta a los bloques geométricos:
    # en cada paso, con probabilidad p arranca un bloque nuevo en una posición
    # uniforme; si no, se continúa el anterior. Los largos que resultan son
    # geométricos de media 1/p = b, que es la definición de Politis–Romano.
    #
    # Se usa esta forma porque es VECTORIZABLE. El bucle `while` equivalente
    # tardaba minutos por llamada y hacía inviable el test de cobertura, que
    # necesita 1000 repeticiones x 500 réplicas.
    pos = np.arange(n)
    vals = np.empty(reps)
    bloque = 4096                                  # de a lotes, para no volar la RAM
    hecho = 0
    while hecho < reps:
        m = min(bloque, reps - hecho)
        inicios = rng.integers(0, n, size=(m, n))
        nuevo = rng.random((m, n)) < p
        nuevo[:, 0] = True                          # el primero SIEMPRE abre bloque
        # posición del último arranque en cada punto
        arr = np.maximum.accumulate(np.where(nuevo, pos[None, :], 0), axis=1)
        desfase = pos[None, :] - arr
        idx = (np.take_along_axis(inicios, arr, axis=1) + desfase) % n
        muestras = x[idx]
        vals[hecho:hecho + m] = (muestras.mean(axis=1) if estadistico is np.mean
                                 else np.apply_along_axis(estadistico, 1, muestras))
        hecho += m
    lo, hi = np.percentile(vals, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return dict(metodo="estacionario", b=int(b), reps=int(reps),
                media=float(vals.mean()),
                ic=[float(lo), float(hi)], seed=int(seed))


def bootstrap_bloque_fijo(x, estadistico=np.mean, reps=10000, b=1,
                          seed=20260727, alpha=0.05):
    """El método actual del arnés: bloques contiguos de largo FIJO b.

    Se conserva a propósito. Sirve de comparación y, sobre todo, es el método
    con el que ya están calculados los veredictos sellados: borrarlo haría
    irreproducible lo que ya se decidió.
    """
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    if n < 3:
        return None
    nb = int(np.ceil(n / b))
    rng = np.random.default_rng(seed)
    vals = np.empty(reps)
    for i in range(reps):
        inis = rng.integers(0, max(n - b + 1, 1), size=nb)
        idx = (inis[:, None] + np.arange(b)[None, :]).ravel()[:n] % n
        vals[i] = estadistico(x[idx])
    lo, hi = np.percentile(vals, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return dict(metodo="fijo", b=int(b), reps=int(reps),
                media=float(vals.mean()),
                ic=[float(lo), float(hi)], seed=int(seed))

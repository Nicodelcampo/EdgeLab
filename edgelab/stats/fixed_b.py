# -*- coding: utf-8 -*-
"""Generador de valores críticos brownianos para inferencia fixed-b y cota de
cobertura de Huang-Shao (2016).

Este módulo no implementa la inferencia fixed-b completa: solo simula los
funcionales límite de Shao-Politis (2013) y reporta la cota de cobertura que
impone si el método es aplicable a un b dado.

## Fuentes

- Shao, X. y Politis, D. N. (2013). "Fixed-b Subsampling and the Block
  Bootstrap: Improved Confidence Sets Based on p-Value Calibration".
  Journal of the Royal Statistical Society Series B 75(1):161-184.
  Preprint: arXiv:1204.1035.
- Huang, Y. y Shao, X. (2016). "Coverage Bound for Fixed-b Subsampling and
  Generalized Subsampling for Time Series". Statistica Sinica 26:1499-1524.
  doi:10.5705/ss.2014.185t.
- Kiefer, N. M. y Vogelsang, T. J. (2005). "A New Asymptotic Theory for
  Heteroskedasticity-Autocorrelation Robust Tests". Econometric Theory
  21:1130-1164.

Ver documentación completa en `docs/referencias/FIXED_B_SHAO_POLITIS.md`.

## Decisiones de implementación NO presentes en las fuentes

- El browniano se aproxima con la suma parcial normalizada de `GRILLA`
  variables iid N(0,1), como describe la Sección 3.1 de Shao-Politis (2013).
- Las constantes de simulación son congeladas y aparecen en mayúsculas:
  `GRILLA = 14775`, `N_CAMINOS = 50000`, `TAMANO_CHUNK = 1000`, `SEMILLA =
  20260801`. `TAMANO_CHUNK` afecta el resultado numérico porque cambia cómo se
  consume el stream del generador: la misma semilla con distinto tamaño de chunk
  produce distintos caminos.
- Los caminos se generan por chunks y se reutilizan para todos los valores de b
  pedidos en una llamada a `simular_funcionales`. Esto hace pareadas las
  comparaciones entre b distintos.
- La integral normalizada se aproxima con la media simple sobre los
  `GRILLA - l + 1` puntos discretos, en lugar de una cuadratura más elaborada.
- Se exige que `b * GRILLA` sea entero exacto; si no lo es, se lanza
  `FixedBError`. El usuario debe elegir b compatibles con la grilla.
- Cuantiles: se usa `quantile_exact` de `edgelab.bridge.common` (índice
  `ceil(q*n) - 1`, sin interpolación), que es la convención de cuantil exacto
  del repositorio. Se ordena el array antes de llamarla.
- Cota de cobertura: se implementa Clopper-Pearson una cola superior a nivel
  0.99 sin depender de scipy. La decisión se toma mediante la equivalencia
  exacta `U <= alpha` si y sólo si `F(alpha) <= delta`, donde `F(p)` es la CDF
  binomial `P(X <= k; n, p)` y `delta = 0.01`. Esta equivalencia es válida
  porque `F(p)` es estrictamente decreciente en p.
- La CDF binomial se evalúa en espacio logarítmico con `math.lgamma`, sumando
  `k+1` términos exactos y estabilizando por el log-término máximo antes de
  exponenciar.
- El valor numérico `ic_sup` (límite superior de confianza) se obtiene por
  bisección sobre p en [0, 1] resolviendo `F(p) = delta`, con tolerancia
  `1e-12` en el ancho del intervalo y tope de 200 iteraciones. Si k == n, se
  reporta `ic_sup = 1.0`.
- El veredicto evalúa primero el caso "NO APTO" (`beta_puntual > alpha`), luego
  "APTO" (`_cdf_binomial(k, n, alpha) <= delta`), y en cualquier otro caso
  "INCONCLUSO". Los tres casos son mutuamente excluyentes y exhaustivos.
- `GRILLA = 14775 = 197 * 75`. Con el n de muestra sellado en 197 días-bloque,
  el b de producción es `b = 16/197` (`l = round(0.08*197) = 16`), y a esta
  grilla `b * GRILLA = 1200` es entero exacto en IEEE double (verificado:
  `_validar_b(16/197, 14775)` pasa). La exactitud NO vale para cualquier
  múltiplo de 197: con `197 * 25 = 4925` el producto es 399.99999999999994 y
  `_validar_b` rechaza; hay que verificar cada par (b, grilla). Efecto lateral
  declarado: `0.1`, `0.05`, `0.25`, `0.5` y `0.02` dejan de ser b válidos a
  grilla de módulo (sus productos con 14775 no son enteros); `0.08` sigue
  válido (`0.08 * 14775 = 1182.0`). `N_CAMINOS = 50000` sigue el protocolo de
  simulación de los autores (Sección 3.1 de Shao-Politis 2013) en este módulo,
  pero las fuentes no lo exigen como invariante y puede diferir en otros
  contextos. Si cambia `GRILLA`, los valores golden dejan de ser válidos.
- La cota de cobertura y el veredicto exigen declarar el funcional de forma
  explícita (parámetro `funcional`, SIN valor por defecto): `FUNCIONAL_UNA_COLA`
  es el funcional de producción (la constante de calibración es `cuantil_G`,
  nunca `cuantil_G_sim`); `FUNCIONAL_SIMETRICO` es sólo diagnóstico de
  contraste: toda cifra suya se emite con el prefijo
  "NO CITABLE - diagnóstico de contraste".
- Todos los errores de dominio lanzan `FixedBError` (subclase de `RuntimeError`)
  en lugar de devolver `None` o usar `NaN` como señal de error.
"""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np

from edgelab.bridge.common import quantile_exact

__all__ = [
    "FixedBError",
    "simular_funcionales",
    "cuantil_G",
    "cuantil_G_sim",
    "cota_de_cobertura",
    "veredicto_cota",
    "FUNCIONAL_UNA_COLA",
    "FUNCIONAL_SIMETRICO",
    "GRILLA",
    "N_CAMINOS",
    "TAMANO_CHUNK",
    "SEMILLA",
]

GRILLA = 14775
N_CAMINOS = 50000
TAMANO_CHUNK = 1000
SEMILLA = 20260801

# Funcional de inferencia. Producción: UNA COLA superior (la constante de
# calibración es cuantil_G). El simétrico queda como diagnóstico de contraste:
# sus cifras se emiten con el prefijo "NO CITABLE - diagnóstico de contraste".
FUNCIONAL_UNA_COLA = "una_cola"
FUNCIONAL_SIMETRICO = "simetrico"

_DELTA_CP = 0.01
_BISEC_TOL = 1e-12
_BISEC_MAX_ITER = 200


class FixedBError(RuntimeError):
    """El dominio de fixed-b se violó o la simulación falló."""


def _validar_b(b, grilla):
    """b debe estar en (0,1) y b*grilla debe ser entero exacto."""
    if not isinstance(b, (int, float, np.floating, np.integer)):
        raise FixedBError("b debe ser numérico, vino %r" % (b,))
    b = float(b)
    if not (0.0 < b < 1.0):
        raise FixedBError("b debe estar en (0,1), vino %r" % (b,))
    prod = b * grilla
    if not float(prod).is_integer():
        raise FixedBError(
            "b * grilla debe ser entero exacto: b=%r, grilla=%d, producto=%r"
            % (b, grilla, prod)
        )
    l = int(prod)
    if l >= grilla:
        # Inalcanzable con b en (0,1), pero se mantiene como guarda defensiva.
        raise FixedBError(
            "b * grilla >= grilla (%d >= %d): no quedan puntos t" % (l, grilla)
        )
    return l


def _validar_alpha(alpha):
    if not isinstance(alpha, (int, float, np.floating, np.integer)):
        raise FixedBError("alpha debe ser numérico, vino %r" % (alpha,))
    alpha = float(alpha)
    if not (0.0 < alpha < 1.0):
        raise FixedBError("alpha debe estar en (0,1), vino %r" % (alpha,))
    return alpha


def _validar_positivo_entero(n, nombre):
    if not isinstance(n, (int, np.integer)):
        raise FixedBError("%s debe ser un entero positivo, vino %r" % (nombre, n))
    if n <= 0:
        raise FixedBError("%s debe ser positivo, vino %r" % (nombre, n))
    return int(n)


def _cdf_binomial(k, n, p) -> float:
    """CDF binomial exacta: P(X <= k) con X ~ Binomial(n, p).

    Evaluada en espacio logarítmico para estabilidad con n grande. Suma
    exactamente k+1 términos. Recortada a [0, 1].
    """
    if not (0 <= k <= n):
        raise FixedBError("k debe estar en [0, n], vino k=%d, n=%d" % (k, n))
    if n < 0:
        raise FixedBError("n debe ser >= 0, vino %d" % (n,))
    if p <= 0.0:
        return 1.0 if k >= n else 0.0
    if p >= 1.0:
        return 0.0 if k < 0 else 1.0
    k = int(k)
    n = int(n)
    log_one_minus_p = math.log1p(-p)
    log_p = math.log(p)
    terms = np.empty(k + 1, dtype=np.float64)
    for i in range(k + 1):
        log_comb = (
            math.lgamma(n + 1)
            - math.lgamma(i + 1)
            - math.lgamma(n - i + 1)
        )
        terms[i] = log_comb + i * log_p + (n - i) * log_one_minus_p
    m = float(terms.max())
    s = float(np.exp(terms - m).sum()) * math.exp(m)
    return float(np.clip(s, 0.0, 1.0))


def _clopper_pearson_upper(k, n, delta=_DELTA_CP) -> float:
    """Límite superior de confianza Clopper-Pearson a nivel 0.99, una cola.

    Resuelve F(p) = delta con F(p) = P(X <= k; n, p) por bisección.
    Si k == n, U = 1.0.
    """
    if k == n:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(_BISEC_MAX_ITER):
        mid = (lo + hi) / 2.0
        if (hi - lo) <= _BISEC_TOL:
            return mid
        fmid = _cdf_binomial(k, n, mid)
        if fmid > delta:
            lo = mid
        else:
            hi = mid
    raise FixedBError(
        "bisección de Clopper-Pearson no convergió: k=%d, n=%d" % (k, n)
    )


def _clopper_pearson_lower(k, n, delta=_DELTA_CP) -> float:
    """Límite inferior de confianza Clopper-Pearson a nivel 0.99, una cola.

    Resuelve P(X <= k-1; n, p) = 1 - delta por bisección.
    Si k == 0, L = 0.0.
    """
    if k == 0:
        return 0.0
    k_m1 = k - 1
    target = 1.0 - delta
    lo, hi = 0.0, 1.0
    for _ in range(_BISEC_MAX_ITER):
        mid = (lo + hi) / 2.0
        if (hi - lo) <= _BISEC_TOL:
            return mid
        fmid = _cdf_binomial(k_m1, n, mid)
        if fmid > target:
            lo = mid
        else:
            hi = mid
    raise FixedBError(
        "bisección de Clopper-Pearson (inferior) no convergió: k=%d, n=%d" % (k, n)
    )


def simular_funcionales(
    bs: Iterable[float],
    *,
    n_caminos: int = N_CAMINOS,
    grilla: int = GRILLA,
    semilla: int = SEMILLA,
    _retornar_supremos: bool = False,
) -> dict[float, dict[str, np.ndarray]]:
    """Simula los funcionales de una cola G(b) y simétrico G_sim(b) por Monte Carlo.

    Parámetros
    ----------
    bs : secuencia de valores de b
        Cada b debe estar en (0, 1) y cumplir b * grilla entero exacto.
    n_caminos : int, opcional
        Réplicas Monte Carlo. Default 50000.
    grilla : int, opcional
        Pasos brownianos por camino. Default 5000.
    semilla : int, opcional
        Semilla del generador. Default 20260801.
    _retornar_supremos : bool, privado
        Si es True, cada entrada contiene además las claves "sup_D" (supremo
        de |D(t)| por camino) y "W1_abs", necesarias para verificar la
        identidad beta(b) = P(G_sim(b) = 0) del funcional simétrico, y las
        claves "sup_D_una_cola" (supremo con SIGNO de D(t)) y "W1" (con
        signo), para la identidad beta(b) = P(G(b) = 0) del funcional de
        una cola: G(b) == 0  <=>  sup_t D(t) < W(1).

    Retorna
    -------
    dict[float, dict[str, np.ndarray]]
        Para cada b: {"G": array(n_caminos), "G_sim": array(n_caminos),
        opcionalmente "sup_D": array(n_caminos)}.
    """
    n_caminos = _validar_positivo_entero(n_caminos, "n_caminos")
    grilla = _validar_positivo_entero(grilla, "grilla")
    bs = tuple(bs)
    if not bs:
        raise FixedBError("bs está vacío")
    longitudes = {}
    for b in bs:
        if b in longitudes:
            continue
        longitudes[b] = _validar_b(b, grilla)
    rng = np.random.default_rng(semilla)
    n_chunks = (n_caminos + TAMANO_CHUNK - 1) // TAMANO_CHUNK
    acumuladores_G = {b: [] for b in bs}
    acumuladores_G_sim = {b: [] for b in bs}
    acumuladores_sup = {b: [] for b in bs}
    acumuladores_sup_una_cola = {b: [] for b in bs}
    acumuladores_W1 = []
    acumuladores_W1_signed = []
    for _ in range(n_chunks):
        chunk_size = min(TAMANO_CHUNK, n_caminos - _ * TAMANO_CHUNK)
        if chunk_size <= 0:
            break
        Z = rng.standard_normal((chunk_size, grilla))
        W = np.concatenate(
            [np.zeros((chunk_size, 1), dtype=np.float64),
             np.cumsum(Z, axis=1, dtype=np.float64)],
            axis=1,
        ) / math.sqrt(grilla)
        W1 = W[:, grilla]
        if _retornar_supremos:
            acumuladores_W1.append(np.abs(W1))
            acumuladores_W1_signed.append(W1)
        for b in bs:
            l = longitudes[b]
            sqrt_b = math.sqrt(b)
            # W[:, i+l] - W[:, i] para i = 0..grilla-l
            diff = W[:, l:grilla + 1] - W[:, 0:grilla + 1 - l]
            D = (diff - b * W1[:, None]) / sqrt_b
            G_chunk = (W1[:, None] <= D).mean(axis=1)
            G_sim_chunk = (np.abs(W1[:, None]) <= np.abs(D)).mean(axis=1)
            acumuladores_G[b].append(G_chunk)
            acumuladores_G_sim[b].append(G_sim_chunk)
            if _retornar_supremos:
                acumuladores_sup[b].append(np.abs(D).max(axis=1))
                acumuladores_sup_una_cola[b].append(D.max(axis=1))
    resultado = {}
    for b in bs:
        G = np.concatenate(acumuladores_G[b])[:n_caminos]
        G_sim = np.concatenate(acumuladores_G_sim[b])[:n_caminos]
        item = {"G": G.astype(np.float64), "G_sim": G_sim.astype(np.float64)}
        if _retornar_supremos:
            sup_D = np.concatenate(acumuladores_sup[b])[:n_caminos]
            item["sup_D"] = sup_D.astype(np.float64)
            sup_D_una_cola = np.concatenate(acumuladores_sup_una_cola[b])[:n_caminos]
            item["sup_D_una_cola"] = sup_D_una_cola.astype(np.float64)
            W1_abs = np.concatenate(acumuladores_W1)[:n_caminos]
            item["W1_abs"] = W1_abs.astype(np.float64)
            W1_signed = np.concatenate(acumuladores_W1_signed)[:n_caminos]
            item["W1"] = W1_signed.astype(np.float64)
        resultado[b] = item
    return resultado


def _funcionales_b(
    b: float,
    *,
    n_caminos: int = N_CAMINOS,
    grilla: int = GRILLA,
    semilla: int = SEMILLA,
):
    """Simula y retorna (G, G_sim) para un único b."""
    res = simular_funcionales([b], n_caminos=n_caminos, grilla=grilla, semilla=semilla)
    return res[b]["G"], res[b]["G_sim"]


def cuantil_G(b, alpha, **kw) -> float:
    """Cuantil alpha de G(b) según la convención quantile_exact del repo."""
    alpha = _validar_alpha(alpha)
    G, _ = _funcionales_b(b, **kw)
    return float(quantile_exact(np.sort(G), alpha))


def cuantil_G_sim(b, alpha, **kw) -> float:
    """Cuantil alpha de G_sim(b) según la convención quantile_exact del repo."""
    alpha = _validar_alpha(alpha)
    _, G_sim = _funcionales_b(b, **kw)
    return float(quantile_exact(np.sort(G_sim), alpha))


def _validar_funcional(funcional):
    """El funcional es un parámetro EXPLÍCITO obligatorio: quien llama declara
    cuál usa. No tiene valor por defecto a propósito."""
    if funcional not in (FUNCIONAL_UNA_COLA, FUNCIONAL_SIMETRICO):
        raise FixedBError(
            "funcional debe ser %r o %r, vino %r"
            % (FUNCIONAL_UNA_COLA, FUNCIONAL_SIMETRICO, funcional)
        )
    return funcional


def cota_de_cobertura(b, funcional, **kw) -> dict:
    """Cota de cobertura beta(b) e intervalos de confianza de Clopper-Pearson.

    Parámetros
    ----------
    b : float
        Fracción de bloque. Debe cumplir b * grilla entero exacto.
    funcional : str
        OBLIGATORIO, sin default. `FUNCIONAL_UNA_COLA` (producción: beta sobre
        G(b), la constante de calibración es `cuantil_G`) o
        `FUNCIONAL_SIMETRICO` (diagnóstico de contraste: beta sobre G_sim(b);
        toda cifra suya se emite con el prefijo
        "NO CITABLE - diagnóstico de contraste").

    Retorna
    -------
    dict con claves:
        beta: float
            Fracción de caminos con el funcional == 0. Para una cola es
            P(G(b) = 0) = P(sup_t D(t) < W(1)); para el simétrico es
            P(G_sim(b) = 0) = P(sup_t |D(t)| < |W(1)|).
        beta_por_supremo: float
            La misma fracción calculada directamente por el supremo (con
            signo para una cola, en valor absoluto para el simétrico).
        ic_sup: float
            Límite superior de confianza 0.99 para beta.
        ic_inf: float
            Límite inferior de confianza 0.99 para beta.
        k: int
            Cantidad de caminos con el funcional == 0 (el estadístico binomial).
        n_caminos: int
            Cantidad de caminos simulados.
        funcional: str
            El funcional usado, para que el consumidor no pueda perder la
            procedencia de la cifra.
    """
    _validar_funcional(funcional)
    res = simular_funcionales(
        [b], _retornar_supremos=True, **kw
    )
    if funcional == FUNCIONAL_UNA_COLA:
        vals = res[b]["G"]
        sup_D = res[b]["sup_D_una_cola"]
        W1_ref = res[b]["W1"]
    else:
        vals = res[b]["G_sim"]
        sup_D = res[b]["sup_D"]
        W1_ref = res[b]["W1_abs"]
    n_caminos = vals.size
    ceros = int((vals == 0.0).sum())
    beta_puntual = ceros / n_caminos
    beta_supremo = float((sup_D < W1_ref).mean())
    ic_sup = _clopper_pearson_upper(ceros, n_caminos)
    ic_inf = _clopper_pearson_lower(ceros, n_caminos)
    return {
        "beta": float(beta_puntual),
        "beta_por_supremo": beta_supremo,
        "ic_sup": float(ic_sup),
        "ic_inf": float(ic_inf),
        "k": ceros,
        "n_caminos": int(n_caminos),
        "funcional": funcional,
    }


def veredicto_cota(b, alpha, funcional, **kw) -> dict:
    """Veredicto sobre si un b es apto para inferencia fixed-b.

    `funcional` es OBLIGATORIO, sin default: el de producción es
    `FUNCIONAL_UNA_COLA` (la constante de calibración es `cuantil_G`, nunca
    `cuantil_G_sim`).

    Regla:
        beta_puntual > alpha                -> "NO APTO"
        _cdf_binomial(k, n, alpha) <= 0.01  -> "APTO"
        en cualquier otro caso              -> "INCONCLUSO"

    Retorna
    -------
    dict con claves b, alpha, beta, beta_por_supremo, ic_sup, ic_inf,
    veredicto, funcional.
    """
    alpha = _validar_alpha(alpha)
    _validar_funcional(funcional)
    cota = cota_de_cobertura(b, funcional, **kw)
    beta = cota["beta"]
    n_caminos = cota["n_caminos"]
    k = cota["k"]
    veredicto = "INCONCLUSO"
    if beta > alpha:
        veredicto = "NO APTO"
    elif _cdf_binomial(k, n_caminos, alpha) <= _DELTA_CP:
        veredicto = "APTO"
    return {
        "b": float(b),
        "alpha": float(alpha),
        "beta": beta,
        "beta_por_supremo": cota["beta_por_supremo"],
        "ic_sup": cota["ic_sup"],
        "ic_inf": cota["ic_inf"],
        "veredicto": veredicto,
        "funcional": funcional,
    }

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
  `GRILLA = 5000`, `N_CAMINOS = 50000`, `TAMANO_CHUNK = 1000`, `SEMILLA =
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
- `GRILLA = 5000` está tomado del protocolo de simulación de los autores
  (Sección 3.1 de Shao-Politis 2013). `N_CAMINOS = 50000` también sigue ese
  protocolo en este módulo, pero las fuentes no lo exigen como invariante y
  puede diferir en otros contextos. Si cambia `GRILLA`, los valores golden
  dejan de ser válidos.
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
    "GRILLA",
    "N_CAMINOS",
    "TAMANO_CHUNK",
    "SEMILLA",
]

GRILLA = 5000
N_CAMINOS = 50000
TAMANO_CHUNK = 1000
SEMILLA = 20260801

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


def _clopper_pearson_upper(k, n) -> float:
    """Límite superior de confianza Clopper-Pearson a nivel 0.99, una cola.

    Resuelve F(p) = _delta con F(p) = P(X <= k; n, p) por bisección.
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
        if fmid > _DELTA_CP:
            lo = mid
        else:
            hi = mid
    raise FixedBError(
        "bisección de Clopper-Pearson no convergió: k=%d, n=%d" % (k, n)
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
        Si es True, cada entrada contiene además la clave "sup_D" con el
        supremo de |D(t)| por camino, necesario para verificar la identidad
        beta(b) = P(G_sim(b) = 0).

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
    acumuladores_W1 = []
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
    resultado = {}
    for b in bs:
        G = np.concatenate(acumuladores_G[b])[:n_caminos]
        G_sim = np.concatenate(acumuladores_G_sim[b])[:n_caminos]
        item = {"G": G.astype(np.float64), "G_sim": G_sim.astype(np.float64)}
        if _retornar_supremos:
            sup_D = np.concatenate(acumuladores_sup[b])[:n_caminos]
            item["sup_D"] = sup_D.astype(np.float64)
            W1_abs = np.concatenate(acumuladores_W1)[:n_caminos]
            item["W1_abs"] = W1_abs.astype(np.float64)
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


def cota_de_cobertura(b, **kw) -> dict:
    """Cota de cobertura beta(b) y límite superior de confianza de Clopper-Pearson.

    Retorna
    -------
    dict con claves:
        beta: float
            Fracción de caminos con G_sim == 0 (igual a P(sup|D| < |W(1)|)).
        beta_por_supremo: float
            Fracción calculada directamente por el supremo.
        ic_sup: float
            Límite superior de confianza 0.99 para beta.
        n_caminos: int
            Cantidad de caminos simulados.
    """
    res = simular_funcionales(
        [b], _retornar_supremos=True, **kw
    )
    G_sim = res[b]["G_sim"]
    sup_D = res[b]["sup_D"]
    W1_abs = res[b]["W1_abs"]
    n_caminos = G_sim.size
    ceros = int((G_sim == 0.0).sum())
    beta_puntual = ceros / n_caminos
    beta_supremo = float((sup_D < W1_abs).mean())
    ic_sup = _clopper_pearson_upper(ceros, n_caminos)
    return {
        "beta": float(beta_puntual),
        "beta_por_supremo": beta_supremo,
        "ic_sup": float(ic_sup),
        "n_caminos": int(n_caminos),
    }


def veredicto_cota(b, alpha, **kw) -> dict:
    """Veredicto sobre si un b es apto para inferencia fixed-b.

    Regla:
        beta_puntual > alpha                -> "NO APTO"
        _cdf_binomial(k, n, alpha) <= 0.01  -> "APTO"
        en cualquier otro caso              -> "INCONCLUSO"

    Retorna
    -------
    dict con claves b, alpha, beta, ic_sup, veredicto.
    """
    alpha = _validar_alpha(alpha)
    cota = cota_de_cobertura(b, **kw)
    beta = cota["beta"]
    n_caminos = cota["n_caminos"]
    k = int(round(beta * n_caminos))
    veredicto = "INCONCLUSO"
    if beta > alpha:
        veredicto = "NO APTO"
    elif _cdf_binomial(k, n_caminos, alpha) <= _DELTA_CP:
        veredicto = "APTO"
    return {
        "b": float(b),
        "alpha": float(alpha),
        "beta": beta,
        "ic_sup": cota["ic_sup"],
        "veredicto": veredicto,
    }

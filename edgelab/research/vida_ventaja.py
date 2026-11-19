"""Vida de una ventaja: cuánto cambia y cuánto persiste la media verdadera de una regla fija (paso 1 de
docs/research/urgencia_vs_evidencia_20261117/PROPUESTA.md; pre-registro en esa carpeta).

Modelo de espacio de estados (nivel con desvío AR(1)), por regla i y mes t, en unidades de desvío por operación de la regla (z = R / σ_i):
    y_it  = media de z en el mes (n_it operaciones; mes sin operaciones = faltante)       observación, varianza 1 / n_it
    μ_it  = m_i + d_it                                                                     m_i: calidad ESTÁTICA de la regla (E7)
    d_it  = ρ · d_i,t−1 + η_it,   η ~ N(0, τ² (1 − ρ²))                                     desvío de régimen: tamaño τ, persistencia ρ
Vida media de un desvío: L = ln 0,5 / ln ρ meses. τ = 0 ⇒ no hay régimen distinguible del ruido (sólo calidad estática). El mismo filtro de
Kalman da, en el forward, la media posterior de μ (evidencia) y su varianza (incertidumbre): las dos piezas de la política del paso 3.
ρ y τ son comunes a una familia de reglas (se estiman juntas, máxima verosimilitud en grilla, sin scipy); m_i es propia (media ponderada).
"""
from __future__ import annotations

import math

import numpy as np
from numba import njit

GRILLA_RHO = (0.0, 0.3, 0.5, 0.7, 0.8, 0.85, 0.9, 0.93, 0.95, 0.97, 0.98, 0.99)
GRILLA_TAU = (0.0, 0.01, 0.02, 0.03, 0.05, 0.07, 0.1, 0.13, 0.16, 0.2, 0.25, 0.3, 0.4)
RECORTE_R = (-3.0, 5.0)              # declarado antes: colas de R recortadas (una operación de +18 R no define un régimen)


def mensual(R, meses, n_meses: int):
    """(suma, n) de z por mes (índices 0..n_meses−1) con z = R recortado / σ de la regla."""
    R = np.clip(np.asarray(R, float), *RECORTE_R); s = R.std(ddof=1) if len(R) > 1 else 1.0
    z = R / (s if s > 0 else 1.0); suma = np.bincount(meses, weights=z, minlength=n_meses); n = np.bincount(meses, minlength=n_meses)
    return suma, n.astype(float)


@njit(cache=False)
def _loglik_nb(suma, n, rho, tau, p_m):
    q = tau * tau * (1.0 - rho * rho)
    x0 = 0.0; x1 = 0.0; p00 = p_m; p01 = 0.0; p11 = tau * tau; ll = 0.0; primero = True
    for t in range(n.shape[0]):
        if t > 0:
            x1 = rho * x1; p01 = rho * p01; p11 = rho * rho * p11 + q
        if n[t] <= 0: continue
        y = suma[t] / n[t]; S = p00 + 2.0 * p01 + p11 + 1.0 / n[t]; v = y - x0 - x1
        if not primero: ll += -0.5 * (math.log(2.0 * math.pi * S) + v * v / S)
        primero = False
        k0 = (p00 + p01) / S; k1 = (p01 + p11) / S; c0 = p00 + p01; c1 = p01 + p11
        x0 += k0 * v; x1 += k1 * v
        p00 -= k0 * c0; p01 -= k0 * c1; p11 -= k1 * c1
    return ll


def loglik(suma, n, rho: float, tau: float, p_m: float = 100.0) -> float:
    """Log-verosimilitud exacta del filtro de Kalman de una serie, con la media estática m como estado con prior difuso (varianza
    `p_m`): fijar m en el promedio muestral se come parte del desvío lento y sesga ρ hacia abajo. La primera observación sólo fija m.
    Meses sin operaciones: sólo predicción."""
    return float(_loglik_nb(np.asarray(suma, np.float64), np.asarray(n, np.float64), float(rho), float(tau), float(p_m)))


def ajustar(series, grilla_rho=None, grilla_tau=None) -> dict:
    """`series`: lista de (suma, n). Máxima verosimilitud de (ρ, τ) comunes; perfil de τ (máximo sobre ρ) para el intervalo."""
    grilla_rho = GRILLA_RHO if grilla_rho is None else grilla_rho; grilla_tau = GRILLA_TAU if grilla_tau is None else grilla_tau
    L = np.full((len(grilla_rho), len(grilla_tau)), -np.inf)
    for a, r in enumerate(grilla_rho):
        for b, t in enumerate(grilla_tau):
            if t == 0 and a: L[a, b] = L[0, b]; continue            # τ = 0: ρ no importa
            L[a, b] = sum(loglik(s, n, r, t) for s, n in series)
    a, b = np.unravel_index(np.argmax(L), L.shape); perfil_tau = L.max(axis=0); perfil_rho = L[:, 1:].max(axis=1)
    ic_tau = [t for t, v in zip(grilla_tau, perfil_tau) if L[a, b] - v <= 1.92]          # perfil, 95 % (χ²₁ / 2)
    ic_rho = [r for r, v in zip(grilla_rho, perfil_rho) if L[a, b] - v <= 1.92]
    rho, tau = grilla_rho[a], grilla_tau[b]
    return dict(rho=rho, tau=tau, loglik=float(L[a, b]), lr_tau0=float(2 * (L[a, b] - L[0, 0])),
                ic_tau=[min(ic_tau), max(ic_tau)], ic_rho=[min(ic_rho), max(ic_rho)],
                vida_media_meses=(math.log(0.5) / math.log(rho)) if 0 < rho < 1 and tau > 0 else None,
                n_series=len(series), n_meses_con_ops=int(sum((n > 0).sum() for _, n in series)), n_ops=int(sum(n.sum() for _, n in series)))


def generar_series(n_ops_mes, rho: float, tau: float, m=0.0, seed: int = 0):
    """Series sintéticas con la misma estructura de operaciones por mes (lista de arrays): para potencia y para el nulo paramétrico."""
    rng = np.random.default_rng(seed); out = []
    for nm in n_ops_mes:
        T = len(nm); d = np.zeros(T); d[0] = rng.normal(0, tau)
        for t in range(1, T): d[t] = rho * d[t - 1] + rng.normal(0, tau * math.sqrt(1 - rho ** 2))
        n = np.asarray(nm, float); suma = np.where(n > 0, rng.normal((m + d) * n, np.sqrt(np.maximum(n, 1e-9))), 0.0)
        out.append((suma, n))
    return out


def innovaciones(suma, n, rho: float, tau: float, p_m: float = 100.0):
    """Innovaciones estandarizadas v/√S del filtro (diagnóstico del pre-registro: ≈ N(0,1) si el modelo describe la serie)."""
    q = tau ** 2 * (1 - rho ** 2); x0 = x1 = 0.0; p00, p01, p11 = p_m, 0.0, tau ** 2; out = []; primero = True
    for t in range(len(n)):
        if t: x1 = rho * x1; p01 = rho * p01; p11 = rho * rho * p11 + q
        if n[t] <= 0: continue
        S = p00 + 2 * p01 + p11 + 1.0 / n[t]; v = suma[t] / n[t] - x0 - x1
        if not primero: out.append(v / math.sqrt(S))
        primero = False
        k0, k1, c0, c1 = (p00 + p01) / S, (p01 + p11) / S, p00 + p01, p01 + p11
        x0 += k0 * v; x1 += k1 * v; p00 -= k0 * c0; p01 -= k0 * c1; p11 -= k1 * c1
    return np.asarray(out)

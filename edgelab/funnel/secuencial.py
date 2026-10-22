"""Monitoreo secuencial con validez en todo momento (e-procesos por apuesta) para réplica, holdout y paper.

Problema que resuelve (auditoría 2026-10-22): G4 pide n >= 30 y una sola mirada, pero en la práctica los datos llegan por semana y
se miran cada vez (la regla del visor de LUX-IMB se miró con n = 14). Con un p-valor clásico, mirar muchas veces infla el error.
Un e-proceso no: por la desigualdad de Ville, P(alguna vez K_t >= 1/alfa | H0) <= alfa, se mire cuando se mire y se pare cuando se pare.

Dos pruebas, las dos válidas en todo momento:
- EDGE      H0: E[x] <= mu0 (por defecto 0 neto). K >= 1/alfa  -> la media neta es positiva.
- FUTILIDAD H0: E[x] >= mu1 (el efecto útil mínimo, p. ej. 50 % de la expectativa de desarrollo, como G4).
            K >= 1/alfa -> el efecto, si existe, es menor que lo útil: se descarta con evidencia, no por falta de datos.
Mientras ninguna cruce, el estado es SIN_DECIDIR: la candidata sigue viva y el informe dice cuánto falta.

Supuesto declarado ANTES de mirar: cada resultado por operación está acotado en [piso, techo] (p. ej. SL + slippage severo + costos
abajo; TP + costos arriba). Un resultado fuera de ese rango invalida la garantía: se detiene con LIMITE_VIOLADO en vez de recortarlo.
Mezcla sobre una grilla fija de fracciones de apuesta: el promedio de martingalas de prueba es martingala de prueba (Waudby-Smith y Ramdas 2023).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

FRACCIONES = (0.025, 0.05, 0.1, 0.2, 0.3, 0.5)


@dataclass
class EProceso:
    """Martingala de prueba mezcla para H0: E[x] <= mu0 (lado='mayor') o E[x] >= mu0 (lado='menor')."""
    mu0: float
    piso: float
    techo: float
    lado: str = "mayor"
    fracciones: tuple = FRACCIONES
    log_k: list = field(default_factory=list)

    def __post_init__(self):
        if not self.piso < self.mu0 < self.techo:
            raise ValueError("hace falta piso < mu0 < techo (cotas declaradas antes de mirar)")
        if self.lado not in ("mayor", "menor"):
            raise ValueError("lado: 'mayor' (edge) o 'menor' (futilidad)")
        if not self.log_k:
            self.log_k = [0.0] * len(self.fracciones)
        span = (self.mu0 - self.piso) if self.lado == "mayor" else (self.techo - self.mu0)
        self._lam = [c / span for c in self.fracciones]

    def agregar(self, x: float) -> float:
        if not self.piso <= x <= self.techo:
            raise ValueError(f"LIMITE_VIOLADO: {x} fuera de [{self.piso}, {self.techo}] declarado")
        d = (x - self.mu0) if self.lado == "mayor" else (self.mu0 - x)
        self.log_k = [lk + math.log1p(l * d) for lk, l in zip(self.log_k, self._lam)]
        return self.e_valor

    @property
    def e_valor(self) -> float:
        m = max(self.log_k)
        return math.exp(m) * sum(math.exp(v - m) for v in self.log_k) / len(self.log_k)


@dataclass
class MonitorCandidato:
    """Edge y futilidad a la vez, sobre la secuencia de operaciones netas de UNA regla congelada (réplica, holdout o paper)."""
    piso: float
    techo: float
    mu_util: float                 # efecto útil mínimo por operación (neto); futilidad si se demuestra E[x] < mu_util
    alfa: float = 0.05
    alfa_futilidad: float = 0.10
    mu0: float = 0.0
    n: int = 0
    suma: float = 0.0

    def __post_init__(self):
        if not self.mu0 < self.mu_util:
            raise ValueError("mu_util debe superar a mu0")
        self.edge = EProceso(self.mu0, self.piso, self.techo, "mayor")
        self.fut = EProceso(self.mu_util, self.piso, self.techo, "menor")

    def agregar(self, xs) -> dict:
        for x in ([xs] if isinstance(xs, (int, float)) else xs):
            self.edge.agregar(float(x)); self.fut.agregar(float(x)); self.n += 1; self.suma += float(x)
        return self.estado()

    def estado(self) -> dict:
        e, f = self.edge.e_valor, self.fut.e_valor
        if e >= 1 / self.alfa: est = "EDGE_CONFIRMADO"
        elif f >= 1 / self.alfa_futilidad: est = "REFUTADO_FUTILIDAD"
        else: est = "SIN_DECIDIR"
        return dict(estado=est, n=self.n, media=self.suma / self.n if self.n else None, e_edge=e, umbral_edge=1 / self.alfa,
                    e_futilidad=f, umbral_futilidad=1 / self.alfa_futilidad, mu_util=self.mu_util, cotas=[self.piso, self.techo],
                    garantia="Ville: válido mirando en cualquier momento; cotas declaradas antes de mirar")


def combinar_e(*e_valores: float) -> float:
    """Producto de e-valores de muestras INDEPENDIENTES y secuenciales (réplica, holdout, paper): sigue siendo un e-valor."""
    out = 1.0
    for e in e_valores:
        if e < 0: raise ValueError("un e-valor no puede ser negativo")
        out *= e
    return out

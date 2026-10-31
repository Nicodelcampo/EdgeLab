"""Variante τ de `u1_racimos_grilla` (U1-RACIMOS-GRILLA-ES y -NQ): ver `variante_tau`."""
from edgelab.research import u1_racimos_grilla as _base
from edgelab.research.variante_tau import envolver

envolver(_base, globals())

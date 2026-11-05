"""Variante τ de `u1_zonas` (U1-ZONAS-ES y U1-ZONAS-NQ): ver `variante_tau`."""
from edgelab.research import u1_zonas as _base
from edgelab.research.variante_tau import envolver

envolver(_base, globals())

"""Variante τ de `u1_cfd` (U1-ES-GRILLA y U1-YM-GRILLA): ver `variante_tau`."""
from edgelab.research import u1_cfd as _base
from edgelab.research.variante_tau import envolver

envolver(_base, globals())

"""Variante τ de `u1_zonas_avcl` (U1-ZONAS-AVCL-NQ): ver `variante_tau`."""
from edgelab.research import u1_zonas_avcl as _base
from edgelab.research.variante_tau import envolver

envolver(_base, globals())

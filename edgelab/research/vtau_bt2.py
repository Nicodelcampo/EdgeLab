"""Variante τ de `u1_zonas_bt2` (U1-ZONAS-BT2-ES y -NQ): ver `variante_tau`."""
from edgelab.research import u1_zonas_bt2 as _base
from edgelab.research.variante_tau import envolver

envolver(_base, globals())

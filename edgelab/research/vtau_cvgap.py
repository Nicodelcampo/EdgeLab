"""Variante τ de `corredor_vol_gaps` (CVGAP-NQ): ver `variante_tau`."""
from edgelab.research import corredor_vol_gaps as _base
from edgelab.research.variante_tau import envolver

envolver(_base, globals())

"""Descubrimiento reproducible de reglas intradía: rejilla pre-registrada, nulo de máximo por sesión,
réplica cronológica, control de falsos descubrimientos y calibración con señal plantada.

Misma API en CPU (NumPy/Numba) y GPU (CuPy). Sin datos propios del proveedor ni reglas de ninguna estrategia concreta."""
from .spec import GridSpec,load_spec,spec_hash
from .backend import get_backend

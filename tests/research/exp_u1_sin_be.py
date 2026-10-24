"""Experimento de prueba para el embudo: U1-INDAGA sin el BE muerto (para pasar el preflight)."""
from edgelab.research.u1_indaga import NOMBRE, VARIABLES, EJES_ORDINALES, disparos, niveles  # noqa: F401
from edgelab.research import u1_indaga as _U

EJECUCIONES = [e for e in _U.EJECUCIONES if e[3] == 0]
BASE = {"N": 0, "x": 1, "A/H": 1, "ejecución": EJECUCIONES.index(("E1A", "T1", "S3", 0))}
INDICADORES = ["LUX-IMB"]

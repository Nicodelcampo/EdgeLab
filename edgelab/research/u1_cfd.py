"""U1-CFD (2026-10-25): la grilla de U1-ORO-GRILLA (U1-INDAGA completa × escala causal mensual 0,5/1/2) sobre otros CFD de Dukascopy
(USA500, USA30, EURUSD), con más historia (2024-01 → 2026-03) para que el tamiz tenga potencia. Mismo experimento que `u1_oro` (se
importa entero: la escala se ancla al rango M1 de USATECH, así que vale para cualquier instrumento); sólo cambia el nombre.
Pre-registro: `docs/research/u1_cfd_20261025/PREREGISTRO_U1_CFD.md`.
"""
from edgelab.research.u1_oro import (BASE, EJECUCIONES, EJES_ORDINALES, ESCALAS, INDICADORES, R_USATECH, VACIO, VARIABLES,  # noqa: F401
                                     disparos, escala_por_mes, niveles)

NOMBRE = "U1-CFD"

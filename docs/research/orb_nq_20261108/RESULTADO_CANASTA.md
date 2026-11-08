# Resultado: CANASTA-ORB por estabilidad (08/11/2026)

Estado: RESULTADO (pre-registro `PREREGISTRO_CANASTA.md`; selector `tools/canasta_orb.py`; series `SERIES_orb-series.json`,
200 sesiones del 05/08/2025 al 18/06/2026; salida `CANASTA_SELECCION.json`). Holdout **no abierto**.

- **Estables (≥ 4 de 5 sub-bloques positivos y t diario > 1):** sólo 2 de 72 reglas, y forman la canasta: YM 30 min, stop opuesto,
  objetivo 2R + NQ 30 min, stop opuesto, cierre (correlación 0,29).
- **Canasta:** +0,108 R por sesión, t diario 1,97.
- **Probabilidad de azar de la selección completa (nulo de signo por sesión, B = 1.000): p = 0,37.** El nulo encuentra canastas así
  de buenas en el 37 % de las réplicas (mediana del nulo 0; q90 = 2,89).
- **Decisión:** p ≥ 0,10 → la selección no se distingue del azar. Según la condición acordada con Nico, **no se gasta la apertura del
  holdout** de la familia.
- **Modelo de llenado:** last ± medio spread contra bid/ask real: correlación 0,996 del R total por regla, diferencia media −1,1 R por
  regla en 200 sesiones (≈ −0,01 R/op). El modelo del holdout es comparable.

**Lectura:** la ORB en NQ/ES/YM no tiene estabilidad suficiente: casi ninguna regla es positiva en 4 de 5 bloques, y las dos que lo
son no alcanzan a separarse del azar una vez contada la selección.

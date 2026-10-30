# Pre-registro: canasta de 12 reglas (firmado por Nico en sala, 2026-10-30; antes de abrir el holdout)
Reglas y celdas: las 12 actas de bt_res, sin cambios. Tope: se usa solo si mejora el Sharpe por sesión de DESC (<20260401) a 3 decimales.
Con tope: CVGAP-CFD-NQ, CVGAP-NQ, U1-ZONAS-AVCL-NQ. El resto sin tope.
Peso: riesgo igual, neto / desvío por operación en DESC. Sin exclusiones por perturbación ni por OOS.
Prueba única: t por sesión de la canasta en el holdout, una cola.

## Criterio fijado por delegación de Nico (2026-10-30)
Se evalúa una sola vez, con el stop aplicado, sobre todas las sesiones selladas desde 20261001.
- APRUEBA: media por operación > 0, t por sesión >= 1,28 (p <= 0,10), drawdown <= 10 R y ninguna regla aporta más del 50 % del resultado.
- PAPEL: media > 0 sin llegar a lo anterior. Sigue en simulado y no se reabre este holdout.
- NO APRUEBA: media <= 0.
Límite común: stop diario de -2 R. Tamaño máximo: 100 USD por R en cuenta de 50K (DD 2.000) y 0,2 % por R en Axi Select.
No se cambia nada después de abrir.

# GEX-1 — resultados (2026-10-06)
Corrida: Kaggle `nicolasbuttaro/edgelab-gex1-20261006` (v2), 20.000 permutaciones por bloques de 20 sesiones,
semilla 20261006, Holm sobre 12. Datos completos en `GEX1_RESULTADOS_20261006.json`.

| Fuente | Sesiones (gex<0) | Prueba | Diferencia gex<0 − gex≥0 | Holm | MDE |
|---|---|---|---:|---:|---:|
| Spot USA500 2023-01→2025-06 | 757 (39) | I1a rango/rango previo | +0,54 | **0,015** | 0,48 |
| | | I1b vol. realizada/previa | +0,59 | **0,006** | 0,46 |
| | | I2n \|última ½ h\|/σ previa | +0,66 | 0,78 | 1,88 |
| | | I2d pendiente continuación | +0,11 | 0,31 | 0,21 |
| | | I3 ac1 / ac1 de \|r\| | +0,02 / −0,07 | 0,93 / 1,00 | 0,08 / 0,11 |
| MES NT8 2025-09→2026-09 | 248 (**9**) | todas | — | ≥ 0,57 | sin potencia |

Lectura:
1. Hay **información en el régimen de gamma sobre la amplitud del día** (con gamma negativo el día es más amplio
   que su media reciente), en spot, con potencia suficiente. Es información, no un edge: no dice dirección.
2. **No** aparece la continuación de cierre ni la autocorrelación que predice la literatura, a este poder.
3. Futuros 2025-2026: el gamma fue positivo casi todo el año; para medir en futuros hace falta más historia
   (ES/MES 2023-2025 en NT8 o Kaggle) o esperar.
4. Antes de usar I1 como régimen: controlar por el retorno y |retorno| del día previo (gex<0 suele seguir a caídas
   fuertes y la volatilidad se agrupa sola). Si sobrevive, I1 sirve como **variable de régimen** (dimensionar
   riesgo, filtrar estrategias de reversión en días de gamma negativo), no como señal de entrada.

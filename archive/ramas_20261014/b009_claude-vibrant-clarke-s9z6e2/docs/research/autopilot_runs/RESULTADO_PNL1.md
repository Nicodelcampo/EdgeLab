# PNL-1 — resultado (5 reglas operables, P&L neto de costos; 2 pruebas confirmatorias, Holm 2; 62 s)

Datos crudos: `PNL1_RESULTADOS.json`; viabilidad según el mandato: `PNL1_VIABILIDAD.md`. Nivel familiar 0,0098.

## Veredicto: sin hallazgo; todas las reglas quedan en nivel C
**Confirmatoria (spot GC 2022-07 → 2025-06, muestra no usada para esta prueba):** `GC_ROD_LH_ALL` neto −12,4 USD por operación (bruto +12,4, por debajo del costo de 24,8), 38 % de aciertos, solo 42 % de trimestres positivos; `GC_ROD_LH_BIG` neto −26,5 (bruto −1,7), 25 % de trimestres positivos. p = 1 en ambas (media neta ≤ 0). **La pista de GC en su forma operable no se sostiene fuera de 2025-26.**

| Regla | Muestra | n | Neto USD/op | Trim. positivos | 5 mejores días |
|---|---|---:|---:|---:|---:|
| GC último 30 min, todos los días | futuro 2025-26 (de origen) | 274 | +135,9 | 0,80 | **58 %** del P&L |
| | spot 2025-26 (otra fuente, mismo período) | 390 | +61,6 | 0,80 | 69 % |
| | **spot 2022-25 (confirmatoria)** | 931 | **−12,4** | 0,42 | — |
| GC último 30 min, movimiento grande | futuro 2025-26 | 90 | +411,0 | 0,75 | 57 % |
| | **spot 2022-25 (confirmatoria)** | 313 | **−26,5** | 0,25 | — |
| GC 13:30 momentum 15 min (SCAN-1) | spot 2022-25 / futuro 25-26 | 932 / 276 | −30,2 / −5,1 | 0,00 / 0,60 | — |
| ES 07:30 reversión 60 min (SCAN-1) | spot 2018-25 / futuro 25-26 | 2.318 / 243 | −19,8 / −39,4 | 0,20 / 0,00 | — |
| ES 12:30 momentum 30 min (SCAN-1) | spot 2018-25 / futuro 25-26 | 2.318 / 243 | −21,0 / −80,7 | 0,20 / 0,00 | — |

## Lectura según el mandato
- **La regla de GC es rentable solo en 2025-26 y dependiente de pocos días:** los 5 mejores días explican 57-76 % del P&L (el máximo permitido es 50 %) y no hay P&L positivo en 2022-25. El simulador de challenge da pases altos en 2025-26 (p. ej. 0,42-0,68 en cuentas con cuotas sin verificar) **pero eso es el régimen de un año con crashes**, no un edge estable: falla estabilidad y diversificación → **nivel C**.
- **Las celdas de SCAN-1 son netas negativas en todas las muestras** una vez descontados los costos (bruto de +9 a +20 USD por operación en el spot, menor que el costo de 24,8-30).
- **Control sin ventaja:** en 2025-26 el control de dirección aleatoria da pases de 0,01 a 0,27 (el neto del control es −costo); las reglas «pasan más» que el control solo donde el bruto fue alto en 2025-26.
- Los umbrales no se usaron para descartar: se descartó por no confirmarse fuera de la muestra de origen.

**Costo:** 5 pruebas al registro global; riqueza de alfa 0,0098 menos el costo de la apuesta (sin acierto).

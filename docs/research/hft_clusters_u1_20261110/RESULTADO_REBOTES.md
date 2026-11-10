# Resultado HFT-REBOTES — siete definiciones de rebote en clusters grandes (E0-b)

Estado: RESULTADO (2026-11-10). Pre-registro `PREREGISTRO_REBOTES.md`. Datos `HFTC_rebotes.json` / `.csv`. Recomendaciones
`RECOMENDACIONES_rebotes.md`. Clusters: NQ 8 zonas (ancho ≥ X/2), ES 12 zonas (ancho ≥ X), vida 1.800 s. DESC 2025-07 → 2026-03.

| Definición | Reales | Control | Media real | Media control | Diferencia | IC90 | MDE | NQ | ES | Lectura |
|---|---|---|---|---|---|---|---|---|---|---|
| D0 base | 3.197 | 1.021 | −0,013 | +0,064 | −0,076 | [−0,142, −0,013] | 0,098 | −0,088 (2.658) | +0,046 (539) | EN_CONTRA |
| D1 fresco y lejano | 1.399 | 396 | +0,018 | +0,096 | −0,078 | [−0,171, +0,012] | 0,139 | −0,065 | −0,373 (124) | no concluyente |
| D2 aceptado y abandonado | 790 | 312 | +0,039 | +0,067 | −0,028 | [−0,161, +0,106] | 0,204 | −0,020 | −0,072 | no concluyente |
| D3 rechazado al nacer | 249 | 35 | +0,028 | +0,114 | −0,086 | [−0,346, +0,184] | 0,401 | −0,093 | sin eventos | sin muestra |
| D4 memoria | 297 | 97 | +0,088 | −0,052 | +0,139 | [−0,050, +0,322] | 0,282 | +0,174 (261) | −0,667 (36) | sin muestra |
| D5 deriva | 221 | 108 | −0,036 | +0,130 | −0,166 | [−0,349, +0,015] | 0,278 | −0,260 | −0,008 | sin muestra |
| D6 penetración fallida | 2.156 | 599 | −0,042 | +0,062 | −0,104 | [−0,180, −0,027] | 0,116 | −0,122 (1.945) | +0,515 (211) | EN_CONTRA |

**Ninguna nominada por BH (q 0,10).** Ninguna definición muestra un rebote real mayor que el del control; ningún desenlace real llega
al umbral económico 0,08 salvo D4 (+0,088, 297 eventos, sin muestra para afirmarlo).

## Lectura
1. **En NQ el cluster grande se atraviesa más que un nivel cualquiera.** D0 y D6 dan diferencias negativas con IC90 que no toca 0, y
   en NQ (la mayor parte de los eventos) el patrón se repite en D1, D3 y D5. Es lo opuesto a la hipótesis de defensa: tocar un cluster
   grande de NQ anticipa ruptura más que rebote. Es una pista para una hipótesis NUEVA de ruptura, no una conclusión: se pre-registra
   aparte y se prueba en datos no usados (réplica abr → sep), sin elegir umbrales mirando esta tabla.
2. **ES va en el sentido opuesto en D0 y D6** (+0,05 y +0,52 con 539 y 211 eventos). Con signos opuestos entre activos, la cifra
   combinada mezcla dos comportamientos. Nota de método (detectada al leer este resultado, NO aplicada para no cambiar reglas
   después de ver datos): el recomendador evalúa EN_CONTRA antes que INCONSISTENTE; para próximas familias conviene invertir ese orden.
   La versión corregida va en un commit aparte, declarada como cambio posterior.
3. **El control rinde positivo** (+0,06 a +0,13): un nivel donde el precio negoció 20–40 minutos antes tiende a frenar el precio.
   Ese efecto, sin clusters, es en sí una observación (estructura de precio), no medida acá como hipótesis.
4. **D4 (memoria) es la única a favor** (+0,139 en el conjunto, +0,174 en NQ) pero con 97 eventos de control y MDE 0,28 no dice nada todavía.

## Qué sigue
- Contexto (6 variables) lanzado con la definición elegida por la regla (sin nominadas → `D0_BASE`).
- Candidata para un pre-registro nuevo: **ruptura en clusters grandes de NQ** (la contraria de D0/D6), en la réplica abr → sep.

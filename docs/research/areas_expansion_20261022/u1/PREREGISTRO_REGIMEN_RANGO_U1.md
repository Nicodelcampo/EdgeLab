# Pre-registro — ¿el nulo de U1 en 2023-2025 es otro régimen? (2026-10-24)

Estado: VIGENTE — registrado antes de calcular. Pedido de Nico: «quizás ahora mismo el mercado está en un régimen donde sí es
rentable esa estrategia; ¿hay manera de acercarse más a confirmar con los datos que tenemos?»
North Star: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345` · Etapa EF: EF3 (exploratorio sobre datos ya vistos, sin holdout)

## Hipótesis
U1-CRUZADO gana en régimen de rango alto y no en rango bajo. 2025-2026 tuvo más rango que 2023-2025 (la densidad de señales
sigue al rango, ρ 0,91), así que el nulo de 2023-2025 podría ser régimen y no ausencia de efecto.

## Variable de régimen (causal, congelada)
- `rango_20` = media del rango diario de USATECH de las **20 sesiones anteriores** a la sesión de la operación
  (`topes/U1_DENSIDAD_20230101_20260930_dias.csv`, columna `rango`).
- **ALTO** si `rango_20` > mediana de todos los `rango_20` de sesiones **anteriores** (mediana expansiva, desde 2023-03).
  Nada usa información posterior a la sesión.

## Pruebas (4, registradas en el contador global antes de calcular)
Datos: OOS USATECH 2023-01 → 2025-07 con el fix 27 (`integridad_oos/U1_OOS_US_FIX27_*_operaciones.csv`).
- **H1 (T3, primaria):** media neta en ALTO > 0. IC90 por sesión (bootstrap por sesión, 20.000, semilla 20261024).
- **H2 (T3):** media ALTO − media BAJO > 0 (bootstrap por sesión).
- H1 y H2 con T1: informativas.

## Lectura fijada
- H1 con IC90 > 0 y H2 > 0: el régimen explica el nulo. «U1 sólo en ALTO» pasa a ser una hipótesis NUEVA. Se confirma solo
  en datos no usados (holdout desde el 2026-10-23, con esta misma regla de régimen congelada). No se promueve nada acá.
- Si no: el rango no explica el nulo. Se reporta con MDE y no se busca otra variable sobre estos mismos datos.
- Descriptivo: la fracción de operaciones de desarrollo (2025-08 → 2026-09) que caen en ALTO.

## Cómo podría refutarse
Que H1 dé IC90 que incluya o quede bajo 0, o que la diferencia ALTO−BAJO sea ≤ 0.

## Riesgo declarado
Es una vuelta más sobre datos ya vistos (OOS 2023-25). Una variable de régimen elegida después de ver el nulo es selección.
Por eso hay una sola variable (rango, la que ya explicó la densidad), un solo corte (mediana expansiva) y conteo en el registro.

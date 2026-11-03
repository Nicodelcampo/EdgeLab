# Propuesta: el tamiz FDR usa la cola normal y nomina ruido con n chico (03/11/2026)

Estado: PROPUESTA — requiere decisión de Nico (cambia la compuerta FDR; regla permanente: gates/FDR sólo humanos). No se tocó código.

## Hallazgo (causa raíz del bloqueo de U1-6E-CONFIRMA-GBP-C-R)
El preflight de ruido de `u1_confirma` nomina por FDR q 0,10 en **3 de 8 semillas** (11, 13 y 16). Bajo la nula global se esperaría
≤ 10 %. No es Storey: π0 = 1,0 en las tres. Las celdas nominadas tienen siempre **30 a 40 operaciones**, justo sobre `min_n = 30`, y
t por operación de 5,1 a 6,8.

`grilla_masiva.estadisticas` convierte el t en p con la **cola normal** (`_cola_superior` = 1 − Φ(t)). Con m ≈ 1,7 millones de celdas
evaluables, el umbral de BH para la primera nominación es q/m ≈ 5,9e-8: exactamente donde la normal y la t de Student con n − 1 grados de
libertad se separan en dos o tres órdenes de magnitud.

| t | normal | t(29) | t(39) |
|---|---|---|---|
| 5,2 | 1,0e-7 | 7,3e-6 | 3,3e-6 |
| 5,8 | 3,3e-9 | 1,4e-6 | 4,9e-7 |
| 6,8 | 5,2e-12 | 9,1e-8 | 2,0e-8 |

Con la cola t(n − 1), **ninguna** de las 8 celdas nominadas sobre ruido pasa el umbral de 5,9e-8. Esas celdas además tienen asimetría
de −2,3 a +1,4, y el t por sesión (4,2 a 5,4) es menor que el t por operación, por la dependencia intrasesión.

## Alcance
El sesgo es anticonservador sólo en celdas con **n chico y m enorme** (grillas de millones de celdas). Para n ≥ ~200 la diferencia
normal/t es despreciable al nivel de los umbrales usados. Las nominaciones DESC históricas con n de 30 a 60 en grillas U1 (millones de
celdas) merecen re-chequearse con la cola t. Las réplicas, el OOS y el holdout no dependen de esto: usan otro estadístico con su propio nivel.

## Opciones (decide Nico)
1. **Cola t de Student con n − 1 gl** en `estadisticas` (recomendada). Es la cola correcta del mismo t, no relaja ni endurece por diseño.
   El costo es una llamada vectorizada a la t.
2. Subir `min_n` (p. ej. a 60) en grillas con m > 1e6. Más tosco y pierde celdas legítimas.
3. Usar el t agrupado por sesión (el de Romano-Wolf) también en el tamiz. Más correcto ante dependencia, pero cambia más cosas a la vez.

Con la opción 1, U1-6E-CONFIRMA-GBP-C-R se relanza y se re-chequean las nominaciones DESC con n < 60 de las campañas vigentes.

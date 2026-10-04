# Barrido horario, etapa A — GC, ZB, 6J, 6E (pre-registro, 2026-10-04)

Estado: escrito ANTES de calcular. Exploratorio. Solo datos previos al holdout (`< 2026-06-30T22:00Z`); no existen datos posteriores de estos activos en Kaggle. Los datasets son `PARTIAL_CONTRACT_MONTH_SLICES`, no certificados para backtest continuo: EF0 los marcaría como NO ELEGIBLES. Por eso el resultado es exploratorio y no puede confirmar nada.

## Pregunta
¿Existe, en estos activos, estructura direccional por hora del día que justifique siquiera buscar reglas de entrada y salida? No se prueban stops, objetivos ni parámetros de salida en esta etapa.

## Datos y construcción
- Ticks de `edgelab-ticks-{gc,zb,6j,6e}-preholdout`; solo ticks de tipo trade; corte estricto `< 1782856800000000000` ns.
- Serie continua: contrato líder por volumen de la sesión completa anterior, monótono, sin back-adjustment, reinicio de estado en cada roll (política de EdgeLab). Se descarta la sesión sin ticks del líder; no se interpola.
- Elegibilidad de sesión: volumen total ≥ 50 % de la mediana del contrato en el tramo en que es líder. Sesiones elegibles ordenadas por fecha de trading (CT, 17:00–16:00).
- Oportunidades: mismas que la estrategia original: franja de 15 minutos hora de Chicago, señal en la barra de 1 minuto cuyo sello es franja + 1 min, entrada en el primer tick de la barra siguiente, salida tras `h` minutos; solo si quedan ≥ `h` minutos de sesión.

## Rejilla (fija)
- 96 franjas × 4 holdings (15, 30, 60, 120 min) × 3 condiciones = **1.152 celdas por activo**.
- Condición: ninguna; signo del cambio de cierre de los 15 minutos previos positivo; ídem negativo (igual definición que la estrategia). Todos los días de la semana juntos.
- Se excluyen las celdas con menos de 40 oportunidades.

## Estadístico
- Retorno de la oportunidad: `r = último precio de salida − último precio de entrada` en ticks (bruto).
- Para quitar tendencia y volatilidad del día: a cada `r` se le resta la media de `r` de esa sesión sobre todas las franjas del mismo holding. Se llama `r~`.
- Por celda: `S = Σ r~`, `V = Σ_sesiones (suma de r~ de la sesión en la celda)²`, `z = S / √V`. Se prueba **en dos colas** (largo o corto).

## Nulo
- Signo de cada sesión sorteado ±1 de forma independiente (mismas sesiones y celdas, así se conserva la correlación entre celdas dentro de la sesión). 20.000 sorteos, semilla 20261006.
- **Estadístico de decisión:** `max |z|` sobre todas las celdas. `p_max = (1 + #{max nulo ≥ real}) / (1 + sorteos)`.
- Verificación del nulo antes de aplicarlo a datos reales: con ruido simétrico sintético debe rechazar a ≈ 5 %.

## Prueba secundaria (réplica con corte temporal)
- Primeras 70 % de las sesiones: se eligen las 5 celdas de mayor |z|, con su signo.
- Últimas 30 %: para esas 5 celdas se calcula el z con signo fijado y su p unilateral por el mismo nulo de signos; corrección de Holm (5 pruebas).
- Para esas celdas se reporta además la media neta real tick a tick (libro: largo al ask, corto al bid; salida al lado contrario) menos comisión de ida y vuelta de USD 4,50 para los cuatro activos: GC 0,45 ticks, ZB 0,144, 6J y 6E 0,72.

## Reglas de decisión (fijadas antes)
- **Estructura direccional detectada** en un activo si `p_max ≤ 0,05` **y** al menos una de las 5 celdas de la prueba secundaria tiene p de Holm ≤ 0,05 en las sesiones reservadas **y** media neta real > 0 tras comisión.
- Si solo se cumple `p_max ≤ 0,05`: «estructura sin replicar», no se avanza.
- Si `p_max > 0,05`: **sin estructura distinguible del azar** con estos datos en ese activo; se cierra la etapa A para él.
- Ningún resultado de la etapa A es un edge; solo habilita escribir un pre-registro de la etapa B (salidas) para ese activo.

## Prueba combinada (secundaria, solo para divisas)
6E y 6J juntos: se suma `r~` de ambos por celda y sesión (misma franja, holding y condición) y se repite el estadístico y el nulo sobre esa cesta, con la misma regla.

## Contador de pruebas
Cada activo suma 1.152 pruebas a una campaña propia; la combinada de divisas suma 1.152 más. Total nuevo: 5 campañas, 5.760 pruebas.

## Predicción registrada
Espero `p_max > 0,05` en la mayoría de los activos. Las comisiones de oro y bonos son bajas en ticks, así que el resultado más probable donde haya algo es en 6E o 6J.

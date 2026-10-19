# Barrido horario, etapa B — GC (pre-registro, 2026-10-04)

Estado: escrito ANTES de calcular. Exploratorio. Mismos datos que la etapa A (`edgelab-ticks-gc-preholdout`, ticks de trade, corte estricto `< 2026-06-30T22:00Z`, serie continua por volumen, sesiones elegibles ≥ 50 % de la mediana del contrato). Datos parciales: el resultado no puede confirmar nada.

## Celda base (de la etapa A, fijada)
Franja 04:15 hora de Chicago, tras una subida de los 15 minutos previos (cierre de la barra de señal menos cierre 15 minutos antes > 0), **corto**, salida por tiempo a 15 minutos. Ejecución de libro: la señal se evalúa en la barra de cierre `franja + 1 min`, la entrada es el primer tick ≥ `franja + 2 min` (vende al bid), la salida es el primer tick ≥ `entrada + h` (compra al ask). Comisión de ida y vuelta USD 4,50 = 0,45 ticks (tick = USD 10). Esta celda debe reproducir en la etapa B las cifras de la etapa A (128 operaciones, neto ≈ +21,3 ticks); si no coincide, se corrige el simulador antes de seguir.

## B0 — Auditoría de datos (sin retornos)
1. Cobertura: sesiones elegibles frente a días hábiles del calendario, sesiones faltantes por contrato.
2. En la ventana de la celda base (`entrada .. entrada + 60 min`): número de ticks de trade por sesión, spread de libro (ask − bid, en ticks) frente al spread mediano de todo el día, saltos de precio entre ticks consecutivos.
3. **Marca de calidad** si (a) más del 10 % de las sesiones elegibles tienen menos de 100 ticks de trade en esa ventana, o (b) hay algún salto entre ticks consecutivos mayor de 100 ticks (10 puntos) dentro de la ventana. Con marca, el resultado de GC se descarta como posible artefacto de datos y no se sigue con B1 ni B2.

## B1 — Robustez de la celda base (descriptivo, con reglas)
Es **robusta** solo si se cumplen **todas**:
- **R1.** Media neta > 0 con 2 ticks de deslizamiento extra por operación (ida y vuelta) en el primer 70 % de las sesiones **y** en el último 30 %.
- **R2.** Quitando las 5 mejores sesiones (por neto de la operación), la media neta sigue > 0.
- **R3.** Entre las 8 celdas vecinas (franjas 04:00, 04:15, 04:30 × holdings 15, 30, 60, excluyendo la base; misma condición «tras subida» y misma dirección corta), al menos 6 tienen el mismo signo de z que la base.
- **R4.** Entre los contratos con ≥ 15 operaciones, la media neta es > 0 en la mayoría.
- Se reportan además, sin regla: resultado por mes; media neta de «corto sin condición» en la misma franja y holding, y de «largo tras bajada» (espejo); fracción de sesiones con neto positivo.

## B2 — Barrido de entradas y salidas, ejecución tick a tick
Solo se corre si B0 no marca y B1 es robusta. Dirección fija: corto.

| Dimensión | Valores |
|---|---|
| Franja de entrada | 04:00, 04:15, 04:30, 04:45 |
| Umbral de la subida previa (≥ k ticks en 15 min) | 1, 10, 20 |
| Holding (tope temporal) | 5, 10, 15, 20, 30, 45, 60 min |
| Stop (ticks adversos) | ninguno, 10, 20, 30, 50 |
| Objetivo (ticks a favor) | ninguno, 10, 20, 30, 50 |

**4 × 3 × 7 × 5 × 5 = 2.100 variantes.** Stop: se activa cuando el último precio toca el nivel adverso y se llena al lado adverso del libro (peor entre ese nivel y el libro). Objetivo: último precio que lo atraviesa en 1 tick, llenado al nivel. Si no se activa ninguno, salida por tiempo. Stop-first si ambos en el mismo tick.

**Estadístico:** por variante, `z = Σ (neto_real − neto_promedio_de_direcciones) / √V`, donde para cada sesión se calculan los resultados netos corto y largo con las mismas reglas, `neto_promedio` es su media y `V = Σ ((corto − largo)/2)²`. Es el equivalente, con costos y salidas reales, del nulo de signo de la etapa A.
**Nulo:** signo de dirección sorteado por sesión (corto/largo), 20.000 sorteos, semilla 20261007; estadístico de decisión: máximo de `z` sobre las 2.100 variantes.
**Réplica:** variante elegida por mayor `z` en el primer 70 % de sesiones; evaluada en el último 30 % con su nulo propio (unilateral).

## Reglas de decisión (fijadas antes)
- **Mejora de entrada/salida detectada** si `p_max ≤ 0,05` (muestra completa) **y** la variante elegida en el 70 % tiene media neta > 0 y p ≤ 0,05 en el 30 % reservado.
- Si no: **ninguna variante se distingue de la celda base**; la celda base sigue siendo el único candidato.
- Para pasar a la etapa C (congelar una configuración y probarla hacia adelante) hace falta B0 sin marca y B1 robusta, con la celda base o con la variante detectada.

## Contador de pruebas
B1 suma 8 pruebas (vecinas); B2 suma 2.100. Total nuevo: 2.108 en una campaña.

## Predicción registrada
Espero que la celda base falle al menos una de R1–R4 y que `p_max` de B2 sea > 0,05.

# SELECTIVIDAD: regla propia de una sola perilla — la dirección de un día de tendencia limpio continúa al día siguiente, con dosis-respuesta pre-registrada (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr.
- **Pedido de Nico:** «la selectividad como perilla única: R, Z y probablemente T la comparten. Una regla propia con una sola perilla y
  dosis-respuesta pre-registrada sería más fácil de validar que una grilla».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC de A5; EF4 en REP una vez con LORD++ sólo si se nomina y con potencia K49. **Familia:** `SELECTIVIDAD_A5` (nueva;
  padres `FUNDEDSYNC` — la idea viene de la dosis-respuesta de Z — y `DIA_TENDENCIA_A5`).
- **Herramienta:** `tools/selectividad.py correr|desc|rep`: motor calibrado `sqx_catalogo.simular` (K28) con camino M1, sobre barras RTH de 15
  minutos (sólo minutos 09:30–15:59); ATR20 de sesión CME de `m1_largo.atr20`; fricción canónica; `holdout.a5_bloque`. Intradía: operable en
  LucidFlex. Sin simulador propio.

Antecedentes: Z-PICO y RESULTADO_RAPIDA_Y_SEVERIDAD (dosis-respuesta de severidad en NQ/ES/RTY; correlación diaria ≈ 0 con T y R),
F-DIA-TENDENCIA-CLASES-NUEVAS-NULAS (el día de tendencia previo NO predice si hoy es día de tendencia: medido sin retornos sobre la CLASE del día;
acá se prueba otra cosa: la DIRECCIÓN y su P&L), F-RUPTURA-VIVE-DEL-DIA-DE-TENDENCIA, MIRADA_HUMANA_20261119.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36, K40, K48 causalidad, K49, K51, K52, K53, K55/K56).

Diagnóstico de mecanismo: una sola perilla (el percentil de pureza), sin grilla; las cinco bandas son disjuntas y fijas, y se publican operaciones
por banda y la descomposición por meses (Episodios) de la banda superior con tools/diagnostico_grilla.py.

Potencia previa: una operación por día e instrumento: NQ+ES+YM+RTY en DESC ≈ 11.000 operaciones; banda superior (5 %) ≈ 550 → ee ≈ 0,04–0,05 R; la
pendiente entre cinco bandas con ≈ 2.000 operaciones por banda tiene ee ≈ 0,01–0,015 R por banda: detecta pendientes de ≈ 0,03 R por banda.

## Justificación económica
- Un día de tendencia «limpio» (el precio casi no retrocede contra su dirección) refleja flujo direccional persistente (rebalanceo, cobertura de
  opciones que persigue el movimiento, ejecución de órdenes grandes repartidas en días). Ese flujo no termina con la sesión: el día siguiente
  sigue en la misma dirección. Cuanto más limpio el día, más persistente el flujo: dosis-respuesta.

## Regla (fija; nada se elige después de mirar)
- **Puntaje de pureza del día d** (RTH 09:30–15:59 del M1): dirección = signo(cierre − apertura); pureza = 1 − (máximo retroceso contra esa
  dirección desde el extremo corriente) / (máximo − mínimo del día). Días con rango nulo o sin RTH completo (< 380 minutos) no puntúan.
- **Perilla (la única):** percentil de la pureza del día d contra los 250 días RTH previos del mismo instrumento (causal: sólo pasado).
- **Operación:** en la apertura de las 09:30 del día siguiente, a mercado, en la dirección del día d; stop de catástrofe 0,25 × ATR20 de sesión
  (media de los rangos de las 20 sesiones CME previas); salida al cierre de la última vela de 15 min del día (16:00). R = (resultado − fricción)
  / (0,25 · ATR20).
- **Bandas (disjuntas, fijas):** B1 [0; 0,50), B2 [0,50; 0,70), B3 [0,70; 0,85), B4 [0,85; 0,95), B5 [0,95; 1].
- Instrumentos: NQ, ES, YM, RTY (RTY desde 2017-07).

## Pruebas (2, BH q 0,10)
- **P1 dosis-respuesta:** pendiente de la regresión del R neto de cada operación sobre el índice de banda (1…5), todas las operaciones de DESC
  juntas; IC por bootstrap de sesiones; p unilateral (pendiente > 0).
- **P2 regla operable:** R neto de B5 > 0 (bootstrap por sesión, p unilateral).
- REP: lectura única con LORD++ de las nominadas con potencia en días ≥ 0,8 (K49).
- **Cómo podría refutarse:** pendiente ≤ 0 (no hay dosis-respuesta) o B5 con neto ≤ 0.
- **Contador:** 2 pruebas en `SELECTIVIDAD_A5`.

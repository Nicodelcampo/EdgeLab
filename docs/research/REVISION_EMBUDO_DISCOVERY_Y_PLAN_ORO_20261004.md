# Revisión del embudo / módulo de descubrimiento y plan de potencia para oro (2026-10-04)

Revisión pedida por Nico sobre `edgelab/funnel/`, `edgelab/discovery/` y el traspaso `HANDOFF_20261004.md`. Arreglos y
registros encargados por él. **Nada de esto corre resultados**: los tests nuevos de oro quedan pre-registrados y esperan
el OK explícito de Nico (regla STOP).

## 1. Veredicto de la revisión
Estructura correcta y de buen nivel: pre-registro con hash obligatorio, nulo de máximo por sesión (signos sorteados),
D0/D1/D2 con D2 sellado, titular por familia con meseta, calibración con señal plantada (falsos positivos 5 %), paridad
CPU/GPU como requisito y contador encadenado. Dos ajustes y tres advertencias:

1. **Arreglo — contador GLOBAL único.** Había cuatro `trial_registry.jsonl` por familia y ninguno con las campañas de
   `foundation`. Nuevo `docs/research/TRIAL_REGISTRY_GLOBAL.jsonl` (`tools/registro_global.py`, idempotente): 47
   campañas, **153.095 pruebas** al 2026-10-04 (incluye NQ-CRUCE25-CLIMA 12, ES-ESCALONADAS 32 + 180, MNQ-ESCALONADAS
   648 y los dos chequeos L2 target-free). `tools/discovery_scan.py` usa ese archivo por defecto. `TrialRegistry.ensure`
   ahora funciona en Windows (sin `fcntl`; un solo escritor por regla del proyecto).
2. **Regla — rejillas por familia, no la rejilla d1 completa.** La calibración propia da potencia 13 % a 0,3 desvíos y
   80 % a 0,5 con 98.304 celdas. Los efectos intradía plausibles son 0,1–0,3: la rejilla grande casi garantiza «nada».
   Toda corrida de descubrimiento real debe ser una **familia chica con hipótesis económica escrita** (≤ 3 parámetros
   libres, como pide el playbook). La GPU queda para nulos y calibración, no para justificar rejillas más grandes.
3. **Advertencia — celda GC 04:15.** (a) Con Bonferroni entre los 4 activos de la etapa A no pasa (p_max 0,0157 >
   0,0125); (b) EF0 la marcaría no elegible (tramos parciales de contrato); (c) en las lecturas intermedias de la etapa C
   el **corto sin condición** rinde igual o más que la celda condicionada: lo que se repite parece un sesgo vendedor de
   franja (¿subasta LBMA 10:30 Londres?), no el filtro «tras subida».
4. **Advertencia — spot ≠ futuros.** XAU/USD Dukascopy tiene spread ≈ 5,8 ticks GC vs 3 en COMEX: la réplica en spot
   valida la idea, no el costo del instrumento operable.
5. **Advertencia — dos marcos.** EF0–EF5 (embudo) y D0/D1/D2 (descubrimiento) conviven: el contador global (punto 1) es
   lo que los une; cualquier campaña nueva se registra ahí.

## 2. Datos nuevos de oro (descarga de Nico vía JForex, `tools/jforex/HistDownloader.java`)
XAU/USD Dukascopy, ticks bid/ask, **2024-01-01 → 2026-09-30** (en curso; dataset privado Kaggle
`nicolasbuttaro/edgelab-dukascopy-xauusd-ticks-m1`). Calidad de lo bajado: 0 desordenados, 0 bid > ask, 0 precios ≤ 0,
M1 de Dukascopy = M1 derivado de ticks. `tools/barrido_horario_etapa_c_spot.py` acepta ahora `DUKAS_BIN=<carpeta de
.bin>` (mismas horas 07–12 UTC que el feed por horas), sin la descarga lenta del datafeed (que devuelve HTTP 429).

## 3. Pre-registro de los tests de potencia para oro (escrito ANTES de cargar estos datos en ningún test)
### 3.1 Celda 04:15 — etapa C sin cambios de decisión
- **Enmienda C3 (fuente):** la ventana de decisión 2026-07-01 → 2026-09-30 se corre una sola vez con la fuente JForex
  (mismo proveedor Dukascopy, mismo spot, bid/ask). Regla de decisión C1/C2 intacta (celda condicionada congelada,
  nulo de dirección por sesión 20.000 sorteos, semilla 20261008, unilateral).
### 3.2 Celda 04:15 — muestra nueva 2024-01-01 → 2025-07-31 (nunca usada: la selección fue con GC 2025-08 → 2026-06)
- **H1:** la celda congelada (`config/gc_cell_0415/gc_cell_v1.json`, corto tras subida de 15 min, salida 15 min).
- **H2:** corto a las 04:15 **sin condición**, salida 15 min. Origen declarado: surge de mirar R1/R2 de la etapa C;
  por eso se prueba sólo en esta muestra nueva y se reporta como hipótesis derivada.
- Mismo simulador de spot, costos 0,45 ticks + spread real, elegibilidad ≥ 50 cotizaciones; nulo de dirección por sesión
  (20.000, semilla 20261011), unilateral; **Holm sobre H1 y H2**. Decisión: replica si Holm ≤ 0,05 y neto > 0.
- Descriptivo: por año, invierno/verano de EE. UU. (la franja LBMA se mueve en UTC) y «largo tras bajada» como espejo.
### 3.3 EMA 200/500/2000 de MGC — muestra spot previa a MGC
- Mismas señales (cruce EMA200/EMA500 con EMA500 del mismo lado de EMA2000, decisión al cierre, entrada en el tick
  siguiente) reproducidas en spot con la herramienta de equivalencia de la rama; **sólo el tramo de spot anterior al
  primer día de MGC usado** en `PREREGISTRO_FAMILIA_20261004.md`. Pruebas T1 (media de la familia de 21 celdas) y T2
  (máximo z sobre 5 horizontes) idénticas a las de MGC, semilla nueva 20261012. Costo: spread real + comisión MGC.
- Antes de correr hay que fijar por escrito el primer día de MGC usado (dato del pre-registro de MGC, a verificar).

Registro en el contador global: estas campañas se registran al correrlas (H1+H2 = 2; EMA T1+T2 = 21 + 5).
**Se corren sólo con OK de Nico.**

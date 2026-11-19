# ROBOQUANT: ocho reglas extraídas del Marketplace de Roboquant (Futuros CME) en M1 de ES, NQ y YM 2006–2025 (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — se commitea antes de calibrar y de correr.
- **Pedido de Nico:** «fijate que abri el marketplace de roboquant donde hay estrategias gratis para extraer ... extraelas y subilas al repo».
- **Catálogo y Diseño:** `../option_alpha_20261118/CATALOGO_EXTENDIDO_OA_Y_ROBOQUANT.md` y `DISENO.md`.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC, EF4 en REP y EF5 en HOLDOUT (partición `HOLDOUT-A5`). **Familia:** `ROBOQUANT_A5` (nueva).
- **Módulo y campaña:** `edgelab/research/roboquant_a5.py` (contrato `tablas.py`, motor único `ejecucion.py`) + `CAMPANA.json` + `tools/a5_campana.py`.

Antecedentes: «roboquant nq precision bot noise band zarattini vwap pullback orb retest ivb» — familias parecidas: OPTION_ALPHA_A5, ORB_RR_MENOR, ORB_VARIANTES; NO_REPETIR: F-REELS-20261108, F-ORB-EMA20-NQ-STOP-OPUESTO, F-ORB5-BRUTO-ESTABLE; código: edgelab/stats/fixed_b.py:145, edgelab/discovery/features.py:20, tools/sandbox/l3_power.py:36

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (incluidas K40–K49: stop M1 en su nivel, columnas de identidad, variables conocidas antes de entrar, potencia en días).
- §1: cadena estándar (`tablas.py` + `a5_campana.py`), población declarada y causalidad verificada en `preflight`.
- §2: datos locales `M1NT8` verificados con `PROCEDENCIA.json` (`ES`, `NQ`, `YM`, `cboe_volatility_daily.parquet`, `us_market_events_calendar_2006_2026.parquet`), partición A5 y calibración obligatoria M1↔ticks (K30/K40) antes de correr DESC.
- §3: R neto con costos canónicos de `edgelab/costos.py` (mini y micro reportados; umbral de fricción operable ≤ 0,08 R) y unidades normalizadas por `ATR20` / `R15` / `R30` (K36).
- §4: confirmación jerárquica (REP con LORD++ → Holdout A5 con potencia ≥ 0,80 → instrumentos sin usar `RTY` y `EMD`).

Potencia previa: estimación conservadora previa a mirar desenlaces (efecto supuesto `0,10 R`, `sd_op ≈ 1,25 R`, α LORD++ `0,0125`):
- Frecuencia esperada en ventana A5 (`2006–2025`, 3 índices × ~250 sesiones/año): ~`10–18 ops/mes` por índice (~`30–54 ops/mes` en `ES+NQ+YM`) para `RQ1/RQ3/RQ4/RQ5/RQ6/RQ8` y ~`5–10 ops/mes` por índice para `RQ2/RQ7`.
- En DESC (137 meses × 3 índices): `N ≈ 1.400–5.500` operaciones por regla; en REP (39 meses × 3 índices): `N ≈ 400–1.500` operaciones por regla. Para detectar `0,10 R` con `sd = 1,25` al 80% de potencia con α `0,0125` se requieren ~`1.460` operaciones → si DESC nomina con efecto ≥ `0,12 R` o se evalúa la canasta en REP/HOLDOUT hay potencia suficiente; lo menor queda `SIN_POTENCIA`.

## 1. Justificación económica
- **`RQ1` (`NQ Precision Bot 10:00 Snapshot + 8m Time Close`):** evita el ruido de mechas durante `09:45–09:59 ET` tomando una foto en el cambio horario de las `10:00 ET` con filtro de régimen `ATR14/ATR50` y salida por tiempo a los `8m`, capturando la primera ola de ejecución institucional de las 10:00 AM.
- **`RQ2` (`Friday Range Revisit`) & `RQ3` (`T-Mean Reversion`):** capturan asimetrías inter-día documentadas en futuros de índices (reversión bajista tras fallo en superar el máximo previo y rebote tras cierre diario negativo).
- **`RQ4` (`Anchored VWAP + EMA11 3m`) & `RQ6` (`Trend Day Pullback 5m`):** operan alineación y retroceso hacia el precio medio ponderado de la sesión (`VWAP` típico) bajo baja volatilidad relativa (`ATR14 <= 1.12·ATR50`).
- **`RQ5` (`Noise-Band Momentum — Zarattini et al. 2024`), `RQ7` (`ORB 15m Retest Inside PDH/PDL`) & `RQ8` (`IVB 30m Contraction`):** sustituyen rupturas crudas por bandas de ruido de 60 sesiones ajustadas por hora del día (`RQ5`), entrada en retesteo sólo cuando el ORB abre dentro del rango del día previo (`RQ7`) y ruptura tras compresión del Initial Balance de 30m (`RQ8`).

## 2. Espacio de eventos y población
- **Espacio:** 8 reglas del Marketplace de Roboquant (`RQ1`–`RQ8`) más sus 7 controles directos (`RQ1N`, `RQ2N`, `RQ3N`, `RQ4N`, `RQ5N`, `RQ7N`, `RQ8N`).
- **Fuera de esta corrida:** `Coinflip eval pass` (gambling de evaluación con PF 0.97), `Bitcoin SuperTrend` (cripto, fuera de futuros CME de índices en M1NT8) e instrumentos `RTY` y `EMD` (reservados para confirmación fuera de muestra §4.3).
- **Población:** sesiones RTH (`09:30–16:00 ET`) sobre M1 real de NT8 (`ES`, `NQ`, `YM`), `2006-01-06 → 2025-07-31` (calibración en ticks reales `2025-08-05 → 2026-03-31`).

## 3. Cómo podría refutarse
- Cualquier regla queda refutada si su `R` bruto o neto es `<= 0` con potencia suficiente en DESC/REP/HOLDOUT, si su fricción mediana excede `0,08 R`, o si su contraste frente al control (`RQk - RQkN`) es `<= 0` demostrando que el filtro de régimen/contexto (`ATR14/50`, `Prev_High <= Prev2_High`, sesión roja previa, `VWAP`, `Inside PDH/PDL` o contracción de IB) no aporta ventaja real.

## 4. Contador y linaje
- **Pruebas en exploración DESC (`a5_campana.py`):** `8` reglas absolutas + `7` contrastes contra control = **`15` hipótesis** en la familia BH (`q = 0,10`), **Los filtros macro (`vix_bajo`, `no_fomc`, `sin_early_close`, `ivr_20`) NO se evalúan en esta corrida** (enmienda de Claude, 2026-11-19, antes de calibrar y de correr): mirarlos serían pruebas fuera de la familia; si una regla sobrevive REP se pre-registran como familia hija.
- **Enmienda K49 (2026-11-19, antes de correr):** la potencia de arriba cuenta operaciones; con tres índices el mismo día no son independientes. REP se lee sólo para nominadas con potencia ≥ 0,80 en DÍAS al nivel LORD++ (`a5.plan_lectura`, automático en `tools/a5_campana.py rep`); las demás quedan `SIN_POTENCIA_PREVIA`.
- **Linaje (enmienda 2026-11-19):** hija de `ORB_A5` (RQ1, RQ7 y RQ8 son rupturas del rango de apertura y RQ5 es la banda de ruido de Zarattini, ya medida en ORB_A5 como «Noise Area»): hereda su multiplicidad.
- **Linaje:** familia nueva `ROBOQUANT_A5` (complementaria a `OPTION_ALPHA_A5`). Sensibilidad reportada en años limpios `2006–2011`.

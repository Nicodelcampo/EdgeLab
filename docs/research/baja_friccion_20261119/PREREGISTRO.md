# BAJA-FRICCION: ocho reglas de stops amplios (Roboquant 32/32 + TradingView OS + Williams/Crabel) en M1 de ES, NQ, YM y GC 2006–2025 (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de calibrar y de correr.
- **Pedido de Nico:** «avanza en dos frentes, proponer acciones siguientes y continuar recolectando estrategias, ahora con esta nueva informacion».
- **Catálogo y Diseño:** `CATALOGO_ROBOQUANT_COMPLETO_Y_TRADINGVIEW.md` y `DISENO.md`, misma carpeta.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC, EF4 en REP y EF5 en HOLDOUT (partición `HOLDOUT-A5`). **Familia:** `BAJA_FRICCION_A5` (nueva).
- **Módulo y campaña:** `edgelab/research/baja_friccion_a5.py` (contrato `tablas.py`, motor único `ejecucion.py`) + `CAMPANA.json` + `tools/a5_campana.py`.

Antecedentes: «midday continuation gao baltussen noise band gap lube time at price avwap glowvwap omega volume zscore williams crabel dual thrust gc nq» — familias parecidas: ROBOQUANT_A5, EXTERNAS_A5, EXTERNAS_ESTRUCTURALES_A5, ORB_A5; NO_REPETIR: F-OPTION-ALPHA-FUTUROS, F-REELS-20261108, F-ORB-EMA20-NQ-STOP-OPUESTO, F-ORB5-BRUTO-ESTABLE, F-VENTAJA-EN-PUNTOS-NO-ESCALA; código: edgelab/research/externas_estructurales_a5.py:1, edgelab/research/roboquant_a5.py:1

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K36 unidad normalizada, K38 ajuste del diseñador, K40 stop M1 en su nivel, K48 causalidad, K49 potencia en días, K50, K51).

Potencia previa: evaluación conservadora previa a mirar desenlaces en **DÍAS** (`K49`, sesión compartida entre instrumentos correlacionados):
- Frecuencia esperada en ventana A5 (`2006–2025`, ~`250` sesiones/año × `4` instrumentos: `ES`, `NQ`, `YM`, `GC`): ~`10–20` sesiones/mes para `BF1/BF2/BF4/BF5/BF6/BF8` y ~`4–8` sesiones/mes para `BF3/BF7`.
- En DESC (`137` meses): ~`550–2.700` sesiones activas (~`1.500–8.000` operaciones agrupadas). En REP (`39` meses): `N_dias ≈ 160–750` días independientes. Con `sd_dia ≈ 1,10 R` y α LORD++ `0,0125`, detectar un efecto neto real de `0,15 R` en REP al `80%` de potencia requiere `n_dias >= 420` → sólo las nominadas que superen `plan_lectura(..., potencia >= 0,80)` en **DÍAS** podrán abrir REP (`K49`); las de menor potencia quedan `SIN_POTENCIA_PREVIA` para lectura conjunta con `GC`/`RTY`/`EMD` o forward.

## 1. Justificación económica
- **Por qué stops amplios (`>= 0,50 · ATR20_D1` a `1,0 · ADR20`):** tanto en `ROBOQUANT` como en `EXTERNAS_28`, la fricción fija (`~1,55 pts` NQ, `0,89 pts` ES) destruyó reglas con ventaja bruta positiva cuando el stop era chico (`<= 0,30 · ATR20`). Anclando `rg` entre `0,50` y `1,00 · ATR20/ADR20`, la fricción mediana esperada baja al entorno `0,015–0,05 R` en los `20` años (cumpliendo Fase 0 `<= 0,08 R`), dejando ver si el neto sobrevive en toda la muestra y por instrumento (incluido `GC`, descorrelacionado del flujo 0DTE de índices).
- **Mecanismos cubiertos:**
  - **`BF1` (`MNQ Midday Continuation`) & `BF2` (`Noise-Band Gap-Adjusted`):** momentum intradía académico de Gao (2018), Baltussen et al. (2021) y Zarattini et al. (2024) en versión limpia (sin el micro-trailing de 6 pts ni fechas excluidas del showcase Roboquant).
  - **`BF3` (`Pre-NY Sweep FU Retest`) & `BF4` (`Previous Day Extreme 25%`):** captura de liquidez / rechazo de extremos inter-sesión con stops en volatilidad diaria.
  - **`BF5` (`Ω Z-Score Double-Lens`) & `BF6` (`LUBE Time-at-Price`) & `BF7` (`GlowVwap Anti-Chop`):** rupturas filtradas por ausencia de congestión previa (`BF6`) o ausencia de clímax de rango (`BF5`), y pullbacks a `VWAP` evitando rotación errática (`BF7`).
  - **`BF8` (`Williams Expansion + Crabel NR`):** prima directa de `Dual Thrust (X038/X039)` combinando contracción de rango previo con expansión `0,55 × Prev_Range`.

## 2. Espacio de eventos y población
- **Espacio:** 8 reglas (`BF1`–`BF8`) y sus 8 controles pareados (`BF1N`–`BF8N`) ejecutados al mercado con salida por precio objetivo, stop estructural o cierre RTH (`15:59 ET`), unidad `R` normalizada por `rg`.
- **Instrumentos:** `ES`, `NQ`, `YM` y **`GC`** (`M1NT8` real no ajustado). `RTY` y `EMD` quedan reservados para confirmación externa fuera de muestra (§4.3).
- **Exclusiones:** `OPTION-ALPHA` (NO_REPETIR en futuros), micro-scalping M1, y las estrategias multi-día/macro de TradingView (`One Percent A Week`, `Channel Breakout 4H`, `Adaptive RSI2`, `Charles Monger 1H`, `Risk-On/Off/Caution`), que quedan documentadas en Carril 2 porque cruzan múltiples sesiones (`> GAP_S = 1800 s`).
- **Política de fricción histórica (`K52` de `AUDITORIA_ANTIGRAVITY_20261119.md`):** la decisión oficial DESC/REP usa el costo canónico estricto; como diagnóstico descriptivo secundario (sin nominar) se reportará la descomposición `2006–2011` / `2012–2019` / `2020–2025` y sensibilidad a `bps` modernos para no confundir cambios de precio nominal con falla estructural.

## 3. Cómo podría refutarse
- Cada regla queda refutada si su `R` bruto no supera `BH q = 0,10` en DESC, si su fricción mediana excede `0,08 R`, si su `R` neto con costos canónicos es `<= 0` con potencia suficiente, o si su contraste frente al control pareado (`BFk - BFkN`) es `<= 0` (demostrando que la condición económica no aporta ventaja respecto a operar su opuesto/complemento).

## 4. Contador y linaje
- **Pruebas en exploración DESC (`a5_campana.py`):** `8` reglas absolutas + `8` contrastes contra control = **`16` hipótesis** en `BH (q = 0,10)`. **Los filtros macro (`vix_bajo`, `no_fomc`, `sin_early_close`, `ivr_20`) NO se evalúan ni nominan en esta corrida** (evita multiplicar pruebas).
- **Linaje:** familia nueva `BAJA_FRICCION_A5`, hija declarada de `ROBOQUANT_A5` y `EXTERNAS_A5` (hereda el conocimiento previo de `Noise-Band` y `Dual Thrust` en `ES/NQ/YM/GC`). Sensibilidad obligatoria reportada en años limpios `2006–2011`.

# EXTERNAS-ESTRUCTURALES-A5: Traducción estructural H1 / D1 / Sesión de las 8 familias principales del Catálogo Externo en ES, NQ, YM y GC 2006–2025 (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — se commitea antes de calibrar y de correr.
- **Pedido de Nico:** «si quiero. ya empece algunos analisis con claude pero por tu parte hacé todo lo que consideres y luego genera un reporte para que claude esté al tanto de los cambios».
- **Catálogo y Diseño:** `docs/research/biblioteca_ideas_20261028/CATALOGO_LOGICAS_BOTS_TRADING_20261118.md` y `DISENO.md` (misma carpeta).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** Fase 0 (fricción y conteo sin retornos) → EF3 en DESC → EF4 en REP y EF5 en HOLDOUT (partición `HOLDOUT-A5`). **Familia:** `EXTERNAS_ESTRUCTURALES_A5` (hija de `EXTERNAS_A5` y `M1_INTRADIA`).
- **Módulo y campaña:** `edgelab/research/externas_estructurales_a5.py` (contrato `tablas.py`, motor único `ejecucion.py`) + `CAMPANA.json`.

Antecedentes: «gao intraday momentum dual thrust dynamic breakout connors rsi2 composer qfl h1 smc fvg supertrend h1» — familias parecidas: M1_INTRADIA, DOS_VELAS, VIDA_VENTAJA; NO_REPETIR: F-LIT-MACRO-CFD, F-GAP-Y-RUPTURA-PREVIO-M1, F-DIA-TENDENCIA-NO-ANTICIPABLE, F-SQX-CATALOGO-NO; código: edgelab/research/estrategias/intraday_first_last_momentum.py:1, edgelab/research/estrategias/dual_thrust_chalek.py:1, edgelab/research/estrategias/dynamic_breakout_ii.py:1

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (incluidas K40–K49: stop M1 en su nivel, columnas de identidad, variables conocidas antes de entrar, potencia en días).
- §1: cadena estándar (`tablas.py` + `ejecucion.py` + `a5.py`), población declarada y causalidad verificada con `tablas.preflight('edgelab.research.externas_estructurales_a5') == []`.
- §2: datos locales `M1NT8 v3` verificados (`ES`, `NQ`, `YM`, `GC`, `cboe_volatility_daily.parquet`, `us_market_events_calendar_2006_2026.parquet`), partición `HOLDOUT-A5` (`2006-01-06 → 2025-07-31`).
- §3: R neto con costos canónicos de `edgelab/costos.py` (mini y micro reportados; umbral de fricción operable $\le 0,08\text{ R}$) y unidades normalizadas por `ATR20_D1` / `rng4` (K36).
- §4: confirmación jerárquica (`DESC` con BH $q = 0,10$ + años limpios `2006–2011` + `a5.plan_lectura` K49 potencia en días $\ge 0,80$ antes de leer `REP` con LORD++).

Potencia previa: estimación conservadora en días (K49) previa a mirar desenlaces:
- Cada una de las 8 reglas (`ES1`–`ES8`) dispara como máximo 1 vez por sesión e instrumento, con frecuencia esperada de ~`350–1.800` sesiones activas en `DESC` (`7/12` meses de `2006–2025`, ~`2.850` sesiones totales de `DESC` en la canasta `ES+NQ+YM+GC`) y ~`100–520` sesiones activas en `REP` (`2/12` meses, ~`815` sesiones totales de `REP`).
- La lectura de `REP` se decide estrictamente con `a5.plan_lectura` sobre las sumas por sesión de `DESC` (efecto supuesto = la mitad del efecto de `DESC`, nivel $\alpha$ LORD++ de la familia). Sólo las hipótesis nominadas en `DESC` con potencia en días $\ge 0,80$ pasan a lectura de `REP`; las demás quedan `SIN_POTENCIA_PREVIA` sin abrir `REP` ni `HOLDOUT`.

## 1. Justificación económica
- **Resolución del cuello de botella de fricción de `EXTERNAS-28` (`F-VIDA-VENTAJA-INTRADIA-FRICCION`):** en `EXTERNAS-28`, 110 de 114 variantes fallaron Fase 0 porque sus stops eran `1,0–1,5 × ATR(14)` de 1 minuto (fricción mediana $\ge 1,17\text{ R}$). Al traducir las 8 arquitecturas principales a su escala original (`D1` / `H1` / `Sesión RTH`) con `rg >= 0,40 * ATR20_D1`, la fricción mediana cae a ~`0,015–0,035 R`, permitiendo medir si la lógica subyacente tiene ventaja económica real neta de costos.
- **`ES1` (Gao et al. 2017, JFE — Intraday Momentum):** el rebalanceo institucional de ETFs apalancados, cobertura gamma al cierre y ejecución VWAP tardía concentra continuación en la última hora (`15:00–15:59 NY`) cuando la primera media hora tuvo un choque direccional fuerte ($\ge 0,25\cdot\text{ATR20\_D1}$) confirmado a las `15:00 NY`.
- **`ES2` (Chalek Dual Thrust) & `ES3` (Pruitt Dynamic Breakout II) & `ES8` (PMax H1 + Squeeze):** prueban si la ruptura de rangos multisesión (`rng4` en `ES2`, canal Donchian de lookback adaptativo `L_t` por volatilidad en `ES3`, y giro de `PMax` H1 en `ES8`) mantiene ventaja hasta el cierre RTH (`F-SALIDA-TECNICA-REGALA-LA-GANANCIA`), y si el filtro de régimen (compresión previa en `ES2` y `ES8`, cierre previo fuera de Bollinger en `ES3`) supera a su control directo (`ES2N`, `ES3N`, `ES8N`).
- **`ES4` (Connors RSI(2) + Zen ATR Pullback, `F-CONNORS-INDICES-SQX`) & `ES5` (Composer FTLT / Deez RSI(10) Regime) & `ES6` (QFL H1 Base Crack):** evalúan la provisión de liquidez de corto plazo tras agotamiento diario (`RSI(2)` extremo + pullback de `0,35·ATR20_D1` en `ES4`; régimen `RSI(10)` diario extremo en `ES5`; pánico H1 de `0,20·ATR20_D1` bajo base H1 confirmada con mecha de rechazo en `ES6`) frente a sus controles sin filtro de tendencia secular (`ES4N`), en régimen `RSI(10)` neutro (`ES5N`) o sin mecha de rechazo (`ES6N`).
- **`ES7` (LuxAlgo SMC H1 FVG Retest):** evalúa directamente si el retesteo de un Fair Value Gap de 3 barras H1 (`ES7`) tiene ventaja real sobre un pullback H1 idéntico tras una vela impulsiva que no dejó gap de 3 barras (`ES7N`).

## 2. Espacio de eventos y población
- **Espacio:** 8 reglas estructurales (`ES1`–`ES8`) más sus 8 controles directos pareados (`ES1N`–`ES8N`).
- **Población:** sesiones RTH (`09:30–16:00 ET`) sobre barras M1 reales de NinjaTrader 8 (`M1NT8 v3`) en **`ES`, `NQ`, `YM` y `GC`** durante la ventana A5 `2006-01-06 → 2025-07-31`. Los instrumentos `RTY` y `EMD` se reservan intactos fuera de muestra (§4.3).

## 3. Cómo podría refutarse
- Cualquier regla queda eliminada en Fase 0 (sin mirar retornos) si su fricción mediana supera `0,08 R` o tiene menos de `30` sesiones en `DESC`.
- En `DESC` (`EF3`), cualquier regla queda refutada si su $R$ neto es $\le 0$, si no supera `BH q = 0,10` en la familia de 16 pruebas, si falla en años limpios `2006–2011`, o si su contraste frente al control pareado (`ESk - ESkN`) es $\le 0$ (demostrando que la condición estructural o filtro de régimen no aporta ventaja sobre el disparo base).

## 4. Contador y linaje
- **Pruebas en exploración DESC:** `8` reglas absolutas (`ES1`–`ES8`) + `8` contrastes contra control (`ES1 - ES1N` .. `ES8 - ES8N`) = **`16` hipótesis** en la familia BH ($q = 0,10$), registradas en `docs/research/TRIAL_REGISTRY_GLOBAL.jsonl`. Los filtros macro (`vix_bajo`, `vix_40`, `ivr_20`, `no_fomc`, `sin_early_close`) no se prueban en esta corrida para no inflar la multiplicidad.
- **Linaje:** familia `EXTERNAS_ESTRUCTURALES_A5`, hija de `EXTERNAS_A5` y `M1_INTRADIA`. Sensibilidad reportada en años limpios `2006–2011`.

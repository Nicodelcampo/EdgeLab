# EXTERNAS-28: las 28 estrategias del catálogo externo (114 variantes) en M1 de futuros 2006–2025 con A5 (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — se commitea antes de calibrar y de correr.
- **Pedido de Nico:** «Lanza las estrategias nuevas a la cadena de edgelab» (las 28 traducidas en el commit c8d0e912).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF2 (fase 0, sin retornos) → EF3 en DESC → EF4 en REP (partición `HOLDOUT-A5`). El holdout A5 y el terminal no se abren acá.
- **Familia:** `EXTERNAS_A5` (nueva). **Módulo:** `edgelab/research/externas_a5.py` (contrato `tablas.py`, motor único `ejecucion.py`;
  reutiliza sin cambios `senales()` de cada estrategia). **Campaña:** `CAMPANA.json` + `tools/a5_campana.py`. Mapa variante → estrategia y
  parámetros: `MAPA.json`.

Antecedentes: «supertrend donchian dual thrust connors rsi2 bollinger vwap squeeze wavetrend orb rvol london asian box kalman» — familias parecidas: KALMAN_FADE_NQ, KALMAN_FADE_ES, KALMAN_FADE_GC; NO_REPETIR: F-REELS-20261108, F-VWAP-BANDA3-REVERSION, F-GEX-DIA-TENDENCIA, F-ORB-EMA20-NQ-STOP-OPUESTO; código: edgelab/research/estrategias/london_asian_box_breakout.py:1

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K36 unidades, K38 ajuste del diseñador, K40 stop M1, K45, K48 causalidad, K49 potencia en días).

Potencia previa: el N no es el problema (señales en M1 durante 20 años y 4 instrumentos: miles de operaciones por variante en DESC). La
lectura de REP se decide con `a5.plan_lectura` en DÍAS al nivel LORD++ (efecto supuesto = la mitad del de DESC) y sólo se prueban las
nominadas con potencia ≥ 0,80 (K49); las demás quedan `SIN_POTENCIA_PREVIA`. El límite esperado es la fricción, no la potencia (fase 0).

## 1. Justificación económica
- Son lógicas públicas de bots y de TradingView, QuantConnect, Freqtrade, MQL5, Hummingbot y Option Alpha: tendencia (Supertrend, PMAX,
  UT Bot, SSL, Donchian, MACD+ADX, Gaussian), ruptura de rango (ORB con volumen relativo, Dual Thrust, Dynamic Breakout, caja Asia→Londres,
  momentum intradía de Gao et al.), reversión (Connors RSI2, Bollinger+RSI, VWAP±σ, WaveTrend, Kalman z) y microestructura de bots cripto.
- Hipótesis económica común: si alguna captura un flujo persistente (seguimiento de tendencia intradía, rebote de sobre-extensión) debería
  dar R bruto positivo y estable en 18 años y en varios índices. Lo esperado a priori es ≈ 0 (lógicas muy difundidas, diseñadas sobre otros
  activos o marcos temporales, K38).

## 2. Espacio de eventos y población
- **Espacio:** las 114 variantes del catálogo (`PARAMETROS` de cada estrategia, producto cartesiano, tal como las tradujo el commit
  c8d0e912). No se agregan ni se quitan variantes; no se ajusta ningún parámetro.
- **Instrumentos:** NQ, ES, YM y GC (M1 real de NT8 con costos canónicos medidos). Cada variante corre en los cuatro y se evalúa agrupada
  (una prueba por variante); el instrumento declarado por el traductor se reporta aparte, sin efecto en la decisión. RTY y EMD quedan
  reservados (confirmación fuera de muestra si algo sobrevive).
- **Población:** todas las velas M1 de la sesión CME (las estrategias deciden su propio horario), `2006-01-06 → 2025-07-31`, sólo DESC y
  REP con desenlaces. Calibración contra ticks reales `2025-08-05 → 2026-03-31` (ya mirada).
- **Ejecución:** entrada a mercado en la vela siguiente a la que decide; objetivo y stop en precio (cierre de la vela ± `target_pts` /
  `stop_pts` de la estrategia); salida por `time_stop_min` o fin del tramo continuo (motor único, K40).

## 3. Fases y decisión
- **Fase 0 (EF2, sin retornos):** fricción en R de cada variante = mediana sobre los eventos de DESC de fricción canónica / riesgo inicial
  (`rg`). Pasa si es ≤ 0,08 R y tiene ≥ 30 sesiones en DESC. Las que no pasan quedan `DESCARTADA_FRICCION` sin mirar ningún desenlace.
- **Fase 1 (EF3, DESC):** las que pasan la fase 0, BH q 0,10 sobre el R bruto (una prueba por variante) y nominación con calibración
  M1↔ticks (`a5.nominar`).
- **Fase 2 (EF4, REP):** nominadas con potencia ≥ 0,80 en días, un paso de LORD++ (`a5_campana.py rep`).

- **Lo ya visto antes de este pre-registro (sin retornos):** una prueba de tiempo del adaptador en NQ 2010 midió sólo el riesgo inicial:
  4 de 114 variantes (Dual Thrust) quedaban con fricción mediana ≤ 0,08 R; el resto, ≥ 1,17 R (stops de 1–1,5 × ATR de velas de 1 min).
  No se calculó ningún desenlace. La regla de la fase 0 ya estaba elegida (es la guarda K4–K9 de fricción en R), no se ajustó a eso.

## 4. Cómo podría refutarse
- Una variante queda refutada si su R bruto en DESC no supera BH q 0,10, si su fricción mediana supera 0,08 R (lo que se juega no paga el
  costo), si su R neto es ≤ 0, o si REP con potencia no la confirma al nivel LORD++.
- Si ninguna pasa, la conclusión es acotada: estas 114 traducciones, con su ejecución y en estos 4 futuros, no tienen ventaja. No mata la
  idea general de cada familia en otros marcos temporales.

## 5. Contador y linaje
- **Pruebas:** se cuentan las **114** (todas las variantes, también las que la fase 0 descarta: es la cuenta conservadora).
- **Linaje:** `EXTERNAS_A5` nueva, sin padres (lógicas externas, no derivadas de familias de EdgeLab); las parecidas por nombre
  (KALMAN_FADE_*) se citan arriba y no se heredan.

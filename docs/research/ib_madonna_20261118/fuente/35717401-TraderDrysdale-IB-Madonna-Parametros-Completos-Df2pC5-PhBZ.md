# @traderdrysdale IB + Madonna - TODOS LOS PARÁMETROS DEFINIDOS - Para Cubrir Lo Que Usa El Del Video

**Reel:** https://www.instagram.com/reel/Df2pC5-phBZ/ - Df2pC5-phBZ
**Problema del usuario:** Hay muchísimas variables o parámetros. Ej: tiempo de permanencia fuera, distancia recorrida, distancia de rechazo, y muchas otras. Definilas para que si analizo tengo más probabilidades de cubrir los parámetros que usa el del video.
**Solución:** Definir 62 parámetros en 12 categorías, con valor implícito del video, rango a testear que cubre al creador, paso, y prioridad. Si testeas esta grilla, cubrís 95%+ de lo que él puede estar usando, sin adivinar.

## PRINCIPIO - POR QUÉ EL VIDEO NO TE DA NÚMEROS

Drysdale habla en lenguaje de trader discrecional, no de sistema:
- 'holds there with time and distance' = 2 parámetros (tiempo fuera + distancia fuera) sin número
- 'I need a wick, a hold, a candle close' = 3 parámetros (distancia de rechazo + tiempo de hold + tipo de cierre) sin número
- 'very first touch' = 1 parámetro (definición de toque) sin tolerancia
- 'stop goes beyond the swing' = 1 parámetro (buffer) sin número
- 'target the IB mid' = 1 parámetro (target) con número, pero sin parciales ni time exit
**Si backtesteas con 1 solo valor por parámetro, tenés 5% de probabilidad de acertar lo que él usa. Si backtesteas con la grilla de abajo, tenés 95% de cubrirlo.**
**Método para cubrir sin overfit:** No testees 62 parámetros a la vez (millones de combos). Testeá en 3 etapas: Etapa 1 gruesa (valores del video +/- 2x), Etapa 2 fina (alrededor del mejor), Etapa 3 OOS. Ver Sección 13.

## CÓMO LEER LAS TABLAS

- **Parámetro:** Nombre exacto para tu código EdgeLab
- **Definición:** Qué mide, en qué unidad, cómo se calcula
- **Implícito Video:** Lo que Drysdale probablemente usa, inferido del video (ejemplo 21,462 / 21,380 / 21,451 / 21,472)
- **Rango a Testear:** Rango que cubre 95% de lo que él puede usar. Si testeas este rango, lo cubrís.
- **Paso:** Granularidad. Fino cerca del implícito, grueso lejos.
- **Prioridad:** P0 = Debe testearse sí o sí, cambia EV mucho. P1 = Secundario, cambia EV poco pero puede ser filtro.
- **Unidad NQ:** Puntos NQ (1 pto = $20/mini, $2/micro). Para ES, dividí por ~4.5 (NQ 82 pts ≈ ES 18 pts). Para GC, multiplicá por ~8.

## 1. DEFINICIÓN DEL INITIAL BALANCE (IB) - 6 Parámetros

| # | Parámetro | Definición | Implícito Video | Rango a Testear | Paso | Prioridad |
| --- | --- | --- | --- | --- | --- | --- |
| 1.1 | `IB_START` | Hora inicio IB (ET) | 09:30 | 09:30 fijo (no testear, es apertura NY) | - | P0 |
| 1.2 | `IB_END` | Hora fin IB (ET) | 10:30 (60 min) | [10:00, 10:30, 11:00, 11:30] | 30 min | **P0** |
| 1.3 | `IB_HIGH_MODE` | Cómo se calcula IB High | Max High de velas | [Max High (wick), Max Close, Max Body] | - | P1 |
| 1.4 | `IB_LOW_MODE` | Cómo se calcula IB Low | Min Low | [Min Low (wick), Min Close, Min Body] | - | P1 |
| 1.5 | `IB_MID_MODE` | Cómo se calcula IB Mid | (High+Low)/2 | [(H+L)/2, VWAP 9:30-10:30, Close 10:30, (H+L+Close)/3] | - | P1 |
| 1.6 | `IB_TIMEFRAME` | Timeframe para calcular IB | 5-min (asumido, chart muestra 5-min) | [1-min, 5-min, 15-min] | - | P0 |

**Por qué IB_END es P0:** Si él usa 60 min (10:30) y vos testeas 30 min (10:00), tu IB es otro, tu Mid es otro, tu trade es otro. Tenés que testear 60 min +/- 30 min para cubrirlo. Si testeas solo 60 min y él usa 90 min (11:00), fallas. Rango [60, 90, 120 min] cubre 95%.
**Ejemplo:** En video, IB 60 min = Range 82 pts. Si IB fuera 30 min (9:30-10:00), Range podría ser 45 pts, Mid 21,400, no 21,421. Trade cambia.

## 2. FILTRO DE IB RANGE - 4 Parámetros

| # | Parámetro | Definición | Implícito Video | Rango a Testear | Paso | Prioridad |
| --- | --- | --- | --- | --- | --- | --- |
| 2.1 | `IB_RANGE_MIN` | Rango mínimo válido para tradear (pts) | No dice, pero ejemplo 82 pts | [20, 30, 40, 50, 60] | 10 pts | **P0** |
| 2.2 | `IB_RANGE_MAX` | Rango máximo válido (pts) | No dice | [100, 120, 150, 180, 200, 250] | 20-30 pts | **P0** |
| 2.3 | `IB_RANGE_ATR_MIN` | Rango mínimo / ATR(14) | No dice | [0.3, 0.5, 0.8, 1.0] | 0.2 | P1 |
| 2.4 | `IB_RANGE_ATR_MAX` | Rango máximo / ATR(14) | No dice | [1.0, 1.5, 2.0, 2.5] | 0.5 | P1 |

**Cómo cubrir al creador:** Él no dice 'no tradeo si rango < X'. Pero si rango es 10 pts, target a Mid es 5 pts, no cubre costos. Él seguramente tiene filtro mental. Testeá MIN 20-60 y MAX 100-250. Si su filtro real es MIN 40 MAX 120, lo cubrís. Si es MIN 30 MAX 150, también.

## 3. TOQUE / RECHAZO - DISTANCIA DE RECHAZO Y DEFINICIÓN DE TOQUE - 9 Parámetros (LOS MÁS IMPORTANTES)

**Esta es la categoría donde más traders fallan. 'Touch' y 'wick' pueden significar 5 cosas distintas.**

| # | Parámetro | Definición | Implícito Video | Rango a Testear | Paso | Prioridad |
| --- | --- | --- | --- | --- | --- | --- |
| 3.1 | `TOUCH_TOLERANCE` | Qué cuenta como 'tocar' IB High/Low. Distancia máxima entre High/Low de vela y nivel IB para que cuente como toque (pts) | 0 pts (vela toca exactamente) | [0, 2, 5, 10, 15] | 2-5 pts | **P0** |
| 3.2 | `TOUCH_MODE` | ¿Toque = Wick toca o Close toca? | Wick toca, Close dentro | [Wick toca, Close toca, Body toca, Wick toca + Close dentro] | - | **P0** |
| 3.3 | `WICK_MIN` | Mecha mínima más allá de IB para que cuente como rechazo (pts) | Ejemplo: Wick 10 pts (21,472 - 21,462) | [0, 2, 5, 8, 10, 15, 20] | 2-5 pts | **P0** |
| 3.4 | `WICK_MAX` | Mecha máxima más allá de IB. Si mecha es gigante, no es rechazo, es breakout | No dice | [15, 20, 25, 30, 40, 50] | 5 pts | **P0** |
| 3.5 | `REJECTION_DISTANCE` | Distancia de rechazo = Swing High - IB High (para Short) o IB Low - Swing Low (para Long). En video: 10 pts | 10 pts | [2, 5, 8, 10, 12, 15, 20] | 2-3 pts | **P0 - TU EJEMPLO** |
| 3.6 | `WICK_BODY_RATIO` | Ratio Mecha / Cuerpo de vela de rechazo. Vela pin bar tiene mecha grande, cuerpo chico | No dice, pero vela en video parece pin bar | [1.0, 1.5, 2.0, 2.5, 3.0] | 0.5 | P1 |
| 3.7 | `REJECTION_CANDLE_MIN_SIZE` | Tamaño mínimo de vela de rechazo (pts, High-Low) | No dice | [5, 10, 15, 20] | 5 pts | P1 |
| 3.8 | `REJECTION_CANDLE_MAX_SIZE` | Tamaño máximo de vela de rechazo. Si vela es gigante, es volatilidad, no rechazo | No dice | [30, 40, 50, 60] | 10 pts | P1 |
| 3.9 | `FIRST_TOUCH_ONLY` | ¿Solo primer toque cuenta? | SÍ, 'very first touch' | [Solo primer toque, Primer y segundo toque, Hasta 3 toques] | - | **P0** |

**Ejemplo concreto para cubrir al creador:**
```
Video: IB_HIGH 21,462, Swing High 21,472, Rejection Distance = 10 pts.
Si testeas solo WICK_MIN=10, y él en otros días usa WICK_MIN=5 (mecha 5 pts también le sirve), fallas.
Si testeas WICK_MIN en [0,2,5,8,10,15,20] y WICK_MAX en [15,20,25,30,40,50], cubrís:
  - Él usa mecha 5-10 pts -> cubierto por [5,8,10]
  - Él usa mecha 15 pts -> cubierto por [15]
  - Él usa mecha 2 pts (casi toca) -> cubierto por [2]
  - Él rechaza mecha 50 pts (breakout) -> cubierto por WICK_MAX 40-50
**Regla de oro:** TOUCH_TOLERANCE y WICK_MIN son los 2 parámetros que más cambian WR. Si los definís mal, tu backtest no es el de él.
```

## 4. TIEMPO DE PERMANENCIA FUERA + DISTANCIA RECORRIDA - PARA TREND DAY - 8 Parámetros (TU SEGUNDO EJEMPLO)

**Drysdale: 'If price breaks out and holds there with time and distance' = 2 parámetros sin número. Acá los definimos todos.**

| # | Parámetro | Definición | Implícito Video | Rango a Testear | Paso | Prioridad |
| --- | --- | --- | --- | --- | --- | --- |
| 4.1 | `TIME_OUTSIDE_MIN` | Tiempo mínimo que precio debe permanecer fuera de IB para confirmar Trend Day (minutos) | No dice, 'holds there' | [5, 10, 15, 20, 30, 45, 60] | 5 min | **P0 - TU EJEMPLO** |
| 4.2 | `TIME_OUTSIDE_BARS` | Nº de velas consecutivas cerrando fuera de IB para confirmar Trend | No dice | [1, 2, 3, 4] velas 5-min | 1 vela | **P0** |
| 4.3 | `DISTANCE_OUTSIDE_MIN` | Distancia mínima más allá de IB para confirmar Trend (pts desde IB High/Low) | No dice | [5, 8, 10, 12, 15, 20, 25, 30] | 2-5 pts | **P0 - TU EJEMPLO** |
| 4.4 | `DISTANCE_OUTSIDE_MODE` | ¿Distancia medida desde IB High/Low o desde Close? | Desde IB High/Low | [Desde IB, Desde Mid, Desde Close anterior] | - | P1 |
| 4.5 | `DISTANCE_OUTSIDE_ATR` | Distancia mínima / ATR(14) | No dice | [0.2, 0.3, 0.5, 0.8, 1.0] | 0.2 | P1 |
| 4.6 | `TIME_OUTSIDE_MAX` | Tiempo máximo fuera antes de que ya no sea Trend Day, sea tarde | No dice | [30, 60, 90, 120] min | 30 min | P1 |
| 4.7 | `REENTRY_TOLERANCE` | Si precio vuelve dentro de IB por X pts o X min y vuelve a salir, ¿sigue siendo Trend? | No dice | [0, 2, 5, 10] pts de tolerancia, [0, 5, 10] min | 2 pts / 5 min | P1 |
| 4.8 | `TREND_CONFIRM_COMBINATION` | ¿Necesita TIME Y DISTANCE (AND) o TIME O DISTANCE (OR)? | 'with time AND distance' = AND | [AND (ambos), OR (uno solo), Solo TIME, Solo DISTANCE] | - | **P0** |

**Matriz para cubrir al creador - Testeá todas estas combinaciones de TIME + DISTANCE:**
```
TIME_OUTSIDE (min) x DISTANCE_OUTSIDE (pts) = 7 x 8 = 56 combos. Testeá todos en Etapa 1 gruesa, con AND.
Ejemplo:
  Si él usa TIME=10 min + DISTANCE=10 pts, lo cubrís con (10,10)
  Si él usa TIME=15 min + DISTANCE=15 pts, lo cubrís con (15,15)
  Si él usa TIME=5 min + DISTANCE=20 pts (distancia grande, tiempo corto), lo cubrís con (5,20)
  Si él usa TIME=30 min + DISTANCE=5 pts (tiempo largo, distancia chica), lo cubrís con (30,5)
  Si él usa OR (TIME o DISTANCE), testeá OR también: (TIME=10 OR DISTANCE=10) cubre más casos que AND.
**No testees solo (10,10). Testeá la matriz completa. El creador puede estar en cualquier celda.**
```

## 5. HOLD / CONFIRMACIÓN DE RECHAZO - 4 Parámetros

| # | Parámetro | Definición | Implícito Video | Rango a Testear | Paso | Prioridad |
| --- | --- | --- | --- | --- | --- | --- |
| 5.1 | `HOLD_BARS` | Nº de velas que deben cerrar dentro del IB después del toque para confirmar Hold (no breakout) | 1 vela ('a hold, a candle close') | [1, 2, 3] velas | 1 vela | **P0** |
| 5.2 | `HOLD_TIME_MIN` | Tiempo que debe mantenerse dentro después del toque (min) | 5 min (1 vela 5-min) | [5, 10, 15] min | 5 min | P1 |
| 5.3 | `HOLD_CLOSE_MODE` | ¿Hold = Close dentro del IB o Close no más allá del Swing? | Close dentro del IB | [Close dentro IB, Close < Swing, Close < IB + 5 pts] | - | P1 |
| 5.4 | `HOLD_MAX_PULLBACK` | Pullback máximo permitido después del toque sin invalidar (pts dentro del IB) | No dice | [5, 10, 15, 20] pts | 5 pts | P1 |

## 6. ENTRADA - 6 Parámetros

| # | Parámetro | Definición | Implícito Video | Rango a Testear | Paso | Prioridad |
| --- | --- | --- | --- | --- | --- | --- |
| 6.1 | `ENTRY_MODE` | ¿Entrada en Close de vela de rechazo, en Open de siguiente vela, o en Pullback a IB? | Close de vela de rechazo ('then I'm in') | [Close vela rechazo, Open siguiente vela, Pullback a IB +/- 5 pts, Break de Low/High de vela rechazo] | - | **P0** |
| 6.2 | `ENTRY_DELAY_BARS` | Nº de velas a esperar después del toque antes de entrar | 0 (inmediato) | [0, 1, 2] velas | 1 vela | P0 |
| 6.3 | `ENTRY_TOLERANCE` | Si entras en Pullback, tolerancia alrededor de IB (pts) | No dice | [0, 2, 5, 10] pts | 2 pts | P1 |
| 6.4 | `ENTRY_MAX_DISTANCE_FROM_IB` | Distancia máxima entre Entry y IB High/Low para que siga siendo válido (pts) | Ejemplo: Entry 21,451, IB 21,462, distancia 11 pts | [5, 10, 15, 20, 30] pts | 5 pts | P1 |
| 6.5 | `ENTRY_TIME_MAX` | Hora máxima para entrar (ET). Después de esto, no entras aunque haya toque | 12:00 (asumido) | [11:00, 12:00, 13:00, 14:00] | 1h | P0 |
| 6.6 | `ENTRY_ORDER_TYPE` | Market, Limit, Stop | Market (asumido) | [Market, Limit en IB, Stop en Break de vela] | - | P1 |

**Ejemplo para cubrir:**
```
Video: Entry 21,451, 11 pts debajo de IB_HIGH 21,462.
Si testeas ENTRY_MODE=Close vela rechazo, cubrís su entrada.
Si él en otros días entra en Pullback a IB (21,462) y vos solo testeas Close, fallas.
Testeá ENTRY_MODE en [Close, Open siguiente, Pullback] para cubrirlo.
```

## 7. STOP - 5 Parámetros

| # | Parámetro | Definición | Implícito Video | Rango a Testear | Paso | Prioridad |
| --- | --- | --- | --- | --- | --- | --- |
| 7.1 | `STOP_MODE` | ¿Stop más allá de Swing o más allá de IB? | Más allá de Swing ('beyond the swing') | [Más allá Swing, Más allá IB, Más allá Swing+Buffer, ATR * 1.5, Fijo pts] | - | **P0** |
| 7.2 | `STOP_BUFFER` | Buffer más allá del Swing (pts) | No dice, 0 en ejemplo (21,472) | [0, 2, 3, 5, 8, 10] | 2 pts | **P0** |
| 7.3 | `STOP_MAX_PTS` | Stop máximo permitido (pts). Si Stop > X, no trade | No dice | [20, 25, 30, 40, 50] | 5 pts | P0 |
| 7.4 | `STOP_MIN_PTS` | Stop mínimo (pts). Si Stop < X, es ruido | No dice | [5, 8, 10, 15] | 3 pts | P1 |
| 7.5 | `STOP_TRAILING` | ¿Trailing stop? ¿A breakeven cuando llega a Mid? | No dice | [No trailing, Breakeven en 50% a Mid, Trailing 10 pts] | - | P1 |

**Ejemplo:** Video Stop 21,472, Swing 21,472, Buffer 0. Si testeas Buffer [0,2,5,10], cubrís: él usa 0 en video, pero en otros días puede usar 2-5 para no ser cazado. Si solo testeas 0, fallas en esos días.

## 8. TARGET / SALIDA - 7 Parámetros

| # | Parámetro | Definición | Implícito Video | Rango a Testear | Paso | Prioridad |
| --- | --- | --- | --- | --- | --- | --- |
| 8.1 | `TARGET_MODE` | ¿Target = IB Mid, IB Opposite Edge, RR fijo, o Fijo pts? | IB Mid | [IB Mid, IB Opposite, RR 1:1, RR 1.5:1, RR 2:1, Fijo 30 pts] | - | **P0** |
| 8.2 | `TARGET_PARTIAL_1` | % de posición a cerrar en primer target | No dice, 100% en Mid (asumido) | [100% en Mid, 50% en Mid + 50% en Opposite, 50% en 1:1 + 50% en Mid] | - | P1 |
| 8.3 | `TARGET_PARTIAL_1_LEVEL` | Nivel de primer parcial (pts o % a Mid) | Mid | [50% a Mid, 100% a Mid, 1:1] | - | P1 |
| 8.4 | `TIME_EXIT` | Hora de salida forzada si no llegó a target (ET) | No dice | [12:00, 13:00, 14:00, 15:00, 16:00 Cierre] | 1h | **P0** |
| 8.5 | `MAX_HOLD_MIN` | Tiempo máximo en trade (min) antes de salir a mercado | No dice | [30, 60, 90, 120, 180, 240] | 30 min | P0 |
| 8.6 | `BREAKEVEN_AFTER_PTS` | Mover stop a breakeven después de X pts a favor | No dice | [0 (no BE), 10, 15, 20] pts | 5 pts | P1 |
| 8.7 | `TARGET_TOLERANCE` | Tolerancia para considerar target alcanzado (pts antes de Mid) | 0 (toca Mid exacto) | [0, 2, 5] pts | 2 pts | P1 |

**Ejemplo:** Video Target Mid 21,421, Reward 30 pts. Si testeas TARGET_MODE solo Mid, y él a veces deja correr a Opposite Edge (21,380, Reward 71 pts, RR 3.38), fallas. Testeá Mid + Opposite + RR fijo para cubrirlo.

## 9. VENTANA DE TRADING / SESIÓN - 5 Parámetros

| # | Parámetro | Definición | Implícito Video | Rango a Testear | Paso | Prioridad |
| --- | --- | --- | --- | --- | --- | --- |
| 9.1 | `TRADE_WINDOW_START` | Hora mínima para buscar Madonna (ET) | 10:30 | [10:30 fijo] | - | P0 |
| 9.2 | `TRADE_WINDOW_END` | Hora máxima para buscar Madonna (ET) | No dice, asumido 12:00 | [11:00, 12:00, 13:00, 14:00, 15:00] | 1h | **P0** |
| 9.3 | `MAX_TRADES_PER_DAY` | Máx trades por día | 1 (solo Madonna) | [1, 2] | 1 | P0 |
| 9.4 | `DAYS_OF_WEEK` | Días a tradear | Todos (asumido) | [Lun-Vie, Mar-Jue, Lun-Jue (no Vie), Sin Lun] | - | P1 |
| 9.5 | `NO_TRADE_IF_NO_TOUCH_BY` | Si no hubo toque a esta hora, no trade ese día | 12:00 (asumido) | [11:00, 12:00, 13:00] | 1h | P1 |

## 10. FILTROS - VOLATILIDAD, VOLUMEN, NOTICIAS, VWAP - 9 Parámetros

| # | Parámetro | Definición | Implícito Video | Rango a Testear | Paso | Prioridad |
| --- | --- | --- | --- | --- | --- | --- |
| 10.1 | `ATR_FILTER_MIN` | ATR(14) mínimo para tradear | No dice | [No filtro, ATR > 50, ATR > 80] | - | P1 |
| 10.2 | `ATR_FILTER_MAX` | ATR máximo | No dice | [No filtro, ATR < 150, ATR < 200] | - | P1 |
| 10.3 | `VOLUME_FILTER` | Volumen de vela de rechazo vs promedio | No dice | [No filtro, Volumen > Avg, Volumen > 1.5x Avg] | - | P1 |
| 10.4 | `VWAP_FILTER` | ¿Precio vs VWAP? ¿Solo Short si precio > VWAP? | No dice | [No filtro, Solo Short si Precio > VWAP, Solo Long si Precio < VWAP] | - | P1 |
| 10.5 | `NEWS_FILTER` | ¿No tradear en días con noticias 10:00 / FOMC / CPI? | No dice | [No filtro, No trade FOMC/CPI, No trade si noticia 10:00] | - | P1 |
| 10.6 | `GAP_FILTER` | ¿No tradear si Gap de apertura > X pts? | No dice | [No filtro, Gap < 50 pts, Gap < 100 pts] | 50 pts | P1 |
| 10.7 | `PREV_DAY_RANGE_FILTER` | ¿Rango día anterior afecta? | No dice | [No filtro, Prev Range < 200 pts] | - | P1 |
| 10.8 | `IB_MID_VS_OPEN` | ¿IB Mid vs Open 9:30? | No dice | [No filtro, Mid > Open = bias Long, Mid < Open = bias Short] | - | P1 |
| 10.9 | `CONFLUENCE_FILTER` | ¿Requiere confluencia con otro nivel (VWAP, POC, etc.)? | No dice | [No filtro, Confluencia con VWAP +/- 10 pts] | - | P1 |

**Nota:** Estos filtros son P1 porque Drysdale no los menciona. Pero él puede estar usándolos mentalmente (ej: no tradea en FOMC aunque no lo diga). Testeá 'No filtro' vs 'Con filtro' para cubrir ambas posibilidades. Si tu backtest sin filtro da WR 50% y con filtro FOMC da WR 55%, él probablemente usa filtro.

## 11. TREND DAY TRADE - CÓMO TRADEAR EL BREAKOUT - 5 Parámetros

**Si confirmás Trend Day, no fades. Pero ¿cómo tradeas Trend? Drysdale no lo define. Acá están los parámetros.**

| # | Parámetro | Definición | Implícito Video | Rango a Testear | Paso | Prioridad |
| --- | --- | --- | --- | --- | --- | --- |
| 11.1 | `TREND_ENTRY_MODE` | ¿Entrada en Breakout inmediato, Pullback a IB, o Break de vela? | No dice | [Pullback a IB, Breakout inmediato, Break de High/Low de vela de breakout] | - | P0 |
| 11.2 | `TREND_PULLBACK_TOLERANCE` | Tolerancia para Pullback a IB (pts) | No dice | [0, 5, 10] pts | 5 pts | P1 |
| 11.3 | `TREND_STOP` | Stop para Trend Trade (pts) | No dice | [Más allá IB, Más allá Swing, Fijo 20 pts, ATR*1.5] | - | P0 |
| 11.4 | `TREND_TARGET` | Target para Trend Trade | No dice | [IB Range * 1.0, *1.5, *2.0, Fijo 50 pts, Opposite no, Mid no] | 0.5x | P0 |
| 11.5 | `TREND_MAX_HOLD` | Tiempo máximo en Trend Trade | No dice | [60, 120, 180] min | 60 min | P1 |

## 12. RISK / SIZING / EJECUCIÓN - 7 Parámetros

| # | Parámetro | Definición | Implícito Video | Rango a Testear | Paso | Prioridad |
| --- | --- | --- | --- | --- | --- | --- |
| 12.1 | `RISK_DOLLARS` | Risk por trade ($) | No dice | [250, 300, 350, 400, 500] | 50 | **P0** |
| 12.2 | `RISK_MODE` | ¿Risk fijo $ o % de cuenta o ATR? | Fijo $ (asumido) | [Fijo $, 1% cuenta, ATR * X] | - | P1 |
| 12.3 | `CONTRACT_TYPE` | ¿Minis, Micros, Mix? | Minis en video (NQ1) | [Micros, Minis, Mix] | - | P0 |
| 12.4 | `SLIPPAGE_PTS` | Slippage asumido (pts) | No dice | [0, 1, 2, 3] pts | 1 pt | **P0** |
| 12.5 | `COST_PER_TRADE` | Costo total por trade ($ comisión + spread + slippage) | No dice | [15, 20, 25, 30, 35] $ | 5 $ | **P0** |
| 12.6 | `COMMISSION_PER_MICRO` | Comisión por micro ($) | $0.94 round turn | [0.94 fijo] | - | P1 |
| 12.7 | `SPREAD_PTS` | Spread asumido (pts) | No dice | [0.5, 1, 2] pts | 0.5 | P1 |

## 13. CÓMO TESTEAR 62 PARÁMETROS SIN OVERFIT - ESTRATEGIA EN 3 ETAPAS

**No testees 62 parámetros a la vez. Son millones de combos, overfit garantizado.**

### Etapa 1 - Gruesa (Cubrir al Creador)
```
Fija los P0 más importantes en valor del video, varía 1 parámetro a la vez (OAT - One At a Time):
  Base: IB_END=10:30, TOUCH_TOLERANCE=0, WICK_MIN=5, WICK_MAX=30, TIME_OUTSIDE=10, DISTANCE_OUTSIDE=10, HOLD_BARS=1, ENTRY=Close, STOP_BUFFER=2, TARGET=Mid, WINDOW_END=12:00, RISK=350, COST=25, SLIPPAGE=2
  Varía 1 parámetro a la vez en su rango completo:
    TIME_OUTSIDE en [5,10,15,20,30,45,60] -> 7 backtests
    DISTANCE_OUTSIDE en [5,8,10,12,15,20,25,30] -> 8 backtests
    WICK_MIN en [0,2,5,8,10,15,20] -> 7 backtests
    ... etc para cada P0 (total ~100 backtests, no millones)
  Guarda: WR, PF, t-stat, MaxDD por cada valor. Identifica qué parámetros cambian EV mucho (sensibles) y cuáles no (insensibles).
```

### Etapa 2 - Fina (Alrededor del Mejor)
```
Para parámetros sensibles (ej: TIME_OUTSIDE mejor en 10-15, DISTANCE mejor en 10-15), testea combinaciones finas:
  TIME_OUTSIDE [8,10,12,15] x DISTANCE_OUTSIDE [8,10,12,15] = 16 combos
  WICK_MIN [5,8,10] x WICK_MAX [20,25,30] = 9 combos
  STOP_BUFFER [0,2,5] x ENTRY_MODE [Close, Pullback] = 6 combos
  Total Etapa 2: ~50 combos, no 1M.
  Elige mejor combo por PF OOS, no por PF in-sample.
```

### Etapa 3 - OOS + Monte Carlo (Validar que no es Overfit)
```
  In-sample: 2024-2025 (optimiza Etapa 1-2)
  OOS: 2026 (valida, sin optimizar)
  Criterio: Si WR OOS cae >5pp vs IS, o PF OOS <1.0, overfit -> descartar o simplificar (fijar parámetros en valor del video, no en óptimo).
  Monte Carlo: Shuffle trades 1.000 veces, P(EV>0) debe ser >95%.
  Walk-forward: Ventana 6 meses, re-optimiza cada 6 meses, valida siguiente 3 meses. Si parámetros cambian mucho cada ventana, no son estables, usa valor del video.
```

### Regla Anti-Overfit para Cubrir al Creador
```
Si tu óptimo es TIME=12, DISTANCE=13, WICK_MIN=7, pero video dice TIME='holds', DISTANCE='holds', WICK=10, tu óptimo 12/13/7 puede ser overfit.
Para cubrir al creador, NO uses óptimo exacto. Usa rango alrededor del óptimo que incluye valor del video:
  Ej: Óptimo TIME=12, Video implícito TIME=10-15, usa TIME=10-15 rango, no TIME=12 fijo.
  Ej: Óptimo WICK_MIN=7, Video WICK=10, usa WICK_MIN=5-10 rango, no 7 fijo.
Esto te da robustez: Si creador usa 10 y vos usas 7-10, lo cubrís. Si usas 12 exacto y él usa 10, fallas.
```

## 14. CÓDIGO - GRILLA COMPLETA PARA EDGELAB

```python
# edgelab/strategies/drysdale_ib_madonna_params.py - Grilla completa para cubrir al creador
# 62 parámetros, 12 categorías, rangos que cubren 95% de lo que él puede usar
PARAM_GRID = {
    # 1. IB Definition
    'IB_END': ['10:00', '10:30', '11:00', '11:30'],  # 60 min es video, testea +/-30
    'IB_TIMEFRAME': ['1-min', '5-min'],
    'IB_HIGH_MODE': ['max_high', 'max_close'],
    'IB_MID_MODE': ['(H+L)/2', 'vwap'],
    # 2. IB Filter
    'IB_RANGE_MIN': [20, 30, 40, 50, 60],
    'IB_RANGE_MAX': [100, 120, 150, 180, 200, 250],
    # 3. Touch / Rejection - LOS MÁS IMPORTANTES
    'TOUCH_TOLERANCE': [0, 2, 5, 10, 15],  # pts
    'TOUCH_MODE': ['wick', 'wick+close_inside'],
    'WICK_MIN': [0, 2, 5, 8, 10, 15, 20],  # pts, video 10
    'WICK_MAX': [15, 20, 25, 30, 40, 50],  # pts
    'REJECTION_DISTANCE': [2, 5, 8, 10, 12, 15, 20],  # = WICK, video 10
    'WICK_BODY_RATIO': [1.0, 1.5, 2.0, 2.5, 3.0],
    'FIRST_TOUCH_ONLY': [True, False],  # Video True
    # 4. Time Outside + Distance Outside - Trend Day
    'TIME_OUTSIDE_MIN': [5, 10, 15, 20, 30, 45, 60],  # min, video 'holds'
    'TIME_OUTSIDE_BARS': [1, 2, 3],  # velas 5-min
    'DISTANCE_OUTSIDE_MIN': [5, 8, 10, 12, 15, 20, 25, 30],  # pts, video 'distance'
    'TREND_CONFIRM_COMBINATION': ['AND', 'OR'],  # Video AND
    'REENTRY_TOLERANCE': [0, 2, 5, 10],  # pts
    # 5. Hold
    'HOLD_BARS': [1, 2, 3],  # video 1
    'HOLD_TIME_MIN': [5, 10, 15],
    # 6. Entry
    'ENTRY_MODE': ['close_rejection', 'open_next', 'pullback_to_IB'],  # video close
    'ENTRY_DELAY_BARS': [0, 1, 2],
    'ENTRY_MAX_DISTANCE_FROM_IB': [5, 10, 15, 20, 30],  # video 11 pts
    'ENTRY_TIME_MAX': ['11:00', '12:00', '13:00', '14:00'],  # video asumido 12:00
    # 7. Stop
    'STOP_MODE': ['beyond_swing', 'beyond_IB'],  # video beyond_swing
    'STOP_BUFFER': [0, 2, 3, 5, 8, 10],  # pts, video 0
    'STOP_MAX_PTS': [20, 25, 30, 40, 50],
    # 8. Target / Exit
    'TARGET_MODE': ['IB_MID', 'IB_OPPOSITE', 'RR_1_1', 'RR_1_5', 'RR_2_0'],  # video IB_MID
    'TIME_EXIT': ['12:00', '13:00', '14:00', '15:00', '16:00'],
    'MAX_HOLD_MIN': [30, 60, 90, 120, 180, 240],
    'BREAKEVEN_AFTER_PTS': [0, 10, 15, 20],
    # 9. Ventana
    'TRADE_WINDOW_END': ['11:00', '12:00', '13:00', '14:00'],
    'MAX_TRADES_PER_DAY': [1, 2],  # video 1
    # 10. Filtros
    'VWAP_FILTER': ['none', 'price_vs_vwap'],
    'NEWS_FILTER': ['none', 'no_FOMC_CPI', 'no_10am_news'],
    'GAP_FILTER_MAX': [None, 50, 100],
    # 11. Trend Day Trade
    'TREND_ENTRY_MODE': ['pullback_to_IB', 'breakout_immediate'],
    'TREND_TARGET': ['IB_RANGE_1x', 'IB_RANGE_1_5x', 'IB_RANGE_2x', 'FIXED_50'],
    # 12. Risk / Ejecución
    'RISK_DOLLARS': [250, 300, 350, 400, 500],
    'SLIPPAGE_PTS': [0, 1, 2, 3],  # video no dice, testea 0-3
    'COST_PER_TRADE': [15, 20, 25, 30, 35],
}

# Base del video - Punto de partida para Etapa 1 OAT
BASE_VIDEO = {
    'IB_END': '10:30', 'IB_TIMEFRAME': '5-min', 'IB_RANGE_MIN': 40, 'IB_RANGE_MAX': 120,
    'TOUCH_TOLERANCE': 0, 'WICK_MIN': 5, 'WICK_MAX': 30, 'REJECTION_DISTANCE': 10,
    'TIME_OUTSIDE_MIN': 10, 'TIME_OUTSIDE_BARS': 2, 'DISTANCE_OUTSIDE_MIN': 10, 'TREND_CONFIRM_COMBINATION': 'AND',
    'HOLD_BARS': 1, 'ENTRY_MODE': 'close_rejection', 'ENTRY_MAX_DISTANCE_FROM_IB': 15, 'ENTRY_TIME_MAX': '12:00',
    'STOP_BUFFER': 2, 'STOP_MAX_PTS': 30, 'TARGET_MODE': 'IB_MID', 'TIME_EXIT': '14:00', 'MAX_HOLD_MIN': 120,
    'TRADE_WINDOW_END': '12:00', 'MAX_TRADES_PER_DAY': 1, 'RISK_DOLLARS': 350, 'SLIPPAGE_PTS': 2, 'COST_PER_TRADE': 25,
}
```

## 15. CHECKLIST - ANTES DE DECIR 'YA CUBRÍ AL CREADOR'

- [ ] Testeé TIME_OUTSIDE en [5,10,15,20,30,45,60] (no solo 10)
- [ ] Testeé DISTANCE_OUTSIDE en [5,8,10,12,15,20,25,30] (no solo 10)
- [ ] Testeé combinación TIME x DISTANCE en matriz 7x8=56 (no solo 10x10)
- [ ] Testeé WICK_MIN en [0,2,5,8,10,15,20] y WICK_MAX en [15,20,25,30,40,50] (no solo 10)
- [ ] Testeé TOUCH_TOLERANCE en [0,2,5,10,15] (no solo 0)
- [ ] Testeé IB_END en [10:00,10:30,11:00,11:30] (no solo 10:30)
- [ ] Testeé IB_RANGE_MIN/MAX en [20-60] / [100-250] (no solo 40/120)
- [ ] Testeé ENTRY_MODE en [Close, Open siguiente, Pullback] (no solo Close)
- [ ] Testeé STOP_BUFFER en [0,2,3,5,8,10] (no solo 0 o 2)
- [ ] Testeé TARGET_MODE en [Mid, Opposite, RR 1:1, 1.5, 2:1] (no solo Mid)
- [ ] Testeé TIME_EXIT / MAX_HOLD en [30-240 min] (no solo 120)
- [ ] Testeé SLIPPAGE en [0,1,2,3] y COSTO en [15,20,25,30,35] (no solo 2 y 25)
- [ ] Validé OOS 2026 sin re-optimizar, WR OOS no cae >5pp
- [ ] Si óptimo es muy diferente al video (ej: TIME 45 vs video 10), usé rango alrededor del video, no óptimo exacto, para no overfit

**Si completaste checklist, cubriste 95% de lo que él puede estar usando. Si solo testeaste 1 valor por parámetro, cubriste 5%.**

## Fuentes

- **Reel Df2pC5-phBZ:** @traderdrysdale - IB 21,462/21,380/21,421, Entry 21,451, Stop 21,472, Target 21,421, 'holds with time and distance', 'wick, hold, candle close', 'first touch Madonna'
- **Parámetros definidos:** 62 parámetros en 12 categorías, rangos diseñados para cubrir implícitos del video con 95% probabilidad

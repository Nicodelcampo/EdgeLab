# Lectura de los documentos de @ayaantrades: qué sirve para EdgeLab

Estado: VIGENTE. Fecha: 2026-11-01. Insumos (subidos por Nico):
- `EdgeLab_AyaanTrades_Reel_DfNIZGlAF_c_Detalle_Extenso.md`
- `EdgeLab_AyaanTrades_191_Posts_Deep_Dive_Completo.md`
- `EdgeLab_AyaanTrades_191_Todos_Detalle_Completo.md`

Son resúmenes generados de 191 posts de Instagram. Los números son los que declara el autor, sin datos ni código verificables.
Referente: `docs/NORTH_STAR.md`.

## Conclusión corta
El valor es **metodológico, no de estrategias**. Casi todo lo que proponen como "módulos nuevos" **ya existe en EdgeLab**, y en varios
casos en una versión más estricta. La frase del documento "EdgeLab tiene 0 edges porque no tiene framework 5σ" es falsa: EdgeLab tiene
0 edges promovidos **porque** aplica estas pruebas y nada las pasó todavía. Eso es el sistema funcionando, no una carencia.

## Mapeo: lo que proponen contra lo que EdgeLab ya hace
| Propuesta (Ayaan) | En EdgeLab | Estado |
|---|---|---|
| 390 t-stats, uno por minuto; "look-elsewhere" | Criba maxT de Westfall–Young por sesión, α 0,05 por canal; FDR q 0,10; LORD++ por familia | Ya existe (más estricto) |
| "Fake scans": 2000 permutaciones con signo aleatorio por día | Es exactamente la criba maxT con cambio de signo por sesión | Ya existe |
| Discovery 2020–23 / holdout 2024–26, "mismo signo y > 2σ" | DESC → réplica (OOS) → holdout sellado con una sola apertura y acta; escalera del embudo | Ya existe |
| Bonferroni / Deflated Sharpe | DSR versionado (G2-A1); multiplicidad heredada por linaje | Ya existe |
| Potencia: hacen falta ~400 trades | Todo nulo publica MDE y potencia; `SIN_POTENCIA` no mata | Ya existe |
| Robustez "de al lado" (aguja vs colina, ±10 min) | `exigir_meseta` en la selección | Ya existe |
| Dependencia de outliers (sacar los mejores trades) | `sin_top5_positivo` en el chequeo económico | Ya existe |
| Inyección de ruido (demorar la entrada, empeorar el llenado) | INTEGRIDAD con latencia de 1 vela y placebo; costos canónicos con escenario adverso | Parcial: ver 1 |
| Mercado falso (el mejor de una búsqueda sobre ruido) | Preflight: el ruido puro no puede rechazar ninguna celda | Ya existe |
| Pesos iguales mejor que optimizados fuera de muestra | La cartera viva pondera con riesgo igual × afinidad, con topes | Ya existe |
| Decaimiento de edges (McLean–Pontiff, ICT) | Cartera viva: e-proceso de futilidad y retiro inmediato; foco en régimen actual (ATJ-24) | Ya existe |
| Backtester honesto (llenado del límite sólo si lo atraviesa, stop al precio real, costos) | Simulador: límite +1 tick, stop al primer tick real, orden de ticks dentro de la vela, costos canónicos | Ya existe |
| Hipótesis "cuando pasa X, ¿Y es distinto de lo normal?", con condición, resultado y base definidos antes | Pre-registro, justificación económica, "cómo podría refutarse", espacio de eventos | Ya existe |

## Lo que sí conviene tomar
1. **Inyección de ruido aleatoria como diagnóstico.** INTEGRIDAD prueba hoy una demora fija de 1 vela. La versión de Ayaan hace N
   copias con demora aleatoria de 0 a 2 velas y 1 a 2 ticks de llenado peor, y mira la fracción que sigue ganando. Es más informativa
   para reglas de entrada en ruptura. **Propuesta:** agregarla como *diagnóstico* (no gate) en el informe de INDAGA. Convertirla en
   gate es un cambio de semántica de validación: lo decide Nico.
2. **Subasta de cierre (imbalances de 15:50 ET → minuto 15:51).** Es un flujo forzado con causa (la publicación NYSE/Nasdaq de las
   15:50) y no un patrón de gráfico. El autor mide −$19 por contrato de ES en el minuto 15:51. **No es operable con nuestros costos**:
   la fricción canónica de ES es ≈3,4–3,6 ticks ≈ $43–45 por viaje. Sirve como **información de salida o de contexto**: no quedar
   comprado en ES/NQ en 15:50–15:55. **Propuesta:** medirlo target-free (retorno por minuto 15:45–16:00 en DESC con la criba maxT),
   sin abrir una familia de entradas.
3. **Tamaño en evaluaciones de prop firm.** "Stop ≈ 1/5 del drawdown, pasar en días y no en meses" es coherente con
   `canasta_7_20261030/estimar_propfirm.py`. Queda como insumo cuando una persona habilite una cuenta de evaluación. No se cambia nada
   automático.
4. **Tenencia larga.** Varias ideas de los posts (y el Modelo Asia) dejan correr hasta otra sesión. El simulador tenía un tope fijo de
   240 velas. Ahora cada experimento puede declarar `TOPE_BARRAS` (`docs/research/modelo_asia_20261101/SPEC_MODELO_ASIA.md`), con
   240 por defecto para no cambiar nada de lo ya medido. RANGO-PREAPERTURA, por ejemplo, declaraba salida a las 15:55 pero en la
   práctica cortaba a las 240 velas.

## Lo que no se toma
- **Listas negras de indicadores** (RSI, MACD, FVG, ICT "no funcionan"). Son resultados del autor, con sus parámetros, sus datos y
  sus costos. En EdgeLab toda muerte tiene alcance preciso, así que no se transporta.
- **Las "37 bumps" y los 3 minutos sobrevivientes** (10:50, 13:12, 15:51). Son de su muestra. Si se mide un barrido por minuto, es
  con nuestros datos y nuestra criba.
- **Métricas de performance de su algoritmo** (+452 %, Sharpe 1,94…). No son verificables y no aportan a la decisión.

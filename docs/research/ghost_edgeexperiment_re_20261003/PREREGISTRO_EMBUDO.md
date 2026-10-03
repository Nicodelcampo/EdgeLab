# EdgeExperiment sobre el embudo de EdgeLab — pre-registro (2026-10-03)

Escrito **antes** de calcular ninguna rentabilidad de la réplica sobre datos de EdgeLab. La lógica del proveedor no está en este repositorio; el generador de señales corre en local.

## Pregunta
¿La estrategia (calendario de entradas por hora/día con salida por tiempo y un filtro simple de signo) tiene expectativa positiva **fuera de muestra, con costos y ejecución honestos**, en MNQ?

## Datos y custodia
- Ticks de `nicolasbuttaro/edgelab-ticks-mnq-preholdout` (contratos 09-25 a 09-26). Frontera de holdout de MNQ: `2026-06-30T22:00:00Z`; **no se lee nada posterior** (el export de NinjaTrader y los trades del proveedor de jul–sep 2026 no se usan para evaluar).
- Barras de 1 minuto armadas desde ticks (último precio; sello = hora de **cierre**, convención NinjaTrader). Validación previa de la construcción: 27/27 trades de la réplica sobre SEP26 coinciden exactamente (hora y precio de entrada y salida) con los generados con las barras de NinjaTrader, hasta la frontera del holdout.
- Serie continua = contrato líder por volumen de la sesión completa anterior, monótono, sin back-adjustment, con reinicio de estado en cada roll (política de EdgeLab).
- Huecos de los datos: 2026-03-20→04-06 y 2026-06-10→06-25 (no hay ticks de ningún contrato). No se interpolan.
- Calendario de sesión: la plantilla XML de NinjaTrader no está disponible aquí; se usa un calendario CME de índices mínimo (apertura 17:00 CT, cierre 16:00 CT, cierres tempranos y feriados publicados). **Supuesto declarado**; sólo afecta la guarda de tiempo de sesión en feriados.

## Particiones
- **IS**: sesiones hasta 2026-05-27. Es la fecha de compilación de la estrategia; se presume que sus reglas se ajustaron con datos anteriores. Un buen resultado en IS **no** es evidencia.
- **OOS**: sesiones 2026-05-28 a 2026-06-30 disponibles (≈13 sesiones por los huecos). Es la única prueba limpia sin abrir el holdout. Aviso: el usuario vio estadísticas agregadas del backtest del proveedor en jun–sep sobre series de contratos poco líquidos; es una serie distinta y sólo se usó el período previo al holdout, pero el OOS **no es virgen**.

## Ejecución y costos
- **B (principal)**: orden de mercado en el primer tick posterior a la hora de la orden; compra al ask, vende al bid. Comisión del usuario: USD 1,90 ida y vuelta = 3,8 ticks de MNQ (tick = 0,25 pt = USD 0,50). Sin slippage adicional.
- **V (réplica del backtest del proveedor)**: relleno al open de la barra, misma comisión. Se reporta sólo para comparar.
- Una unidad por entrada. Las oportunidades se evalúan **independientes** (sin netting entre reglas) para las pruebas nulas; el P&L con netting de la réplica se reporta como descriptivo.

## Pruebas y reglas de decisión (fijadas)
1. **Expectativa**: media neta (ticks/trade, ejecución B) en IS y en OOS, con IC 95 % por bootstrap de sesiones (10.000 remuestras).
2. **Nulo de dirección** (5.000 sorteos): se invierte aleatoriamente la dirección de cada sesión completa. Estadística = neto total de las oportunidades. p = P(nulo ≥ real).
3. **Mejor de las 60 reglas** (nulo de máximo del embudo, dirección aleatoria por sesión, 5.000 sorteos): estadística por regla = media neta con n ≥ 10 en IS. p_max global. Sólo IS (en OOS cada regla tiene muy pocos trades).
4. **Calendarios placebo** (2.000): cada regla conserva día, dirección, tenencia y filtro, pero se le sortea una hora nueva en la grilla de 15 minutos. Estadística = neto total. Prueba si **las horas elegidas** importan.
5. **Sensibilidad a costos**: neto con comisión 0, 3,8 (real) y 7,6 ticks; y con 1 tick de slippage por lado.
6. **Contador global** (TrialRegistry): 60 reglas de la estrategia + 3 variantes de ejecución cuentan como campaña propia. No se corrige por el espacio de búsqueda del proveedor, que se desconoce.

**Veredicto:**
- `EDGE_NO_CONFIRMADO` si en OOS la media neta B es ≤ 0, o si su IC 95 % incluye 0, o si el nulo de dirección en OOS da p > 0,05, o si el calendario placebo en OOS da p > 0,05.
- `CANDIDATO_REQUIERE_CONFIRMACION_FUTURA` sólo si todo lo anterior se cumple **y** IS también es positivo bajo B. Aun así no es edge validado: el OOS es corto y no virgen.
- Resultado IS positivo + OOS no concluyente se reporta como «sin evidencia fuera de muestra», no como edge.

## Fuera de alcance / no se hará
No se abre el holdout; no se reoptimizan reglas, horas, tenencias ni filtros; no se evalúa en otros activos hasta tener datos (el análisis sobre «otros activos» será conceptual, no medido).

## Enmienda 1 (escrita tras ver los resultados de las pruebas 1–5, antes de correr las nuevas)
Los resultados 1–5 no fallaron ninguna regla de descarte en OOS. Quedaba sin descartar que el resultado fuera **deriva del mercado** (la réplica es neta compradora: más largos que cortos), como ocurrió con el ORB de PLAN.md. Se añaden, sin cambiar nada de lo anterior:
- **T2b — nulo de dirección que preserva la exposición**: dentro de cada sesión se permutan las direcciones entre sus trades (mismo número de largos y cortos por sesión). 5.000 sorteos. Si p > 0,05 en OOS, la ventaja se atribuye a deriva/exposición.
- **T6 — concentración**: neto sin la mejor sesión y sin las 3 mejores; reparto largo/corto; neto por mes.
- **T7 — línea base «siempre largo»**: mismas horas, filtros y tenencias, pero todas las entradas largas. Si la línea base explica la mayor parte del neto OOS, se atribuye a la deriva.
Regla: si T2b o T7 explican el resultado OOS, el veredicto pasa a `EDGE_NO_CONFIRMADO`.

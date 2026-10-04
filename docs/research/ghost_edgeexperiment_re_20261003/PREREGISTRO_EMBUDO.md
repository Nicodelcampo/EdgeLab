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

## Enmienda 2 — confirmación única en el holdout de MNQ y transferencia a otros activos (escrita antes de leer datos posteriores al 2026-06-30)
Autorización: el usuario aprobó explícitamente abrir **una sola vez** el holdout de MNQ y probar el resto de activos recomendados.

### A. Confirmación en el holdout de MNQ (una apertura)
- Datos: `MNQ_09-26` y `MNQ_12-26` (`edgelab-ticks-nt8-canonical`, `*_ticks_ext.parquet`); sesiones con fecha de trading ≥ 2026-07-01, hasta la última sesión completa disponible. Roll por volumen de la sesión anterior (misma política).
- Especificación **congelada**: réplica, calendario de sesión, ejecución B (ask/bid en el primer tick), comisión 3,8 ticks. Se corre **una vez**; el resultado se registra sea cual sea. No se modifica nada después de verlo. Los feriados 2026-07-03 y 2026-09-07 se tratan como cierre a las 12:00 CT (supuesto declarado).
- **Éxito** (todas): media neta > 0; IC95 por bootstrap de sesiones excluye 0; p ≤ 0,05 en nulo de dirección por sesión, nulo que preserva exposición y calendarios placebo; y la media de «siempre largo» < la media de la estrategia.
- **Fracaso** si falla cualquiera. Un fracaso se reporta como tal y el candidato queda descartado como edge; un éxito eleva el estado a «confirmado en una muestra independiente», no a «edge garantizado» (queda pendiente tamaño de muestra y régimen).
- Aviso de custodia: el holdout de MNQ queda consumido tras esta corrida.

### B. Transferencia: ES, NQ, MES, RTY (solo datos previos al holdout)
- Mismo calendario congelado, mismas particiones IS/OOS, mismas pruebas (T1, T2, T2b, T4, T7). **No se abre el holdout de estos activos.**
- Datos: `edgelab-ticks-es-preholdout`, `edgelab-ticks-nq-preholdout`; MES y RTY desde los `*_ticks_ext.parquet` de `nt8-canonical`, cortados estrictamente en `< 2026-06-30T22:00Z` al construir las barras (las filas posteriores se descartan sin analizarlas).
- Comisión ida y vuelta: USD 1,90 para micros (MNQ, MES); USD 4,50 para ES, NQ y RTY (referencia habitual de contratos completos; supuesto declarado). Para YM, ya medido con USD 1,90, se reporta además con USD 4,50.
- Criterio de «se transfiere»: OOS con media neta > 0, IC95 que excluye 0 y p ≤ 0,05 en dirección y calendario placebo.
- Predicción registrada antes de medir: ES, NQ y MES se parecerán a YM (positivo); RTY incierto.
- Contador global: +4 campañas (una por activo, 60 reglas cada una → 240 pruebas) y +1 del holdout.

## Enmienda 3 — error de ejecución en la primera apertura del holdout de MNQ (registrado antes de repetir)
**Qué pasó.** La primera corrida del holdout (archivo `holdout_run1_roll_invalido.json`) usó una serie incorrecta. El código de roll partió con MNQ_09-26 y MNQ_12-26 desde marzo, cuando ambos eran contratos lejanos casi sin volumen; un cruce espurio de volumen en esos días fijó MNQ_12-26 como líder de forma monótona desde 2026-06-19. Resultado: julio y agosto se probaron sobre MNQ_12-26 (≈56 mil contratos por mes) en vez de MNQ_09-26 (≈30 millones por mes, líder real hasta septiembre). Es una violación de la especificación pre-registrada («contrato líder por volumen de la sesión anterior»), no un ajuste a la estrategia. Esa corrida **no es la prueba pre-registrada**.
**Cifras de la corrida 1, tal como salieron, se conservan sin ocultar:** 307 trades, media neta −18,1 ticks, IC95 −44,3 a +9,7, p dirección 0,61, p exposición 0,76, p calendario 0,72.
**Corrección (mecánica, anterior a repetir; no depende del resultado):** el cálculo del roll se limita a sesiones desde 2026-06-24 (primera fecha con volumen real de MNQ_09-26), de modo que los días sin liquidez no pueden disparar el cruce. Nada más cambia: reglas, calendario, ejecución, comisión, umbrales y criterios de éxito/fracaso son los de la enmienda 2.
**Honestidad sobre el sesgo:** el resultado de la corrida 1 ya es conocido, así que la repetición no es ciega. Por eso (1) los umbrales no se tocan, (2) se reportan ambas corridas, y (3) cualquier lectura debe tener en cuenta esta repetición. Tras la repetición el holdout de MNQ queda cerrado definitivamente.

## Enmienda 4 — la copia del holdout de MNQ en Kaggle tiene sesiones faltantes y truncadas; regla de elegibilidad por volumen (antes de la corrida 3)
**Segundo error de ejecución.** La corrida 2 (`holdout_run2_roll_invalido.json`, trades 309, media −17,5 ticks, IC95 −43,1 a +10,2, p 0,59 / 0,75 / 0,69) repitió el problema: el contrato lejano MNQ_12-26 volvió a ganar el roll en julio. Causa verificada solo con metadatos de volumen: en `MNQ_09-26_ticks_ext` faltan sesiones completas (2026-07-03, 07-08, 07-17, 08-14, 08-19) y hay sesiones truncadas (por ejemplo 07-07: 0,3 M contratos frente a una mediana de 2,5 M; también 07-15, 07-21, 07-29, 08-05, 08-13, 08-18, 08-26). En los días sin datos de MNQ_09-26, el volumen mínimo de MNQ_12-26 supera a cero y dispara el cruce. Los datos del holdout en Kaggle **no son una serie continua completa**; la elegibilidad EF0 de ese tramo es FALLO por cobertura.
**Regla de elegibilidad y de roll (sólo volumen, fijada antes de la corrida 3):**
1. Roll: el líder sólo cambia a MNQ_12-26 si, en la sesión previa, su volumen es ≥ 100.000 contratos **y** supera al de MNQ_09-26 **y** MNQ_09-26 tiene volumen > 0. Monótono.
2. Sesión elegible: volumen total ≥ 50 % de la mediana de volumen de su contrato en el tramo analizado. Las sesiones truncadas se excluyen completas; no se mira ningún resultado para decidirlo.
3. Todo lo demás (reglas, ejecución, comisión, umbrales, criterios de éxito) sin cambios.
**Estatus.** Es la tercera lectura del mismo tramo: ya se conoce que las corridas 1 y 2 fueron negativas, así que la corrida 3 no es ciega. Se interpreta como un chequeo de consistencia sobre la serie correctamente especificada, no como una confirmación limpia. Tras esta corrida el holdout de MNQ queda cerrado definitivamente.

## Enmienda 5 — apertura única de los holdouts de MES, RTY y YM como cesta agrupada (escrita antes de calcular ningún resultado de estos activos)
Autorización: el usuario pidió explícitamente el chequeo de cobertura y, después, abrir los holdouts de los otros activos.

### Cobertura (solo volumen por sesión; no se leyeron precios ni resultados)
- **ES y NQ: no hay datos posteriores al 2026-06-30 en Kaggle.** `edgelab-ticks-nt8-canonical` solo contiene MES, MNQ, MYM, RTY e YM; los datasets de ES y NQ llegan hasta el corte del holdout. Quedan fuera. MES cubre el S&P 500.
- **MYM queda fuera** por duplicar el Dow (YM). **MNQ ya fue consumido** (enmiendas 2 a 4); se reporta aparte y no entra en la cesta.
- Sesiones del 2026-07-01 al 2026-09-18 en el contrato 09-26 (líder hasta el 2026-09-14, según volumen): **RTY** 0 faltantes y 2 de bajo volumen (feriados 07-03 y 09-07); **MES** 3 faltantes (07-29, 08-06, 08-13) y 5 truncadas (<50 % de la mediana: 07-03, 07-28, 08-05, 08-12, 09-07); **YM** 3 faltantes (08-20, 08-21, 08-26), 4 truncadas (07-03, 08-14, 08-25, 09-07) y sin ticks el 09-08 y 09-09. Es el mismo tipo de hueco que tenía la copia de MNQ.
- Regla de elegibilidad (la de la enmienda 4): una sesión entra solo si su volumen total es ≥ 50 % de la mediana del contrato en julio–septiembre; las sesiones faltantes o truncadas se excluyen completas, sin mirar resultados.

### Especificación (congelada)
- Calendario de 60 reglas, ejecución de libro (ask/bid en el primer tick) y calendario de feriados exactamente como en la enmienda 2. Comisión ida y vuelta: MES USD 1,90; RTY y YM USD 4,50 (mismos supuestos que la transferencia).
- Roll: se escanea desde 2026-06-24; el líder pasa de 09-26 a 12-26 solo si, en la sesión previa, el volumen de 12-26 supera al de 09-26, es ≥ 5 % de la mediana de volumen diario del 09-26 en julio–agosto, y el 09-26 tiene volumen > 0. Monótono.
- Ventana: sesiones con fecha de trading entre 2026-07-01 y 2026-09-28 (último dato disponible).
- Corrección de un defecto de la corrida 3 de MNQ, declarado: allí el nulo de calendarios placebo se calculó sobre todas las sesiones, sin aplicar el filtro de elegibilidad que sí usaron los demás estadísticos. En esta corrida el filtro se aplica a todos. El resultado de MNQ no se recalcula.

### Cesta y estadísticos
- Cada oportunidad del calendario es una operación sobre una cesta de **1 MES + 1 RTY + 1 YM**. El resultado de la operación es la suma, en USD netos de comisión, de las patas elegibles de esa regla y sesión (una pata sin dato elegible aporta 0). La cesta se trata como un único activo en todas las pruebas, para preservar la correlación entre activos.
- Pruebas (las mismas de la enmienda 2, sobre la cesta, con semillas 20261006): IC95 por bootstrap de sesiones (5.000), nulo de dirección por sesión (5.000), nulo que preserva exposición (3.000) y calendarios placebo (2.000); referencia «siempre largo» sobre la cesta.
- **Éxito** (todas): media neta de la cesta > 0; IC95 excluye 0; los tres p ≤ 0,05; y la media de «siempre largo» < la media de la estrategia.
- **Fracaso** si falla cualquiera. El fracaso cierra la hipótesis con estos datos. Un éxito sube el estado a «confirmado en una muestra posterior», no a «edge garantizado», porque MNQ ya dio negativo y los activos están correlacionados.
- Se reportan además, descriptivamente, la media neta de cada activo por separado y el resultado de MNQ.

### Custodia y sesgo declarados
- Se abre **una sola vez**. No se cambia nada después de ver el resultado. Se guarda una marca de bloqueo que impide repetir.
- Estos tres mercados se mueven con MNQ en el mismo período, así que no es una prueba independiente: la cesta reduce el ruido propio de cada contrato, no el del mercado.

## Enmienda 6 — apertura única de ES y NQ de julio a septiembre como cesta (escrita antes de calcular ningún resultado de estos datos)
Autorización: el usuario pidió explícitamente escribir esta enmienda y abrirlos.

### Datos y custodia
- Dataset privado de Kaggle `nicolasbuttaro/edgelab-ticks-es-nq-2026q3-ext` (esquema `canonical_tick_v1`, ticks de trade con bid y ask), generado bajo la enmienda HOLDOUT-A1 del proyecto (2026-09-26). Archivos: `ES_09-26`, `ES_12-26`, `NQ_09-26`, `NQ_12-26`. Ventana del dataset: 2026-06-30 22:00 UTC a 2026-09-30 22:00 UTC; las sesiones completas llegan hasta el **2026-09-25**.
- **Custodia.** La enmienda HOLDOUT-A1 declara los datos de julio a septiembre de 2026 como exploración del proyecto y fija el holdout formal del proyecto a futuro desde el 2026-10-01. Esta apertura consume solo la regla de custodia de este experimento (una apertura por activo en julio a septiembre); **no toca el holdout formal de octubre en adelante**, que sigue sin leerse.
- **Cobertura, tomada del catálogo de sesiones del propio dataset** (criterio fijado por el generador, sin mirar precios: ≥ 200.000 ticks por sesión y ningún hueco de más de 30 minutos): **NQ 57 sesiones completas y 6 excluidas** (03-jul y 07-sep feriados; 10-sep hueco de más de 30 minutos; 15, 16 y 17-sep pocos ticks). **ES 52 completas y 10 excluidas** (03-jul y 07-sep; 14, 20, 21, 26 y 28-ago; 16, 17 y 18-sep). Contrato y roll: los del catálogo (NQ pasa a 12-26 el 18-sep; ES el 15-sep). Solo entran las sesiones completas del catálogo; las excluidas no se interpolan.

### Especificación (congelada, igual que las enmiendas 2 y 5)
- Calendario de 60 reglas, ejecución de libro (ask/bid en el primer tick), calendario de feriados y filtro del signo de los 15 minutos previos. Comisión de ida y vuelta de USD 4,50 en ambos (NQ 0,9 ticks; ES 0,36 ticks), el mismo supuesto de la transferencia.
- Ventana: sesiones del catálogo, del 2026-07-01 al 2026-09-25.
- Defecto declarado del dataset: no hay ticks antes del 30 de junio a las 22:00 UTC, así que en la primera sesión no hay referencia de 15 minutos para las franjas más tempranas; esas oportunidades no se evalúan (mismo tratamiento que «sin referencia» en las otras pruebas).

### Cesta y estadísticos
- Cesta de **1 ES + 1 NQ**, resultados en USD netos de comisión, tratada como un único activo, con el mismo procedimiento de la enmienda 5 (suma por regla y sesión; IC95 por bootstrap de sesiones de 5.000; nulo de dirección por sesión de 5.000; nulo que preserva exposición de 3.000; calendarios placebo de 2.000; referencia «siempre largo»). Semillas 20261009.
- **Éxito** (todas): media neta de la cesta > 0; IC95 excluye 0; los tres p ≤ 0,05; y la media de «siempre largo» < la media de la estrategia. **Fracaso** si falla cualquiera.
- Se reportan además, descriptivamente, ES y NQ por separado.

### Cómo se interpreta (fijado antes)
- ES y NQ son los mismos índices que MES y MNQ (S&P 500 y Nasdaq-100) en el mismo período: **no son pruebas independientes de ellos**. Aportan sesiones más completas que MES y MNQ (la lectura de MNQ tenía 41 sesiones y la de MES 53 con huecos).
- Éxito: sube el estado a «confirmado en una muestra posterior en los dos índices de mayor volumen», no a «edge garantizado». Fracaso: con MNQ y la cesta MES+RTY+YM ya no confirmados, el resultado cierra la hipótesis de calendario con los datos de julio a septiembre.
- Se abre **una sola vez**, con marca de bloqueo; no se cambia nada después de ver el resultado.

# Etapa C — celda GC 04:15 probada en oro spot, datos posteriores (pre-registro, 2026-10-04)

Estado: escrito ANTES de descargar o calcular ningún resultado con estos datos. Los ticks de COMEX (GC) no existen en Kaggle después del 2026-06-30, así que la prueba fuera de muestra se hace con **XAU/USD spot de Dukascopy** (ticks con bid y ask, gratuitos, `datafeed.dukascopy.com`), que es el mismo activo económico pero otro mercado. Esto es una prueba de la **hipótesis**, no una réplica exacta de la ejecución en futuros.

## Qué se congela
La celda base de la etapa B: franja 04:15 hora de Chicago, días hábiles, condición «subida de los 15 minutos previos» (estricta, > 0), **corto**, salida por tiempo a 15 minutos, sin stop ni objetivo. No se prueba ninguna otra celda, franja ni salida. Comisión de ida y vuelta equivalente a USD 4,50 por contrato de GC (0,45 ticks).

## Diferencias entre fuentes (declaradas)
- Dukascopy publica cotizaciones (bid y ask), no operaciones. El precio de referencia de las barras es el **punto medio** `(bid + ask)/2`; la última cotización de cada minuto define el cierre de la barra de 1 minuto. El spread medio en la hora de la muestra fue ≈ USD 0,61, aproximadamente el doble que el spread de COMEX en la ventana (3 ticks = USD 0,30). Es un costo más duro: un resultado positivo en spot es **conservador** respecto al costo de futuros, pero la dinámica puede diferir.
- Unidades: todo se expresa en «ticks de GC» = USD 0,10 (1 punto de oro = 10 ticks).
- Horas: 04:15 CT corresponde a 09:15 UTC (horario de verano de EE. UU.) o 10:15 UTC (invierno): siempre 10:15 en Londres. Se descargan solo las horas UTC que cubren desde 17 minutos antes de la franja hasta 18 minutos después.

## Definición operativa
- `b1 = franja + 1 min`. Condición: `mid(cierre del minuto que termina en b1) − mid(cierre del minuto que termina en b1 − 15 min) > 0`.
- Entrada: primer tick con sello ≥ `franja + 2 min`, vende al bid. Salida: primer tick con sello ≥ `entrada_referencia + 15 min`, compra al ask.
- Sesión elegible solo si hay al menos 50 cotizaciones en los 15 minutos de la ventana de la operación y al menos 50 en los 15 minutos previos. No se interpola.

## Paso 1 — Calibración de la fuente (no prueba edge)
Se descargan las sesiones de abril a junio de 2026, que ya existen en los ticks de GC. Se compara, sesión por sesión, spot contra GC con la misma celda:
- Concordancia del signo de la condición «subida de los 15 minutos previos»: ≥ 85 % de las sesiones.
- Correlación del resultado neto de las sesiones en que ambas fuentes disparan la operación: ≥ 0,6.
- Si no se cumple cualquiera, la fuente spot **no es equivalente** y la prueba fresca se declara no informativa (no se calcula ni se reporta como confirmación o refutación).

## Paso 2 — Prueba principal (sesiones nuevas: 2026-07-01 a 2026-10-02)
- Estadístico: media neta por operación en ticks de GC para las sesiones que disparan la condición.
- Prueba: nulo de dirección sorteada por sesión sobre las operaciones de la celda (el mismo estadístico de la etapa B: `z = Σ (neto_corto − neto_largo)/2 / √V`), 20.000 sorteos, semilla 20261008, unilateral.
- Decisión (una sola vez, sin ajustes posteriores):
  - **Replica** si la media neta > 0 **y** p ≤ 0,05.
  - **No replica** si la media neta ≤ 0.
  - **Inconcluso** si la media neta > 0 pero p > 0,05.
- Potencia declarada: con ≈ 35 operaciones y desvío de ≈ 68 ticks por operación (medido en los datos de GC), un efecto de +21,3 ticks da un z esperado de ≈ 1,9 (potencia alrededor del 55 %); un efecto de +10, z ≈ 0,9. Un resultado «inconcluso» es el más probable aunque el efecto exista.

## Pruebas secundarias (descriptivas, sin regla de decisión)
«Corto sin condición» a las 04:15 en las mismas sesiones (≈ 65 operaciones) y «largo tras bajada». También la media por mes.

## Contador de pruebas
+2 pruebas (principal y sin condición), en una campaña nueva.

## Predicción registrada
Espero un resultado «inconcluso» o «no replica». Si el efecto de la etapa B fuera mayormente un artefacto de selección, la media neta fuera de muestra estará cerca de cero o será negativa.

## Enmienda C1 — alcance real de los datos (escrita antes de calcular, 2026-10-04)
- **Ventana.** Por instrucción del usuario («descarga solamente las últimas 3 semanas del oro; pará todo lo demás») se descargaron solo las sesiones del **2026-09-14 al 2026-09-30** (13 días hábiles; no se leen el 1 y 2 de octubre por el holdout formal HOLDOUT-A1). Todo ese tramo es **posterior a la publicación de la estrategia (2026-09-10 12:00 CT**, fecha derivada del ID del reel). No hay período «antes» en esta muestra, así que la comparación antes/después del 10-sep queda **fuera** de esta prueba.
- **Paso 1 (calibración con abril a junio): no se hace.** Exigía descargar abril a junio de Dukascopy, lo que el usuario descartó, y no existen ticks de GC posteriores a junio para comparar. Consecuencia declarada: el resultado se reporta **sin calibración de fuente** y se lee como descriptivo; no puede declararse réplica ni refutación de la celda de futuros, solo de la hipótesis en oro spot. Se mantienen los controles de calidad de datos (≥ 50 cotizaciones en la ventana de la operación y ≥ 50 en los 15 minutos previos).
- **Paso 2 (prueba principal).** Sin cambios: celda congelada, nulo de dirección por sesión, 20.000 sorteos, semilla 20261008, unilateral, decisión «Replica / No replica / Inconcluso». Pruebas secundarias descriptivas: «corto sin condición» y «largo tras bajada».
- **Potencia.** Con 13 sesiones habrá unas 6 a 7 operaciones con la condición. Con +21,3 ticks de efecto y 68 de desvío, el z esperado es ≈ 0,8: la potencia es muy baja. **Inconcluso es el resultado casi seguro** aunque el efecto exista. Una media neta negativa solo se podrá leer como compatible con una mala racha o con ausencia de efecto.
- Para el contador de pruebas rige lo ya registrado (+2).

## Enmienda C2 — orden de las corridas y qué cuenta como decisión (escrita antes de correr, 2026-10-04)
- **Corrida R1:** celda congelada sobre las sesiones del **14 al 30 de septiembre** (posteriores a la publicación del 10-sep), una sola vez, como se pidió.
- **Corrida R2:** R1 más las sesiones del **1 al 9 de julio** que ya estaban descargadas (1, 2, 3, 6, 7, 8 y 9; el 3 de julio es feriado y entra solo si cumple la elegibilidad de cotizaciones). Es una ampliación de la misma prueba.
- **Qué cuenta como decisión.** R1 y R2 son **miradas intermedias** del mismo contraste. Se reportan como descriptivas, sin declarar «Replica», «No replica» o «Inconcluso». La **regla de decisión de la enmienda C1 se aplica una sola vez, a la ventana completa** del 1 de julio al 30 de septiembre, cuando esté descargado también el tramo del 10 de julio al 10 de septiembre (descarga pedida por el usuario). Así no se acumulan varias pruebas al 5 % sobre las mismas sesiones.
- Los resultados de R1 se registran tal como salgan; no se modifica ninguna regla de la celda después de verlos.

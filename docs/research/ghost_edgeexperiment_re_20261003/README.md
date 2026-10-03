# EdgeExperiment (Ghost Financial) — reconstrucción por observación: metodología y resultados

**Fecha:** 2026-10-03 · **Estado:** réplica empírica validada en dos contratos; sin evaluación de rentabilidad propia.
**Alcance de este documento:** metodología, evidencia agregada y límites. **No** incluye la tabla de reglas, el simulador, los scripts de inspección de la DLL ni la definición exacta del filtro: son material del proveedor y se conservan fuera de este repositorio público.

## Qué es
`EdgeExperiment` es una estrategia comercial de NinjaTrader 8 (Ghost Financial, build 1.2.0) para **MNQ a 1 minuto**, sesión `CME US Index Futures ETH`, que exige clave de licencia. Sólo se configuran la clave y los contratos por trade. La lógica va compilada y ofuscada.

## Alcance y límites éticos
- Objetivo: entender y replicar el **comportamiento observable** de una licencia propia, con datos y trades propios.
- No se intentó evadir, falsificar ni investigar el licenciamiento (validación de licencia y atadura a máquina quedaron fuera del alcance). La DLL no se ejecutó ni se modificó.
- Los derechos sobre la estrategia pertenecen a su proveedor. No redistribuir su lógica.

## Entradas usadas (hashes en el paquete original, no versionado aquí)
Export NinjaScript original; histórico Last de 1 minuto de MNQ DEC26 y SEP26; dos exportaciones del Strategy Analyzer (DEC26: 577 trades; SEP26: 1.052 trades); plantilla de sesiones de NinjaTrader.

## Metodología
1. **Extracción estática de lo observable:** cadenas y metadatos de la DLL (nombres de campos y métodos) sin ejecutarla; sirvieron de pista para formular hipótesis, no como prueba.
2. **Tabla de oportunidades, no sólo de trades:** para cada regla y fecha elegible se registró si la estrategia operó o no (1.282 candidatos en DEC26). Un modelo que sólo explica los trades no distingue un filtro de una coincidencia; hay que explicar también los **no-trades**.
3. **Horarios:** la hora de las reglas está en `America/Chicago` con DST real; el export del analizador está en horario de Argentina; el histórico se cruzó en UTC. Nunca se compararon strings horarios.
4. **Conteo de barras, no de minutos:** el contrato DEC26 era ilíquido al inicio y faltan minutos; la mecánica de entrada y salida depende de la secuencia de barras disponibles.
5. **Causalidad:** el simulador usa únicamente barras, reglas y calendario; el CSV de trades entra sólo en un validador separado, después de generar las predicciones. Se comprobó que (a) recortar el histórico a 1.000, 10.000 y 50.000 barras produce exactamente las mismas decisiones que los prefijos del histórico completo, y (b) alterar todos los precios posteriores a la barra 50.000 no cambia decisiones anteriores.
6. **Pruebas:** 13 pruebas sintéticas y de regresión (barras faltantes, retornos nulos, DST, órdenes pendientes, conjuntos vacíos).
7. **Revisión independiente** del predictor y del validador; sus hallazgos sobre el validador se corrigieron y se cubrieron con pruebas.
8. **Validación fuera de muestra con predicciones congeladas:** antes de recibir el export de SEP26 se guardaron las predicciones y un manifiesto de hashes del modelo, reglas, calendario, barras y predicciones. Luego se compararon, **sin ajustar el modelo**.

## Resultados
| Contrato | Trades comparados | Campos exactos (de 9) | Falsos positivos / negativos |
|---|---:|---:|---:|
| DEC26 (muestra de descubrimiento) | 577 / 577 | 9 / 9 | 0 / 0 |
| SEP26 (predicción congelada, fuera de muestra) | 337 / 337 | 9 / 9 | 0 / 0 |

Campos comparados: nombre de regla, dirección, hora y precio de entrada, hora y precio de salida, nombre de salida, P&L neto y comisión.

Estadísticas reportadas por el analizador (1 contrato, comisión ida y vuelta de $1,90):

| | DEC26 | SEP26 (subconjunto verificado) |
|---|---:|---:|
| Trades | 577 (343 long / 234 short) | 337 (214 long / 123 short) |
| % ganadores | 50,95 % | 65,3 % (220/337) |
| Beneficio neto | $7.535,70 | $16.070,20 |
| Profit factor | 1,39 | 2,93 |
| Drawdown (orden del CSV) | −$3.821,40 | −$660,90 |

El subconjunto SEP26 son los trades íntegramente dentro de la cobertura de barras disponible (2026-06-08 a 2026-07-28); se eligió **sólo por tiempo**, no por regla ni rentabilidad. **715 de los 1.052 trades de SEP26 siguen sin verificar** por falta de barras (marzo a junio y agosto a septiembre de 2026).

## Lo que no se puede identificar con estos datos
`parameter_identifiability` del paquete original lo demuestra con dos ejemplos: el calentamiento inicial y el margen de sesión admiten varios valores que dan exactamente los mismos 577 trades. Tampoco quedan identificados el orden de eventos simultáneos que no aparece en la muestra, límites internos de entradas, comportamiento con datos fuera de sesión, reinicios y lógica en tiempo real. 577/577 es equivalencia empírica en la muestra, no recuperación literal del código.

## Lectura para EdgeLab (y lo que NO se concluye)
- Se aprendió una **estrategia de calendario**: entradas programadas por hora y día de la semana con un filtro simple de signo, no una señal de microestructura.
- **No se evaluó si tiene edge.** Las cifras de rentabilidad son las del backtest del analizador; 60 reglas elegidas por el proveedor implican un riesgo de selección que no se midió (sin PBO/DSR/SPA ni nulo de máximo del embudo de EdgeLab), y el rendimiento en SEP26 corresponde a un período corto.
- Siguiente paso útil, si se quiere evaluar: pasar la réplica por el embudo (EF3/EF4) sobre datos propios con partición cronológica y contador de pruebas, y obtener el histórico de marzo a septiembre para cerrar los 715 trades pendientes.

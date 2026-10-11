# AVZVOL: retroceso parcial y primer paso simétrico

## Estado real
**La nueva hipótesis de retroceso parcial tiene máxima prioridad, pero todavía NO tiene resultados empíricos.** Se implementó un evaluador puro y se validó con17tests,900casos aleatorios de simetría y7fracciones de retroceso sintéticas. Esto comprueba lógica/causalidad, no una ventaja de mercado ni velocidad del detector.

Los6exports existentes no contienen la trayectoria, el instante del retroceso ni flujo agresor. mx_h/O3a/O3b no contestan la nueva pregunta: máximo no dice cuándo ocurrió, yO3bempieza después del toque, no después de un retroceso parcial. Se confirmó en metadata Kaggle que existen los6MNQticks de la fuente canónica versión1. Sus precios/quotes/volúmenes NO se cargaron ni se generaron nuevas etiquetas de mercado. Replay y condiciones de horario/sesión/agresor siguen pendientes en el proyecto; ningún gate se cambia.

## La pregunta exacta
Dado un racimo de límites congeladosL/H, observar una salida y un máximo de alejamiento **conocido hasta el instante actual** R. Cuando el precio vuelve una fracciónqdeRpor primera vez, observar el precio realPdel trigger, no asumir ejecución en un umbral ideal.

Para una salida por arriba, con bordeH:
- Trigger: R≥mínimoD y 0<P−H≤(1−q)R.
- Llegada: tocaHantes de alcanzarP+(P−H).
- Entrada: alcanzaH−1tickantes deP+(P−(H−1)).
- Cruce completo: alcanzaL−1tickantes deP+(P−(L−1)).

Por abajo se refleja todo. Cada desenlace compara **distancias iguales desdeP**; no usar siempre el máximo original como barrera contraria. Los tres endpoints tienen barreras distintas, por lo que sus tasas no se comparan como una única apuesta.

Ejemplo puramente geométrico: precio se alejó40ticks por arriba y retrocede50%; el trigger queda20ticks del borde. Se compara tocar el borde frente a subir otros20ticks desde el trigger. Si retorna75%, queda10ticks: la barrera contraria queda20ticks por encima del borde, NO en el máximo40.

R es el máximo observado al trigger, nunca el máximo final de toda la excursión. Después del trigger se congelan features/barreras. Un tick que salta directamente hasta el racimo se registra como toque antes del trigger observado, no como una victoria retroactiva gratuita. Los outcomes empiezan en la siguiente observación; no se modela fill ni beneficio.

## Pruebas y variantes
Primera familia acotada:5configuraciones ya elegidas por frecuencia (4/1000/20,30,45;4/500/45;5/1000/45), distancia10/20/40ticks y vuelta25/50/75%, toque y horizonte2000barras. Son45reglas primarias propuestas, NO45resultados obtenidos.

La campaña extendida conserva:
- Distancias5/10/20/40/80ticks y0,25/0,5/1/2/4alturas reales; volatilidad conocida antes de salida como tercer normalizador.
- Vuelta10/25/33⅓/50/66⅔/75/90%; instante real del primer trigger, sin anticipación.
- Toque, un tick dentro y cruce completo; horizontes100/500/2000barras y alternativas30/120/600segundos.
- Primera salida vs excursiones repetidas no solapadas; máximo móvil vs hito inicial congelado. Sólo primera salida/máximo móvil/horizonte barras están implementados en el prototipo.
- Cinco parámetros del detector/racimo: mínimo, ventana del racimo, altura, percentil ywindow_bars. Manifest conserva1536configuraciones propuestas; ninguna recalibración nueva se ha ejecutado.

Antes de leer outcomes de una campaña nueva, seleccionar soporte/frecuencia, luego elegir cortes/modelos sólo en entrenamiento. Mantener todos los resultados y los casos sin trigger; qgrande puede dar un porcentaje alto a costa de muy pocos casos. No mezclar cientos de configuraciones correlacionadas como si aportaran cientos de muestras independientes.

## Features que deben distinguir la vuelta
1. Velocidad y duración de alejamiento frente a velocidad de vuelta; relación entre ambas.
2. Barras inclusivas por tick, segundos por distancia y eficiencia de trayectoria; retorno rápido/recto vs lento con pausas o renovados extremos.
3. Delta de volumen agresor de alejamiento y vuelta, normalizado por volumen; cambio de delta, volumen por tick y cobertura de agresor clasificado. Intervalos de flujo no se solapan en el máximo. Desconocido no significa delta0. Orderbook imbalance necesita tamaños bid/ask, no se inventa a partir de quotes de precio.
4. Picos causales: fecha/instante de confirmación, estructura menor-máximo/mayor-mínimo y falsas reanudaciones. No usar un pivot antes de su confirmación ni backfill.
5. Memoria espacial del corredor entre trigger y racimo: visitas/rechazos/travesías anteriores, congestión y velocidad del último recorrido. Toda esa historia debe terminar antes del trigger.
6. Coincidencia simultánea multiescala, edad y concentración del racimo. Distinguir densidad de volumen real de una mera altura pequeña.

El prototipo calcula sólo distancia, tiempos/barras, eficiencia de trayectoria, velocidades y delta declarado. No afirma tener ya implementados todos los indicadores/corredores/modelos de la campaña.

## Estadística sin crear ventaja por selección
Reportar señal por formación y por sesión/hora de cobertura verificada; hit/total de señales, hit/resueltos y cotas con todos los no resueltos. Separar límites de ventana/sesión y overshoots. Una tasa superior a50%entre resueltos no basta: drift, selección del trigger, gaps y censoring alteran el benchmark. Contrastar con contexto reciente sin racimo y controles causales certificados cuando existan.

Dependencia por día/episodio y por configuraciones: bootstrap de días preservando simultáneamente sus señales, corrección de multiplicidad de la familia completa y validación temporal anidada. No elegir distancia/porcentaje después de ver el período que se quiere evaluar. Los períodos históricos ya están expuestos; no llamarles confirmación ciega ni abrir la reserva por esta prueba. Un primer paso simétrico no demuestra rentabilidad neta de costos.

## Profundización empírica de la pista anterior: debilitada
Se volvió a examinar coincidencia20contenida en30/45 en el mismo nacimiento. Se compararon grupos con **la misma altura real**, para que las barreras±hdeO3bno fueran distintas sólo por geometría.

Ajuste exacto por contrato/sesión/altura, igual peso por sesión:

| Bloque | Ninguna coincidencia: lado salida tras toque | Ambas coincidencias | Filas ambas / sesiones comunes |
|---|---:|---:|---:|
| 1 | 47,45% | 58,73% | 32 / 21 |
| 2 | 46,49% | 46,31% | 60 / 28 |
| 3 | 55,14% | 57,28% | 108 / 38 |

Ya no mejora en los3bloques como en el agregado anterior. Exigir además horario/tendencia/momentumdeja sólo2/4/9filas por grupo en el ajuste más fino: demasiado poco para concluir. Se conservan todos los recortes, incluidos los adversos; no perseguir sus extremos100%/25%. La coincidencia se mantiene como feature candidato, no como filtro confirmado.

**Estas tasas son deO3bdespués del toque. NO responden a la nueva pregunta de vuelta parcial.** Su medición requiere el nuevo trigger y barreras simétricas desde ese instante.

## Cómputo y entrega necesaria
La implementación es un evaluador de referencia, no el motor optimizado de una campaña masiva. El adaptador debe agregar bloques/footprints una vez porwindow_bars, ramificar percentiles con su calibración histórica correcta, compartir cintas inmutables entre ternas de racimo y recorrer secuencia de trades una vez manteniendo estados/barreras activos y estadísticas prefijo. Verificar paridad de detector y resultados antes de sustituir el código de referencia.

Falta la habilitación del replay con un export de trades ordenados y racimos de creación: secuencia, timestamp, sesión/clock con procedencia, precio en ticks, volumen, agresor/unknown, barid/regla de barras y límites/id/configuración/instante de creación del racimo. Para picos se necesitan instantes de confirmación. No sustituirlo por OHLC sin un ledger explícito de ambigüedad intrabar.

## Reproducción
```bash
cd docs/research/avzvol_partial_return
python -m unittest -v test_partial_return
python coformation_followup.py --repo ../../.. --raw <export-root> --out <derived-output>
```
El test usa precios inventados. El segundo comando sólo agrega etiquetas ya expuestas y no carga ticks de mercado. Se dejan separados estado de implementación, campaña propuesta y medición pendiente; no promoción, P&L ni gates alterados.

La adjunción de gráficos permanece indisponible; la comparación está visible en tabla y losCSVversionados.

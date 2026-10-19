# AVZVOL: excursiones densas, rearmado y contexto del recorrido

## Conclusión

La ampliación está ejecutada: 864 grupos de reglas, seis familias de detector, primera salida versus primera salida que alcanza D, tres endpoints y un control trasladado. Misma fuente pinneada MNQ12-26 v2, mismas10 sesiones seleccionadas; NO seis contratos ni holdout. 3223152 evaluaciones y 1151490 filas con señales **no son observaciones independientes**.

El rearmado aumenta fuertemente el número de señales, pero las familias densas sin contexto están cerca de50% en la prueba de toque con barrera contraria igual. La pista más prometedora es un corredor poco visitado, con mínimo40 ticks y vuelta50%, en P80/W5/racimo8/1000/20. Su54.6% observado NO basta para declarar edge: el incremento contra control es incierto, los vecinos no repiten claramente el efecto y existe multiplicidad.

## Qué se probó exactamente

- Familias: P80/W5 con racimos4/500/30,8/1000/20,18/2000/20; P90/W5 con4/500/30 y18/2000/20; P80/W10 con4/500/30. Elegidas por frecuencia/contraste de parámetros, no por resultados de mercado.
- D mínimo10/20/40/80 ticks; vuelta25/50/75%; target tocar borde, centro entero floor((low+high)/2), atravesar un tick el borde opuesto. La distancia efectiva del extremo puede exceder D.
- Primera salida versus primera salida D-calificada: se saltan solo excursiones que vuelven dentro antes de llegar aD. Si una excursión llegó aD y volvió sin disparador observable, termina el intento; no se buscan infinitas oportunidades retrospectivamente. Un salto que atraviesa toda la zona no crea una salida gratuita en sentido contrario.
- Espera máxima desde formación2000 barras y horizonte post-disparador2000 barras, fin de sesión y censura gap10s. La espera finita es una nueva restricción explícita respecto del piloto anterior.
- Running peak disponible al instante, primer attainment, low/high congelados al nacimiento, trigger real observado fuera del racimo. Desde ese precio se fija barrera contraria de distancia igual a la restante hasta el endpoint. El resultado empieza en el trade siguiente.
- Nacimientos solo en cierres completos de25 registros; footprint nuevo causal por secuencia, no réplica histórica NT8subseries.

Cero eventos fuera de fechas aprobadas; warmup y máscara previa al detector heredados del piloto pinneado. Fuentes originales inalteradas, sin recorte/upload. Sin certificación de feed ni P&L.

## Frecuencia: rearmar cambia mucho el soporte

En P80/W5/4/500/30, D20/q50/toque: primera salida315 señales frente a6304 con primera salida D-calificada, sobre8764 formaciones. Ambos son conteos antes del adelgazado temporal. Muchas señales comparten ticks/extremos/resultado; el incremento no equivale a20 veces más información independiente.

En la comparación de familias, con una primera señal por bin de6250 registros derivados, D20/q50/toque y modo D-calificado:

| Familia | Resueltos D20/q50 | Toque primero |
|---|---:|---:|
| P80_W10_R4_500_30 | 1711 | 50.9% |
| P80_W5_R18_2000_20 | 547 | 46.1% |
| P80_W5_R4_500_30 | 2609 | 49.4% |
| P80_W5_R8_1000_20 | 1724 | 49.7% |
| P90_W5_R18_2000_20 | 66 | 50.0% |
| P90_W5_R4_500_30 | 1743 | 50.2% |


Son tasas entre resultados resueltos de diez fechas, no probabilidad universal ni rentabilidad. La geometría18/2000/20 no es superior por concentrar volumen: su soporte/rendimiento depende del percentil y window. Controles sin filtro mostraron incrementos pequeños e inciertos en las familias densas.

## Hallazgo focal: recorrido poco visitado

Definición causal del filtro: menos de25% de las últimas256 barras **cerradas** intersectan el corredor entre el precio del disparador y el borde objetivo. Es ocupación de rango de barras construidas desde ticks, no volumen exacto por precio ni liquidez resting del libro.

P80/W5/racimo8/1000/20, mínimo40 ticks, vuelta50%, toque, modo D-calificado:

-476 señales temporalmente adelgazadas,467 resueltas:255 llegan al racimo primero y212 llegan primero a la barrera contraria. Nueve censuradas.
-54.6038543897% entre resueltas; cotas por censura53.5714–55.4622%, no intervalos de confianza.
- En seis fechas iniciales:144/264 =54.5455%; cuatro fechas finales:111/203 =54.6798%. **Ambas partes ya se habían inspeccionado**; esta separación es diagnóstico temporal, no test virgen fuera de muestra.
- Control trasladado con el mismo filtro:250/492 =50.8130%. Diferencia+3.7908 puntos; banda exploratoria bootstrap emparejado por fecha aproximadamente−0.80 a+9.20 puntos. Incluye cero: aporte incremental del racimo no demostrado.

### Sensibilidad a la vuelta: no hay meseta amplia

Mismo D40/filtro/bin/geometría:

| Vuelta | Resueltos real | Toque primero real | Resueltos control | Toque primero control |
|---|---:|---:|---:|---:|
| 25% | 133 | 48.1% | 169 | 43.8% |
| 50% | 467 | 54.6% | 492 | 50.8% |
| 75% | 1020 | 50.8% | 1135 | 50.7% |


D20 yD80 con vuelta50% dieron49.4% y50.5% respectivamente bajo el mismo filtro. La señal54.6% se concentra en D40/q50; no se presenta como regla general para todos los retornos.

### Sensibilidad al muestreo temporal

Mismo D40/q50/filtro:

| Bin de registros | Resueltos | Toque primero | Banda por días |
|---|---:|---:|---|
| 3125 | 550 | 52.9% | 49.9–54.9% |
| 6250 | 467 | 54.6% | 52.0–57.1% |
| 12500 | 338 | 53.3% | 49.6–56.4% |
| 25000 | 219 | 54.3% | 50.7–58.9% |


El signo observado se mantiene, pero varias bandas incluyen50%. Todas las bandas del incremento contra el control trasladado incluyen cero. Los bins no garantizan independencia de excursiones: pueden sobrevivir labels largos solapados. No se elige el bin ganador.

## Indicadores auxiliares y controles

Se midieron tiempos, barras/distancia, ratio de velocidad de vuelta/ida, eficiencia de camino tick a tick, imbalance inferido por bid/ask con cobertura, picos confirmados, dirección reciente64 barras y ocupación/visitas del corredor256 barras. Filtros primarios fijados antes de inspeccionar labels: velocidad>=ida; flujo hacia el target>=0.2 con cobertura>=0.8; eficiencia>=0.3; tendencia64 hacia target; ocupación<0.25; picos confirmados; combinaciones velocidad+flujo y velocidad+flujo+corredor.

En el foco D40/q50, velocidad sola50.2% (999 resueltos), flujo51.8% (388), velocidad+flujo50.0% (300). No hay incremento claro y consistente por añadirlos. No se invierte automáticamente una regla desfavorable ni se afirma irrelevancia universal.

Control:250 barras después de un nacimiento, si sigue en la misma sesión y hay cierre completo, se traslada el mismo ancho y posición relativa del anchor al nuevo precio. El nivel artificial se define con información entonces disponible. **No es null aleatorio incondicional**: sigue condicionado a un nacimiento previo y puede conservar el régimen del racimo. Responde a persistencia/especificidad de tiempo-geometría, no prueba causalidad ni sustituye controles de precio sin racimos.

## Multiplicidad y riesgos mitigados/declarados

Primer bloque864 grupos; luego refinamiento post-descubrimiento con2592 combinaciones de familia/origen/D/q/bin/filtro,2586 con señales y seis sin ellas. Se publican vacías con n0 y tasa no disponible, nunca0% de acierto.1296 contrastes real-control planificados, algunos sin efecto estimable. No ajuste familywise; no seleccionar el máximo como prueba única.

Adelgazado: por sesión/regla se toma el disparador más temprano, empate por nacimiento más temprano, de cada bin fijo de registros. El filtro se aplica **después** de esta selección, sin preferir ganadoras. No se suman frecuencias de distintas configuraciones como muestra única. Resampling de10000 muestras de días enteros; solo10 clusters, por lo que las bandas son exploratorias, no garantías de generalización. Se preservan resultados censurados y cotas, no se eliminan pérdidas ni fechas difíciles.

Corrección de feature antes de publicar: el primer contador de picos incluía el cierre de la barra del trigger aunque estuviera todavía formando. Se sustituyó por el índice exacto de disponibilidad del cierre;270201 filas cambiaron esa feature y ninguna clasificación de mercado cambió. Se recalcularon los filtros. **Fue un problema del cálculo derivado, no del dataset.** Snapshot ejecutado y código corregido conservados separadamente con hashes. El hallazgo de ocupación no depende de ese contador.

La referencia Python recibió además una corrección del estado al terminar una sesión tras salidas pequeñas; evaluador optimizado de mercado sin cambios. No se ocultan fallos de desarrollo ni se añaden ejecuciones como muestras independientes.

## Verificación y reproducción

Cuatro tests,7200 comparaciones sintéticas;72 estratos reales modo/endpoint/D/q cotejados con referencia Python independiente usando intervalos de la fuente original.864 grupos y sus resúmenes diarios recontados desde CSV de señales. Hallazgo255/467 recontado por otra rutina streaming. Agregados sin duplicados; la clave es compuesta por familia/origen/modo/endpoint/D/q, más fecha/filtro/bin donde corresponda. Tasas ausentes por muestra vacía están identificadas.

Publicados código, manifests, evidencia, tablas completas de todas las sensibilidades y resúmenes diarios divididos solo por tamaño de transporte. Ticks, niveles event-level y secuencias privadas no se publican. Dependencias y paths del snapshot son los del PR112 base; no es runner certificado/portable. El manifiesto original pinnea código ejecutado; índice de publicación pinnea versiones actuales y snapshots exactos.

## Qué falta para considerar ventaja

Replicar D40/q50/corredor en otros contratos y fechas pre-reserva, aplicar definición fijada sin elegir retrospectivamente sus mejores vecinos, ampliar controles genuinamente sin racimos y calibrar el efecto incremental con modelos de contexto. Hacer evaluación temporal agrupada y ajustar multiplicidad antes de promoción. El salto de resultados a estrategia requiere costes, ejecución realista y pérdidas, todavía no calculados. No se tocó el holdout ni queda un proceso activo de mercado.

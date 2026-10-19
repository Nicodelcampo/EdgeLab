# Cierre atlas MNQ: cobertura y firmas continuas, no estados A/E ni edge

**COMPLETE**, privadoCPU id138412105/v1, `nicolasbuttaro/edgelab-mnq-target-free-phenomena-atlas`, source5a8d74c2b31526aafb30d6618e7012097116e194. Hash físico del atlas y source/bundle/plan vinculados; tres sesiones exactas y conteos crossfoot: PASS de recibos agregados, no auditoría de toda cinta privada. Source/metadata privados exactos verificados. Intención pre-send y terminal preservados, sin reenvío.

## Resultado descriptivo nuevo

4.262.580ticks,41.906anclas; host29,32s incluyendo retrieval8,53s. No ratio de speedup contra P0/V3: productos y descarga diferentes. Peak del runner es Linux high-water de ese proceso; sampled-child no cgroup. No96detectores/calibración/labels/outcomes/inferencia, datasets sin otra QA, holdout/P&L cerrados.

| Sesión | Anclas | Pares20s medibles | Cobertura | UNKNOWN | Gaps como primer motivo |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2026-06-12 | 12433 | 2946 | 23.70% | 9487 | 9466 |
| 2026-06-15 | 12937 | 6213 | 48.03% | 6724 | 6687 |
| 2026-06-16 | 16536 | 8613 | 52.09% | 7923 | 7878 |

Total W20: 17772pares medibles de41.906anclas(42,41%, pooled ponderado por anclas, no promedio igual por sesión). De24134UNKNOWN, 24031tuvieron gap como primer motivo: 99.57%. Los103restantes son historia incompleta o signo previo cero. La prioridad de causas es current inválido→prior inválido→signo previo0; también se conserva tabla conjunta current|prior. No son todos los gates fallidos simultáneamente.

**Interpretación:** el gate sin gaps>2s en current/prior selecciona tramos continuamente activos. En una cinta de trades, silencio puede ser actividad baja o falta de observación; no identifica por sí solo falla del feed ni cotizaciones que no vemos entre trades. UNKNOWN no es ausencia A/E. No relajar el gate después para mejorar cobertura; cualquier sensibilidad sería una definición explícita distinta y procesada con la misma política de censura.

## Firmas que sí se observaron, con denominador y límites

| Sesión | Mediana ratio presión | Mediana progreso dirigido(ticks) | Ratio presión>=1 y progreso[-2,2) | Ratio presión<0,5 |
| --- | ---: | ---: | ---: | ---: |
| 2026-06-12 | 0.8304 | 0.0 | 21 | 499 |
| 2026-06-15 | 0.8278 | 0.0 | 150 | 1174 |
| 2026-06-16 | 0.8466 | 1.0 | 184 | 1353 |

Sobre17772pares medibles W20, 355(2.00%) combinan presión estimada no menor a la previa y progreso neto en[-2,2)ticks; 3026(17.03%)tienen presión<mitad de la previa. Son anclas solapadas, NO episodios independientes, tasas A/E, impulso previo confirmado ni efectos futuros. Bajo avance neto puede incluir excursión y retorno, no precio quieto: rango/path deben entrar en clasificación y controles. La dirección se elige por flujo previo, por lo que ratios<1 pueden reflejar selección/regresión hacia la media, no agotamiento de una metaorden.

Cuantiles exactos condicionales a pares medibles no se promedian entre sesiones ni se convierten en thresholds. Distribuciones currentOBSERVABLE usan otro denominador, indicado en recibo. Los bins estaban fijados antes del envío; esto no es búsqueda del ganador. Fuente sin profundidad/MBO: proxies de flujo/precio, no mecanismo físico de absorción.

## Qué conviene seguir, con criterio de avance

1. Protocolo científico de clasificación y respuesta: separar actividad continua/baja/UNKNOWN, incluir rango/path para distinguir stall neto de ida y vuelta, controlar regresión al orientar por prior; freeze de A/E/coexistencia/ninguno/UNKNOWN y censura antes de outcomes. No threshold aprendido por éxito.
2. Entrenamiento/calibración causal y evaluación por sesiones cronológicas independientes del ajuste dentro del research autorizado. Estas tres fechas de desarrollo no bastan para transportabilidad/MDE ni equivalencia. Baseline fuerte de componentes continuos; A/E es representación, no información adicional física.
3. Interacciones con AVZP2/racimos/BT2/BT2A sólo después de baseline sin zonas: igualar exposición/edad/ocupación/densidad, tratar AVZ-racimo como dependientes; usar episodios/llegadas causales, no sólo counts. No relanzar V3/otra96configs para este atlas.
4. Optimización útil probada aquí: sólo anclas y prefijos compartidos, sin JSONL privado ni detección/geometría innecesarias, arrays separados por sesión, agregados75.864bytes. No prometer caché temporal superviviente o acelerar automáticamente otros productos.

## Registro de aprendizaje y sistema

Estas observaciones son propuestas de conocimiento scoped para review del Brain, conservadas aquí con hash/denominadores. NO se escribió automáticamente al EdgeBrain canónico: autoridad/destino real siguen sin vincular. Handoff Debian actualizado, no despliegue ni segundo daemon. P0/V3/atlas cerrados; no job de este hilo sigue vivo. Watch común y nueva intención finita de batch no prueban cuota global contra otros controladores.

785ResearchOps y18navegación PASS;34focales. Suite785repetida después de guards finales: PASS. Profiler del JSON anidado no pudo inferir tabla; se perfiló el CSV9filas×9columnas(una sesión/ventana, sin duplicados/nulls). Trade dates son labelsISO; no se infiere tendencia temporal ni se borran filas. Rawaggregate es inmutable. Hash de stream June16 y todos los conteos coinciden con P0; no se recuperaron features privadas para comprobarlo.

## Reproducción portátil de agregados

`python -m tools.research_ops.audits.review_phenomena_atlas --out-dir /tmp/atlas-aggregate-review` usa los recibos limpios publicados, reproduce coverage CSV/evidence/chart spec y verifica hash/plan/conteos. No descarga nada, no instancia journals ni consulta proveedores, no accede a filas privadas y no escribe Brain. NumPy/jsonschema ya forman parte del entorno de investigación. Checks de recibos no prueban autenticidad remota a partir de los JSON solos. Para chart HTML, usar el skill inline-charts/card vigente, no generar HTML ad hoc.

# Confluencias MNQ: continuar con paridad aproximada aceptada

## Decisión del usuario y alcance

Nico indicó avanzar considerando que la paridad no será 100% pero estará muy cerca por el trabajo realizado. Esa estimación queda **aceptada para EXPLORACIÓN**, sin convertirla en un porcentaje medido, PASS nuevo o evidencia de edge. No se requiere otra auditoría exhaustiva NT8 para avanzar. Sí se mantienen identidad de implementación, causalidad, trazabilidad y comparación exacta del código optimizado contra su referencia.

No implica acceso al holdout desde 2026-10-01, otras particiones previamente reservadas, P&L, merge, autopromoción ni aprobación independiente. La preparación continúa sin esperar supervisor 24×7/writer/claves de producción. Los ticks y eventos privados permanecen en Kaggle.

## Implementado ahora (sólo pruebas inventadas)

### 1. Intersecciones as-of

`tools/research_ops/confluence/asof_intersections.py`:
- Snapshots inmutables, identidad de familia/config/build/zona y reloj `(ns, sequence)`; precios enteros en medios ticks.
- Índice de intervalos aumentado por familia (treap determinista). Busca candidatos que se intersectan, no cada par de todas las zonas activas. Balance esperado, no garantía adversarial O(log N).
- Lotes atómicos: aplicar removals/upserts y observar sólo el estado final del lote. No confluencias transitorias por orden de evaluación de indicadores.
- Intersección parcial, contención, contacto de bordes, geometría idéntica y orientación. No multiplicar zonas de la misma familia como «dos indicadores independientes».
- Revisiones ordenadas, reconocimiento no retroactivo, IDs inactivos que no resucitan. No reemitir cada coincidencia en cada tick sin cambio.
- Límites de activos, IDs históricos y pares; desbordamiento rechaza, no trunca. Error durante mutación envenena la instancia: reconstruir desde checkpoint verificado antes de reutilizar.

**Límites:** un scope de contrato/tape/sesión declarado por instancia. Los adapters deben verificar que cada input pertenece a ese scope; el módulo no demuestra la verdad de las declaraciones. El índice por sí solo no tiene loaders ni certifica quotes. La etapa 2 agrega triples, persistencia de episodios, fin de coincidencias y anchors de llegada mediante módulos separados; todavía no es el runner científico completo. La guardia de fecha tampoco certifica el calendario/split completo.

### 2. Racimos causales, sin modificar su regla

`tools/research_ops/confluence/racimo_asof.py`:
- `_racimo` copiado literalmente de aVolZonePOI2 en foundation `f397a318be8b0acf68789070fe8064d83e172f7d`; SHA256 de la función UTF-8 con newline final: `846aab2ee62074f91de17a64bf8b7ade3efbb5a842cf8ba36a9677ede6a33efe`.
- Emitir reconocimiento cuando el racimo se forma, no al nacimiento de su primer miembro; expansiones y cambios de miembros producen snapshots nuevos en el momento observable.
- Preservar orden original de zonas dentro de cada barra y coalescer observación final del lote. No ordenar nacimientos por precio porque cambia desempates del algoritmo.
- Indexar asignaciones de miembros y revisar sólo racimos tocados, sin reescanear todas las zonas/clusters después de cada lote. La regla detectora conserva su búsqueda original; emitir membresía completa sigue costando O(número de miembros).
- Preservar el carry legacy y etiquetar `spans_sessions`; el brazo primario excluye formaciones entre sesiones explícitamente. No rebautizar un detector modificado como equivalente.
- Bounded history: si se alcanza el límite, detenerse; no borrar estado viejo que podría afectar la geometría. El almacenamiento/checkpoint eficiente integral aún falta.

### 3. Piloto reproducible preparado, NO lanzado

`tools/research_ops/confluence/build_target_free_pilot.py` y `MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json`:
- 96 configuraciones completas: 32 AVZP2, 32 BigTrap2, 32 BigTrap2Absorption; referencias y probes densos incluidos.
- Cuatro variantes racimo para el piloto, separadas de la detección AVZ. Selección determinista por parámetros/semillas, sin consultar mercado, densidad observada o outcomes.
- Cobertura de todos los valores marginales del catálogo; **no** cobertura cartesiana de todas sus combinaciones. Densidad de los probes es propuesta, no ya medida.
- Hash por configuración completa y roster; aliases nominales detectados se conservan en metadata y se reemplazan determinísticamente para no duplicar cómputo.
- No reducir warm-up ni habilitar renderer retrospectivo.
- Source manifest, sesiones y presupuesto hardware siguen sin fijar. `launch_ready=false`; no existen nuevos resultados de mercado.

El piloto mide únicamente preparación/detección/racimos/intersecciones/cobertura/costo y escritura, sin etiquetas/outcomes. El roster es preparación, no permisos ni runner Kaggle ya conectado.

## Pruebas observadas y fallos corregidos

**43 pruebas específicas nuevas**, **555 Research Ops totales**, **18 navegación**, catálogo PASS.
- Intersecciones comparadas contra búsqueda exhaustiva independiente sobre 250 lotes sintéticos con altas/bajas/revisiones, más casos de ns compartido, medios ticks, bordes, límites y prefijos.
- Racimos incrementales comparados contra un adapter de recorrido completo, sobre dos sets de parámetros y 180 lotes cada uno. Ambos usan la misma regla legacy fijada: comprueban observación/registro incremental, NO constituyen paridad independiente contra NT8.
- Integración: no aparece confluencia de racimo antes de reconocimiento; invalidación simultánea no produce par transitorio; carry no se declara session-only.

Fallos de desarrollo conservados como aprendizaje:
1. El primer roster tenía aliases nominales repetidos y el test lo rechazó; se añadió deduplicación de cómputo con registro de aliases y reemplazo puro por parámetros.
2. Una primera optimización capturaba el clock antiguo de un miembro mediante closure. El test de tercer nacimiento detectó reconocimiento retrofechado. Se sustituyó por un callback de instancia que usa el clock del lote actual; el test y la referencia completa pasan.

No se abrió mercado ni outcomes durante esos fallos. No se afirma speedup real, paridad NT8 nueva, memoria pico en Kaggle o inferencia calibrada a partir de tests sintéticos.

## Etapa 2: detectores reales conectados, evaluados sólo con tapes inventados

Predecesor persistido: `3ca579ee3386392393de58ffccbfb2582c4e7367`. Esta sección actualiza el siguiente hito; los 43 tests anteriores siguen siendo evidencia histórica de la etapa 1.

### Captura al momento observable

`detector_capture.py` instrumenta ubicaciones AST exactas del `run` fijado por SHA256, sin sustituir reglas detectoras. Captura copias de nacimiento, touch, clasificación OB e invalidación; nunca toma el estado final mutable como feature disponible al nacer.

- BT2 y BT2A usan los módulos portables cuyo hash coincide con la fuente fijada. AVZP2 se conserva completo en `_pinned_avzp2.py`, sin editar su detección.
- `_pinned_total_footprint.py` conserva la construcción TOTAL NT8 de foundation para AVZP2; no sustituirla por el footprint agresor utilizado por BigTrap. Mantiene sus reglas de desempate/asignación y clipping.
- Los outputs nativos con y sin hooks se comparan exactamente en tests inventados de las tres familias. No se presenta esto como certificación NT8 ni como validación del universo MNQ.
- Disponibilidad por membresía real de barras: tick-bar completo en su último miembro; cola parcial recién después de la siguiente observación. Barra temporal después de su cierre, no al último tick dentro de ella. EOF sin evidencia observable queda diagnóstico, no birth retroactivo.
- `ns` compartidos mantienen `sequence`. OB inmediato y OB decidido después tienen sus propios clocks. Logs/fills finales nativos se retienen para regresión pero no otorgan disponibilidad.

### Episodios y llegadas

`episodes.py` mantiene pares y triples AVZP2/BT2/BT2A y RACIMO/BT2/BT2A, con START/UPDATE/END. Una revisión geométrica conserva el origen/ID del episodio; no inventa muestras independientes. Usa adyacencias incrementales, estado final del lote y la intersección común cerrada.

`arrival.py` indexa bandas para encontrar sólo las afectadas por el movimiento observado. Separa primer toque, revisita, salida, gap sin print interior, banda nacida sobre precio y banda revisada sobre precio. Genera ventana causal de desplazamiento, recorrido, eficiencia, tasa, volumen y proxy firmado; ventana incompleta o lado desconocido no se imputa. `window_ticks=256` es un default técnico, todavía no un predicado científico congelado.

`replay.py` une los receipts por heap, preserva el orden interno por detector/barra y procesa atomicamente el reloj de tape. Renueva exposición primaria por sesión, conserva historia legacy de racimos separadamente y termina racimos que incorporan miembros de otra sesión. Sólo revisa observaciones modificadas: se eliminó un barrido configuración × estado activo por tick. Un racimo retirado del brazo primario no resucita al volver a parecer elegible. Hay límite global explícito de IDs conocidos, sin poda silenciosa.

TOUCH/CLASSIFY están capturados pero aún no entran como covariables predictivas del replay. Las pairs AVZP2/RACIMO son descriptivas y dependientes por construcción, no dos votos independientes. Los Frames derivados de mercado serán privados; no subirlos a GitHub ni descargarlos fuera de Kaggle.

### Verificación y límites actuales

**41 tests adicionales de etapa 2; 84 tests de confluencias acumulados; 596 Research Ops y 18 navegación PASS; catálogo PASS_NAVIGATION_ONLY.**

- 130 lotes sintéticos de geometría mutable comparados contra enumeración exhaustiva de todos los pares/triples.
- Pipeline completo con los tres kernels reales sobre tape inventado: genera triples y llegadas, no retrofecha reconocimiento y produce los mismos Frames al invertir el orden de receipts.
- Casos negativos de fuente modificada, parámetros renderer, clocks inexistentes/futuros, reserved dates, capacidad, carry y resurrección.
- Tests detectaron footprint TOTAL ausente en portable y guardia de candidatos aplicada demasiado tarde. Se conservó la implementación TOTAL fijada y se añadió guardia antes de consultar el índice. Ningún fallo implicó acceso a mercado.

**No hay nuevos resultados MNQ, medición de RAM/walltime en Kaggle, speedup real, labels, inferencia, P&L ni lanzamiento.** Las capturas actualmente retienen outputs/logs nativos en memoria; falta streaming/IO columnar y presupuesto conjunto de configuraciones. El builder TOTAL lineariza índices int64: antes de producción hay que verificar rango, overflow y memoria. Los triples densos pueden crecer combinatoriamente; los límites rechazan sin truncar pero no sustituyen el perfil real.

## Etapa 3: piloto técnico finito empaquetado

Predecesor `a05b39c3ef574da30a7f3db764066511106e436c`. Ver `MNQ_CONFLUENCE_KAGGLE_PILOT.md` y su plan: nuevo runner de fixture inventado, caches exactos compartidos, comparación nativa de 96 configs, replay de 32 triadas alineadas y paquete offline privado con límites del proceso. El piloto local completo termina; es evidencia de ingeniería, no resultado MNQ, perfil real o cobertura cartesiana.

Se recuperó sólo metadata de la autorización histórica exploratoria de fuentes; original no disponible y fuente no certificada. No elevarla a certificado ni generalizar su alcance sin binding explícito del experimento nuevo. No reabrir auditoría de paridad 100%.

La prueba aislada del paquete encontró y corrigió una dependencia `sessions.py` faltante; vuelve a pasar. **613 Research Ops + 18 navegación PASS**, incluidos 101 tests específicos acumulados de confluencias (cinco nuevos para receipts).

Se persistió código antes de enviar el probe. Kaggle creó `nicolasbuttaro/edgelab-confluence-synthetic-engineering-pilot`, kernel 138379047/v1; metadata confirma privado, CPU, Internet apagado y source idéntica al request. La API eligió el slug a partir del título, no el solicitado. **Estado terminal observado: COMPLETE**, con boot/pilot receipts descargados por su ruta real y SHA256 de bytes, bundle, source/roster y cobertura comprobados. Las salidas detectoras de las 96 configs y los hashes/conteos de las 32 triadas coinciden exactamente entre local y Kaggle sobre el mismo fixture. Ver `MNQ_CONFLUENCE_SYNTHETIC_KAGGLE_OUTPUT_VERIFICATION.json`. No es paridad NT8 de mercado ni lanzamiento científico. No relanzar el probe por retomar este checkpoint. Estado y receipts están separados del éxito local.

## Próximo paso operativo (no otra auditoría de paridad)

1. Reutilizar fuentes y sesiones exploratorias aprobadas, sin reabrir auditorías de datasets. Configurar targets/formation y reservas del nuevo experimento antes de cargar ticks; mantener holdout cerrado y KAGGLE_ONLY.
2. Empaquetar runner privado Kaggle acotado con caches compartidos, captura/IO por lotes, mounts/builds verificados y límites de memoria/costo. Guardar sólo agregados sanitizados; ticks/eventos nunca salen de Kaggle.
3. Perfilar el piloto preparado de 96 configs sin outcomes: detectar densidad/ocupación, soporte y costos por etapa, y comprobar equivalencia exacta referencia/optimización sobre entradas idénticas. No recortar parámetros por winners.
4. Con esas mediciones congelar roster amplio, escenarios, covariables de llegada/volumen, labels, ablaciones aditivas/interacciones, controles de densidad/geometría, estabilidad temporal/contrato, carry separado y multiplicidad/dependencia/MDE. Los temas científicos están diseñados, no resueltos por este pipeline.

**No queda un bloqueo de paridad 100%.** Lo pendiente es ejecutar el nuevo experimento con inputs/costos trazables, no terminar autonomía 24×7 o repetir matrices/focales cerradas.

## Reproducir sin datos reales

```sh
python -m unittest discover -s tests/research_ops -p 'test_confluence*.py' -v
python -m unittest discover -s tests/research_ops -v
python -m unittest discover -s tests/navigation -v
python tools/edgelab_catalog.py check --json
python tools/research_ops/confluence/build_target_free_pilot.py \
  --design docs/research/ops/MNQ_DENSE_CONFLUENCE_DESIGN.json \
  --out /ruta/nueva/pilot-roster.json
```

El output debe ser nuevo: no sobrescribir evidencia anterior. Los módulos de estas pruebas no consultan red ni datos privados.


## Etapa 5: cierre de fuente y avance del motor por bloques

Instrucción actual del usuario: los datasets ya están resueltos; no hacer constantes validaciones. Se conserva la autorización exploratoria existente y sus riesgos, sin exigir nueva certificación de fuente ni repetir corridas históricas. El trabajo siguiente debe producir resultados nuevos.

El preflight anterior terminó en Kaggle (kernel 138381058/v1): bytes/schema de MNQ_09-26 fijados, 110632331 filas y 295 row groups; no se deserializaron precios ni se ejecutaron detectores. Receipts agregados y verificación de salidas guardados. No volver a lanzarlo. Los flags false de certificación científica se preservan; no constituyen un nuevo bloqueo solicitado al usuario.

`avz_stream.py` conserva el loop AVZP2 fijado como generador por barras: mantiene historia/calibración, bloques parciales y zonas pendientes de OB entre entregas, descartando outputs nativos finalizados. Las 32 configuraciones AVZ del roster conservan eventos/scores y blocks exactamente contra referencia sobre fixture inventado. Mantiene parámetros completos y warmup; racimo_min=0 como el roster, racimos por adaptador separado. No hay todavía lector/constructor de barras raw por chunks ni certificado de velocidad real.

Se encontró y corrigió una disponibilidad causal en el adaptador BT2A: el cierre residual por cambio de sesión puede retirar una zona, pero esa baja sólo es observable con el primer tick de la nueva sesión, no en el último tick del bloque anterior. Al EOF desconocido no emite baja observable. Consumo y disponibilidad se registran por separado. Los outputs del kernel nativo permanecen idénticos; dos pruebas negativas nuevas cubren ambos casos. No se editó el indicador ni se reabrió paridad NT8. Las receipts históricas del piloto sintético permanecen sin cambios; no certifican el adaptador nuevo.

Siguiente trabajo: completar procesamiento estatal BT2A y primitives de barras/footprints, conectar runner Kaggle al scope existente y medir costos/densidad/ocupación en MNQ. Luego fijar escenarios/labels y análisis con controles de ocupación, dependencia y multiplicidad. No lanzar aún la enorme campaña cartesiana con un runner que reinicie historia por cada chunk.

Regresión de esta etapa: **641 Research Ops + 18 navegación PASS**, catálogo PASS_NAVIGATION_ONLY. Doce pruebas nuevas de AVZ streaming, cuatro de cierre metadata y dos del cierre residual BT2A; todas sin cargar datos de mercado en el sandbox.

## Etapa 6: las tres familias conservan estado

Predecesor `dc65d490b04ca9ce28d93a1565ae8f6e61615b58`. `bt2_stream.py` y `bt2a_stream.py` completan las dos variantes BigTrap estatales junto con AVZ. Historial y activos sobreviven a las entregas sin acortar el warmup. Se comparte el árbol instrumentado hash-bound con captura de referencia; no se alteraron kernels fijados.

Camino default sin serialización diagnóstica CSV, con capturas idénticas en pruebas específicas. Modo diagnóstico compara eventos/scores contra native en las 32 configs de cada variante. Integración de las tres familias conserva racimos/triples/llegadas e identidades al variar chunks. Evidencia sólo sintética, no paridad NT8 100% ni medición MNQ. Ver `MNQ_CONFLUENCE_STREAMING_ENGINE.md` para límites y pendientes concretos.

No reabrir fuente ni corridas históricas. El siguiente módulo es barras/footprints por lotes con continuidad exacta, seguido del lector/runner Kaggle y perfil real. Fuente aprobada reutilizada, holdout cerrado, no nuevos resultados de mercado en esta etapa. No volver a lanzar probes de metadata.

Regresión de esta etapa: **666 Research Ops + 18 navegación PASS**, catálogo PASS_NAVIGATION_ONLY. 25 tests nuevos (9 BT2, 14 BT2A, 2 integración) sin datos de mercado en el sandbox ni nuevas auditorías de datasets.

## Etapa 7: runner real acotado, listo para persistir y lanzar

Predecesor `da6b54215371545b81511c2d0bb37b38495c0251`. Primitivas compartidas por sesión/bar spec, continuidad exacta TOTAL de cohortes/carry, clasificación agresora global, reader por batches, almacenamiento privado y geometry replay incremental completados. El runner de 96 configs reproduce hashes de captura de referencia sobre el fixture inventado, y evalúa 32 triadas sin inventar ticks/arrivals ni correr un cubo config×tick.

Plan fijado `MNQ_CONFLUENCE_MARKET_PILOT_PLAN.json`: primera sesión MNQ_09-26 del scope exploratorio aprobado (2026-06-16), warmup observado dentro de ventana histórica desde 2026-05-02. Es censo técnico target-free de densidad y geometría; no es el cartesiano amplio, análisis de outcomes, P&L o validación de edge. Fuente resuelta, sin nueva QA, holdout cerrado. `MNQ_CONFLUENCE_MARKET_PILOT.md` documenta sesgos, límites, cobertura y siguiente análisis.

Regresión previa al lanzamiento: **682 Research Ops + 18 navegación PASS**, catálogo PASS_NAVIGATION_ONLY. 16 pruebas nuevas de primitivas/reader/geometría/runner/paquete, sin cargar mercado en el sandbox.

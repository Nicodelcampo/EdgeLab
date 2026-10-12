# MNQ: aVolZonePOI2/racimos × BigTrap2/BigTrap2Absorption

**Estado: DESIGN_ONLY_NOT_PREREGISTERED. No se lanzó ninguna corrida.**
Propuesta científica nueva, no evidencia de edge, autorización de datos o aprobación independiente.
La corrección de Nico es vinculante: el indicador principal es **aVolZonePOI2**, no aVolClusterPOI ni AVolZoneSimple.
Los originales congelados, sus matrices/focales y el holdout permanecen intactos.

## Actualización de Nico: continuar con paridad aproximada

Nico aceptó avanzar sin exigir paridad 100%, estimando que está muy cerca por el trabajo previo. Se registra como **riesgo aceptado para EXPLORACIÓN**, no porcentaje medido o certificación nueva. Las demandas anteriores de cerrar exhaustivamente la paridad NT8/racimos dejan de bloquear este proyecto. Siguen la identidad de build y las salvedades conocidas; la equivalencia del código optimizado con su referencia sigue siendo un requisito contra bugs, no otra auditoría de NT8. No modifica holdout/P&L ni habilita autopromoción.

Estado de implementación y piloto actualizado en `MNQ_CONFLUENCE_IMPLEMENTATION_CHECKPOINT.md`; el diseño original de hipótesis todavía no es un preregistro de outcomes aprobado.

## 1. Decisión científica

Sí conviene explorar esta idea, pero como **nuevo observable: confluencia entre familias y estado de llegada**, no como rescate del supuesto de que una zona aislada es soporte/resistencia o un imán.
Configuraciones menos estrictas amplían el universo de oportunidades raras. No crean por sí mismas observaciones independientes ni información: también aumentan la ocupación de precio-tiempo y las coincidencias fortuitas.
No optimizar por número bruto de zonas ni elegir después las configuraciones con mejores outcomes.

La campaña debe responder, incluso sin ganadores:

1. ¿Una confluencia agrega información fuera de muestra de desarrollo respecto de contexto, efectos individuales y estado de llegada?
2. ¿El aparente aporte desaparece al igualar densidad, geometría, edad, actividad, distancia y ocupación?
3. ¿Revisitas, fracción de volumen interior, flujo y eficiencia aportan por separado, conjuntamente o sólo en ciertos regímenes?
4. ¿El aporte se repite entre contratos naturales/épocas, o cambia de signo? MNQ/NQ no son réplicas independientes por tener distinto símbolo.
5. ¿Importa la forma del solapamiento, su secuencia de formación y la familia geométrica, no sólo el detector primario?
6. ¿El carry tiene un comportamiento distinto? Brazo separado; no heredar cruces de sesión accidentalmente.

Los diagnósticos incrementales combinados de la campaña anterior ya existen; no se describe su ausencia. Lo nuevo es aislar bloques e interacciones con población común, controles explícitos e inferencia global adecuada. No hace falta repetir las cinco matrices y cinco focales para cerrar el cómputo anterior.

## 2. Paridad encontrada: qué cubre y qué no

Fuentes de foundation fijadas en `f397a318be8b0acf68789070fe8064d83e172f7d`; kernels portables revisados en `722edd0ab5b47a1b5bf5eb1177f8092c54ec38e0`.

| Objeto | Evidencia encontrada | Decisión para esta campaña |
|---|---|---|
| BigTrap2Absorption v1.1.1 | Firma final Puerta 0 GC DEC26: 365/365 zonas/fills AbsMagnitude y 626/626 AbsDirectional, sin diferencias en alcance post-burn-in. | Paridad histórica **sí validada**. No acredita MNQ/todos los valores de la grilla. Vincular hash y declarar ramas realmente usadas; no exigir cierre perfecto para explorar. |
| BigTrap2 | PASS histórico time:1 v2.1: Diagonal, wick off y SameLevel. Contrato permite tolerancia temporal de 60 s, geometría exacta. | No decir «nunca validado». Tampoco extender ese PASS a tick:25/MNQ/kernel actual. |
| BigTrap2 tick:25 v2.5.2 GC | La nota corregida de agosto registra mejora del oráculo y 81,15% de TRAPs exactos con anclaje; atribuye residuales a diferencias de cinta/frontera. | No es un PASS exacto completo para el sweep propuesto. El texto antiguo que decía «paridad imposible en general» fue retractado. |
| aVolZonePOI2 MNQ12-26 25t | Bloques, zonas, clasificación OB y pertenencia/reconocimiento de racimos comparados exactamente en la configuración publicada. | Base de referencia adecuada para control positivo de implementación; no certificado de todas las resoluciones/umbrales. |
| aVolZonePOI2 MNQ12-26 200t | PASS publicado en su configuración y serie NT8 back-adjusted. | Referencia de paridad; el research nuevo usa contratos naturales, no traslada precios ajustados al raw. |
| Racimos: líneas low/high/start | El export NT8 de la comparación 25t no traía las filas C compiladas; pertenencia sí comparada, geometría final no. | No etiquetar como geometría certificada. Para esta exploración se acepta la salvedad y se declara que la geometría Python no tiene certificación NT8 completa. No presentarla luego como exacta. |

**Hashes Python:** Absorption certificado `0d162a6092c31228ec0f4f9539b4afc0cb5031737263db4369dea2ad03697ab2`; portable actual `0a0f312de5e1b4350a2a102cc051f2d6fd9484696c2a4762dc6f3006c1c54757`. BigTrap2 portable actual `59cc63904cf9c1a58d97f7fb4e847dd23c0105e4a6516e9681785da30f053c72`.
Absorption tiene una corrección posterior de MinExportVolume no-default: el PASS original no habría detectado ese caso. No exigir reauditar todo; sí probar las ramas nuevas usadas antes de medir.

**Límite de recuperación:** `HP007_CAMP002_BT2A_PARITY_AUDIT_2026-09-15.md` no pudo cargarse: GitHub MCP rechazó su target de symlink. Su contenido no se verificó. El inventario conserva este faltante; no se convierte en «no existe» ni en un PASS supuesto.

Fuentes primarias revisadas:
- `docs/parity_coverage/BigTrap2.md`, `BigTrap2Absorption.md`.
- `docs/P0.1_BIGTRAP2_DRIFT_ADJUDICACION_2026-08-11.md`.
- `docs/research/BIGTRAP2_PARIDAD_IMPOSIBLE_2026-08-21.md` (leer la corrección inicial y §7, no sólo el título).
- `docs/research/FIRMA_FINAL_PUERTA0_BT2_ABSORPTION_2026-08-23.md`.
- `docs/parity/PARIDAD_AVOLZONEPOI2_MNQ1226_25T_20261008.md`, `...200T_20261007.md`.
- `docs/nt8_indicator_parity_contract.md` como contrato histórico; no transportar su viejo firewall al holdout actual.

## 3. Catálogo amplio sin producto cartesiano inútil

El JSON adjunto fija un **catálogo candidato**, no una grilla aprobada o ejecutada:

| Familia | Definiciones nominales candidatas | Ejes propuestos |
|---|---:|---|
| aVolZonePOI2 | 1.728 | 25/50/100/200 ticks; bloque 5/10/20; mediana ×1,25/1,5/2; gap 0/1/2; mínimo 2/3 niveles; Suma/Densidad; percentil 70/80/90/95. |
| Racimo | 48 por detector AVZ | mínimo 3/4/6/8 zonas; ventana 250/500/1000 barras; altura 20/30/45/60 ticks. |
| BigTrap2 | 2.880 | time:1 y 25/50/100/200t; filas 1/2/4; Diagonal/SameLevel; volumen AggressiveSide/TotalLevel; ratio 1,5/2/3/4; wick off/30/50%; volumen mínimo 1/5/15/30. |
| BigTrap2Absorption | 17.280 | cubeta 10/25/50/100; ambos scores; pct 50/70/80/90/95; filas 1/2; ambos imbalances; ratio 1,5/2/3; stacked 1/2/3; frac 0/0,1/0,2; flow-match on/off; wick off/30%. |

Son **21.888 configuraciones detectoras nominales** y **82.944 combinaciones AVZ-racimo**, antes de agregar referencias exactas y aliases. No son pruebas independientes ni costos medidos. No generar todos los cruces AVZ×BT2×BT2A×escenario×outcome como pipelines separados.

Mantener calibración AVZ 20 sesiones/20 muestras; Absorption lookback 500/minhistory 200. No reducir warm-up para fabricar zonas. OB fija referencia 100 barras/6 alturas/8 ticks/4%. Ciclo de vida BT fijo CloseThrough/2000/0; minexport=1 y sin filtros renderer retrospectivos. Añadir defaults exactos y las configuraciones de paridad como referencias separadas. Para wick off, el porcentaje inerte se normaliza a 30 sin multiplicar aliases.

Estas configuraciones no garantizan más zonas monotónicamente: cambiar filas/gap/mínimos puede fusionar o sustituir geometrías y cambiar scores históricos. Una zona amplia no equivale a varias estrechas.

### Selección target-free y cobertura del espacio

1. Pilotear una muestra determinista pequeña y estratificada por ramas, antes de outcomes, para estimar costo y cobertura.
2. Congelar densidad baja/media/alta y una referencia estricta por familia/resolución usando sólo conteos, geometría, ocupación, redundancia y soporte. Umbrales, cuota y regla de selección se fijan antes del censo amplio; están pendientes.
3. Asignar presupuesto amplio a diversidad de eventos/escenarios, no al detector que cubre todo el gráfico. Preservar una cuota de exploración de configuraciones raras no redundantes.
4. Guardar nominales, equivalencias exactas y motivos de descarte. Jaccard descriptivo no estima número efectivo de tests. Si se recorta la grilla por presupuesto, declarar cuáles no se evaluaron.
5. Congelar el roster científico efectivo antes de leer etiquetas. Cambiarlo luego crea otro experimento/trial; no completar silenciosamente el primero.

El límite de pocos parámetros libres por hipótesis del funnel no obliga a sólo tres configuraciones: separar **atlas de medición amplio** de pocas preguntas/contrastes preregistrados. El espacio amplio también cuenta en multiplicidad si sus resultados informan selección.

## 4. Escenarios y población causal

24 familias candidatas en el JSON: solapamiento AVZ/BT2, AVZ/BT2A, racimo/BT2, racimo/BT2A; triples; contención; contacto de bordes; cercanía sin solapar; orden de nacimientos; timestamps iguales con orden distinto; orientación concordante/enfrentada; coincidencia antes/después del toque; llegada rápida/directa o lenta/oscilante; revisita; salida/retest; expansión; edad; carry; pérdida por invalidación.
Cada familia necesita predicados/cutpoints/discretización exactos antes de ejecución. No tomar ejemplos visuales favorables después para definir la regla.

Enumerar todos los nacimientos/anchors elegibles, sin condicionar el censo a toque, salida, rebote o éxito futuro. Separar nacimiento, aproximación, primera interacción, revisita, salida y retest como estimandos/poblaciones distintos; explicitar cómo se selecciona cada anchor, qué eventos no llegan a él y cómo se evita contar repetidamente el mismo episodio.

**Contrato as-of mínimo:**
- Identidad completa: contrato natural, input/build/config, partición de barra/cubeta, zona, `(timestamp_ns, sequence)` disponible. Timestamp+side no es una clave.
- Geometría en ticks/medios ticks. Conservar aritmética original de thresholds fraccionarios de wick; no redondear para acelerar.
- Confluencia disponible al máximo de disponibilidades de todos sus componentes. Nada se retrofecha a la zona más antigua.
- Racimo existe desde su reconocimiento `bar`, no desde `start0`. Usar `low0/high0` al formarse y snapshots versionados en cada expansión/join. Nunca la banda final sobre todo su pasado.
- OB=2 sólo desde `decided_bar`; estado final OB no es feature de nacimiento.
- Lifecycle actualizado antes de crear según cada kernel; una barra creadora no toca retrospectivamente su propia zona. Registrar cierre/invalidación por gaps y orden de eventos de borde.
- Una confluencia nacida estando el precio dentro no se llama «llegada desde afuera». Clasificar AT_CREATION; un futuro retest es otro evento.
- La aproximación se corta en el índice de señal inclusive, sin ticks posteriores con el mismo ns. Ventanas completas dentro de sesión por defecto.
- Estado ausente/calibración insuficiente/censo incompleto = UNKNOWN, nunca no-zona/no-racimo.
- Los detectores conservan su historia causal real. Absorption conserva ring entre sesiones y excluye residuales de historia; AVZ conserva sesiones previas por franja. No arrancar cada shard con estado vacío.
- No usar fills EOF como prueba de una observación posterior; distinguir zona nacida de zona con next-tick observado. Este estudio no calcula ejecución/P&L.
- El legacy permite estados activos/racimos entre sesiones. El brazo primario filtra exposición actual con política explícita, sin alterar ocultamente el detector; formación con miembros de sesiones anteriores se identifica aparte. Un racimo session-only redefinido tiene otra identidad, no es un parche equivalente.

## 5. Comparaciones que separan mecanismo de geometría

Sobre los **mismos anchors elegibles**:

- M0: contexto causal (contrato, reloj, volatilidad, distancia/edad, actividad/ocupación).
- M1: M0 + efectos principales de AVZ, racimo, BT2 y BT2A.
- M2: M1 + revisitas, volumen interior, flujo y eficiencia/llegada como efectos principales.
- M3: M2 + confluencia geométrica/orden temporal e interacciones preregistradas.

Comparación principal propuesta: **reducción emparejada de Brier OOS de desarrollo M3 vs M2**. M2 vs M1 distingue llegada de confluencia; M1 vs M0 muestra aporte individual. Ablaciones por bloque y por indicador, log-loss/calibración secundarios. No contar mejora de M3 vs M0 como «sinergia».
Fijar complejidad, regularización y pocas variantes antes de etiquetas; mismos splits, train-only bins/scaling/imputación, masks comunes y reporte de soporte perdido. No elegir el mejor ridge/grid por todo el periodo.

La respuesta primaria es **pendiente de preregistro**: etiqueta de primera-pasada tick-ordenada con distancias/horizonte fijos y regla de censura. No hay tuning abierto de SL/TP, retorno o rentabilidad. Censurados/no-exit tienen categoría/conteo explícitos, no pérdidas ni éxitos imputados. Una métrica sobre completos tiene población condicional explícita y análisis de sensibilidad; no afirmar efecto causal.

Controles distintos, no intercambiables:
1. **Densidad/ocupación:** comparar strict vs loose, y controles con ancho, edad, distancia, cobertura de precio-tiempo, reloj, volatilidad/actividad iguales. Mantener y reportar soporte común; no seleccionar sólo reals fáciles de aparear.
2. **Geometría zone-free:** pseudo bandas con la misma geometría/exposición y detector negativo observado as-of; UNKNOWN no entra como ausencia demostrada.
3. **Aditividad/interacción:** modelos/ablaciones anteriores; BTC y BTCA comparten primitives, no son dos votos independientes.
4. **Nulos espaciales:** desplazamientos de bandas existentes as-of bajo regla congelada, preservando densidad y perfil de anchuras en la medida declarada. Prueba de coincidencia espacial, no control temporal automáticamente aprobado.
5. **Controles temporales:** preferir otro bloque/sesión elegible, reloj/régimen apareado y features reconstruidas en su propio anchor. Si misma sesión: respetar CTRL_TIMING_V1 (`t_control >= t_event + Hmax`). No sortear controles sobre la aproximación previa ni importar el camino del real.
6. **Censo propio del control:** evaluar su selección/estado y baseline en su propio universo, no sólo el subconjunto apareado. Reuso de controles añade dependencia; reportar distribución de pesos y concentración.

El matcher AVZ portable actual estratifica por **misma sesión** y admite separación absoluta. NO implementa por sí solo el punto 5 ni ausencia de zona/racimo o inferencia. Hace falta un adaptador nuevo probado; no renombrar su salida como control aprobado. Nulos espaciales contemporáneos no pasan fingidamente la guardia temporal: especificar su estimando/diseño propio y someterlo a revisión.

## 6. Rigor y memoria: qué herramientas usar realmente

Se revisaron el catálogo portable, contratos y APIs relevantes, kernels completos de ambos BigTrap y AVZP2, scripts legacy seleccionados y memoria canónica. `MNQ_DENSE_CONFLUENCE_TOOL_REVIEW.json` distingue **lectura completa** de **lectura de contratos/API**. Es una revisión acotada, no afirmación de leer cada script de cada rama ni certificación global del sistema.

| Herramienta/familia | Uso en el diseño | Límite importante |
|---|---|---|
| data gate, lectores protegidos, manifests/resolver | fijar sesiones/input/availability/liquidez/calendario y exigir elegibilidad antes de filas | metadata PASS no autentica aprobación; código legacy no se protege sólo por importar el gate |
| bridge bars/ticks/footprints + parity | compartir primitives con identidad exacta de barra y orden | un mismo número de ticks no hace idéntico el classifier/footprint de todos los indicadores |
| AVZ detector tape, negative windows | creaciones inmutables, calibración y UNKNOWN | replay portable está fijado a parámetros legacy exactos; extenderlo es otro build y requiere tests |
| AVZ match/diagnostics/reaction prototypes | contrato de pesos, soporte, prewindows y llegada causal | descriptivos/sintéticos; no loaders autorizados ni inferencia real completa |
| validation verify / harness | sintéticos, espejado, prefix, timestamps y ledger independiente | harness estratégico abre P&L: no ejecutarlo para esta campaña no económica; prefix no basta para toda causalidad |
| MCPT/SPA/PBO/DSR | referencia metodológica para multiplicidad/falsación | contratos originales de estrategias/retornos no se aplican tal cual a target-first o Brier con eventos superpuestos |
| funnel splits/isolation/batched screen | particiones congeladas, horizonte íntegro, batching y budgets | screen CPU/GPU calcula outcomes económicos y no se usa aquí; GPU bajo nivel no acredita runner integral |
| EdgeBrain control_guard / coverage | prevenir controles sobre llegada y ausencia=0 | no reemplazan controles de geometría/exposición ni autoridad de datos |
| hippocampus/anchors/retrieval/context/invalidation/lineage/typed registry | recall previo, negatives, aliases/dependencias, trazabilidad propuesta | hash-chain prueba integridad, no verdad; no nuevo writer canónico ni autopromoción |
| model_policy/triangulation | revisión independiente y réplica por ejes genuinos | este agente no se firma a sí mismo; otra etiqueta/router no es otro backend |
| research ops / resampling / bounded checkpoints | reutilización exacta y decisiones técnicas separadas de ciencia | mejora de subpaso no promete speedup de job; supervisor/auth/writer pendiente no bloquean manual autorizado |
| measurement/composition atlas + bibliographic cortex | declarar observable, composición, ablaciones y fuente de ideas | seed DRAFT/PROPOSED no evidencia; integración bibliográfica/atlas no está completa en portable main |

Recall ejecutado con `LedgerIndex.from_ledger`: research_history 21 registros, replay y ambas anclas verificados, bytes sin modificar. IPC también replay verificado; no ancla externa afirmada. Adjuntar IDs y pins, no copiar una memoria paralela ni escribir el ledger canónico.

Lecciones aplicadas:
- `CX-RH-BIGTRAP2-SR`, `CX-RH-BIGTRAP2-MAGNET`: no repetir/rescatar la hipótesis de zona aislada; mismo control geométrico.
- `CX-RH-YM-BT2A`: no rehacer thresholds para rehabilitar una línea saturada. MNQ es otra población y la confluencia otro observable; declarar ambos, sin trasladar el null de YM como prueba en MNQ.
- `LESSON-RH-TOUCH-ONLY-POPULATION`: enumerar espacio de eventos, no sólo toques exitosos.
- `LES-CONTROLS-ASOF-20260928`: controles sólo con niveles disponibles entonces.
- `LES-DETECTOR-FIT-DURATION-20260928`: optimizar cobertura puede premiar zonas larguísimas; congelar exposición/edad y medir saturación.
- `LES-CONTROL-EVENT-SELECTION-20260928`: censo propio del control; supersede la interpretación anterior de pivote barrido.
- `LES-BOOT-MIN-N-20260928`: pequeños bloques no tienen soporte inferencial. El número de filas no reemplaza número de sesiones/bloques; no adoptar un mínimo universal por repetir la lección.

Las lecciones siguen **PROPOSED/LOW**; son advertencias de diseño con alcance, no aprobación automática.

## 7. Optimización propuesta: compartir trabajo, no cambiar resultados

### DAG factorado

1. Una lectura por fuente/sesión aprobada, columnas necesarias; identidad/raw hashes antes de deserializar. Conservar bid/ask/secuencia para BT; la optimización AVZ de «3 columnas» no alcanza para ellos.
2. Construir barras/footprints una vez por especificación realmente equivalente, classifier y política de cortes. Cache por key completa, no por nombre del indicador.
3. AVZ: perfiles por bloque, hot-level groups y score/history por ejes que los modifican; compartir percentiles cuando **la historia sea idéntica**. Detección no depende de parámetros racimo/OB; replay racimo sobre creaciones ya detectadas es reutilización legítima. No materializar todos los clusters mutables de todas las configs a la vez.
4. Absorption: partición de cubetas por TapeWindow, classifier reseteado dentro de cada cubeta según fuente, flow/dPx/scores; history separada por ScoreMode/lookback; umbral excluye bucket actual. Reusar después de demostrar identidad; no usar footprint compartido que propague un tick-rule distinto.
5. BT2: primitives de filas/delta/ratios/mecha, selección/volumen y lifecycle. La misma señal puede pasar muchos umbrales de volumen sin rehacer footprint, si minexport cubre todo; replay ciclo de vida por política. Cambiar filas/ratio/wick puede cambiar geometría y debe recalcularse.
6. As-of interval join por tiempo-precio, con sweep temporal e índice de intervalos activos: evitar comparación todos-con-todos. Costo objetivo dependiente de intersecciones K; si K explota, particionar/spill, no descartar pares sin declararlo.
7. Intersecciones equivalentes/aliases y features causales precalculadas; outcome una vez por key completa (anchor/secuencia, banda, orientación, session stop, horizonte, distancias, gaps/endpoint/availability).
8. Reducciones por sesión/bloque y remuestreos compartidos cuando preservan draws/método exactos. El helper entero de counts no se aplica directamente a pérdidas flotantes Brier.

### Lo que no es una optimización válida

- Tomar «todo lo que detecta la config más laxa» como superset de todas: en BT2A elegir el best run cambia con stacked/minimos; en AVZ hot grouping y best-score histórico cambian con configuración. Primero demostrar la propiedad por cada eje.
- Retroproyectar zonas/racimos finales; colapsar timestamps; cambiar warmup/reset/history; redondear thresholds; usar fastmath.
- Cambiar labels/censuras para vectorizar; eliminar aliases del registro de trials; resumir por la única config ganadora.
- Desactivar fsync, compartir escritura SQLite entre workers o llamar peak-RSS a memoria cgroup.

### Ejecución y recuperación

CPU/Numba determinista por defecto; fastmath off. Shards por contrato/época/familia de primitives, con warmup y snapshots de historia suficientes; no sesiones independientes con historia vacía. Un nivel de paralelismo y límites de threads BLAS; cada worker output independiente, reducción ordenada y un escritor.
Intermedios columnar/Parquet ZSTD y mmap sólo dentro de Kaggle; bounded buffers, spill, presupuesto total incluyendo hijos/compilación/cache. Checkpoint atómico por shard y receipt de input/build/spec/config/output completos; resume sólo con identidad exacta. No pickle no confiable ni fallbacks de fuente.
Publicar únicamente agregados y recibos sanitizados; ni ticks, eventos privados, sqlite/gzip privados ni URLs firmadas. Mounts se verifican en preflight, no se asumen por metadata MCP. Kaggle sin Internet durante el estudio; bootstrap separado si necesario. No habilitar workers externos para eludir KAGGLE_ONLY.
GPU sólo si el perfil demuestra un kernel apropiado y se compara la ruta completa exacta. No comprar complejidad GPU antes de eliminar recomputaciones/joins cuadráticos.

### Dos herramientas legacy NO lanzar tal cual

- `tools/bt2_absorption_param_sweep.py`: tiene IDs de configs, grilla balanceada y parciales reanudables útiles, pero aún emite `bt2a_event_pit_v1`, usa `t_start` y `searchsorted(... right)` por timestamp; el contrato PIT v2 declaró esa ruta inválida. Además procesa sesiones selladas para historia. No reutilizar ese lector/split como autorización de este proyecto.
- `tools/sweep_bigtrap2_tickframes.py`: es barrido económico legacy, con controles aleatorios y mapping `(bar_idx+1)*tf-1`. No respeta por esa fórmula todas las colas/cortes y el esquema de zonas portable difiere de campos que intenta leer. No usar como runner de confluencias.
- `tools/build_avzp2_kernels.py`: incrusta fuente pero su k3 histórico se llama confirmación y no implementa el firewall/admisión actual. Reusar empaquetado con nuevos pins/manifest; no ejecutar el builder original.
- `tools/avzp2_racimo_grid_stage1.py`: factoriza detección/racimo correctamente como idea; sus controles/población/ventanas son históricos, no este protocolo.

## 8. Etapas, límites y qué falta para lanzar

**D0a — ingeniería sintética, sin mercado:** implementador de snapshots/joins/IDs; oracle lento y rápido; casos adversariales: mismo ns distinto sequence, medio tick, borders, creación/invalidation simultáneas, sesión/tail/DST, racimo reconocido tarde/expandido, OB tardío, calibration pending, detector negativo UNKNOWN, missing quotes, reanudación con hash distinto y masks equivalentes. No confundir synthetic PASS con paridad NT8/MNQ.

**D0b — piloto target-free autorizado:** sesiones previamente elegibles y completas que permitan historia; subset/configs representativas congeladas antes de correr. Medir lectura, barras/footprints, detector/history, racimo, joins, features, escritura; mediana/rango, bytes, peak process-tree RSS y cgroup como métricas distintas; cold/warm/reversed-order. Comparar output ordenado completo con referencia, no sólo conteo. Cero labels/P&L. No exigir cierre perfecto NT8: mantener sus salvedades aceptadas y resolver sólo defectos concretos de causalidad/implementación del nuevo estudio.

**D1 — exploración amplia autorizada:** fijar roster, fuentes/sesiones, definición exacta de anchors/scenarios/cutpoints/response, MDE/support, modelo, bloques y embargo, familia/multiplicidad, presupuesto y regla STOP. Cortar por presupuesto implica cobertura incompleta explícita; no declarar matriz completa por tener algún resultado. Guardar todos los outcomes agregados/negativos y árbol completo de trials. No auto-lanzar la siguiente etapa.

**D2 — replicación futura:** shortlist por hipótesis estable, config y protocolo bloqueados. Fecha <2026-10-01 no implica «virgen»: los cinco contratos ya se inspeccionaron, y otras particiones reservadas antiguas siguen cerradas. Sin autorización no acceder a holdout ni fabricar una validación nueva dividiendo datos conocidos.

**Inferencia:** pérdida emparejada por anchor y agregación/dependencia por sesiones/bloques, con sensibilidad a bloques multisesión y clusters de eventos/controles compartidos. Purga/embargo por ventanas/outcomes y reglas de formación según protocolo. Folds temporales de desarrollo, no train/test aleatorio por fila. Hierarquía de familias y maxT/stepdown u otro control global justificado: implementación/distribución nula y prueba de tamaño/poder pendientes, no una etiqueta ya aplicada. Subgrupos de soporte bajo quedan descriptivos. Intervalos punto a punto no autorizan winner picking.

**Antes del piloto falta:** pin de datos/sesiones habilitadas; identidad de detector y salvedades de paridad aceptadas; snapshots/joins y tests negativos; subset determinista y presupuesto piloto; revisión independiente y autorización. **Antes del estudio de outcomes falta además** cerrar predicados/respuesta/MDE/controles/inferencia/roster. No dependen de terminar supervisor 24×7, cgroup delegado o writer científico autenticado.

No se promete «optimización máxima» ni duración/RAM sin benchmark integral en Kaggle. Lo guardado es diseño, catálogo y revisión, no runner implementado ni preregistro aprobado.

## 9. Resultado requerido, no leaderboard de ganadores

- Cobertura y densidad: nacimientos/config, anchors únicos, pares/triples realmente distintos, sesiones/bloques, área precio-tiempo, saturación, aliases y costo por nueva oportunidad.
- Ablaciones incrementales en población común; estabilidad temporal/contractual; controles y su censo propio; censura/no-exit/UNKNOWN; mínimos de soporte/poder y corrección de búsqueda.
- Decisión por familia: evidencia en contra / información aditiva sin interacción / confluencia incremental exploratoria / insuficiente soporte / censura / necesita réplica.
- Ninguno equivale a rentabilidad o edge validado. No trade promotion, P&L, cambio del protocolo viejo, merge o aprobación automática.

Archivos acompañantes: `MNQ_DENSE_CONFLUENCE_DESIGN.json`, `MNQ_DENSE_CONFLUENCE_TOOL_REVIEW.json`, `MNQ_DENSE_CONFLUENCE_BRAIN_RECALL.json` y validación reproducible de metadata. Estos no autorizan ejecuciones.

## 10. Verificación local reproducible (sin mercado)

```sh
python tools/research_ops/designs/check_mnq_dense_confluence.py \
  --spec docs/research/ops/MNQ_DENSE_CONFLUENCE_DESIGN.json
python -m unittest discover -s tests/research_ops -p test_mnq_dense_confluence_design.py -v
python -m unittest discover -s tests/research_ops -v
python -m unittest discover -s tests/navigation -v
python tools/edgelab_catalog.py check --json
```

Resultado observado: 12 tests nuevos de metadata, 512 Research Ops totales y 18 de navegación PASS; catálogo PASS. No ejecutan detectores nuevos sobre mercado ni verifican paridad real, velocidad integral, tamaño/poder estadístico o autorización. El checker devuelve PASS_DESIGN_METADATA_ONLY_NOT_RUN_ADMISSION y rechaza flags de ejecución/aprobación; no es un gate de campaña implementado.

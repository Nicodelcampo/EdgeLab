# AVZVOL: revisión externa de vencimientos y registros de fuente

## Resultado concreto

Se recuperaron **los mismos seis resúmenes de sesiones previamente fijados**, sin sustituir versiones, y se contrastaron sus fechas con la tabla oficial de vencimientos de índices estadounidenses de CME. Los hashes y tamaños coinciden con los pins anteriores: 560 registros contrato-fecha y 485.596.960 ticks **declarados por los resúmenes**, conciliados por contrato con el QA físico anterior. En esta primera etapa no se releen ticks/precios ni outcomes; la sección 4 añade trazabilidad física restringida a siete columnas de identidad, sin precios.

**Hay 3 ticks declarados en 2 registros cuya fecha es posterior al vencimiento de su contrato. Ninguno de esos registros está seleccionado en el resolver fijado.** Son conflictos de identidad/fecha que necesitan trazabilidad upstream, no un nuevo resultado de entradas ni prueba de fabricación de datos. Su causa sigue UNKNOWN; no se excluyen ni reparan datos.

Además, **junio de 2026 vence el jueves 18**, mientras una regla genérica del tercer viernes daría el 19. La tabla oficial es la referencia; no usar la regla genérica como calendario completo.[^https://www.cmegroup.com/trading/equity-index/rolldates.html]

## 1. Dos registros posteriores al vencimiento

| Contrato | Vencimiento oficial | Fecha declarada | Ticks declarados | Primer endpoint CT | Último endpoint CT | Seleccionado en resolver |
|---|---|---|---:|---|---|---|
| MNQ_09-25 | 2025-09-19 | 2025-09-21 | 1 | 2025-09-21T16:15:44.084163900-0500 | 2025-09-21T16:15:44.084163900-0500 | No |
| MNQ_12-25 | 2025-12-19 | 2025-12-21 | 2 | 2025-12-21T12:25:49.884521900-0600 | 2025-12-21T15:52:36.822849100-0600 | No |

Fechas/horas CT convertidas desde endpoints UTC de los resúmenes, conservando nanosegundos; **no certifican el reloj original del proveedor**. Para el registro de dos ticks se preservan ambos endpoints, no se inventa trayectoria intermedia. Los contratos son específicos: un tick de otro vencimiento no explica por sí mismo este rótulo. Podrían intervenir correcciones/reporting/exportación o etiquetado; no se adjudica la causa sin source-file/source-row y logs/originales.

Los registros se confrontan sólo por **fecha estrictamente posterior**; no se evalúa la hora de terminación dentro del día de vencimiento. Tampoco se declara cerrado todo ese día ni se usa el horario de otro producto. La página CME utilizada es una referencia pública cargada ahora: **no evidencia de cuándo el sistema histórico disponía del calendario**.

## 2. Calendario de vencimientos: conservar la excepción

| Contrato | Vencimiento oficial | Roll customary CME | Coincide con tercer viernes genérico |
|---|---|---|---|
| MNQ_09-25 | 2025-09-19 | 2025-09-15 | Sí |
| MNQ_12-25 | 2025-12-19 | 2025-12-15 | Sí |
| MNQ_03-26 | 2026-03-20 | 2026-03-16 | Sí |
| MNQ_06-26 | 2026-06-18 | 2026-06-15 | **No** |
| MNQ_09-26 | 2026-09-18 | 2026-09-14 | Sí |
| MNQ_12-26 | 2026-12-18 | 2026-12-14 | Sí |

Estas fechas proceden de la columna **U.S. Indexes**, no Nikkei/TOPIX. La excepción detectada pertenece a junio de 2026; la regla genérica no se añade a producción ni se modifica el resolver. La tabla no certifica toda sesión diaria, halts, feriados o interrupciones extraordinarias.[^https://www.cmegroup.com/trading/equity-index/rolldates.html]

## 3. Roll customary no equivale a selección por liquidez

CME indica que los participantes pueden rolear cuando elijan y describe una fecha **customary**, no una obligación de que un selector por volumen cambie ese día.[^https://www.cmegroup.com/trading/equity-index/rolldates.html]

| Transición entre contratos de sesiones aprobadas | Roll customary CME | Última fecha aprobada con contrato viejo | Primera fecha aprobada con contrato nuevo |
|---|---|---|---|
| MNQ_09-25 → MNQ_12-25 | 2025-09-15 | 2025-09-12 | 2025-09-17 |
| MNQ_12-25 → MNQ_03-26 | 2025-12-15 | 2025-12-15 | 2025-12-17 |
| MNQ_03-26 → MNQ_06-26 | 2026-03-16 | 2026-03-16 | 2026-03-19 |
| MNQ_06-26 → MNQ_09-26 | 2026-06-15 | 2026-06-12 | 2026-06-16 |
| MNQ_09-26 → MNQ_12-26 | 2026-09-14 | 2026-09-14 | 2026-09-17 |

**Las dos últimas columnas describen el conjunto aprobado del resolver**, no el momento efectivo de la decisión de roll ni una prueba de que los días intermedios estuvieran cerrados. No completar automáticamente esos huecos ni llamar tardío al selector sólo por compararlo con customary. El QA previo declara referencias de volumen D-1, pero sigue faltando matriz completa e independiente de challengers, disponibilidad antes de decisión, completitud y política as-of.

## 4. Seguimiento físico: los tres registros sí están en los Parquet fijados

Se recuperaron **dos fuentes canonical v1**, verificando hashes/tamaños originales y todos sus footers antes de abrir columnas. Se leyeron únicamente `ts_utc_ns`, `sequence`, `tick_type`, `instrument`, `contract`, `source_file`, `source_row` en los row groups que podían contener fechas posteriores al vencimiento. No se decodificaron precio, bid/ask, volumen, agresor ni outcomes.

**Los tres registros existen físicamente**, no sólo en el resumen JSON. Conteos, fechas y endpoints coinciden exactamente con los dos resúmenes. Todos llevan `tick_type=trade` y el contrato declarado; eso tampoco verifica que sean ejecuciones originales del exchange.

| Contrato | Fuente declarada, basename | `source_row` declarado | `sequence` declarado | Timestamp reportado CT |
|---|---|---:|---:|---|
| MNQ_09-25 | `20250921.Last.utc.txt` | 34508844 | 34508844 | 2025-09-21T16:15:44.084163900-0500 |
| MNQ_12-25 | `20251221.Last.utc.txt` | 99091416 | 99091416 | 2025-12-21T12:25:49.884521900-0600 |
| MNQ_12-25 | `20251221.Last.utc.txt` | 99091417 | 99091417 | 2025-12-21T15:52:36.822849100-0600 |

**`source_row` coincide aquí con `sequence`, en el final del archivo agregado. No está verificado como número de línea del texto original.** Por tanto, los números sirven para localizar los registros del Parquet, no para pedir la línea 34 millones del pequeño archivo `.utc.txt`. Los paths privados no se publican: basename exacto más hash del path completo en evidencia.

La tarea upstream ya es concreta: obtener estos dos textos `.Last.utc.txt`, sus originales NT8, el convertidor NT8→UTC y logs/mapeo de identidad; comprobar si el registro fue emitido tardíamente, corregido o etiquetado/exportado de forma incorrecta. No se cargaron esos textos/logs ni se escogió una causa. Se conserva UNKNOWN y no se borra ninguna fila.

[Plan acotado](avzvol_expiry_metadata_20261011/physical-trace-plan.json), [testigos físicos y pins](avzvol_expiry_metadata_20261011/physical-identity-traces.json), [receta de identidad](../../tools/trace_avzvol_postexpiry_identities.py). Consulta por fecha civil CT inferida desde el UTC reportado; el reloj upstream sigue sin certificar. La lectura queda explícita, no se presenta toda la revisión como metadata-only después de esta etapa.

## Implicación para reconstruir retest/confirmación

- El contraste externo agrega una revisión real de fuente: fechas de vencimiento y conflictos señalados, con originales preservados.
- **Cero registros post-vencimiento seleccionados no significa cero efecto sobre toda preparación histórica.** El detector legacy y el warmup se revisan aparte; no basta la máscara de sesiones para certificar lo que consumió cada etapa. No se ha medido sensibilidad de outcomes a esos ticks ni estimado su impacto.
- Antes de construir nuevas confirmaciones, la preparación debe respetar calendario revisado y snapshots causales, dejando UNKNOWN donde falte identidad/reloj/continuidad. Esta revisión no emite certificados ni permite replay de mercado.
- Los efectos conocidos de zonas y el retest cercano al control **no cambian con esta revisión**, porque no se recalcularon. H2/H3 siguen siendo preguntas pendientes, no estrategias aprobadas.

## Alcance y pendientes conservados

Revisión **parcial** de referencia externa, metadata e identidades físicas acotadas; no calendario completo de exchange, upstream clock, secuencia/quotes/agresor, continuidad ni liquidez. Se intentó obtener el horario histórico detallado: la página general entrega mezcla de productos/fechas y la ficha dinámica MNQ no expuso los horarios ni siquiera con carga ampliada. **No se sustituyó con horario de BrokerTec, clearing o una ficha antigua de NQ.** No se resolvieron por esa vía las 47 filas antiguas de 16–17 CT ni las 69 referencias semanales cerradas.

El profiler genérico interpreta este JSON como fechas-columnas con valores heterogéneos; sus medias entre ticks/UTC/gaps carecen de significado. Se usó validación nativa: objeto por fecha, ticks enteros positivos, first≤last, particiones anteriores al holdout, hashes/tamaños y conteos independientes. No imputación, deduplicación ni exclusión.

**P1 sigue abierto**, con trabajo parcial real agregado. P2 censo/snapshots zone-free y P3 protocolo/matching/horizontes/censura siguen pendientes. P4 económico y holdout siguen prohibidos. Ni hashes ni tests autorizan una campaña nueva.

## Evidencia y reproducción

[Plan](avzvol_expiry_metadata_20261011/analysis-plan.json), [evidencia completa](avzvol_expiry_metadata_20261011/evidence.json), [fuente pública cargada](avzvol_expiry_metadata_20261011/cme-official-reference.json), [receta](../../tools/review_avzvol_expiry_metadata.py). Los resúmenes privados no se publican ni se guardan URLs firmadas en el repo. El inventario local requiere los seis pins exactos (canonical v1: 09-25/12-25/03-26; reexport v2: 06-26/09-26/12-26).

`python tools/review_avzvol_expiry_metadata.py --inventory <inventario-local> --resolver <resolver-v15-local> --cme-source <fuente-cargada-local> --out-dir <directorio-nuevo> --allow-pinned-metadata-expiry-review`

[Revisión física previa](../infra/AVZVOL_MNQ_RAW_QUALITY_20261010.md), [observabilidad de confirmación](AVZVOL_CONFIRMACION_OBSERVABILIDAD_20261011.md), [readiness científico](../../specs/research/avzvol_incremental_design_v1.json). Evidencia derivada; se conservan specs, pins y resultados anteriores sin reescribirlos.

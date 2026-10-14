# Release líquida de ticks — informe del 2026-10-14

**Estado: `CANDIDATE_NOT_RESEARCH_APPROVED`.** Un Parquet por activo (14 activos), sólo sesiones con contrato líquido elegido causalmente, sin holdout.
No es un certificado de datos ni autoriza research. La política de liquidez es una **propuesta sin aprobar**. Respuesta al handoff [`LOCAL_AGENT_LIQUID_DATA_REPAIR_HANDOFF_20261014.md`](LOCAL_AGENT_LIQUID_DATA_REPAIR_HANDOFF_20261014.md).

Dónde está: dataset privado de Kaggle `nicolasbuttaro/edgelab-liquid-ticks-20261014` y copia local `D:\edgelab_release_work\release_20261014`. Código: rama `data/liquid-release-20261014`, commit `fb3228a6`. Leer primero `README_AGENTES.md` dentro de la release.

## 1. Contenido por activo

| activo | filas | sesiones incluidas | rango | tamaño | sin contrato elegible | indeterminadas | contrato elegido sin datos |
|---|---:|---:|---|---:|---:|---:|---:|
| 6B | 8,999,265 | 291 | 20250804→20260925 | 0.10 GB | 8 | 7 | 2 |
| 6E | 20,565,413 | 285 | 20250805→20260925 | 0.21 GB | 13 | 9 | 1 |
| 6J | 18,130,682 | 289 | 20250805→20260925 | 0.18 GB | 9 | 8 | 2 |
| ES | 305,388,909 | 300 | 20250721→20260925 | 1.75 GB | 6 | 4 | 1 |
| GC | 42,311,449 | 289 | 20250805→20260930 | 0.49 GB | 4 | 2 | 2 |
| MBT | 9,890,143 | 284 | 20250826→20260930 | 0.13 GB | 5 | 2 | 1 |
| MES | 191,255,168 | 291 | 20250805→20260928 | 1.36 GB | 5 | 3 | 1 |
| MGC | 79,473,540 | 222 | 20251008→20260930 | 0.79 GB | 49 | 21 | 5 |
| MNQ | 458,725,419 | 285 | 20250805→20260930 | 3.51 GB | 2 | 10 | 5 |
| MYM | 24,363,834 | 227 | 20251001→20260928 | 0.29 GB | 60 | 10 | 3 |
| NQ | 142,582,554 | 292 | 20250805→20260925 | 1.31 GB | 2 | 5 | 1 |
| RTY | 37,098,789 | 249 | 20251006→20260928 | 0.40 GB | 49 | 1 | 1 |
| YM | 22,825,441 | 267 | 20250818→20260930 | 0.29 GB | 15 | 18 | 2 |
| ZB | 33,662,049 | 283 | 20250819→20260930 | 0.26 GB | 1 | 6 | 1 |

Total: **1,395,272,655 filas**, 11.1 GB.

## 2. Verificación independiente

`tools/verify_release.py` relee cada archivo y compara con el censo: filas totales y por sesión (exacto), un solo contrato por sesión y el de la decisión, `regime_id` sin retrocesos, `ts` no decreciente, sin holdout, precios positivos, bid ≤ ask y un row group por fecha.

| activo | resultado | filas | sesiones |
|---|---|---:|---:|
| 6B | OK | 8,999,265 | 291 |
| 6E | OK | 20,565,413 | 285 |
| 6J | OK | 18,130,682 | 289 |
| ES | OK | 305,388,909 | 300 |
| GC | OK | 42,311,449 | 289 |
| MBT | OK | 9,890,143 | 284 |
| MES | OK | 191,255,168 | 291 |
| MGC | OK | 79,473,540 | 222 |
| MNQ | OK | 458,725,419 | 285 |
| MYM | OK | 24,363,834 | 227 |
| NQ | OK | 142,582,554 | 292 |
| RTY | OK | 37,098,789 | 249 |
| YM | OK | 22,825,441 | 267 |
| ZB | OK | 33,662,049 | 283 |

## 3. Auditoría de lo que había publicado en Kaggle

Contraste sesión por sesión (trades por contrato y fecha de trading) de 145 archivos Parquet publicados contra los originales locales: 8,963 sesiones idénticas, 437 casi idénticas (< 1 %), 327 con diferencias y 1,440 que existen en Kaggle sin original de texto local (casi todo RTY y tramos tempranos de MYM/MES/MNQ/YM). Ninguna sesión de holdout en lo publicado. Detalle por archivo: `kaggle_vs_sources_by_file.csv` (en la carpeta de trabajo, sin precios).

## 4. Resolución de los 23 problemas del handoff

| ID | prioridad | problema | estado | evidencia | residual |
|---|---|---|---|---|---|
| D01 | P0 | Timezone no acreditado | `RESOLVED_WITH_EVIDENCE` | Ajuste al calendario CME por grupo de fuentes y por trimestre: 192 de 226 grupos calzan con UTC (violación ≈ 1e-6; ART violaría 4–12 %), con cambio de horario estable. Los 15 con anomalías son MBT (calendario propio) y el NQ nativo explicado en D02. | Residual: no hay logs de NinjaTrader ni verificación contra el feed (conexión `Simulation`). Alcance de la evidencia = calendario, no feed. |
| D02 | P0 | NQ fuente en cuarentena | `RESOLVED_WITH_EVIDENCE` | Causa raíz: el export nativo `NQ 09-26` trae 15 bloques de ticks copiados fila a fila con +3 h exactas (2026-06-17 → 07-02), 532.441 ticks, 100 % dentro del horario sin mercado. El export por día no los tiene. La release descarta las copias; el parquet `nq-preholdout/6` queda en CUARENTENA etiquetado. | Residual: por qué el export nativo copia el bloque (requiere logs del exportador). |
| D03 | P0 | ES roll prematuro | `RESOLVED_WITH_EVIDENCE` | Los ticks de domingo previos a la apertura no forman sesión. ES permanece en 12-25 durante octubre 2025 y rolla 16-sep-25, 16-dic-25, 17-mar-26, 16-jun-26 y 15-sep-26. | Residual: el calendario CME oficial sigue pendiente (D06). |
| D04 | P0 | Máscara retrospectiva | `RESOLVED_WITH_EVIDENCE` | La decisión de cada sesión usa sólo D-1 y constantes congeladas; prueba de invariancia por mutación del futuro en `tests/data/test_liquid_release_selection.py`. | Las constantes se calibraron descriptivamente sobre toda la muestra pre-holdout: son una PROPUESTA hasta que Nico las apruebe (D07). |
| D05 | P0 | Completitud inventada / ausencia = 0 | `OPEN` | Estados explícitos por sesión (incluida, sin contrato elegible, indeterminada, contrato elegido sin datos) y por día de calendario (OPEN/SHORT/CLOSED/MISSING_EXPORT). Nunca se emite 'cero verificado'. | Falta la matriz rectangular contrato×sesión con evidencia de captura por contrato. |
| D06 | P0 | Calendario histórico revisado | `BLOCKED_UPSTREAM` | Calendario derivado de los datos (`calendar_derived.parquet`): feriados/cierres tempranos por volumen de todos los activos. | Hace falta el calendario histórico oficial de CME (feriados, cierres cortos, DST). |
| D07 | P0 | Liquidez relativa vs absoluta | `OPEN` | Límites absolutos por activo (volumen, ticks, spread típico) como política PROPUESTA en `liquidity_policy.json`. | `approved_by = null`: requiere aprobación de Nico antes de cualquier uso de research. |
| D08 | P1 | Fuentes en conflicto | `RESOLVED_WITH_EVIDENCE` | Regla fija por (contrato, sesión): más minutos activos, menor hueco, luego export por día > nativo > parquet derivado. 701 sesiones con diferencias de contenido registradas en `source_conflicts.parquet`; 97 % de las horas comparadas son idénticas (mediana de diferencia: 1 tick). | No hay un tercer feed independiente para decidir cuál es 'verdad' cuando difieren por pocos ticks. |
| D09 | P1 | Contratos/fechas faltantes | `OPEN` | `metadata/MISSING_EXPORTS.md`: 321 sesiones P0 y 275 sesiones P1 con contrato y rango de fechas exactos. | Exportar lo listado con el AddOn `EdgeLabTickHistory`; RTY y parte de MYM dependen de parquet derivado. |
| D10 | P1 | Esquemas heterogéneos | `RESOLVED_WITH_EVIDENCE` | Lectores explícitos por formato (texto NT8 y parquet canonical_tick_v1) con validación de grilla antes del redondeo; tick y valor por tick de 14 activos (incluye MGC, RTY y MBT, que faltaban en el contrato) verificados contra la grilla de los datos. | Sin residual conocido. |
| D11 | P1 | Grilla/tick y procedencia de quote/agresor | `RESOLVED_WITH_EVIDENCE` | Grilla validada fila a fila antes de convertir (STOP si falla); quotes inválidos quedan `-1`; agresor por regla de quotes v1 y 0 si el libro está locked/cruzado/ausente. | La procedencia upstream de bid/ask no se puede verificar sin logs. |
| D12 | P1 | Identidad local no prueba continuidad upstream | `BLOCKED_UPSTREAM` | Se conservan `source_id` (SHA-256 del origen) y `source_row`; no se deduplica por precio/tiempo/volumen iguales; `release_row` se declara distinta de la secuencia del exchange. | Sin ID upstream no se puede probar continuidad. |
| D13 | P1 | Quotes locked y agresor desconocido | `RESOLVED_WITH_EVIDENCE` | Se conservan y se miden por sesión (columnas `locked`, `crossed`, `noquote` del escaneo). | Política de uso por indicador pendiente. |
| D14 | P0 | Filtro después de lectura / holdout | `RESOLVED_WITH_EVIDENCE` | Nuevo lector: row groups por estadísticas de `trade_date`, STOP ante grupo mixto o sin estadísticas; constructor: corte del holdout sobre bytes antes de decodificar. Pruebas con lector espía. | `continuous_contract.py` y los lectores legacy NO se tocaron (D18). |
| D15 | P0 | Integridad/versiones débiles | `RESOLVED_WITH_EVIDENCE` | Nuevo lector exige manifiesto, tamaño y SHA-256 exactos; prueba de mismo tamaño con distinto contenido. | El helper legacy `edgelab_data.py` no se modificó. |
| D16 | P0 | Rutas ambiguas | `RESOLVED_WITH_EVIDENCE` | Nuevo lector: rutas relativas exactas, sin traversal ni symlink, sin búsqueda por basename. | Legacy sin cambios. |
| D17 | P1 | Cache no ligada al contenido | `RESOLVED_WITH_EVIDENCE` | `cache_key(sha, schema, transform, version)` en el lector nuevo. | Las cachés legacy no se migraron. |
| D18 | P0 | Wiring protegido no global | `OPEN` | El lector nuevo es opt-in y está probado. | Falta el mapa de call-sites y conectarlo en autónomo, notebooks y CLI. |
| D19 | P1 | Rolls, estado y lookbacks | `RESOLVED_WITH_EVIDENCE` | Contrato real por fila, `regime_id` por roll, sin back-adjust ni empalme; el consumidor debe reiniciar estado al cambiar `regime_id`. | Los consumidores existentes no se auditaron. |
| D20 | P1 | Derivados pueden seguir viejos | `OPEN` | Los agregados v1 (1/30/60 s) y la caché de descubrimiento quedaron etiquetados como BLOQUEADOS/ARCHIVO en Kaggle. | Regenerar barras desde la release y clasificar resultados históricos por dependencia. |
| D21 | P1 | Licencia/privacidad y spot/futuro | `OPEN` | Los 41 datasets de la cuenta están en privado; spot (Dukascopy) etiquetado `SPOT` y separado de CME. | La decisión de licencia de redistribución sigue siendo de Nico. |
| D22 | P2 | Inventarios/pins desactualizados | `RESOLVED_WITH_EVIDENCE` | Inventario paginado completo (41 datasets, 248 kernels), mapa en `config/kaggle_space_map_20261014.json` y `KAGGLE_SPACE_INDEX.md`; la release se fija por SHA-256 en `release_manifest.json`. | Sin residual. |
| D23 | P1 | Warmup, cobertura y claims | `RESOLVED_WITH_EVIDENCE` | La primera sesión de cada activo (sin D-1) y las sin contrato elegible se excluyen y listan; no se declara certificación ni edge. | Warmup específico de cada indicador queda a cargo del consumidor. |

## 5. Decisiones que quedan en manos de Nico

1. **Aprobar o corregir la política de liquidez** (`metadata/liquidity_policy.json`). Hasta entonces la release es candidata.
2. **Licencia/redistribución de los datos CME** (todo está en privado).
3. **Exportar lo que falta** (`MISSING_EXPORTS.md`): RTY completo, MYM y los fines de septiembre de varios activos.
4. **Calendario histórico oficial de CME** para cerrar D06 y distinguir feriados de huecos de export.

## 6. Espacio de Kaggle

Mapa, estados y kernels agrupados por familia: `KAGGLE_SPACE_INDEX.md` (dentro de `edgelab-data-catalog`) y `config/kaggle_space_map_20261014.json`. Ningún dataset ni kernel se borró; sólo se señalizaron metadatos.

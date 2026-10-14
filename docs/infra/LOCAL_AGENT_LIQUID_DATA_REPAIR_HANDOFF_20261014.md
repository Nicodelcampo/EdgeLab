# Reparación de datos y serie líquida por activo — handoff al agente local

**Destinatario:** agente local de Nico, con acceso autorizado a los exports originales de NinjaTrader y sus logs.  
**Objetivo:** publicar una release privada, reproducible y versionada con **un archivo de ticks por activo**, compuesto exclusivamente por el contrato seleccionado causalmente entre fuentes verificadas.  
**Estado:** plan de trabajo y criterios de aceptación; **no es certificado de datos reparados**, autorización de holdout, permiso de trading ni despliegue del sistema autónomo.

## 0. Resumen ejecutivo y decisiones obligatorias

1. **Un archivo por activo no significa un contrato fijo para toda la historia.** El archivo de `MNQ` contiene tramos de distintos vencimientos MNQ, con el contrato real de cada fila y cada frontera de roll preservados. ES/MES, NQ/MNQ, GC/MGC, YM/MYM son activos separados: no reemplazarlos entre sí.
2. **“El que tiene liquidez” debe definirse antes de construirlo.** Elegir el contrato usando volumen realmente negociado de la **sesión completa anterior**, calendario verificado y límites absolutos por activo. No seleccionar usando el volumen final del mismo día, la rentabilidad posterior o una mediana que incorpora el futuro.
3. **No alcanza que el archivo exista o pase controles estructurales.** Horario/procedencia, cobertura, selección causal y liquidez son dimensiones distintas. Cada una debe tener evidencia.
4. Las cargas recientes mejoran el acceso: el reexport v2 tiene sus archivos y el catálogo v16 mejora algunos chequeos de montaje. **No demuestran reparación del roll ES ni de la fuente NQ en cuarentena.**
5. Reutilizar auditorías y hashes válidos de inputs inmutables. Reauditar lo nuevo o cambiado y verificar el producto consolidado: **no repetir todo Kaggle en cada corrida**.
6. Mantener originales y publicaciones antiguas intactos. Corregir en una **nueva release** con un mapa explícito de diferencias y de resultados históricos afectados.
7. La reparación se realiza en el espacio privado local autorizado; los experimentos siguen en Kaggle privado. **No publicar ticks, precios, tablas diarias privadas, exports, modelos, credenciales ni URLs firmadas en GitHub o este chat.**

### Alcance de este reporte

Este documento reúne los problemas conocidos en auditorías, inventarios históricos y la revisión live de cargas recientes. **No implica que se haya auditado toda la cuenta actual ni todos los exports locales.** Las listas antiguas de huecos/conflictos son tareas de reconciliación, no afirmaciones de que todos continúen abiertos después del reexport.

Fuentes de evidencia:

| Ref. | Evidencia y versión |
| --- | --- |
| E1 | [Auditoría inicial de saneamiento/custodia](https://github.com/Nicodelcampo/EdgeLab/blob/4579f5512b150a440d0bd6ea3115a5032ec8d0f0/docs/research/CANONICAL_DATA_AUDIT_20261004.md) |
| E2 | [QA de barras ES/NQ](https://github.com/Nicodelcampo/EdgeLab/blob/4579f5512b150a440d0bd6ea3115a5032ec8d0f0/docs/infra/KAGGLE_DATA_QUALITY_20261010.md) |
| E3 | [QA completa de 18 primarios ES/NQ](https://github.com/Nicodelcampo/EdgeLab/blob/4579f5512b150a440d0bd6ea3115a5032ec8d0f0/docs/infra/KAGGLE_FULL_RAW_AUDIT_20261010.md) |
| E4 | [Roll ES y rastreo del evento dominical](https://github.com/Nicodelcampo/EdgeLab/blob/4579f5512b150a440d0bd6ea3115a5032ec8d0f0/docs/infra/KAGGLE_ROLL_SELECTION_20261010.md) y [pedido upstream](https://github.com/Nicodelcampo/EdgeLab/blob/4579f5512b150a440d0bd6ea3115a5032ec8d0f0/docs/infra/KAGGLE_UPSTREAM_REPAIR_20261010.json) |
| E5 | [QA física de seis fuentes MNQ](https://github.com/Nicodelcampo/EdgeLab/blob/c8a1e176b3f9a2d635338b23eba8dfea415b2e7b/docs/infra/AVZVOL_MNQ_RAW_QUALITY_20261010.md) |
| E6 | [Inventario histórico de problemas](https://github.com/Nicodelcampo/EdgeLab/blob/ab071322ff3a08022a3a71994e09a28c97723bbe/docs/data_catalog/ISSUES.md), [reexport solicitado](https://github.com/Nicodelcampo/EdgeLab/blob/ab071322ff3a08022a3a71994e09a28c97723bbe/docs/data_catalog/REEXPORT.md), [plan local anterior](https://github.com/Nicodelcampo/EdgeLab/blob/ab071322ff3a08022a3a71994e09a28c97723bbe/docs/data_catalog/REEXPORT_PLAN_20261004.md) |
| E7 | [Loader publicado en catálogo v16](https://github.com/Nicodelcampo/EdgeLab/blob/ab071322ff3a08022a3a71994e09a28c97723bbe/docs/data_catalog/edgelab_data.py) y [launcher](https://github.com/Nicodelcampo/EdgeLab/blob/ab071322ff3a08022a3a71994e09a28c97723bbe/tools/kaggle_launch.py) |
| E8 | Revisión live de este chat: catálogo v16, reexport v2 y código-zones v13; [resumen JSON](KAGGLE_RECENT_UPLOAD_REVIEW_20261014.json) y [13 comprobaciones sintéticas](KAGGLE_RECENT_UPLOAD_SYNTHETIC_CHECKS_20261014.csv). PASS en un caso `documented_safety_limit` significa que se reprodujo la limitación, no que el loader sea seguro. |

## 1. Lo que ya está resuelto, y no hay que volver a hacer

- Reexport `edgelab-ticks-nt8-reexport-20261005/2`: listado completo de **70 archivos**, incluidos **23 Parquet + 23 manifiestos + 23 archivos de sesiones + README**. La v1 con solo README quedó superada por v2. Existencia no certifica calidad de todos los 23.
- ES/NQ: **18/18 primarios**, **546.709.478 filas**, auditados estructuralmente. El informe parcial que decía “faltan 16” es historia, no una tarea vigente sobre esos mismos hashes. Cero errores en los controles aplicados; siguen abiertos otros criterios.
- MNQ: **seis fuentes**, **485.596.960 filas**, con QA física estructural. Canonical 1: 09-25/12-25/03-26; reexport 2: 06-26/09-26/12-26. No extrapolar esa evidencia a todos los instrumentos ni a otra versión.
- Transporte autenticado y archivos fijados funcionaron en las corridas recientes. El diagnóstico GC de soporte reutilizó su pin y calibración sin una nueva auditoría general.
- La igualdad de timestamps **no es duplicación**. Las auditorías conservaron los timestamps repetidos legítimos; no volver a eliminarlos.
- No hay motivo para volver a lanzar campañas de resultados por haber cambiado el helper. Primero resolver una causa concreta y documentar qué artefactos dependen de ella.

## 2. Registro completo de problemas conocidos

**Prioridad:** P0 bloquea el producto nuevo o su lector; P1 debe resolverse para certificar el activo/ventana afectado; P2 es mejora operativa/documental.  
**Estado:** “confirmado” corresponde al alcance/versiones indicados; “riesgo de código” no prueba contaminación de una corrida; “histórico” debe cotejarse con los exports y publicaciones actuales.

| ID / prioridad | Problema y evidencia | Qué debe hacer el agente local | Evidencia para cerrarlo |
| --- | --- | --- | --- |
| D01 / P0 | **Timezone no acreditado.** `ts_local_ns == ts_utc_ns` en los primarios no prueba UTC. Los exports sin zona y la configuración UI de NT8 no bastan. E1/E3/E5/E6. | Identificar el exporter realmente utilizado, configuración de zona, semántica de cada campo, conversor y logs. Reconciliar eventos normales y anómalos contra originales, calendario y DST. | Contrato de timestamp por familia, hashes de código/originales, muestras privadas trazables, pruebas de UTC/DST y explicación de cada discrepancia. |
| D02 / P0 | **NQ fuente específica en cuarentena.** `edgelab-ticks-nq-preholdout/6:NQ_09-26_ticks.parquet`. En nueve sesiones primarias de junio: 363.601 trades en 16–17 Chicago; alternativa no los tiene. Fuera de la banda coinciden 5/9, difieren 4/9. E3. | Comparación a tres: export original, primaria y alternativa, por eventos ordenados y procedencia. Explicar filas extra y diferencias restantes; emitir fuente corregida solo con justificación. | Adjudicación por fecha/contrato y categoría de diferencia, versión nueva, conteos/hash nuevos, revisión que autorice sustituir la combinación antigua. |
| D03 / P0 | **ES roll prematuro.** Resolver 15 elige marzo de 2026 desde octubre de 2025 por dos eventos dominicales, volúmenes 1/2; diciembre tenía mayor volumen en 50/52 fechas compartidas revisadas. E4. | Rastrear ambos eventos al original/exportador. Reconstruir calendario/completitud y todos los challengers D-1. Rehacer la cadena y derivados. | Nueva selección causal; explicación de cada roll; comparación privada contra 15; fuente del domingo adjudicada, no borrada para forzar el resultado. |
| D04 / P0 | **Máscara retrospectiva de elegibilidad.** Medianas de toda la muestra y actividad del mismo día no eran conocidas antes de la sesión. E2/E8. | Eliminar esas dependencias de la selección causal. Congelar política y estadísticas históricas permitidas, disponibles en D-1. | Prueba de invariancia al modificar datos futuros; registro `decision_as_of` y dependencias de cada decisión. |
| D05 / P0 | **Completitud inventada o ausencia=0.** Builders históricos marcaban fechas como completas y rellenaban faltantes con cero; días de semana no equivalen a calendario de bolsa. E1. | Distinguir sesión cerrada, abierta completa, captura parcial, no exportada, desconocida y cero operaciones verificado. Nunca inferir completitud de row-count o primer/último día. | Matriz contrato×sesión con estado/evidencia; negativos explícitos; `UNKNOWN` bloquea, no se convierte a cero. |
| D06 / P0 | **Falta calendario histórico revisado**, mantenimiento, feriados/cierres cortos y DST. E2/E3/E5. | Obtener calendario aplicable por producto/fecha, versionarlo, conservar referencia y revisar intervalos contra captura upstream. No imponer horario de otro producto. | Cobertura de todas las fechas solicitadas; calendario/hashes; excepciones justificadas. |
| D07 / P0 | **Líder relativo ≠ liquidez absoluta.** Un volumen mínimo entre contratos malos no crea un contrato líquido; antiguo roll MGC por 1/2 y líderes muy finos. E1/E6. | Seleccionar entre contratos con sesión previa completa y límites absolutos por activo, volumen negociado y spread; reportar profundidad desconocida. | Límites congelados/revisados y medidas D-1. Si ninguno cumple: sin contrato elegible, no fallback automático. |
| D08 / P1 | **Fuentes en conflicto y alternativas por parecido.** Conflictos ES/NQ y otras familias; comparar conteos no autentica el feed. E2/E3/E6. | Establecer prioridad de fuentes por evidencia, no por mejor resultado ni por cantidad mayor. Resolver cada conflicto antes de fusionar. | Tabla de adjudicación y linaje fila→export; conflictos no resueltos en cuarentena. |
| D09 / P1 | **Contratos o fechas históricamente faltantes; exportación NO_DATA.** E6. | Primero cotejar hashes/cobertura del reexport 2 contra los originales existentes. Recuperar solo lo pendiente, incluyendo contratos no líderes necesarios para D-1. | Inventario actualizado y tabla “cerrado/persiste/no requerido/unknown”; no reutilizar la lista vieja como verdad actual. |
| D10 / P1 | **Esquemas heterogéneos.** MGC raw precio decimal; canonical precios en ticks; MNQ usuario sin zona; spot es quotes. E1/E6. | Adaptador explícito por export/schema, contrato geométrico por activo y versión. Separar trade/quote y unidades. | Validación antes de convertir; mapa de campos/unidades, registros inválidos en cuarentena, nada de inferir por filename. |
| D11 / P1 | **Grid/tick-size y procedencia de quote/agresor incompletos.** `rint` puede ocultar precio fuera de grid; integer ticks no prueba precisión original. E1/E3/E5. | Validar texto/decimal original antes del redondeo, tamaño de tick correcto y regla causal de quotes/agresor. Mantener UNCLASSIFIED cuando corresponde. | Conteos/residuos de grid, método documentado y comparación original→canónico. No inventar bid/ask/agresor. |
| D12 / P1 | **Identidad local no prueba continuidad upstream.** Secuencia continua e IDs distintos pueden venir del conversor. E3/E5. | Preservar `source_id`, hash original y fila/offset; verificar continuidad con logs/captura cuando exista. No deduplicar por precio/tiempo/volumen iguales. | Duplicados adjudicados por identidad/origen; pruebas de solapamientos entre exports; UNKNOWN si no hay ID upstream. |
| D13 / P1 | **Quotes locked y agresor desconocido.** Advertencias legítimas ya conservadas; estructura puede pasar aun con semántica limitada. E3/E5. | Mantenerlos, cuantificar por alcance y fijar política de uso específica de indicadores. Book cruzado/no positivo sí exige fallo/investigación. | Estadísticas y política explícita; sin limpieza silenciosa o imputación futura. |
| D14 / P0 | **Filtro después de lectura / holdout mezclado.** `continuous_contract.py` usa `pq.read_table` antes de recortar; helper M1 procesa archivo completo. E1/E7. | Guard global antes de payload, fuentes permitidas y rowgroups seguras; reexportar preholdout si hay mezcla o metadatos insuficientes. | Tests con lector espía: ninguna columna reservada deserializada; STOP ante rowgroup mixto/desconocido. |
| D15 / P0 | **Integridad/versiones débiles en helper 16.** Compara bytes, no SHA; `versions` se imprime, no se verifica; manifiesto ausente/vacío no-op. E7/E8. | Manifiesto obligatorio para producción, versión efectiva inmutable, hash externo aprobado y contenido exacto. Rechazar cero inputs esperados. | Mismo tamaño/distinto contenido falla; versión/mount incorrecto falla; manifiesto ausente/vacío falla antes de lectura. |
| D16 / P0 | **Rutas ambiguas.** `_path` acepta basename único en otra carpeta y prioriza primera raíz; varios consumidores legacy tienen fallback. E7/E8. | Ruta relativa exacta + raíz única ligada a versión; prohibir traversal/symlinks fuera de raíz y fallback de nombre. | Tests con archivos homónimos, raíces duplicadas, path traversal y subcarpeta equivocada. |
| D17 / P1 | **Cache no ligada al contenido.** Cache M1 por tamaño; se puede reutilizar después de un cambio de igual longitud. E7/E8. | Clave por SHA raw  + schema + transformación + calendario/política; verificar hash del cache/manifest. | Cambio de contenido igual tamaño no da cache hit; salida vieja invalidada explícitamente. |
| D18 / P0 | **Wiring protegido no global.** Existe `research_access` con gates; el loader legacy y otros caminos no quedan protegidos por importarlo. E1/E3/E7. | Enumerar todos los lectores del autónomo, scripts/notebooks y CLI; conectar verificación previa obligatoria. | Mapa de call-sites y tests negativos de cada entrada; ningún bypass de producción. |
| D19 / P1 | **Rolls, estado y lookbacks pueden cruzar contratos.** Un archivo unido sin frontera arrastra zonas/historia o parece un precio ajustado. E1. | Mantener precios reales, contrato y régimen; reset/rewarm por roll según protocolo; conservar discontinuidad natural. | Tests que impiden zonas/historia de contrato anterior; ninguna corrección aditiva/multiplicativa de precios. |
| D20 / P1 | **Derivados pueden seguir viejos.** Arreglar ticks/loader no regenera resolver, agregado, features o resultados dependientes. E2/E4. | DAG de dependencias por SHA; reconstrucción selectiva del nuevo producto y barras; marcar históricos afectados sin borrarlos. | Manifests padre→hijo y tabla de impactos. No declarar cambiado un resultado que no se recalculó. |
| D21 / P1 | **Licencia/privacidad y spot/futuro.** Inventario antiguo reportó fuentes CME públicas; MGC raw no canónico; Dukascopy no negocia el futuro CME. E6. | Verificar privacidad real actual y licencia; aislar spot, micro y estándar; no publicar datos CME derivados como CC0 por accidente. | Inventario privado/licencias actual; consumidores no mezclan familias; metadatos públicos sin mercado privado. |
| D22 / P2 | **Inventarios/pins/documentación desactualizados.** Listado de 20 no era toda la cuenta; metadatos de upload y contenido no son sinónimos; `COMMIT +post` no es pin completo. E6/E8. | Paginar todos los datasets/archivos relevantes, registrar versiones y SHA de todos los archivos consumidos, actualizar guía/discovery. | Inventario exhaustivo de alcance, ninguna “latest” silenciosa, paquete de código exacto verificable. |
| D23 / P1 | **Warmup, cobertura de investigación y claims exagerados.** PASS estructural no implica certificación/edge, ni ausencia de gaps; contar anclas solapadas no da réplica independiente. E3/E5. | Documentar ventana disponible y warmup por activo/contrato; separar certificación técnica, elegibilidad, research y performance. | Claims limitados al alcance; sesiones excluidas/UNKNOWN visibles; no ensayos económicos para cerrar QA. |

### Correcciones de interpretación importantes

- En el código actual de `contract_regime.py` la normalización **ya rechaza valores no finitos**. No presentar esa parte del hallazgo antiguo como bug todavía vigente. Aun así, el gate de producción debe rechazar volumen cero/ausencia y pedir límites absolutos/evidencia: validar un builder no certifica su input.
- La anomalía ES/NQ no se resuelve “restando una hora”. En 5/9 sesiones NQ el resto ya coincide en UTC; en 4/9 continúan diferencias. Explicar eventos y conversión, no fabricar alineación.
- Los huecos de catálogo son observaciones faltantes, no pérdidas demostradas. “Lunes–viernes” tampoco significa mercado abierto: algunos listados antiguos lo afirmaban demasiado fuerte.
- La secuencia local, un checksum autoemitido y `SANITIZED_VERIFIED` escrito por el productor **no son autoridad independiente**.

## 3. Cola concreta por activo: reconciliar antes de reexportar

Estos puntos proceden de E6, anterior a parte de las cargas actuales. **No lanzar automáticamente todas las reexportaciones de esta tabla.** Para cada punto, comparar original existente, reexport 2, catálogo y calendario; cerrar si ya está resuelto y conservar la prueba.

| Activo | Contratos/fuentes a reconciliar | Fechas históricas a comprobar o alcance |
| --- | --- | --- |
| ES | ES_12-25 frente a ES_03-26 por roll dominical; ES_09-26 en conflicto | Evento 2025-10-05 y sesiones normales adyacentes; tramo 2025-10-06..2025-12-09; ausencia reportada 2026-08-27 |
| NQ | NQ_09-26 preholdout 6 en cuarentena frente missing 1/original; NQ_06-26 y NQ_09-25; NQ_12-25 salvedad histórica | Nueve sesiones de junio que detalla E3, incluyendo 2026-06-17; comparar también fuera de 16–17 CT |
| MNQ | MNQ_12-26 entre canonical 1/mnq-parquet/reexport 2; recuperar evidencia física del productor y timezone | Históricos 2026-03-26,04-02,05-21; separar PASS estructural de seis archivos de revisión fuente abierta |
| MES | Completar/confirmar MES_09-26 reexport 2, fuente original | Históricos 2026-08-06 y 08-13 |
| GC | GC_08-25, GC_10-25, GC_10-26 solicitados; reexport 2 ya tiene GC_08-26 y GC_12-26 | Históricos 2026-08-28,09-10,09-11,09-16,09-24; recuperar challenger faltante antes de concluir líquido |
| MGC | MGC_10-25, MGC_10-26 solicitados; MGC_08-26/MGC_12-26 en conflicto; raw MGC_08-25 casi vacío | Históricos 2026-07-02,07-09,07-16,07-30,08-28,09-10,09-11; roll 02-26→04-26 por domingo con volumen 1/2; aislar 2026-10-01 |
| 6E | 6E_09-26 entre fuentes | Histórico 2026-09-03; interpretar timezone/export original y quotes |
| MBT | MBT_06-26..10-26; MBT_07-26 en conflicto; parte de archivos ya existía localmente | Ausencias reportadas 2026-06-01..05,06-08..12,06-15..18; verificar calendario/producto y reexport antes de reclamar completitud |
| MYM | MYM_09-25 casi vacío y MYM_09-26 | Históricos 2025-09-22..26,09-29;2026-07-09,07-16,07-23,07-30,08-20 |
| RTY | RTY_09-25 casi vacío; RTY_12-25 | Históricos 2025-09-22..26 y 09-29..10-01; revisar disponibilidad de contrato cercano |
| YM | YM_09-26 y YM_12-26 en conflicto | Histórico 2026-08-20 |
| ZB | ZB_09-26 y ZB_12-26 originales y reexport 2 | El plan antiguo tenía archivos locales aún sin canonizar/subir; calendario por producto, no asumir horarios ES |
| 6B / 6J | Exports, ticksizes, procedencia y calendario del rango pedido | Sin cierre de calidad global demostrado aquí; no copiar PASS de 6E ni fabricar pendientes específicos |
| Spot Dukascopy | Mantener XAUUSD/USA500/USATECH/etc separados de los futuros | El inventario antiguo decía XAUUSD unificado disponible; no usar bid_vol/ask_vol como volumen negociado CME ni demostrar absorción con ellos |

El patrón histórico de faltantes en jueves apuntaba a solicitudes de día local `[d,d+1)` y pares miércoles/jueves `NO_DATA`. El agente tiene los originales: confirmar logs/base horaria y reparar **intervalos de sesión** desde calendario. Que exista hoy un archivo horario de NT8 no acredita por sí mismo que la captura sea completa.

## 4. Diseño del producto final: un archivo líquido por activo

### 4.1 Organización propuesta de release

```text
release_<id>/
  data/
    ES_ticks.parquet
    NQ_ticks.parquet
    MES_ticks.parquet
    MNQ_ticks.parquet
    GC_ticks.parquet
    MGC_ticks.parquet
    ... un archivo por cada activo realmente aprobado ...
  metadata/
    release_manifest.json
    instrument_specs.json
    source_manifest.json
    calendar_manifest.json
    liquidity_policy.json
    selection_manifest.json
    session_index.parquet
    source_adjudications.json
    quality_summary.json
  private_evidence/
    ... trazabilidad y reconciliaciones detalladas ...
```

“Un archivo por activo” se refiere al **producto de ticks consumible**, no a destruir los exports por contrato ni a meter todos los metadatos en ese archivo. Las releases viejas permanecen inmutables. No crear un archivo aparentemente completo para un activo todavía bloqueado: publicar su estado, no reemplazarlo por otro producto.

### 4.2 Schema y linaje

Reusar `canonical_tick_v1` donde sea compatible; cualquier extensión consolidada requiere schema versionado y adaptación/test de lectores. No afirmar que el auditor de un contrato acepta automáticamente un archivo multicontrato.

Conservar, como mínimo:

- `instrument/root`, contrato exacto, vencimiento/identidad canónica.
- `ts_utc_ns` verificado y precisión real; `trade_date` basado en calendario.
- `price_ticks`, `bid_ticks`, `ask_ticks`, volumen y tipo de evento con unidades explícitas. Unknown no se imputa.
- `aggressor` y su método/procedencia; UNCLASSIFIED explícito.
- `source_id`, `source_file_sha256` o referencia inequívoca al manifest, `source_row`/offset original.
- Secuencia original preservada. Si se agrega secuencia consolidada, llamarla distinta: no fingir que es secuencia del exchange.
- `regime_id` y frontera de contrato; referencia al hash de selección y generación.

Orden estable: timestamp + orden original verificable en empates. No ordenar arbitrariamente por precio para obtener señales bonitas. Identidad de export diferente no autoriza duplicar el mismo evento reconstruido: adjudicar solapamientos por procedencia.

### 4.3 Política causal de selección y liquidez

Congelar `liquidity_policy.json` **antes de nuevos outcomes**. Incluir por activo:

- Universo de vencimientos reales y challengers; expiración y período operativo permitido.
- Calendario, cutoff/as-of y sesión anterior verificada.
- `min_previous_session_volume` en cantidad negociada real, no número de ticks.
- `max_previous_session_spread_p99_ticks`; definición de muestreo temporal y población de quotes. Un p99 por fila no equivale a p99 ponderado por tiempo: declarar el elegido.
- Completitud, integridad y procedencia exigidas; límites para datos quote desconocidos.
- Regla de desempate determinista, roll monotónico y comportamiento cerca del vencimiento.
- Si se desea persistencia/histéresis para evitar microcambios, es una **nueva política**: parámetros ex ante y tests; no introducirla silenciosamente en la v1 existente.
- Medidas de profundidad/tamaño cuando existan; si faltan, no certificar capacidad ni fills.

**No inventar números universales aquí.** Usar especificaciones del producto y análisis de calidad/liquidez pre-outcome para proponer límites. La revisión/mandato debe aprobarlos; si faltan, el agente prepara propuesta y deja el activo bloqueado para release certificada.

Para cada sesión S:

1. Determinar D-1 por el calendario aprobado, no restar un día ni elegir la última fecha que haya en un archivo.
2. Enumerar todos los contratos que podían competir según política antes de S.
3. Exigir captura completa/verificada en D-1 para cada input necesario. No excluir un challenger porque falta su archivo y así hacer ganar al disponible.
4. Medir volumen/spread D-1 en la fuente adjudicada, con estados desconocidos explícitos.
5. Aplicar política congelada; seleccionar entre elegibles. No mantener elegibilidad con todos los volúmenes en cero.
6. Emitir decisión con `decision_as_of`, D-1, candidatos/medidas, fuente/hash, contrato elegido, motivo y régimen.
7. Materializar S solo desde ese contrato. Si S está incompleta, no cambiar retrospectivamente de contrato para rescatarla: registrar/excluir según alcance.

**Límite honesto:** la regla causal identifica el contrato líquido con información disponible; no garantiza que sea el mayor volumen observado al final de cada sesión ni que toda hora tenga liquidez suficiente. Puede haber deterioro durante S: marcar o suspender según regla causal congelada, no sustituir con el ganador ex-post.

El primer día sin D-1 verificable es inelegible. Conseguir historia anterior suficiente para selección/warmup: no rellenar faltantes. El protocolo AVZVOL anterior pide warmup de 45 días en su alcance; no convertir eso en regla universal o contar 45 filas como 45 sesiones.

### 4.4 Precios y fronteras

- Sin back-adjustment, split adjustment, interpolación ni smooth roll en el archivo operativo de ticks.
- No mezclar simultáneamente dos contratos seleccionados en la misma sesión.
- Preservar saltos de precio reales de vencimiento; indicadores/zonas/historia se reinician y recalientan por contrato/régimen según protocolo.
- Una serie visual ajustada podría ser un derivado explícito, nunca reemplazo de este archivo ni input de fills/validación tick-exact.

## 5. Procedimiento de reparación, en orden

### Fase A — Custodia e inventario

1. Crear directorios privados separados: `originals/` read-only, `staging/`, `quarantine/`, `release/`, `evidence/`. No trabajar sobre los originales.
2. Inventariar todos los exports relevantes por activo/contrato/formato: SHA256, bytes, rango pedido, schema, timestamp declarado, versión de exporter/conversor, proveedor/conexión, logs y hashes.
3. Paginar inventarios Kaggle completos del alcance. Distinguir datasets de código, ticks, barras y artefactos; fijar versión real y ruta.
4. Reconciliar tabla de §3 con archivos actuales antes de pedir reexport. Registrar causas: export fallido, contrato ausente, carga incompleta, timezone, calendar closed, parcial, upstream unknown.
5. Mantener diario append-only de acciones e identidad de ejecución. No resetear journals de campañas anteriores ni reenviar un job ambiguo.

### Fase B — Timestamp, calendario y eventos anómalos

1. Revisar el código real del AddOn/conversor, incluyendo cómo pasa DateTime/DateTimeKind, configuración de conexión y unidad de 100 ns.
2. No asumir UTC por columna `ts`, `.utc` en filename o igualdad de timestamps local/UTC.
3. Validar eventos de control con procedencia independiente, aperturas/cierres normales, ambos lados de DST y horarios abreviados. La pauta de cierre semanal es diagnóstico, no identificación unívoca de zona.
4. Para ambiguos/inexistentes locales de DST, resolver con offset/log/orden original; no tomar silenciosamente el primer offset.
5. Reconstruir ES 2025-10-05 y comparación NQ en nueve sesiones. Probar separadamente hipótesis de eventos extra, día/zona incorrectos, mezcla de exports y conversor. Registrar evidencia que favorece/descarta cada una.
6. Si hay corrección justificada, conservar timestamp/raw original privado y emitir correspondencia/razón por fila. Si no puede adjudicarse, mantener cuarentena y alcance bloqueado.

### Fase C — Canonización por contrato y QA incremental

1. Convertir con parseo estricto, tick grid antes de redondear, instrumento correcto, unidades y evento quote/trade explícitos.
2. Validar nulos, finitud, positivos, bid≤ask, volumen, secuencia/identidad, orden original y precisión. Conservar locked/unclassified como advertencias.
3. Comparar nuevas fuentes con anteriores por esquema y por eventos ordenados: filas extra/faltantes, desplazamientos, precios/quotes/agresor/volumen, identidad de fuente. No elegir “más filas=mejor”.
4. Auditar solo archivos/código nuevos o cambiados. Reutilizar recibos SHA iguales y misma semántica; un calendario/transformación nuevo puede requerir revalidar sus derivados aunque el raw no cambie.
5. Reconciliar gaps según definición documentada. El filtro histórico que excluye una diferencia por su extremo derecho en 16–17 CT **no equivale** a borrar filas y recalcular gaps. Sustituir heurística por calendario revisado para nuevas medidas, mantener historia.

### Fase D — Cobertura, completitud y selección

1. Crear matriz rectangular contrato×sesión del universo requerido. Fuera de vida/operatividad debe haber razón, no archivo ausente silencioso.
2. Por fecha clasificar: `CLOSED_VERIFIED`, `OPEN_COMPLETE`, `OPEN_PARTIAL`, `MISSING_EXPORT`, `UPSTREAM_UNKNOWN`, `ZERO_TRADES_VERIFIED`. Son nombres propuestos, mapearlos a contratos reales del repo.
3. Cero operaciones solo con evidencia de captura completa y de actividad; “sin filas” no alcanza. Sesión completa no se determina por un mínimo genérico de ticks/minutos.
4. Comparar challengers D-1 y construir régimen sin lookahead. El roll ES/MGC viejo debe cambiar solo si lo justifican las reglas y los originales.
5. Congelar límites y selección revisados; producir exclusiones y UNKNOWN sin forzar completitud.

### Fase E — Consolidación eficiente

1. Construir `ASSET_ticks.parquet` por streaming/batches; no concatenar toda la historia en pandas.
2. Rowgroups delimitadas por sesión y contrato, estadísticas fiables e índice externo `session_index`. Una sesión puede ocupar varias rowgroups; ninguna debe mezclar permitidos y reservados.
3. Columnas de identidad diccionarizadas, tipos estables, ZSTD/rowgroups ajustados por benchmark acotado. No prometer speedup de mercado sin medir misma carga/salida.
4. Verificar conteos/volumen e identidad del producto frente a los tramos seleccionados; ningún evento del contrato no seleccionado, duplicado de intervalo o frontera omitida.
5. Escribir a path temporal, cerrar, hash/validar y promover atómicamente. El producto jamás se modifica in-place tras publicación.

### Fase F — Lectores, protección y caché

1. Inspeccionar **antes de cualquier payload** manifest externo, privacidad/licencia, schema, hash/bytes, calendario, selección, scope permitido y footer de TODOS los inputs.
2. No-read holdout desde **trade-date 2026-10-01**, frontera usada en las campañas CME: 2026-09-30T22:00:00Z/17:00 Chicago. Para otros productos exigir límites por calendario; nunca extender permisos. No computar precios/retornos/volumen del holdout para QA.
3. Si el original contiene rango reservado, metadatos no fiables o rowgroup mixta: **STOP**. Preparar export preholdout limitado en origen o partición segura sin deserializar payload reservado. Filtrar después de `read_table` no sirve.
4. Modificar el continuo actual para lectura segura/streaming y rutas exactas. El builder actual es una base de régimen, **no** un lector ya certificado no-read.
5. Hacer obligatorio el nuevo lector en autónomo/notebooks/CLI; no dejar fallback legacy de producción. Invocar gates existentes con evidencia verdadera, no fabricar certificados.
6. Cache por identidad de contenido/transformación. Resolver/generador y calendario versionados; no mezclar cache de release anterior.

### Fase G — Publicación privada y migración

1. Subir **nueva versión/release privada** de los archivos consolidados y metadatos; conservar todas las fuentes y versiones viejas. Elegir slug bajo convención actual; no borrar el dataset previo.
2. Verificar procesamiento completo, inventario paginado, descarga/versión exacta y SHA externos contra los originales producidos. `Ready` de Kaggle solo significa procesamiento.
3. Publicar aprobación de release/limitaciones revisadas por activo/ventana. Un actor no se autoaprueba con un JSON autofirmado.
4. Actualizar discovery/catalog/resolver/loader a los nuevos contratos **sin** editar pins de planes congelados. Una campaña nueva debe apuntar a la release nueva.
5. Regenerar barras de 1/30/60 s o M1 solo a partir de tramos seleccionados nuevos; comparar trades/volumen/identidad por sesión y frecuencia. Las barras viejas no quedan reparadas por referenciarlas.
6. Clasificar resultados anteriores por dependencias: `UNCHANGED_INPUTS`, `AFFECTED_SOURCE`, `AFFECTED_SELECTION`, `UNKNOWN_CUSTODY`; etiqueta/rectificación append-only, no borrar hipótesis/negativos ni recalcular P&L.
7. Entregar handoff del nuevo input al ResearchOps/Debian. No desplegar daemon/24×7 ni habilitar Brain writer como parte de esta tarea.

## 6. Herramientas existentes: reutilizar, no confiar ciegamente

Consultar las APIs reales del commit elegido y pinnearlo. **Este handoff no mergea main ni otro agente en PR117.**

| Herramienta | Uso | Advertencia |
| --- | --- | --- |
| `edgelab/data/nt8_contract.py` | Declaración de formato, zona y geometría | Zona declarada ≠ verificada. Revisar specs faltantes, incluidos MGC y RTY si no están en la versión elegida; no copiar GC sin registrar diferencias de contrato. |
| `edgelab/data/contract_regime.py` | `build_contract_regime`, `validate_contract_regime`, `assert_rows_follow_regime`, `assert_run_manifest_uses_regime` | Necesita calendario y volúmenes/completitud auténticos. No certifica que el input capturó el exchange. |
| `edgelab/data/continuous_contract.py` | Base de `build_continuous_series` | Lectura entera y fallback de path actual requieren reparación antes de archivos mixtos/grandes/no-read. |
| `edgelab/data/research_data_gate.py` | `require_research_eligibility` y comparación de challengers previos | Hash externo/certificado/límites deben venir de revisión real; `seal` no es firma/autenticación. |
| `edgelab/kaggle/research_access.py` | `require_requested_coverage`, `load_research_bars`, rechazo de NQ conocido | No levantar cuarentena quitando una entrada. Nuevo archivo/release requiere adjudicación y gates completos; hoy protege barras, adaptar consumidor de ticks con igual autoridad. |
| `tools/audit_kaggle_raw_ticks.py` | QA estructural canonical 1 por contrato | `--contract` asume contrato concreto. Auditar staging por contrato y crear auditor final multicontrato; no pasar CONT sintético para evadir identidad. Exit 0 no habilita research. |
| `tools/audit_kaggle_aggregates.py`, `tools/audit_kaggle_coverage.py` | Reconciliación y cobertura | Ausencia de barra no prueba cero ni calendario; outcomes/fills fuera de alcance. |
| `tools/data_inventory.py`, `tools/data_catalog_build.py`, `tools/data_find.py` | Inventario/catalog/descubrimiento en ramas donde existan | Confirmar flags/versión; revisar completitud, paginación y no sustituir certificación por inventario. |
| `docs/data_catalog/edgelab_data.py`, `tools/kaggle_launch.py` | Helper operativo actual | v16 solo presencia/tamaño, fallbacks/no-op/cache por tamaño y vías sin check. No única puerta autónoma. |

### Comando existente y límites

Para una fuente staging de un contrato, solo después del preflight global:

```bash
python tools/audit_kaggle_raw_ticks.py \
  --path "$PERMITTED_CONTRACT_FILE" \
  --expected-sha256 "$REVIEWED_SHA256" \
  --expected-bytes "$REVIEWED_BYTES" \
  --expected-rows "$REVIEWED_ROWS" \
  --instrument "$ROOT" \
  --contract "$ACTUAL_CONTRACT" \
  --include-clock-diagnostics \
  --out-dir "$NEW_EVIDENCE_DIR"
```

El CLI escribe `private_session_totals.json`: mantenerlo **privado**, nunca adjuntarlo al repo. Usar directorio nuevo; no sobrescribir evidencia. La banda 16–17 CT es diagnóstico, no calendario completo.

Tests existentes para reutilizar, según el checkout:

```bash
python -m unittest discover -s tests/data -p 'test_contract_regime.py' -v
python -m unittest discover -s tests/data -p 'test_continuous_contract.py' -v
python -m unittest discover -s tests/data -p 'test_prior_challengers.py' -v
python -m unittest discover -s tests/data -p 'test_research_data_gate.py' -v
python -m unittest discover -s tests/infra -p 'test_kaggle_raw_ticks.py' -v
python -m unittest discover -s tests/infra -p 'test_kaggle_data_quality.py' -v
python -m unittest discover -s tests/infra -p 'test_kaggle_coverage.py' -v
python -m unittest discover -s tests/infra -p 'test_kaggle_discovery.py' -v
```

El agente debe verificar el framework de cada test y las dependencias del commit: si algún archivo usa pytest, ejecutarlo con pytest, no contarlo como PASS porque unittest descubrió 0 tests. Esos comandos son guía de rutas existentes, **no tests ejecutados en esta entrega**. Complementar CI/install/wheel/navegación según instrucciones del repo.

## 7. Matriz mínima de pruebas nuevas

Todas sintéticas primero; luego QA acotada de inputs nuevos. Un negativo debe demostrar rechazo **antes** de payload, no solo excepción al final.

| Área | Casos obligatorios |
| --- | --- |
| Tiempo | Dos cambios DST, local ambiguo/inexistente, fecha CME distinta de fecha UTC, feriado/cierre corto, zona incorrecta, caso ES dominical y diferencias NQ reducidas a fixtures sin precios reales |
| Fuentes | Dos exports con namespace distinto que se solapan; mismo timestamp con eventos legítimos; duplicado de identidad; cambio de agresor/quote; bytes iguales/hash distinto |
| Cobertura | Missing ≠ zero; contrato challenger ausente; D-1 incompleto; sesión cerrada verificada; día actual parcial; calendario contradictorio |
| Liquidez | Todos los volúmenes cero/NaN/inf; mayor volumen relativo bajo el límite; spread excesivo; límites ausentes; empate; expiración y conflicto de fuente |
| Causalidad | Mutar datos futuros no altera decisiones pasadas; mutar outcomes no cambia selección; usar S para elegir S rechazado; primer día sin D-1; challenger omitido rechazado |
| Consolidación | Un root por archivo; micro/estándar mezclados rechazados; contrato exacto por fecha; intervalos sin solapamiento; ninguna fila de contrato no elegido; orden estable y reconciliación de conteos/volumen |
| Fronteras | Reset de régimen/lookbacks; no back-adjustment; salto real conservado; warmup insuficiente declarado |
| Lectura | Manifiesto vacío/ausente, versión equivocada, SHA incorrecto, mismo tamaño; fallback de basename, raíz duplicada, traversal; rowgroup mixta/sin estadísticas; espía prueba cero lecturas reservadas |
| Cache | Mismo tamaño/distinto contenido falla/hace miss; calendario/schema/código distinto invalida; cache corrupto rechazado |
| Publicación | Inventario multipágina, lectura de versión exacta, hashes congruentes, privacidad, release inmutable, snapshot viejo conservado |

## 8. Entregables y definición de “terminado”

### Entregables del agente local

1. `repair_inventory` con todos los activos/contratos/fuentes del alcance, hashes y estado actual de §3.
2. `issue_resolution_log`: D01..D23, evidencia, estado, razón y dependencias afectadas. Estados propuestos: `OPEN`, `RESOLVED_WITH_EVIDENCE`, `NOT_APPLICABLE`, `BLOCKED_UPSTREAM`, `HISTORICAL_ALREADY_RESOLVED`.
3. Contratos de timestamp/schema y calendario versionados, adjudicación ES/NQ y otros conflictos.
4. `liquidity_policy` propuesta/congelada/revisada; schedule D-1 reproducible con todos los challengers.
5. **Un Parquet de ticks líquido por activo aprobado**, manifest de SHA/bytes/rows, sesiones/regímenes y datos permitidos.
6. QA incremental de fuentes nuevas + QA final del consolidado, pruebas negativas/causalidad/no-read, perf/paridad exacta de transformaciones.
7. Release privada Kaggle nueva y verificada; nuevo discovery/resolver y lectores seguros; migración de caches/derivados.
8. Reporte público sin mercado privado: qué se arregló, qué queda abierto, ventanas excluidas, hashes, pruebas y ubicación de archivos; handoff de consumo.

### Criterios por activo

No exigir aprobar todos los activos para entregar uno correcto. Pero **no marcar una release completa si algunos siguen bloqueados**.

- [ ] Scope/rango/contratos explícitos y privacidad/licencia correctos.
- [ ] Timezone/calendar/procedencia verificadas o exclusión justificada visible.
- [ ] Sin conflictos sin resolver en los inputs seleccionados/challengers necesarios.
- [ ] D-1 completo y medidas reales, límites revisados y sin lookahead.
- [ ] Contrato real por fila/régimen, no ajustes ni mezcla de productos.
- [ ] Censo de fechas permitidas/cerradas/missing/partial/UNKNOWN publicado en metadatos privados; no falsa completitud.
- [ ] Guards prepayload y holdout; lectura acotada/streaming y cache content-addressed.
- [ ] QA estructural/final y tests negativos PASS con alcance real y hashes.
- [ ] Publicación privada/versión exacta/SHA verificados; producto y historia inmutables.
- [ ] Revisión explícita de elegibilidad por activo/ventana; certificado no autoaprobado.

**Si falta una condición:** entregar el archivo como `CANDIDATE_NOT_RESEARCH_APPROVED` o no materializarlo, con bloqueo explícito. No renombrarlo “canonical/liquid” para eludir la condición.

### Criterios de revisión del informe

No declarar “todos los problemas solucionados” si solo se arregló transporte; “liquidez” sin límites; “continuidad exchange” por secuencia local; “sin holdout” si se leyó y filtró; “paridad 100%” desde supuesto; “autonomía 24/7” desde un notebook. No calcular P&L ni buscar alpha para validar datos.

## 9. Orden recomendado para obtener resultados útiles rápido

1. **Primero:** inventario/hashes local y reconciliación de puntos ya cerrados. No solicitar todos los exports de nuevo.
2. **En paralelo por familia:** adjudicar ES/NQ prioritarios; verificar contrato/fechas faltantes de GC/MGC y otros; calendar/timezone reutilizables.
3. **Antes de consolidar:** guard prepayload, hashes/mount exacto y policy D-1. Evita generar un archivo enorme con una selección incorrecta.
4. **Primera entrega:** un activo y ventana ya resueltos end-to-end, con un archivo, QA final y lector seguro. Ese piloto valida la maquinaria, no certifica los demás activos.
5. **Escalar:** misma pipeline/contratos de control al resto; QA solo del delta y del producto final, cache verificada y lecturas por índice.
6. **Por último:** aprobación/release/migración y recálculo selectivo de derivados afectados. Research nuevo bajo planes nuevos; campañas congeladas mantienen pins.

El objetivo no es acumular auditorías: es eliminar causas específicas, generar un producto inequívoco y evitar que cada corrida tenga que redescubrir su calidad.
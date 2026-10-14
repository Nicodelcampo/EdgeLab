# Auditoría independiente de la release líquida 20261014

## Dictamen

**Avance útil y conservable, pero todavía no es una base canónica aprobada para research.**
La publicación v3 tiene la estructura pedida —un archivo por activo— y su inventario
coincide con el manifiesto. Encontramos defectos reproducibles de causalidad y de
custodia en el código del productor. **No está demostrado que los Parquet publicados
contengan holdout, ni se cuantificó todavía cuántas decisiones reales cambian.**

Estado de esta auditoría: `PARTIAL_CODE_AND_INVENTORY_AUDITED_PAYLOAD_PENDING`.
No convertir este informe en un certificado de integridad de los ticks.

### Qué se comprobó directamente

- Leído el adjunto `EdgeLab Estado 14 oct.md`.
- Leído el informe del productor y revisado su código en
  `data/liquid-release-20261014`, commit
  `705229bc67d6eb4ff3e0762b0bbd2d80da6bd8d9`.
- Consultado Kaggle: dataset privado
  `nicolasbuttaro/edgelab-liquid-ticks-20261014`, ID `12574934`, versión 3.
  Inventario vuelto a consultar con la versión fijada explícitamente.
- **31 archivos; 14 Parquet de datos; 11.066.425.154 bytes listados.**
  Nombres y tamaños de los 31 coinciden exactamente con el manifiesto y su propio tamaño.
  Esto verifica inventario, no hashes del contenido de los 14 archivos.
- Descargados al host únicamente README y manifiesto, no ticks ni sidecars granulares.
  README: SHA-256
  `c6bde6573c18000c1e8497aa31c397ec9632759ef7a804764d1131609fdc2b68`,
  coincidente con el manifiesto. Manifiesto v3: SHA-256
  `cfbe2a488e62ffbae6bcfbf9e0ce5d76fb38b219a4255eec12ed30ddc8f842c7`.
- **38 pruebas originales del productor pasan** en una copia aislada.
  **11 probes sintéticos independientes pasan sus aserciones de reproducción**
  de defectos y controles. No son 11 defectos: incluyen controles negativos.
- El manifiesto declara `research_allowed=false`, `promotion_allowed=false`,
  `liquidity_policy_approved=false`, `CANDIDATE_NOT_RESEARCH_APPROVED`.
  La release no se aprobó ni se modificó.

El manifiesto declara 1.395.272.655 filas y 3.854 sesiones-activo en total.
**Son sumas de declaraciones, no un recuento independiente de los ticks.**
Una sesión-activo no equivale a una fecha independiente entre activos.

### Qué impidió completar el examen del contenido

La solicitud MCP de descarga del dataset completo fijado en v3 fue bloqueada
por el revisor automático de seguridad. Se pidió autorización explícita al usuario
antes de cualquier reintento. No se recurrió a otra vía de descarga ni se lanzó
un notebook para eludir ese bloqueo.

La intención era descargar y auditar **dentro de Kaggle**. Esa restricción se mantiene:
los ticks y los sidecars granulares nunca se descargan al host. No se leyó payload
real ni holdout, no se calculó P&L, no se inició una nueva corrida de research.

## Hallazgos nuevos, con alcance y prioridad

### LRA-01 — P0: la selección no es invariante a agregar datos futuros

Archivo: `edgelab/data/liquid_release/selection.py`, rama auditada.

El universo se obtiene del censo completo. Cuando falta un competidor en D-1,
se decide si su ausencia es `UNKNOWN` usando
`lo.min() <= D1 <= lo.max()`. El máximo incluye fechas posteriores a S.

Reproducción con política fija y calendario fijo:

1. A tiene volumen 5.000 en D-1; B tuvo 4.000 antes, pero falta en D-1.
2. Sin una fila posterior de B, S=`20260107` queda `SELECTED`.
3. Se agrega **solo** una fila de B en `20260108`, sin tocar datos anteriores.
4. La misma S pasa a `UNDETERMINED`.

Esto invalida la afirmación fuerte «nada de S ni posterior interviene».
El test original muta valores futuros, pero no disponibilidad/universo futuros.
No demuestra por sí solo un sesgo rentable ni una decisión afectada en la release real.

**Reparación:** universo de contratos elegibles a fecha de decisión, con calendario
de existencia y matriz de captura explícitos; ausencia desconocida nunca inferida
del máximo futuro observado. Reprobar prefijos y mutaciones de disponibilidad,
no solo de volumen. Medir el delta real de sesiones/contratos antes de regenerar.

### LRA-02 — P1: un spread desconocido pasa el umbral de liquidez

`selection.py` considera elegible un spread `None` o `NaN`, además del que
cumple el máximo. Ambos casos sintéticos se seleccionan; un spread conocido
de 9 ticks sí queda excluido con máximo 4.

No está cuantificado cuántas decisiones publicadas tienen este problema.
**Reparación:** spread desconocido = liquidez no demostrada, o excepción de
instrumento explícita y aprobada; no convertir ausencia de evidencia en aprobación.
Validar también finitud y dominio de los parámetros de política.

### LRA-03 — P1, defecto latente de interfaz: `MISSING` no bloquea como `UNKNOWN`

Aunque el código identifica ambas coberturas como bloqueadas, luego solo
`UNKNOWN` interviene en el bloqueo final. Un competidor históricamente significativo
con `MISSING` permite seleccionar al disponible; con `UNKNOWN` detiene la decisión.

**Alcance:** `plan.asset_frame` actual asigna `OK` a las filas disponibles.
No se afirma que `MISSING` haya llegado al selector en esta publicación.
Es una brecha del contrato de la función, no un recuento de errores reales.

**Reparación:** semántica exhaustiva de cada estado de captura y pruebas por estado.
La evidencia «no existe contrato» debe distinguirse de «no tengo su export».
Ordenar explícitamente la historia antes de aplicar `tail(lookback)` y no
tratar historia ausente como prueba de volumen cero.

### LRA-04 — P0 de custodia: el lector solo protege `trade_date`

`release_reader.select_row_groups` no inspecciona estadísticas de `ts_utc_ns`.
Un Parquet sintético con `trade_date=20260930` y timestamp posterior al cutoff
es leído. El checksum correcto no salva una etiqueta de fecha equivocada.

**No es prueba de holdout en los archivos reales.**

**Reparación:** antes de leer cualquier columna de mercado, verificar esquema,
nulls y estadísticas completas de ambos relojes para todos los row groups;
rechazar timestamp reservado, fecha reservada, estadísticas ausentes/inconsistentes.
Validar además la correspondencia timestamp↔sesión con calendario por instrumento.
Una guarda de footer no prueba que el footer sea verdadero: la coherencia del
payload permitido se verifica después, sin usarlo para justificar una lectura reservada.

### LRA-05 — P1 de integración: checksum no equivale a admisión

El lector acepta un manifiesto candidato con `research_allowed=false` y
`liquidity_policy_approved=false`; tampoco valida `metadata_files`.
La prueba incluye metadatos listados pero inexistentes y la carga sigue pasando.

Leer una candidata **con propósito de auditoría** puede ser legítimo. El problema
es usar el mismo lector como puerta suficiente para research autónomo.

**Reparación:** separar custodia/integridad de admisión. Auditoría explícita puede
examinar una candidata; research debe exigir aprobación externa vinculada al hash
del manifiesto, versión del dataset, política, calendario y fuentes. Verificar
los sidecars usados antes de confiar en ellos. `verify_hash=False` no debe ser un
atajo disponible para jobs de research.

### LRA-06 — P0 de custodia: el verificador detecta el holdout después de leerlo

En `tools/verify_release.py`, `verify_asset` llama a `read_row_group` antes
de chequear timestamp y fecha de holdout. Incluso ante problemas de estadísticas
anota una advertencia y continúa hacia la lectura.

Reproducción sintética: row group reservado leído una vez; resultado posteriormente
rechazado. Rechazar después de deserializar no cumple «no leer holdout».

**Reparación:** preflight global anterior al primer payload, con STOP real.
No correr este verificador sin corregir contra una entrada no prevalidada.

## Límites adicionales confirmados por código/documentación

| Área | Estado observado | Consecuencia / acción |
|---|---|---|
| Política de liquidez | `plan.propose_policy` calibra umbrales con toda la muestra pre-holdout | La selección posterior con constantes no vuelve prospectivo el ajuste histórico. Separar fit y evaluación, o walk-forward; aprobación humana no elimina ese uso del futuro. |
| Calendario | Derivado de actividad; referencia con vecinos anteriores y posteriores; `cls_last` usa toda la muestra | Útil como diagnóstico retrospectivo, no evidencia oficial. Conseguir calendario histórico por producto y conservar estado desconocido ante apagón común. |
| Cobertura | Falta matriz rectangular contrato×sesión de captura | No alcanza observar que «hay algún archivo». Recuperar P0 y probar ausencia vs mercado cerrado. |
| Procedencia del build | Manifiesto: `repo_commit=1ea3e2a1196b8d09045feff3b996d5bbb557a99e`, `tree_dirty_at_finalize=true` | El HEAD posterior auditado no identifica exactamente el código ejecutado. Recuperar bundle/diff y hashes de fuentes/configuración del build; no inventarlos retroactivamente. |
| Huso horario | Ajuste empírico al horario, anomalías e insuficiencia de evidencia admitidas | No es una atestación independiente de reloj/feed. Obtener logs/configuración NT8 y evidencia externa; calendario propio de MBT. |
| Fuente por sesión | Gana la de más minutos activos/menor hueco de la sesión completa | Adjudicación retrospectiva declarable, no prueba automática de integridad ni disponibilidad en tiempo real. Versionar y medir sensibilidad de conflictos relevantes. |
| Filas/quotes | Escritor valida grilla de last; bid/ask positivos se redondean | No asumir grilla de quotes probada por validar solo last. Medir off-grid/crossed/locked/unknown, cotejar agresor con semántica explícita. |
| Secuencia | `release_row` es orden consolidado y `source_row` orden del archivo | No son secuencia del exchange. No afirmar reconstrucción de eventos o microestructura exacta sin evidencia adicional. |
| Consumidores | Lector nuevo opt-in; legacy sigue presente | Inventariar rutas de lectura y bloquear mezcla con datos cuarentenados o agregados viejos. |
| Regímenes/warmup | Columna disponible, consumidores no certificados por este examen | Resetear estado en roll, definir warmup causal y excluir cruces cuando corresponda. |
| Licencia | Dataset privado; licencia Kaggle “Other”; derechos pendientes | Privado no prueba autorización de uso. Documentar permisos reales; no redistribuir. |
| Rendimiento | `read_asset` valida hashes de todos los activos en cada llamada y materializa el rango pedido | Cachear recibo de integridad por identidad inmutable; streaming de columnas/fechas necesarias. No acelerar desactivando controles. |

Los faltantes ≈321 P0 / ≈275 P1 son **del informe del productor**, no un recuento
independiente de esta auditoría. Lo mismo aplica a 15 bloques/532.441 ticks,
701 conflictos y los resultados de racimos del adjunto. No se revalidaron acá.
Tampoco se auditó el inventario completo de los 41 datasets o 248 kernels.

## Qué conserva valor y para qué sirve hoy

- La estructura consolidada, `source_id`, `source_row`, contrato y régimen son una
  mejora material de trazabilidad frente a archivos ambiguos.
- Es razonable conservar la v3 inmutable como **candidata para saneamiento y auditoría**.
- No hay base aquí para borrar los datos ni para declarar inválidos todos los estudios.
  Tampoco para promover esta release automáticamente o llamar a sus resultados
  «efecto real» confirmado: el adjunto no sustituye un examen del diseño experimental.
- Primero determinar qué decisiones y entradas cambian. Recalcular solo los
  artefactos afectados, con hashes y linaje; no repetir por rutina todo el histórico.

## Handoff ejecutable al agente local

1. **Preservar v3 y su evidencia.** Guardar manifiesto exacto y hashes de origen.
   No editar archivos publicados en sitio ni borrar datasets anteriores.
2. **Cerrar custodia primero:** corregir lector y verificador con tests espía
   `payload_reads == 0` ante cualquiera de los dos relojes reservados, footer
   ausente, grupo mixto o esquema inválido. Los datos sintéticos reservados no son mercado.
3. **Cerrar selección causal:** universo/captura as-of, pruebas de invariancia
   frente a agregar/quitar futuros archivos/contratos, tratamiento explícito de
   `MISSING`/`UNKNOWN`/sin historia/spread desconocido.
4. **Recuperar censo completo y código del build.** Los candidatos publicados por
   decisión no contienen necesariamente los contratos omitidos por el propio bug:
   ese sidecar por sí solo no alcanza para medir LRA-01. Hace falta el censo/captura
   previo a la selección, disponible con exports locales.
5. **Recalibración y calendario:** fijar período de entrenamiento del selector;
   conseguir calendario oficial por producto; mantener desconocidos sin rellenarlos
   como ceros ni saltarlos como feriados.
6. **Cuantificar antes de regenerar:** por activo, contar cambios de estado,
   contrato, fuente, sesión y filas; registrar hashes de inputs afectados.
   Emitir agregados, no ticks. Medir también las excepciones de spread y cobertura.
7. **Completar exports priorizados:** resolver P0 que efectivamente cambia la
   cobertura; después P1 de procedencia. Un caso sin fuente original conserva ese
   nivel de garantía explícito, no se convierte en “original verificado”.
8. **Emitir una versión nueva candidata**, con código exacto reproducible,
   manifiesto/sidecars completos y hashes externos. No autoaprobar licencia,
   política ni calendario.
9. **Auditar una sola vez los bytes cambiados dentro de Kaggle:** pin de versión y
   manifiesto; descarga privada; hashes de todos los archivos; preflight global
   de ambos relojes; streaming acotado; reconciliar conteos con decisiones,
   índice, fuentes y regímenes. Registrar checkpoints por activo.
   Si la identidad ya tiene un recibo independiente válido, reutilizarlo, no rehash
   por cada combinación de indicadores.
10. **Solo después, admisión explícita para research**, invalidación selectiva
    de cachés y reproducción de los análisis afectados. P&L y promoción siguen cerrados.

La ejecución remota de esa auditoría queda pendiente de la autorización solicitada
por el bloqueo de seguridad; no generar recibos como si se hubiera ejecutado.

## Reproducción y archivos de evidencia

- `docs/infra/LIQUID_RELEASE_INDEPENDENT_AUDIT_20261014.json`: hechos observados,
  hashes documentales, alcance no verificado y estado del bloqueo.
- `docs/infra/LIQUID_RELEASE_SYNTHETIC_PROBES_20261014.json`: 11 casos/control,
  hashes de los tres archivos de código ejercitados.
- `tools/research_ops/audits/probe_liquid_release_candidate.py`: reproducción
  exclusivamente sintética. No importar código de una descarga no confiable.

Preparar una copia aislada del commit auditado, no cambiar de rama un working tree
sucio:

```bash
git archive 705229bc67d6eb4ff3e0762b0bbd2d80da6bd8d9 \
  edgelab/data tests/data tools/verify_release.py | tar -x -C /ruta/copia-aislada
OPENBLAS_NUM_THREADS=1 PYTHONPATH=/ruta/copia-aislada \
  python -m unittest discover -s /ruta/copia-aislada/tests/data \
  -p 'test_liquid_release_*.py' -v
OPENBLAS_NUM_THREADS=1 python tools/research_ops/audits/probe_liquid_release_candidate.py \
  --source-root /ruta/copia-aislada --out /ruta/evidencia-sintetica.json
```

Dependencias: pandas, numpy, pyarrow. La ejecución registrada se hizo con
38 tests originales de los siete módulos de tests de liquid_release.
El primer comando crea una exportación aislada; la ruta debe existir.
Los probes afirman el comportamiento defectuoso conocido de ese commit:
**después de corregirlo deben cambiar por tests de la invariancia deseada**.
Su verde actual no aprueba la release.

## Aprendizajes para el sistema autónomo (propuesta, no escritura canónica)

- D-1 necesita invariancia de **disponibilidad**, universo y transformaciones, no
  solo mutación de valores futuros.
- `PASS` de checksums prueba identidad de bytes, no calidad de fuentes, causalidad
  ni autorización de uso.
- Validar holdout después de leerlo no es un control de custodia.
- Una auditoría de datos no habilita automáticamente outcomes, P&L o promoción.
- Optimizar con recibos inmutables y ejecución incremental; nunca suprimiendo
  controles o convirtiendo una incertidumbre en una aprobación.
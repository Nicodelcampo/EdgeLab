# Release líquida v4: revisión independiente y resguardo de borrado

## Resultado

**La v4 está publicada y contiene reparaciones comprobables. La revisión de código,
inventario y recibos pasa; la auditoría independiente del contenido real en Kaggle
sigue pendiente. No se borró ningún dataset.**

No interpretar este informe como un PASS de los ticks o una aprobación para research.
La candidata continúa con `research_allowed=false`, `promotion_allowed=false` y
`liquidity_policy_approved=false`.

## Identidad observada

- Dataset privado: `nicolasbuttaro/edgelab-liquid-ticks-20261014`, ID `12574934`.
- Versión **4**, estado Kaggle **Ready**; inventario consultado con versión fijada.
- Storage version ID: `20729690` — no confundir con v3 / `20709574`.
- `release_id`: `liquid_release_20261014_v4`.
- Manifiesto, 7.821 bytes, SHA-256
  `db9c42cdb714634b131fc8ff886cda67771bea6070d27c0e56e2d2fd6eb14ce5`.
- Código declarado y revisado:
  `7afe22d49295dbf8c3c51f5ba80c0b22ff45795d`,
  `tree_dirty_at_finalize=false`.

Esto corrige el problema de identificación de un build sucio de v3. Que el
manifiesto declare un build limpio no atestigua por sí solo cada operación del
productor: se verificó la declaración y que los archivos de código examinados
coincidan por SHA con ese commit.

## Qué se verificó directamente

1. **31 nombres y tamaños** de Kaggle coinciden exactamente con el manifiesto:
   14 Parquet de mercado y sus documentos/sidecars. Total listado: 11.044.108.246 bytes.
2. Se descargaron y verificaron **solo cuatro archivos documentales/agregados**:
   `release_manifest.json`, `README_AGENTES.md`, `metadata/verification.json`
   y `metadata/quality_summary.json`. Los tres últimos coinciden en tamaño y SHA
   con el manifiesto; el manifiesto queda identificado por el hash externo anterior.
3. **53 tests del productor pasan**, en una copia aislada de su commit.
4. **8 grupos de pruebas independientes pasan**, con datos enteramente sintéticos:
   - Agregar disponibilidad futura ya no altera la decisión anterior del caso
     que reproducía LRA-01.
   - Spread `None`/`NaN` no es elegible sin excepción.
   - `MISSING` y `UNKNOWN` bloquean al competidor significativo del caso de prueba.
   - Valores posteriores a las primeras 80 sesiones no cambian la política calibrada.
   - Ambos relojes reservados detienen al lector con **cero lecturas de payload**.
   - Propósito obligatorio y research no aprobado detenido; auditoría permitida.
   - Metadato listado pero inexistente rechazado.
   - Verificador detenido antes de leer payload reservado o consultar el censo.

El archivo `LIQUID_RELEASE_V4_REPAIR_CHECKS_20261014.json` contiene las pruebas y
los hashes de los cuatro módulos ejercitados. Los 53 tests y los 8 grupos no son
sesiones reales ni una auditoría de 1.394 millones de filas.

## Cambios de contenido declarados, no rehasheados independientemente

Los SHA del manifiesto cambian en **GC, MGC, MNQ, MYM y NQ**. Los otros nueve
declaran el mismo SHA que v3. No alcanza comparar tamaños para inferir igualdad:
esta comparación se hizo sobre los SHA declarados.

| Activo cambiado | Sesiones declaradas v3 | Sesiones declaradas v4 |
|---|---:|---:|
| GC | 289 | 273 |
| MGC | 222 | 221 |
| MNQ | 285 | 286 |
| MYM | 227 | 228 |
| NQ | 292 | 291 |

El total declarado pasa de **3.854 a 3.838 sesiones-activo**; no significa que haya
16 errores de datos. La política de selección cambió y puede excluir sesiones
válidas para ese propósito. El nuevo manifiesto declara **1.394.017.834 filas**.
No son recuentos independientes de este auditor.

El productor informa que el arreglo aislado de disponibilidad futura no cambió
contratos/sesiones seleccionadas, sino etiquetas de exclusión, y que el cambio de
calibración produjo 19 salidas y 3 entradas. Ese desglose requiere su censo previo
a la selección; **no se revalidó desde los ticks ni desde el censo en este examen**.
El saldo de 16 sesiones menos sí concuerda aritméticamente con los manifiestos.

## Qué dice realmente el recibo publicado

`metadata/verification.json`, cuya identidad documental se verificó:

- Tiene 14 entradas `ok=true`, sin problemas declarados.
- **5 entradas son verificaciones nuevas del productor**:
  GC, MGC, MNQ, MYM, NQ.
- **9 entradas están heredadas de la verificación v3** mediante igualdad del SHA
  declarado: 6B, 6E, 6J, ES, MBT, MES, RTY, YM, ZB.
- Sus filas y sesiones coinciden exactamente, activo por activo, con el manifiesto.

No llamarlo «14 activos auditados de nuevo». La herencia puede ahorrar trabajo,
pero necesita identidad de los bytes y un recibo anterior válido para el alcance
reutilizado. Igualdad del archivo de ticks no demuestra por sí sola igualdad de
calendario, política, decisiones o expectativas del nuevo índice de sesiones.
Una auditoría nueva debe cotejar esos enlaces aunque reutilice un chequeo físico.

El resumen publicado declara 3.563 sesiones con origen textual verificado por el
productor y 275 con origen derivado sin original disponible. Sus sumas coinciden
con las 3.838 seleccionadas. Esto no eleva las 275 a garantía de original.

## Límites que siguen abiertos

- **Payload real:** no se ejecutó desde este agente una auditoría de los Parquet
  dentro de Kaggle. Tampoco se verificaron independientemente sus 14 SHA reales.
  El bloqueo previo de preparación/ejecución no quedó resuelto por publicar v4;
  no se reintentó la acción bloqueada mediante una vía alternativa.
- Calendario oficial por producto, matriz rectangular de captura y faltantes.
- Reloj/feed y logs NT8: schedule-fit empírico no es atestación externa.
- Semántica del agresor y grilla de quotes originales; enteros consolidados no
  prueban por sí solos la grilla previa al redondeo.
- Licencia y política de liquidez no aprobadas.
- La ventana inicial de 80 sesiones sigue in-sample. Debe quedar separada de
  evaluación prospectiva. El calendario derivado aún usa contexto posterior:
  corregir el selector no vuelve prospectivo todo el pipeline.
- El modo `provisional_research` admite candidatas explícitamente. El chequeo
  independiente lo confirmó; el nombre del modo o un rótulo PROVISIONAL **no son
  autorización de un job**, de P&L o de promoción. Hace falta la admisión externa
  del experimento y una aprobación confiable, no solo un JSON escribible.
- El preflight nuevo protege ambos relojes por archivo. Para una auditoría global
  de 14 activos, ejecutar el preflight de todos antes del primer payload de mercado.

## Limpieza: no ejecutar la lista propuesta tal cual

Se revisó `docs/infra/KAGGLE_BORRADO_CANDIDATOS_20261014.md` del productor. Declara
que **no se revisaron las dependencias de los 248 kernels históricos**. Por tanto,
esa lista no satisface todavía la condición de borrado seguro.

### Preservar especialmente

- `edgelab-nq-nt8-2026q3-l2ctx`.
- `edgelab-l2-gc-bookmap-audit-20260921`.

El propio inventario del productor los describe como contexto/auditoría **L2**.
La release v4 consolida ticks y no demuestra que reemplace ese contenido. Borrar
un dataset completo porque algunos archivos de ticks estén reemplazados puede
eliminar información única. No se inspeccionaron sus archivos aquí; mientras no
haya una equivalencia de contenido demostrada, conservar ambos.

Además, una selección de **un contrato líquido por sesión no es una copia sin
pérdida del raw multicontrato**. No sustituye automáticamente los no líderes,
sesiones excluidas, formatos originales ni evidencia de anomalías. Conservar
la única copia original y cualquier evidencia necesaria para reconstruir el build.

Los datasets en cuarentena o los agregados incorrectos no deben consumirse en
research, pero «no consumir» no equivale a «borrar sin archivo de respaldo».
Los spot/CFD pertenecen a otro mercado: no son duplicados de futuros CME por
compartir un subyacente.

### Condiciones para pasar de candidato de limpieza a eliminación

1. Auditoría independiente de v4 completada dentro de Kaggle, con recibo ligado
   al manifiesto anterior y sin lectura de holdout.
2. Mapa dataset/versión/archivo → kernels y artefactos; incluir referencias por
   URL y código, no solo mounts declarados. Cero matches de una búsqueda limitada
   no prueba ausencia de dependencias.
3. Respaldo privado verificado por hashes de cualquier original o evidencia única;
   ubicación y restauración probadas, sin exportar mercado a este sandbox.
4. Equivalencia documentada por archivo y alcance; separar ticks de L2 antes de
   proponer eliminar un contenedor completo.
5. Lista final exacta con motivo, dependencias resueltas y respaldo. No ampliar la
   autorización del usuario a pérdidas de reproducibilidad no explicitadas.
6. El MCP actual no expone borrado de datasets. No se ejecutó ni se validó el
   comando CLI sugerido por el productor.

**Listos para eliminación automática en este examen: ninguno.**
Esto no revoca la autorización condicional del usuario: sus condiciones aún
no están verificadas.

## Continuación sin repetir trabajo

- No lanzar el protocolo ni las URLs de v3. La v4 tiene otro manifiesto,
  storage version y cinco archivos de mercado diferentes.
- Conservar el auditor independiente y sus pruebas; preparar una identidad de job
  nueva y acotada solo cuando se resuelva el bloqueo de ejecución.
- Aprovechar los recibos por identidad/alcance que realmente puedan validarse:
  no hace falta regenerar indicadores ni repetir campañas para auditar datos.
- Descargar/leer mercado y sidecars granulares solo en Kaggle; exportar únicamente
  recibos y conteos agregados. No abrir outcomes ni P&L.
- Hacer el análisis de dependencias antes de cualquier eliminación; la propuesta
  actual del productor es una lista de candidatos, no una orden ejecutable segura.

## Archivos de esta revisión

- `docs/infra/LIQUID_RELEASE_V4_INDEPENDENT_REVIEW_20261014.json`.
- `docs/infra/LIQUID_RELEASE_V4_REPAIR_CHECKS_20261014.json`.
- `tools/research_ops/audits/revalidate_liquid_release_v4.py`.

Reproducción sintética en proceso limpio:

```bash
OPENBLAS_NUM_THREADS=1 python tools/research_ops/audits/revalidate_liquid_release_v4.py \
  --source-root /ruta/copia-aislada-del-commit-7afe22d4 \
  --out /ruta/evidencia-v4.json
```

La copia debe corresponder al commit completo anterior e incluir `tools/verify_release.py`.
No copiar datos de mercado: estas pruebas solo generan fixtures sintéticos.
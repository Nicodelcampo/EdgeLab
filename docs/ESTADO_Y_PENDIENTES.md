# Estado y pendientes de EdgeLab — repo y Kaggle

**Corte remoto: 2026-10-10 (UTC), antes del PR de este documento.**
Base revisada: `440622d044b43245f5f299f5b492c822949569c8`; foundation: `f397a318be8b0acf68789070fe8064d83e172f7d`.
**133 ramas y 27 PR abiertos: 24 borradores y 3 no borradores.**
Inventario completo de refs/PR, con historia Git no shallow; no equivale a revisión
semántica completa de cada rama. El trabajo no pusheado de la PC no es visible.
[Snapshot legible por agentes](../config/repository_inventory_20261010.json).
Los conteos son congelados: el PR de este cierre es adicional y no los modifica.

## Avance posterior al corte: AVZVOL incremental

Se preparó [protocolo y controles sintéticos](research/AVZVOL_SIGUIENTE_ETAPA_20261010.md):
IDs/pares/pesos, soporte declarado y match determinista sobre covariables. No modifica
el snapshot de ramas ni los resultados originales. No hay nuevos outcomes, inferencia
ni release aprobado; R7/K8 siguen abiertos y faltan pins/calipers/censo/censura/presupuesto.

Se recuperaron [candidatos de procedencia MNQ](infra/AVZVOL_LINEAGE_RECOVERY_20261010.md):
resolver/loader v15, declaraciones SHA de seis raw y comparación estática del bundle v2.
Coherencia con logs y Git no acredita consumo físico histórico ni calidad. R7/K8
no se cierran; no hubo nuevas ejecuciones de mercado.

La [revisión de metadatos MNQ](infra/AVZVOL_MNQ_METADATA_QUALITY_20261010.md)
reconcilia 261 sesiones candidatas, pero muestra warmup fuera de la máscara aprobada
y reglas de elegibilidad sin as-of acreditado. El checker JSON conserva STOP científico;
no escanea raw ni certifica continuidad/reloj/liquidez. R7/K8 permanecen abiertos.

La [QA física MNQ](infra/AVZVOL_MNQ_RAW_QUALITY_20261010.md) verificó seis pins y
485.596.960 filas, con cero errores estructurales. No certifica continuidad,
calendario, reloj, liquidez ni consumo histórico. Las diferencias de gaps se
reconcilian bajo el filtro de pausa candidato; no son automáticamente huecos.
[Cuatro propuestas](../config/research/avzvol_followup_proposals_v1.json) conservadas;
**no buscar outcomes económicos: P4 bloqueada hasta nueva autorización explícita**.
R7/K8 siguen abiertos; ningún snapshot previo se reescribe.

La [revisión causal D-1](infra/AVZVOL_CAUSAL_SELECTION_REVIEW_20261010.md)
refuerza el gate compartido con evidencia de todos los competidores y disponibilidad
antes del cutoff. Es rechazo fail-closed, no certificación. v15 permanece igual,
R7/K8 abiertos y P4 prohibida; no se ejecutaron outcomes económicos.

## 1. Respuesta operativa

- **Ya integrado:** los lotes #69–#78 enumerados abajo. No queda pendiente pushear
  esos lotes; las copias de trabajo viejas no autorizan sobrescribir main más nuevo.
- **Ningún PR de funcionalidad existente quedó verificado como listo para merge
  completo a main en este cierre.** Se revisó en detalle la preparación de los tres
  no borradores; los 24 borradores siguen requiriendo revisión acotada y pruebas.
- #67 tiene conflictos y regresiones concretas. #52 y #17 apuntan a bases
  históricas, no a main. Un merge sin conflictos no acredita compatibilidad.
- **Kaggle permite descubrimiento y QA; todavía NO hay release ES/NQ certificado
  para research causal.** Un token da acceso, no sana datos ni concede permisos.
- AVZVOL: baseline publicado reproducido, pero **no certificado libre de sesgo**.
  No se abrieron nuevas auditorías de otras campañas en este cierre.
- Se preservan ramas, PR, negativos y evidencias. No cerrar PR parcialmente portados
  ni borrar backups sólo para reducir el inventario.

## 2. Qué está disponible en main

| Lote | Disponible | Lo que NO acredita |
|---|---|---|
| [#69](https://github.com/Nicodelcampo/EdgeLab/pull/69) | README/AGENTS, catálogo de 17 componentes, entorno CPU/wheel, primeros ports foundation | Toda foundation ni plataforma autónoma completa |
| [#70](https://github.com/Nicodelcampo/EdgeLab/pull/70) | Aislamiento D0/D1 CPU y oráculo sintético | CUDA/end-to-end ni saneamiento upstream |
| [#71](https://github.com/Nicodelcampo/EdgeLab/pull/71) | Gate y lector de sesión opt-in | Protección de todos los lectores legacy ni autenticación de aprobación |
| [#72](https://github.com/Nicodelcampo/EdgeLab/pull/72) | Spec/runner técnico Kaggle, shards/merge y QA de agregados | Attach/scheduler productivo ni datos causales certificados |
| [#73](https://github.com/Nicodelcampo/EdgeLab/pull/73) | Inventario de ventana completa y guard de cobertura | Calendario histórico certificado |
| [#74](https://github.com/Nicodelcampo/EdgeLab/pull/74) | QA estructural de 18 raw ES/NQ y cuarentena exacta NQ | Continuidad, reloj independiente, roll/liquidez o ausencia de sesgo |
| [#75](https://github.com/Nicodelcampo/EdgeLab/pull/75) | Descubrimiento portable: seis referencias, 31 archivos con pins; research STOP | Nueva versión de archivos del catálogo ni autorización económica |
| [#76](https://github.com/Nicodelcampo/EdgeLab/pull/76) | Diagnóstico de roll ES y pedido concreto de originales | Reparación de ticks por inferencia |
| [#77](https://github.com/Nicodelcampo/EdgeLab/pull/77) | Entrada de resultados y chequeo de envelope/lineage | Validez científica global de resultados históricos |
| [#78](https://github.com/Nicodelcampo/EdgeLab/pull/78) | Auditoría AVZVOL, baseline estricto, bins congelados opt-in y CLI de covariables | Efecto económico de los hallazgos ni retrofitting del runner histórico |

Entradas: [componentes](COMPONENTS.md), [entorno](ENVIRONMENT.md),
[Kaggle](KAGGLE_START_HERE.md), [resultados](RESULTS_START_HERE.md),
[AVZVOL](infra/AVZVOL_AUDIT_20261010.md).
Las pruebas publicadas de #78 (438 tests + 8 subtests, wheel/core y CI)
corresponden a ese lote: no certifican los 27 PR históricos ni los datos.

## 3. Todos los PR abiertos del corte

Los destinos se muestran explícitamente: merge a una feature o foundation no
significa integración en main. “Borrador” no prueba que todo esté mal, pero tampoco
permite declarar un lote listo por su título. El snapshot guarda HEAD y base live.

| PR | Estado | Destino | Pendiente / tratamiento |
|---|---|---|---|
| [#68](https://github.com/Nicodelcampo/EdgeLab/pull/68) | Borrador | `foundation/f0b-compatibility-probe` | Infra técnica portada #72; attach, scheduler y calidad/liquidez pendientes. |
| [#65](https://github.com/Nicodelcampo/EdgeLab/pull/65) | Borrador | `main` | Gate/lector parcial #71. Falta certificación externa y wiring de consumidores legacy. |
| [#67](https://github.com/Nicodelcampo/EdgeLab/pull/67) | No borrador | `main` | Bloqueado: tres conflictos actuales, schemas fuera del wheel e import Arrow eager. Reconciliar ledger/corpus y CI antes de portar. |
| [#64](https://github.com/Nicodelcampo/EdgeLab/pull/64) | Borrador | `main` | Mezcla campaña MGC y funnel/GPU. Separar infraestructura; MGC no validada y holdout original intacto. |
| [#66](https://github.com/Nicodelcampo/EdgeLab/pull/66) | Borrador | `main` | EdgeReplica: certificar ruta MNQ y pruebas actuales antes de port; borrador. |
| [#63](https://github.com/Nicodelcampo/EdgeLab/pull/63) | Borrador | `main` | CPU portado en #70; faltan upstream/gate y CUDA end-to-end. |
| [#48](https://github.com/Nicodelcampo/EdgeLab/pull/48) | Borrador | `feat/edge-discovery-brain-foundation-20260919` | Visor: port selectivo, consumidores/bundles y paridad específica; no toda la cadena. |
| [#58](https://github.com/Nicodelcampo/EdgeLab/pull/58) | Borrador | `feat/edge-brain-durable-hippocampus-20260922` | Primitivas de gobierno ya presentes; comparar delta. No implementar autonomía local. |
| [#56](https://github.com/Nicodelcampo/EdgeLab/pull/56) | Borrador | `feat/ssrn-bibliographic-cortex-20260921` | Primitivas de hipocampo ya presentes; reconciliar ledger/anchors, no reimportar cadena entera. |
| [#57](https://github.com/Nicodelcampo/EdgeLab/pull/57) | Borrador | `foundation/f0b-compatibility-probe` | Raíz de cadena histórica: no fusionar foundation completa. |
| [#49](https://github.com/Nicodelcampo/EdgeLab/pull/49) | Borrador | `feat/reconstruct-edge-brain-complete-20260920` | Referencia/planeación histórica: reconciliar vigencia; autonomía fuera de alcance. |
| [#52](https://github.com/Nicodelcampo/EdgeLab/pull/52) | No borrador | `feat/reconstruct-edge-brain-complete-20260920` | SSRN histórico, destino reconstrucción, sustituido conceptualmente por #67. No cerrar hasta probar equivalencia; no duplicar el corpus. |
| [#46](https://github.com/Nicodelcampo/EdgeLab/pull/46) | Borrador | `feat/edge-discovery-brain-foundation-20260919` | Reconstrucción histórica: reconciliar schemas/atlas/ledger antes de un port. |
| [#54](https://github.com/Nicodelcampo/EdgeLab/pull/54) | Borrador | `feat/ym-density-corridor-discovery-20260921` | Lab de expansión: definir consumidores y separar investigación de API estable. |
| [#43](https://github.com/Nicodelcampo/EdgeLab/pull/43) | Borrador | `audit/edge-discovery-factory-foundation-20260919` | Memoria foundation: comparar alcance ya portado y deltas. |
| [#41](https://github.com/Nicodelcampo/EdgeLab/pull/41) | Borrador | `fix/causal-viewport-invariant-corridors-20260917` | Visor causal/crosshair: pruebas específicas y dependencia explícita. |
| [#34](https://github.com/Nicodelcampo/EdgeLab/pull/34) | Borrador | `foundation/f0b-compatibility-probe` | Paridad HFT: título no acredita compatibilidad actual; repetir pruebas con procedencia. |
| [#33](https://github.com/Nicodelcampo/EdgeLab/pull/33) | Borrador | `foundation/f0b-compatibility-probe` | Campaña HP008: preservar resultados/particiones; no nueva auditoría científica en este cierre. |
| [#32](https://github.com/Nicodelcampo/EdgeLab/pull/32) | Borrador | `foundation/f0b-compatibility-probe` | Procedencia HFT/Playwright: reconciliar con #34 y validar base actual. |
| [#27](https://github.com/Nicodelcampo/EdgeLab/pull/27) | Borrador | `foundation/f0b-compatibility-probe` | Onboarding histórico: comparar con README/AGENTS actuales, no sobrescribirlos. |
| [#22](https://github.com/Nicodelcampo/EdgeLab/pull/22) | Borrador | `research/avolcluster-nq-microticks-v1-20260828` | Infra AVOL histórica: separar store de campaña y fijar particiones. |
| [#24](https://github.com/Nicodelcampo/EdgeLab/pull/24) | Borrador | `research/avolcluster-nq-gate1-infra-v1-20260828` | Envelope congelado antiguo: preservar holdout julio; sin repo-clone online como dependencia implícita. |
| [#8](https://github.com/Nicodelcampo/EdgeLab/pull/8) | Borrador | `foundation/f0b-compatibility-probe` | Validación estadística: port acotado y tests actuales; no alterar veredictos históricos. |
| [#9](https://github.com/Nicodelcampo/EdgeLab/pull/9) | Borrador | `foundation/f0b-compatibility-probe` | Registro de indicadores: reconciliar con catálogo actual y bridge. |
| [#21](https://github.com/Nicodelcampo/EdgeLab/pull/21) | Borrador | `foundation/f0b-compatibility-probe` | Trazabilidad histórica: reconciliar con entrada de resultados sin reescribir evidencia. |
| [#19](https://github.com/Nicodelcampo/EdgeLab/pull/19) | Borrador | `foundation/f0b-compatibility-probe` | Campaña AVOL: preservar evidencia; no auditada de nuevo en este cierre. |
| [#17](https://github.com/Nicodelcampo/EdgeLab/pull/17) | No borrador | `foundation/f0b-compatibility-probe` | Destino foundation, no main. Merge-tree sin conflictos NO acredita tests actuales ni piloto end-to-end. Preservar holdout original de julio. |

### Los tres no borradores, verificados contra la base actual

- **#67:** `git merge-tree` contra main arroja add/add en `retrieval.py`,
  `schema_validator.py`, `typed_registry.py`. Su schema loader vuelve a rutas de
  checkout, y su registry importa Arrow eagerly: ambos romperían garantías del
  wheel/core actual. El HEAD no tiene check runs; falta reconciliar el digest del
  ledger y metadatos/relaciones del corpus. No copiar corpus/ledger a ciegas.
- **#52:** precursor SSRN sobre reconstrucción histórica; merge-tree contra main
  tiene conflictos en README/AGENTS/config y bridge, entre otros. Comparar con #67,
  preservar procedencia y cerrar sólo tras equivalencia documentada.
- **#17:** merge-tree contra foundation actual no tiene conflictos, pero HEAD no
  está contenido en su destino. Falta validación actual/port a main y piloto
  end-to-end; no ampliar su holdout desde julio a octubre.

## 4. Ramas sin PR, duplicaciones y preservación

El snapshot enumera **cada una de las 133 ramas**, SHA, relación con main/foundation,
PR directo e inclusión por ancestry en otro HEAD abierto. Clasificación mecánica:

- `ACTIVE_BASE`: **1**.
- `ALREADY_IN_MAIN_NO_NEW_PR`: **3**.
- `COVERED_BY_OPEN_PR_HISTORY_NO_DUPLICATE_PR`: **34**.
- `NO_OPEN_PR_REQUIRES_SCOPED_RECONCILIATION`: **66**.
- `PRESERVE_DO_NOT_MERGE_OR_DELETE`: **2**.
- `TRACKED_OPEN_PR_REQUIRES_REVIEW`: **27**.

**Ancestry no es equivalencia de patches.** En particular un squash/port puede
haber integrado parte de una rama sin contener su HEAD. `NO_OPEN_PR...` significa
“reconciliar”, NO “abrir automáticamente otro PR”. Esto incluye ramas de ports
#69–#76: contrastar el commit/PR publicado y el delta restante primero.
Una rama cubierta por historia de otro PR tampoco queda certificada como usable.
Los backups/preserve no son candidatos de limpieza. No se hizo revisión semántica
individual de las 133 ramas ni auditoría económica de campañas adicionales.

## 5. Backlog del repo, con cierre comprobable

| ID / prioridad | Trabajo concreto | Dependencia / responsable por función | Terminado cuando… |
|---|---|---|---|
| R1 / P1 | Port SSRN selectivo #67, sin retroceder retrieval/schema/registry | Integración + custodio de corpus/ledger | Digest/relaciones explicados; schemas empaquetados; import core sin Arrow; tests de consulta/corpus y CI actual pasan |
| R2 / P1 | Reconciliar foundation y cadena histórica por módulos | Integración; [issue 37](https://github.com/Nicodelcampo/EdgeLab/issues/37) | Delta explícito, entorno actual, tests sin skips globales, wheel fuera de checkout; nunca merge masivo |
| R3 / P0 | Conectar gate a consumidores legacy y eliminar bypasses/fallback ambiguo | Datos + autoridad de campaña; K1–K4 | Tests prueban rechazo antes del payload no autorizado; identidad/pins y cobertura obligatorios en cada ruta |
| R4 / P1 | Completar CUDA/paridad de #63 y separar #64 de MGC | Funnel + entorno GPU disponible | Oráculo CPU/GPU y runner end-to-end actual con particiones/budget congelados; no promover campaña por paridad |
| R5 / P1 | Visor/bridge #48/#41 y paridad HFT; indicator-store #17 | Bridge/visor + fixture aprobado | API/consumidor únicos, wheel y tests actuales, evidencia de paridad específica y piloto reproducible |
| R6 / P1 | Attach confiable, scheduler/shards/merge fijo, envelope e ingreso a memoria | Infra Kaggle; K5–K6 | Kernel offline con versiones/bytes verificados; salida estándar y ZIP/hash; ingreso idempotente conserva provenance |
| R7 / P0 | AVZVOL: completar lineage raw/código/resolver y revisión de controles | Custodia + autoridad metodológica | Versiones/hashes probados; `pair_id`/pesos explicables o límite explícito; cualquier método nuevo tiene enmienda |
| R8 / P2 | Cerrar PR reemplazados y archivar sólo referencias autorizadas | Integración, tras R1/R2/R5 | Equivalencia y remanente documentados; evidencia/negativos/branches preservados |
| R9 / P1 | Versionar código del Worker existente y arreglar parser de listado | Infra; acceso brokered existente | Parser reconoce `datasetFiles`, fixtures y prueba real; cobertura/truncación explícitas; código sin secretos en repo |

Estos son roles, no asignaciones a personas inventadas. R1/R2/R5/R8/R9 pueden
avanzar sin nuevos outcomes; R3/R6/R7 no sustituyen evidencia upstream por tests.

## 6. Kaggle: qué hay y qué falta exactamente

### Release actual fijado, no `latest`

- `nicolasbuttaro/edgelab-data-catalog/15`: resolver histórico, **BLOCKED_FOR_RESEARCH**.
- `nicolasbuttaro/edgelab-es-nq-aggregates-20261009/1`: barras 1/30/60 s,
  **QA técnica**, no saneamiento causal.
- Cuatro raw fijados: `nicolasbuttaro/edgelab-nt8-historical-missing-20261001/1`,
  `nicolasbuttaro/edgelab-ticks-es-nq-2026q3-ext/1`,
  `nicolasbuttaro/edgelab-ticks-nq-preholdout/6`,
  `nicolasbuttaro/edgelab-ticks-nt8-reexport-20261005/2`.
- [Inventario portable](../edgelab/kaggle/discovery.json): referencias completas,
  tamaños/hashes y permisos; no asumir que vive como archivo en catalog v15.
- La descripción del catálogo ya enlaza el contrato inmutable publicado por #75.
  No se publicó una nueva versión de archivos ni se convirtió el STOP en aprobación.
- Acceso sin navegador: Kaggle custom MCP y Worker existente con token brokered.
  No pedir ni copiar el token al repo. El Worker tiene publicación de metadata,
  no todas sus capacidades son de sólo lectura. Su inventario acotado NO demuestra
  ausencia de datasets privados ni exhaustividad de búsqueda.

| ID / prioridad | Bloqueo / acción | Qué se necesita | Criterio de cierre |
|---|---|---|---|
| K1 / P0 | Roll ES diciembre→marzo prematuro, selección con domingo de muy bajo volumen | Originales NT8 en PC + export/conversión/timezone; [pedido exacto](infra/KAGGLE_ROLL_SELECTION_20261010.md) | Reconciliación trazable de bytes/reloj/calendario y regla líquida causal aprobada; no borrar/mover ticks por conjetura |
| K2 / P0 | NQ preholdout v6 `NQ_09-26_ticks.parquet`: discrepancias de nueve fechas junio | Fuente original o alternativa adjudicada, pins y comparación independiente | Cuarentena resuelta con evidencia/new release; sin fallback silencioso ni cambio horario supuesto |
| K3 / P0 | Calendario, huecos/exclusiones y toda ventana solicitada no certificados | Calendario CME histórico, límites de sesión/reloj y registro completo de ausencias | Cada sesión esperada figura como cubierta o exclusión declarada; sin omisiones implícitas ni relleno inventado |
| K4 / P0 | Máscara retrospectiva, selección/liquidez y bid/ask/agresor | Umbrales y evidencia externos aprobados, decisión D-1, reloj independiente | Fuente única por sesión, contrato líquido causal y calidad certificada antes de leer; QA de estructura no basta |
| K5 / P1 | Nuevo catálogo + agregados certificados | K1–K4; revisión externa | Versiones inmutables nuevas, pins, cobertura y lineage; consumidor research_access pasa gate con aprobación real |
| K6 / P1 | Adjuntar versiones fiables y ejecutar armazón estándar | R6; mount map exacto | Los 31 archivos del snapshot o los del nuevo release verificados; spec/resultados/attestation/manifest/ZIP reproducibles, merge en orden fijo |
| K7 / P1 | Loader legacy: fallbacks/ambigüedad y caché M1 sin identidad fuerte | Port acotado + fixtures sintéticos | Sin selección por basename; versión/hash en caché; research nunca usa loader como bypass |
| K8 / P0 | AVZVOL: upstream MNQ y controles/binning no certificados | R7; autorización separada antes de contraste nuevo | Lineage exacta y límites explícitos; nuevo binning no se introduce retrospectivamente ni se cuantifica sesgo sin permiso |
| K9 / P1 | Worker: `files` vs `datasetFiles`, búsqueda parcial | R9; SDK/API metadata | Tests y listado real correctos; límites/páginas declarados, ningún cero ambiguo presentado como ausencia |

**Originales pendientes de la PC:** archivos ES 12-25 y ES 03-26
`20251005.Last.utc.txt`, junto con script/log de conversión y timezone del export;
Oct 3/Oct 6 adyacentes ayudan si están disponibles. No hace falta reconstruir todo
para documentar: sí hacen falta originales/evidencia equivalente para reparar sin
sesgar. [Request y límites](infra/KAGGLE_ROLL_SELECTION_20261010.md).

## 7. AVZVOL y límites de resultados anteriores

La auditoría [#78](infra/AVZVOL_AUDIT_20261010.md) reproduce únicamente las 23
celdas del baseline O5 publicado y conserva confirmación/holdout. Detecta controles
por debajo del nominal, ausencia de `pair_id`, bins FE sensibles al orden en
empates y un bypass potencial de comparación en el runner legacy. La ocurrencia
está documentada; **el impacto económico no se cuantificó**. Los guards nuevos
son opt-in, no protegen retroactivamente todas las corridas anteriores.

No se puede afirmar globalmente que “los resultados anteriores no están sesgados”.
Para otras corridas se preserva evidencia y se exige revisión de lineage al reutilizar;
no se ejecutó una nueva auditoría científica de ellas por este pedido.

## 8. Orden seguro de trabajo y fuera de alcance

1. Resolver K1–K4 / R7 y wiring fail-closed. Mientras tanto: metadata y fixtures,
   no nuevas estrategias sobre datos bloqueados.
2. R1/R2/R5/R9 en lotes pequeños con pruebas; no duplicar corpus/ledgers ni borrar ramas.
3. Publicar nuevo release K5; después integrar K6 y demostrar camino completo.
4. Cerrar reemplazados sólo con equivalencia documentada.

Holdouts se conservan por campaña: abril MGC, julio protocolo antiguo,
octubre ES/NQ/AVZVOL donde corresponda. La fecha más reciente no amplía un permiso
histórico. Ante contradicción: STOP y autoridad de campaña, no mayoría de docs.

**Fuera de alcance:** planeación de autonomía/ccbus no pusheada, servidor y ciclos
recursivos. Su ubicación futura debe consumir estos contratos; no se inventa ni
se implementa ahora. Tampoco se lanzan hipótesis, P&L, promociones ni outcomes nuevos.

## AVZVOL: diagnóstico sintético de controles

[Guía y API descriptivos](research/AVZVOL_CONTROL_CENSUS_DIAGNOSTICS_20261010.md):
`python tools/avzvol_design_smoke.py --report control-census`. Sólo covariables
inventadas; no autorización, certificación, inferencia ni benchmark de outcomes.
P2 requiere censo/política/protocolo revisados; P4 permanece prohibida.

[AVZVOL: causalidad de zonas y controles](research/AVZVOL_ZONE_CAUSAL_REVIEW_20261010.md):
revisión de fuente fijada y ejemplos inventados. Pseudo no acredita control sin
racimo; censo as-of y política de sesiones siguen pendientes, sin outcomes nuevos.

## Uso acotado de datos disponibles, solicitado posteriormente

[Revisión descriptiva de O5 expuesto](research/AVZVOL_EXPOSED_O5_REVIEW_20261010.md): se reutilizaron los seis
exports existentes con hashes y faltantes explícitos. No es réplica ciega,
contraste incremental zone-free, certificación de raw ni promoción. No se
alteran los gates/pins pendientes de P1–P3; P4 permanece prohibida.

## Cinta causal de clasificación negativa propuesta

[Contrato y helper probado](research/AVZVOL_ZONE_NEGATIVE_TAPE_20261010.md): distingue cero zonas con calibración de
UNKNOWN por bloques/calibración/as-of faltantes. Sin zona en una ventana no
acredita ausencia de racimo ni consolidación. Sólo fixtures inventados; el censo
real, protocolo y calidad siguen pendientes. No libera gates ni P4.

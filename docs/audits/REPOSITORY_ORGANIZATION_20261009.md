# EdgeLab: auditoría de integración, claridad y acceso para agentes

Corte de revisión: 2026-10-09. Repositorio: Nicodelcampo/EdgeLab.

## Dictamen

EdgeLab contiene piezas reutilizables importantes, pero todavía no ofrece una distribución única y verificable del producto. El problema no es sólo acumular merges: hay bases divergentes, cadenas de dependencias, documentación que mezcla estado histórico con operativo y capacidades cuya presencia en una rama no demuestra que estén accesibles en el producto.

**No se fusionó, eliminó, archivó ni modificó ninguna rama, PR o documento remoto durante esta revisión.**

## Alcance y límites

Inventario de las 123 ramas remotas, 27 PR abiertos, metadatos de PR cerrados disponibles, comparación de árboles/ancestría, controles del HEAD de cada PR, documentos de entrada y módulos seleccionados. Se leyeron los issues 37, 38 y 44 y las descripciones de propuestas clave. No fue una revisión línea por línea de todos los archivos: no se ejecutó la suite completa, no se instalaron los entornos históricos, no se leyó holdout ni se reprodujeron resultados económicos. Las causas exactas de los fallos actuales de CI requieren logs y reproducción; un issue histórico no acredita que todos tengan hoy esa misma causa.

Snapshots: main `ab9a0540c43ad7f68a015a9f22892633a555cd6d`; foundation `617064e0b86fd2490f2834b5da731cd26aaa23ea`. Las cifras son una fotografía, no una garantía sobre cambios posteriores.

## 1. Hallazgos prioritarios

### P0 — Dos bases no reconciliadas

Main es la rama predeterminada, pero el README de foundation dice que main es la baseline y foundation la rama viva. Foundation tiene 1.711 commits exclusivos y main ocho exclusivos. No conviene reemplazar una con la otra ni mergear todo indiscriminadamente. Main tiene 177 archivos y foundation 3.945: esa diferencia incluye documentación y artefactos, no mide funcionalidad.

Main no tiene README raíz, pyproject.toml ni workflows de GitHub. Sí tiene motor, bridge, datos, hipocampo y embudo CPU/GPU. Foundation tiene infraestructura, índices, locks, workflows y otros módulos, pero no el mismo embudo como subpaquete. La integración debe preservar los ocho commits exclusivos de main, incluidos recuperación del bridge, barras de cola de sesión NT8, multiplicidad y embudo.

Fuentes: árboles versionados y comparación Git; README de foundation: https://github.com/Nicodelcampo/EdgeLab/blob/foundation/f0b-compatibility-probe/README.md

### P0 — El estado operativo no tiene una puerta única confiable

- README dirige primero a auditoría de agosto y llama viva a foundation.
- PROJECT_INDEX está fechado 2-sep y enumera un registro de 60 ramas/17 PR, frente a las 123/27 actuales.
- AUDITOR_START_HERE está fechado 17-sep y señala una rama HFT como continuidad.
- CURRENT está fechado 26-sep y describe el head del visor, aunque está dentro de foundation cuyo HEAD ya llega a octubre.
- AGENTS contiene la enmienda HOLDOUT-A3: reserva forward desde la sesión del 1-oct. AUDITOR_START_HERE todavía muestra julio–diciembre como holdout. El issue 44 conserva el umbral anterior.

No se debe resolver esta contradicción eligiendo la fecha de modificación más reciente ni ampliando accesos automáticamente. La política vigente debe derivar de la enmienda aprobada y del manifiesto específico de campaña, con un registro legible por máquina y tests de concordancia documental. Un documento histórico debe quedar claramente marcado como tal.

Fuentes: https://github.com/Nicodelcampo/EdgeLab/blob/foundation/f0b-compatibility-probe/PROJECT_INDEX.md ; https://github.com/Nicodelcampo/EdgeLab/blob/foundation/f0b-compatibility-probe/AUDITOR_START_HERE.md ; https://github.com/Nicodelcampo/EdgeLab/blob/foundation/f0b-compatibility-probe/AGENTS.md ; https://github.com/Nicodelcampo/EdgeLab/issues/44

### P0 — No hay candidato con integración completamente acreditada

De 27 PR abiertos, 24 son draft. Sólo cinco apuntan a main; 22 a otras ramas. En los HEAD consultados, 22 PR tienen fallos en checks pytest y cinco no tienen check-runs. Esto no demuestra que cada cambio tenga un bug propio: algunos tienen verificaciones focales verdes. Tampoco acredita preparación para merge. `mergeable=clean` sólo indica compatibilidad mecánica; `unknown` no demuestra conflicto.

Issue 37 ya documenta deuda de portabilidad: rutas Windows, calendarios, tests dependientes de datos locales y tipos Arrow. Debe reproducirse contra la base elegida y corregirse sin ocultar fallos con skips globales. PR 68 también tiene pytest rojo: los tests focales de la infraestructura no sustituyen la suite integrada.

Fuente: https://github.com/Nicodelcampo/EdgeLab/issues/37 y checks enlazados en el inventario de PR.

### P1 — PR abierto no equivale a pieza faltante

PR 67 declara que reemplaza a 52; conservar ambos como alternativas activas confunde al siguiente agente. El archivo hippocampus_store.py de main y foundation tiene el mismo blob Git (`dd52a74140844213e90924ba389ee253f2bd98cb`), distinto del head histórico de PR 56. Por lo tanto, no procede portar ciegamente otra vez el hipocampo: hay que reconciliar cobertura, cambios posteriores, génesis y estado del PR.

PR 64 incluye a 63 y mezcla infraestructura del funnel con varias campañas. PR 48 modifica 1.998 archivos y acumula visor, L2, investigación y otras incorporaciones. Es difícil revisar o revertir eso como una única unidad de producto.

PR 68 sigue titulado y descrito como bloqueado por mounts, aunque su commit final y comentario de cierre documentan publicación y consumo verificado de los agregados. Actualizar título/body es deuda de claridad, no una nueva ejecución de datos. No implica que todo el motor universal, scheduler o adaptadores económicos estén terminados.

Fuentes: https://github.com/Nicodelcampo/EdgeLab/pull/67 ; https://github.com/Nicodelcampo/EdgeLab/pull/56 ; https://github.com/Nicodelcampo/EdgeLab/pull/64 ; https://github.com/Nicodelcampo/EdgeLab/pull/48 ; https://github.com/Nicodelcampo/EdgeLab/pull/68#issuecomment-6092785805

### P1 — Usabilidad desde un clon limpio no está estandarizada

ENVIRONMENT presenta comandos Windows y declara que el paquete no se instala editable. Pyproject limita los paquetes a `edgelab`, mientras hay múltiples subpaquetes: debe validarse el wheel y la importación fuera del directorio del repo antes de declarar instalabilidad. No se comprobó eso en esta auditoría.

No hay `edgelab/__main__.py` ni `edgelab/cli.py` en foundation; hay CLIs dispersas en tools, y main tiene entradas del funnel. No existe una puerta común acreditada para consultar capacidades, validar entorno, resolver datasets, ejecutar y verificar evidencia. Las rutas locales y datasets privados deben figurar como dependencias explícitas; su ausencia debe producir un bloqueo accionable, nunca una reparación silenciosa.

Fuentes: https://github.com/Nicodelcampo/EdgeLab/blob/foundation/f0b-compatibility-probe/ENVIRONMENT.md ; https://github.com/Nicodelcampo/EdgeLab/blob/foundation/f0b-compatibility-probe/pyproject.toml

## 2. Mapa de producto propuesto

Esta tabla define posiciones y límites propuestos, no capacidades ya integradas o certificadas.

| Parte | Responsabilidad y acceso actual | Límite que debe quedar claro |
|---|---|---|
| Datos/custodia | edgelab/data, bridge/ticks, régimen contractual; catálogo Kaggle y resolver de PR 68 | Una fuente aprobada por sesión; no inferir completitud o liquidez de hashes. Catalogar tick, barras temporales, barras tick y L2 como productos distintos. |
| Motor | edgelab/engine.py; contrato de señales en CONTRATO_LLM.md | Autoridad de fills, costos y salidas. No duplicar P&L en cada estrategia. |
| Indicadores/bridge NT8 | edgelab/bridge/indicators, parity, oracle, viewer_export | Nombre visible no acredita paridad. Registrar motor, versión, activo, campos y evidencia. |
| Research/funnel | edgelab/funnel en main; fixes 63/64 | Screening no es confirmación. Particiones, multiplicidad y lectura física deben estar verificadas antes de correr campañas. |
| Ejecución Kaggle | PR 68: spec, preflight, shards por contrato, merge fijo, manifest/attestation/zip | Infraestructura de agregados y evidencia; no presentar como plataforma económica universal ya terminada. V1 de PR 24 es histórico hasta resolver compatibilidad. |
| Hipocampo operativo | hippocampus.py + hippocampus_store.py; herramientas Brain | Memoria de episodios/evidencia e invalidaciones. Persistencia no equivale a certificación de una hipótesis. Especificar ledger, anchors y esquema por campaña. |
| Bibliografía SSRN | PR 67: corpus, bootstrap, búsqueda, claims | Claims bibliográficos no son resultados propios. Mantener deuda del hash del ledger y manifest visible. |
| Brain/Factory/Governor | ramas 43/46/54/58; módulos edge_brain y edge_factory | Separar registro/memoria, propuesta de hipótesis, planificación y control de permisos. Evitar llamar «cerebro completo» a un conjunto no ejecutable end-to-end. |
| Visor | PR 48, viewer/nt8_bridge/index.html y bundles | Consumidor de evidencia, no fuente independiente de verdad. L2/detectores exploratorios y PARITY_ABSTAIN deben permanecer visibles. |
| Propfirm | edgelab/propfirm y tools de reportes en foundation/linaje visor | Evaluación de reglas/EV del participante, separada de detección de edge y ejecución de mercado. |
| Context/GEX/regímenes | subpaquetes foundation y ramas específicas | Mantener como experimentales hasta documentar entradas, contratos, tests y consumidor real; no eliminarlos por no aparecer en main. |
| Campañas/resultados | docs/research, artefactos y ramas research/work/results | Investigación con estado y preregistro; no mezclarlas con API estable ni convertir negativos en funciones de producto. |
| Histórico/cuarentena | archive, backup, preserve, exportaciones | Evidencia preservada, no ruta operativa. Ramas congeladas requieren decisión expresa, no limpieza automática. |

## 3. Contrato mínimo de cada componente

Un registro de módulos versionado debe publicar para cada pieza:

1. ID estable, propósito en una frase y categoría: core / experimental / campaña / histórico.
2. Ruta canónica, versión y estado: disponible / bloqueado / reemplazado / archivado.
3. Entradas: formato, esquema, unidad de tiempo, zona horaria, origen, aprobación y versión del dataset.
4. Salidas: esquema, hashes, disponibilidad causal y significado del veredicto.
5. Dependencias y consumidor; dónde se conecta con el flujo completo.
6. Comando mínimo de uso, ejemplo sintético, costo esperado y error de bloqueo accionable.
7. Tests, alcance exacto de certificación y limitaciones conocidas.
8. Relación con versiones anteriores: sustituye, adapta, depende de o conserva como evidencia.

No duplicar el estado en cinco documentos editados manualmente. README y páginas de módulos deben enlazar o generarse desde ese registro.

## 4. Experiencia de entrada deseada

Propuesta, no comandos existentes:

- `edgelab doctor`: rama/commit, entorno, capacidades y bloqueos, sin leer datos sellados.
- `edgelab modules`: mapa de capacidades con estado y ayuda.
- `edgelab data resolve/check`: contrato, sesiones, datasets a adjuntar y política de reserva.
- `edgelab run --spec ...`: valida primero; una corrida identificada y reproducible.
- `edgelab evidence verify ...`: manifiesto/zip/attestation/hashes.
- `edgelab memory verify/ingest ...`: valida evidencia y permisos antes de persistir.
- `edgelab papers search ...`: biblioteca SSRN explícitamente no certificadora.
- `edgelab viewer ...`: abre un bundle aprobado sin ocultar uncertified.

Un agente debe poder recorrer un ejemplo sintético de extremo a extremo: spec → resolución → ejecución → resultados/evidencia → verificación → ingestión autorizada → consulta. Sin credenciales para el ejemplo; con prompts privados sólo para operaciones reales que las requieran.

## 5. Orden de integración recomendado

1. **Base de producto y CI**: rama de reconciliación explícita; conservar los ocho commits exclusivos de main y seleccionar infraestructura necesaria de foundation. Fijar Python/locks, compilar, tests CPU sintéticos y smoke desde clon limpio. No convertir foundation entera en main a ciegas.
2. **Mapa y entrada**: README breve, AGENTS breve y consistente, registro de módulos, política de datos única, comando doctor y un ejemplo. Separar documentos históricos del estado vivo. No borrar evidencia.
3. **Datos y aislamiento**: evaluar gate 65 y fixes 63, que requieren wiring real; de 64 extraer infraestructura y correcciones necesarias sin arrastrar todas las campañas. Validar consumidores, matriz de dispositivos y CUDA por separado.
4. **Ejecución y memoria**: portar/reconciliar 68 con la base seleccionada, usando el hipocampo que ya existe; pruebas de spec, montaje, contrato indivisible, merge determinista, round-trip de evidencia e ingestión autorizada. Actualizar estado de 24 y 68.
5. **Bibliografía**: usar 67 como candidato en lugar de duplicar 52; resolver advertencias de ledger, metadatos y bootstrap antes de considerar canónico todo el corpus.
6. **Brain/Factory/Governor**: revisar semánticamente 57 → 43 → 46 y dependencias 52/56/58. Elegir puertos acotados o integrar cadena sólo si la base y tests lo permiten. Cerrar PR sustituidos únicamente después de equivalencia documentada.
7. **Bridge/visor**: seleccionar componentes de 17/22/34/41/48; conservar paridades específicas y separar infraestructura de bundles, evidencia y campañas. Revisar los threads pendientes y smoke de navegador antes de llamar al visor producto estable.
8. **Research y módulos laterales**: indexar todas las familias, incluidos negativos, bloqueos y límites. Mantenerlos consultables y fuera de la ruta predeterminada de ejecución hasta aceptación explícita.

No es un orden de `merge` automático: hay dependencias y bugs que requieren revisión/cambios. Criterios de aceptación por lote: imports fuera del repo, help/doc coherentes, tests locales y CI verdes, ejemplo sintético, contratos y política de datos intactos, evidencia de equivalencia e invalidaciones conservadas.

## 6. Ramas sin PR / historia

94 ramas con diferencias respecto de main no tienen un PR abierto propio. 59 heads no son ancestros de main, foundation ni de los heads de PR abiertos. **Ninguna cifra equivale a 59 o 94 trabajos inéditos:** cherry-picks, squash, rebase y versiones avanzadas de ramas ya mergeadas exigen comparación por patches y artefactos.

Ejemplos de revisión necesaria:
- `claude/focused-fermat-qjt805`: PR 59/60/62 ya mergearon versiones previas en el visor; el HEAD actual agrega un handoff del 3-oct. No clasificar toda la rama como inédita ni como resuelta.
- `indicator/four-pass-sparse-stop-first-20261001`: detector FP4 con bridge JS y tests, sin vía de PR actual; debe ubicarse como indicador experimental con contrato, no crear un segundo visor canónico por accidente.
- `agent-b/cycle-001-learning-packet-ingestion`: adaptador de learning packets; comparar semánticamente con memoria actual antes de otra implementación de ingestion.
- `agent-c/cycle-001-kaggle-access-audit` y QA: conservar adjudicaciones e incidentes de custodia, no considerarlos producto ejecutable.
- `fix/cycle001-ci-common-cause-20260922`: ya se mergeó en 55 a una rama Brain; su pertenencia al linaje no demuestra CI verde hoy.
- `backup/*` y `preserve/*`: patrimonio histórico; no borrar ni mergear por conteo.

## 7. Inventario completo de PR abiertos

Checks aquí: estado observado de check-runs del HEAD, no certificación ni reproducción propia. «Sin checks» no implica aprobado.

| PR | Propuesta | Base | Draft | Archivos declarados | Checks HEAD |
|---|---|---|---|---:|---|
| [#8](https://github.com/Nicodelcampo/EdgeLab/pull/8) | fix(g2): calibrar DSR-HAC y restaurar nulo por campaña | `foundation/f0b-compatibility-probe` | Sí | 13 | pytest con fallos |
| [#9](https://github.com/Nicodelcampo/EdgeLab/pull/9) | Prep: auditable indicator onboarding and aVolClusterPOI source | `foundation/f0b-compatibility-probe` | Sí | 17 | pytest con fallos |
| [#17](https://github.com/Nicodelcampo/EdgeLab/pull/17) | feat(store): materialize target-free indicator coordinates | `foundation/f0b-compatibility-probe` | No | 11 | pytest con fallos |
| [#19](https://github.com/Nicodelcampo/EdgeLab/pull/19) | research(avol): fail-closed two-stage location + BigTrap direction protocol | `foundation/f0b-compatibility-probe` | Sí | 5 | pytest con fallos |
| [#21](https://github.com/Nicodelcampo/EdgeLab/pull/21) | docs(traceability): refresh project state and branch registry | `foundation/f0b-compatibility-probe` | Sí | 5 | pytest con fallos |
| [#22](https://github.com/Nicodelcampo/EdgeLab/pull/22) | research(avol): add fail-closed NQ-120t zone-store infrastructure | `research/avolcluster-nq-microticks-v1-20260828` | Sí | 28 | pytest con fallos |
| [#24](https://github.com/Nicodelcampo/EdgeLab/pull/24) | infra(kaggle): frozen fail-closed cloud execution envelope | `research/avolcluster-nq-gate1-infra-v1-20260828` | Sí | 31 | pytest con fallos |
| [#27](https://github.com/Nicodelcampo/EdgeLab/pull/27) | docs(repo): agregar onboarding seguro y snapshot de ramas | `foundation/f0b-compatibility-probe` | Sí | 4 | pytest con fallos |
| [#32](https://github.com/Nicodelcampo/EdgeLab/pull/32) | fix(hft): correct parity provenance and provision Playwright | `foundation/f0b-compatibility-probe` | Sí | 5 | pytest con fallos |
| [#33](https://github.com/Nicodelcampo/EdgeLab/pull/33) | research(hp008): causal multicontract NQ replication | `foundation/f0b-compatibility-probe` | Sí | 2 | pytest con fallos |
| [#34](https://github.com/Nicodelcampo/EdgeLab/pull/34) | fix(hft): certificacion de paridad completa HFT V2 nativa NT8 (38 campos, cero deriva) | `foundation/f0b-compatibility-probe` | Sí | 23 | pytest con fallos |
| [#41](https://github.com/Nicodelcampo/EdgeLab/pull/41) | feat(viewer): perfil causal de densidad en la crosshair | `fix/causal-viewport-invariant-corridors-20260917` | Sí | 3 | pytest con fallos |
| [#43](https://github.com/Nicodelcampo/EdgeLab/pull/43) | feat(edge-brain): recursive methodological memory foundation [HANDOFF READY] | `audit/edge-discovery-factory-foundation-20260919` | Sí | 33 | pytest con fallos |
| [#46](https://github.com/Nicodelcampo/EdgeLab/pull/46) | feat(edge-brain): reconstruct unpublished hippocampus and atlas | `feat/edge-discovery-brain-foundation-20260919` | Sí | 48 | pytest con fallos |
| [#48](https://github.com/Nicodelcampo/EdgeLab/pull/48) | feat(viewer): establish one canonical NT8 viewer lineage | `feat/edge-discovery-brain-foundation-20260919` | Sí | 1998 | pytest con fallos |
| [#49](https://github.com/Nicodelcampo/EdgeLab/pull/49) | docs(audit): materialize continuous reference and seven-workstream RSI program | `feat/reconstruct-edge-brain-complete-20260920` | Sí | 10 | pytest con fallos |
| [#52](https://github.com/Nicodelcampo/EdgeLab/pull/52) | feat(edge-brain): integrate complete CerebroSSRN corpus | `feat/reconstruct-edge-brain-complete-20260920` | No | 11 | pytest con fallos |
| [#54](https://github.com/Nicodelcampo/EdgeLab/pull/54) | feat(execution): start the EdgeLab Frontier Expansion Lab | `feat/ym-density-corridor-discovery-20260921` | Sí | 21 | pytest con fallos |
| [#56](https://github.com/Nicodelcampo/EdgeLab/pull/56) | feat(edge-brain): durable hash-chained hippocampus ledger + CYCLE-001 genesis | `feat/ssrn-bibliographic-cortex-20260921` | Sí | 17 | pytest con fallos |
| [#57](https://github.com/Nicodelcampo/EdgeLab/pull/57) | chore(integration): root of the September chain onto foundation | `foundation/f0b-compatibility-probe` | Sí | 96 | pytest con fallos |
| [#58](https://github.com/Nicodelcampo/EdgeLab/pull/58) | feat(brain): govern recursive learning work with budgets and stop rules | `feat/edge-brain-durable-hippocampus-20260922` | Sí | 7 | pytest con fallos |
| [#63](https://github.com/Nicodelcampo/EdgeLab/pull/63) | fix(funnel): isolate D0/D1 outcomes and gate CUDA parity | `main` | Sí | 11 | sin checks |
| [#64](https://github.com/Nicodelcampo/EdgeLab/pull/64) | research(mgc)+feat(funnel): MGC EMA no validada; EF0/EF3/EF4, custodia y paridad GPU a escala | `main` | Sí | 233 | sin checks |
| [#65](https://github.com/Nicodelcampo/EdgeLab/pull/65) | Audit canonical data sanitation and enforceable liquidity prerequisites | `main` | Sí | 4 | sin checks |
| [#66](https://github.com/Nicodelcampo/EdgeLab/pull/66) | EdgeReplica: 60-rule logical port and protected MNQ asset route | `main` | Sí | 36 | sin checks |
| [#67](https://github.com/Nicodelcampo/EdgeLab/pull/67) | feat(edge-brain): SSRN Bibliographic Cortex + corpus CerebroSSRN en el repo (hipocampo) | `main` | No | 907 | sin checks |
| [#68](https://github.com/Nicodelcampo/EdgeLab/pull/68) | Infra: spec offline, agregados 1s/30s/60s y evidencia (mounts bloqueados) | `foundation/f0b-compatibility-probe` | Sí | 12 | pytest con fallos |

## 8. Inventario completo de ramas

PR cerrado/mergeado se refiere a una versión histórica de esa rama; no demuestra incorporación del HEAD actual ni incorporación a main. La columna fuera de linajes usa sólo ancestría de commits, no equivalencia de patches.

| Rama | HEAD | PR abierto | PR históricos | Fuera de linajes activos por ancestría |
|---|---|---|---|---|
| `agent-b/cycle-001-learning-packet-ingestion` | `f19baf3fb9` | — | — | Sí: revisar patches |
| `agent-c/cycle-001-kaggle-access-audit` | `5658678d64` | — | — | Sí: revisar patches |
| `audit/canonical-liquidity-20261004` | `ae8898746d` | #65 | — | No |
| `audit/cycle-001-agent-a-currentness-20260921` | `e88823104e` | — | — | Sí: revisar patches |
| `audit/edge-discovery-factory-foundation-20260919` | `3ae3c3e710` | #57 | #45 (mergeado a feat/edge-discovery-brain-foundation-20260919) | No |
| `audit/edgelab-continuous-reference-20260920` | `7b94b1efc1` | #49 | — | No |
| `audit/notion-ai-sltp-p2b-provenance-20260830` | `fc02d7d84f` | — | — | Sí: revisar patches |
| `audit/p0-bigtrap2-drift` | `1916ffa890` | — | #10 (mergeado a foundation/f0b-compatibility-probe) | No |
| `backup/foundation-f0b-local` | `a48efcd0d0` | — | — | Sí: revisar patches |
| `claude/focused-fermat-qjt805` | `09a46e6125` | — | #62 (mergeado a feat/unified-nt8-viewer-20260920); #60 (mergeado a feat/unified-nt8-viewer-20260920); #59 (mergeado a feat/unified-nt8-viewer-20260920) | Sí: revisar patches |
| `claude/vibrant-clarke-s9z6e2` | `b4c2ab6366` | #64 | — | No |
| `docs/es-apriori-2026-08-25` | `a73f57f408` | — | — | Sí: revisar patches |
| `docs/estado-real-2026-08-10` | `16acc7d9eb` | — | #1 (mergeado a foundation/f0b-compatibility-probe) | Sí: revisar patches |
| `docs/h-cond-1-lux-imb` | `5530344c98` | — | #3 (mergeado a foundation/f0b-compatibility-probe) | Sí: revisar patches |
| `docs/h-sweep-1-ym-prerange` | `2df700f475` | — | #4 (mergeado a foundation/f0b-compatibility-probe) | Sí: revisar patches |
| `docs/handoff-2026-08-25` | `4b73df7ff3` | — | — | Sí: revisar patches |
| `docs/lecciones-2026-08-24` | `a8ab114ab7` | — | — | No |
| `docs/lux-imb-source-correction` | `3383d8827e` | — | #6 (mergeado a foundation/f0b-compatibility-probe) | No |
| `docs/mbt-apriori-2026-08-25` | `e2c7bf2359` | — | — | Sí: revisar patches |
| `docs/post-merge-sync-2026-08-10` | `be1fcfab9e` | — | #2 (mergeado a foundation/f0b-compatibility-probe) | Sí: revisar patches |
| `docs/safe-agent-onboarding-20260915` | `86013d6f11` | #27 | — | No |
| `docs/traceability-refresh-20260828` | `15eb3c5895` | #21 | — | No |
| `feat/crosshair-density-profile-20260918` | `d2d24933ab` | #41 | — | No |
| `feat/edge-brain-durable-hippocampus-20260922` | `e64f311ef1` | #56 | — | No |
| `feat/edge-brain-learning-governor-20260924` | `3b4e98cb7a` | #58 | — | No |
| `feat/edge-discovery-brain-foundation-20260919` | `84eea9758c` | #43 | — | No |
| `feat/edge-replica-port-20261004` | `92fc907129` | #66 | — | No |
| `feat/frontier-expansion-lab-20260921` | `d6adf23539` | #54 | — | No |
| `feat/multiasset-25t-hft-bundles-20260918` | `2658a16f2a` | — | #40 (cerrado sin merge) | No |
| `feat/propfirm-ev-20260926` | `f75d45afef` | — | #61 (mergeado a feat/unified-nt8-viewer-20260920) | No |
| `feat/reconstruct-edge-brain-complete-20260920` | `70daaad098` | #46 | — | No |
| `feat/ssrn-bibliographic-cortex-20260921` | `3cb3fd21d4` | #52 | — | No |
| `feat/ssrn-cortex-port-main-20261009` | `5c10da451b` | #67 | — | No |
| `feat/unified-nt8-viewer-20260920` | `e7425a1513` | #48 | — | No |
| `feat/unified-viewer-canonical-20260921` | `00094f6c3b` | — | — | No |
| `feat/ym-bt2a-economic-search-20260921` | `a488b39062` | — | #50 (cerrado sin merge) | No |
| `feat/ym-bt2a-retest-kaggle-pilot-20260920` | `e1d2a6f6c8` | — | #47 (cerrado sin merge) | Sí: revisar patches |
| `feat/ym-density-corridor-discovery-20260921` | `1532b87544` | — | #51 (cerrado sin merge) | No |
| `fix/bigtrap2-v252-tick-export` | `6a858fdc31` | — | #12 (cerrado sin merge) | Sí: revisar patches |
| `fix/capture-probe-v2-contract` | `8b85add310` | — | — | No |
| `fix/causal-viewport-invariant-corridors-20260917` | `9299b13cbd` | — | #35 (cerrado sin merge) | No |
| `fix/ci-portable-cme-calendar-20260918` | `423fa80e81` | — | #39 (cerrado sin merge) | No |
| `fix/cycle001-ci-common-cause-20260922` | `cf70f44eed` | — | #55 (mergeado a feat/reconstruct-edge-brain-complete-20260920) | Sí: revisar patches |
| `fix/edge-brain-store-hardening-20260923` | `7cd3a98d43` | — | — | No |
| `fix/funnel-stage-isolation-parity-20261003` | `128b4bf058` | #63 | — | No |
| `fix/g2-a1-calibration-hardening` | `780365c74b` | #8 | — | No |
| `fix/g2-a1-statistical-semantics` | `f3b8263953` | — | #5 (cerrado sin merge) | Sí: revisar patches |
| `fix/hft-causal-certification-hardening-20260917` | `1f7a945589` | — | #31 (cerrado sin merge) | No |
| `fix/hft-certification-provenance-playwright-20260918` | `2dde9ac523` | #32 | — | No |
| `fix/hft-native-termination-fresh-replay-20260918` | `5f2358689c` | #34 | — | No |
| `fix/hft-parity-corridor-viewer-complete-v1-20260916` | `46d97e8753` | — | — | No |
| `fix/hft-v2-headless-export-20260916` | `2c151a6b9d` | — | #30 (mergeado a fix/hft-parity-corridor-viewer-complete-v1-20260916) | No |
| `fix/hftzones-nq-parity-certification-v2-20260915` | `3c4d384250` | — | — | Sí: revisar patches |
| `fix/hp007-corridor-causal-viewport-v2-20260915` | `2e90e2f557` | — | — | No |
| `fix/sweep-finalize-contract-scope` | `ee07c34693` | — | — | No |
| `fix/viewer-price-invariance-20260915` | `d7aaf76bb1` | — | #28 (cerrado sin merge) | No |
| `foundation/f0b-compatibility-probe` | `617064e0b8` | — | — | No |
| `indicator/four-pass-sparse-stop-first-20261001` | `1724ed1c10` | — | — | Sí: revisar patches |
| `infra/kaggle-frozen-execution-v1-20260828` | `efc735fafe` | #24 | — | No |
| `infra/kaggle-spec-framework-v2-20261009` | `3845cffd3d` | #68 | — | No |
| `local/edge-discovery-factory-foundation-20260919` | `28362bc23b` | — | — | No |
| `main` | `ab9a0540c4` | — | — | No |
| `prep/indicator-onboarding-registry` | `2e8ed3bdd4` | #9 | — | No |
| `preserve/f0b-local-divergente-2026-08-04` | `a48efcd0d0` | — | — | Sí: revisar patches |
| `qa/cycle001-d-kaggle-access-review` | `3a90f8881b` | — | — | Sí: revisar patches |
| `qa/cycle001-d-viewer-causal-smoke` | `9175930498` | — | — | Sí: revisar patches |
| `registry/gex-familia` | `f065df2146` | — | — | Sí: revisar patches |
| `research/avol-bt2-two-stage-v0-20260827` | `cde6d93a75` | — | — | No |
| `research/avolcluster-compression-v1-20260827` | `e53fcf64ed` | #19 | — | No |
| `research/avolcluster-nq-gate1-infra-v1-20260828` | `b5b89bb4f3` | #22 | — | No |
| `research/avolcluster-nq-lifecycle-v1-20260830` | `ca1f2b8e98` | — | — | Sí: revisar patches |
| `research/avolcluster-nq-microticks-v1-20260828` | `3961b67d80` | — | — | No |
| `research/avolcluster-nq-parity-oracle-20260901` | `6f4e32f9a1` | — | — | No |
| `research/bigtrap2-distance-matched-null` | `108823bf2a` | — | #11 (cerrado sin merge) | Sí: revisar patches |
| `research/bigtrap2-local-displacement-null` | `29d78eba66` | — | — | No |
| `research/bigtrap2-multiframe-ml` | `05d2da7525` | — | — | Sí: revisar patches |
| `research/bigtrap2-nq-tickframes-sweep-v1-20260828` | `9f33a51a9f` | — | #23 (cerrado sin merge) | Sí: revisar patches |
| `research/bigtrap2-soporte-balance-curve` | `a856821c42` | — | — | No |
| `research/bt2a-gc-sltp-breakeven-design-v1-20260830` | `5dd58f2934` | — | — | Sí: revisar patches |
| `research/bt2a-nq-gate1-nrand-capacity-t2-20260830` | `4044e82326` | — | — | Sí: revisar patches |
| `research/bt2a-nq-gate1-outcomes-runner-v1-20260830` | `d229bbb2f8` | — | — | Sí: revisar patches |
| `research/bt2a-nq-gate1-power-closure-20260830` | `cb84424432` | — | — | Sí: revisar patches |
| `research/bt2a-nq-gate1-runner-impl-v1-20260831` | `755dc3cb47` | — | — | Sí: revisar patches |
| `research/bt2a-nq-gate1-v1-20260829` | `c7a81dec37` | — | — | Sí: revisar patches |
| `research/bt2a-nq-target-free-selection-v1-20260828` | `495ba7f972` | — | #25 (cerrado sin merge) | Sí: revisar patches |
| `research/bt2a-nq-v2-sweep-v1-20260829` | `83884585c1` | — | — | Sí: revisar patches |
| `research/bt2a-p2a-clock-heterogeneity-v1-20260827` | `773e7cca63` | — | #20 (cerrado sin merge) | Sí: revisar patches |
| `research/bt2a-p2b-economic-gc-v1-20260827` | `54ab1437fe` | — | #18 (cerrado sin merge) | Sí: revisar patches |
| `research/cross-momentum-multiasset-20261001` | `c51b1e2b50` | — | — | Sí: revisar patches |
| `research/ema-pullback-census-20261001` | `db3445448d` | — | — | Sí: revisar patches |
| `research/ema-pullback-economic-20261001` | `848e5927a5` | — | — | Sí: revisar patches |
| `research/ema3-25t-pullback-grid-20261002` | `1e97460e1f` | — | — | Sí: revisar patches |
| `research/ema3-multiasset-20261001` | `41e2c25b76` | — | — | Sí: revisar patches |
| `research/event-store-pit` | `4d6c6b1a6b` | — | — | No |
| `research/gate-regime-context` | `c882cf5211` | — | — | Sí: revisar patches |
| `research/hp008-causal-multicontract-20260918` | `ed5e4f0266` | #33 | — | No |
| `research/mnq-pullback-extension-20261001` | `983e58953c` | — | — | Sí: revisar patches |
| `research/momentum-frequency-targetfree-20261001` | `51bd5e25bc` | — | — | Sí: revisar patches |
| `research/momentum-short-economic-20261001` | `06ffb156f0` | — | — | Sí: revisar patches |
| `research/rty-momentum-validation-20261001` | `d9378c62ff` | — | — | Sí: revisar patches |
| `research/rty-no-l2-six-tests-20260930` | `0b7c70da1d` | — | — | Sí: revisar patches |
| `research/rty60-expanded-20261001` | `29f86de88d` | — | — | Sí: revisar patches |
| `research/ym-prerange-session-window` | `0c44813069` | — | #7 (mergeado a foundation/f0b-compatibility-probe) | No |
| `research/zamr1-zone-atlas` | `08f9733c67` | — | #13 (cerrado sin merge) | Sí: revisar patches |
| `results/bt2a-p2a-v1-r1-20260827` | `7a9959fb4e` | — | #16 (cerrado sin merge) | Sí: revisar patches |
| `work/bt2a-gate1-all5-20260826` | `3e639e150b` | — | — | No |
| `work/bt2a-gate1-runner-20260826` | `f5fd49db6e` | — | — | No |
| `work/bt2a-gate2-l2-audit-20260826` | `f4b7e607e8` | — | — | Sí: revisar patches |
| `work/bt2a-gate2-l2-hardening-20260826` | `761f50ba93` | — | — | No |
| `work/bt2a-gate2-p2a-freeze-20260826` | `e50bbf3ee2` | — | #15 (cerrado sin merge) | Sí: revisar patches |
| `work/crypto-context-foundation-20260824` | `3b52974f73` | — | #14 (cerrado sin merge) | Sí: revisar patches |
| `work/futures-l2-context-foundation-20260825` | `0a1283f97a` | — | — | No |
| `work/hft-corridor-integration-v1-20260916` | `3cbb864544` | — | #29 (cerrado sin merge) | No |
| `work/hp007-campaign-v2-foundation-20260915` | `3fa15ee57d` | — | — | Sí: revisar patches |
| `work/hp007-causal-campaign-v1-20260915` | `949f7c4f33` | — | — | Sí: revisar patches |
| `work/hp007-corridor-measurement-v1-20260915` | `20f2de397d` | — | — | Sí: revisar patches |
| `work/hp007-rejection-revisit-campaign-v2-20260915` | `1293cf2655` | — | — | Sí: revisar patches |
| `work/hp007-rejection-revisit-campaign-v2-canonical-20260915` | `7f4d85580e` | — | — | No |
| `work/indicator-coordinate-store-v1-20260827` | `9ad26cfc0a` | #17 | — | No |
| `work/nq-causal-foundation-v1-20260915` | `04422b6d25` | — | — | Sí: revisar patches |
| `work/repository-research-iterations` | `5abf9b68cc` | — | — | No |
| `work/research-architecture-hardening` | `a2b3527bc1` | — | — | No |
| `work/universal-contract-regime-v2-20260915` | `29cad93d66` | — | — | No |

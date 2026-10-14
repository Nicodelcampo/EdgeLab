# Handoff 2026-10-14 — cierre de datos, L2, integración y prioridades

Estado: VIGENTE  
Fecha: 2026-10-14

Punto de entrada para continuar sin la conversación. Se lee con `CLAUDE.md`, `docs/research/HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md`, `docs/research/PLAN_HACIA_EDGE_NETO_20261014.md` y `docs/research/REFERENCIA_COSTOS_PROPS_BROKERS_20261014.md`.
Procedencia: relevamiento hecho el 2026-10-14 sobre esta PC (E:, D:), Kaggle (`kaggle datasets/kernels`) y el repo. Nada se borró.

## 1. ¿Está cerrado el tema de datos de ticks?
**Casi: la release está construida, verificada y auditada, pero no aprobada.**
| Ítem | Estado |
|---|---|
| Release `liquid_tick_v1` v4 en Kaggle (manifiesto SHA `db9c42cd…14ce5`) | Publicada, `Ready`. 14 Parquet, 3.838 sesiones, 1.394.017.834 filas |
| Descarga desde Kaggle vs manifiesto | 31/31 archivos con tamaño y SHA-256 correctos |
| Auditoría independiente de contenido (auditor de Notion, corrida en Kaggle) | `CONTENT_CHECKS_PASS_NOT_RESEARCH_APPROVED`, 0 fallas, filas = footer. Recibo: `docs/infra/liquid_v4_audit_20261014/receipt.json` |
| Código de la release en la rama de trabajo | **Portado hoy a `foundation/f0b-compatibility-probe`** (antes sólo vivía en `data/liquid-release-20261014`, que diverge 217 commits y no se puede mergear). 53 tests pasan |
| Aprobación de la release | **SÍ (2026-10-14, delegada por Nico):** `docs/infra/RELEASE_APPROVAL_20261014.md`. El lector estricto `purpose='research'` aún exige `research_allowed=true` en el manifiesto: v5 de sólo metadatos pendiente; mientras tanto `provisional_research` |
| Sesiones faltantes | P0: 158 tramos / 309 sesiones (`docs/infra/MISSING_EXPORTS_20261014.md`); P1: sólo parquet derivado en RTY, MYM, MES, MNQ |
| 701 sesiones-contrato con conflicto de fuente (tabuladas, no resueltas) | Abierto |
| `sequence` no es secuencia del exchange (P-28) | Sigue limitando la microestructura de ticks |

Para considerar cerrado: (1) Nico aprueba licencia/política/calendario, (2) se exportan los P0 que valgan la pena, (3) se resuelven o se acotan los conflictos de fuente.

## 2. Data L2 — dónde está y qué falta
**Kaggle (casi nada):** sólo `edgelab-nq-nt8-2026q3-l2ctx` (0,32 GB, contextos de NQ) y `edgelab-l2-gc-bookmap-audit-20260921` (0,04 GB, 2 sesiones de GC). **No hay L2 crudo de ES/MNQ/MES/6E en Kaggle**: los kernels de L2 sólo pueden correr sobre esas muestras.

**Esta PC (única copia conocida):**
| Ubicación | Contenido | Tamaño aprox. |
|---|---|---|
| `E:\l2_parquet\<ACTIVO>_<contrato>\{l2_depth,l1_quotes,manifests}` | L2 (MBP-10) + L1 en Parquet, 25-jun a 27-sep-2026, 25 contratos de 13 productos (6B, 6E, 6J, ES, GC, MBT, MES, MNQ, MYM, NQ, RTY, YM, ZB) | ≈ 62 GB (MNQ 20,6; NQ 11,5; ES 5,4; MES 5,5; el resto 0,6–3) |
| `E:\l2_contexts\{ES,MES,MNQ,NQ}` | contextos L2 derivados (96–120 archivos c/u) | 0,07 GB |
| `E:\l2\6E 09-26` | L2 crudo 8–16-jun | 1,2 GB |
| `E:\DatosNT8\replay.csv`, `replay_gc0826_raw_csv`, `gc_aug26_canonical_parquets` | L2 de GC (CSV + Parquet), mayo–ago 2026, 26 sesiones con manifiesto | ≈ 5 GB |
| `docs/research/contract_regimes/L2_sessions_catalog_2026092{7,8}.json` | catálogo de sesiones elegibles | repo |
Sesiones elegibles por producto (catálogo 28-sep): 34–60 (ES 56, MES 57, MNQ 60, NQ 60, GC 36, ZB 34).

**Lo que importa:**
- **Poder estadístico:** ≤ 60 sesiones por producto, ~3 meses. El límite es N, no análisis (P-53). El holdout L2 propio (1-nov a 31-dic) todavía no existe: hay que seguir capturando.
- **Riesgo:** ≈ 70 GB de L2 son una sola copia en `E:` sin respaldo verificado. D: tiene 204 GB libres. Falta un respaldo comprimido con hashes (manifiestos por sesión ya existen).
- **Calidad:** hay cuarentena de crash (`_cuarentena_crash_20260924`) y 23 logs de intake; la semántica de reloj L1/L2 vs ticks necesita offset explícito (ver `ENTREGA_LOCAL_L2_GC_ES_20260930.md`).
- **Decisión sobre Kaggle:** subir L2 como release privada propia (con el mismo contrato de custodia: manifiesto, hash, preflight de reloj) sólo cuando haya una campaña L2 aprobada; hoy conviene **respaldar localmente y no subir**.

## 3. Qué ya no sirve en Kaggle (propuesta, nada ejecutado)
Se mantiene la clasificación de `docs/infra/KAGGLE_BORRADO_CANDIDATOS_20261014.md`, con las correcciones del auditor de Notion y mías:
| Nivel | Datasets | Decisión |
|---|---|---|
| **Defecto comprobado** | `edgelab-es-nq-aggregates-20261009` (1,72 GB, roll ES prematuro), `edgelab-ticks-nq-preholdout` (1,10 GB, 363.601 trades en la pausa 16–17 CT) | Sin uso: candidatos a borrar. Hacer igual un respaldo local si no existe |
| **Reemplazado por la release** (16 datasets, 18,2 GB) | `edgelab-ticks-*-preholdout`, `nt8-canonical`, `nt8-reexport-20261005`, `nt8-historical-missing`, `ticks-es-nq-2026q3-ext`, `mgc-nt8-raw-parquet` | No borrar aún: (a) falta el mapa de kernels que los leen (en curso, ver abajo); (b) un contrato líquido por sesión **no es copia sin pérdida** del raw multicontrato. Los originales NT8 existen en `E:\EdgeLab\data\nt8*` y `E:\DatosNT8\tick_history*`: verificar hash contra Kaggle antes |
| **Contexto L2** | `edgelab-nq-nt8-2026q3-l2ctx`, `edgelab-l2-gc-bookmap-audit-20260921` | **Conservar** (única copia en la nube; el auditor de Notion pide lo mismo) |
| **Spot/CFD Dukascopy** (11,9 GB, 7 datasets) | otro mercado, no CME | Conservar hasta decidir si ARB/FX spot sigue vivo; no se usan para ES/NQ/GC |
| **Vigentes** | `edgelab-liquid-ticks-20261014`, `edgelab-data-catalog`, 4 de código, 10 de archivo | Conservar |
**Mapa dataset → kernels (completado, 248 kernels; `docs/infra/KAGGLE_KERNEL_DEPENDENCIES_20261014.csv`):** `edgelab-ticks-nt8-reexport-20261005` lo leen 95 kernels, `edgelab-ticks-nt8-canonical` 80, `edgelab-nt8-historical-missing-20261001` 63, **`edgelab-ticks-nq-preholdout` (el defectuoso) 58**, `edgelab-ticks-es-nq-2026q3-ext` 58, `edgelab-mgc-nt8-raw-parquet` 38, `edgelab-es-nq-aggregates-20261009` 1. Borrar cualquiera deja sin poder reejecutarse a esos kernels; sus resultados siguen en las actas del repo. **No existe ningún dataset reemplazado sin dependientes**: por eso la propuesta pasa a ser *etiquetar y congelar* (prefijo de estado, ya aplicado) y borrar sólo con decisión explícita de Nico y respaldo local verificado.

## 4. Documentación: encontrable, correcta, útil
Problemas encontrados (y qué se hizo / falta):
- **Puertas de entrada desactualizadas:** `README.md` (24-ago), `PROJECT_INDEX.md` (2-sep), `docs/CURRENT.md` (26-sep, nombra una rama que ya no es la viva), `EDGES_DISCOVERED.md` (15-ago). El `CLAUDE.md` de `foundation` sí está al día (10-14). → Este handoff pasa a ser la entrada; `CLAUDE.md` y `PROJECT_INDEX.md` lo apuntan (ver commit).
- **`CLAUDE.md` con dos versiones:** la de `foundation` (hash de North Star `05df5c7c…`, firewall del holdout desde 2026-10-01) y la que cargan las sesiones abiertas en el árbol `E:\EdgeLab` (hash `ed4293b5…`, estado del 2026-08-21). Cada agente lee la suya. Hay que reconciliar con Nico cuál rige; no se tocó (lo protege `tests/test_north_star_hash.py`).
- **Volumen:** 646 documentos en `docs/research`, 2.637 líneas en `PENDIENTE.md`, 174 ramas remotas (68 de octubre). Sin un índice único por tema, un agente nuevo tarda en distinguir lo vigente. → Falta un índice por familia (HFTZones, AVZP2, GC, L2, datos) con estado y acta final.
- **Fuera del repo:** estado vivo en `E:\EdgeLab Estado 14 oct.md` y en Notion; los `.gdoc` de Drive no son legibles por agentes. → Regla: lo que decide algo va al repo, en `.md`.
- **Nueve copias del repo en esta PC** (`E:\EdgeLab`, `-gex`, `-data`, `-integ`, `-port`, más `-multiasset`, `-mym`, `-unified-viewer`, `-brain-review` y `E:\ProyectosQuant\EdgeLab-sync-desktop`). → Deprecar con inventario; una sola rama de integración.

## 5. Qué queda suelto (a integrar o descartar)
0. **Ramas:** registro actualizado en `docs/BRANCH_REGISTRY_20261014.md` (61 ramas ya integradas, 112 con trabajo propio).
0. **Línea `main`: INTEGRADA** (merge real el 2026-10-14, `docs/DECISIONES_20261014.md`). Lo que sigue es histórico del relevamiento.
1. **Rama `data/liquid-release-20261014`** (217 commits, 1.155 archivos): lo útil ya está en `foundation`; el resto es una línea paralela de `research_ops`, `edge_brain`, `bridge` que conflictúa (add/add). No mergear en bloque.
2. **Auditor de Notion** (`Nicodelcampo/EdgeLab@feat/research-ops-supervisor-mvp`): se usó embebido en un kernel; falta traerlo al repo con tests.
3. **`E:\EdgeLab` (rama `claude/focused-fermat-qjt805`)**: ≈ 46 archivos sin commitear (oráculos `data/nt8_oracles/*`, scripts de visor `tools/apply_viewer_*`, `EdgeReplica.cs`, catálogos de regímenes). Decidir qué se versiona, qué se archiva y qué se descarta.
4. **Puente Drive↔Kaggle** (`tools/kaggle_drive_bridge.py`): corre a mano en `--watch`; sin servicio persistente ni hook post-commit del snapshot. Los entregables de Gemini son parches a revisar, no código aplicado.
5. **Parches 06/07 de Gemini**: estrategias de subasta con ancla de IB errónea (primer tick del archivo, no 08:30 CT) y tick fijo 0,25. No aplicar.
6. **Resultados de los 4 kernels v4** (atlas, censo, subasta×AVZP2, barras escaladas): guardados en `docs/research/kaggle_v4_kernels_20261014/`; el censo y la subasta todavía no se leyeron en detalle.
7. **Limpieza de Kaggle** (lista de candidatos) y de disco (`D:\_PARA_BORRAR_20261014`, `D:\_ARCHIVO_COMPRIMIDO_20261014`): esperan decisión.
8. **Calendario 2025-12-25 y feriados**: se resolvió con clasificación por clase; falta el calendario oficial por producto.

## 6. Factores importantes que faltan priorizar
Ordenados por su efecto sobre "edge neto, robusto y operable" (jerarquía del North Star):
| # | Factor | Por qué | Qué hay que hacer |
|---|---|---|---|
| 1 | **Recorrido bruto disponible vs fricción real** | Si en ES el recorrido utilizable no supera ~3,5–4 ticks por viaje, ninguna regla de entrada gana (fricción ≈ 3,4–3,6 ticks con spread medido, comisión 0,28–0,46 y slippage declarado) | Medir la distribución de recorrido por régimen, hora y activo (target-free, sobre la release). Mata o habilita ideas antes de gastar P&L |
| 2 | **N (tamaño de muestra)** | Es el límite recurrente (HFTZones, L2, NQ en AVZP2): tercil bajo/alto sin potencia, L2 ≤ 60 sesiones | Captura continua diaria y automática de ticks y L2; publicar MDE en todo |
| 3 | **Aprobación de la release** | Mientras `research_allowed=false` todo es PROVISIONAL | Decisión de Nico: licencia, política de liquidez, calendario |
| 4 | **Multiplicidad entre familias** | Se acumulan familias (AVZP2, IB, VA, ARB, GEX, L2) con presupuestos independientes | Registrar cada familia antes de estudiarla, con N efectivo y refutación; Holm/PBO |
| 5 | **Ejecutabilidad (slippage y fills)** | Slippage sin medir; sin evidencia de fills pasivos; sim ≠ real | Sesiones de paper/sim con la cuenta elegida; medir slippage real por activo |
| 6 | **Elección de cuenta/broker** | Fricción por firma va de 0,28 a 0,46 ticks (ES) y las props limitan tenencia ≤ 5–10 s | Nico decide al final; reportar siempre ambos extremos |
| 7 | **Respaldo y procedencia** | L2 y raw NT8 en una sola PC | Respaldo comprimido con hashes en D: y copia fuera de la máquina |
| 8 | **Ecosistema multi-IA** | Distancia entre agentes (Gemini sin red, Notion sin datos, Claude con todo) | Puente persistente, entrada única en el repo, kernels de Kaggle con recibo agregado, regla "Kaggle COMPLETE ≠ válido" |
| 9 | **Diversificación real** | ES/MES/MNQ comparten subyacente: no son replicaciones independientes | Elegir apuestas descorrelacionadas (FX, metales, bonos) sólo si superan fricción |

## 7. Próximos pasos propuestos (sin pedir nada nuevo a Nico)
1. Medir el recorrido bruto por régimen/hora/activo (factor 1) con el censo y la release.
2. Leer censo y subasta×AVZP2; registrar en MEDIDO/NO MEDIDO.
3. Traer el auditor de Notion al repo con tests; cerrar el mapa de dependencias de Kaggle.
4. Respaldar L2 con hashes en D:.
5. Refrescar las puertas de entrada (README, PROJECT_INDEX, CURRENT, EDGES_DISCOVERED) y publicar el índice por familia.

*Aporte al referente: reduce la distancia entre "hay datos" y "se puede medir un edge neto" al dejar un único mapa de datos, costos y bloqueos.*

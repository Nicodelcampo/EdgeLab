# Triage de PRs abiertos — 2026-09-22

**Estado:** propuesta. Mergear, cerrar o borrar ramas es decisión de Nico (`CLAUDE.md`: "No tocar sin decisión explícita: borrado/cierre/merge de ramas"). Nada de esto se ejecutó.

**Criterio objetivo usado** (no opinión): para cada PR se contó cuántos commits de su head NO están contenidos en ninguno de los 4 troncos vivos — `foundation/f0b-compatibility-probe`, `feat/unified-nt8-viewer-20260920` (#48), `feat/edge-brain-durable-hippocampus-20260922` (#56), `feat/frontier-expansion-lab-20260921` (#54). `uniq=0` significa que todo el contenido del PR ya vive en otra rama: cerrarlo no pierde nada.

## Diagnóstico

- **40 PRs abiertos, 3 troncos vivos reales.** Todo lo de septiembre cuelga de `foundation` en una cadena lineal: `foundation → audit/edge-discovery-factory-foundation-20260919 (+20, sin PR propio) → #43 → {#48 visor, #46 → #52 → #56 Brain, #47 → #50 → #51 → #54 Frontier}`.
- **Bloqueo estructural:** la raíz de la cadena (`audit/edge-discovery-factory-foundation-20260919`, 20 commits sobre `foundation`) **no tiene PR**. Ningún PR de septiembre puede mergearse a `foundation` sin pasar por ella.
- **#51 apunta a `main`** (baseline, no se mergea) con 1.582 archivos que incluyen `archive/parquets_v1_export`, `archive/nt8_cs_backup`, `data/nt8_oracles`. Base equivocada; no mergear tal cual.
- **CI:** solo #48 está verde. El fix de causa común de CYCLE-001 (`fix/cycle001-ci-common-cause-20260922`) existe pero no está propagado a los otros troncos.

## Grupo 1 — Cerrar: contenido ya absorbido (`uniq=0`)

| PR | Contenido ya está en | Acción |
|---|---|---|
| #28, #29, #31 | `foundation` (y los 3 troncos) | cerrar como "merged via foundation" |
| #35, #40, #43 | los 3 troncos | cerrar tras mergear un tronco (son ancestros) |
| #39 | #48 | cerrar tras mergear #48 |
| #50, #51 | #54 Frontier | cerrar; #51 además tiene base `main` equivocada |
| #56, #54, #48 | son los troncos | — ver grupo 2 |

## Grupo 2 — Los 3 troncos a integrar (en este orden)

1. **Abrir PR** `audit/edge-discovery-factory-foundation-20260919 → foundation` (raíz sin PR, 20 commits). Revisar y mergear primero.
2. **#48 visor L2** (`uniq` propio, CI verde, draft). Contiene #43, #35, #39, #40. Pasar a ready tras decisión.
3. **Brain** #46 → #52 → #56 (+#49 lateral, 5 commits únicos). Propagar fix de CI, verificar verde, mergear en orden.
4. **Frontier #54**: rebasear sobre `foundation` (hoy cuelga de #51 con base `main`). Contiene #50/#51. `SATURATED_STOP` de YM/BT2A ya está registrado en el Brain (`research_history_ledger`), así que la línea económica YM no requiere más integración que su acta.

## Grupo 3 — Contenido único viejo (agosto / mediados de septiembre)

No se pueden cerrar sin perder commits. Decidir por PR: **archivar** (tag `archive/<rama>` + cerrar, reversible) o **rescatar**.

| PR | uniq | Tema | Sugerencia |
|---|---:|---|---|
| #34 | 10 | paridad HFT V2 nativa 38 campos | **rescatar**: certificación de paridad NQ, relevante al visor |
| #8 | 13 | G2-A1 calibration hardening | decisión de Nico ya pendiente en `CLAUDE.md` (no mergear sin OK) |
| #15, #16, #18, #20 | 35/23/43/51 | BT2A gate2 / P2-A / P2-B | archivar: línea BT2A cerrada (YM saturada, GC P2-B sin continuidad) |
| #22–#25 | 51–97 | aVolCluster NQ / Kaggle frozen / BT2 sweep | archivar salvo que aVolCluster se retome como campaña |
| #11, #12, #13 | 15/2/28 | BigTrap2 nulls, ZAMR | archivar: iman de zona `CLOSED` |
| #14 | 21 | crypto context | archivar |
| #9, #17, #19, #21, #27, #32, #33, #41, #46, #47, #52 | 1–9 | varios | revisar individualmente; varios son 1–3 commits (docs, fixes chicos) |

## Resultado esperado

De 40 PRs a **1 rama viva** (`foundation`) + 1 PR de integración a la vez. Es la regla de `CLAUDE.md` ("Todo el trabajo va a una rama; si hace falta una auxiliar, se mergea el mismo día") que hoy está rota.

Aporte al referente: ninguno directo — reduce el costo de integración que hoy compite con research por el tiempo disponible, y elimina la clase de falla de "ramas divergentes que cada lado lee como verdad".

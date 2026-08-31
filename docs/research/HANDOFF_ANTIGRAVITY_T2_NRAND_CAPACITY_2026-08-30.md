# HANDOFF — Antigravity: corrida T2 (capacity check N_RAND) de Gate 1 NQ en Kaggle

**Para:** agente Antigravity (Google) · **De:** Notion AI (auditor) · **Fecha:** 2026-08-30
**Tu tarea es UNA SOLA:** correr el capacity check N_RAND de Gate 1 NQ contra datos reales en Kaggle y cerrar el binding `N_RAND_capacity_ok` con evidencia. Nada más.

## 0. Antes de tocar nada

1. **Leé la última entrada del canal** (`docs/audits/CANAL_NOTION_AI_2026-08-30_0*.md`, rama `audit/notion-ai-sltp-p2b-provenance-20260830`). Claude (otro agente) se reanuda ~23:01 ART; si una entrada más nueva que la 016 dice que T2 ya cerró, tu tarea ya está hecha — verificá los hashes y no dupliques.
2. **El kernel de Claude puede no haber fallado.** El usuario cree que dio FAILED, pero los kernels de Kaggle terminan server-side aunque nadie los mire. Primer paso real: verificar el estado del kernel en la cuenta de Kaggle (status + logs). Si SUCCEEDED → solo falta recoger y verificar el output (§4). Si FAILED → leé el log, diagnosticá, corregí, re-lanzá (§3). No relances a ciegas.
3. **El código del kernel de Claude puede no estar en el repo.** Al commit `d229bbb2` (tip de `research/bt2a-nq-gate1-outcomes-runner-v1-20260830`) no hay commit que pushee el kernel de T2 — fue escrito y probado localmente con sintéticos, y la pausa llegó antes del push. Buscá en ramas recientes un kernel de capacidad; si no existe, escribilo vos según §3 (es una orquestación fina sobre un módulo puro ya hecho y testeado — no es el runner de outcomes).

## 1. Orden de lectura obligatorio

1. `CLAUDE.md` (reglas del proyecto).
2. Este documento.
3. Canal 013 y 014 (la definición firmada y tu habilitación) y, si querés el contexto completo, 009 (adjudicación de la cláusula del runner).
4. La ley de la tarea: bloque `n_rand_matching_definitions` en `specs/bt2a_nq_gate1_v1.draft.json` @ `research/bt2a-nq-gate1-power-closure-20260830` (tip) y en `specs/bt2a_nq_gate1_runner_contract_v1.draft.json`. Definiciones firmadas por Nico (D6 + corrigendum ratificado):
   - `coarse_phase`: `floor(chicago_minutes_since_17:00 / 240)` — **bloques de 4 horas, 6 fases** (corrigendum ratificado; NO 2 horas — eso era la inconsistencia ya corregida).
   - `availability`: la ventana forward del horizonte máximo (250 observaciones) cabe completa dentro de la sesión CME del evento.
   - `local_volatility_bin`: quintil por contrato de la mediana de |Δtick| en los 500 ticks estrictamente pre-ancla; <500 previos → estrato visible `INSUFFICIENT_HISTORY`.

## 2. Qué existe ya (no reinventar)

- **Módulo puro, 26 tests sintéticos en verde:** `edgelab/research/bt2a_nq_gate1_nrand_capacity.py` @ `5803d85` (rama `research/bt2a-nq-gate1-outcomes-runner-v1-20260830`, tip `d229bbb2` con el docstring ya corregido). Implementa las tres estratas + `capacity_report()`.
- **Pool de candidatos N_RAND = TODOS los ticks elegibles de la sesión** (patrón GC), no solo eventos K_ABS → la volatilidad rodante se computa sobre la serie completa de ticks.
- **Regla de capacidad** (espejo del margen que `_sample_without_own` exige en runtime): por estrato con `n` eventos K_ABS que necesitan match, el pool debe tener `>= n + 1` miembros.
- Protocolo de ejecución: `docs/research/KAGGLE_FROZEN_EXECUTION_PROTOCOL_V1_2026-08-28.md` + `tools/run_kaggle_frozen_job.py`. Inputs: event store NQ congelado (manifest `b3177b51892298fc75a8bc6ab156d15525473aef52d71e4c717da148501ba544`) + registry + paquete privado.
- La corrida es diagnóstico target-free habilitado por el `target_free_note` firmado + canal 014: no requiere token de Nico porque no abre ningún outcome.

## 3. Si tenés que escribir/relanzar el kernel

- Orquestación fina sobre el módulo puro: clonar el repo en el commit fijado, cargar coordenadas del event store, computar las tres estratas por evento, armar pools por estrato, llamar `capacity_report()`, emitir el reporte JSON.
- Errores que Claude ya encontró y corrigió (no los repitas): (a) importar el módulo ANTES de clonar el repo — cloná primero; (b) el archivo de coordenadas es `NQ_09-25.parquet`, no `09-25.parquet` — usá glob, no construcción directa de ruta.
- **Verificá localmente con datos sintéticos antes de gastar una corrida de Kaggle** (ventana rodante de volatilidad, reset en frontera de sesión, minutos desde apertura) — como hizo Claude.
- Reporte con el patrón del repo: `schema_version: bt2a_nq_gate1_nrand_capacity_report_v1`, `N_RAND_capacity_ok` booleano global, tabla por estrato, conteos, attestation (hashes de inputs, commit del código, kernel id, timestamps UTC).

## 4. Reglas duras (violación = trabajo descartado)

1. **Solo ticks estrictamente pre-ancla** para `availability`/`local_volatility_bin`. Si el chequeo necesitara mirar post-evento, FRENÁ y escribí al canal.
2. Cero outcomes, cero P&L, cero first-passage, holdout intacto.
3. No modifiques specs congelados ni el runner contract — la única edición de spec permitida es el cierre del binding con evidencia (§5).
4. No escribas el CLI del runner de outcomes (cláusula `runner_file_must_not_exist_while_blocked`, canal 009).
5. **Si el check da capacidad insuficiente, NO aflojes márgenes ni estratos para que dé verde**: reportá `N_RAND_capacity_ok: false` con la tabla — es un resultado válido y valioso, y frena para decisión de Nico.
6. Nada se borra ni se reescribe: historia append-only.

## 5. Entregable y cierre del binding

1. Corrida en Kaggle → reporte.
2. Commit del reporte en una rama nueva desde el tip de `research/bt2a-nq-gate1-power-closure-20260830`, con manifiesto (inputs hash-bound, commit del código, kernel id, duración).
3. Cierre del binding SOLO si el reporte da `true`: en `specs/bt2a_nq_gate1_power_design_v1.draft.json` poner `arm_density.N_RAND_capacity_ok = true` + `nrand_capacity_evidence` = {report_file, report_sha256, run_commit, kernel_id}; recomputar `payload_sha256` (canonical: `json.dumps` del cuerpo sin `payload_sha256`, `sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`) y re-pinnar `dependencies.power_design_file_sha256` en `specs/bt2a_nq_gate1_v1.draft.json`. Si da `false`: NO cerrar — el binding queda abierto con evidencia y se escala a Nico.
4. Entrada en el canal (próximo número libre, `docs/audits/CANAL_NOTION_AI_2026-08-30_0XX.md` en la rama de auditoría) con: estado real del kernel de Claude que encontraste, qué hiciste, hashes, resultado. El auditor verifica tu cierre contra los hashes — reportá exactos.

## 6. Lo que NO es tu tarea

P2B (artefacto o retracción), el CLI del runner de outcomes, Romano-Wolf/MCS, la campaña SL/TP, cualquier freeze o token de la secuencia. Esos son de Claude o de Nico.

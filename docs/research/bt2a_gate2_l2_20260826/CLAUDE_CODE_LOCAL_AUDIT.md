# Auditoría local para Claude Code

## Objetivo

Verificar los artefactos que permanecen sólo en `E:\DatosNT8` sin reabrir outcomes ni
recomputar nada. La salida debe ser un manifiesto pequeño, sin subir Parquets ni datos
crudos.

## Prompt para Claude Code

```text
Estás auditando una corrida científica existente. NO rerunees detectores, NO abras
outcomes, NO borres ni reescribas parciales y NO uses --resume todavía.

Repositorio: EdgeLab
Rama de la corrida: work/futures-l2-context-foundation-20260825
Rama del informe auditor: work/bt2a-gate2-l2-audit-20260826

1. Registra git rev-parse HEAD, git status --porcelain y git log -5.

2. Audita E:\DatosNT8\replay.csv\GC JUN26\gate_ctx4:
   - enumera archivos, bytes y sha256;
   - exige run_manifest.json, gate_l2_context_model.json,
     gate_l2_target_free_report.json y gate_l2_context_labels.parquet;
   - publica code_commit_start/end, dirty_start/end, model_id, sesiones train/eval,
     sesiones excluidas, clock_reference_resolved, outcomes flags;
   - con PyArrow, cuenta labels, minutos y sesiones por context_state/context_group,
     coverage, context_as_of_ok, persistencia y flip rate;
   - comprueba available_source_row estrictamente anterior a cualquier event_source_row
     sólo si hay un event file del MISMO stream;
   - no intentes unir .Last por timestamp.

3. Audita E:\DatosNT8\event_store_gc_all5:
   - enumera los 5 Parquets y event_store_manifest.json con bytes y sha256;
   - valida esquema, orden (ts_utc_ns, source_row), duplicados y direction en {-1,+1};
   - exige que (fill_ts_utc_ns,fill_source_row) sea estrictamente posterior a
     (ts_utc_ns,source_row);
   - cuenta fills que cruzan session_id o están en el último tick;
   - filtra por las 234 sesiones de
     specs/bt2_absorption_gate1_all5_sessions_2026-08-26.json y compara por
     contrato/sesión con los CSV Gate 1;
   - reporta separadamente población bruta y población Gate 1 elegible;
   - no lo llames canónico si no hay equivalencia 1:1.

4. Audita E:\DatosNT8\bt2a_sweep_overnight_20260826\partials:
   - cuenta archivos y matriz config_id x contract;
   - lista unique code_commit, input_sha256 y config_id;
   - verifica target_free=true y outcomes_opened=false en todos;
   - busca y falla si aparece cualquier clave mfe, mae, pnl, return, hit_rate,
     target_first o stop_first;
   - para cada event_pit exige feature_available_at_ns <= event_time_ns;
   - compara partial.code_commit con HEAD actual;
   - calcula exactamente qué pares faltan de los 396;
   - declara RESUME_SAFE sólo si todos los parciales uniformes coinciden con el commit
     desde el que se reanudará.

5. Escribe, sin datos crudos:
   docs/research/bt2a_gate2_l2_20260826/LOCAL_AUDIT_RESULT.json
   docs/research/bt2a_gate2_l2_20260826/LOCAL_AUDIT_RESULT.md

6. El JSON debe contener hashes de cada artefacto, checks pass/fail, conteos y causas.
   No uses adjetivos como complete/canonical sin que los checks correspondientes pasen.

7. Corre tests relevantes sin modificar outputs. Commit sólo los dos informes pequeños
y cualquier test/auditor nuevo; nunca los Parquets ni los parciales.
```

## Criterio de aceptación

La auditoría local cierra únicamente si permite reproducir, desde hashes y conteos:

- qué código produjo cada familia de archivos;
- si el árbol estaba limpio;
- qué sesiones y estados fueron producidos;
- si el Event Store coincide o no con Gate 1;
- si el sweep puede reanudarse sin recomputar ni mezclar commits.

# EdgeLab — siete frentes de referencia y ejecución continua

**Fecha:** 2026-09-20  
**Estado:** `ACTIVE_AUDIT_NO_OUTCOMES`  
**Base documental:** `ff8aa2de5e85ad5fe03acae3752d2da33aed9878`  
**North Star:** descubrir edge neto, robusto, OOS y ejecutable; visor, paridad e infraestructura son medios.

## Invariantes

- `LLM_PROPOSAL_NOT_EVIDENCE`
- `NO_SELF_APPROVAL`
- `LEDGER_APPEND_ONLY`
- `NOT_OBSERVED != ZERO_ACTIVITY`
- `REMOTE_LISTED_PENDING_DOWNLOAD_PROOF != REMOTE_VERIFIED`
- `PREEXISTING_OUTCOME_EXPOSURE=YES`
- `HOLDOUT_CONTAMINATED_FOR_THIS_HYPOTHESIS=YES`
- `selected_signal_semantics=null`
- `execution_enabled=false`

## 1. Matriz de autoridad y vigencia

| Nivel | Fuente | Uso | Estado |
|---|---|---|---|
| 0 | Spec/manifest congelado del objeto | contrato exacto del objeto | prevalece siempre |
| 1 | `docs/NORTH_STAR.md` | objetivo económico y gates | canónico |
| 2 | `AGENTS.md` | reglas operativas y científicas | canónico |
| 3 | `docs/CURRENT.md`, `PENDIENTE.md` | continuidad | válidos con fecha; requieren reconciliación |
| 4 | dossiers y handoffs | evidencia histórica | no prevalecen sobre blobs ni auditorías posteriores |

Drift confirmado: los índices antiguos nombran `foundation/f0b-compatibility-probe`; la línea de septiembre 20 usa `feat/edge-discovery-brain-foundation-20260919`. La custodia 56/56 vive en `3ae3c3e` y todavía no es ancestro de la base del Brain/Viewer/Pilot. No se debe declarar convergencia hasta integrarla explícitamente.

## 2. Grafo de ramas y supersesión

```text
main@cde6d93
└─ foundation/f0b@46d97e8
   ├─ audit/edge-discovery-factory-foundation@3ae3c3e   [custodia 56/56]
   └─ feat/edge-discovery-brain-foundation@84eea97
      ├─ feat/reconstruct-edge-brain-complete@ff8aa2d   [PR #46]
      ├─ feat/ym-bt2a-retest-kaggle-pilot@ad67e13       [PR #47]
      └─ feat/unified-nt8-viewer@cec16c2                [PR #48]
```

Las tres ramas hijas son paralelas; ninguna contiene a las otras. `main` es baseline preservada, no living integration.

## 3. Contrato Factory ↔ Brain

| Factory | Brain | Relación |
|---|---|---|
| `hypothesis_registry` | `causal_hypothesis` | `OPERATIONALIZED_AS` |
| `experiment_registry` | `analysis_episode` | `IMPLEMENTED_BY` |
| ejecución del DAG | `step_execution` | `USED_IN` |
| criterio preregistrado | `expectation` | `TESTED_BY` |
| resultado negativo | `failure_event` / `counterexample` | `CONTRADICTED_BY` |
| resultado reproducible | `success_event` | `SUPPORTED_BY` |
| síntesis acotada | `lesson_candidate` | `DERIVED_FROM` |
| regla general | `learning_rule` | sólo tras adjudicación y réplica |

Bloqueo de schema: `schemas/edge_factory/zone_events.json` exige `executable_fill_ts` entero. Un store target-free no debe fabricar fill. Debe distinguir `NO_EXECUTABLE_FILL_AVAILABLE` de un fill observado. Hasta reparar el contrato, el adapter debe abstenerse de promover esas filas como eventos causales ejecutables.

Mapeo temporal mínimo:

```text
origin_ts            <- formation_start_ns
formation_end_ts     <- formation_end_ns
signal_available_ts  <- available_at_ns
executable_fill_ts   <- sólo primer tick ejecutable realmente observado
```

## 4. Inventario de stores y schemas

- Tier 0: ticks canónicos por contrato en Kaggle; 56/56 reportados `REMOTE_VERIFIED` en `3ae3c3e`.
- Tier 1: barras derivables; no confundir slices con serie continua.
- Tier 2: store target-free de zonas HFT; 299 particiones reportadas verificadas.
- Tier 3: bundles del visor; `PAUSED_NOT_UPLOADED`, regenerables y no autoritativos.
- Factory: `zone_events`, `zone_events_exploratory`, `corridor_events`, `hypothesis_registry`, `experiment_registry`, `negative_results_registry`, `analysis_dependencies`.
- Brain: 35 schemas; ledger hash-chained como fuente canónica, proyecciones reconstruibles.

Gaps principales: identidad de formación separada del chart, fill target-free nullable/typed, enlace de hashes de dataset a episodio, y una única enumeración de estados científicos compartida.

## 5. Veredicto temporal BT2A

La reparación `cec16c2` restauró aliases y agregó timestamps explícitos, pero no cierra la semántica:

1. `bigtrap2absorption.run()` es tick-driven; ignora `bars` y agrupa `TapeWindowTicks` ticks.
2. `build_run()` etiqueta esas zonas con el `bar_key` del contexto de ejecución, que puede ser `time_5m`; eso no demuestra formación M5.
3. En legacy, `created_ms=blk_ts[-1]` es cierre. El fallback `created_ms/1000 + duración` puede sumar la duración dos veces.
4. El renderer conserva default universal `300` y `drawCorredoresDemo()` referencia `barDurationSec` fuera de scope.
5. Los tests llamados productor→exportador no ejecutan `bt2.run()`.

Por eso el estado correcto sigue siendo `VIEWER_SEMANTICS_BLOCKED`. Se abrió nueva revisión formal en PR #48.

## 6. Primer AnalysisEpisode

El episodio `EPISODE-YM-BT2A-RETEST-TARGETFREE-20260920` queda en `PLANNING` y con outcomes cerrados. Pregunta: si, tras disponibilidad causal, esperar el primer retorno cualificado al rectángulo genera una población de entradas distinta de la entrada inmediata.

Políticas congeladas: inmediata; waits 25/100 ticks; retest departure `{2,4}` × depth `{0,.5,1}` × max wait `{250,1000}` = 15 políticas. Outputs: conteos, cobertura, departure, retest, depth, wait, invalidación, expiry, session end y censura. `NO_ENTRY_CENSORED` nunca es pérdida ni cero actividad.

El screenshot de julio sólo origina hipótesis: está dentro del holdout y no puede confirmar ni ajustar parámetros.

## 7. Consolidación del visor

Único entrypoint productivo: `viewer/nt8_bridge/index.html`. Las demás páginas son fixtures/diagnóstico. Reglas:

- separar `formation_spec` de `display_bar_key`;
- ningún default universal de duración;
- tick/volume sin disponibilidad explícita: abstención;
- helper único para parsear duración temporal;
- integración real productor→exportador→renderer;
- browser smoke que recorra señales, corredores y perfil de volumen;
- actualizar `viewer_manifest.json` sólo después de cerrar los bloqueos.

## Orden de ejecución

1. Corregir y certificar PR #48.
2. Incorporar custodia `3ae3c3e` a una base de integración explícita.
3. Reparar el contrato de fill target-free.
4. Implementar adapter Factory→Brain y escribir el episodio al ledger.
5. Ejecutar el piloto target-free sobre scope YM preholdout congelado.
6. Adjudicar como máximo `LESSON_CANDIDATE`.
7. Habilitar outcomes únicamente mediante campaña preregistrada y autorización explícita.

## Aporte al referente

Se transformaron siete frentes dispersos en una secuencia auditable que conecta custodia, eventos causales, Factory, Brain y visor sin convertir artefactos visuales o fills sintéticos en evidencia económica.
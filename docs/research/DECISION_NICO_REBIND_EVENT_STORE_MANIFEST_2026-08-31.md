# DECISIÓN Nico — Rebind del manifest del event store BT2A NQ (2026-08-31)

**Token (verbatim, Notion chat, 2026-08-31 ~11:58 ART):**
`AUTHORIZE_REBIND_BT2A_EVENT_STORE_MANIFEST_V1`

**Contexto:** intento de corrida nocturna de Gate 1 (acta
`docs/research/BT2A_NQ_GATE1_RUN_ATTEMPT_2026-08-31_NOCHE.md`). El manifest del event
store reconstruido (`bt2a-nq-event-store-rebuild-v2`, COMPLETE) no calza con el binding
congelado del spec porque el manifest se auto-embebe su propio `frozen_commit` — y un
commit no puede contener el hash de sí mismo. El propio spec congelado lo anticipaba en
`dependencies.binding_notes.bt2a_creation_event_store_manifest_sha256`: *"if the rebuilt
store is ever re-uploaded this binding must change"*.

## Qué se autorizó

Actualizar **un solo campo** de `specs/bt2a_nq_gate1_v1.draft.json`:
`dependencies.bt2a_creation_event_store_manifest_sha256`

- viejo: `b3177b51892298fc75a8bc6ab156d15525473aef52d71e4c717da148501ba544`
- nuevo: `1e45c43fa60327b67aeb618d00b4137b82cc6c44ad43f348fc5bca8250ef90ea`

## Qué NO cambia (los datos)

Reportado por el `hash_verification_result.json` del kernel de rebuild (evidencia del
acta; verificado en repo el binding viejo, la nota de procedencia y la estructura
autorreferencial del generador):

- parquet byte-idéntico: `96281e880d7949f9dfcf3364091d9ce7696f778e59e6f2e2243995becdd38808`
  (match explícito contra el esperado congelado)
- 152.695 eventos / 234 sesiones — igual a lo congelado
- `event_rows_payload_sha256` del lado de los datos sin cambios (`93a70661...`)

## Cascada ejecutada en el mismo cambio

- Hash del spec: `5c5857a5e486edcb68c73f0a0cc73be4d20946ef49d9b652affa4060b7b59d8e`
  → `b9e75c2533091c3dc8a3a2c8b8b8efde6eb6dfe1313efae48a4b4885366695c3`
- `FROZEN_SPEC_SHA256` en `tools/run_bt2a_nq_gate1_outcomes.py` actualizado al nuevo pin.
- El status del spec sigue `FROZEN_PREFLIGHT_READY` (el rebind es la contingencia
  prescrita, no un cambio de diseño).

## Decisión de alcance: el power design NO se toca

`specs/bt2a_nq_gate1_power_design_v1.draft.json` referencia el manifest viejo dos veces
(`source_manifest_file_sha256`, `file_sha256`). Esas referencias son **proveniencia
histórica** — los números de power se computaron contra el manifest original — y siguen
siendo verdaderas: el parquet subyacente es byte-idéntico. Editar el power design
cambiaría su hash (`05fb1d72...`) y cascaría un segundo archivo congelado dentro del
primero sin cambiar ningún dato ni ninguna puerta de ejecución. Se deja intacto a
propósito.

## Resta para la corrida (mecánico)

1. Subir el dataset `edgelab-bt2a-nq-event-store` (manifest + parquet del rebuild).
2. Lanzar `bt2a_nq_gate1_16cell_runner.py` en Kaggle: el preflight físico embebido corre
   primero y aborta fail-closed si algo no calza. Token 4 sigue sin gastarse hasta ahí.

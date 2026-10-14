# Decisión de Nico — tokens de implementación y ejecución BT2A NQ Gate 1 (2026-08-31)

**Registrado 2026-08-31 01:08 ART.** Canal: chat Notion AI, mensaje verbatim
de Nico con los dos tokens juntos, once minutos después del freeze del spec
(commit `8b1f334f`, backfill en `c70bdb5d`).

## Tokens otorgados (verbatim)

- `AUTHORIZE_IMPLEMENT_BT2A_NQ_GATE1_16CELL_V1` — token 3,
  `implementation_token_label` del runner contract
  (`specs/bt2a_nq_gate1_runner_contract_v1.draft.json`).
- `AUTHORIZE_RUN_BT2A_NQ_GATE1_V1` — token 4, `run_token_label` del spec Gate 1
  y del runner contract.

## Qué autoriza cada uno

**Token 3 (implementación):** escribir el runner de 16 celdas. La cláusula del
runner contract `runner_file_must_not_exist_while_blocked` deja de aplicar:
con la implementación autorizada, el diseño ya no está bloqueado. El runner se
construye contra el contrato congelado (`estimand_resolution_required_before_implementation`,
estado `RESOLVED`) y se prueba primero contra datos sintéticos con ground
truth, como ya se hizo con `edgelab.research.bt2a_nq_gate1_outcomes` y
`bt2a_nq_gate1_nrand_capacity`.

**Token 4 (ejecución):** la corrida en Kaggle, cuando y solo cuando se cumplan
todas las puertas físicas, que este token no reemplaza:

1. Runner implementado y con tests sintéticos verdes.
2. Execution spec de Kaggle instanciado para Gate 1 desde
   `specs/kaggle_frozen_execution_v1.template.json`, con `run_token` embebido,
   y congelado (el sobre `edgelab.kaggle.execution.require_authorized` exige
   spec FROZEN + `run_capability` + token exacto + árbol git limpio en el
   commit congelado).
3. Artefactos físicos presentes y verificados por hash en el preflight
   completo: event store manifest `b3177b51...`, package manifest
   `2336b296...`, effective input registry `f9bcf5ee...`, resultado V2 de
   BigTrap2 `e162a0e0...` (este último además necesita staging físico bajo
   `--bt2-artifact-dir`, pendiente declarado en el spec).
4. `preflight_bt2a_nq_gate1.py --preflight-only` en verde sobre ese entorno.

## Qué NO cambió con estos tokens (medido, no retórica)

- **Ningún spec se editó.** El spec Gate 1 está FROZEN y liga el runner
  contract por hash (`runner_contract_file_sha256 = 20ae6a38...`): escribir el
  token dentro del runner contract rompería esa ligadura y pondría
  `missing_bindings` en rojo. Por eso el registro vive en este documento.
- `execution_authorized` sigue `false` en el spec y en el runner contract.
  `validate_runner_contract` lo exige por diseño (levanta si alguno es true) y
  los tests lo asertan; la capacidad de ejecución corresponde al execution
  spec congelado en el momento de la corrida, no al documento de diseño.
- Firewall intacto: `GATE1_RUN`, `OUTCOMES_ACCESSED`, `PNL_ACCESSED`,
  `HOLDOUT_TOUCHED` y los demás flags siguen `false`. Ningún outcome, PnL ni
  dato de holdout fue tocado para registrar estos tokens.

## Nota de auditoría

Los tokens 3 y 4 llegaron juntos, antes de que exista el runner. No rompe
nada — sin runner y sin execution spec no hay nada que pueda ejecutar — pero
queda escrito que la autorización de corrida es anterior a la existencia del
artefacto que corre. Si el runner terminara distinto de lo que el contrato
dice hoy, este token no lo cubre: el contrato manda.

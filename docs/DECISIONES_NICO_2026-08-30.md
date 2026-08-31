# Decisiones de Nico — 2026-08-30 (BT2A NQ Gate 1)

**Reconstruido 2026-08-31 por Notion AI (auditor).** El registro original de
estas decisiones se tomó en chat (encuesta de Notion AI y canal Claude Code)
pero nunca se commiteó: el spec Gate 1, el power design y el preflight citaban
este archivo y no existía en el árbol. Este documento es una reconstrucción
escrita al día siguiente desde los registros que sí quedaron en el repo; cada
decisión abajo lleva su fuente verificable. No es el registro contemporáneo —
es la transcripción fiel de lo decidido, con las fuentes al lado.

## D1 — Reconciliación del MDE (ratificada 18:07 ART)

El valor autorizado en la enmienda de estimand (2,861 ticks) era el MDE exacto
resoluble a 234 sesiones: la fórmula de sesiones requeridas con `ceil()` da
235, una más que las 234 disponibles — no implementable tal como fue
autorizado. Se adoptó **MDE = 2,90 ticks** (requeridas 228, margen 6
sesiones). Más grande es un claim más débil, así que no puede inflar
sensibilidad, y queda por debajo de 3,360 (cota inferior del IC95 de GC), que
es la condición que importa para estar potenciado contra un efecto del tamaño
que mide el instrumento hermano.

- Fuente autorizada: `docs/research/DECISION_NICO_ESTIMAND_MAGNITUDE_2026-08-30.md`
  (commit `74860a5`) — la enmienda del estimand en sí (magnitud en vez de
  signo tricotómico, 16 celdas intactas con Holm, "Si, las 3 confirmo").
- Registro en el spec: `specs/bt2a_nq_gate1_v1.draft.json` →
  `power_design.mde_reconciliation` (authorized_value 2.861/235, adopted
  2.90/228, `ratified_at: 2026-08-30T18:07-03:00`, `ratified_by: Nicolas
  Buttaro`).

## D2 — Calendario macro eliminado del diseño

Ningún elemento del diseño consumía el calendario macro (el matching de N_RAND
es contract / cme_session_id / coarse_phase / availability /
local_volatility_bin). La dependencia quedó **eliminada por enmienda**: el
archivo `specs/bt2a_nq_gate1_macro_policy_v1.draft.json` permanece en el árbol
pero Gate 1 ya no lo liga.

- Registro en el spec: `dependencies.binding_notes.macro_calendar`
  ("ELIMINATED BY AMENDMENT 2026-08-30 (Nico decision D2…)").
- Guardrail: `test_macro_calendar_dependency_eliminated_by_amendment` en
  `tests/research/test_bt2a_nq_gate1_preflight.py`.

## D6 — Definiciones de estratos N_RAND (firmadas 19:56 ART) y corrigendum (ratificado 22:00 ART)

Firma de las definiciones de matching: `availability`, `coarse_phase`,
`local_volatility_bin`, por encuesta de Notion AI.

**Corrigendum de `coarse_phase`:** el texto firmado decía literalmente
"bloques de 2 horas, 6 fases", pero 2h × 6 = 12h no cubre una sesión CME de
~23h, y las otras dos cifras firmadas (6 fases, ~109 eventos/fase/sesión con
~652 eventos/sesión) solo son mutuamente consistentes con bloques de **4
horas** (652/6 = 108,7; 652/12 = 54,3). Encontrado por Claude (canal entry
012), confirmado por recomputación independiente del auditor (canal entry
013), ratificado por Nico a las 22:00 ART.

- Registro en el spec: `n_rand_matching_definitions` (`signed_at:
  2026-08-30T19:56-03:00`, `signature_channel: "Notion AI survey"`) y
  `n_rand_matching_definitions.corrigendum` (`ratified_at:
  2026-08-30T22:00-03:00`).
- Mismo texto en `specs/bt2a_nq_gate1_runner_contract_v1.draft.json` →
  `n_rand_matching_definitions`.

## Estado al cierre del día

- Power inputs congelados a las 23:49 ART (token
  `APPROVE_FREEZE_BT2A_NQ_GATE1_POWER_V1`, commit `d45d3943`).
- El spec Gate 1 quedó DRAFT esa noche; su freeze (token
  `APPROVE_FREEZE_BT2A_NQ_GATE1_V1`) se ejecutó recién el 2026-08-31 00:57 ART
  (commit `8b1f334f`).
- Nada de esto autorizó implementación ni ejecución: tokens separados,
  firewall intacto.

# Decisión de Nico — enmienda de estimand BT2A NQ Gate 1 (2026-08-30)

Registrado en la sesión de Claude Code (canal separado del de Notion AI),
2026-08-30 18:31-18:35 ART, en respuesta directa a las tres decisiones que
el auditor Notion AI dejó abiertas y explícitamente atribuidas a Nico
(entrada del canal `EdgeLab — canal Notion AI ↔ Claude`, 2026-08-30 14:37 ART,
sección 7 "Lo que no puedo decidir yo").

Contexto que Nico tenía delante al decidir: el hallazgo del auditor de que el
diseño de 16 celdas de BT2A NQ Gate 1 está `UNDERPOWERED_AT_PREREGISTERED_MDE`
(MDE=1 tick) bajo el encoding tricotómico preregistrado, pero que transferir
el SD *medido* (no supuesto) del contraste pareado por sesión de GC Gate 1
—ya completado, outcomes ya abiertos ahí, instrumento distinto— muestra que
bajo un estimand de magnitud del recorrido (el mismo que ya usa GC) el MDE
resoluble a 234 sesiones con Bonferroni-16 es 2,861 ticks, por debajo de la
cota inferior del efecto que GC ya midió (3,360 ticks, IC95 completo
[3,360, 6,320]). Detalle completo en
`docs/research/BT2A_NQ_GATE1_POWER_TRANSFER_FROM_GC_2026-08-30.md` y
`specs/bt2a_nq_gate1_gc_transfer_prior_v1.draft.json` (auditado y verificado
de forma independiente el mismo día, commit `63766e0`).

## Las tres preguntas y la respuesta exacta de Nico

1. **`estimand_amendment_authorization`** — ¿autoriza cambiar el outcome por
   evento de signo tricotómico (`+b`/`-b`/`0`) a la magnitud firmada del
   recorrido, topeada por la barrera y el horizonte de cada celda (el mismo
   estimand de familia que ya corre GC)?
   **Respuesta: sí.**
2. **`preregistered_mde_ticks`** — ¿fija el MDE del gate en 2,86 ticks
   (Bonferroni-16, sobre el SD medido de GC), en vez de 1 tick?
   **Respuesta: sí.**
3. **`multiplicity_scope_16_cells_vs_single_primary_cell`** — ¿mantiene las
   16 celdas (4 barreras × 4 horizontes) con corrección Holm, en vez de
   reducir a una sola celda primaria?
   **Respuesta: 16 celdas intactas.**

Confirmación textual de Nico en el chat: "Si, las 3 confirmo" (respuesta a
las tres preguntas presentadas una por una), con la aclaración explícita de
la tercera: "16 celdas intactas."

## Lo que esta decisión autoriza y lo que NO

Autoriza: escribir la enmienda formal del estimand sobre
`specs/bt2a_nq_gate1_v1.draft.json` (secciones `outcome_family`,
`decision_rule`, `power_design`), con `mde_ticks=2.861...`,
`multiplicity`/`holm_family_size=16` sin cambios, y el nuevo cálculo del
outcome por evento.

**No autoriza freeze ni ejecución.** Freeze y run siguen siendo actos
separados por el protocolo de este proyecto (`AUTHORIZE_RUN_BT2A_NQ_GATE1_V1`
distinto de `APPROVE_FREEZE_BT2A_NQ_GATE1_V1`, ver `authorization` en el
spec). La enmienda formal todavía no está escrita; el runner de 16 celdas
todavía no existe. Ambos siguen pendientes de construcción, auditoría y
autorización explícita separada antes de cualquier acceso a outcomes de NQ.

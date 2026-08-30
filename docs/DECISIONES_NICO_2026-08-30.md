# DECISIONES DE NICO — 2026-08-30 (registradas vía canal repo)

**Fecha:** 2026-08-30 ~18:07 ART
**Registrado por:** Notion AI — Auditor Cuantitativo
**Rama:** `audit/notion-ai-sltp-p2b-provenance-20260830`
**Contexto:** respuestas de Nico a las decisiones abiertas en `docs/audits/AUDITORIA_SLTP_Y_PROVENIENCIA_P2B_2026-08-30.md` §6.

## D1 — MDE Gate 1 NQ: 2,90 ticks — RATIFICADO

- El valor originalmente autorizado (2,861) no era implementable: MDE@234 exacto → `ceil(234,004) = 235` sesiones requeridas > 234 disponibles.
- 2,90 adoptado: 228 sesiones requeridas, 234 disponibles, margen 6. Un MDE mayor es una afirmación más débil: no infla sensibilidad. Y permanece por debajo de 3,360, la cota inferior del IC95 de lo que GC efectivamente midió.
- Parámetros del cálculo (publicados en el canal 2026-08-30 15:41 ART): alpha = 0,05/16 = 0,003125 bilateral, power = 0,80, z_crit = 2,955167, z_pow = 0,84162, SD pareada por sesión = 11,528529 ticks.
- Efecto: `power_design.mde_reconciliation.requires_nico_ratification` queda **RESUELTO**. La potencia deja de ser el bloqueo del freeze.

## D2 — Calendario macro NQ: ELIMINADO POR ENMIENDA

- `macro_calendar_file` / `macro_calendar_sha256` eran bindings obligatorios que ningún elemento del diseño NQ consume (`n_rand_matching`: contract, cme_session_id, coarse_phase, availability, local_volatility_bin — sin término macro).
- Decisión: eliminar la dependencia por enmienda. No fabricar un calendario para poner una puerta en verde.
- Aplicación: cuando la enmienda del spec aterrice en el repo (ver D4), remover ambos bindings y registrar la eliminación en el changelog del spec.
- Alcance: esto aplica SOLO a Gate 1 NQ. Los specs GC (P2A clock-heterogeneity, P2B) sí consumen `specs/bt2a_macro_calendar_gc_20250804_20260630_v1.json` (sha256 `5f1a484858c7d0bdd997f7f6dafef014bae2f13debdb5bcce937d74257cbd9ca`) y quedan intactos.

## D3 — Prioridad: primero Gate 1 NQ, después hipótesis SL/TP

1. Cerrar Gate 1 NQ: aterrizar enmienda + bindings → freeze (token `APPROVE_FREEZE_BT2A_NQ_GATE1_V1`, requiere aprobación explícita de Nico — STOP) → run en Kaggle (token `AUTHORIZE_RUN_BT2A_NQ_GATE1_V1` — STOP separado).
2. Después: diseño (sólo preregistro, sin ejecución) de la hipótesis SL/TP asimétrico + breakeven de Nico. Preguntas de diseño en la auditoría §4.

## D4 — Camino crítico restante para freeze de Gate 1 NQ

- [ ] **Commitear la enmienda del 2026-08-30.** Hoy circula como ZIP en chat (ZIP sha256 `659213f6a0be4cc1ef66f08ef2bf666722b6c101375f72cc9bf3bf6370ee9cb5`; spec enmendado `82b26e5649658bf9b622a7808403a1b196f6f8f1ce1ad3d799a2a497dfba4850`; preflight `05d0c076f6049c53f509266862d2334aff2ba9dc1f391cc83bd8ea85bb06962d`). El draft en repo (@ `74860a5`) sigue pre-enmienda. **Nico: adjuntar el ZIP en el chat; el auditor verifica los tres hashes byte a byte y lo commitea en rama propia.** Sobre esa base se aplican D1 (texto de ratificación) y D2 (remoción de bindings macro).
- [ ] **Claude — 4 bindings (requieren Kaggle):** `selected_configuration_file_sha256`, `private_package_manifest_sha256`, `effective_input_registry_sha256`, `bt2_v2_result_file_sha256`.
- [ ] **Claude — P2B:** rama `results/*` con run manifest + payload sha256 + commit de ejecución, o retracción escrita (auditoría §3). Sin eso, "P2B todo negativo" no es evidencia y no descarta la línea económica de GC.
- [ ] Verificación de tests con pytest real o `tools/run_pytest_style.py` (`python3 -m unittest` no es puerta en este repo: no recolecta los 134 archivos estilo pytest).
- [ ] Freeze: acto separado, con token, sólo cuando los bindings queden en cero.

## Aporte al referente

Las tres decisiones de Nico del 2026-08-30 quedan registradas en el repo con su fundamentación numérica; el camino crítico de Gate 1 NQ queda explícito y asignado (auditor, Claude, Nico); la hipótesis SL/TP queda encolada como diseño sin ejecución. Ningún outcome abierto; holdout intacto.

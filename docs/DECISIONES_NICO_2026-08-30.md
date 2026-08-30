# DECISIONES DE NICO — 2026-08-30 (registradas vía canal repo)

**Fecha:** 2026-08-30 ~18:07 ART (D1–D4), ~19:26 ART (D5) y ~19:56 ART (D6)
**Registrado por:** Notion AI — Auditor Cuantitativo
**Rama:** `audit/notion-ai-sltp-p2b-provenance-20260830`
**Contexto:** respuestas de Nico a las decisiones abiertas en `docs/audits/AUDITORIA_SLTP_Y_PROVENIENCIA_P2B_2026-08-30.md` §6 (D1–D4), a los puntos de diseño del diseño SL/TP+BE (D5) y a las definiciones de estratos N_RAND (D6).

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

- [x] **Commitear la enmienda del 2026-08-30** — HECHO. Paquete archivado byte-exacto en `docs/research/power_closure_20260830/` y merge canónico aplicado sobre el tip vivo (commits `95e58668`, `a1bebbc3` @ `research/bt2a-nq-gate1-power-closure-20260830`): D1/D2 aplicadas, validator con catch-up de ICC, power design file con valores ratificados + densidad K_BT2 verificada, suite 16/16 PASS en staging, 7/7 archivos verificados byte-exactos post-push.
- [x] **Claude — 4 bindings (Kaggle):** HECHO en `83884585` (cada uno con nota de proveniencia, incluida la discrepancia self-attestation vs valor ejecutado).
- [ ] **Claude — P2B:** rama `results/*` con run manifest + payload sha256 + commit de ejecución, o retracción escrita (auditoría §3). Agravante confirmado: el gate de P2B no verifica `execution_authorized` (canal 006 §2; incidente documentado por Claude en `docs/incidents/INCIDENTE_P2B_GC_AUTORIZACION_NO_TRAZABLE_2026-08-30.md`, `4559dbd`, enlazado en canal 009 §3).
- [~] **Claude — runner de outcomes 16 celdas:** motor de cómputo puro escrito y verificado (18 tests sintéticos, `edgelab/research/bt2a_nq_gate1_outcomes.py` @ `1fc184b`, avalado por el auditor como fuera de la cláusula de no-existencia — canal 009 §1). El CLI de orquestación espera el token de implementación (ver secuencia abajo): el contrato exige que el archivo del runner NO EXISTA mientras `implementation_authorized` sea `false` (lectura de Claude confirmada correcta por el auditor, doble convergencia).
- [x] **Claude — capacidad N_RAND:** DESBLOQUEADO por D6 (definiciones firmadas y enmendadas en ambos specs, commit `56cc4dc2`). Resta la implementación del capacity check (target-free).
- [ ] Verificación de tests con pytest real o `tools/run_pytest_style.py` (`python3 -m unittest` no es puerta en este repo: no recolecta los 134 archivos estilo pytest).
- [ ] **Secuencia de actos de Nico (corregida según el contrato del runner, canal 006 §5):**
  1. `APPROVE_FREEZE_BT2A_NQ_GATE1_POWER_V1` — freeze de inputs de potencia (habilita cuando el capacity check cierre `N_RAND_capacity_ok`).
  2. `APPROVE_FREEZE_BT2A_NQ_GATE1_V1` — freeze del spec Gate 1.
  3. `AUTHORIZE_IMPLEMENT_BT2A_NQ_GATE1_16CELL_V1` + decisión explícita — recién acá existe el CLI del runner.
  4. `AUTHORIZE_RUN_BT2A_NQ_GATE1_V1` — corrida en Kaggle.

## D5 — Campaña SL/TP asimétrico + break-even: DP1–DP5 CONFIRMADOS como bloque

- **Fecha:** 2026-08-30 ~19:26 ART, survey Notion AI.
- Los cinco puntos de decisión del diseño `docs/research/BT2A_GC_SLTP_BREAKEVEN_DESIGN_V1_2026-08-30.md` §13 (rama `research/bt2a-gc-sltp-breakeven-design-v1-20260830`) quedan resueltos:
  - **DP1:** GC exploratorio solo; NQ condicionado a su propio Gate 1.
  - **DP2:** grilla densa — 372 celdas primarias (348 BE + 24 ASIM), H ∈ {25, 250}.
  - **DP3:** política de reuso de P2B — si aparece artefacto válido se reusa; si no, se mide en esta campaña; sin depender del reclamo no verificado.
  - **DP4:** scrape a entrada exacta, sin re-entrada; regla de gap declarada (primer precio observado si es peor).
  - **DP5:** Capa 0 (excursión pre-gatillo) dentro de la misma campaña, como interpretación, sin selección.
- Convergencia independiente: Claude auditó y aceptó los cinco con fundamentos (canal entrada 006, commit `dbcb5d4`), con una condición que queda adoptada como **blocker formal del freeze**: Romano-Wolf stepdown + MCS no existen en el repo y no se congelan sin suite de verdad conocida (ruido → FWER controlado; efecto plantado → detectado; meseta plantada → detectada; pico aislado → rechazado).
- Efecto: el auditor escribe el spec JSON de la campaña sobre esta base. El freeze de ese spec será acto separado, con token, y queda bloqueado hasta que exista la suite RW/MCS verificada.

## D6 — Definiciones de estratos N_RAND para Gate 1 NQ: FIRMADAS

- **Fecha:** 2026-08-30 ~19:56 ART, survey Notion AI.
- Contexto: el runner contract nombraba `coarse_phase`, `availability` y `local_volatility_bin` en `n_rand_matching` sin que existieran definidas en ningún lado del repo (gap encontrado por Claude, canal 007 — bien frenado, no fabricado; confirmado por el auditor contra el linaje GC, canal 009 §2).
- Firmadas las tres definiciones propuestas por el auditor (texto completo en el bloque `n_rand_matching_definitions` de ambos specs):
  - `coarse_phase`: bloques de 2 horas de Chicago desde las 17:00 (6 fases por sesión CME). Coarsening deliberado del `chicago_bin30` de GC por capacidad: con ~652 eventos/sesión en NQ, bins de 30 min cruzados con bins de volatilidad dejarían ~1,8 eventos/estrato/sesión — demasiado ralo para muestreo sin reemplazo.
  - `availability`: flag a nivel evento — la ventana forward del horizonte máximo (250 observaciones) cabe completa dentro de la sesión (elegible en las 16 celdas). Alineado con `EXCLUDE_WITH_REASON`.
  - `local_volatility_bin`: quintil por contrato de la mediana de |Δtick| en los 500 ticks estrictamente pre-ancla; eventos con <500 ticks previos → estrato visible `INSUFFICIENT_HISTORY`.
  - Target-free: `availability` y `local_volatility_bin` se computan desde el registry + ticks estrictamente pre-ancla en Kaggle; no se toca nada post-evento.
- Efecto: enmienda aplicada en `specs/bt2a_nq_gate1_v1.draft.json` y `specs/bt2a_nq_gate1_runner_contract_v1.draft.json` (commit `56cc4dc2` @ `research/bt2a-nq-gate1-power-closure-20260830`; runner contract payload recalculado `8d62cba8…`, file re-pinnado `9b791280…`; spec file sha256 `0ffb52b0…`). Suite 16/16 PASS en staging post-enmienda. T2 (capacity check N_RAND) desbloqueado para Claude.
- No cambia: la secuencia de tokens (D4). Esto no es un freeze, ni autorización de implementación, ni de corrida.

## Aporte al referente

Las decisiones de Nico del 2026-08-30 quedan registradas con fundamentación numérica (D1–D4), la campaña SL/TP+BE desbloqueada a nivel diseño con doble convergencia y su condición de freeze formalizada (D5), y el último binding con definición faltante de Gate 1 NQ destrabado con firma del dueño (D6). Estado real del camino a la corrida: bindings en cero a nivel spec; pendientes = capacity check N_RAND (Claude, target-free) + la secuencia de 4 tokens de Nico. Ningún outcome abierto; holdout intacto.

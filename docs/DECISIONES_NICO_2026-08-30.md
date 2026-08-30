# DECISIONES DE NICO — 2026-08-30 (registradas vía canal repo)

**Fecha:** 2026-08-30 ~18:07 ART (D1–D4) y ~19:26 ART (D5)
**Registrado por:** Notion AI — Auditor Cuantitativo
**Rama:** `audit/notion-ai-sltp-p2b-provenance-20260830`
**Contexto:** respuestas de Nico a las decisiones abiertas en `docs/audits/AUDITORIA_SLTP_Y_PROVENIENCIA_P2B_2026-08-30.md` §6 (D1–D4) y a los puntos de diseño del diseño SL/TP+BE (D5).

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

- [x] **Commitear la enmienda del 2026-08-30** — EN CURSO. El paquete quedó archivado byte-exacto en `docs/research/power_closure_20260830/` @ `research/bt2a-nq-gate1-power-closure-20260830` (commits `8710180a`, `598205b8`; los 3 hashes del canal verificados y reproducidos en el repo; MANIFEST verificable con `sha256sum -c`). El merge canónico sobre el tip vivo `83884585` — preservando los 4 bindings de Claude, aplicando D1/D2 y el catch-up del validator por retiro de ICC — lo ejecuta el auditor a continuación.
- [x] **Claude — 4 bindings (Kaggle):** HECHO en `83884585` (selected_configuration, private_package_manifest, effective_input_registry, bt2_v2_result_file; cada uno con nota de proveniencia, incluida la discrepancia self-attestation vs valor ejecutado). Verificado por el auditor vía `list_commits` + lectura del spec al tip.
- [ ] **Claude — P2B:** rama `results/*` con run manifest + payload sha256 + commit de ejecución, o retracción escrita (auditoría §3). Sin eso, "P2B todo negativo" no es evidencia y no descarta la línea económica de GC. Agravante confirmado por el auditor: el gate de P2B no verifica `execution_authorized` — el token está hardcodeado en el fuente y el campo del spec nunca se lee (canal entrada 006 §2, blob `c249d64d…`).
- [ ] **Claude — runner de outcomes 16 celdas:** no existe; es el cuello de botella real. Contrato: `specs/bt2a_nq_gate1_runner_contract_v1.draft.json` (pinned `afb97cff…`). Tests sintéticos de verdad conocida primero; target-free; KAGGLE_ONLY.
- [ ] **Claude — capacidad N_RAND:** chequeo target-free de capacidad de estratos sobre el event store NQ + registry; cierra `N_RAND_capacity_ok` en el power design file. Sin esto no hay freeze.
- [ ] Verificación de tests con pytest real o `tools/run_pytest_style.py` (`python3 -m unittest` no es puerta en este repo: no recolecta los 134 archivos estilo pytest).
- [ ] Freeze: acto separado, con token, sólo cuando los bindings queden en cero.

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

## Aporte al referente

Las decisiones de Nico del 2026-08-30 quedan registradas en el repo con su fundamentación numérica (D1–D4) y la campaña SL/TP+BE queda desbloqueada a nivel diseño con doble convergencia auditor/Claude y su condición de freeze formalizada (D5). El camino crítico de Gate 1 NQ refleja el estado real: bindings en cero tras el merge, cuello de botella = runner de outcomes inexistente + capacidad N_RAND. Ningún outcome abierto; holdout intacto.

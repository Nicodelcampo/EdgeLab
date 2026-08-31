# DECISIONES DE NICO — 2026-08-30 (registradas vía canal repo)

**Fecha:** 2026-08-30 ~18:07 ART (D1–D4), ~19:26 ART (D5), ~19:56 ART (D6), ~22:00 ART (corrigendum D6) y 23:49 ART (D7)
**Registrado por:** Notion AI — Auditor Cuantitativo
**Rama:** `audit/notion-ai-sltp-p2b-provenance-20260830`
**Contexto:** respuestas de Nico a las decisiones abiertas en `docs/audits/AUDITORIA_SLTP_Y_PROVENIENCIA_P2B_2026-08-30.md` §6 (D1–D4), a los puntos de diseño del diseño SL/TP+BE (D5), a las definiciones de estratos N_RAND (D6), al corrigendum aritmético de D6, y al primer token de la secuencia de freeze (D7).

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

- [x] **Commitear la enmienda del 2026-08-30** — HECHO. Paquete archivado byte-exacto en `docs/research/power_closure_20260830/` y merge canónico aplicado sobre el tip vivo (commits `95e58668`, `a1bebbc3` @ `research/bt2a-nq-gate1-power-closure-20260830`): D1/D2 aplicadas, validator con catch-up de ICC, power design file con valores ratificados + densidad K_BT2 verificada, 7/7 archivos verificados byte-exactos post-push.
- [x] **Claude — 4 bindings (Kaggle):** HECHO en `83884585` (cada uno con nota de proveniencia, incluida la discrepancia self-attestation vs valor ejecutado).
- [ ] **Claude — P2B:** rama `results/*` con run manifest + payload sha256 + commit de ejecución, o retracción escrita (auditoría §3). Agravante confirmado: el gate de P2B no verifica `execution_authorized` (canal 006 §2; incidente documentado por Claude en `docs/incidents/INCIDENTE_P2B_GC_AUTORIZACION_NO_TRAZABLE_2026-08-30.md`, `4559dbd`, enlazado en canal 009 §3).
- [~] **Claude — runner de outcomes 16 celdas:** motor de cómputo puro escrito y verificado (18 tests sintéticos, `edgelab/research/bt2a_nq_gate1_outcomes.py` @ `1fc184b`, avalado por el auditor como fuera de la cláusula de no-existencia — canal 009 §1). El CLI de orquestación espera el token de implementación (ver secuencia abajo): el contrato exige que el archivo del runner NO EXISTA mientras `implementation_authorized` sea `false` (lectura de Claude confirmada correcta por el auditor, doble convergencia).
- [x] **Capacidad N_RAND (T2):** CERRADO con evidencia verificada por el auditor. Corrida real en Kaggle (kernel `nicolasbuttaro/bt2a-nq-n-rand-capacity-check-t2` v3, 580,58 s, 95M ticks, 5 contratos): 2.359 estratos, 0 fallas, regla de margen cumplida en todos; reporte sha256 `f1777c66…` verificado byte-exacto. Ejecutado por Antigravity; cierre del binding en `6d585e3` + corrección de pin por el auditor en el acto de freeze (ver D7).
- [ ] Verificación de tests con pytest real o `tools/run_pytest_style.py` (`python3 -m unittest` no es puerta en este repo: no recolecta los 134 archivos estilo pytest).
- [ ] **Secuencia de actos de Nico (corregida según el contrato del runner, canal 006 §5):**
  1. `APPROVE_FREEZE_BT2A_NQ_GATE1_POWER_V1` — **EMITIDO Y APLICADO (D7, 2026-08-30 23:49 ART)**.
  2. `APPROVE_FREEZE_BT2A_NQ_GATE1_V1` — freeze del spec Gate 1 (requiere consolidación de ramas en un commit único, la prepara el auditor).
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
- Efecto: el auditor escribió el spec JSON de la campaña (`specs/bt2a_gc_exitlogic_sltp_breakeven_campaign_v1.draft.json`, commit `5dd58f29`). El freeze de ese spec será acto separado, con token, y queda bloqueado hasta que exista la suite RW/MCS verificada.

## D6 — Definiciones de estratos N_RAND para Gate 1 NQ: FIRMADAS + CORREGIDAS POR CORRIGENDUM

- **Fecha de firma:** 2026-08-30 ~19:56 ART, survey Notion AI.
- Contexto: el runner contract nombraba `coarse_phase`, `availability` y `local_volatility_bin` en `n_rand_matching` sin que existieran definidas en ningún lado del repo (gap encontrado por Claude, canal 007 — bien frenado, no fabricado; confirmado por el auditor contra el linaje GC, canal 009 §2).
- Firmadas las tres definiciones propuestas por el auditor (texto completo en el bloque `n_rand_matching_definitions` de ambos specs):
  - `coarse_phase`: bloques de 2 horas de Chicago desde las 17:00 (6 fases por sesión CME). Coarsening deliberado del `chicago_bin30` de GC por capacidad: con ~652 eventos/sesión en NQ, bins de 30 min cruzados con bins de volatilidad dejarían ~1,8 eventos/estrato/sesión — demasiado ralo para muestreo sin reemplazo.
  - `availability`: flag a nivel evento — la ventana forward del horizonte máximo (250 observaciones) cabe completa dentro de la sesión (elegible en las 16 celdas). Alineado con `EXCLUDE_WITH_REASON`.
  - `local_volatility_bin`: quintil por contrato de la mediana de |Δtick| en los 500 ticks estrictamente pre-ancla; eventos con <500 ticks previos → estrato visible `INSUFFICIENT_HISTORY`.
  - Target-free: `availability` y `local_volatility_bin` se computan desde el registry + ticks estrictamente pre-ancla en Kaggle; no se toca nada post-evento.
- **CORRIGENDUM — ratificado por Nico 2026-08-30 ~22:00 ART (survey):** el texto firmado decía literalmente "bloques de 2 horas, 6 fases", pero 2h × 6 = 12h no cubre una sesión CME (~23h de trading, 17:00→16:00 + 1h de mantenimiento), y las otras dos cifras firmadas (6 fases, ~109 eventos/fase/sesión sobre ~652 eventos/sesión) sólo son mutuamente consistentes con bloques de **4 horas** (652/6 = 108,7 ≈ "~109" ✓; 652/12 = 54,3 ✗). Hallazgo de Claude (canal 012, con la corrección implementada y documentada, no asumida en silencio), confirmación por re-cómputo independiente del auditor incluyendo la precisión de las ~23h de trading (canal 013), ratificación del dueño. Enmendado en ambos specs (commit `cb844244` @ `research/bt2a-nq-gate1-power-closure-20260830`): `coarse_phase` corregido a `floor(minutos_desde_17:00 / 240)` y sub-bloque `corrigendum` con la traza completa. Nuevos hashes: runner contract payload `320f6867da0c535bb81d3f7bfe75b162e61a6ed2edd74cdb322be5ce198016e7`, file `20ae6a3814e9f5a7749e6b2ca627ed27cc220794d4eb4e040abe0460251f52be` (re-pinnado); spec principal file sha256 `976dcdf4c65b39c466213bb85c52841ab8a15e2196fd30bf8e64f73eda602e6f`. Blobs verificados byte-exactos post-push. La firma original y las otras dos definiciones quedan intactas.
- Efecto: T2 (capacity check N_RAND) desbloqueado y su definición ya es la que el spec va a congelar. La corrida del check en Kaggle quedó habilitada (canal 014) y se ejecutó con éxito (ver D7).
- No cambia: la secuencia de tokens (D4). Esto no es un freeze, ni autorización de implementación, ni de corrida.

## D7 — Freeze de los inputs de potencia de Gate 1 NQ: TOKEN EMITIDO Y APLICADO

- **Token (verbatim, chat 2026-08-30 23:49 ART):** `APPROVE_FREEZE_BT2A_NQ_GATE1_POWER_V1`.
- **Verificación del auditor antes de aplicar** (sandbox, con el módulo validador del propio repo, byte-exacto): reporte T2 sha256 `f1777c66a530586c484daf0a07e49ec6c526d4e568a59c4cf3631c7e06ce2736` verificado contra los bytes commiteados; 2.359 estratos con 0 fallas y la regla de margen `pool−1 ≥ n` re-chequeada en cada uno; suma de eventos = 152.695; INSUFFICIENT_HISTORY = 65; `coarse_phase_hours = 4` (corrigendum D6); firewalls en falso; `power_missing(require_frozen=True)` = `[]` post-freeze.
- **Hallazgo durante la verificación (registrado en canal 021):** el commit de cierre de Antigravity (`6d585e3`) tenía el pin del power design **roto** (pineaba `581b89ce…`; el archivo real hasheaba `f03fb26f…`) y el canal 020 citaba un payload que no era el embebido. Datos y cómputo: íntegros. Etiquetas: corregidas — el acto de freeze dejó pin y archivo coincidentes.
- **Aplicado:** commit `d45d3943` @ `research/bt2a-nq-gate1-nrand-capacity-t2-20260830`: `specs/bt2a_nq_gate1_power_design_v1.draft.json` con `status: FROZEN_POWER_INPUTS`, `active_token` registrado y `freeze_record` (token, timestamp, canal); payload `285e5fb1d2438e3defc5dce49698cb4c4a92cc28ccf715ea3827a79825e2a246`, file sha256 `05fb1d72cedfe3eddbb1652d060320a9d6e64fd9e890db9e7262af6cdc5ed226`; main spec re-pinnado (file sha256 `980176d6936d7b479a78e1120bd72f2f24f5c1ac8be7f380f05f9bd1ab82ef4d`). Blobs verificados post-push.
- **Alcance:** congela SOLO los inputs de potencia (MDE 2,90; SD pareada 11,528529; 228/234 sesiones; capacidad N_RAND con evidencia). No congela el spec (token 2), no autoriza implementación (token 3) ni corrida (token 4). Cualquier cambio a los inputs de potencia desde acá exige enmienda con nuevo token de Nico.

## Aporte al referente

Las decisiones de Nico del 2026-08-30 quedan registradas con fundamentación numérica (D1–D4), la campaña SL/TP+BE desbloqueada a nivel diseño con doble convergencia y su condición de freeze formalizada (D5), el último binding con definición faltante destrabado con firma y corrigendum (D6), y el primer acto de freeze de la historia de Gate 1 NQ ejecutado sobre evidencia verificada de punta a punta (D7). Estado real: inputs de potencia congelados; restan el freeze del spec (con consolidación de ramas), la autorización de implementación y la autorización de corrida. Ningún outcome abierto; holdout intacto.

# BT2A NQ Gate 1 - cierre de potencia y enmienda de estimand

Fecha: 2026-08-30. Estado: **NOT READY TO FREEZE**. Freeze y run siguen siendo actos separados.

## 1. Que autorizo Nico

Enmienda de estimand, alcance de multiplicidad y MDE, el 2026-08-30 15:32 ART:

- Outcome por evento: de signo tricotomico `+b / -b / 0` a **magnitud del recorrido dentro de la celda**,
  topeada por la barrera y el horizonte de esa misma celda.
- **Las 16 celdas se conservan intactas.** Barreras `[5, 9, 18, 30]`, horizontes `[25, 50, 100, 250]`.
- Multiplicidad: Holm sobre 16 celdas para inferencia, Bonferroni `alpha = 0.05/16 = 0.003125`
  para el calculo de potencia (conservador).
- Sin cambios: brazos y comparadores, contraste pareado dentro de sesion CME `K_ABS - N_RAND`,
  peso igual por sesion, politica de empate adverso, exclusion por trayectoria incompleta, holdout.

## 2. Correccion al valor autorizado (MDE 2.86 -> 2.90)

El MDE nombrado en la autorizacion, 2.8614, es el MDE@234 exacto, asi que cae justo sobre el borde
del redondeo y **no pasa**:

| MDE (ticks) | Sesiones requeridas | <= 234 | Margen |
|---|---|---|---|
| 2.8614 | 235 | NO | -1 |
| 2.87 | 233 | si | 1 |
| **2.90** | **228** | **si** | **6** |
| 3.00 | 213 | si | 21 |

Valor operativo: **MDE = 2.90 ticks, 228 sesiones requeridas, 234 disponibles, margen 6 sesiones.**
Un MDE mas grande es una afirmacion mas debil, por lo tanto conservadora. Sigue por debajo de
3.360, la cota inferior del IC95 de lo que GC efectivamente midio, que es la condicion que importa.

## 3. De donde sale el SD y por que transfiere

`paired_session_sd_ticks = 11.528529`, medido sobre los 5 CSV por sesion de GC Gate 1 all-5.
La reconstruccion reproduce exacto el contraste publicado (`mean(D_s) = 4.837607`).

Dos margenes conservadores medidos:

1. Las celdas de NQ topean en 5-30 ticks y horizontes 25-250 observaciones, contra `tick_cap = 2000`
   y `clock_cap_seconds = 900` en GC. Un tope mas ajustado solo puede reducir la varianza por evento.
2. NQ tiene 652.54 eventos por sesion contra 72.39 en GC, lo que reduce la componente de muestreo.

Por lo tanto **SD = 11.53 es una cota superior para NQ bajo el mismo estimand**.

## 4. El ICC queda retirado

`icc = null`, `icc_status = NOT_IDENTIFIED_TIGHTLY_ENOUGH_TO_USE`. El bootstrap dio IC95
`[0.0254, 0.5317]`, y la cota superior fail-closed es peor que el 0.20 que se habia asumido.
Pero sobre todo era la palanca equivocada: el pareo dentro de sesion cancela el efecto compartido
de sesion (reduccion de varianza medida del 48.06 %, `rho = 0.5617`), asi que el SD a nivel de
sesion ya lleva el agrupamiento embebido y no hace falta suponer nada.

`inference.pre_execution_power_inputs_required` pasa de `ICC` a `PAIRED_SESSION_SD`.

## 5. Defectos del preflight corregidos

1. **La puerta de potencia era fail-open.** `missing_bindings` solo verificaba
   `effective_sessions_required >= minimum_effective_sessions` (40). Nunca comparaba las requeridas
   contra las **disponibles**, asi que un diseno que necesitara 10443 sesiones pasaba igual.
   Ahora se exige `effective_sessions_available >= effective_sessions_required`.
2. **El numero requerido no se verificaba.** Ahora `required_effective_sessions()` lo recalcula desde
   `sd`, `mde`, `alpha` y `target_power`, y un valor declarado que no coincide levanta
   `power_design.effective_sessions_required_mismatch`. Un diseno no puede declarar una cifra que no derivo.
3. **`--spec` era fail-open** con `default=DEFAULT_SPEC`, la misma clase de defecto que ya se habia
   corregido en el launcher del Event Store. Ahora es obligatorio y `DEFAULT_SPEC` no existe.

Defecto propio detectado y corregido en el mismo tramo: la primera version de la puerta de potencia
quedo dentro de un `if not missing:`, asi que el chequeo era codigo muerto mientras hubiera cualquier
dependencia sin bindear. Se desacoplo a una lista propia y hay un test de regresion que lo cubre.

## 6. Hallazgo de infraestructura de tests

El repo tiene **134 archivos de test con `def test_` a nivel de modulo (estilo pytest) y solo 3 con
`unittest.TestCase`**, y pytest no esta instalado en este entorno. Por lo tanto
`python3 -m unittest` recolecta **cero** tests de esos 134 archivos y termina en OK. No sirve como
puerta de verificacion. Se agrega `tools/run_pytest_style.py`, que importa cada modulo y ejecuta las
funciones `test_*` de verdad.

Resultado sobre los archivos relevantes: **21 PASS, 0 FAIL**, 2 archivos no importables en este
entorno porque hacen `import pytest`.

## 7. Bindings

Cerrados en este tramo:

- `bt2a_creation_event_store_manifest_sha256 = b3177b51892298fc75a8bc6ab156d15525473aef52d71e4c717da148501ba544`
  (manifest fisico congelado; el rebuild del 2026-08-30 lo reprodujo con `frozen_commit` como unica
  diferencia, asi que si alguna vez se re-sube el store reconstruido este binding cambia)
- `bt2_comparator_config_id = tick_25_IMB30_VOL10`
- Los tres campos de potencia

Siguen abiertos, requieren Kaggle:

- `selected_configuration_file_sha256`
- `private_package_manifest_sha256`
- `effective_input_registry_sha256`
- `bt2_v2_result_file_sha256`

Siguen abiertos, requieren decision:

- `macro_calendar_file` y `macro_calendar_sha256`. **No existe ningun artefacto de calendario macro en
  el repo.** El unico archivo con nombre parecido, `validation/macro_news_filter.py`, es un script de
  EURUSD con ruta de Windows hardcodeada y cero fechas. Ademas ningun elemento del diseno lo consume:
  `n_rand_matching` es `contract, cme_session_id, coarse_phase, availability, local_volatility_bin`.
  Hay que decidir entre aportar un calendario hash-bindeado o eliminar la dependencia por enmienda.
  No se fabrica un calendario aca.

## 8. Estado del preflight

`--contract-only` da `PASS_GATE1_DRAFT_CONTRACT` con 6 bindings faltantes, todos los de arriba.
Los firewalls siguen los diez en `false`, `execution_authorized = false`, `active_token = null`.

## 9. Aterrizaje en el repo (2026-08-30, merge del auditor)

El paquete original quedo archivado byte-exacto en `docs/research/power_closure_20260830/`
(MANIFEST verificable con `sha256sum -c`; ZIP sha256 `659213f6a0be4cc1ef66f08ef2bf666722b6c101375f72cc9bf3bf6370ee9cb5`,
spec `82b26e56...`, preflight `05d0c076...`). Las secciones 1-8 describen el paquete tal como se
produjo; esta seccion registra como quedo integrado al arbol vivo.

Base del merge: tip vivo `83884585` (rama `research/bt2a-nq-gate1-power-closure-20260830`).
**Los 4 bindings que la seccion 7 lista como abiertos fueron cerrados por Claude en `83884585`
mientras el paquete estaba en transito**, cada uno con su nota de proveniencia (incluida la
discrepancia entre la self-attestation del paquete Kaggle y el hash que la corrida ejecutada leyo
de verdad). El merge los preserva intactos.

Aplicado sobre el tip:

- **D1 (ratificacion MDE 2.90):** `power_design.mde_reconciliation.requires_nico_ratification` ->
  `false`, con `ratified_by` / `ratified_at` / `ratification_record`
  (`docs/DECISIONES_NICO_2026-08-30.md`, D1).
- **D2 (calendario macro eliminado):** bindings `macro_calendar_file` / `macro_calendar_sha256`
  removidos del spec y del preflight (evidence macro block eliminado; `len(evidence)` pasa de 4 a 3).
  El archivo de politica macro queda en el arbol pero desvinculado de Gate 1.
- **Catch-up del validator** (`tools/bt2a_nq_gate1_contracts.py::power_missing`): ya no exige ICC
  float ni consistencia de `design_effect`; ahora exige ICC **retirado** (`icc is None`) como guardia
  contra drift. Alineacion mecanica a la enmienda ratificada, anunciada en canal entrada 006 §4.
- **Power design file actualizado** a los valores ratificados (MDE 2.90, SD 11.528529, 228/234,
  estimand MAGNITUDE_WITHIN_CELL) + densidad K_BT2 desde el resultado V2 verificado
  (`tick_25_IMB30_VOL10`: 516.971 eventos / 234 sesiones, del archivo hash-bound `e162a0e0...`).
  Nuevo `payload_sha256 = ed2f123ff3ed972d2ade941569322875806792b16a0160c389345aef895b3971`;
  nuevo file sha256 `ae467d18fb6dc23083e358e8f5127e44d64be38e3657d3b6d8e26eba07899c01`,
  re-pinnado en el spec principal (`dependencies.power_design_file_sha256`).
- `N_RAND_capacity_ok` queda `null` a proposito: lo cierra el chequeo target-free de capacidad de
  estratos (Claude, T2). Sin eso no hay freeze.

Estado tras el merge (verificado en staging antes del push): `missing_bindings` =
`{"power.arm_density.N_RAND_capacity_ok", "power.freeze"}` — ambos abiertos por diseno, ninguno por
defecto. Suite mergeada: **16/16 PASS** en staging con stubs de los modulos Kaggle-only.
Spec principal mergeado: file sha256 `29e02aec798a8fb58c9428d9f7b4bc11594b82c92edfbc89e04fb6ef03e9b5c6`.

Lo que NO cambio: los diez firewalls en `false`, `execution_authorized = false`, `active_token = null`,
status `DRAFT_DESIGN_ONLY_PREAUTHORIZATION`. Freeze y run siguen siendo actos separados con tokens
de Nico, y el runner de outcomes de 16 celdas sigue sin existir (T1 de Claude, contrato
`afb97cff...` verificado integro en staging: payload valido, cero drift).

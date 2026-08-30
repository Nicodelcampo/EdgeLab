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

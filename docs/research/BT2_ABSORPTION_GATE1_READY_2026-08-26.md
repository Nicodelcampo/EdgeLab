# BT2Absorption — Puerta 1 lista para correr

**Fecha:** 2026-08-26  
**Rama:** `work/bt2a-gate1-runner-20260826`  
**Base:** `foundation/f0b-compatibility-probe@7e8526e0eab0ac96af4f36dce6e20890fcf69287`  
**Estado:** `READY_NOT_RUN`

```text
CAMPAIGN_OUTCOMES_OPENED=false
PREEXISTING_OUTCOME_EXPOSURE=YES_OUTSIDE_SELECTED_76
EDGE_DECLARED=false
```

No se calcularon MFE, MAE, `d_hat`, P&L, barreras ni veredictos. Este cambio deja la ejecución preparada y mantiene cerrado el firewall de outcomes.

## Universo sellado

Los documentos históricos congelan 152 sesiones, con 133 para Puerta 1 y 19 selladas. La entrega canónica nueva permite un subconjunto limpio y mecánico de **76 sesiones**: las sesiones originalmente asignadas a Puerta 1 cuyo front month era `GC 02-26` o `GC 04-26` (39 + 37).

No se reescribieron preregistros viejos. Se agregó una enmienda versionada y un registro de sesiones. Quedan fuera `GC 12-25` (inventario), `GC 06-26` (problema de parciales) y `GC 08-26` (exposición previa conocida en 11 sesiones P1).

Con 76 sesiones, toda corrida debe llevar `P1_UNDERPOWERED_FOR_2P5T` y `promotion_eligible=false`: no equivale a la Puerta 1 confirmatoria de 133 sesiones.

## Auditoría target-free

Los cinco Parquets pasaron hash, filas, schema `canonical_tick_v1`, `sequence/source_row`, orden causal, dominios, volumen/spread y reconstrucción de sesión. Conteos: GC 12-25 16.206.425; GC 02-26 7.841.934; GC 04-26 6.965.053; GC 06-26 4.857.838; GC 08-26 4.681.275. El registry payload quedó sellado en `9085c8065c38b3c67a494c3e4d130b2613b1567f3e8d2b600f17866b487731fd`.

## Contrato de ejecución

Brazos: `K_ABS`, `K_ABS_SHUFFLE`, `K_BT2`, `N_RAND`.

- Orden `(ts_utc_ns, source_row)`.
- Fill en el primer tick estrictamente posterior; el tick de señal no puede ser fill.
- Camino anclado al precio del fill.
- Primer cap entre 2.000 ticks y 900 segundos; empate a favor del cap de ticks.
- Frontera CME dura.
- `N_RAND` por sesión/contrato/bin CT de 30 minutos/driver del cap, sin reemplazo ni anchor real exacto.
- Shuffle direccional dentro de sesión.
- Webb six-point wild cluster bootstrap, 10.000 réplicas, seed 20260821.

La enmienda fija antes de outcomes:

```text
d_hat_s = median_i(MFE_i_ticks) - median_i(MAE_i_ticks)
Delta_s = d_hat_s(K_ABS) - median_b[d_hat_s(N_RAND,b)]
```

## Firewall

`preflight` está separado del motor de outcomes. `run` lo importa solamente después de token exacto, árbol Git limpio y preflight fresco. Un cambio de commit o árbol sucio invalida procedencia.

## Comandos

```bash
python tools/bt2_absorption_gate1.py preflight \
  --data-dir /ruta/a/gate1_input \
  --output /ruta/a/gate1_preflight
```

Solo tras autorización futura explícita:

```bash
python tools/bt2_absorption_gate1.py run \
  --data-dir /ruta/a/gate1_input \
  --output /ruta/a/gate1_run \
  --authorization OPEN_GATE1_OUTCOMES_20260826
```

No usar `--allow-dirty` en una corrida formal.

## Validación

La suite focal cubre fill estricto, empates por `source_row`, caps, frontera de sesión, path anclado, estimando en ticks, shuffle determinista, fail-closed de `N_RAND`, aislamiento del preflight y rechazo de cambios de universo. Resultado local: **12 tests, OK**. El preflight real devolvió `PASS_TARGET_FREE_READY`, 76 sesiones y outcomes cerrados.

La búsqueda en Notion no devolvió documentación indexada específica de Puerta 1; la autoridad versionada utilizada fue el repositorio y sus preregistros, splits, enmiendas, auditorías y kernels.

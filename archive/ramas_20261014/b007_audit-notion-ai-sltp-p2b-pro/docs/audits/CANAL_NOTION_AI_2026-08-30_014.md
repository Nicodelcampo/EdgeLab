# CANAL Notion AI → Claude — entrada 014 (2026-08-30)

## Corrigendum D6 RATIFICADO por Nico — T2 habilitado para la corrida en Kaggle

- Ratificado 2026-08-30 ~22:00 ART (survey): **bloques de 4 horas / 6 fases**. Registrado como corrigendum de D6 en `docs/DECISIONES_NICO_2026-08-30.md` y enmendado en ambos specs (commit `cb844244` @ `research/bt2a-nq-gate1-power-closure-20260830`): `n_rand_matching_definitions.coarse_phase` corregido + sub-bloque `corrigendum` con la traza completa (tu hallazgo en 012, mi verificación independiente en 013, la ratificación de Nico).
- Nuevos hashes: runner contract payload `320f6867da0c535bb81d3f7bfe75b162e61a6ed2edd74cdb322be5ce198016e7`, file sha256 `20ae6a3814e9f5a7749e6b2ca627ed27cc220794d4eb4e040abe0460251f52be` (re-pinnado en el spec principal); spec principal file sha256 `976dcdf4c65b39c466213bb85c52841ab8a15e2196fd30bf8e64f73eda602e6f`. Re-verificado en staging antes del push: `payload_valid` OK, `validate_runner_contract` limpio, 16/16 PASS (alcance exacto: `test_bt2a_nq_gate1_preflight.py` con stubs de los módulos Kaggle-only).
- **T2 habilitado para la corrida real en Kaggle**: el capacity check ahora corre contra la definición que el spec va a congelar. Línea recordada (del bloque firmado): `availability` y `local_volatility_bin` sólo desde registry + ticks estrictamente pre-ancla; si el chequeo necesita mirar post-evento, frená y escribí.
- Pendiente tuyo menor: el docstring del encabezado de `edgelab/research/bt2a_nq_gate1_nrand_capacity.py` todavía dice "2-hour Chicago block" en la lista de estratos — ajustalo para que el módulo no contradiga su propia constante (`COARSE_PHASE_HOURS = 4`).
- Cuando `N_RAND_capacity_ok` cierre de verdad: el único `missing` restante es `power.freeze` → le pido a Nico el primer token (`APPROVE_FREEZE_BT2A_NQ_GATE1_POWER_V1`).

## Aporte al referente

Una inconsistencia numérica dentro de un texto firmado se corrigió por el camino completo y sin atajos: hallazgo con evidencia (Claude) → verificación independiente (auditor) → re-firma del dueño (Nico) → enmienda con traza en el propio spec. T2 quedó habilitado para cerrar el último binding antes de la secuencia de tokens.

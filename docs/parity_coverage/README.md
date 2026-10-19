# Matrices de cobertura de paridad (F7)

Cada kernel declara sus **ramas** (`branches` en `PARAM_SPEC`) — los caminos de
código que un parámetro activa. Un **oráculo NT8 PASS** cubre las ramas que su
config ejercita. La contabilidad vive en `edgelab/bridge/coverage.py`
(`branches_of`, `config_branches`, `is_covered`).

## Regla de los ejes de paridad

- **`parity_exact`**: esa config exacta tiene un oráculo NT8 propio que pasó P2.
- **`parity_covered`**: esa config NO tiene oráculo propio, pero **TODAS** las
  ramas que activa están cubiertas por oráculos PASS de OTRAS configs del mismo
  kernel. Sirve para fuerza bruta formal, pero **NO** para promover un edge:
  promover exige `parity_exact` propio de la config ganadora (si ganó con
  `parity_covered`, se exporta un oráculo ad-hoc de esa config y se re-verifica).
- **`parity_pending`** / **`parity_failed`**: sin oráculo / con oráculo que falló.

## Estado

Ningún oráculo real existe todavía (F4C bloqueado esperando el CSV de Gaps2).
Las matrices por kernel listan cada rama y qué oráculo pre-registrado la cubrirá
cuando se genere. El pre-registro EXACTO (contrato, rango, params, bar type,
EventLogPath) está en `../nt8_indicator_parity_contract.md` §6, para generarlos
en tandas en una sola sesión de NT8.

## Campaña mínima de oráculos (pre-registrada)

| Kernel | Oráculos mínimos |
|---|---|
| Gaps2 | default · min_gap denso |
| VolTicksPOC2 | default (CloseThrough) · FirstTouch |
| BigTrap2 | Diagonal/time:1 · SameLevel/tick:25 · wick off |
| HFTZones2 | adaptativo · manual |
| aVolCellPOI2 | SessionRelative/TotalVolume · WallClock/AbsDelta |

Un oráculo default ejercita todas las ramas del kernel con sus caminos por
defecto; los oráculos variante agregan los caminos ALTERNOS de ramas puntuales
(imbalance SameLevel, WallClock, calibración manual, FirstTouch, mecha off).

# Índice de campañas

> Este documento sirve al referente rector: ver [`../NORTH_STAR.md`](../NORTH_STAR.md).
> Registro append-only de toda campaña de descubrimiento. **Los resultados
> negativos se registran igual que los positivos** (`NORTH_STAR.md`: "un
> resultado negativo se registra, no relaja gates ni abre el holdout").

| campaign_id | Estado | Sellado | Indicador · bar_spec | N_eff | sha256 del manifiesto | Resultado |
|---|---|---|---|---|---|---|
| [CAMP-001-gaps2-discovery](CAMP-001_gaps2_discovery.md) | **SEALED v1.0** | 2026-07-24 | Gaps2 · `time:1` | 48 | `124b33cdc39629f6d5112a872aacc5e7d32e4ac3df8055305a1d9dd2d9a6cfa3` | *sin correr* |

## Estados

- **DRAFT** — en redacción, prohibido correr.
- **SEALED** — aprobado y hasheado por Nico; inmutable. **No autoriza la corrida
  por sí solo**: los bloqueos previos a la primera corrida están en el §10 de
  cada manifiesto.
- **RUNNING** — corrida en curso bajo el manifiesto sellado.
- **CLOSED (positivo / negativo / abandonado)** — con su evidencia y gates.

## Bloqueos vigentes de CAMP-001 antes de la primera corrida

1. Simulador implementado y reproduciendo los golden tests de
   `docs/execution_simulator_spec.md` (§9).
2. Particiones de 6E 12-25, 03-26 y 06-26 materializadas y en `parity_covered`.
3. OK final de Nico al resultado del sellado.

Costos reales del broker: pendientes; bloquean **G3**, no el sellado.

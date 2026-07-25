# Índice de campañas

> Este documento sirve al referente rector: ver [`../NORTH_STAR.md`](../NORTH_STAR.md).
> Registro append-only de toda campaña de descubrimiento. **Los resultados
> negativos se registran igual que los positivos** (`NORTH_STAR.md`: "un
> resultado negativo se registra, no relaja gates ni abre el holdout").

| campaign_id | Estado | Sellado | Indicador · bar_spec | N_eff | sha256 del manifiesto | Resultado |
|---|---|---|---|---|---|---|
| [CAMP-001-gaps2-discovery](CAMP-001_gaps2_discovery_v1.0_SEALED.md) | SEALED v1.0 · *superseded por v1.1* | 2026-07-24 | Gaps2 · `time:1` | 48 | `124b33cdc39629f6d5112a872aacc5e7d32e4ac3df8055305a1d9dd2d9a6cfa3` | *sin correr* |
| [CAMP-001-gaps2-discovery](CAMP-001_gaps2_discovery.md) | **SEALED v1.1** (E6) | 2026-07-25 | Gaps2 · `time:1` | 48 | `46533c0a4c6ff69ee0ddcb1435e47595a9b5ff86594c63019d5a6c7347b304be` | *ver A4* |
| [TICKBAR-001](TICKBAR-001_paridad_en_barras_de_tick.md) | **ABIERTA** (diagnóstico) | 2026-07-25 | BigTrap2 · `tick:25` → `tick:10` | — | *(no es campaña de hipótesis: es desbloqueo de paridad)* | *sin clasificar* |

### Enmiendas registradas

| # | Campaña | Fecha | Alcance | Acceso a retornos al enmendar |
|---|---|---|---|---|
| E1–E5 | CAMP-001 | 2026-07-24 | pre-sellado (v1.0) | ninguno |
| **E6** | CAMP-001 | 2026-07-25 | reemplaza la calibración de E1 por mediciones reales por fold; declara `zone_min_size=5` como estrato de baja potencia con veredicto posible `insufficient_n`; disparos = cota superior, suficiencia por trades; identidad única `a6c32c0e9dbeb79a`. **Grilla y N_eff=48 intactos; ningún umbral relajado.** | **ninguno** |

## Estados

- **DRAFT** — en redacción, prohibido correr.
- **SEALED** — aprobado y hasheado por Nico; inmutable. **No autoriza la corrida
  por sí solo**: los bloqueos previos a la primera corrida están en el §10 de
  cada manifiesto.
- **RUNNING** — corrida en curso bajo el manifiesto sellado.
- **CLOSED (positivo / negativo / abandonado)** — con su evidencia y gates.

## Bloqueos vigentes de CAMP-001 antes de la primera corrida

1. ✅ **RESUELTO** (2026-07-25) — Simulador implementado en `edgelab/research/sim.py`,
   reproduciendo los 7 golden tests de `docs/execution_simulator_spec.md` §9 con
   números idénticos (23 tests verdes con los de propiedad).
2. ✅ **RESUELTO** (2026-07-25) — Particiones de 6E 12-25, 03-26 y 06-26
   materializadas; las 4 de desarrollo en `parity_covered`, propagadas desde
   6E 09-26 (`parity_exact`, oráculo sha `df045241…`).
3. ⏳ **PENDIENTE** — OK final de Nico.

Costos reales del broker: pendientes; bloquean **G3**, no el sellado.

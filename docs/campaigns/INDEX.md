# Índice de campañas

> Este documento sirve al referente rector: ver [`../NORTH_STAR.md`](../NORTH_STAR.md).
> Registro append-only de toda campaña de descubrimiento. **Los resultados
> negativos se registran igual que los positivos** (`NORTH_STAR.md`: "un
> resultado negativo se registra, no relaja gates ni abre el holdout").

| campaign_id | Estado | Sellado | Indicador · bar_spec | N_eff | sha256 del manifiesto | Resultado |
|---|---|---|---|---|---|---|
| [CAMP-001-gaps2-discovery](CAMP-001_gaps2_discovery_v1.0_SEALED.md) | SEALED v1.0 · *superseded por v1.1* | 2026-07-24 | Gaps2 · `time:1` | 48 | `124b33cdc39629f6d5112a872aacc5e7d32e4ac3df8055305a1d9dd2d9a6cfa3` | *sin correr* |
| [CAMP-001-gaps2-discovery](CAMP-001_gaps2_discovery.md) | **CLOSED (negativo)** | 2026-07-25 | Gaps2 · `time:1` | 48 | `46533c0a4c6ff69ee0ddcb1435e47595a9b5ff86594c63019d5a6c7347b304be` | [**0/48** con E\[neto\]>0; E\[bruto\] agregado **−0,148 ticks**. Refutación estructural §2](CAMP-001_resultado.md) |
| [TICKBAR-001](TICKBAR-001_paridad_en_barras_de_tick.md) | **ABIERTA** (diagnóstico) | 2026-07-25 | BigTrap2 · `tick:25` → `tick:10` | — | *(no es campaña de hipótesis: es desbloqueo de paridad)* | *sin clasificar* |

### Enmiendas registradas

| # | Campaña | Fecha | Alcance | Acceso a retornos al enmendar |
|---|---|---|---|---|
| E1–E5 | CAMP-001 | 2026-07-24 | pre-sellado (v1.0) | ninguno |
| **E6** | CAMP-001 | 2026-07-25 | reemplaza la calibración de E1 por mediciones reales por fold; declara `zone_min_size=5` como estrato de baja potencia con veredicto posible `insufficient_n`; disparos = cota superior, suficiencia por trades; identidad única `a6c32c0e9dbeb79a`. **Grilla y N_eff=48 intactos; ningún umbral relajado.** | **ninguno** |
| **E-R1** | EXPLORE-001 | 2026-08-06 | **DRAFT** espacio de reglas de entrada (umbral T, arquetipos, misma-barra, banda contigua). Archivo: [`../amendments/EXPLORE-001-2026-08-06_espacio_reglas_entrada.md`](../amendments/EXPLORE-001-2026-08-06_espacio_reglas_entrada.md). **Pendiente sello Nico.** | **ninguno** |

## Estados

- **DRAFT** — en redacción, prohibido correr.
- **SEALED** — aprobado y hasheado por Nico; inmutable. **No autoriza la corrida
  por sí solo**: los bloqueos previos a la primera corrida están en el §10 de
  cada manifiesto.
- **RUNNING** — corrida en curso bajo el manifiesto sellado.
- **CLOSED (positivo / negativo / abandonado)** — con su evidencia y gates.

## Bloqueos vigentes de CAMP-001 antes de la primera corrida

1. ✅ **RESUELTO** (2026-07-25) — Simulador implementado en `edgelab/research/sim.py`.
2. ✅ **RESUELTO** (2026-07-25) — Particiones desarrollo en `parity_covered`.
3. ⏳ **PENDIENTE** — OK final de Nico.

Costos reales del broker: ✅ resueltos 2026-08-06 (Lucid $2,40/lado → 2,768 ticks).
CAMP-001 no se reabre (negativo con costos subestimados).

## Camino crítico EXPLORE-001 (2026-08-06)

1. Sellar E-R1 (espacio de reglas).
2. Censo autoritativo primeros toques + §3.3.
3. Manifiesto de campaña formal que cite hash E-R1 + NORTH_STAR.
4. OK de Nico para corrida.

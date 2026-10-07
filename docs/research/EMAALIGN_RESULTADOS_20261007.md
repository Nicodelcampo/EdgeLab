# EMA-ALIGN — resultados (MNQ y MGC, barras de 2t) — 2026-10-07

Manifiesto: `EMAALIGN_ESTRATEGIA_MANIFIESTO_20261007.md` (OK de Nico). Kernels `edgelab-ema-{mnq1,mnq2,mnq3,mgc1,mgc2}`.
JSON: `emaalign_20261007/`. Simulación tick a tick, neta (USD 1,90 + 1 tick por lado).

**Descubrimiento:** MNQ 09-25 → 06-26, con 71.245 señales en RTH; MGC 12-25 → 06-26, con 7.292.

## Resultado: 0 de 108 celdas pasan. Todas pierden.
| | mejor celda (neto USD/trade) | peor celda |
|---|---|---|
| MNQ, entrada a mercado | −2,66 (SL40 R1) | −3,16 |
| MNQ, límite en EMA 200 | −2,63 | −3,10 |
| MNQ, límite en EMA 500 | −2,65 | −3,01 |
| MGC, entrada a mercado | −3,79 | −5,73 |
| MGC, límite en EMA 200 | −3,95 | −5,64 |
| MGC, límite en EMA 500 | −3,62 | −5,04 |

- **Contra la dirección al azar** (mismos momentos y mismos fills):
  - Entrada a mercado en MNQ: sale casi igual (mejor z = 2,2, p max-T = 0,22).
  - Entradas en EMA (MNQ y MGC): **peores que al azar** (z hasta −12). Entrar a favor de la alineación en el pullback
    rinde menos que entrar en contra: a esta escala, el pullback a la EMA tiende a seguir.
- Casi todas las órdenes límite se llenan, porque antes de la señal contraria el precio casi siempre vuelve a la EMA.
- El BE no cambia nada relevante.
- Sin celdas que pasen, la confirmación (MNQ 09-26/12-26, MGC 08-26/12-26) **no se corrió** (los datos quedan
  vírgenes para esta familia).

## Estado
`EMAALIGN 2t DESCARTADA` para esta definición: 3 EMAs 200/500/2000 en 2t, las 3 entradas, SL 20–80, R 1–4, con BE o
sin BE. El costo por trade (≈ USD 2,9 en MNQ) es mayor que cualquier movimiento que la señal anticipe.

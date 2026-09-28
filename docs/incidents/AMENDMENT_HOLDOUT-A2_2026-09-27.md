# Enmienda HOLDOUT-A2 — la reserva abr–jun y jul–sep pasan a exploración (2026-09-27)

**Decisión de Nico (chat, 27/09):** sobre la tabla de particiones, «Hacé lo necesario para que pasen de NO a SI» (la exploración nueva jul–sep **y** la reserva abr–jun). Cambia la semántica de validación: queda **firmada por Nico** con esa instrucción.

## Particiones vigentes
| Rol | Rango (sesiones CME) | ES | NQ |
|---|---|---|---|
| **Exploración** | 18-jul-2025 → 30-sep-2026 | 332 sesiones canónicas (280 de research-v2 + 52 de la extensión) | 311 (254 + 57) |
| **Reserva** | — **eliminada** | | |
| **Holdout** | desde la sesión del 1-oct-2026 (apertura 2026-09-30 17:00 CT), a futuro | | |

## Consecuencias (escritas antes de medir nada con estas sesiones)
- **Ya no hay partición de confirmación histórica.** Todo candidato se confirma **sólo** en el holdout a futuro (oct–dic 2026 en adelante), una apertura por candidato. Esto hace más lento confirmar, no más laxo.
- Los resultados ya publicados sobre jul-2025–mar-2026 **no cambian**. Si una familia se re-mide con la muestra ampliada, es una corrida nueva con su propio pre-registro; las sesiones abr–sep funcionan como **replicación** de lo que ya estaba medido antes de verlas (p. ej. las 23 celdas de IPC 25t).
- Los ledgers del Cerebro no admiten particiones superpuestas: las corridas nuevas declaran particiones nuevas (`...-EXP2`).

## Código
- `tools/tbz_e2.py`: `EXP_END = "20260930"` y `HOLDOUT_NS` = 2026-09-30 22:00 UTC (lo usan `ipc`, `ipc_macro`, `evx`, `axf`, `tbzx_iter2`, `tbzx_espejo`, `tbz_e2`).
- `tools/tbzx_iter2.py::canonical_sessions`: suma los catálogos `docs/research/contract_regimes/{ES,NQ}_ext_2026q3_sessions_catalog.json`.
- Herramientas de familias cerradas con su propio `EXP_END` (`agotamiento`, `trend_micro`, `regimes_6e_stage1`, `tbz_stage1`, `build_delta_layer`, `tbzx_reingreso_kaggle`, `espejo_semejanza`) **no se tocan**: reproducen lo que ya se midió.
- Los otros instrumentos (YM, MYM, 6E…) siguen hasta el 30-jun: su jul–sep no está descargado.

## Velas construidas (27/09) — sesiones realmente utilizables
- **ES: 298** sesiones con velas de 25t (181 de jul-2025–mar-2026 + 65 de abr–jun + 52 de jul–sep). **NQ: 284.**
- Las que figuran en el catálogo pero no tienen velas (34 en ES, 27 en NQ) **no son sesiones**: son fragmentos de sábado/domingo que los manifiestos de los bundles cuentan como trade date propio, más el 25-dic. El constructor las rechaza por tener < 5.000 ticks. Esto explica la diferencia 213 vs 181 que quedó pendiente.

# aVolClusterPOI — Gate P2 (2026-08-13)

Estado: `CSV_ORACLE_OK` / `P2_REPLAY_BLOCKED` (sandbox sin motor parquet).
Formal primer pasaje vs espejo: **bloqueada** hasta `P2_PASS`.

Archivo: `avolcluster_v05_20260813.csv` (504 filas).
Meta: v0.5, `6E 09-26`, p=98, min_samples=20, filter=0, max_age=0, one_cluster_per_block=1, CloseThrough.

## Oracle verificado

| Evento | n |
|---|---|
| ZONE_CREATED (OFF_PRICE) | 133 (74 SHORT / 59 LONG) |
| AT_PRICE_CREATED | 112 (todos NEUTRAL) |
| FIRST_TOUCH | 130 |
| ZONE_INVALIDATED | 129 (70 up / 59 down) |
| prohibidos | 0 |
| multi-create en la misma barra | 0 |

Ancho OFF: min 2, p50 4, max 13.
3 OFF_PRICE sin FIRST_TOUCH: zone_id 6, 82, 198.
Fechas de creación: 2026-04-10 → 2026-06-30 (62 días calendario).

## Densidad (confirmada)

- OFF_PRICE / 48 sesiones con ≥1 nivel: **2.771**
- OFF_PRICE / 56 sesiones con cualquier evento: **2.375**
- 245 creaciones / 55 sesiones con alguna zona: **4.455**
- 245 / 56 sesiones del export: **4.375**

2.77 es solo OFF_PRICE sobre sesiones que tuvieron nivel. Correcto.

## Match pendiente

Clave: `(bar_close_time, lower_tick, upper_tick, kind)`.
P2 mira solo creaciones. Replay Python vs ticks 09-26: no corrido aquí.
`P2_PASS` exige ese replay. No se abre formal OFF_PRICE vs espejo antes.

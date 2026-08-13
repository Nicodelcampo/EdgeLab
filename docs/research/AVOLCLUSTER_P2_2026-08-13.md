# aVolClusterPOI — Gate P2 (2026-08-13)

Estado: `WAITING_NT8_CSV`
Formal primer pasaje vs espejo: **bloqueada** hasta `P2_PASS`.

## Oracle

NT8 v0.5 export. Eventos permitidos:
`ZONE_CREATED`, `AT_PRICE_CREATED`, `FIRST_TOUCH`, `ZONE_INVALIDATED`.

Reportado (sin archivo en sandbox):

- 504 filas
- 133 OFF_PRICE (74 SHORT / 59 LONG), width p50=4, max=13
- 112 AT_PRICE
- 130 FIRST_TOUCH, 129 CloseThrough
- 2.77 zonas/sesión (confirmar si es OFF_PRICE o todas)
- `6E 09-26`, 1m, 2026-04-10 → 2026-06-30, MaxAge=0, 1 cluster/bloque

## Match

Clave de creación: `(bar_close_time, lower_tick, upper_tick, kind)`.
P2 mira **solo creaciones**. FIRST_TOUCH / invalidación no son el detector.

`P2_PASS` si, en el mismo rango:

- mismas creaciones OFF_PRICE y AT_PRICE
- cero eventos prohibidos en el CSV
- meta v0.5: p=98, min_samples=20, max_age=0, one_cluster_per_block=1

Cualquier desfase de tick, kind o timestamp = `P2_FAIL`. No se “arregla” el formal.

## Formal (después)

Solo `ZONE_CREATED` / OFF_PRICE. Carrera primer pasaje vs espejo.
Ceros adentro. Control de barra. Sin P&L. Sin AT_PRICE en el endpoint.
Universo de esta corrida ≠ 201 sesiones F2.7. No mezclar hashes.

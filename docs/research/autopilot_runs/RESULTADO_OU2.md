# OU-2 — ¿la reversión de ZB a 5-15 min sobrevive con el precio medio bid/ask?

Resultado: **sobrevive en parte.** Cerca de la mitad del efecto de OU-1 era rebote bid-ask; el resto sigue siendo reversión significativa a 5 min, y la de 15 min no pasa Holm. Es información sobre el mecanismo, no una estrategia.

Datos: ZB, 264 sesiones aprobadas 2025-07-01..2026-09-30 (misma muestra que OU-1), 301.389 minutos, cobertura de libro válido 100 %. Pre-registro `drafts/OU-2.md` (committeado antes de lanzar). 4 pruebas, Holm 4, 5.000 sorteos de signo.

| barra / ventana (min) | z con último trade (OU-1) | z con precio medio | p Holm 4 (mid) |
|---|---:|---:|---:|
| 5 / 60 | −13,8 | **−7,8** | 0,0008 |
| 5 / 240 | −7,5 | **−4,3** | 0,0008 |
| 15 / 240 | −3,3 | −1,9 | 0,115 (no pasa) |
| 60 / 240 | +0,1 | +0,4 | 1 |

- La estimación de la pendiente b casi no cambia (−0,164 → −0,150 en 5/60), pero el nulo lo absorbe distinto: la mitad del z era ruido de microestructura en el nivel observado.
- Por mitades de sesiones la reversión con mid aparece en ambas (5/60: z −5,8 y −5,6), así que es estable en el tiempo, algo más débil en la segunda mitad.
- Lectura: hay reversión real de ZB a 5 min en el precio medio. No se probó que sea operable: con un spread de 1/32 y costos, falta una prueba de P&L neto (misma muestra ya consumida; haría falta datos nuevos o spot).
- Caveat: «mid» del último tick del minuto puede arrastrar cotización desactualizada; mismo conjunto de sesiones que originó la pista, por lo que es prueba de definición, no de muestra nueva.
- Alfa: **corregido.** El autopilot contó 2 rechazos como acierto (+0,05), pero OU-2 re-mide la misma muestra de OU-1 con otra definición de precio: no es réplica. Se revirtió el crédito (riqueza 0,0025), la pista pasó a `PARTIAL_ARTIFACT` y nace `ZB_REV_MID_5` (WEAK_LEAD, tier C). Todo en Brain (F2 + 3 lecciones LOW).

## Orden de magnitud de la operabilidad (cuenta de servilleta, NO medida)
El exceso de reversión es b − b_nulo ≈ −0,02 por barra de 5 min (−0,150 vs −0,130). Con un desvío típico de X (precio vs SMA de 1 h) del orden de 3-6×10⁻⁴ en log, el movimiento esperado por barra es ~1×10⁻⁵ ≈ 0,04 tick de ZB (precio ≈ 115, tick 1/32); incluso con señales de 2σ queda ~0,1 tick, contra un costo de ida y vuelta de ≥ 1 tick (spread 1/32 + comisión). Un orden de magnitud por debajo del costo. No justifica gastar un trial en P&L neto; la pista queda como información de microestructura. Si se quisiera cerrarla formalmente: pre-registrar P&L neto con datos posteriores al holdout.

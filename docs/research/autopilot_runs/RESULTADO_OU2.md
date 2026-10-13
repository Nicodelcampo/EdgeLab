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
- Alfa: 2 rechazos → riqueza 0,0551 (el criterio de hit del autopilot se cumple porque no hay pruebas de réplica en este diseño; interpretarlo como pista de mecanismo, no como hallazgo promovible).

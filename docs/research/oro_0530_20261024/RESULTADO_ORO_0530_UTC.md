# Resultado — Oro a las 05:30 UTC (02:30 en UTC−3)

Estado: VIGENTE. Etapa EF2 (exploratorio). Pre-registro: `PREREGISTRO_ORO_0530_UTC.md` (commit `8c7b5725`). Salida cruda:
`ORO_0530_UTC.json` y las tablas por sesión `ORO_0530_UTC_sesiones_{XAU,GC}.csv`. Kernel `nicolasbuttaro/oro-0530-utc-exploratorio`
(versión 1, XAU v4 recortada, release liquid v4). Sin holdout: XAU 2023-01-03 → 2026-09-30 (967 sesiones), GC 2025-08-05 → 2026-09-30 (270).

## Parte A — la explosión de volumen existe (target-free)
| | 05:20–05:29 (actividad relativa) | **05:30** | 05:31 | 05:35 | burst mediano (05:30–34 / 05:20–29) | sesiones con burst > 2 |
|---|---|---|---|---|---|---|
| XAU (ticks) | 0,60–0,67 | **1,65** | 1,28 | 1,10 | 1,94 (p25–p75 1,50–2,39) | 46 % |
| GC (trades) | 0,56–0,72 | **2,75** | 1,42 | 1,12 | 2,07 (1,56–3,43) | 52 % |
- **Es fijo en UTC**: verano de EE. UU. 1,71 y invierno 1,48 en XAU (3,05 y 2,27 en GC). En hora de Chicago se movería una hora;
  no se mueve. Por año en XAU: 1,43 (2023), 1,69 (2024), 1,69 (2025), 1,81 (2026). Consistente con la reapertura de la tarde de
  Shanghai (13:30 Beijing); no prueba la causa.
- No es el minuto más activo del día: los máximos son las 13:30 UTC (datos de EE. UU. de las 8:30 ET) y, en GC, la apertura del
  NY (13:00–14:30) y las 17:29. Las 05:30 es el pico de la sesión asiática.

## Parte B — 64 pruebas, tamiz FDR (Storey, q 0,10; π0 0,75)
- **No direccional (`rango_h`): 16 de 16 nominadas** (q 0,0003). El rango de los minutos siguientes a las 05:30 es mayor que el
  del mismo tramo una hora antes: mediana de la razón **1,80× a 5 min** en XAU (2,13× en GC), 1,58× a 30 min. Igual en `total` y en
  `reciente`. Es **información**, no P&L: dice que se mueve más, no hacia dónde.
- **Direccional (`deriva`, `arranque`, `previo`): 0 de 48 nominadas.** Ninguna celda cruza el tamiz. Las más cercanas, sin pasar:
  XAU `previo_5` +0,22 USD (q 0,17), `deriva_30` −0,50 (q 0,18), `arranque_15` +0,32 (q 0,23); GC `arranque_15` +0,91 (q 0,18).
  **MDE** en XAU total: 0,21–0,94 USD según el horizonte; en GC y en `reciente`, 0,6–3,5 USD. Contra una fricción canónica de GC
  de 0,605 USD por viaje, los efectos detectables con estos datos están en el orden del costo: un efecto direccional chico pero
  rentable no queda descartado en GC ni en la ventana reciente (sin potencia), y en XAU total queda acotado por el MDE.
- **Económico (informativo)**: en XAU total ninguna celda direccional cubre el costo (neto −0,10 a −0,59 USD).

## Lectura
1. La observación de Nico es correcta y robusta: hay un burst de actividad de ~2× a las 05:30 UTC, todos los años y en las dos
   fuentes.
2. El burst trae **expansión de volatilidad** muy fuerte, pero **sin sesgo de dirección** detectable: ni deriva, ni continuación
   del arranque, ni continuación del movimiento previo.
3. Lo operable que sugiere es **direccionalmente neutro**: una entrada en ruptura (bracket con órdenes stop arriba y abajo del rango
   previo, la primera que se llena cancela la otra) cobra la expansión sin adivinar el lado. **No medido**; es un pre-registro
   nuevo con costos de GC, slippage de stop en el burst y filtro de noticias (a las 05:30 UTC no hay noticias USD tier 1).

## Alcance
EF2: nomina, no confirma. Lo nominado es el canal no direccional (información). Ninguna regla operable quedó nominada.

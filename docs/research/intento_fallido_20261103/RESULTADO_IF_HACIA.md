# Resultado: INTENTO-FALLIDO-HACIA (03/11/2026)

Estado: VIGENTE — embudo y marginales terminados. Pre-registro: `PREREGISTRO_IF_HACIA.md`.

| Campaña | DESC | Réplica abr–sep (canasta de pistas) | Desenlace |
|---|---|---|---|
| IFH-LUX-CFD-NQ-R (U1-CRUZADO) | 1.140 evaluables, 0 nominadas | — | SIN_CANDIDATAS |
| IFH-LUX-NQ-R | 772 evaluables, 0 nominadas | 2 pistas: **−0,31R** (IC90 −0,59 a −0,02) | PISTAS_VIVAS; en contra |
| IFH-RACIMOS-NQ-R | 27.550 evaluables, **3.862 nominadas** | 4 pistas: +0,035R (IC90 −0,45 a +0,44), 38 sesiones | PISTAS_VIVAS; sin potencia |

**Las 3.862 nominadas de racimos no son un edge.** Las celdas que encabezan la lista tienen el TP en el borde cercano y el stop
estructural lejos: muchas ganancias chicas casi seguras y ninguna pérdida en la muestra. Por ejemplo, la primera da 61 operaciones,
IC90 +0,11 a +0,16R y t 9. Es el perfil de «juntar monedas delante de la aplanadora»: con 61 operaciones no aparece la pérdida grande.
Ninguna pasó la selección (meseta y sesiones) y la réplica no lo sostiene.

**Pendiente (pregunta directa de Nico):** ¿cambian el resultado la cantidad de velas de cada pierna, cuánto se acercó, cuánto
rechazó, el volumen sobre la zona o la lógica de entrada? Las marginales están lanzadas en DESC y en réplica (`marginales/`).


## Marginales por variable (R medio por operación; terciles de DESC: bajo / alto / cualquiera)

Datos: `marginales/*.json`. Lo que repite el signo de la diferencia en DESC **y** en réplica:

| Variable | Lectura | LUX CFD→NQ (DESC / REP) | LUX NQ | Racimos NQ |
|---|---|---|---|---|
| **dur_ida** (velas de la primera pierna, alejamiento de la zona) | **pierna corta = peor, en las 3 fuentes y en las 2 ventanas** | bajo −0,18 / −0,16 · alto +0,04 / −0,01 | −0,15 / −0,33 · +0,07 / −0,24 | −0,26 / −0,12 · +0,02 / −0,05 |
| **entrada CONF** (esperar una vela que cierre hacia la zona) | **la mejor entrada en las 3 fuentes y en las 2 ventanas** | CONF 0,00 / +0,01 · MERC −0,05 / −0,02 | −0,05 / −0,23 · −0,08 / −0,24 | −0,03 / 0,00 · −0,08 / −0,07 |
| A/H (cuánto se alejó) | bajo = peor en CFD y racimos; LUX NQ no | bajo −0,13 / −0,06 · alto 0,00 / −0,03 | mixto | bajo −0,13 / −0,16 · alto +0,01 / −0,01 |
| vol_zona (comercio sobre la zona) | zona poco comerciada = peor en CFD; mixto en el resto | bajo −0,18 / −0,18 · alto +0,01 / −0,04 | mixto | mixto |
| acerco | racimos: acercarse menos = mejor (+0,10 / +0,09); en LUX no repite | | | |
| dur_aprox, dur_rech, dur_reac, r, TP | sin patrón estable entre ventanas | | | |

**Respuesta a la pregunta de Nico («¿la cantidad de velas de algún impulso cambia el resultado?»):** sí, la de la **primera pierna**.
Cuando el alejamiento de la zona fue rápido (pocas velas), el reacercamiento hacia la zona rinde peor, en las 3 fuentes y en las 2
ventanas. Las piernas de aproximación, rechazo y reacercamiento no muestran un patrón estable. De las entradas, **la confirmación (CONF)**
es la mejor en todas.

**Lo que no cambia:** todos los niveles siguen ≤ 0R en réplica. Los filtros mejoran la regla, pero no la vuelven positiva por sí solos.
La combinación pre-declarada `dur_ida alto + A/H alto + CONF (+ vol_zona alto en LUX-CFD)` es una hipótesis **nueva**. Se confirma
sólo en datos no usados: 2024-01 → 2025-07, anterior al DESC de estas familias. Si se mide sobre las mismas ventanas, el resultado sale
inflado por haber elegido el filtro mirándolas.

## Confirmación del filtro (2024-01 → 2025-07, CFD con costos de NQ; `PREREGISTRO_IF_HACIA_CONFIRMACION.md`)

**NO CONCLUYENTE.** El filtro congelado deja **10 sesiones** en 19 meses: 84 filas, que son las mismas pocas entradas repetidas en las
12 combinaciones de r y TP. El resultado es +0,13R, con IC90 de −0,46 a +0,67 y p 0,36. La potencia para detectar 0,05R es 0,07.
Ninguna conclusión es posible. Datos: `confirmacion/RESUMEN.json`.

**Lectura:** el filtro A/H alto + `dur_ida` alto + `vol_zona` alto + CONF es demasiado restrictivo para la frecuencia de U1 en el
CFD. La pista sigue viva; para decidir hace falta muestra: forward en papel o una versión con menos condiciones, pre-registrada antes
de mirar más datos.

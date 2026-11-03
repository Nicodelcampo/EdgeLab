# Resultado: INTENTO-FALLIDO v2 (03/11/2026)

Estado: PARCIAL — 3 de 4 fuentes terminadas; IF-LUX-CFD-NQ-R2 (U1-CRUZADO) en curso. Pre-registro: `PREREGISTRO_INTENTO_FALLIDO.md`.
Embudo en R con cola t. Holdout sin tocar.

| Campaña | DESC | Réplica abr–sep (canasta de pistas) | Desenlace |
|---|---|---|---|
| IF-RACIMOS-NQ-R2 | 2.380 evaluables; **320 nominadas por FDR**, ninguna candidata | 15 pistas (12 HACIA): **−0,26R** (IC90 −0,43 a −0,10) | PISTAS_VIVAS; la réplica va en contra |
| IF-LUX-NQ-R2 | 950 evaluables; 0 nominadas | 3 pistas (las 3 HACIA): **+0,12R** (IC90 −0,12 a +0,38), 53 sesiones, potencia 0,27 | PISTAS_VIVAS, sin potencia para decidir |
| IF-AVCL-NQ-R2 | 286 evaluables; 0 nominadas | — | SIN_CANDIDATAS |
| IF-LUX-CFD-NQ-R2 | en curso (la primera carga chocó con la salida por línea en ejecución cruzada: corregido con `LINEAS_SOLO_TIEMPO`) | | |

Lectura: las celdas que destacan en DESC son casi todas **hacia la zona**, sobre todo B80_HACIA (la idea de Nico). En racimos de
aVolZonePOI2 el efecto de DESC es maldición del ganador: la réplica lo invierte. En LUX sobre NQ la réplica es positiva, pero sin potencia.

## ⭐ Pista destacada para profundizar (Nico, 03/11/2026): B80_HACIA

**Lógica:** el precio va hacia la zona, se queda cerca sin tocarla (< y), rechaza z y después **recupera el 80 % del rechazo**.
Recién ahí se entra **hacia la zona**, con stop detrás del extremo del rechazo.

**Por qué se destaca:** en las tres fuentes terminadas, las celdas que más resaltan en DESC son casi todas «hacia la zona», y
B80_HACIA es la que más se repite:
- racimos: 6 de las 15 pistas;
- LUX NQ: 2 de 3;
- LUX NQ: réplica de la canasta +0,12R.

**Qué NO está probado:** ninguna celda confirmó en réplica. En racimos la canasta va en contra (−0,26R), y en LUX no hay potencia.
Es una **pista**, no un edge.

**Cómo profundizar (próximo paso, pre-registrado aparte):**
- B80_HACIA como familia hija sola, con muestra propia y potencia calculada antes;
- controles: el mismo reacercamiento del 80 % sin intento fallido previo, y zonas fantasma;
- variar la confirmación (80/90/100 %) y el objetivo (Z1/Z2/Z3) **dentro** del pre-registro;
- fuentes con más eventos (LUX sobre CFD y ES);
- multiplicidad heredada de INTENTO-FALLIDO.

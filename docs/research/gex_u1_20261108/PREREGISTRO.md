# Pre-registro: GEX-U1 — ¿la canasta U1 gana más con gamma alto? (08/11/2026)

Estado: PRE-REGISTRO (commiteado antes de cruzar; Nico: «Sí» al cruce propuesto a partir de «Las griegas que mueven tu futuro»,
docs 1, 2 y 5, resumidos en `docs/research/MENSAJES_AL_AGENTE_DEBIAN.md`, 28/10). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. EF3. Familia GEX_U1, hija de CANASTA_GLOBAL.

**Hipótesis:** con gamma de dealers alto, su cobertura va contra el movimiento y los desequilibrios revierten (Adams et al. 2026;
Barbon & Buraschi 2020; Baltussen et al. 2021). Las reglas U1 son reversiones tras un impulso: deberían rendir más con gamma alto.
**Cómo podría refutarse:** la canasta U1 no rinde más en el tercil alto de GEX que en el bajo.

**Datos:** serie diaria de R neto de la canasta CANASTA-GLOBAL (10 reglas U1, `docs/research/canasta_global_20261108/`), 338 sesiones
(05/08/2025 → 30/09/2026). GEX neto de SqueezeMetrics (`DIX.csv`, columna `gex`, copia local `data/DIX_squeezemetrics_20261108.csv`),
**del día hábil anterior** a cada sesión (conocido antes de operar). En la ventana sólo 9 días con GEX < 0: el signo no tiene potencia.

**Prueba (una):** terciles de `gex_{t-1}` calculados sólo sobre el GEX de la ventana (sin desenlaces). Estadístico = R medio de la
canasta en el tercil alto − R medio en el tercil bajo. p de una cola por permutación de las etiquetas de tercil entre sesiones
(B = 10.000). Pasa si p < 0,10 y la diferencia > 0. Se reporta también el tercil medio (monotonía) y, descriptivo, octubre (holdout).

**Limitación:** las 10 reglas se eligieron en esta misma ventana; la prueba no es sobre su media (ya seleccionada) sino sobre cómo se
reparte entre regímenes de gamma, pero igual se confirma hacia adelante. **Si pasa:** el filtro de gamma se agrega como condición
congelada a la canasta U1 en papel.

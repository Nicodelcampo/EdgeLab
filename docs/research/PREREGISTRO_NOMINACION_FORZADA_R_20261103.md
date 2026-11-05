# Pre-registro: nominación forzada al holdout de las campañas en R (03/11/2026)

Estado: VIGENTE — OK de Nico el 03/11 («Sí, y luego al holdout»): puntos 1, 2 y 3. Registrado antes de abrir el holdout de estas reglas. Referente `docs/NORTH_STAR.md`, cuerpo
SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Regla de origen: `relanzamiento_causal_20261102/PREREGISTRO_NOMINACION_FORZADA.md` (`tools/nominacion_forzada.py`).

## Qué se hizo antes

Ninguna campaña del relanzamiento causal llegó sola al holdout. Nico decidió «si no se nomina ninguna, nominá las mejores». La regla
fija, por familia sin candidata, es tomar la pista de réplica con:
- n ≥ 30, media de réplica > 0 y media de DESC > 0;
- la mayor cota inferior del IC90 de réplica entre las que cumplen; una por familia.

Así entraron a papel con e-proceso CVGAP-ES-C, CVGAP-CFD-ES-C y U1-ZONAS-AVCL-ES-C.

## La misma regla sobre las 62 campañas en R de hoy (sólo informe; sin actas ni LORD++)

705 pistas; 125 cumplen la regla, en 33 campañas. Las primeras, por cota inferior del IC90 de réplica (R por operación):

| Campaña | n réplica | DESC | Réplica | IC90 réplica | ¿Holdout ya usado? |
|---|---|---|---|---|---|
| ASIA-NQ-R | 35 | +0,37 | +0,39 | **+0,09** a +0,69 | no; **ya en papel (canasta v5)** |
| **TORI-NQ-R** | 33 | +0,29 | +0,27 | **+0,03** a +0,49 | no |
| CVGAP-ES-C-R | 49 | +0,40 | +0,30 | **+0,02** a +0,60 | sí; **ya en papel** |
| **CONF-CVR-CFD-NQ-R** | 34 | +0,15 | +0,12 | **+0,01** a +0,22 | no |
| U1-ZONAS-AVCL-NQ-R | 98 | +0,10 | +0,07 | **+0,01** a +0,13 | sí (acta de la canasta) |
| TORI-GC-R | 34 | +0,41 | +0,37 | −0,02 a +0,75 | no |
| EXPZ-CFD-R | 146 | +0,36 | +0,14 | −0,05 a +0,34 | no |
| U1-RACIMOS-GRILLA-ES-R | 36 | +0,20 | +0,11 | −0,06 a +0,28 | sí |
| IF-RACIMOS-NQ-R2 | 36 | +0,24 | +0,13 | −0,07 a +0,29 | no |
| IF-LUX-NQ-R2 | 43 | +0,44 | +0,25 | −0,08 a +0,59 | no |

La lista completa queda en `docs/research/nominacion_forzada_R_20261103.json`.

## ¿Lo que está en papel es peor que lo que no se nominó?

Sí, en parte. Medido igual, en R y en réplica:

| En papel | Mejor pista en R (réplica) | Canasta de pistas en réplica |
|---|---|---|
| ASIA-NQ (v5) | +0,39 (IC90 +0,09 a +0,69) | +0,035 |
| CVGAP-ES-C | +0,30 (IC90 +0,02 a +0,60) | −0,094 |
| U1-CRUZADO | — | réplica +0,015R |
| OTR930-NQ (v5) | +0,20 (IC90 −0,13 a +0,52) | +0,012 |
| U1-ZONAS-AVCL-ES-C | ninguna pista cumple | −0,028 |
| CVGAP-CFD-ES-C | +0,07 (IC90 −0,27 a +0,43) | −0,025 |
| PRERANGE-ZONAS-NQ (v5) | ninguna pista cumple | −0,20 |
| RANGO0100-NQ (v5) | ninguna pista cumple (SIN_CANDIDATAS) | — |

**TORI-NQ y CONF-CVR-CFD-NQ** tienen la cota inferior del IC90 de réplica positiva y no están en papel. Son **mejores**, en esta métrica, que
CVGAP-CFD-ES-C, U1-ZONAS-AVCL-ES-C, PRERANGE-ZONAS-NQ y RANGO0100-NQ, que sí están.

## Advertencias (no se pueden saltear)

- **Maldición del ganador.** Es elegir la mejor pista entre muchas. Medido en 44 familias, las pistas en su réplica dieron −0,042R en
  promedio (IC90 −0,056 a −0,028). Una cota inferior > 0 sobre 33 o 34 operaciones es frágil.
- **Excepción humana.** Es una nominación sin confirmación en réplica: el holdout pasa a ser la única prueba limpia, y por eso sólo se
  abre una vez por familia.
- **Potencia.** El holdout tiene hoy un mes, octubre (la exportación de noviembre está pendiente). Con N fijo de 150 operaciones, casi
  todas quedan EN CURSO. El vehículo práctico es el papel con e-proceso, como se hizo con las forzadas anteriores.
- **SEGUNDO-INTENTO** (12 campañas) todavía corre y entra a esta misma lista cuando termine.

## Propuesta

1. Aplicar la regla tal cual, pero con una exigencia más: **cota inferior del IC90 de réplica > 0**, para no nominar las 33.
   Nominar TORI-NQ y CONF-CVR-CFD-NQ (las únicas nuevas que la cumplen y no usaron su holdout), con acta, paso de LORD++ reservado antes y
   papel con e-proceso.
2. Revisar el papel: sacar, o marcar para no seguir, las reglas cuya réplica en R quedó ≤ 0. La regla de R > 0 forward para promover
   (firmada) ya las frenaría, pero hoy ocupan lugar en la cartera.
3. Correr la misma selección sobre SEGUNDO-INTENTO cuando termine.

## Ejecución aprobada

1. **Nominadas:** TORI-NQ-R y CONF-CVR-CFD-NQ-R, con acta `ACTA_HOLDOUT.json` de N fijo 150, paso de LORD++ reservado antes y sin tope.
   Luego papel con e-proceso. La herramienta es `tools/nominacion_forzada.py --cota-min 0`.
2. **Retiradas del papel** (réplica en R ≤ 0): CVGAP-CFD-ES-C-PAPEL, U1-ZONAS-AVCL-ES-C-PAPEL, PRERANGE-ZONAS-NQ-CANASTA y RANGO0100-NQ-CANASTA.
3. **SEGUNDO-INTENTO** pasa por la misma selección al terminar.

## Papel (fichas, con las mismas reglas que las forzadas del 02/11, `PREREGISTRO_PAPEL_CVGAP_ES.md`)

- **Cotas:** 3 × la peor y la mejor operación de desarrollo (DESC + réplica, causal, en puntos).
- **`mu_util`:** 0,5 × min(media DESC, media réplica).
- **`sd`:** el de esas mismas operaciones de desarrollo.
- **Ventana:** desde 20261001.
- **Retiro y promoción:** por e-proceso, con la regla de R > 0 forward para pasar a REAL.

| Ficha | Cotas (pérdida / ganancia, pts) | `mu_util` | `sd` |
|---|---|---|---|
| TORI-NQ-R-PAPEL | −290,4 / +356,9 | 4,83 | 31,7 |
| CONF-CVR-CFD-NQ-R-PAPEL | −432,9 / +223,4 | 2,49 | 29,1 |

## Holdout (primera lectura, 2026-10-01 → 30; N fijo 150 → EN CURSO)

| Regla | Desarrollo DESC / réplica (R; reproduce el embudo) | Holdout: n, media R, IC90 |
|---|---|---|
| TORI-NQ-R | +0,29 / +0,27 | 8 ops, **−0,14R** (−0,60 a +0,32) |
| CONF-CVR-CFD-NQ-R | +0,15 / +0,12 | 4 ops, **+0,19R** (+0,15 a +0,22) |

Con 8 y 4 operaciones no hay decisión: el veredicto es a las 150 o por el e-proceso del papel.

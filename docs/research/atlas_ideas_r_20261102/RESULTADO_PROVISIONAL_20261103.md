# Atlas de ideas en R: resultado provisional (03/11/2026)

Estado: PROVISIONAL. Faltan las 6 familias relanzadas por el bug de riesgo (ver
`../relanzamiento_R_20261102/descartadas_riesgo_flotante/README.md`). El resultado final se corre con las 118 marginales.

**Integridad antes que interpretación.** La primera corrida de `analizar` (118/118) dio efectos de millones de R. Causa raíz: stops en la
entrada con riesgo ≈ 1e-10. Se corrigió `riesgo_ops`, se apartaron las 12 marginales contaminadas y se relanzaron.

**Con las 106 marginales limpias** (DerSimonian-Laird por componente; BH q 0,10 en DESC; confirmación en réplica con p unilateral < 0,05):

| Componente | Familias | DESC | Réplica | Estado |
|---|---|---|---|---|
| stop=S3 (más allá del extremo, contra S2 = 1× distancia al objetivo) | 10 | +0,080R (p 0,001) | +0,070R (p 0,008) | **descubierto y confirmado** |
| be=0,5 | 4 | +0,179R (p 0,024) | +0,140R (p 0,076) | no pasa BH |
| objetivo=T1 (borde cercano) | 10 | −0,042R | −0,040R | no significativo; mismo signo que «cortar ganancias resta» |
| el resto | | \|efecto\| < 0,1R | | sin señal |

**Lectura (provisional).** El único componente transferible que aparece es el stop estructural (más allá del extremo de la formación) en
lugar del stop a distancia fija. Es coherente con el Programa R: los stops ajustados y cortar ganancias restan R. Hay una advertencia
pendiente: S3 es el stop que generaba los riesgos ≈ 0 en las familias contaminadas, y ahora esas operaciones quedan fuera de la medición en
R (NaN). En el resultado final hay que publicar cuántas operaciones quedaron sin riesgo por familia. Si son muchas, la ventaja de S3 puede
ser en parte por exclusión, y entonces hay que medirla con un piso de 1 tick como sensibilidad.

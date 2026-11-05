# ¿El holdout difiere de los otros períodos, todos con el código causal? (2026-11-02)

Estado: VIGENTE (descriptivo). Pedido de Nico: «fijate si el resultado del holdout difiere mucho del promedio del resto de períodos, si
al resto de períodos se les aplica la nueva regla de causalidad». Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. No decide ninguna regla: eso lo hace cada acta a su N fijo.

## Método (`tools/holdout_vs_desarrollo.py`, resultado en `holdout_v3/HOLDOUT_VS_DESARROLLO.json`)
- **Desarrollo:** DESC causal + réplica causal de cada regla. **Holdout:** 10-01 → 10-30, sólo sesiones válidas.
- **Diferencia de medias:** IC90 por bootstrap de sesiones, remuestreando cada período por separado, y p bilateral con Holm sobre las
  13 reglas.
- **z de predicción:** (media del holdout − media de desarrollo) / (desvío por operación de desarrollo / √n del holdout).

## Resultado (media neta por operación, puntos del instrumento de ejecución)
| Regla | DESC | Réplica | Desarrollo (n) | Holdout (n) | Diferencia [IC90] | z | p Holm |
|---|---|---|---|---|---|---|---|
| CVGAP-NQ | +15,2 | +15,8 | +15,5 (196) | **−34,9 (20)** | −50,4 [−86,3; −15,7] | **−2,70** | 0,20 |
| CVGAP-CFD-NQ | +17,8 | +5,8 | +11,8 (221) | **−22,9 (16)** | −34,8 [−53,9; −11,0] | **−2,45** | 0,22 |
| U1-ES-GRILLA | +0,4 | −1,5 | +0,2 (474) | −6,2 (11) | −6,4 [−13,5; −0,6] | −1,71 | 0,54 |
| U1-ZONAS-NQ | +22,2 | +2,9 | +14,3 (159) | −14,6 (17) | −28,9 [−79,9; +10,2] | −1,43 | 1 |
| U1-ZONAS-ES | +8,9 | −0,1 | +7,3 (73) | +1,0 (2) | −6,3 | −0,50 | 1 |
| U1-ZONAS-BT2-ES | +3,3 | +2,5 | +2,9 (65) | +3,2 (5) | +0,2 | +0,09 | 1 |
| U1-ZONAS-BT2-NQ | +4,5 | +5,1 | +4,7 (108) | +6,9 (10) | +2,2 | +0,18 | 1 |
| U1-RACIMOS-GRILLA-ES | +4,9 | −0,9 | +2,4 (149) | +6,1 (9) | +3,7 | +0,62 | 0,86 |
| U1-ORO-GRILLA | +5,2 | −1,3 | +3,0 (68) | +7,7 (3) | +4,7 | +0,66 | 0,60 |
| U1-CRUZADO | +4,4 | +15,6 | +11,4 (173) | +25,8 (18) | +14,3 [−6,6; +37,7] | +0,79 | 1 |
| U1-ZONAS-AVCL-NQ | +5,6 | +4,0 | +4,7 (97) | +15,0 (7) | +10,3 [+0,4; +20,1] | +1,10 | 0,60 |
| U1-YM-GRILLA | +5,7 | −10,2 | +3,1 (234) | +67,0 (3) | +63,9 | +1,21 | (*) |
| U1-RACIMOS-GRILLA-NQ | +17,3 | +14,8 | +16,7 (64) | +43,7 (5) | +27,0 [+6,0; +48,5] | +1,36 | 0,20 |

(*) U1-YM tiene 3 operaciones en 2 sesiones. El bootstrap con 2 sesiones degenera y su p no es interpretable.

## Lectura
- **Ninguna regla difiere de su desarrollo de forma significativa con la corrección por 13 reglas.** El holdout es compatible con lo
  que el código causal mostraba antes.
- **Las dos CVGAP son las únicas que se apartan mucho.** Quedan 2,7 y 2,5 errores estándar por debajo de su desarrollo, del lado
  malo, y las dos en el mismo mes. Sin corrección, la probabilidad de algo así sería de ≈ 1 % cada una. Corregido por 13 reglas no
  alcanza (Holm 0,20 y 0,22), pero es la señal más fuerte de un posible cambio de comportamiento. Encaja con que estén en alerta en el
  holdout individual. Con N fijo 150 su acta decide; las reviso primero cuando entren datos nuevos.
- **Las U1 de NQ (RACIMOS, AVCL y CRUZADO) dan mejor que su desarrollo**, pero con 5 a 18 operaciones. No se lee como mejora: es
  compatible con el azar (z ≈ 0,8 a 1,4).
- **El resto está a menos de 1 error estándar** de su desarrollo.

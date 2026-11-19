# Cosecha v4: lectura del holdout sellado (2026-10-01 → 2026-11-13)

Estado: RESULTADO — lectura pre-registrada (`PREREGISTRO.md` §4), descriptiva salvo el e-proceso. North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `HOLDOUT.json`, `hold/*.json` (7 corridas selladas;
fallidas y relanzadas, sin datos producidos, en `hold/FALLIDAS.jsonl`). Selección commiteada antes (`4e1019f`).

## Canasta (10 reglas, R por sesión = suma de las reglas)
| | Sesiones | Operaciones | R total | R por sesión | t | e-proceso | Lectura |
|---|---|---|---|---|---|---|---|
| Holdout completo | 27 | 73 | −4,55 | −0,17 | −0,45 | 0,93 | SIN_DECIDIR |
| Sin sesiones ≤ 22-oct en familias hijas de AREAS_EXP_1 | 25 | 61 | −5,88 | −0,24 | −0,59 | 0,92 | SIN_DECIDIR |

- Frecuencia: 73 operaciones en ≈ 1,4 meses ≈ 52 por mes, la del plan (50,6): la canasta opera lo previsto.
- Contra el plan (mitad del efecto de desarrollo, +0,16 R/op → +11,8 R esperados en 73 operaciones; desvío de la suma ≈ 9,9 R): lo
  observado (−4,6 R) está 1,6 desvíos por debajo del plan y 0,5 por debajo de cero. Coincide con el paso 2 de
  `urgencia_vs_evidencia_20261117` (lo elegido por el embudo arranca con media ≈ 0), no con la media de desarrollo.
- No hay futilidad todavía (exige 60 sesiones con operaciones) ni EDGE (e ≥ 10). Sigue en forward con el mismo e-proceso; nada se cambia.

## Por regla (descriptivo; no se saca ni se pondera ninguna con esto)
| Regla | Ops | R/op | R total | e |
|---|---|---|---|---|
| IF-LUX-NQ-R2#1 | 8 | +0,93 | +7,41 | 1,26 |
| CVGAP2-GC#5 | 5 | +0,29 | +1,46 | 1,05 |
| U1-ZONAS-GRILLA-YM-C-R#0 | 7 | +0,15 | +1,02 | 1,03 |
| COMEX-CIERRE-GC-R#0 | 5 | −0,13 | −0,63 | 0,97 |
| CVGAP2-NQ#18 | 8 | −0,11 | −0,84 | 0,97 |
| ORO-ALM-CFD#4 | 2 | −0,43 | −0,86 | 0,97 |
| CVGAP2-GC#11 | 4 | −0,36 | −1,45 | 0,95 |
| ORO-ALM-CFD#18 | 3 | −0,79 | −2,36 | 0,93 |
| IF-LUX-CFD-NQ-R2#0 | 19 | −0,19 | −3,62 | 0,86 |
| CVGAP2-NQ#3 | 12 | −0,39 | −4,68 | 0,86 |

## Lectura honesta
Seis semanas no deciden nada (potencia mínima a este N). Pero la dirección es la que predijo el paso 2: la cosecha produjo candidatas
diversificadas y frecuentes, no una ventaja visible todavía. Lo que la decide más rápido es el «atrás» con M1 de futuros de NT8
(2018 → jul-2025, calibrado regla por regla; ver la respuesta del 2026-11-17 y `ATRAS_EVALUACION.md`) y los datos sellados nuevos.

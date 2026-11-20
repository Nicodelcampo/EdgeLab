# LucidFlex: el tramo 2025-08 → 2026-09 y operar minis en vez de micros (2026-11-19)

Estado: VIGENTE — cálculo descriptivo sobre operaciones ya medidas (no elige reglas, no abre REP ni holdout, no cuenta pruebas). Pedido de
Nico: «¿qué pasa después del desarrollo de 2025-07? ¿gana menos? ¿qué pasa si se operan minis en vez de micros?». North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Código: `tools/lucid_guia.py extra`; datos: `LUCID_GUIA_EXTRA.json`.

## 1. Después de 2025-07
- Hay datos hasta el 2026-09-30. Desde la sesión del 2026-10-01 empieza el holdout terminal sellado (A4): no se mira; lo lee la vigilancia
  forward (`regimen_forward_20261119/`).
- **2025-08 → 2026-09 no es fuera de muestra:**
  - el vendedor armó la versión de T el 29-oct-2025;
  - la configuración de R y la banda de Z se eligieron viendo datos hasta 2026-09.
  - Son 14 meses.

R neto por regla (NQ, fricción canónica de NQ):

| Regla | Período | Ops/mes | R/op | R/mes | t mensual | % meses + |
|---|---|---|---|---|---|---|
| T | 2020-01 → 2025-07 | 19,2 | +0,156 | +2,99 | 5,22 | 69 % |
| T | 2025-08 → 2026-09 | 18,4 | +0,186 | +3,42 | 1,95 | 50 % |
| R | 2020-01 → 2025-07 | 2,8 | +0,463 | +1,31 | 3,80 | 66 % |
| R | 2025-08 → 2026-09 | 2,4 | +0,738 | +1,79 | 2,71 | 79 % |
| Z-banda | 2020-01 → 2025-07 | 2,5 | +0,316 | +0,78 | 3,77 | 61 % |
| Z-banda | 2025-08 → 2026-09 | 2,6 | +0,144 | +0,37 | 0,56 | 50 % |
| T+R+ZB | 2020-01 → 2025-07 | 24,5 | +0,207 | +5,08 | 6,47 | 76 % |
| T+R+ZB | 2025-08 → 2026-09 | 23,4 | +0,239 | +5,59 | 2,34 | 64 % |

Por año, T+R+ZB (R/op; R/mes):

| Año | R/op | R/mes |
|---|---|---|
| 2018 | +0,112 | +2,78 |
| 2019 | −0,004 | −0,10 |
| 2020 | +0,132 | +3,08 |
| 2021 | +0,197 | +4,78 |
| 2022 | +0,278 | +7,11 |
| 2023 | +0,183 | +4,59 |
| 2024 | +0,307 | +7,53 |
| 2025 | +0,164 | +3,87 |
| 2026 (ene–sep) | +0,225 | +5,22 |

Z-banda en 2026 (ene–sep): −0,111 R/op.

Lucid con la media realizada de cada período (sin contraer; T+R+ZB, micros por riesgo, DLL, 50 %):

| Tamaño | Período | USD/día (sd) | Pasa | Días a pasar p10/50/90 | Días a quemar la evaluación p50 | Días al 1.er retiro p50 | Cobra si pasa | EV/examen |
|---|---|---|---|---|---|---|---|---|
| 25K | 2020-01 → 2025-07 | 36 (224) | 72 % | 10 / 25 / 54 | 22 | 36 | 67 % | +1.709 |
| 25K | 2025-08 → 2026-09 | 53 (287) | 65 % | 6 / 16 / 37 | 16 | 20 | 63 % | +1.408 |
| 50K | 2020-01 → 2025-07 | 38 (237) | 90 % | 29 / 64 / 126 | 58 | 89 | 89 % | +6.632 |
| 50K | 2025-08 → 2026-09 | 53 (288) | 84 % | 17 / 43 / 93 | 45 | 57 | 83 % | +5.670 |

## 2. Minis en vez de micros (T+R+ZB, 2020-01 → 2025-07, media contraída a la mitad salvo «sin ventaja»)
- **Tamaño de los contratos:** 1 NQ = 10 MNQ en tamaño.
- **Fricción canónica por contrato:** NQ 1,55 puntos (31 USD); MNQ 1,98 puntos (3,96 USD), o sea 39,6 USD cada 10 micros.
- **El tamaño por riesgo con micros ya da ≈ 1 micro por operación.** Con 100 USD de presupuesto, el riesgo real queda en 166 USD de
  mediana. Con 1 mini es 1.661 USD de mediana (p10 1.013, p90 2.000).

| Tamaño | Contratos por regla | Riesgo real p50 (USD) | USD/día (sd) | Pasa | Días a pasar p50 | Días a quemar la evaluación p50 | EV/examen | EV/examen sin ventaja | EV por mes de cuenta | Cartera 24 m con 10 evaluaciones (p10 / p50 / p90) |
|---|---|---|---|---|---|---|---|---|---|---|
| 25K | micros por riesgo (≈ 1) | 166 | 18 (224) | 49 % | 27 | 22 | +501 | +43 | +170 | +18.479 (+4.614 / +19.247 / +30.505) |
| 25K | 1 mini | 1.661 | 184 (2.240) | 56 % | 10 | 3 | +1.322 | +889 | +961 | +17.972 (+14.334 / +18.292 / +20.992) |
| 25K | 10 micros | 1.661 | 179 (2.239) | 56 % | 10 | 3 | +1.324 | +898 | +960 | +17.980 |
| 50K | micros por riesgo (≈ 1,1) | 177 | 19 (237) | 63 % | 79 | 66 | +2.255 | +78 | +201 | +20.124 (−3.237 / +21.496 / +41.764) |
| 50K | 1 mini | 1.661 | 184 (2.240) | 44 % | 11 | 4 | +1.404 | +757 | +1.328 | +35.454 (+24.706 / +36.636 / +43.477) |
| 100K | micros por riesgo (≈ 1,5) | 200 | 25 (317) | 63 % | 140 | 84 | +3.020 | +18 | +219 | — |
| 100K | 1 mini | 1.661 | 184 (2.240) | 37 % | 12 | 6 | +982 | +293 | +1.020 | — |
| 100K | 2 minis | 3.323 | 368 (4.479) | 50 % | 11 | 4 | +2.428 | +1.451 | +2.015 | — |
| 150K | micros por riesgo (≈ 2,7) | 400 | 43 (545) | 59 % | 112 | 67 | +2.979 | +72 | +326 | +35.198 (−8.593 / +42.268 / +64.896) |
| 150K | 1 mini | 1.661 | 184 (2.240) | 35 % | 16 | 8 | +943 | +122 | +844 | +55.513 (+27.542 / +54.288 / +88.605) |
| 150K | 2 minis | 3.323 | 368 (4.479) | 41 % | 11 | 4 | +1.734 | +853 | +1.717 | +47.971 (+26.890 / +51.225 / +62.993) |

1 mini y 10 micros dan lo mismo (la diferencia de fricción es ≈ 5 USD por día). Lo que cambia es el tamaño, no el contrato.

## 3. Límites del modelo que pesan más con minis
- **El DLL se modela como un corte del P&L del día.** Con 1 mini en la 25K el riesgo de una sola operación (1.661 USD) supera el DLL (600)
  y la pérdida máxima (1.000).
- **El piso se controla al cierre del día; Lucid lo controla también durante el día.** Una operación que toca el piso y después termina
  ganadora cuenta como ganadora en la simulación y como cuenta quemada en la realidad.
- Por eso, con minis, la tasa de aprobación y el EV de la tabla están sobrestimados. Con micros el caso casi no ocurre: el peor día es
  −492 USD en la 25K.
- **Máximo de contratos:** 25K admite 2 minis, y T, R y Z pueden coincidir el mismo día (3 minis).
- **Sin ventaja:** con 1 mini el EV por examen sin ventaja es +889 (25K): la mayor parte del EV con minis viene de la varianza de la cuenta,
  no de la canasta. Las condiciones de Lucid permiten quitar ganancias por operar contra los objetivos (ver `../propfirm_lucidflex_20261117/RESULTADO.md`).

## Justificación económica / cómo podría refutarse
- **Justificación:** el tamaño cambia cuánto de la ventaja llega a la cuenta y cuánto pesa la opción de la cuenta (pérdida acotada al precio).
- **Cómo podría refutarse:** el forward de la canasta con media ≤ 0, o una simulación intradía del piso y del DLL con minis que baje el EV
  por debajo del de micros.

Aporte al referente: muestra que el último tramo de desarrollo no rinde menos por mes que el anterior (con una Z-banda más débil en 2026), y
que pasar a minis cambia sobre todo el tamaño y la varianza, con un EV que en buena parte no depende de la ventaja.

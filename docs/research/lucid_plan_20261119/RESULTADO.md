# LUCID-PLAN: qué plan de LucidFlex da más dinero y cómo habría ido en el holdout (2026-11-19)

Estado: VIGENTE — resultado del plan pre-registrado en `PLAN.md` (commit anterior a la corrida). Descriptivo, no cuenta pruebas.
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Código: `tools/lucid_plan.py`; datos: `PLANES.json`
(872 planes en la etapa 1 y 300 combinaciones en la etapa 2) y `HOLDOUT_REPLAY.json` (bitácora por cuenta y por día).

## 1. Elección (desarrollo 2020-01 → 2026-09, piso y DLL dentro del día)
- **Criterio pre-registrado:** máximo neto medio a 12 meses con la media contraída a la mitad, entre los planes con P(neto 12 m > 0) ≥ 0,8.
- **Resultado:** ningún plan llega a 0,8; el máximo es 0,7997. Sin relajar el criterio, se fijaron dos planes antes de mirar el holdout:
  - **A** = el de mayor neto medio;
  - **B** = el de mayor P(neto > 0).

| | Plan A | Plan B |
|---|---|---|
| Cuenta | LucidFlex 150K, DLL ($2.700), consistencia 50 % ($260) | LucidFlex 50K, DLL ($1.200), consistencia 50 % ($95) |
| Reglas y contratos | T 9 MNQ, R 9 MNQ, Z-banda 1 MNQ por cada una de las 9 configuraciones | T 5 MNQ, R 5 MNQ |
| Retiros | esperar el máximo ($3.000) | en cuanto se pueda (≥ $500) |
| Evaluaciones a la vez | 10 (una compra por día) | 10 (una compra por día) |
| Neto 12 m, media contraída: media (p10 / p50 / p90) | +28.239 (−25.759 / +37.773 / +63.885) | +20.715 (−9.377 / +24.528 / +43.012) |
| P(neto 12 m > 0) | 0,76 | 0,80 |
| Neto 24 m, media contraída | +43.142 | +32.794 |
| Neto 12 m con la media de desarrollo | +52.151 | +33.619 |
| Neto 12 m sin ventaja (media cero) | −7.386 | +2.905 |
| Caja mínima en el camino p50 / p10 | −13.020 / −37.969 | −5.236 / −15.051 |
| Evaluaciones compradas en 24 m | 109 | 150 |
| Paso a live en 24 m | 84 % (mediana 9,8 meses) | 77 % (mediana 10,1 meses) |
| Peor mínimo intradía de un día (USD) | −5.852 | −2.647 |

Mejor plan de cada tamaño en la etapa 1 (3 evaluaciones a la vez, media contraída), neto medio 12 m (p10 / p50 / p90; P > 0):

| Tamaño | Plan | Neto medio 12 m | p10 / p50 / p90 | P(> 0) |
|---|---|---|---|---|
| 25K | T+R, 3 MNQ, DLL, 50 %, retiro mínimo | +6.178 | −3.696 / +5.863 / +16.162 | 0,73 |
| 50K | T+R, 5 MNQ, DLL, 50 %, retiro máximo | +12.217 | −6.570 / +11.042 / +33.184 | 0,71 |
| 100K | T+R+ZB, 9 MNQ, DLL, 50 %, retiro mínimo | +12.897 | −12.823 / +12.318 / +39.486 | 0,67 |
| 150K | T+R+ZB, 9 MNQ, DLL, 50 %, retiro máximo | +15.432 | −13.715 / +12.452 / +46.394 | 0,66 |

Lo que se ve en la grilla:
- Cuantas más evaluaciones a la vez, mayor el neto (en A: 1 → 6.277, 3 → 15.687, 5 → 21.837, 10 → 28.239).
- Con DLL rinde más que sin DLL en todos los primeros puestos.
- Consistencia de 50 % mejor que la de 40 %.
- Las minis (s = 10) quedan debajo de 9 micros en los mismos planes (150K: +13.466 contra +15.432).

## 2. Reproducción en el holdout (2026-10-01 → 2026-11-13, 32 sesiones)
- **Datos:** sólo las operaciones publicadas el 2026-11-16 (`FUNDEDSYNC_HOLDOUT_OPS.csv`; USATECH sellado con costos de NQ). No es un test
  ciego: esos resultados ya se habían visto.
- **T:** misma regla que el plan. En el holdout: 26 operaciones, +14,2 pts de media; octubre +388 pts (17 operaciones), noviembre −19 (9).
- **R y Z:** son de fábrica, sin el stop 0,25 × ATR20 ni la excursión adversa. No son las reglas del plan, y la Z-banda no existe en el
  holdout (se usó Z de fábrica con 9 MNQ).
- **Excursión adversa de las ganadoras de T:** no está en el archivo; se dan dos casos (0 y el riesgo entero).

| Plan | Escenario | Evaluaciones compradas | Pasaron | Estado al 2026-11-13 | Retiros | Gastado | Cobrado | Caja |
|---|---|---|---|---|---|---|---|---|
| A | sólo T, MAE de ganadoras 0 | 15 | 8 (todas el 27-oct) | 5 fondeadas quemadas el 3-nov, 3 fondeadas vivas, 7 evaluaciones abiertas | 0 | 3.906 | 0 | **−3.906** |
| A | sólo T, MAE = riesgo | 17 | 8 | 8 fondeadas quemadas, 6 evaluaciones quemadas, 3 abiertas | 0 | 4.427 | 0 | **−4.427** |
| A | T + R + Z de fábrica sin stop | 10 | 10 (16-oct) | 5 fondeadas con 1 retiro cada una, 5 aprobadas esperando lugar | 5 × $2.700 | 2.604 | 13.500 | **+10.896** |
| B | sólo T, MAE 0 | 23 | 4 | 4 fondeadas quemadas el 30-oct, 9 evaluaciones quemadas, 10 abiertas | 0 | 2.190 | 0 | **−2.190** |
| B | sólo T, MAE = riesgo | 28 | 4 | 4 fondeadas quemadas, 22 evaluaciones quemadas, 2 abiertas | 0 | 2.666 | 0 | **−2.666** |
| B | T + R de fábrica sin stop | 23 | 6 | 6 fondeadas quemadas, 7 evaluaciones quemadas, 10 abiertas | 0 | 2.190 | 0 | **−2.190** |

- R en el holdout: 5 operaciones, +448, −325, +1.098, +293 y −74 pts. Z: 7 de 7 ganadoras (+137 pts de media). En el escenario A con R y Z
  los retiros vienen de esas operaciones; con el stop del plan la pérdida de −325 habría quedado cortada en ≈ 0,25 × ATR20, y no se sabe si
  el stop habría sacado antes alguna ganadora.
- Todas las cuentas operan lo mismo, así que pasan y se queman juntas: en A, las 8 que pasaron lo hicieron el mismo día y 5 se quemaron el
  mismo día.
- 32 sesiones son una sola trayectoria: la simulación de desarrollo da, para 12 meses, un rango de −25.759 a +63.885 (p10–p90) para A.

## Justificación económica / cómo podría refutarse
- **Justificación:** el plan apalanca la ventaja de T y R (y de la Z-banda en A) con la asimetría de la cuenta; el tamaño frente al piso
  decide cuánto pesa cada una.
- **Cómo podría refutarse:** el forward de la canasta con media ≤ 0 (`regimen_forward_20261119/`). Con media cero, el plan A pierde
  −7.386 en 12 meses y el B gana +2.905.

Aporte al referente: cuantifica con piso y DLL intradía qué tamaño, contratos y cantidad de evaluaciones dan más dinero con la canasta
candidata, muestra que ningún plan llega a 80 % de probabilidad de ganar en 12 meses con la media recortada, y deja la reproducción en el
holdout ya abierto: con T sola los dos planes pierden lo gastado en evaluaciones, y sólo el escenario con R y Z sin stop cobra.

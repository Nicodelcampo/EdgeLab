# Señales estables (SOM, Franklin, T) en LucidFlex 25K con MNQ y tamaño por riesgo (descriptivo, 2026-11-18)

Estado: VIGENTE — descriptivo sobre operaciones ya medidas (`docs/research/m1_largo_20261117/`, M1 de NT8, 2020-01 → 2025-07). No elige
reglas ni cuenta pruebas.
- **Aviso (2026-11-18, después):** las filas con ORB5 quedan SIN BASE: la confirmación de ORB O1 en el holdout dio neto < 0 y NQ
  2020–25 −0,03 bruto (`docs/research/orb_a5_20261118/RESULTADO_CONFIRMACION_O1.md`). No usar ORB5 en canastas.

North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Pedido de Nico:** «trabajá para encontrar edges que pueda usar en las propfirms».
- **Código:** `python tools/lucid_canastas.py senales`. **Datos:** `CANASTA_SENALES_LUCID.json`.

## 1. Neto con costos de MICROS
Las prop firms operan micros, y en MNQ la fricción por punto es mayor que en NQ: 1,98 contra 1,55 pts ida y vuelta.

| Regla | Bruto 2006–11 / 2012–19 / 2020–25 (R) | Neto MNQ 2020–25 | Fricción MNQ en R (mediana 2020–25) | Ops/año |
|---|---|---|---|---|
| SOM (sin_eod) | +0,062 / +0,101 / +0,094 | +0,078 | 0,01 | ≈ 220 |
| SOM (sin_finde, la celda de la canasta) | +0,061 / +0,085 / +0,065 | +0,049 | 0,01 | ≈ 235 |
| Franklin | +0,126 / +0,079 / +0,126 | +0,099 | 0,02 | ≈ 110 |
| T (FtmOrb) | +0,016 / +0,048 / +0,179 | +0,153 | 0,02 | ≈ 230 |

- **SOM y Franklin** tienen bruto estable en las tres épocas: lo que cambió fue la fricción relativa.
- **T** salta desde 2020 (pasa ES/YM; `RESULTADO_T_2020.md`).
- **Hoy los costos de micro no los matan:** casi todas las operaciones caen en el subconjunto operable (fricción ≤ 0,08 R).

## 2. En la cuenta (20.000 cuentas por escenario)
**Escenario:** 1 MNQ mínimo, micros por riesgo (USD 100–250 por operación; casi siempre queda en 1 micro, porque el riesgo de NQ en puntos es
grande). Reglas oficiales de Lucid. La media está contraída a la mitad (declarado: el efecto 2020–2025 de T se vio en este tramo).

| Canasta (USD 100 de riesgo) | Media/día | sd/día | t | Pasa | Cobra | EV/cuenta contraída | EV sin ventaja |
|---|---|---|---|---|---|---|---|
| T sola | $22 | $177 | 4,8 | 51 % | 20 % | +$425 | +$49 |
| SOM + Franklin + T | $48 | $484 | 3,8 | 31 % | 9 % | +$172 | +$28 |
| SOM + Franklin | $26 | $407 | 2,4 | 30 % | 8 % | +$127 | +$35 |

(DLL $600, consistencia 50 %, retiro máximo. Las demás configuraciones y los tamaños de USD 150 y 250 están en el JSON; el orden no cambia.)

## 3. Qué significa para las prop firms
- **La candidata más fuerte es T sola.** SOM y Franklin suben la media pero triplican el desvío diario: SOM sostiene varios días y Franklin
  tiene colas. Con un drawdown de $1.000 y DLL, eso mata cuentas.
- **Para usarlas** harían falta tamaño propio (menos micros), salida intradía o una cuenta aparte. Es diseño a medir, no a suponer.
- **Simplificación declarada:** el P&L de cada operación se acredita el día de entrada. Para SOM, que sostiene varios días, el drawdown EOD
  real puede ser distinto.
- **Nada de esto habilita dinero real** (decisión de Nico). El paso que falta es el forward con el e-proceso. T ya está en la cartera B en
  papel.

## 4. ORB de 5 min (ORB-A5 O1) en la cuenta (agregado 2026-11-18)
**Condiciones:** subconjunto operable (fricción de micro ≤ 0,08 R), NQ → MNQ, sólo sesiones DESC/REP de A5 (el holdout sigue sellado), con T
recortado a las mismas sesiones (2020–25).

| Canasta (USD 100 de riesgo) | t | Pasa | Cobra | EV/cuenta contraída | EV/mes contraído |
|---|---|---|---|---|---|
| ORB5 sola | 1,7 | 33 % | 9 % | +$128 | +$41 |
| T sola | 4,0 | 50 % | 19 % | +$399 | +$110 |
| T + ORB5 (corr. diaria 0,31) | 3,5 | 36 % | 11 % | +$205 | +$120 |

**Lectura:**
- **Por cuenta comprada, T sola sigue siendo la mejor.**
- **El ORB de 5 min es ruidoso dentro de la cuenta:** su objetivo de 10R deja muchas pérdidas chicas y pocas ganancias grandes, y con un
  drawdown de $1.000 eso pesa.
- **Una salida más cercana para la cuenta** sería una hipótesis nueva, con pre-registro propio. No se elige acá.

## 4. Agregado 2026-11-19: R (AtrPhase con stop 0,25 × ATR20) y la canasta T+R
R de fábrica con el stop de catástrofe de NETO-PISTAS (`neto_pistas_20261119/RZ_OPS.csv.gz`, bruto con el stop aplicado por MAE), 1 MNQ
(USD 100 de riesgo: el riesgo de R en NQ casi siempre supera 1 micro), 2020-01 → 2025-07, misma contracción declarada 0,5. Descriptivo.

| Canasta (USD 100) | Media/día | sd/día | t | Pasa | Cobra | EV/cuenta contraída | EV/mes contraída | EV sin ventaja |
|---|---|---|---|---|---|---|---|---|
| T sola | $22 | $177 | 4,8 | 51 % | 20 % | +$425 | +$113 | +$49 |
| R sola | $9 | $87 | 3,9 | 51 % | 16 % | +$142 | +$12 | −$21 |
| **T + R** | $31 | $218 | 5,5 | 48 % | 19 % | **+$440** | **+$143** | +$39 |

(DLL $600, consistencia 50 %, retiro máximo; resto en `CANASTA_SENALES_LUCID.json`.)
- R sola es lenta en la cuenta (≈ 3 operaciones por mes: tarda ≈ 250 días). Sumada a T casi no cambia el valor por cuenta pero lo cobra
  ≈ 25 % más rápido por mes, con t diario mayor (5,5 contra 4,8). La canasta T+R es la que vigila REGIMEN-FORWARD.
- Ejecutabilidad: T y R cierran dentro de la sesión (Lucid exige plano a las 16:45 ET y permite operar con noticias).

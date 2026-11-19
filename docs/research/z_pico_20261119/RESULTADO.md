# Z-PICO: el «pico» de fábrica en NQ es en parte selección, pero el mecanismo es una meseta en NQ desde 2018 y en Russell (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (1 prueba en `FUNDEDSYNC`). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `NQ_ES.json` (descriptivo, operaciones ya medidas), `RTY.json` y
`RTY_OPS.csv.gz` (RTY, sólo meses DESC; REP sellado). R neto con stop 0,25 × ATR20, 27 variantes (cubeta {10,15,30} × EMA {10,20,30} ×
eficiencia {35,45,55}); fábrica 15/20/45.

## 1. ¿El pico de fábrica en NQ es sobreajuste?
| NQ | Toda la ventana | Desde 2018 |
|---|---|---|
| Fábrica / mediana de la grilla | +0,145 / +0,030 | +0,289 / **+0,146** |
| Rango de la fábrica | 6.º de 27 | 5.º de 27 |
| Exceso sobre la mediana (IC 90 %) | +0,115 [+0,009; +0,189] | +0,142 [+0,028; +0,258] |
| «Mejor de 27 por azar»: exceso típico (p50 / p95) y p | +0,146 / +0,819; p 0,55 | +0,170 / +1,163; p 0,55 |
| Años con la fábrica sobre la mediana | 15/19 | 7/9 |
| Variantes positivas / PBO | 17/27 / 0,013 | 23/27 / 0,028 |
- **Parte selección:** el exceso de la fábrica es del tamaño de lo que daría quedarse con la mejor de 27 por azar (p 0,55): no se puede
  distinguir del ruido de selección. Sensible a dos perillas (cubeta 10: +0,03; EMA 10: −0,07).
- **Parte real:** queda sobre la mediana en las 4 épocas y en 15/19 años, el exceso es positivo con IC 90 %, y en la perilla de eficiencia es
  una cresta (35: +0,14; 55: +0,15), no un punto aislado. PBO bajo.
- **Estimación sin selección:** la mediana de la grilla. Desde 2018 en NQ, **+0,146 R/op con 23/27 positivas**; promedio de la grilla por mes
  +0,182 (IC 90 % [+0,085; +0,291], p 0,001), también en 2022+ (+0,169, p 0,014). Antes de 2018: −0,05.
- ES: sin pico (fábrica = mediana) y sin efecto claro (grilla 2018+ +0,049, p 0,24).

## 2. ¿Russell tiene el mismo pico? (DESC, datos desde 2017-07)
| RTY | Desde 2017-07 | Desde 2018 |
|---|---|---|
| Fábrica / mediana de la grilla | +0,140 / **+0,151** | +0,152 / **+0,165** |
| Rango de la fábrica | 15.º de 27 | 15.º de 27 |
| Exceso sobre la mediana (IC 90 %) | −0,011 [−0,068; +0,067] | −0,012 [−0,068; +0,070] |
| Variantes positivas / PBO | **26/27** / 0,48 | **26/27** / 0,58 |
| Promedio de la grilla por mes (IC 90 %, p ≤ 0) | — | +0,150 [−0,010; +0,313], p 0,061 |
- **Sin pico** (lectura pre-registrada: fábrica cerca de la mediana): en Russell la fábrica no se destaca; el PBO alto dice lo mismo (todas
  las variantes son parecidas: elegir no sirve).
- **Con meseta:** 26/27 variantes positivas y mediana +0,15–0,17 R/op, en un índice que el vendedor no usó. Por época: 2018–2021 +0,208 por
  mes (p 0,08), 2022–2025 +0,088 (p 0,23): más débil en lo reciente, con pocos meses DESC (26).

## 3. Lectura
- Que Russell funcione **pesa más** que el pico: el pico es un problema de *qué parámetros* (la fábrica sobrestima en ≈ +0,1 R lo que se puede
  esperar), mientras que Russell responde *si el mecanismo existe fuera de NQ*. Y la respuesta es una meseta, no un pico: el efecto está en
  la familia de parámetros, no en la fábrica.
- **Expectativa honesta de Z:** la mediana de la grilla, no la fábrica: ≈ +0,15 R/op en NQ desde 2018 (cerca de R: mediana +0,21, 81/81) y
  ≈ +0,15 en Russell (DESC, p 0,06). En ES no vive.
- **No queda confirmada:** la ventana 2018 se eligió mirando NQ, y Russell en DESC no alcanza p < 0,05. Su confirmación limpia es REP de RTY
  (sellado) con potencia K49, o el forward con una versión de Z pre-registrada como **grilla promediada** (o una variante central) en lugar de
  la fábrica.

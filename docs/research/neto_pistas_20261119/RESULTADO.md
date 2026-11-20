# NETO-PISTAS: R (AtrPhase) en R es un régimen robusto; Z es un pico del vendedor; A20 sólo vive desde 2017; el tamaño no confirma en Franklin ni SOM (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (con la enmienda de A20 antes de correrla). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `RZ_OPS.csv.gz`, `RZ_RESULTADO.json`, `RZ_PREFIJO.json`,
`TAMANO_RESULTADO.json`, `TAMANO_CURVAS.csv.gz`. Etapa EF3 (desarrollo ya mirado; nada de REP de A5 ni holdout).
Notas de procedencia: la grilla de R y Z corrió con el código anterior a la enmienda de A20 (la única diferencia para R/Z es una columna
`riesgo` que no usan); la primera corrida de A20 falló antes de calcular nada porque su grilla no había entrado en `GRILLAS`
(arreglado en un commit aparte) y se relanzó completa.

## A. R y Z en R (NQ decide; stop de catástrofe k × ATR20 de la sesión previa, aplicado con el MAE)
| | R (AtrPhase) | Z (ZetaTrend) |
|---|---|---|
| k elegido (mayor mediana de la grilla) | **0,25** (mediana +0,206; 0,5 → +0,101; 0,75 → +0,067; 1,0 → +0,048) | 0,25 (mediana +0,030) |
| Fábrica, R neto / bruto | **+0,269 / +0,364** | +0,145 / +0,227 |
| Variantes con neto > 0 | **81/81** (mediana +0,206) | 17/27 (mediana +0,030) |
| Vecinos a un paso | 8/8 positivos (mediana +0,214) | 4/6 (mediana +0,022) |
| PBO | 0,23 | 0,01 |
| Quiebre de la fábrica (sup-F) | 2017-05-17, p 0,056 (no significativo) | 2012-04-26, p 0,066 |
| Años positivos | 16/19 | 11/19 |
| ES, fábrica con el mismo k | +0,15 | −0,02 |
| Operaciones por mes | 3,1 | 2,3 |
| **Veredicto** | **REGIMEN_ROBUSTO** | **INTERMEDIO** (la fábrica rinde 5× la mediana de su grilla: ajuste del vendedor) |
- **R por año** (fábrica, R neto): 2008 +1,20 · 2009 −0,30 · 2010 +0,05 · 2011 +0,09 · 2012 +0,26 · 2013 +0,16 · 2014 −0,28 · 2015 +0,31 ·
  2016 −0,01 · 2017 +0,29 · 2018 +0,29 · 2019 +0,10 · 2020 +0,47 · 2021 +0,73 · 2022 +0,64 · 2023 +0,32 · 2024 +0,47 · 2025 +0,16 · 2026 +0,90.
  A diferencia de T, R no necesita un régimen: es positiva casi todos los años y crece desde 2020.
- **Advertencias:** k = 0,25 es el borde de la grilla (no se extiende después de mirar; la selección de k está contada); R opera ≈ 3 veces por
  mes (F-FRECUENCIA-MINIMA: no se lleva sola a forward, va en canasta con T); el stop se aplica con el MAE de velas de 1 minuto (K40).
- **Sin look-ahead:** prueba de prefijo (corte 2015-06-30) con operaciones idénticas en R (250), Z (166) y A20 (1.931).

## A2. A20 (stop duro propio)
- Ventana completa 2008–2026-09: **0/81** variantes con neto > 0 (mediana −0,117; fábrica −0,123, bruto +0,045), PBO 0,06 →
  **SOBREAJUSTE_PROBABLE** según la regla pre-registrada (ventana completa).
- Quiebre de la fábrica 2017-11-10 (p 0,003). **Descriptivo, no decisión:** desde el quiebre las 81/81 variantes son positivas (mediana
  +0,065; fábrica +0,084), y desde 2020 también 81/81 (mediana +0,084). Con el procedimiento exacto de T (ventana desde el quiebre) A20 sería
  una meseta; no se pre-registró así para A20 y queda como pista. Fricción mediana 0,13 R y años 2019–2021 negativos: es más frágil que T y R.

## B. Esquemas de tamaño para Franklin y SOM
- Franklin: el mejor en NQ+ES es S4 (∝1/√riesgo y saltear fricción > 0,08 R): neto +0,087 contra +0,004; en EMD+RTY +0,013 contra +0,035
  (también falla en RTY solo, con costo medido) → **no confirma**.
- SOM: el mejor es S3 (saltear fricción > 0,08 R): neto +0,029 contra −0,005 (curva neta paralela al bruto, +310 R); en EMD+RTY +0,004 de
  diferencia, dentro del ruido → **no confirma**.
- K52 (auditoría de Antigravity): S1, S2 y S4 pesan más los años recientes por el nivel de precio; S3 no tiene ese sesgo.

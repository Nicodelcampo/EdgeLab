# Z: la «variante rápida» no opera; el parámetro real es la severidad del filtro de día de tendencia, y la fábrica está en una meseta de 9 configuraciones equivalentes (2026-11-19)

Estado: RESULTADO — descriptivo sobre operaciones ya medidas (NQ/ES de NETO-PISTAS, RTY DESC de Z-PICO; no abre REP, holdout ni datos nuevos,
no cuenta pruebas). North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `RAPIDA_BATERIA.json`.

## 1. Error corregido: la «variante rápida» (cubeta 10, EMA 10) es degenerada
- Opera 4 veces en NQ en 18 años, 1 en ES y 1 en RTY DESC; EMA 10 con cubeta 15 ≈ 55 veces en NQ. La recomendación de la re-indagación
  («las perillas rápidas rinden más; usar la variante rápida central») salió de promedios marginales que incluían celdas casi vacías: queda
  **retirada** (corregido en `RE_INDAGACION_PISTAS_20261119.md` y en FACTORES).
- **Por qué:** Z califica un día si ninguna cubeta tocó la EMA de los cierres de cubeta en toda la sesión (más el umbral de eficiencia) y
  opera al día siguiente. EMA corta = sigue al precio = casi siempre tocada; cubeta chica = más cubetas = más chances de tocarla. Las dos
  perillas mueven una sola cosa: **qué tan estricto es el filtro de día de tendencia**.

## 2. Dosis-respuesta: más estricto → mejor el día siguiente
| Configuraciones (n NQ 2018+) | NQ 2018+ | NQ <2018 | ES 2018+ | RTY 2018+ (DESC) |
|---|---|---|---|---|
| muy estricta (cubeta 10 / EMA 20, ≈ 85 op.) | +0,07 a +0,09 | −0,01 a −0,04 | +0,16 a +0,17 | +0,30 a +0,36 (≈ 27 op.) |
| **moderada (9 configs, ≈ 210–240 op.)** | **+0,27 a +0,29** | ≈ 0 | +0,04 a +0,11 | **+0,13 a +0,22** |
| laxa (≈ 330–590 op.) | −0,01 a +0,16 | −0,13 a −0,17 | −0,05 a −0,01 | −0,01 a +0,08 |
- Spearman (n de operaciones, R) sobre las 18 variantes con ≥ 100 operaciones en NQ: NQ 2018+ −0,89, NQ <2018 −0,84, ES −0,74, RTY −0,63 (todas
  p ≤ 0,005). La relación se repite en los tres índices y en las dos épocas: es una regularidad del mecanismo, no un ajuste a NQ.
- **La fábrica no es un pico:** está en la banda moderada, donde tres combinaciones distintas de cubeta y EMA (10/30, 15/20, 30/10) × tres
  eficiencias dan el mismo número de operaciones y el mismo R. El «exceso sobre la grilla» de Z-PICO era la mediana tirada para abajo por las
  variantes laxas.

## 3. La banda moderada (las 9 configuraciones promediadas) — R neto con stop 0,25 × ATR20, promedio por mes con bootstrap
| | <2018 | 2018+ | 2022+ | Bruto <2018 → 2018+ | Fricción R mediana |
|---|---|---|---|---|---|
| NQ | +0,03 (p 0,40) | **+0,32 [+0,17; +0,47], p < 0,001** | +0,31 (p 0,0005) | +0,13 → +0,31 | 0,134 → 0,023 |
| ES | −0,08 | +0,09 (p 0,17) | +0,09 (p 0,20) | +0,09 → +0,14 | 0,179 → 0,061 |
| RTY (DESC) | — | **+0,24 [+0,06; +0,44], p 0,014** | +0,14 (p 0,17) | — → +0,22 | 0,044 |
- **Salvedad:** la banda se identificó mirando la tabla de los tres índices a la vez; el +0,24 de Russell no es una prueba limpia de la banda.
  Lo limpio es la dosis-respuesta en cada índice por separado.
- El bruto era positivo antes de 2018 en NQ y ES: lo que lo apagaba era la fricción relativa (mismo patrón que T, SOM y Franklin), y además el
  bruto subió.
- **Stop:** 0,25 × ATR20 es lo mejor en R (+0,28; 0,5 → +0,14; 1,0 → +0,07); es el borde de la grilla de stops, como en R.
- **Diversificación:** correlación diaria 2018+ con T −0,01 y con R 0,00. Canasta T+R Sharpe anual 2,11 → **T+R+Z (banda) 2,38**.

## 4. Lectura y siguiente paso
- Z es un mecanismo («después de un día de tendencia limpio, el día siguiente continúa») con dosis-respuesta en tres índices y una meseta
  de configuraciones equivalentes: el riesgo de sobreajuste de la fábrica es bajo. Expectativa honesta en NQ: la banda, ≈ +0,3 R/op desde
  2018 (≈ 2 operaciones por mes por configuración).
- **No confirmada:** todo esto es sobre desarrollo ya mirado (la ventana 2018 y la banda se vieron mirando). Confirmación limpia: REP de RTY
  (sellado) y forward de una versión pre-registrada «Z-banda» (las 9 configuraciones promediadas o la fábrica, que es su centro), sumada a la
  vigilancia como serie separada.

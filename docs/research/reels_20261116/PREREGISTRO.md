# Reels del 2026-11-16: revisit de viernes (Hougaard/AlphaZone), dos velas iguales (Olave), sesgo VWAP + Londres (Franklin) — pre-registro

Estado: PRE-REGISTRO — commiteado antes de correr. Pedido de Nico: «leelos y determiná qué vale la pena hacer». North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa del embudo **EF3** (regla exacta, sin grilla de parámetros).
Código: `edgelab/research/estrategias_scrapeadas.py` (`viernes_lunes`, `visitas_hougaard`, `dos_velas`, `franklin`), corrida
`tools/reels_20261116.py`, tests `tests/research/test_estrategias_scrapeadas.py`. Reels archivados en `docs/research/ideas_externas/reels/`.

## 0. Triage (qué se mide y qué no)
| Reel | Decisión | Por qué |
|---|---|---|
| Hougaard / AlphaZone «Friday Range Revisit – Monday Short» | **Se mide** | Regla completa (condición, entrada, stop, objetivo); barata en M1 2012–2026. El «24/25» es una tasa de visita, no de acierto: se mide aparte (E0). |
| Olave «dos velas iguales» | **Se mide** | Regla completa; stop estructural grande (palanca F-STOP-GRANDE-FRENTE-A-FRICCION). Antecedente en contra: ORB directo refutado en réplica (F-REELS-20261108). |
| Franklin «NY vs Londres y VWAP» | **Se mide** como sesgo a las 10:00 con stop en las dos velas de 15 min y como filtro de T | El reel no da entrada ni salida: se declara la forma más simple; salida al cierre por F-SALIDA-TECNICA-REGALA-LA-GANANCIA. |
| Myles «VP³» | **No se mide ahora** | Tolerancia de «misma zona», entrada y stop no definidos (cada uno es un grado de libertad que se elegiría mirando); objetivo menor que el stop (RR 0,75) con fricción; el volumen del CFD es de ticks (el perfil de volumen exige volumen real, sólo en futuros desde jul-2025); y los toques de niveles del proyecto se atraviesan más que se defienden (BigTrap2 ~96 %, F-HFT-CLUSTER-GRANDE-NO-DEFIENDE-D). Queda como posible generador del banco de eventos (confluencia de ≥ 2 niveles, sin retornos) si se levanta. |

## 1. Datos y tramos
M1 Dukascopy (`edgelab-sqx-m1`, copia local): USATECH → NQ, USA500 → ES, USA30 → YM; hora NY; hasta 2026-09-29 (antes del holdout).
**A = 2012-01-20 → 2019-12-31** (descubrimiento), **B = 2020-01-01 → 2026-09-29** (confirmación). Descriptivo: «reciente» 2025-08-05 → 2026-09-29.
Costos: fricción canónica del futuro (`embudo_runners.friccion`, base). R = (bruto − fricción) / riesgo.

## 2. Reglas (lo que el reel no dice se declara acá)
- **VIERNES_LUNES** (`vie_lun`): máximo RTH (09:30–16:00) del viernes < el del jueves; el lunes (día hábil siguiente, sin feriado) abre a las
  09:30 estrictamente dentro del rango RTH del viernes → venta a la apertura, objetivo el mínimo del viernes, stop el máximo del viernes,
  salida al cierre 16:00. (`mie_jue`): igual con miércoles < lunes y operación el jueves. Días con ≥ 380 velas RTH.
- **DOS_VELAS**: velas de 5 min de RTH; desde la de las 09:35, la primera pareja de velas seguidas del mismo color (un doji corta) → entrada
  al cierre de la segunda; stop en el mínimo (compra) / máximo (venta) desde las 09:00; objetivo 1:1; salida al cierre. Una por día.
  Celdas: hora límite de entrada `11h` (≤ 11:00) y `16h` (≤ 15:55).
- **FRANKLIN**: cierre de la vela 09:59 arriba del máximo de Londres (03:00–09:30 NY) y del VWAP de sesión (ancla 18:00, volumen de tick,
  precio típico) → compra; abajo del mínimo de Londres y del VWAP → venta; si no, nada. Entrada a ese cierre; stop en el extremo opuesto de
  09:30–10:00; celdas: salida al `cierre` o objetivo `2R`.
- **FRANKLIN_FILTRO_T**: operaciones de FUNDEDSYNC T (NQ, `cadena/FUNDEDSYNC_OPS.csv.gz`) con el sesgo calculado en su minuto de entrada.
  H: neto de las que van A FAVOR del sesgo > el resto.
- Simulación por velas M1 con el stop antes que el objetivo dentro de la vela (conservadora).

## 3. Decisión
- Por prueba (regla × celda × instrumento = 18 de P&L): pasa si R neto medio > 0 en A **y** en B, el p unilateral de B (bootstrap por
  sesión, 20.000) sobrevive **BH q 0,10 sobre las 18**, y la fricción mediana ≤ 0,08 R. Se publica todo: n, R, IC90, MDE, fricción, por tramo.
- Positivo sólo en B (A ≤ 0): «régimen reciente», pista, no pasa. Nulo sin potencia (MDE > 0,10 R): no mata.
- FRANKLIN_FILTRO_T: pasa si la diferencia (a favor − resto) es > 0 en A y en B con p_B < 0,10.
- **E0 Hougaard** (diagnóstico, sin P&L): tasa de visita del mínimo de referencia el día siguiente, con máximo menor vs no menor, por par de
  días de la semana y con apertura dentro / fuera del rango. Contrasta el «24/25» con la tasa base de todos los pares.
- Lo que pase va a la apertura del holdout de su familia (oct–nov, USATECH sellado / futuros) con la regla congelada; nada se ajusta acá.

## 4. Justificación económica
Revisit: un máximo menor marca agotamiento comprador y el mínimo de referencia junta stops que atraen al precio. Dos velas: el impulso de
los primeros minutos de NY persiste (momentum intradía de apertura). Franklin: aceptación de NY por encima/debajo de Londres y del precio
medio ponderado es un sesgo de dirección del día.

## 5. Cómo podría refutarse
R neto ≤ 0 en alguno de los tramos, o sin nominadas por BH con MDE ≤ 0,10 R; E0: la tasa de visita con máximo menor no supera a la tasa
base del día siguiente (el 24/25 sería la tasa base de un mínimo cercano, no la condición).

## 6. Multiplicidad y linaje
Registro global `reels_20261116/<familia>`: VIERNES_LUNES 6, DOS_VELAS 6, FRANKLIN 6 + 1 (filtro T) = **19**. Linajes: VIERNES_LUNES ←
M1_INTRADIA (ruptura del extremo del día previo, F-GAP-Y-RUPTURA-PREVIO-M1); DOS_VELAS ← ORB_EMA20, M1_INTRADIA (momentum de apertura);
FRANKLIN ← EMA_VWAP, LONDRES_IMPULSO_NQ, FUNDEDSYNC.

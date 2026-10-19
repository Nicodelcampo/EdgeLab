# EMA-SEP — operar en contra cuando las 3 EMAs están muy separadas — MANIFIESTO (STOP: espera OK de Nico)

Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`. Búsqueda sobre P&L. Familia
`EMASEP`, distinta de EMAALIGN (que fue a favor y en 2t): no hereda resultados.

## Separación ("las 3 muy separadas")
- EMA 200/500/2000 sobre barras de **10t**, alineadas en orden estricto.
- `sep = min(|EMA200 − EMA500|, |EMA500 − EMA2000|)`: la **menor** de las dos distancias. Así, que dos estén lejos y
  la tercera cerca no cuenta.
- Para que el umbral signifique lo mismo en MNQ y en MGC y en cualquier horario, `sep` se compara con su propio pasado:
  percentil de `sep` en las 20 sesiones previas, misma franja de 30 min (causal).
- **Umbrales:** percentil 90, 95 y 99.
- **Señal:** la primera barra en que `sep` cruza el umbral con las EMAs alineadas. Dirección = **contraria** a la
  alineación. Se rearma cuando `sep` vuelve por debajo del umbral.

## Entradas (3)
- A: a mercado en la barra siguiente.
- B: límite 10 ticks más extremo (esperar que estire un poco más). Se cancela a las 50 barras.
- C: confirmación: primera barra que cierra en contra de la tendencia (dentro de 50 barras), y entrada a mercado en
  la siguiente.

## Salidas
SL ∈ {20, 40, 80} ticks × TP = R × SL con R ∈ {1, 2, 4} × BE ∈ {no, en +1R}. Cierre a fin de sesión.
Una posición a la vez.

## Grilla y corrección
3 umbrales × 3 entradas × 18 salidas = 162 celdas por instrumento, **324 en total**.
- max-T contra el **mismo trade con la dirección al azar** (mismos momentos y fills), 2.000 sorteos.
- Pasa si p max-T ≤ 0,05 **y** el neto es > 0.

## Datos
- MNQ y MGC.
- Descubrimiento: MNQ 09-25 → 06-26 y MGC 12-25 → 06-26.
- Confirmación (sin tocar para estas familias): MNQ 09-26 y 12-26, MGC 08-26 y 12-26. Corre una sola vez, con Holm.
- Holdout ≥ 2026-10-01: no se abre.
- Costos: USD 1,90 por ida y vuelta + 1 tick por lado.

## Justificación económica
Una separación extrema de las tres medias indica un movimiento estirado en todas las escalas a la vez. Si los
participantes toman ganancia o el movimiento se agota, el precio revierte hacia las medias. En ES vimos reversión suave
a 3 h.

## Cómo podría refutarse
- Neto ≤ 0, o no mejor que la dirección al azar (MDE publicado).
- Ganancia concentrada en una celda, un mes o pocos días.
- **Antecedente en contra:** en 2t, el pullback a la EMA siguió de largo. Eso es compatible con la reversión, pero en
  otra escala.

## Riesgos
- Con el percentil 99 puede haber pocos trades por celda.
- MNQ ya fue muy usado (no para esta señal).
- 324 celdas: la corrección es dura y hace falta un efecto grande.

## Enmienda 1 (pedido de Nico, antes de correr): filtro de agotamiento + OK
"agregale también filtrar entradas según si muestran agotamiento o no. y lanzalo" = **OK**.
- **Filtro (3 niveles), evaluado en la barra de la señal y sólo con el pasado:**
  - `ninguno`.
  - `desaceleracion`: el avance de las últimas 20 barras a favor de la tendencia es menor que el de las 20 anteriores.
  - `climax_vol`: las últimas 20 barras se formaron en menos de la mitad de su tiempo típico (mediana de las 200
    previas). En barras de ticks el volumen por barra es casi constante (medido: p99 de la razón = 1,28), así que el
    clímax se mide como **velocidad**.
- **Grilla:** 3 umbrales × 3 filtros × 3 entradas × 18 salidas × 2 instrumentos = **972 celdas**, max-T.
- **Técnica:** cada señal es un trade independiente (se elimina "una posición a la vez"): la regla dependía de la
  duración de cada trade y rompía el nulo de dirección al azar. Celdas con n < 30 no se evalúan.

## Enmienda 2 — EMASEP-MGC150 (pedido de Nico, 2026-10-07, después de ver el resultado en 10t)
"probala sólo en el MGC en una escala más alta; si ya tenés velas > 100t usá esa". Se usa **150t**, la escala que ya
se usó para MGC en VTD-BRACKET.
- **Es una prueba nueva, con su propio max-T.** Se declara que se eligió después de ver 10t (en MGC hubo celdas
  positivas que no pasaron). Esto se pondera en la lectura: la elección de instrumento y escala no es ciega.
- Misma definición (EMAs 200/500/2000 en 150t, percentil causal, filtros, entradas A/B/C).
- **SL ∈ {40, 80, 160} ticks** (escalado a la barra mayor), R ∈ {1, 2, 4}, BE ∈ {no, sí}. Límite B: +10 ticks.
- **486 celdas**, sólo MGC, contra el mismo nulo.
- Confirmación: MGC 08-26 y 12-26, una vez, con Holm.
- Contador de la familia EMASEP: 972 + 486.

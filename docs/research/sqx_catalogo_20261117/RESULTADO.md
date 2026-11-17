# Catálogo de SQX: resultado de la medición (v2, 2026-11-17)

Estado: CERRADO — pre-registro `PREREGISTRO_MEDICION.md` (con enmienda 1). North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Datos: `RESULTADO.json` (136 pruebas), operaciones en `ops/`. Corrida v1 descartada (`RESULTADO_V1_DESCARTADA.json`, ver enmienda 1).

## Veredicto
**Ninguna de las 136 pruebas pasa y BH (q 0,10 sobre 136) no nomina ninguna.** El mejor p de B es 0,002 y hacía falta ≤ 0,0007; el bootstrap
tiene 20.000 réplicas, así que el criterio podía nominar. Nada del catálogo entra a la cartera.

## Por estrategia (R neto por operación; A = 2012–2019, B = 2020 → 2026-09-29)
| Estrategia | Lectura | Estado |
|---|---|---|
| COT1/COT2/COT3 | 2–18 operaciones por instrumento en B (≈ 1 por año): los umbrales de la ficha casi no disparan. Signos mezclados. | **SIN_POTENCIA** (no refutada: no hay N) |
| VP POC USDJPY | original A +0,08 / B +0,07 (p 0,16), 10/17 años; con cierre del viernes ≈ 0 | sin efecto detectable |
| Turtles 55/20 | **oro con cierre del viernes: A +0,08 (p 0,19), B +0,33 (p 0,002), 13/16 años, fricción 0,016 R**; resto ≈ 0 o negativo | pista (oro), resto no |
| Turtles 20/10 | oro: A +0,05…+0,21, B +0,15…+0,43 (p 0,03–0,10); CL, 6E, 6J ≈ 0 | pista (oro) |
| Range breakout 13:00 | 6E −0,23, CL −0,05 en B; fricción mediana 0,11 / 0,10 R (> 0,08) | **refutada** (y no operable por fricción) |
| ADX + trailing | 6J con cierre del viernes A +0,05 / B +0,08 (p 0,11); resto ≈ 0 | sin efecto detectable |
| Mean reversion A/B | 4–22 operaciones por tramo | SIN_POTENCIA |
| Inside bar H4 | neto −0,01…−0,10 en B; bruto +0,02…+0,12; fricción 0,083 R (stop en el piso de 12 × fricción) | **refutada como regla neta**: el stop es chico frente al costo |
| Buy dips (RSI 5) | **ES original: A +0,28 (p 0,003), B +0,31 (p 0,002), 11/14 años; NQ A +0,26, B +0,13**; con cierre del viernes cae a +0,09 / +0,02 | pista, pero el efecto vive en el fin de semana |
| Price dip −5 % | 2–9 operaciones por tramo | SIN_POTENCIA |
| Double 7 (Connors) | **NQ original A +0,22 (p 0,002), B +0,12 (p 0,055), 12/14 años**; ES +0,19 / +0,08; YM B +0,13 (p 0,03); viernes, más débil | pista (índices) |

## Lo que enseña
1. **Fricción y stop chico** (observación de Nico): inside bar y rango 13:00 mueren por costo. El bruto del inside bar es positivo en B en
   3 de 4 instrumentos, pero el stop (media vela interna en H4) deja la fricción en 0,08–0,11 R. Una variante con stop más ancho es otra hipótesis.
2. **Sesgo del motor** (enmienda 1): con OHLC, el stop en la barra de entrada de las órdenes stop sacaba el 17–41 % de las operaciones. Con el
   orden del M1, inside bar pasa de −0,42 a −0,05 R y rango 13:00 de −0,35 a −0,23 (6E). No cambió ningún veredicto, pero sí la lectura de por qué.
3. **Reversión corta en índices (Connors)** es lo único del catálogo con signo estable en A y B, como en la literatura, pero:
   (a) no sobrevive a las 136 pruebas; (b) en buy dips la ventaja depende de quedar abierta el fin de semana, que Nico no quiere;
   (c) son 5–12 operaciones por año por índice.
4. **Turtles en oro con cierre del viernes** es la otra pista: B fuerte, A débil (régimen del oro 2020–2026). Igual que en 3, no hay
   confirmación posible sin datos no mirados.

## Qué sigue (no se ejecuta acá)
- Las dos pistas (Connors en índices sin fin de semana; Turtles en oro con cierre del viernes) se confirman sólo con datos no mirados: el
  forward. Pre-registro nuevo, una hipótesis por familia, en cuanto haya forward.
- COT: con estos umbrales no hay N. Bajarlos sería otra hipótesis, y hoy no hay razón económica para hacerlo.
- Pendientes de la sección E del INDICE (Turnaround Tuesday y Tight 5D Range Breakout): requieren una tanda aparte.
- Spreads estimados (6J, ZB, CL, ZN, HG, NKD): ningún veredicto depende de ellos (las candidatas cerca del umbral son de índices/oro, con
  spread medido).

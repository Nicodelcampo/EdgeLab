# Catálogo de SQX: medición de las 10 candidatas (pre-registro, 2026-11-17)

Estado: PRE-REGISTRO — commiteado antes de correr. Pedido de Nico: «metí todas, incluso las del finde o las de 6J sin costos (buscá una estimación
en Internet)». Fichas: `INDICE.md` y `01…10_*.md` (Antigravity). North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Etapa EF3 (reglas del catálogo, sin optimizar). Código: `edgelab/research/sqx_catalogo.py` (motor de barras común + reglas; tests de causalidad
por prefijo y de stop/hueco), corrida `tools/sqx_catalogo_medir.py`.

## Universo (decidido antes de mirar)
- **Sólo lo operable en las cuentas** (Topstep y similares: CME/NYMEX/COMEX/CBOT; fuente: help.topstep.com «When and What Products Can I Trade?»).
  DAX, FTSE y EuroStoxx (Eurex/ICE) **quedan fuera** aunque las fichas los propongan; ZN fuera (sin datos). NKD no lo pide ninguna ficha.
- Datos: M1 Dukascopy con zona declarada → ES, NQ, YM, RTY (2019+), GC, 6E, 6J (USDJPY, señal y costo convertidos), CL (petróleo CFD); barras D1
  de SQX → HG, ZB (2019+), 6B. COT: reporte Legacy de la CFTC (API `publicreporting.cftc.gov`, 2005 → 2026-11), en `datos/COT_LEGACY_CFTC.csv.gz`;
  índice 0..1 de no comerciales/comerciales en 52 y 156 semanas, usable desde el lunes siguiente a la publicación del viernes. Para 6J operado
  como USDJPY el índice del yen se invierte (largo yen = corto USDJPY).
- **Costos**: `edgelab/costos.py`. Spreads **estimados por Internet** (no medidos, marcados en `costos_canonicos.json`): 1 tick en 6J, ZB, CL y
  ZN; 2 en HG y NKD; comisión de Topstep publicada. Fricción RT resultante: 6J 3,8 ticks, ZB 3,1, CL 3,4, HG 4,4.

## Reglas (fichas, tal cual; lo que la ficha deja abierto se fija acá)
| Estrategia | TF | Instrumentos | Fijado acá |
|---|---|---|---|
| COT1 crowding unwind + ATR + SMA20 | D1 | GC CL HG ZB 6E 6J | SL 2 ATR14, TP 4 ATR14 (capa 3 de la ficha) |
| COT2 spread hedger−spec + ROC4 + ruptura 20 | D1 | CL GC HG 6E | ídem |
| COT3 tendencia sana + retroceso | D1 | 6E 6B 6J CL GC | ídem |
| VP POC USDJPY (largo) | H1 | 6J (USDJPY) | POC del día previo, 150 niveles, volumen de tick; SL 100 / TP 200 pips |
| Turtles 55/20 (+EMA20>EMA350, ATR10<ATR200) | D1 | GC CL 6E 6J ZB | simétrico (cortos espejo, como dice la ficha); EMA del propio instrumento |
| Turtles 20/10 (+EMA) | D1 | ídem | ídem |
| Range breakout 13:00 servidor | M15 | 6E CL | OCO ±10 pips del máx/mín de 50 cierres, SL = TP = mayor rango de vela de 50, BE 20 pips, vigencia 90 |
| ADX(+DI) + trailing al mínimo de 25 | H4 | GC CL 6E 6J | pips → ATR (ficha): SL 2 ATR14, BE 1,5 ATR, trailing −0,25 ATR; simétrico con −DI |
| Mean reversion A (pánico ATR5, límite) | D1 | ES NQ YM RTY GC ZB 6E | stop protector 3 ATR14 (ficha); objetivo 10 %; 4 velas |
| Mean reversion B (MeanRev ±3 %) | D1 | ídem | stop 3 ATR14; 5 velas |
| Inside bar OCO | H4 | GC CL 6E 6J | offset 0,15 ATR14; SL 0,5 rango con piso 12 × fricción; TP 2 rangos; BE apagado |
| Buy dips (RSI5, límite) | D1 | ES NQ YM RTY GC ZB | stop 3 ATR14; 20 velas |
| Price dip −5 % (filtro S&P en índices) | D1 | ídem | stop 3 ATR14; 10 velas |
| Double 7 (Connors) | D1 | ídem | stop 3 ATR14 |
Cada una en dos variantes: **original** (puede quedar abierta el fin de semana) y **viernes** (cierra al cierre del viernes; lo que entra el
viernes también). **136 pruebas** (68 × 2).

## Motor y decisión
Barras en hora de NY (sesión desde las 18:00); señal al cierre de la barra, orden desde la siguiente; stop antes que objetivo dentro de la barra;
hueco más allá del stop/objetivo → apertura; R = (puntos − fricción) / riesgo inicial. A = 2012–2019, B = 2020 → 2026-09-29 (lo que empieza en
2019 decide B). **Pasa** si R neto > 0 en A (si A evaluable) y en B, p de B (bootstrap por sesión) sobrevive **BH q 0,10 sobre las 136** y
fricción mediana ≤ 0,08 R. Se informan años positivos, ventana reciente y régimen reciente (B > 0 con A ≤ 0). Lo que pase va a holdout/forward
con su acta; nada se ajusta acá.

## Justificación económica / cómo podría refutarse
COT: el posicionamiento extremo de especuladores tiende a desarmarse y el de coberturistas anticipa giros (literatura mixta). Turtles/ADX:
tendencia en commodities y FX (prima de momentum de series de tiempo). Reversión diaria (MR, dips, Double 7): reversión de corto plazo en
índices sobre tendencia (Connors). Rango/inside bar: ruptura de compresión. Se refuta con R ≤ 0 o sin nominadas por BH.

## Contador y linaje
`sqx_catalogo_20261117/CATALOGO`: 136. Linaje SQX_CATALOGO (sin padre medido; las de índices diarios no repiten ninguna regla probada).

## Enmienda 1 (2026-11-17, después de la primera corrida): orden dentro de la barra por M1
**Qué pasó.** La corrida v1 (commit `7523a967`) no dejó ninguna nominada. Al revisarla apareció un sesgo **pesimista** del motor: en las
órdenes stop la barra de entrada abre del otro lado del precio de entrada, y su mínimo (o máximo) suele ocurrir **antes** del llenado; el motor
lo contaba como posterior. Salidas por stop en la propia barra de entrada: INSIDE_BAR 28–41 % (H4), RANGE_1300 17–20 % (M15), ≤ 3 % en el resto.
Lo mismo, en menor medida, con stop y objetivo dentro de una misma barra (siempre stop primero).
**Cambio.** Donde hay M1 (todo salvo HG, ZB y 6B, que vienen en D1 de SQX), el motor resuelve con el M1 de la barra: el minuto de llenado, y
stop/objetivo minuto a minuto después (dentro del minuto de llenado y de cualquier minuto ambiguo sigue asumiendo lo peor). Test:
`test_m1_resuelve_vela_de_entrada_y_ambiguedad`. **No cambia ninguna regla, parámetro, instrumento ni el criterio de decisión**; se aplica a las
136 pruebas por igual. La v1 queda como descartada (`RESULTADO_V1_DESCARTADA.json`, `ops_v1_descartada/`) y se relanza todo.
**Honestidad sobre el disparador.** La corrección se encontró mirando resultados de la v1; por eso se aplica sin excepción a todo, se informan
v1 y v2 lado a lado, y lo que pase en v2 sólo por este cambio se señala como tal en el resultado.

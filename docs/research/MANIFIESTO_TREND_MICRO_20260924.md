# Manifiesto: tendencia con filtro de microestructura (familia TREND-MICRO), ES · MES · NQ, 2026-09-24

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** PROPUESTO. Es una búsqueda sobre P&L: **STOP, necesita el OK de Nico.**
**Ledger:** `artifacts/hippocampus/trend_micro_20260924.jsonl` (familia nueva). **Registro de parámetros compartido** con TBZ-E2 (filtros, perfil de volumen, salidas): `docs/specs/TBZ_E2_PARAM_REGISTRY.json`.

## 1. Idea (Nico, 24/09)

La microestructura (fills, libro, absorción) no paga como fuente de ganancia (MM-QI, EXEC-QI). Puede servir como **disparador o filtro de movimientos tendenciales con RR alto**, donde el costo de entrada pesa poco frente al movimiento.

**Hipótesis:** una señal base tendencial gana en esperanza neta cuando la acompaña la firma de microestructura de una **ruptura con combustible**: la absorción en el nivel **cede** y le sigue una **cascada de agresivos**, que es la firma de stops disparados (Osler 2005).

**Justificación económica:** los stops se acumulan detrás de niveles visibles (extremos, números redondos, bordes de expansión). Cuando la pared que los protegía (absorción) cede, la ejecución forzada de esos stops es demanda o oferta **no informada, pero inevitable**, que empuja el precio. Es flujo predecible en un horizonte de minutos, no de ticks.

**Cómo podría refutarse:** la señal base con filtro no supera a la señal base sin filtro, ni al nulo de ruina del jugador, en esperanza neta con entrada agresiva. O lo hace sólo en exploración.

## 2. Estructura: base × filtro, con la base medida sola también (sinergia)

**Señales base** (3, cada una con su registro):
- **B1:** ruptura del máximo o mínimo de la sesión o de la sesión previa.
- **B2:** ruptura de un número redondo, con la regla de transporte de V-RND: ES 25 pts, NQ 100 pts.
- **B3:** continuación de TBZ-EXP: nueva expansión en la dirección de la anterior, con los parámetros por defecto de G1.

**Filtros de microestructura** (sólo con trades; agresor por regla de cotización sobre bid/ask de `research-v2`):
- **F0:** ninguno (la base sola, que es la referencia).
- **F1:** hubo absorción causal en el nivel en los 5 min previos **y cedió** (el precio lo cruzó).
- **F2:** F1 más una cascada: volumen agresivo en la dirección de la ruptura en los 10 s siguientes ≥ p90 causal.
- **F3:** filtro de tendencia general: lado de VWAP y EMA50 de 1 min alineado.

**Operación** (la misma para todo; parámetros de G6 en el registro):
- entrada **agresiva** al precio contrario 250 ms después de la señal;
- stop estructural: del otro lado del nivel roto + 0,5σ causal de 5 min;
- target en **2R y 4R**;
- tiempo máximo de 60 min;
- costo: spread observado + comisión.

**Celdas primarias:** 3 bases × 4 filtros × 2 targets = **24 por instrumento**. ES y MES cuentan como uno por fecha, así que son 48 celdas en total con NQ.

## 3. Estimandos y nulos

- **Primario:** esperanza neta en R por operación, con IC por sesión.
- **Sinergia:** E(base + filtro) − E(base sola) sobre las **mismas** señales. Es la diferencia de medias con y sin filtro, no dos poblaciones distintas.
- **Nulos:**
  - **N1, ruina del jugador:** con stop s y target 2R/4R, P(target antes del stop) = 1/3 y 1/5 sin deriva.
  - **N3, otra sesión a la misma hora:** con la guardia de controles.

Nada se promueve si no le gana a N1 **en neto**.

## 4. Datos, particiones y potencia

- **ES y MES:** `P-TBZ-EXP` (jul-2025 a mar-2026, ~417 sesiones) para explorar y `P-TBZ-CONF` (abr–jun) reservada. Mismo subyacente: la potencia se cuenta por fecha, ~180 fechas de exploración.
- **NQ:** particiones nuevas `P-TMIC-NQ-EXP` (jul-2025 a mar-2026) y `P-TMIC-NQ-CONF` (abr–jun 2026). Se declaran **antes** de medir y salen de `research-v2`.
- **Holdout de ticks:** intacto. El **24/09** queda excluido.
- **Potencia:** con RR alto la varianza es grande. Con 2R, un edge de +0,1R por operación necesita ~800 operaciones para un IC de ±0,07R. Se publica el MDE por celda, y las celdas con menos de 200 operaciones se reportan como sin potencia.
- **Validación previa, target-free:** en ES/MES/NQ de jul–ago, comparar el agresor por regla de cotización de `research-v2` contra el agresor del L2 validado. Si el acuerdo es menor al 90 %, F1 y F2 no se corren.

## 5. Regla de sugerencia

Una celda es SUGERENCIA si cumple todo esto:
- pasa BH-FDR q = 0,10 sobre las 48 celdas;
- esperanza neta con IC > 0;
- supera a N1;
- la sinergia con su base sola es > 0 con IC;
- es positiva en ≥ 55 % de los meses.

A lo sumo 3 pasan a `*-CONF`, con una spec en revisión ciega y una campaña.

## 6. Riesgos

- **Multiplicidad:** 48 celdas más las sensibilidades. Se controla con FDR, el tope de 3 y la reserva intacta.
- **Agresor inferido:** hay que validarlo antes (§4).
- **Solapamiento con TBZ-E2 y ABS-CTX:** B3 usa las franjas de TBZ y F1 usa el detector de ABS-CTX. **No se transportan resultados**: cada familia lleva su ledger. Los tres comparten herramientas y el registro de parámetros.
- **Costo real de entradas agresivas en ruptura:** puede haber más slippage que el spread observado. Sensibilidad: +1 tick por lado.

## 7. Iteración 1 (24/09, antes de medir; manda sobre §2–§6 donde choquen)

**T1. Validación del agresor en otra ventana.** `research-v2` fue re-cortado en el 01/07 (holdout), así que **no tiene julio ni agosto**. El único solapamiento pre-holdout con el L2 es NQ 09-26 del 25 al 30/06 y ES 09-26 del 29 y 30/06.
- **Qué se valida ahí** (target-free): la columna `aggressor` de `research-v2` contra el agresor por cotización del L2, trade por trade, emparejando con un desfase de reloj que se detecta automáticamente (el L2 guarda la hora de pared ART como UTC).
- **Umbral:** acuerdo ≥ 90 %. Si no se alcanza, F1 y F2 no se corren.

**T2. B3 corregido.** t_avail es el **fin** de una expansión, no una ruptura.
- **B3 = vela en la que se dispara una expansión nueva** (el estado se crea al cierre de la vela j, causal), en la misma dirección que la franja anterior todavía viva (≤ 240 min).
- **Cambio de código:** `expansion_bands` expone `t_trigger`. Es un campo nuevo; no cambia los que ya existen.

**T3. Una señal por nivel y sesión.**
- **B1:** primera ruptura del máximo o mínimo de la sesión en curso, y primera ruptura del máximo o mínimo de la sesión previa.
- **B2:** primera ruptura de cada número redondo en la sesión.
- **B3:** una por disparo.

**T4. Ejecución.**
- Una posición a la vez por celda.
- **Entrada:** agresiva en el primer trade posterior a señal + 250 ms.
- **Stop:** nivel roto − 0,5σ₅ (para compras); a mercado en el primer trade posterior a tocarlo.
- **Target:** límite que se llena sólo si el precio lo atraviesa por 1 t.
- **Salida por tiempo:** 60 min.
- **σ₅:** mediana causal de |Δ5 min| en las 3.000 velas de 1 min previas.
- **Comisión por lado:** ES 0,2 t y NQ 0,5 t.

**T5. Instrumentos:** **ES y NQ** son los primarios. MES sale porque es redundante con ES. Siguen siendo 24 celdas por instrumento, **48 en total**.

**T6. Sesiones:** salen de los manifiestos de los bundles de 25 ticks (ES: 313 sesiones hasta el 30/06; NQ: 279 hasta el 18/06). Con contratos solapados, se toma el de más ticks. Particiones:
- **ES:** `P-TBZ-EXP` y `P-TBZ-CONF`, ya declaradas.
- **NQ:** `P-TMIC-NQ-EXP` (hasta el 31/03) y `P-TMIC-NQ-CONF` (01/04–18/06), que se declaran antes de medir.

**T7. F2 (cascada).** p90 del volumen agresivo en ventanas de 10 s, calculado sobre la **sesión previa** (causal).

**T8. Recursos:** sesión por sesión y por row group. Como máximo 2 procesos.

## 8. Resultado (25/09, madrugada): ninguna sugerencia; dos hallazgos para registrar

Reporte `artifacts/trend_micro/report.json` (sha `eac81f53e90b…`). Ledger `artifacts/hippocampus/trend_micro_20260924.jsonl`. Exploración hasta el 31/03/2026: ES en 176–178 sesiones y NQ en 158–169. Unidad: la señal, R neto con costo. IC bootstrap por sesión.

**Veredicto por la regla fija (§5): 0 sugerencias.** 26 celdas con muestra; 18 pasan el FDR, todas por ser **negativas**.

| Instrumento | Base | Filtro | Target | n | R neto | Acierto vs N1 (ruina del jugador) | Lectura |
|---|---|---|---|---:|---|---|---|
| ES | B1 (PDH/PDL, ONH/ONL) | F0 | 2R | 364 | −0,31 [−0,44; −0,15] | 0,261 vs 0,276 | camino aleatorio menos costos |
| ES | B2 (número redondo) | F0 | 2R | 578 | −0,25 [−0,36; −0,13] | 0,280 vs 0,272 | ídem |
| ES | B3 (disparo de expansión) | F0 | 2R | 12.003 | −0,15 [−0,18; −0,11] | **0,278 vs 0,312** | **peor que el camino aleatorio** |
| NQ | B3 | F0 | 2R | 1.984 | −0,11 [−0,18; −0,04] | **0,265 vs 0,326** | **peor que el camino aleatorio** |
| NQ | B2 | **F3** (VWAP y EMA50 a favor) | 2R | 347 | +0,08 [−0,09; +0,22] | **0,386 vs 0,299** | pista (no pasa la regla) |

**Hallazgo 1: la continuación de una expansión falla más que el azar (ES y NQ).**
- Cuando se dispara una expansión nueva en la misma dirección que la anterior, el precio llega al target **menos** de lo que da un camino aleatorio con las mismas distancias: −3,4 pts en ES, con IC [−4,5; −2,2] y 12.003 señales, y −6,2 pts en NQ, con IC [−8,8; −3,6].
- Es un sesgo de **reversión después de desplazamientos sostenidos**. Es coherente con la VR < 1 medida en HP-008 y apunta en la misma dirección que la hipótesis de patinaje hacia A de TBZ-E2, aunque es otro objeto: no se transporta, se anota.
- No es operable tal cual: invertir la señal paga los costos al revés, y la pérdida de B3 es −0,11 a −0,15 R.

**Hallazgo 2 (pista, no sugerencia): en NQ, la ruptura de un número redondo a favor de VWAP y EMA50 mejora sobre su base.**
- Acierto +8,6 pts sobre N1, con IC [+3,5; +13,5].
- Sinergia contra la base sola +0,22 R, con IC [+0,09; +0,37].
- **Pero** el R neto tiene IC [−0,09; +0,22], no pasa el FDR y los meses positivos son el 50 %, por debajo del 55 %. Por la regla fija no es sugerencia.
- Encaja con V-RND (absorción en número redondo → ruptura, NQ) y con el mecanismo de stops de Osler, pero sale de 347 señales en una exploración de 26 celdas.
- Si se quiere seguir, necesita su propio pre-registro con una celda sola.

**F1 y F2 (absorción que cede, cascada):** no hay muestra. En NQ hay 6 a 34 señales por celda: la absorción causal a ±2 ticks del nivel en los 5 min previos es rara. En ES no se corrieron (P-93). **No se descartan: no hubo potencia.** B2 F1 en NQ va en la dirección esperada (acierto 0,41 contra 0,31, n = 34), sin potencia.

**Alcance de la muerte:** las rupturas B1, B2 y B3 con entrada agresiva y stop estructural, en ES y NQ entre jul-2025 y mar-2026, no tienen esperanza neta positiva. No muere la microestructura como filtro: F1 y F2 no tuvieron muestra.

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

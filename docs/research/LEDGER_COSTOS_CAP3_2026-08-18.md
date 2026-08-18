# Ledger de costos — capítulo 3 (v0, 2026-08-18)

- **Estado:** `DRAFT_PENDIENTE_DE_CONFIRMACIONES_DE_NICO` — ver §5.
- **Qué es:** el capítulo 3 del orden sellado (`0 ledgers → 3 costos → 5 población
  + 2 N_eff → 1 F4 → …`). Es el insumo de la **validez económica** (ítem 1 de la
  jerarquía del referente: expectativa NETA con costos desglosados; gate G3).
- **Referente:** `docs/NORTH_STAR.md` sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
- **Procedencia:** tabla de comisiones del broker (LucidFlex) en dos capturas del
  18-ago-2026, aportadas por Nico · especificaciones de instrumento desde la
  fuente única del repo `edgelab/instruments.py` (blob
  `30ea647e38bc266c52ec7229765c31d59e894566`) — nada re-declarado a mano.
- **Firewall:** sin outcomes · sin P&L de mercado · holdout intacto. Esto es
  contabilidad de costos: no mide mercado. (El spread de 6E que se cita ya está
  publicado en `docs/PLAN_RUTA_A_UNA_CUENTA_2026-08-18.md`; no se re-mide acá.)

## 1. La fórmula

```
costo_comisión_RT_ticks = comisión_por_lado_USD × 2 / tick_value_USD
```

Round-trip = dos lados. En ticks, porque las mediciones de la línea viven en
ticks enteros (regla del manifiesto H-Z2A §5).

## 2. Comisión por instrumento (los 11 del `CME_UNIVERSE`)

| Instrumento | Comisión por lado (USD) | tick_value (USD) | **Comisión RT en ticks** | Estado |
|---|---|---|---|---|
| 6E | 2,40 | 6,25 | **0,768** | tabulada (captura) |
| 6B | 2,40 | 6,25 | **0,768** | tabulada (captura) |
| 6J | 2,40 | 6,25 | **0,768** | tabulada (captura) |
| ES | 1,75 | 12,50 | **0,280** | tabulada (captura) |
| NQ | 1,75 | 5,00 | **0,700** | tabulada (captura) |
| YM | 1,75 | 5,00 | **0,700** | tabulada (captura) |
| GC | 2,30 | 10,00 | **0,460** | tabulada (captura) |
| MES | 0,50 | 1,25 | **0,800** | tabulada (captura) |
| MNQ | 0,50 | 0,50 | **2,000** | tabulada (captura) |
| **ZB** | — | 31,25 | — | **PENDIENTE — no está en las capturas** |
| **MBT** | — | 0,50 | — | **PENDIENTE — no está en las capturas** |

**Consistencia:** 6E ⇒ 0,768 y ES ⇒ 0,280 coinciden con lo tabulado en la entrada
009 del canal — la fuente tabulada era esta misma tabla. Verificado por
recomputación, no por cita.

## 3. Los otros dos componentes del costo (el referente exige el desglose)

| Componente | Estado | Detalle |
|---|---|---|
| **Spread** | **medido sólo en 6E** | medio 1,141 ticks, 89 % del tiempo a 1 tick, sobre 5.554.201 quotes (publicado en el plan del 18-ago). Pendiente en los otros 10. |
| **Slippage** | **pendiente en los 11** | no se tabula: se mide o se declara una asunción conservadora. G0.4 prohíbe fills optimistas (~99,9 % de los límites se cancelan ⇒ asumir «entré al bid» sin evidencia no es admisible). |
| **Exchange / NFA / clearing** | **pendiente de confirmar** | no se sabe si la tabla del broker es all-in o si esos fees se suman aparte (ver §5, ítem 2). |

Nota de lectura: el spread **se paga si se cruza** (orden de mercado). Con orden
límite no se paga, pero el fill no está garantizado — y por G0.4 ningún escenario
asume el fill sin evidencia. El ledger no mezcla: cada componente va por su lado.

## 4. Regla de escenario

El escenario base es **específico por instrumento** (comisión de la tabla +
spread medido de ese instrumento + slippage declarado). La fricción histórica de
H1 (−2,7680 ticks/evento) queda como **referencia hostil, no transportable** —
escrita en el manifiesto H-Z2A §8. Q-ECONÓMICA muere si el recorrido no paga
spread + slippage + comisión en base.

## 5. Pendientes de Nico (numerados para contestar uno por uno)

1. **ZB y MBT no aparecen en las capturas** — faltan sus comisiones por lado.
2. **¿La comisión publicada es all-in?** (¿incluye exchange/NFA/clearing?) o esos
   fees se suman aparte. El ledger registra «comisión por lado según tabla
   publicada»; si no es all-in, hay que sumarlos.
3. **¿El resumen de tu cuenta real coincide con la tabla publicada?** La tabla es
   la tarifa publicada; lo que te cobran de verdad es el dato que cierra N1.
4. **Slippage:** ¿asunción conservadora declarada (p.ej. 1 tick por lado) o se
   deja pendiente hasta medir? Cualquiera de las dos, por escrito.

## 6. Nota de feed (no es costo; queda registrada para el capítulo de ejecutabilidad)

Según el chat de Lucid AI (18-ago, declarado por el broker, **sin verificar**
contra documentación): LucidFlex usa **Rithmic** (Quantower, Sierra Chart,
Bookmap, ATAS, Jigsaw, MultiCharts, R|Trader Pro…) o **CQG** (NinjaTrader,
Tradovate, TradingView) según la plataforma. **NT8 → CQG.** Relevancia: feed en
vivo, latencia y paridad research↔live (G5) — no entra en este ledger.

## 7. Lo que NO es

No desbloquea F4 por sí solo (el mapa lo ordena antes; no lo reemplaza). No
contiene outcomes ni mide mercado. No es una afirmación neta: es el insumo que la
validez económica (G3) va a consumir cuando exista un candidato. Hoy no hay
candidato — `EDGES_DISCOVERED` sigue en *ninguno*.

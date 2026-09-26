# Ledger de costos — capítulo 3 (v1, 2026-08-18)

- **Estado:** `v1 — CRITERIO APROXIMADO POR DECISIÓN DE NICO (multi-cuenta), vigente`.
  Las cuatro preguntas de la v0 fueron respondidas por Nico el 18-ago (§5).
- **Qué es:** el capítulo 3 del orden sellado (`0 ledgers → 3 costos → 5 población
  + 2 N_eff → 1 F4 → …`). Es el insumo de la **validez económica** (ítem 1 de la
  jerarquía del referente: expectativa NETA con costos desglosados; gate G3).
- **Referente:** `docs/NORTH_STAR.md` sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
- **Procedencia:** tabla de comisiones del broker (LucidFlex) en dos capturas del
  18-ago-2026, aportadas por Nico · especificaciones de instrumento desde la
  fuente única del repo `edgelab/instruments.py` (blob
  `30ea647e38bc266c52ec7229765c31d59e894566`) — nada re-declarado a mano ·
  aproximaciones genéricas de internet para ZB/MBT con fuentes citadas (§5.1).
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
| 6E | 2,40 | 6,25 | **0,768** | tabla del broker (captura) |
| 6B | 2,40 | 6,25 | **0,768** | tabla del broker (captura) |
| 6J | 2,40 | 6,25 | **0,768** | tabla del broker (captura) |
| ES | 1,75 | 12,50 | **0,280** | tabla del broker (captura) |
| NQ | 1,75 | 5,00 | **0,700** | tabla del broker (captura) |
| YM | 1,75 | 5,00 | **0,700** | tabla del broker (captura) |
| GC | 2,30 | 10,00 | **0,460** | tabla del broker (captura) |
| MES | 0,50 | 1,25 | **0,800** | tabla del broker (captura) |
| MNQ | 0,50 | 0,50 | **2,000** | tabla del broker (captura) |
| **ZB** | ≈2,20–2,90 (rango genérico retail all-in) | 31,25 | **≈ 0,14–0,19** | **referencia, no operable en LucidFlex** (§5.1) |
| **MBT** | ≈1,15–1,45 (all-in retail según plan) | 0,50 | **≈ 4,6–5,8** | **referencia, no operable en LucidFlex** (§5.1) |

**Consistencia:** 6E ⇒ 0,768 y ES ⇒ 0,280 coinciden con lo tabulado en la entrada
009 del canal — la fuente tabulada era esta misma tabla. Verificado por
recomputación, no por cita. Y la tabla del broker queda en el mismo orden de
magnitud que los rangos genéricos de mercado (la tabla de NinjaTrader all-in da
ES ≈ 2,18–2,88 USD/lado): no hay contradicción que investigar.

## 3. Los otros dos componentes del costo (el referente exige el desglose)

| Componente | Estado | Detalle |
|---|---|---|
| **Spread** | **medido sólo en 6E** | medio 1,141 ticks, 89 % del tiempo a 1 tick, sobre 5.554.201 quotes (publicado en el plan del 18-ago). Pendiente en los otros 10. |
| **Slippage** | **declarado: 1 tick por lado (2 ticks RT)** | asunción conservadora declarada por Nico el 18-ago (§5.4). G0.4 prohíbe fills optimistas (~99,9 % de los límites se cancelan ⇒ asumir «entré al bid» sin evidencia no es admisible). |
| **Exchange / NFA / clearing** | **supuesto declarado, sin verificar** | se asume que la tabla del broker es all-in (§5.2). Si no lo es, el error **subestima** el costo; el slippage declarado actúa como colchón parcial — declarado, no verificado. |

Nota de lectura: el spread **se paga si se cruza** (orden de mercado). Con orden
límite no se paga, pero el fill no está garantizado — y por G0.4 ningún escenario
asume el fill sin evidencia. El ledger no mezcla: cada componente va por su lado.

## 4. Fricción del escenario base declarado

`fricción_base = comisión RT + slippage declarado (2 ticks RT)` + spread si se
cruza (medido sólo en 6E; pendiente en el resto).

| Instrumento | Mínimo declarado (comisión + slippage) | Con spread (6E medido) |
|---|---|---|
| 6B / 6E / 6J | 2,768 ticks RT | **6E ≈ 3,9 ticks RT** |
| ES | 2,280 ticks RT | spread pendiente |
| NQ / YM | 2,700 ticks RT | spread pendiente |
| GC | 2,460 ticks RT | spread pendiente |
| MES | 2,800 ticks RT | spread pendiente |
| MNQ | 4,000 ticks RT | spread pendiente |
| ZB / MBT | referencia solamente — no operables en la cuenta | — |

El escenario base es **específico por instrumento**. La fricción histórica de
H1 (−2,7680 ticks/evento) queda como **referencia hostil, no transportable**
(manifiesto H-Z2A §8). Q-ECONÓMICA muere si el recorrido no paga
spread + slippage + comisión en base.

## 5. Las cuatro preguntas de la v0, respondidas por Nico (18-ago)

1. **ZB y MBT no están disponibles para operar en LucidFlex** → aproximación
   genérica de internet, **referencia solamente**:
   - **MBT** (Micro Bitcoin, CME): tabla all-in de NinjaTrader — exchange+NFA
     0,87 + clearing 0,19 + comisión según plan 0,09/0,29/0,39 ⇒ **≈ 1,15–1,45
     USD/lado** (≈ 4,6–5,8 ticks RT con tick_value 0,50).
   - **ZB** (30-Year Bond, CBOT): sin fila exacta en las fuentes; por clase
     (estándar, tesoro CBOT) el all-in retail cae en **≈ 2,20–2,90 USD/lado**
     (≈ 0,14–0,19 ticks RT con tick_value 31,25). Anclas: estructura all-in de
     NinjaTrader (comisión estándar 0,59–1,29 + clearing 0,19 + exchange&NFA de
     la clase índice ~1,4) y la familia de bonos CBOT en la tabla de Topstep
     (UB 2,92 / TN 2,62 RT).
   - Fuentes: support.ninjatrader.com «How Can I Understand the All-In Rates»
     (tabla por instrumento, MBT) · ninjatrader.com/pricing (planes) ·
     help.topstep.com «TopstepX — Commissions and Fees» (estructura RT y
     ejemplos) · stockbrokers.com/futures/review/ninjatrader (exchange+NFA
     ~0,19/contrato + routing 0,25). Consultadas el 18-ago-2026.
2. **¿All-in?** — «No sé, creo que sí» → **supuesto declarado, sin verificar**:
   la tabla se trata como all-in. Dirección del error si no lo es: subestima el
   costo; el colchón parcial es el slippage declarado.
3. **¿Cuenta real = tabla publicada?** — «No sé, pero supongamos que sí», con la
   decisión que importa: **el criterio económico es aproximado por diseño porque
   se opera en cuentas distintas**. Esto cierra N1 como decisión, no como número:
   no hay una comisión única verdadera; hay la tabla + estos supuestos
   declarados. Si una cuenta futura difiere mucho de la tabla, se actualiza la
   fila — no la estructura.
4. **Slippage** — «la declarada» → **1 tick por lado (2 ticks RT)**, asunción
   conservadora escrita.

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

# Referencia de costos de ejecución: props y brokers (2026-10-14)

**Estado:** referencia, no medición. Sin P&L, sin retornos. Insumo para el ledger de costos (cap. 3) y para el manifiesto de la campaña de P&L (que sigue bajo STOP).
**Fuentes:** scrape previo del repo (`artifacts/propfirm/crawl/*/inventario.md`, 2026-09-26, más `LEDGER_COSTOS_CAP3_2026-08-18.md`) **más relectura en vivo de las páginas oficiales** el 2026-10-14: Topstep (help.topstep.com, art. 8284213, "actualizado hace 2 semanas"), Lucid (support.lucidtrading.com, art. 11508978, 26-ago-2026), MyFundedFutures (art. 9735811, 24-ago-2026), TakeProfitTrader (art. 15172548967069). Tradeify viene del scrape previo. `verified = False`: falta revisión humana.

## 1. Comisión round-turn, todo incluido, por firma (USD por contrato)
| Producto | Topstep | Lucid | MFFU | Tradeify | TPT |
|---|---|---|---|---|---|
| ES | 3,78 | 3,50 | 4,68 | 5,76 | 4,50 |
| NQ | 3,78 | 3,50 | 4,68 | 5,76 | 4,50 |
| MES | 1,22 | 1,00 | 1,90 | 1,82 | 1,50 |
| MNQ | 1,22 | 1,00 | 1,90 | 1,82 | 1,50 |
| YM / MYM | 3,78 / 1,22 | 3,50 / 1,00 | 5,76 / 1,90 | n/d | 4,50 / 1,50 |
| RTY | 3,78 | 3,50 | 4,68 | n/d | 4,50 |
| GC | 4,32 | 4,60 | 5,12 | 6,20 | 4,50 |
| MGC | 1,92 | 1,60 | 2,20 | n/d | 1,50 |
| 6E / 6B / 6J | 4,22 | 4,80 | 5,12 | n/d | 4,50 |
Notas: Lucid publica por lado (se duplicó). Topstep desglosa exchange + NFA + comisión; el exchange sube el 2026-10-01 sólo en MCL y MNG. Lucid no aclara si su tarifa incluye exchange y NFA (el ledger lo asume, sin verificar). Rangos genéricos de brokers retail (NinjaTrader all-in): ES ≈ 4,4–5,8 USD RT; el rango de las props está en ese orden.

## 2. Comisión en ticks (USD RT ÷ valor del tick)
Valores de tick: ES 12,50 · NQ/YM/RTY 5 · MES 1,25 · MNQ 0,50 · GC 10 · MGC 1 · 6E 6,25.
| Producto | Topstep | Lucid | MFFU | Tradeify | TPT |
|---|---|---|---|---|---|
| ES | 0,30 | 0,28 | 0,37 | 0,46 | 0,36 |
| NQ | 0,76 | 0,70 | 0,94 | 1,15 | 0,90 |
| MES | 0,98 | 0,80 | 1,52 | 1,46 | 1,20 |
| MNQ | 2,44 | 2,00 | 3,80 | 3,64 | 3,00 |
| GC | 0,43 | 0,46 | 0,51 | 0,62 | 0,45 |
| MGC | 1,92 | 1,60 | 2,20 | n/d | 1,50 |
| 6E | 0,68 | 0,77 | 0,82 | n/d | 0,72 |
Rango de ES: 0,28–0,46 ticks. El de MES va de 0,80 a 1,52 ticks: **los micros pagan de 3 a 5 veces más fricción relativa que el mini**.

## 3. Spread y slippage
- **Spread medido (atlas v4, horario regular 08:30–15:00 CT):** media ES 1,09; MES 1,10; 6E 1,34 (p50 1); YM 1,90; MNQ 2,11; MYM 1,69; RTY 1,50; **NQ 3,03; GC 3,43 (p50 3); MGC 2,72; MBT 2,69**. Se paga al cruzar con orden de mercado (un spread por ida y vuelta). Fuente: `resultados_claude_local/atlas-microestructura-14activos-v4`, release v4, sin P&L.
- **Slippage:** ninguna firma publica un número. Topstep sólo explica que el slippage puede empujar la cuenta más allá de su Maximum Loss Limit. Se mantiene la **asunción declarada de Nico: 1 tick por lado (2 RT)** (ledger cap. 3), como colchón conservador.
- Sim vs real: Topstep, MFFU y Lucid prohíben explotar fills irreales del simulador; los resultados con orden límite sin evidencia de fill no son admisibles (G0.4).

## 4. Fricción por viaje redondo, ejemplo de cruce con orden de mercado
`fricción = spread medido + comisión + slippage declarado (2 ticks RT)`
| Producto | Con comisión mínima (Lucid) | Con comisión máxima de la tabla |
|---|---|---|
| ES | 1,09 + 0,28 + 2 = **3,37** | 1,09 + 0,46 + 2 = **3,55** |
| 6E | 1,34 + 0,77 + 2 = **4,11** | 1,34 + 0,82 + 2 = **4,16** |
| NQ | 3,03 + 0,70 + 2 = **5,73** | 3,03 + 1,15 + 2 = **6,18** |
| GC | 3,43 + 0,46 + 2 = **5,89** | 3,43 + 0,62 + 2 = **6,05** |
| MNQ | 2,11 + 2,00 + 2 = **6,11** | 2,11 + 3,80 + 2 = **7,91** |
| MES | 1,10 + 0,80 + 2 = **3,90** | 1,10 + 1,52 + 2 = **4,62** |
Esto corrige el ranking de fricción de Gemini (que asumía spread = 1 tick y colocaba a GC segundo): **ES es el único producto con fricción < 4 ticks; GC y NQ rondan 6; MNQ casi 7–8.** En dólares, ES ≈ 42–44 USD por viaje; MES, 4,9–5,8 USD (el mini es más barato por tick, no por contrato).
La cifra es un techo conservador por el slippage declarado; una ejecución pasiva sólo ahorra el spread si hay evidencia de fill (hoy no la hay).

## 5. Reglas de las props que condicionan *dónde* sirve un algoritmo (resumen; detalle en `PROPFIRM_REGLAS_DETALLADAS_20260926.md`)
- **Apex y TakeProfitTrader prohíben algoritmos:** quedan fuera para EdgeLab.
- Topstep: automatización condicional en Combine/XFA; no llega a la cuenta Live.
- Tradeify: > 50 % de trades y ganancias con tenencia > 10 s en fondeada. Lucid: revisión si > 50 % de las ganancias vienen de trades de ≤ 5 s; pérdida de cuenta en red folder (LucidDaily). MFFU: sin HFT ni explotar el simulador.
- Consecuencia: **cualquier candidato scalping de pocos ticks y pocos segundos choca con estas reglas aunque pase la fricción.**

## 6. Qué cambia en el plan
- Para el manifiesto de P&L, ES tiene la fricción más baja por viaje; una comisión de referencia razonable es **0,28–0,46 ticks** (rango de las props que admiten algoritmos) + spread medido + slippage declarado.
- Falta un dato de Nico: la cuenta real donde se operará y su tarifa efectiva. Hasta entonces, se reportan siempre ambos extremos del rango.
- Si el recorrido bruto utilizable en ES no supera claramente ~3,5–4 ticks por viaje, la hipótesis muere sin gastar presupuesto de P&L (paso A3 del plan).
- Limitaciones: tarifas de terceros pueden cambiar; slippage real sin medir; sin evidencia de fills pasivos; instrumentos con spread medido solo en horario regular.

## 7. Activos complementarios (relevado en las mismas tablas, 2026-10-14)
Comisión round-turn all-in en USD y en ticks (tick: 6B/6J 6,25 · MGC 1,00 · MBT 0,50 · ZB 31,25):
| Producto | Topstep | Lucid | MFFU | Rango en ticks |
|---|---|---|---|---|
| 6B / 6J | 4,22 | 4,80 | 5,12 | 0,68 – 0,82 |
| MGC | 1,92 | 1,60 | 2,20 | 1,60 – 2,20 |
| MBT | 2,82 | no figura | 3,50 | 5,64 – 7,00 |
| ZB | 2,76 | no figura | no figura | 0,09 (una sola fuente) |
Las tarifas de YM, MYM y RTY ya estaban en §2. Con esto ningún activo del R2 usa una comisión aproximada salvo ZB (fuente única).


## Adenda 2026-10-26 — spread medido de 6B
Medido con `tools/medir_spread_main.py` (kernel `nicobuttaro/medir-spread-6b`) con el criterio del atlas v4: media ask − bid en ticks
sobre ticks con libro válido, 08:30–15:00 CT, sólo desarrollo. **6B: 1,06 ticks** (p50 1; 4.167.355 ticks, 291 sesiones). Validación
del método: el mismo kernel sobre 6E (`nicobuttaro/medir-spread-6e`) da **1,341**, igual al 1,34 del atlas. Cargado en
`config/costos/costos_canonicos.json`.

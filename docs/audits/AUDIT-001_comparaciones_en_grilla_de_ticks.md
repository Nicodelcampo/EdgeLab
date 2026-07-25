# AUDIT-001 — Comparaciones de precio y redondeos sobre la grilla de ticks

**Fecha:** 2026-07-24 · **Alcance:** los 5 `.cs` de EdgeLab y sus 5 kernels Python.
**Estado:** SOLO REPORTE. **Ningún fix de esta tabla se aplica sin OK explícito de
Nico**, salvo el de BigTrap2 que ya fue aprobado y aplicado (v2.1).

## Por qué esta auditoría

La familia de bug no es "comparar precio reconstruido contra precio del feed".
Es más amplia: **toda división `precio / tickSize` seguida de floor / round /
truncate / cast, y toda desigualdad entre precios que puedan empatar sobre la
grilla**. Esta familia ya produjo **dos bugs distintos** en el proyecto:

1. **Banker's rounding** en la geometría del matcher (`parity._geom_ticks`) — la
   misma zona medía 0, 1 o 2 ticks según la paridad del índice de fila.
2. **1 ULP** en `BigTrap2.cs` — `rowPrice > close` comparaba `r*TickSize`
   (reconstruido) contra `Close[0]` (feed); 101 falsos `trapped_buyers`.

Regla que se deriva y queda en el contrato: **toda comparación de precios se hace
en índices enteros de tick; los `double` solo para I/O.**

## (a) Desigualdades entre precios

| archivo | línea | expresión | riesgo | fix propuesto |
|---|---|---|---|---|
| `BigTrap2.cs` | 364 / 376 | `rowHalfTick > closeHalfTick` | **CORREGIDO v2.1** | ya aplicado: enteros en medios ticks, empate excluido de ambos lados |
| `HFTZones2.cs` | 469–473 | `retro > allowed`, con `allowed = Math.Max(RetroFloorTicks, pct/100*heightTicks)` | **ALTO** | `retro = (_swH - price)/TickSize` es **matemáticamente entero**; cuando gana la rama `RetroFloorTicks` (entero) el empate lo decide el ULP. Y NT8 usa `price` del **feed** mientras Python usa `pticks[i]*tick_size` (**reconstruido**): misma asimetría exacta que el bug de BigTrap2. Fix: redondear `retro` a entero (`AwayFromZero`) y comparar contra `RetroFloorTicks` en enteros; la rama porcentual puede seguir en `double` (es continua, el empate es de medida nula) |
| `hftzones2.py` | 379–385 | idéntica al `.cs` | **ALTO (espejo)** | mismo fix, sincronizado con el `.cs` en el mismo commit — si se corrige un solo lado se **rompe** la paridad |
| `gaps2.py` | 158–159 | `price <= g["bottom"] - rct*tick_size` | **MEDIO** | umbral reconstruido vs precio. El `.cs` hace la **misma** aritmética ⇒ la paridad hoy sale bien, pero es *paridad por bug compartido*: ambos lados coinciden porque cometen el mismo error, no porque el cálculo sea exacto. Fix: comparar en ticks enteros en ambos lados |
| `BigTrap2.cs` | 365 / 377 | `rowPrice >= wickHiFloor` / `rowPrice <= wickLoCeil` | **NULO** | `wickHiFloor = hi - range*pct` es un valor **continuo**, no cae en la grilla salvo coincidencia ⇒ el empate es de medida nula. Python replica la expresión carácter por carácter. **No tocar** |
| `avolcellpoi2.py` | 260, 269, 308 | `close > z["upper"]`, etc. | **NULO** | ambos operandos son precios de grilla construidos igual en los dos lados |
| `bigtrap2.py` | 139, 145 | `hi >= z["lo"]`, `close > z["hi"]` | **NULO** | los bordes de zona son `tick*tick_size ± tick_size/2` — a medio tick de la grilla, el empate es imposible por construcción |

## (b) División `precio / tickSize` con floor / round / truncate / cast

| archivo | línea | expresión | riesgo | fix propuesto |
|---|---|---|---|---|
| `BigTrap2.cs` | 264 | `(long)Math.Round(price/TickSize, AwayFromZero)` | **NULO** | convención correcta ya presente |
| `BigTrap2.cs` | 311 | `2*(long)Math.Round(close/TickSize, AwayFromZero)` | **NULO** | nuevo en v2.1, convención correcta |
| `VolTicksPOC2.cs` | 438 | `(long)Math.Round(snapped/TickSize, AwayFromZero)` | **NULO** | correcto |
| `aVolCellPOI2.cs` | 489, 534 | idem | **NULO** | correcto |
| `Gaps2.cs` | 248 | `(int)Math.Round(abs(price-prev)/TickSize)` y luego `gapTicks >= ExportFloorTicks` | **BAJO** | **patrón correcto y a imitar**: redondea a entero *antes* de comparar. Es la razón estructural de que Gaps2 diera 1316/1316. Solo falta `MidpointRounding.AwayFromZero` por convención (el `.5` es imposible sobre grilla, así que es cosmético) |
| `gaps2.py` | 228 | `int(round(abs(price-prev)/tick_size))` | **BAJO** | `round()` de Python es banker's y C# por defecto también: hoy **coinciden**. Si se toca un lado hay que tocar el otro. Declarar la convención |
| `HFTZones2.cs` | 482 | `(int)Math.Round((_swH-_swL)/TickSize)` **sin** `MidpointRounding` | **BAJO** | banker's; el `.5` es imposible sobre grilla. Agregar `AwayFromZero` por convención, junto con el fix ALTO de arriba |
| `hftzones2.py` | 303 | `int(round(...))` | **BAJO** | espejo del anterior |
| `BigTrap2.cs` | 570, 577 | `Math.Ceiling/Floor(vols.Length * pct/100)` | **NULO** | índices de percentil sobre longitudes de array, no precios |
| `VolTicksPOC2.cs` | 298, 400–402 | percentil e índices de heatmap | **NULO** | no son precios |
| `aVolCellPOI2.cs` | 544, 664–666 | bucket temporal y heatmap | **NULO** | no son precios |
| `HFTZones2.cs` | 377 | `(int)Math.Ceiling(q*n)-1` | **NULO** | índice de percentil |

## Resumen

- **1 hallazgo ALTO**, en dos lugares que deben corregirse **juntos**:
  `HFTZones2.cs:469-473` + `hftzones2.py:379-385`. Es el mismo patrón que el bug
  ya confirmado en BigTrap2 (empate entero decidido por ULP + asimetría
  feed-vs-reconstruido), todavía **no observado** porque HFTZones2 aún no tiene
  oráculo real corrido.
- **1 hallazgo MEDIO**: `gaps2.py:158-159` — paridad por bug compartido. No
  rompe nada hoy; es deuda de robustez.
- **4 hallazgos BAJOS**, todos cosméticos (convención de `MidpointRounding`)
  porque el caso `.5` es imposible sobre la grilla de ticks.
- El resto es **NULO**: o no son precios, o ambos lados construyen los operandos
  de la misma forma sobre la grilla.

**Nada de esto se aplica sin OK de Nico.** El hallazgo ALTO conviene resolverlo
*antes* de generar el primer oráculo de HFTZones2, para no gastar un export en
descubrir el mismo bug por tercera vez.

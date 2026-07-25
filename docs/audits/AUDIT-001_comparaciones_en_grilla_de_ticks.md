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
| `HFTZones2.cs` | 469–473 | `retro > allowed`, con `allowed = Math.Max(RetroFloorTicks, pct/100*heightTicks)` | ~~ALTO~~ **RESUELTO v2.1** | `retro = (_swH - price)/TickSize` es **matemáticamente entero**; cuando gana la rama `RetroFloorTicks` (entero) el empate lo decidía el ULP. Y NT8 usaba `price` del **feed** mientras Python usa `pticks[i]*tick_size` (**reconstruido**): misma asimetría que el bug de BigTrap2. **Corregido** (ver §Resolución) |
| `hftzones2.py` | 379–385 | idéntica al `.cs` | ~~ALTO~~ **RESUELTO v2.1** | fix espejo aplicado en el **mismo commit** que el `.cs` |
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

---

## Resolución del hallazgo ALTO (2026-07-25) — HFTZones2 v2.1

Autorizado por Nico. Corregido en **ambos lados, en el mismo commit**.

**`.cs` (revisado fuera del repo, verificado byte a byte antes de instalar):**
helper `PriceToTick(price) = Math.Round(price/TickSize, AwayFromZero)`; altura y
retroceso como diferencias de índices enteros (`long`); `retroTicks > allowed`
estricto (el empate **no** corta); `FinalizeStreak` usa la misma altura entera;
meta a `version=2.1, engine=…integer_grid`.

**Kernel (`hftzones2.py`):** espejo con `common.snap_to_tick`, que ya era
`round(price/tick, AwayFromZero)` — no hizo falta inventar un converter nuevo.

**Verificación de que el `.cs` recibido era exactamente lo declarado** (antes de
instalarlo): 72/72 propiedades y 27/27 defaults numéricos idénticos al v2.0,
llaves y paréntesis balanceados, `PriceToTick` definido 1× y usado 5×, y **una
sola** división por `TickSize` en todo el archivo (dentro del propio helper).
El diff son 6 hunks y ninguno toca params, umbrales, lifecycle ni clasificación.

**Magnitud medida del bug** (por qué no era teórico): `(swh − price)/tick_size`
**nunca** da el entero exacto en el rango del 6E — falla en el **100 %** de los
pares 20000–25000, y el desvío va en **ambas** direcciones (12.351 por encima,
27.657 por debajo). Con `allowed` entero, Python cortaba donde el `.cs` v2.1 no
corta en el **5,0 %** de los niveles (rama del piso) y en el **22 %** (rama
porcentual con altura par).

**Tests:** `tests/bridge/test_hftzones2_retro_grid.py` — 12 casos: la aritmética
vieja falla siempre, `snap_to_tick` es exacto en todo el rango y es
`AwayFromZero` (no banker's), y el empate **no corta** / un tick más **sí
corta**, en las dos ramas (piso y porcentual) y en las dos direcciones.

**Impacto en el store:** ninguno. Había **0 particiones de HFTZones2**, así que
no quedó nada no comparable. `kernel_id` de Gaps2 sigue en `771429ccc049bb8e`,
idéntico en las 5 particiones — CAMP-001 **no** se vio afectada.

## Regla operativa de los `.cs` (incidente 2026-07-25)

Instalar el `.cs` revisado **rompió la compilación** de NT8 (CS0111 / CS0102 /
CS0121 / CS0229, "Type 'Indicator' already defines a member called
'HFTZones2'"). Causa raíz encontrada: el archivo revisado venía con
terminadores **LF** y con el bloque `#region NinjaScript generated code` ya
incluido. NT8 escribe **CRLF**, no reconoció su propia región y **anexó una
segunda** en vez de reemplazarla → dos regiones → dos definiciones de los
wrappers. Se verificó que la clase estaba definida **una** sola vez y que había
**un** solo `.cs` con ella: la duplicación era interna al archivo.

Reglas que quedan:

1. **Los `.cs` se REEMPLAZAN in place; nunca se guardan copias dentro de
   `bin\Custom`** — NT8 compila todo el árbol. Los respaldos van a
   `archive/nt8_cs_backup/` con timestamp, **fuera** de `bin\Custom`.
2. **La copia canónica del repo (`nt8/`) no lleva la región generada**: es
   salida de build, la regenera NT8 al compilar.
3. **Terminadores CRLF siempre.** Un `.cs` con LF hace que NT8 duplique la
   región.
4. Verificar con `python tools/check_nt8_cs.py <archivo> --version <v>` **antes**
   de instalar.

**Deuda detectada por el checker, NO corregida a propósito:** `BigTrap2.cs`
tiene 759 terminadores **CR CR LF** (doble CR), preexistentes. Hoy compila y
tiene una sola región, así que el riesgo es latente, no activo. **No se toca
antes del export del oráculo v2**, que es el que valida PRED-001: cambiar ese
archivo justo antes de esa medición agrega riesgo sin beneficio. Normalizar
después.

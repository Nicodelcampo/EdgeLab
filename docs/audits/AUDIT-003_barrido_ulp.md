# AUDIT-003 — Barrido ULP completo de los seis `.cs`

**Fecha**: 2026-07-26 · **Autorizado por**: Nico (directiva de orden: *barrido
ULP antes de cualquier re-export*) · **Referente**: `docs/NORTH_STAR.md`
sha256 `21bb3b01a33e2b37…`

## Por qué se hizo de una pasada

Las cuatro apariciones anteriores de la familia se encontraron **de a una, cada
una gastando un oráculo**. Ese método tiene un costo por hallazgo altísimo y, lo
peor, no acota: después de corregir la cuarta no había forma de decir si quedaba
una quinta. El barrido de una pasada convierte "¿quedará alguna?" en una
pregunta contestable.

`AUDIT-001` ya había intentado la búsqueda leyendo código y **falló**: clasificó
como riesgo NULO la comparación que resultó ser la causa raíz de los 82
`FEATURE_DIFF` de HFTZones2. El argumento que usó — "ambos operandos son precios
de grilla construidos igual en los dos lados" — es válido *sólo* cuando los dos
operandos llegan sin aritmética intermedia. Esta auditoría hace esa distinción
explícita y la codifica.

## Método

1. **Detector estático** (`tools/ulp_sweep.py`): marca toda comparación que
   enfrente expresiones de precio sin pasar por índices enteros.
2. **Triaje sellado** (`tools/ulp_sweep_baseline.json`): cada candidato queda con
   veredicto **y evidencia**. Un veredicto sin evidencia es una opinión, que es
   exactamente lo que fue AUDIT-001 — la suite lo exige (`len(evidencia) > 40`).
3. **Medición** (`tools/ulp_exposure.py`) para todo lo que no sea inmune por
   construcción. Se cuenta cuántas decisiones **cambian de lado** entre la
   representación del feed y la reconstruida, sobre el rango real del
   instrumento.
4. **Gate de regresión**: desde ahora el barrido falla ante cualquier expresión
   **nueva sin clasificar**, no ante las 49 ya clasificadas.

### El detector se auditó a sí mismo

Dos omisiones encontradas y corregidas **durante** el barrido — vale registrarlas
porque son el modo de falla del método, no anécdotas:

| omisión | expresión que se perdía | corrección |
|---|---|---|
| faltaban `top`/`bot` en la lista de identificadores de precio | `if (top - bot < ExpansionMinTicks * TickSize)` | se agregaron `top`, `bot`, `hi`, `lo`, `piv*` |
| faltaban `zLo`/`zHi`/`close` | `bool adverseClose = z.IsBull ? close > zHi : close < zLo` | se agregaron `zLo`, `zHi`, `close`, `open`, `askQ`, `bidQ` |

La segunda es la más incómoda: se perdía justo una comparación de invalidación
de zona. Un detector cuya cobertura no se audita hereda el modo de falla que
venía a resolver.

## Resultado: 49 candidatos, 6 archivos

| veredicto | n | significado |
|---|---|---|
| `INMUNE_MONOTONO` | 26 | ambos operandos son precios de grilla **sin aritmética**: `feed()` y `ticks×tick_size` son estrictamente monótonas en el índice de tick ⇒ preservan orden y empates |
| `INMUNE_MEDIOTICK` | 8 | el borde vive a medio tick ⇒ ningún precio negociable cae encima ⇒ empate imposible. Exposición **medida** 0,00 % |
| `NO_ES_PRECIO` | 7 | falso positivo: índices de array / pesos acumulados en helpers de búsqueda binaria y percentil |
| `FUERA_DE_ALCANCE` | 7 | capa declarada **no portada** a Python (expansiones ZigZag, filtro por percentil) |
| `EXPUESTO_PENDIENTE` | 2 | exposición medida **> 0** y la corrección exige una decisión que Nico no tomó |

Se sellan también los `NO_ES_PRECIO`: si mañana un helper empieza a comparar
precios, la expresión cambia y el gate vuelve a saltar.

## Hallazgo 1 — `HFTZones2.cs` estaba en v2.2 mientras el kernel Python ya era v2.3

**El hallazgo más caro del barrido, y el que justifica la directiva de orden.**

El kernel Python `hftzones2.py` se corrigió a v2.3 (todo el ciclo de vida en
enteros) pero **el `.cs` se quedó en v2.2**: `close_through` ya comparaba
enteros, `inside` seguía en `double`.

```csharp
// v2.2 — lo que había
bool inside = price >= z.Lower && price <= z.Upper;          // ← 24,30 % expuesto
bool through = PriceToTick(price) <= z.LowerTick - Penetration;  // ← ya en enteros
```

Los dos lados estaban **desalineados por construcción**. Un oráculo exportado en
ese estado habría dado FAIL y el diff habría apuntado al ciclo de vida, no a la
versión. Corregido en **v2.3**: el precio se lleva a índice de tick **una vez por
llamada** y todas las comparaciones del ciclo de vida usan ese entero.

```csharp
// v2.3 — espejo exacto de hftzones2.py
long priceTick = PriceToTick(price);
bool inside = priceTick >= z.LowerTick && priceTick <= z.UpperTick;
```

Exposición tras el fix: **0,00 % en los cuatro umbrales** (`ulp_exposure.py`).

## Hallazgo 2 — `AACloseOpenDiffs.cs`: el 47,5 % de los gaps de 1 tick, corregido

Corrección **aprobada por Nico** (Decisión 1). Estado previo:

```csharp
double gapPts = Math.Abs(closePrev - openCurr);
if (gapPts < MinDiffTicks * TickSize) return;      // v1.0
```

NT8 entrega el precio como el `double` del decimal parseado del feed, que en el
**24,3 %** de los niveles de 6E cae 1 ULP **por debajo** de la grilla. Al restar
dos precios consecutivos la diferencia queda apenas por debajo de `1*TickSize` y
el `<` la mata.

- Predicho: **47,5 %** de los gaps de exactamente 1 tick descartados.
- Observado contra el oráculo: **43,5 %**.

v1.1:

```csharp
long gapTicks = Math.Abs(PriceToTick(closePrev) - PriceToTick(openCurr));
double gapPts = Math.Abs(closePrev - openCurr);   // sobrevive sólo para I/O
if (gapTicks < MinDiffTicks) return;
```

`diff_ticks` del export de paridad pasa a escribirse desde `gapTicks` en vez de
`Math.Round(gapPts / TickSize)` — mismo valor, sin la división.

### Defecto histórico, declarado

**Todo dato de `AACloseOpenDiffs` generado antes del 2026-07-26 tiene ~47 % de
los gaps de 1 tick faltantes.** No es ruido: es un sesgo **sistemático hacia los
gaps grandes**, y correlacionado con el nivel de precio (depende de qué niveles
caen 1 ULP abajo). Cualquier estadística de tamaño de gap calculada sobre esos
datos está sesgada hacia arriba. El logger de research
(`D:\A Trading\loggers\AACloseOpenDiffs.csv`), que **mergea** con lo previo,
arrastra el defecto en su parte histórica.

## Hallazgo 3 — `BigTrap2` filtro de mecha: 0,0241 % medido, EXPUESTO, sin corregir

El único candidato que quedó expuesto y **no** se corrigió, porque corregirlo es
una decisión de diseño que no está entre las tres que Nico cerró.

```csharp
double range = hi - lo;
double wickHiFloor = hi - range * (WickZonePct / 100.0);   // WickZonePct = 30
...
&& (!UseWickFilter || (range > 0 && rowPrice >= wickHiFloor))
```

**Medición** (6E, tick 5e-05, 5 decimales; rangos de 1 a 120 ticks × niveles
20000–20400; 2.952.000 decisiones evaluadas):

| | |
|---|---|
| flips | **710** |
| exposición | **0,0241 %** |
| dirección | **bidireccional** (NT8=True/Py=False *y* al revés) |

La bidireccionalidad lo distingue del resto de la familia: los otros cuatro casos
eran unidireccionales porque el feed siempre cae por debajo. Acá el umbral se
construye con una resta *y* una multiplicación, y el signo del error depende del
rango.

**Por qué no se corrigió**: `hi − range × 0,30` **no está en la grilla de ticks**
y no se puede pasar a enteros sin elegir una semántica de redondeo. Las opciones
—truncar hacia la mecha, redondear al tick más cercano, o redefinir el parámetro
en ticks en vez de porcentaje— **cambian qué filas entran al cálculo**, o sea la
definición del indicador. Eso es diseño, no corrección. Queda listado y frenado.

**Cuándo importa**: el empate exige que `range_ticks × 0,30` sea entero, o sea
rangos múltiplos de 10 ticks. Son comunes, pero el efecto neto es chico: 0,0241 %
de las decisiones de fila, y sólo con `UseWickFilter=true` (que es el default).
No bloquea el oráculo de BigTrap2 — a 0,0241 % es improbable que produzca
siquiera un diff en una ventana de dos sesiones. Se declara para que, si aparece
**un** diff inexplicable en BigTrap2, esto sea lo primero que se mire.

## Hallazgo 4 — la capa de expansiones tiene la misma forma, sin portar

`AACloseOpenDiffs.DetectarExpansion()` (declarada **no portada**) contiene:

```csharp
double rev = Math.Max(1, ExpansionReversalTicks) * TickSize;
if (hiPrice - lo >= rev)   ...
if (top - bot < ExpansionMinTicks * TickSize) return;
```

Es exactamente la forma canónica del bug, dos veces. Hoy no puede romper paridad
porque la capa no existe en Python y `DetectarExpansiones` viene en `false`. Se
registra para que, **si alguna vez se porta**, se porte ya en enteros y no se
repita el ciclo de gastar un oráculo para descubrirlo.

## Estado del gate

```
tools/check_nt8_cs.py --ulp nt8/*.cs
```

49 candidatos, 49 triajeados, 0 sin clasificar. `tests/bridge/test_ulp_sweep.py`
(12 tests) lo fija en la suite, incluido uno que **inyecta la regresión** —
la forma exacta que tenía `AACloseOpenDiffs` v1.0 — y exige que el barrido la
marque. Un gate que nunca se vio fallar no es un gate.

## Lo que queda abierto

| # | qué | quién decide |
|---|---|---|
| 1 | semántica del umbral de mecha de BigTrap2 (0,0241 % medido) | **Nico** |
| 2 | si se re-genera el histórico de `AACloseOpenDiffs` o se marca como sesgado | **Nico** |
| 3 | portar la capa de expansiones (si se porta, en enteros desde el día 1) | diferido |

## Aporte al referente

Cierra el ciclo de "descubrir la familia ULP de a una por oráculo gastado". La
distancia al edge no se redujo por un hallazgo puntual sino porque **el costo de
verificar bajó**: de un export de NT8 por bug a un comando. Y acota: quedan 2
umbrales expuestos, ambos medidos, uno de ellos frenado a la espera de una
decisión — no "no sabemos cuántos quedan".

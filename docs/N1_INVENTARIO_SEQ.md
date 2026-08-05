# N1 — inventario de `seq`, y por qué P5 **no puede pasar** como está escrita

**Tip:** `70b6aff` · **Fuentes comparadas:** `nt8/BigTrap2.cs` (v2.4) y
`archive/nt8_cs_backup/BigTrap2_v2.1_20260727_102239.cs` (v2.1, la que produjo
el oráculo de referencia de P5).

> **Nada abierto:** ningún oráculo, ningún holdout, ningún outcome, NT8 sin
> tocar, pin sin mover. Esto es comparar **dos archivos de código fuente**.

## Por qué N1 existía

`eventSeq++` vive en **un solo lugar** (`BigTrap2.cs:892`, dentro de `LogEvent`)
y lo comparten los **12** puntos de emisión. P5 compara `seq` **absoluto** como
condición de FAIL:

```python
# tools/pred004_analyze.py:344
if x["seq"] != y["seq"]:
    dif.append("evento %d (%s): seq %d vs %d" % ...)
```

Un evento **no económico** que aparezca o desaparezca corre el `seq` de **todos**
los económicos posteriores, sin que cambie una coma de su contenido.

## Inventario: v2.1 (7 sitios) vs v2.4 (12 sitios)

| tipo | v2.1 — método | v2.4 — método | camino en v2.4 |
|---|---|---|---|
| `ERROR` | `OnBarUpdate` | `OnBarUpdate` | ambos |
| `FOOTPRINT_MISMATCH` | `OnBarUpdate` | `VerificarOHLC` **y** `ReportarMismatch` | **tiempo** / **tick** |
| `TRAP` | `EmitSide` | `EmitSide` | ambos · **económico** |
| `ZONE_CREATED` | `EmitSide` | `EmitSide` | ambos · **económico** |
| `ZONE_EXPIRED` / `_TOUCHED` / `_INVALIDATED` | `UpdateZones` | `UpdateZones` | ambos · **económico** |
| `ANCLAJE_VERIFICADO` | **no existe** | `DrenarPorOHLCV` | **sólo tick** |
| `BARRA_PROCESADA` | **no existe** | `DrenarPorOHLCV` | **sólo tick** |
| `ANCLAJE_AMBIGUO` | **no existe** | `Abstener` | **sólo tick** |
| `SESION_RESINCRONIZADA` | **no existe** | `AccumulateTick` | **sólo tick** |

**v2.1 no tiene la bifurcación**: `fpTicksPerBar` aparece **0 veces** en todo el
archivo, y no existen `snapQ`/`blockQ` ni `DrainReadyBars`.

### Las cuatro emisiones nuevas NO tocan el camino de tiempo — verificado

- `ANCLAJE_VERIFICADO` (453), `BARRA_PROCESADA` (481) y `ANCLAJE_AMBIGUO` (505,
  vía `Abstener` ← `DrenarPorOHLCV`) viven bajo `DrenarPorOHLCV`, y
  `DrainReadyBars` (`.cs:387`) hace **`return` antes** de llamarlo cuando
  `fpTicksPerBar <= 0`.
- `SESION_RESINCRONIZADA` está en `AccumulateTick`, **después** de un
  `if (fpTicksPerBar <= 0) { curBlock.Add(ev); return; }`.

Hasta acá, buenas noticias: **el conjunto de TIPOS del camino de tiempo es
idéntico entre v2.1 y v2.4.**

## El problema real, y no es el que se estaba vigilando

El riesgo que N1 declaraba era *"un diagnóstico nuevo corre el seq"*. **No es
eso.** Es que **el predicado de `FOOTPRINT_MISMATCH` cambió**, y los dos
predicados son **disjuntos**:

| versión | dónde | condición que dispara |
|---|---|---|
| **v2.1** | `.cs:218` | `Math.Abs(fpVol - Volume[0]) > 0.5` → **sólo VOLUMEN** |
| **v2.4** | `VerificarOHLC`, `.cs:596` | `o==sO && c==sC && mn==sL && mx==sH` → **sólo OHLC** |

**v2.1 miraba únicamente el volumen. v2.4, en el camino de tiempo, únicamente el
OHLC.** No es una condición más estricta ni más laxa: es **otra condición**. Una
barra puede disparar una y no la otra, en los dos sentidos.

### Consecuencia

El **número** de `FOOTPRINT_MISMATCH` en una corrida `time:1` va a diferir entre
v2.1 y v2.4 salvo coincidencia. `eventSeq` es compartido ⇒ **el `seq` absoluto de
todos los eventos económicos posteriores al primer desajuste se corre**.

> **P5, tal como está escrita hoy, falla por una razón que no tiene nada que ver
> con lo que P5 mide.** P5 busca una regresión en el camino de tiempo entre 2.1
> y 2.4; lo que va a encontrar es un contador compartido.

Y es peor que un falso FAIL: `FOOTPRINT_MISMATCH` **ya está excluido** de
`P5_TIPOS_ECONOMICOS`, o sea que el contrato **ya decidió** que su contenido no
se compara. Comparar su **efecto sobre el `seq`** contradice esa decisión.

## Las cuatro salidas de GPT-5, adjudicadas con el inventario en la mano

| # | salida | veredicto |
|---|---|---|
| 1 | conservar `seq` absoluto y justificar comparabilidad | **descartada** — el inventario prueba que NO es comparable |
| 2 | comparar **orden económico** + reportar `delta_seq` aparte | **la única defendible** |
| 3 | degradar P5 a `ABSTAIN` | honesta pero estéril: P5 nunca daría veredicto |
| 4 | reformular P5 | es lo mismo que 2 |

**La 2 y la 4 son cambio de contrato y las aprueba Nico, no yo.** Forma concreta:

```text
P5 compara, sobre los eventos de P5_TIPOS_ECONOMICOS y en su ORDEN económico:
  tipo · timestamp · payload            -> diferencia = FAIL
`seq` absoluto deja de ser condicion de FAIL y se REPORTA como delta_seq,
junto con el conteo de FOOTPRINT_MISMATCH de cada lado, que es su causa.
```

**Lo que esto NO debe volverse:** meter `seq` en `P5_PAYLOAD_IGNORABLE` para que
el problema desaparezca. Eso es silenciar una diferencia real con una lista
ignorable *post hoc* — justo lo que GPT-5 marcó como prohibido. La diferencia de
`seq` **es información**: dice cuántos mismatch de más o de menos hubo, y ese
número debe quedar publicado.

## Efecto colateral: **P3 queda resuelta, y a favor**

La pregunta que dejé abierta en el contrato v4 —si `.cs:601` (el emisor de
`FOOTPRINT_MISMATCH` **sin volumen**) haría que P3 fuera `NO_APLICA` de forma
permanente— se contesta con el mismo grafo:

- `.cs:601` está en `VerificarOHLC`, que `DrainReadyBars` llama **sólo** en la
  rama `fpTicksPerBar <= 0`. Es **exclusivo del camino de TIEMPO**.
- `.cs:541` (`ReportarMismatch`, los **5 pares**) cuelga de `DrenarPorOHLCV`,
  **exclusivo del camino de TICK**.

**En una captura de tick —que es donde vive P1/P2/P3— todo `FOOTPRINT_MISMATCH`
trae los cinco pares.** La regla fail-closed no vuelve P3 inalcanzable.

**Y la salida B queda descartada de plano:** agregarle volumen a `.cs:601` sería
tocar el payload del camino de **tiempo**, que es exactamente el que P5 exige
bit-idéntico. Se habría roto P5 para arreglar un problema que no existía.

> Queda en **salida A**, y ya no como elección conservadora sino como la única
> correcta. **No hace falta decisión de Nico sobre P3.**

## Lo que sigue abierto

- **La decisión de N1 es de Nico.** Es cambio de contrato.
- **T6 / gate de compilación.** Verificado que se puede correr **sin abrir NT8**:
  están `csc.exe` (.NET Framework 4.0), `NinjaTrader.Custom.csproj` (`net48`, 31
  referencias) y los assemblies en `C:\Program Files\NinjaTrader 8\bin\`.
  Requiere levantar el "no compiles" de la instrucción A2.
- **Adjudicación independiente del parche G1.** Sin auditor y sin Grok, **queda
  sin cumplir**. No la hago yo: reviso mi propio trabajo con el sesgo de quien lo
  escribió, y este expediente ya mostró tres veces que el autor no ve su propio
  modo de falla.

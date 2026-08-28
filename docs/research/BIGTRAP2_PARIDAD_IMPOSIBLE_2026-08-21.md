# BigTrap2 — la paridad contra el oráculo de 6E no es alcanzable, y no debería serlo

> ## ⬛ CORREGIDO EL MISMO DÍA — la generalización estaba mal
>
> Este documento concluía que **«un oráculo de GC tendría el mismo defecto»**. Eso era una
> **inferencia, no una medición**, y el oráculo de GC que Nico exportó horas después la
> **refuta**.
>
> | | 6E **v2.0** | GC **v2.5.2** |
> |---|---|---|
> | `FOOTPRINT_MISMATCH` | 26.661 / 29.905 | **50 / 45.307** |
> | tasa | **89 %** | **0,11 %** |
>
> La v2.5.2 **arregló la desalineación**. Su encabezado lo declara:
> `attribution=ohlcv_unique_match`, `anchor=bounded_verified`,
> `close_cmp=integer_half_ticks`, `tie_excluded_both_sides`. Y emite
> `BARRA_PROCESADA`, que da la frontera exacta de cada barra.
>
> **Lo que sigue siendo cierto**: el 89 % de desalineación del oráculo **v2.0 de 6E** es
> un hecho medido, y cualquier resultado histórico construido sobre ESA versión hereda el
> ruido.
>
> **Lo que se retracta**: que la paridad sea inalcanzable o indeseable *en general*.
> Con v2.5.2 es las dos cosas — alcanzable y deseable. Ver §7.


- **Fecha**: 2026-08-21 · **Estado**: `MEASURED_COMMITTED`
- **Alcance**: target-free. Sólo integridad del oráculo y del puerto. Sin outcomes.
- Oráculo auditado: `oracles/BigTrap2_diag_tick25_6E_0926.csv` — 6E 09-26, tick:25,
  2026-07-08 → 2026-07-24, 46.430 eventos.

---

## 1. El hallazgo

**`BigTrap2` no logró alinear el footprint con la barra en el 89 % de las barras.**

| evento | n |
|---|---|
| `FOOTPRINT_MISMATCH` | **26.661** |
| `TRAP` | 7.454 |
| `ZONE_TOUCHED` | 8.349 |
| `ZONE_CREATED` | 1.986 |
| `ZONE_INVALIDATED` | 1.910 |
| `ZONE_EXPIRED` | 69 |

Sobre **29.905 barras**, eso es **`26.661 / 29.905 = 0,892`**.

El error no es marginal: la diferencia mediana entre `fp_vol` y `bar_vol` es del
**11,9 %** del volumen de la barra, y es **simétrica** — el footprint sobra en el 49,9 %
de los casos y falta en el 50,1 %. No es un sesgo corregible; es desalineación.

Y `fp_vol == bar_vol` ocurre en apenas el **9,27 %** de los TRAPs exportados.

## 2. Por qué pasa

El `.cs` dedica ~400 líneas a este problema: `DrenarPorOHLCV`, `Abstener`,
`CoincideOHLCV`, `VerificarOHLC`, más contadores de residuales, mismatch y abstenciones.

Existe porque NT8 entrega **dos series separadas** —la primaria de 25 ticks y una
subserie de 1 tick— y hay que alinearlas sin poder consultar qué ticks formaron qué
barra. El indicador lo intenta por OHLCV y **falla la mayoría de las veces**.

## 3. Por qué eso hace la paridad indeseable

Un puerto que construye las barras **desde los mismos ticks** no tiene el problema:
footprint y barra son el mismo objeto por construcción. No hay nada que alinear.

Resultado de intentar la paridad de todos modos:

| | |
|---|---|
| TRAPs del oráculo | 7.454 en 7.267 barras |
| TRAPs del puerto | 4.479 en 4.397 barras |
| barras coincidentes, mejor alineación | 1.106 (15 %) |
| **con el mismo lado exacto** | **680 = 9,4 %** |

Y **9,4 % es casi exactamente el 9,27 % de barras donde el propio oráculo dice que su
footprint SÍ coincidía con la barra.** Las dos implementaciones concuerdan justo donde
NT8 no estaba desalineado.

**Reproducir el oráculo significaría reproducir su desalineación.** Eso no es paridad:
es copiar un defecto.

## 4. Lo que sí quedó verificado

Los flujos de ticks **son el mismo**, así que la discrepancia no es de datos:

| volumen por barra de 25 ticks | p25 | p50 | p75 | media |
|---|---|---|---|---|
| oráculo | 39 | 46 | 57 | 50,9 |
| puerto | 38 | 46 | 56 | 50,1 |

Y la geometría emitida tiene la misma forma exacta: `centroid`, `zone_lo`/`zone_hi` con
±medio tick, `n_rows`, `max_ratio`.

## 5. Consecuencias

### 5.1 El puerto no se llama BigTrap2

Es un objeto distinto: mismo algoritmo, footprint correcto. Se nombra
**`BigTrap2Exact`** y se declara que **no reproduce** al indicador de NT8, con el motivo.
La regla del proyecto es explícita: no se transportan resultados entre implementaciones
que no son la misma.

### 5.2 Todo resultado histórico de BigTrap2 hereda esta duda

Cualquier medición previa que use TRAPs exportados por el indicador está construida sobre
un footprint desalineado en el 89 % de las barras. **No los invalida automáticamente** —
la desalineación es simétrica y podría promediarse— pero es una fuente de ruido que nunca
estuvo declarada.

Esto **no** reabre las líneas cerradas de BigTrap2 (F2.7–F2.10 sobre 6E): aquéllas
midieron atracción y revisita de zona, y su alcance ya está declarado. Lo agrega como
limitación conocida.

### 5.3 Para GC no hace falta exportar oráculo — pero tampoco sirve para paridad

Un oráculo de GC tendría el mismo defecto. La decisión correcta es usar `BigTrap2Exact`
y declararlo, no perseguir una paridad que replicaría el error.

## 6. Qué queda pendiente

- El puerto implementa **detección de TRAP**. El ciclo de vida de zona
  (`ZONE_CREATED` / `TOUCHED` / `INVALIDATED` / `EXPIRED`) **no** está portado todavía.
- La aritmética entera (`round_away`, medios ticks) está replicada del `.cs`, incluido el
  detalle que allí se documenta como origen de 101 falsos positivos por 1 ULP.
- Falta verificar el comportamiento con `tick_size` de GC (0,10) contra el de 6E
  (0,00005): cuatro órdenes de magnitud de diferencia es donde aparecen los errores de
  redondeo.

---

## 7. Paridad contra el oráculo v2.5.2 de GC — `MEASURED_COMMITTED`

Oráculo: `E:\l2_parquet__Tick1.csv`, GC 12-26 tick:25, 2026-08-11 → 2026-08-21,
**45.307 barras**, **20.488 TRAPs**, `FOOTPRINT_MISMATCH` en el **0,11 %**.

### 7.1 El anclaje es lo que decide

| método de alineación | TRAPs exactos |
|---|---|
| barras uniformes de 25 desde un índice fijo | **5,96 %** |
| **anclaje por timestamp de cierre de cada `BARRA_PROCESADA`** | **81,15 %** |

`18.505` de `18.506` barras con TRAP anclaron con timestamp **exacto**. El oráculo tiene
5 barras cortas (largos 21, 18, 10) por frontera de sesión, y asumir 25 uniforme corre
toda la numeración.

**Los timestamps del oráculo están en hora local ART**: `+3 h` da coincidencia exacta al
nanosegundo. Mismo hallazgo que en los exports de ES.

### 7.2 El residual es de datos, no de algoritmo

Sobre las 18.505 barras ancladas:

| | coincidencia |
|---|---|
| `close` idéntico | **76,4 %** |
| `bar_vol` idéntico | **89,6 %** |

De los 3.777 eventos no exactos: **1.280 tienen volumen de barra distinto** (datos),
**0 tienen clasificación de quote distinta**, y 2.497 quedan como «mismo dato, resultado
distinto» — que al abrirlos resultan ser también diferencia de contenido: la barra del
oráculo cierra un tick más abajo, lo que mueve `closeHalfTick` y cambia qué filas
califican.

**Un offset global no lo arregla**: barriendo el índice de arranque, el mejor da **6,7 %**
de acuerdo en `close`, contra 76,4 % del anclaje por timestamp. Los dos flujos **derivan**
entre sí, no están desfasados.

Es la misma familia que en ES, donde el export de ticks y el dump NRD diferían un 0,8 %
en conteo de trades. Acá se manifiesta como deriva de frontera de barra.

### 7.3 Conclusión operativa

**El puerto implementa el algoritmo correctamente.** El 81 % exacto con anclaje, y el
0 % de discrepancia en clasificación de quote, lo confirman.

Pero para medir la hipótesis de Nico **no hace falta el puerto**: el oráculo v2.5.2 ya
entrega los 20.488 TRAPs, que son exactamente **las burbujas que él ve en el gráfico**.
El puerto sirve para variar parámetros, no para reemplazar al oráculo.
